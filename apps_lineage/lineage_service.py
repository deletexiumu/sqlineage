import requests
import json
import logging
from django.conf import settings
from django.utils import timezone
from apps_metadata.models import HiveTable
from .models import LineageRelation, ColumnLineage, LineageParseJob


logger = logging.getLogger(__name__)


class LineageService:
    def __init__(self):
        self.config = settings.SQLFLOW_CONFIG
        self.session = requests.Session()
        
        # 设置默认请求头，模拟浏览器请求以避免跨域问题
        self.session.headers.update({
            'Accept': 'application/json, text/javascript, */*; q=0.01',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Content-Type': 'application/json;charset=UTF-8',
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36',
            'X-Requested-With': 'XMLHttpRequest',
            'Origin': 'http://localhost:19600',
            'Referer': 'http://localhost:19600/',
        })

    def _init_session(self):
        """初始化会话，获取必要的Cookie"""
        try:
            base_url = self.config['url'].replace('/sqlflow/datalineage', '')
            home_url = f"{base_url}/"
            
            logger.info(f"Initializing session by visiting: {home_url}")
            response = self.session.get(home_url, timeout=10)
            
            if response.status_code == 200:
                logger.info(f"Session initialized successfully. Cookies: {dict(self.session.cookies)}")
            else:
                logger.warning(f"Failed to initialize session: {response.status_code}")
                
        except Exception as e:
            logger.warning(f"Session initialization failed: {str(e)}")
            # 继续执行，可能服务不需要会话

    def _clean_name(self, name):
        """
        清理表名、字段名，去除反引号、空格等特殊字符，进行归一化处理
        
        Args:
            name (str): 原始名称
            
        Returns:
            str: 清理后的名称
        """
        if not name:
            return name
        
        # 去除各种引号
        cleaned = name.strip()
        cleaned = cleaned.strip('`"\'[]')
        
        # 去除首尾空格
        cleaned = cleaned.strip()
        
        return cleaned

    def parse_sql(self, sql_text):
        if not sql_text or not sql_text.strip():
            logger.error("Empty SQL text provided")
            return None
        
        # 如果启用模拟模式，返回示例数据
        if self.config.get('mock_mode', False):
            return self._mock_parse_sql(sql_text)
            
        payload = {
            "dbVendor": "dbvhive",
            "sqlText": sql_text,
            "ignoreRecordSet": True,
            "showConstantTable": False,
            "simpleShowFunction": False,
            "indirect": False,
            "tableLevel": False,
            "showTransform": False
        }
        
        try:
            logger.info(f"Sending SQL to lineage service: {self.config['url']}")
            
            # 确保有正确的会话，如果需要的话先访问主页获取会话
            if not self.session.cookies.get('JSESSIONID'):
                self._init_session()
            
            response = self.session.post(
                self.config['url'],
                json=payload,
                timeout=self.config['timeout']
            )
            
            logger.info(f"Response status: {response.status_code}")
            logger.info(f"Response content: {response.text[:500]}...")
            
            response.raise_for_status()
            
            result = response.json()
            if result.get('code') == 200:
                data = result.get('data')
                if isinstance(data, str):
                    return json.loads(data)
                elif isinstance(data, dict):
                    return data
                else:
                    logger.error(f"Unexpected data format: {type(data)}")
                    return None
            else:
                logger.error(f"SQL parsing failed: {result.get('msg', 'Unknown error')}")
                return None
                
        except requests.exceptions.ConnectionError as e:
            logger.error(f"Cannot connect to SQL lineage service at {self.config['url']}: {str(e)}")
            raise Exception(f"血缘解析服务无法访问，请确保服务运行在 {self.config['url']}")
        except requests.exceptions.Timeout as e:
            logger.error(f"SQL parsing service timeout: {str(e)}")
            raise Exception("血缘解析服务响应超时")
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to parse SQL: {str(e)}")
            raise Exception(f"血缘解析服务请求失败: {str(e)}")
        except json.JSONDecodeError as e:
            logger.error(f"Failed to decode response: {str(e)}")
            raise Exception("血缘解析服务返回无效响应")

    def _mock_parse_sql(self, sql_text):
        """模拟SQL解析，用于演示和测试"""
        import re
        logger.info("Using mock SQL parsing mode")
        
        # 简单的表名提取正则
        create_pattern = r'CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?([^\s\(]+)'
        insert_pattern = r'INSERT\s+(?:OVERWRITE\s+|INTO\s+)?TABLE\s+([^\s\(]+)'
        from_pattern = r'FROM\s+([^\s\;,\)]+)'
        join_pattern = r'(?:LEFT\s+|RIGHT\s+|INNER\s+|OUTER\s+)?JOIN\s+([^\s\;,\)]+)'
        
        tables = set()
        target_tables = set()
        source_tables = set()
        
        # 提取CREATE TABLE
        create_matches = re.findall(create_pattern, sql_text, re.IGNORECASE)
        for match in create_matches:
            table_name = self._clean_name(match)
            target_tables.add(table_name)
            tables.add(table_name)
        
        # 提取INSERT TABLE
        insert_matches = re.findall(insert_pattern, sql_text, re.IGNORECASE)
        for match in insert_matches:
            table_name = self._clean_name(match)
            target_tables.add(table_name)
            tables.add(table_name)
        
        # 提取FROM TABLE
        from_matches = re.findall(from_pattern, sql_text, re.IGNORECASE)
        for match in from_matches:
            table_name = self._clean_name(match)
            source_tables.add(table_name)
            tables.add(table_name)
        
        # 提取JOIN TABLE
        join_matches = re.findall(join_pattern, sql_text, re.IGNORECASE)
        for match in join_matches:
            table_name = self._clean_name(match)
            source_tables.add(table_name)
            tables.add(table_name)
        
        # 构造模拟响应
        relationships = []
        if target_tables and source_tables:
            for target_table in target_tables:
                for source_table in source_tables:
                    if target_table != source_table:
                        relationships.append({
                            "id": f"mock_{len(relationships) + 1}",
                            "type": "fdd",
                            "effectType": "insert",
                            "target": {
                                "id": f"target_{len(relationships) + 1}",
                                "parentName": target_table
                            },
                            "sources": [{
                                "id": f"source_{len(relationships) + 1}",
                                "parentName": source_table
                            }],
                            "processId": "mock_process"
                        })
        
        mock_response = {
            "code": 200,
            "data": {
                "sqlflow": {
                    "relationships": relationships
                }
            }
        }
        
        logger.info(f"Mock parsing found {len(relationships)} relationships")
        return mock_response["data"]

    def extract_lineage_relations(self, parsed_data, sql_script_path=""):
        relations = []
        skipped_tables = set()  # 记录跳过的表
        
        try:
            # 处理真实SQLFlow服务的响应格式
            if 'data' in parsed_data and 'sqlflow' in parsed_data['data']:
                # 真实SQLFlow服务格式
                sqlflow_data = parsed_data['data']['sqlflow']
            elif 'sqlflow' in parsed_data:
                # 模拟格式
                sqlflow_data = parsed_data['sqlflow']
            else:
                logger.warning("No sqlflow data found in response")
                return []
                
            relationships = sqlflow_data.get('relationships', [])
            logger.info(f"Found {len(relationships)} relationships in SQLFlow data")
            
            for relationship in relationships:
                try:
                    # Get source table info
                    sources = relationship.get('sources', [])
                    target = relationship.get('target', {})
                    
                    if not sources or not target:
                        continue
                    
                    # Extract target table information
                    target_parent_name = target.get('parentName', '')
                    target_parent_name = self._clean_name(target_parent_name)
                    if '.' in target_parent_name:
                        target_db, target_table = target_parent_name.split('.', 1)
                        target_db = self._clean_name(target_db)
                        target_table = self._clean_name(target_table)
                    else:
                        continue
                    
                    # 只匹配现有的目标表，不创建新表
                    try:
                        target_hive_table = HiveTable.objects.get(
                            name=target_table,
                            database=target_db
                        )
                    except HiveTable.DoesNotExist:
                        skipped_tables.add(f"{target_db}.{target_table}")
                        logger.debug(f"目标表 {target_db}.{target_table} 在元数据中不存在，跳过血缘关系创建")
                        continue
                    
                    # Process each source
                    for source in sources:
                        source_parent_name = source.get('parentName', '')
                        source_parent_name = self._clean_name(source_parent_name)
                        if '.' in source_parent_name:
                            source_db, source_table = source_parent_name.split('.', 1)
                            source_db = self._clean_name(source_db)
                            source_table = self._clean_name(source_table)
                        else:
                            continue
                        
                        # 只匹配现有的源表，不创建新表
                        try:
                            source_hive_table = HiveTable.objects.get(
                                name=source_table,
                                database=source_db
                            )
                        except HiveTable.DoesNotExist:
                            skipped_tables.add(f"{source_db}.{source_table}")
                            logger.debug(f"源表 {source_db}.{source_table} 在元数据中不存在，跳过血缘关系创建")
                            continue
                        
                        # Create or update lineage relation
                        relation, created = LineageRelation.objects.get_or_create(
                            source_table=source_hive_table,
                            target_table=target_hive_table,
                            sql_script_path=sql_script_path,
                            defaults={
                                'relation_type': relationship.get('effectType', 'insert'),
                                'process_id': relationship.get('processId', '')
                            }
                        )
                        
                        # Create column lineage if available
                        source_column = source.get('column', '')
                        target_column = target.get('column', '')
                        
                        if source_column and target_column:
                            # 清理字段名
                            source_column_clean = self._clean_name(source_column)
                            target_column_clean = self._clean_name(target_column)
                            
                            try:
                                column_lineage, created = ColumnLineage.objects.get_or_create(
                                    relation=relation,
                                    source_column=source_column_clean,
                                    target_column=target_column_clean
                                )
                                if created:
                                    logger.info(f"Created column lineage: {source_column_clean} -> {target_column_clean}")
                                else:
                                    logger.debug(f"Column lineage already exists: {source_column_clean} -> {target_column_clean}")
                            except Exception as col_e:
                                logger.error(f"Failed to create column lineage {source_column_clean} -> {target_column_clean}: {str(col_e)}")
                        else:
                            logger.debug(f"Missing column info - source: '{source_column}', target: '{target_column}'")
                        
                        relations.append(relation)
                        
                except Exception as e:
                    logger.error(f"Error processing relationship: {str(e)}")
                    continue
            
            # 记录解析总结
            if skipped_tables:
                logger.info(f"Git仓库解析完成: 创建了{len(relations)}个血缘关系，跳过了{len(skipped_tables)}个不存在的表: {', '.join(sorted(skipped_tables))}")
            else:
                logger.info(f"Git仓库解析完成: 创建了{len(relations)}个血缘关系，所有表都在现有元数据中找到")
            
            return relations
            
        except Exception as e:
            logger.error(f"Error extracting lineage relations: {str(e)}")
            return []

    def get_column_lineage_graph(self, parsed_data):
        """获取字段级血缘关系的图形化数据"""
        try:
            # 处理真实SQLFlow服务的响应格式
            if 'data' in parsed_data and 'sqlflow' in parsed_data['data']:
                sqlflow_data = parsed_data['data']['sqlflow']
            elif 'sqlflow' in parsed_data:
                sqlflow_data = parsed_data['sqlflow']
            else:
                logger.warning("No sqlflow data found in response")
                return {'tables': [], 'relationships': []}
                
            relationships = sqlflow_data.get('relationships', [])
            
            # 收集所有表和字段信息
            tables_info = {}
            column_relationships = []
            
            for relationship in relationships:
                try:
                    sources = relationship.get('sources', [])
                    target = relationship.get('target', {})
                    
                    if not sources or not target:
                        continue
                    
                    # 处理目标表
                    target_table_name = target.get('parentName', '')
                    target_column = target.get('column', '')
                    target_table_name_clean = None
                    target_column_clean = None
                    
                    if target_table_name:
                        # 清理表名
                        target_table_name_clean = self._clean_name(target_table_name)
                        
                        if target_table_name_clean not in tables_info:
                            tables_info[target_table_name_clean] = {
                                'name': target_table_name_clean,
                                'type': 'target',
                                'columns': set()
                            }
                    
                    if target_column:
                        # 清理字段名
                        target_column_clean = self._clean_name(target_column)
                        if target_table_name_clean:
                            tables_info[target_table_name_clean]['columns'].add(target_column_clean)
                    
                    # 处理源表
                    for source in sources:
                        source_table_name = source.get('parentName', '')
                        source_column = source.get('column', '')
                        
                        if source_table_name:
                            # 清理表名和字段名
                            source_table_name_clean = self._clean_name(source_table_name)
                            
                            if source_table_name_clean not in tables_info:
                                tables_info[source_table_name_clean] = {
                                    'name': source_table_name_clean,
                                    'type': 'source',
                                    'columns': set()
                                }
                                
                            if source_column:
                                source_column_clean = self._clean_name(source_column)
                                tables_info[source_table_name_clean]['columns'].add(source_column_clean)
                                
                                # 添加字段级关系（只有当源字段和目标字段都存在时）
                                if target_table_name_clean and target_column_clean:
                                    column_relationships.append({
                                        'id': f"rel_{len(column_relationships)}",
                                        'source_table': source_table_name_clean,
                                        'source_column': source_column_clean,
                                        'target_table': target_table_name_clean,
                                        'target_column': target_column_clean,
                                        'relation_type': relationship.get('effectType', 'insert')
                                    })
                                
                except Exception as e:
                    logger.error(f"Error processing relationship for graph: {str(e)}")
                    continue
            
            # 转换为列表格式
            tables_list = []
            for table_name, table_info in tables_info.items():
                tables_list.append({
                    'name': table_name,
                    'type': table_info['type'],
                    'columns': list(table_info['columns'])
                })
            
            return {
                'tables': tables_list,
                'relationships': column_relationships
            }
            
        except Exception as e:
            logger.error(f"Error generating column lineage graph: {str(e)}")
            return {'tables': [], 'relationships': []}

    def parse_sql_file(self, sql_text, file_path=""):
        parsed_data = self.parse_sql(sql_text)
        if parsed_data:
            return self.extract_lineage_relations(parsed_data, file_path)
        return []

    def get_downstream_impact(self, table_name):
        try:
            if '.' in table_name:
                database, table = table_name.split('.', 1)
            else:
                database = 'default'
                table = table_name
            
            source_table = HiveTable.objects.get(name=table, database=database)
            
            # Get direct downstream tables
            direct_relations = LineageRelation.objects.filter(
                source_table=source_table
            ).select_related('target_table')
            
            downstream_tables = set()
            visited = set()
            
            def traverse_downstream(current_table):
                if current_table.id in visited:
                    return
                visited.add(current_table.id)
                
                relations = LineageRelation.objects.filter(
                    source_table=current_table
                ).select_related('target_table')
                
                for relation in relations:
                    downstream_tables.add(relation.target_table)
                    traverse_downstream(relation.target_table)
            
            traverse_downstream(source_table)
            
            return {
                'source_table': {
                    'name': source_table.full_name,
                    'database': source_table.database,
                    'table': source_table.name
                },
                'downstream_tables': [
                    {
                        'name': table.full_name,
                        'database': table.database,
                        'table': table.name
                    }
                    for table in downstream_tables
                ],
                'total_count': len(downstream_tables)
            }
            
        except HiveTable.DoesNotExist:
            return {'error': f'Table {table_name} not found'}
        except Exception as e:
            logger.error(f"Error getting downstream impact: {str(e)}")
            return {'error': str(e)}

    def batch_parse_repository(self, git_repo):
        from apps_git.git_service import GitService
        
        job = LineageParseJob.objects.create(
            git_repo=git_repo,
            status='pending'
        )
        
        try:
            job.status = 'running'
            job.started_at = timezone.now()
            job.save()
            
            git_service = GitService(git_repo)
            sql_files = git_service.get_sql_files()
            
            job.total_files = len(sql_files)
            job.save()
            
            for sql_file in sql_files:
                try:
                    content = git_service.read_file(sql_file['path'])
                    if content:
                        self.parse_sql_file(content, sql_file['path'])
                    
                    job.processed_files += 1
                    job.save()
                    
                except Exception as e:
                    logger.error(f"Failed to process file {sql_file['path']}: {str(e)}")
                    job.failed_files += 1
                    job.save()
                    continue
            
            job.status = 'completed'
            job.completed_at = timezone.now()
            job.save()
            
            return job
            
        except Exception as e:
            job.status = 'failed'
            job.error_message = str(e)
            job.completed_at = timezone.now()
            job.save()
            logger.error(f"Batch parsing failed: {str(e)}")
            return job