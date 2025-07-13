"""
SQL Language Server Protocol 实现
提供SQL语法分析、自动补全、语法检查等功能
"""
import json
import logging
import re
from typing import Dict, List, Optional, Any, Tuple
from django.conf import settings
import sqlparse
from sqlparse import sql
from sqlparse.tokens import Keyword, Name

logger = logging.getLogger(__name__)


class SQLLanguageServer:
    """SQL语言服务器，提供LSP协议支持"""
    
    def __init__(self):
        self.capabilities = {
            "textDocumentSync": 1,  # Full document sync
            "completionProvider": {
                "resolveProvider": False,
                "triggerCharacters": [".", " ", "\n", "\t"]
            },
            "hoverProvider": True,
            "diagnosticsProvider": True,
            "definitionProvider": True,
            "referencesProvider": True
        }
        self._cached_tables = None
        self._cached_schemas = None
    
    def get_capabilities(self):
        """返回服务器能力"""
        return self.capabilities
    
    def _get_metadata_cache(self):
        """获取元数据缓存"""
        if self._cached_tables is None:
            self._refresh_metadata_cache()
        return self._cached_tables, self._cached_schemas
    
    def _refresh_metadata_cache(self):
        """刷新元数据缓存"""
        try:
            # 延迟导入Django模型，避免应用初始化时的循环依赖
            from apps_metadata.models import HiveTable
            tables = HiveTable.objects.select_related().all()
            self._cached_tables = {}
            self._cached_schemas = set()
            
            for table in tables:
                full_name = f"{table.database}.{table.name}"
                self._cached_tables[full_name] = {
                    'database': table.database,
                    'name': table.name,
                    'full_name': full_name,
                    'comment': '',  # HiveTable模型没有comment字段
                    'columns': [
                        {
                            'name': col.get('name', ''),
                            'type': col.get('type', ''),
                            'comment': col.get('comment', '')
                        }
                        for col in table.columns  # table.columns 返回解析后的JSON列表
                    ]
                }
                self._cached_schemas.add(table.database)
                
            logger.info(f"Refreshed metadata cache: {len(self._cached_tables)} tables, {len(self._cached_schemas)} schemas")
            
        except Exception as e:
            logger.error(f"Failed to refresh metadata cache: {str(e)}")
            self._cached_tables = {}
            self._cached_schemas = set()
    
    def provide_completion(self, document_text: str, line: int, character: int) -> List[Dict]:
        """提供自动补全建议"""
        try:
            tables_cache, schemas_cache = self._get_metadata_cache()
            
            # 分析当前光标位置的上下文
            lines = document_text.split('\n')
            if line >= len(lines):
                return []
            
            current_line = lines[line]
            text_before_cursor = current_line[:character]
            
            # 获取当前SQL语句段落
            full_text_before = '\n'.join(lines[:line]) + '\n' + text_before_cursor
            context = self._analyze_sql_context(full_text_before)
            
            suggestions = []
            
            # 根据上下文提供不同的建议
            if context['type'] == 'table_reference':
                # 在FROM/JOIN等位置，优先建议表名
                for table_name, table_info in tables_cache.items():
                    suggestions.append({
                        'label': table_name,
                        'kind': 8,  # Class (表)
                        'detail': f"表: {table_info['comment']}",
                        'documentation': f"数据库: {table_info['database']}\n表名: {table_info['name']}\n说明: {table_info['comment']}",
                        'insertText': table_name,
                        'sortText': f"0_{table_name}"  # 高优先级
                    })
                    
                # 添加数据库名建议
                for schema in schemas_cache:
                    suggestions.append({
                        'label': schema,
                        'kind': 9,  # Module (数据库)
                        'detail': f"数据库: {schema}",
                        'insertText': schema,
                        'sortText': f"1_{schema}"
                    })
                    
            elif context['type'] == 'column_reference':
                # 在SELECT等位置，优先建议字段名
                # 首先查找表别名映射
                table_aliases = context.get('table_aliases') or self._extract_table_aliases(full_text_before)
                
                # 如果有表别名前缀，只显示该表的字段
                if context.get('table_prefix'):
                    table_alias = context['table_prefix']
                    target_table = table_aliases.get(table_alias)
                    
                    logger.info(f"Looking for table alias '{table_alias}' -> '{target_table}'")
                    logger.info(f"Available tables in cache: {list(tables_cache.keys())[:5]}...")  # 显示前5个表名
                    
                    # 首先尝试精确匹配
                    table_found = False
                    if target_table:
                        # 尝试多种匹配方式
                        possible_keys = [
                            target_table,  # 原始表名
                            f"dwd_clk.{target_table}",  # 带schema的完整表名
                            target_table.split('.')[-1] if '.' in target_table else target_table  # 只取表名部分
                        ]
                        
                        for possible_key in possible_keys:
                            if possible_key in tables_cache:
                                table_info = tables_cache[possible_key]
                                logger.info(f"Found table {possible_key} with {len(table_info['columns'])} columns")
                                table_found = True
                                
                                for col in table_info['columns']:
                                    suggestions.append({
                                        'label': col['name'],
                                        'kind': 5,  # Field (字段)
                                        'detail': f"字段: {col['type']} - {col['comment']}" if col['comment'] else f"字段: {col['type']}",
                                        'documentation': f"表: {possible_key}\n字段: {col['name']}\n类型: {col['type']}\n备注: {col['comment'] if col['comment'] else '无'}",
                                        'insertText': col['name'],
                                        'sortText': f"0_{col['name']}"
                                    })
                                break
                    
                    # 如果精确匹配失败，尝试模糊匹配
                    if not table_found:
                        logger.warning(f"Table alias '{table_alias}' -> '{target_table}' not found in cache, trying fuzzy matching...")
                        
                        for table_name, table_info in tables_cache.items():
                            # 检查多种匹配条件
                            target_lower = target_table.lower() if target_table else ''
                            table_lower = table_name.lower()
                            
                            match_conditions = [
                                target_lower in table_lower,
                                table_lower.endswith(target_lower.split('.')[-1]) if '.' in target_lower else False,
                                target_lower.split('.')[-1] in table_lower if '.' in target_lower else False,
                                table_alias.lower() in table_lower
                            ]
                            
                            if any(match_conditions):
                                logger.info(f"Fuzzy match found: {table_name} for alias {table_alias}")
                                for col in table_info['columns'][:8]:  # 限制数量避免太多
                                    suggestions.append({
                                        'label': col['name'],
                                        'kind': 5,
                                        'detail': f"推测字段: {col['type']} - {col['comment']}" if col['comment'] else f"推测字段: {col['type']}",
                                        'documentation': f"推测表: {table_name}\n字段: {col['name']}\n类型: {col['type']}\n备注: {col['comment'] if col['comment'] else '无'}",
                                        'insertText': col['name'],
                                        'sortText': f"1_{col['name']}"
                                    })
                                break
                else:
                    # 显示引用表的字段
                    referenced_tables = self._find_referenced_tables(full_text_before)
                    
                    if referenced_tables:
                        # 如果找到了引用的表，显示这些表的字段
                        for table_name in referenced_tables:
                            if table_name in tables_cache:
                                table_info = tables_cache[table_name]
                                for col in table_info['columns']:
                                    suggestions.append({
                                        'label': col['name'],
                                        'kind': 5,  # Field
                                        'detail': f"{col['type']} - {col['comment']}" if col['comment'] else col['type'],
                                        'documentation': f"表: {table_name}\n字段: {col['name']}\n类型: {col['type']}\n备注: {col['comment'] if col['comment'] else '无'}",
                                        'insertText': col['name'],
                                        'sortText': f"0_{col['name']}"
                                    })
                    else:
                        # 没有找到引用的表时，显示最常用的字段名（适用于SELECT开始时）
                        common_columns = {}
                        for table_name, table_info in tables_cache.items():
                            for col in table_info['columns']:
                                col_name = col['name']
                                if col_name not in common_columns:
                                    common_columns[col_name] = {
                                        'name': col_name,
                                        'type': col['type'],
                                        'comment': col['comment'],
                                        'count': 0,
                                        'example_table': table_name
                                    }
                                common_columns[col_name]['count'] += 1
                        
                        # 按出现频率排序，显示最常见的字段
                        sorted_columns = sorted(common_columns.values(), key=lambda x: x['count'], reverse=True)
                        for col_info in sorted_columns[:7]:  # 显示前7个最常见的字段
                            suggestions.append({
                                'label': col_info['name'],
                                'kind': 5,  # Field
                                'detail': f"{col_info['type']} - {col_info['comment']}" if col_info['comment'] else col_info['type'],
                                'documentation': f"常用字段: {col_info['name']}\n类型: {col_info['type']}\n备注: {col_info['comment'] if col_info['comment'] else '无'}\n出现在 {col_info['count']} 个表中\n示例表: {col_info['example_table']}",
                                'insertText': col_info['name'],
                                'sortText': f"0_{col_info['name']}"
                            })
                    
                    # 添加SQL关键字建议（高优先级）
                    keywords = self._get_sql_keyword_suggestions()[:3]
                    suggestions.extend(keywords)
                    
                    # 如果没有找到字段或字段很少，添加一些SQL函数作为补充
                    if len(suggestions) < 7:
                        functions = self._get_sql_function_suggestions()[:2]
                        suggestions.extend(functions)
                
            elif context['type'] == 'keyword_continuation':
                # 关键字继续类型，例如GROUP -> GROUP BY
                keyword_continuations = self._get_keyword_continuations(context.get('last_keyword'))
                suggestions.extend(keyword_continuations)
                
                # 如果在某些关键字后，也可能需要字段补全
                if context.get('last_keyword') in ['GROUP', 'ORDER']:
                    referenced_tables = self._find_referenced_tables(full_text_before)
                    if referenced_tables:
                        for table_name in referenced_tables[:2]:  # 限制表数量
                            if table_name in tables_cache:
                                table_info = tables_cache[table_name]
                                for col in table_info['columns'][:3]:  # 每个表限制字段数量
                                    suggestions.append({
                                        'label': col['name'],
                                        'kind': 5,
                                        'detail': f"{col['type']} - {col['comment']}" if col['comment'] else col['type'],
                                        'documentation': f"表: {table_name}\n字段: {col['name']}\n类型: {col['type']}\n备注: {col['comment'] if col['comment'] else '无'}",
                                        'insertText': col['name'],
                                        'sortText': f"2_{col['name']}"
                                    })
                
            elif context['type'] == 'general':
                # 通用建议，包含表名、数据库名和SQL关键字
                
                # 表名建议
                for table_name, table_info in tables_cache.items():
                    suggestions.append({
                        'label': table_name,
                        'kind': 8,  # Class
                        'detail': f"表: {table_info['comment']}",
                        'insertText': table_name,
                        'sortText': f"1_{table_name}"
                    })
                
                # SQL关键字建议（高优先级）
                keywords = self._get_sql_keyword_suggestions()[:5]
                suggestions.extend(keywords)
                
                # SQL函数建议
                functions = self._get_sql_function_suggestions()[:3]
                suggestions.extend(functions)
            
            # 限制建议数量，避免性能问题
            return suggestions[:10]
            
        except Exception as e:
            logger.error(f"Error in provide_completion: {str(e)}")
            return []
    
    def _analyze_sql_context(self, text_before_cursor: str) -> Dict[str, Any]:
        """分析SQL上下文，确定当前位置适合什么类型的补全"""
        text_upper = text_before_cursor.upper()
        
        # 查找最后一个完整的SQL关键字
        keywords = ['SELECT', 'FROM', 'WHERE', 'JOIN', 'INNER JOIN', 'LEFT JOIN', 'RIGHT JOIN', 'GROUP BY', 'ORDER BY', 'HAVING']
        
        last_keyword_pos = -1
        last_keyword = None
        
        for keyword in keywords:
            pos = text_upper.rfind(keyword)
            if pos > last_keyword_pos:
                last_keyword_pos = pos
                last_keyword = keyword
        
        # 增强的别名.字段检测
        dot_match = re.search(r'(\w+)\.(\w*)$', text_before_cursor)
        if dot_match:
            table_alias = dot_match.group(1)
            partial_column = dot_match.group(2)
            
            # 提取表别名映射
            table_aliases = self._extract_table_aliases(text_before_cursor)
            
            logger.info(f"Detected alias reference: {table_alias}.{partial_column}, available aliases: {table_aliases}")
            
            return {
                'type': 'column_reference',
                'table_prefix': table_alias,
                'partial_column': partial_column,
                'table_aliases': table_aliases
            }
        
        # 检测关键字后的空格位置，可能需要关键字补全
        keyword_space_pattern = r'\b(SELECT|WHERE|GROUP|ORDER|HAVING)\s+$'
        if re.search(keyword_space_pattern, text_upper):
            return {'type': 'keyword_continuation', 'last_keyword': last_keyword}
        
        # 特殊处理：检查是否在SELECT...FROM之间的位置（字段选择区域）
        select_from_pattern = r'SELECT\s+.*?\s+FROM\s+'
        if re.search(select_from_pattern, text_upper, re.DOTALL):
            # 如果已经有FROM，检查最后的关键字
            if last_keyword in ['FROM', 'JOIN', 'INNER JOIN', 'LEFT JOIN', 'RIGHT JOIN']:
                return {'type': 'table_reference', 'keyword': last_keyword}
            elif last_keyword in ['WHERE', 'GROUP BY', 'ORDER BY', 'HAVING']:
                return {'type': 'column_reference', 'keyword': last_keyword}
            else:
                return {'type': 'general'}
        elif re.match(r'SELECT\s+', text_upper):
            # 在SELECT后但还没有FROM，应该是字段选择
            return {'type': 'column_reference', 'keyword': 'SELECT'}
        
        # 根据最后的关键字确定上下文
        if last_keyword in ['FROM', 'JOIN', 'INNER JOIN', 'LEFT JOIN', 'RIGHT JOIN']:
            return {'type': 'table_reference', 'keyword': last_keyword}
        elif last_keyword in ['SELECT', 'WHERE', 'GROUP BY', 'ORDER BY', 'HAVING']:
            return {'type': 'column_reference', 'keyword': last_keyword}
        else:
            return {'type': 'general'}
    
    def _extract_table_aliases_with_sqlparse(self, sql_text: str) -> Dict[str, str]:
        """使用sqlparse提取SQL中的表别名映射"""
        aliases = {}
        
        try:
            # 解析SQL语句
            parsed = sqlparse.parse(sql_text)[0]
            
            # 查找FROM关键字后的内容
            from_found = False
            
            for token in parsed.tokens:
                if token.ttype is Keyword and token.value.upper() == 'FROM':
                    from_found = True
                    continue
                
                if from_found:
                    # 如果遇到其他关键字，停止解析
                    if token.ttype is Keyword and token.value.upper() in ['WHERE', 'GROUP', 'ORDER', 'HAVING', 'LIMIT']:
                        break
                    
                    # 跳过空白符
                    if token.is_whitespace:
                        continue
                    
                    # 处理标识符
                    if isinstance(token, sql.Identifier):
                        self._extract_alias_from_identifier(token, aliases)
                    elif isinstance(token, sql.IdentifierList):
                        for identifier in token.get_identifiers():
                            self._extract_alias_from_identifier(identifier, aliases)
                    # 对于复杂的标识符，可能被解析为普通token
                    elif hasattr(token, 'tokens') and token.tokens:
                        self._parse_complex_identifier(token, aliases)
            
        except Exception as e:
            logger.error(f"Failed to parse SQL with sqlparse: {str(e)}")
            # 回退到正则表达式方法
            return self._extract_table_aliases_regex_fallback(sql_text)
        
        logger.info(f"sqlparse extracted table aliases: {aliases}")
        return aliases
    
    def _parse_complex_identifier(self, token, aliases: Dict[str, str]):
        """解析复杂的标识符token，提取表名和别名"""
        try:
            # 将token转换为字符串，然后分析
            token_str = str(token).strip()
            
            # 尝试识别 "schema.table alias" 或 "table alias" 格式
            parts = token_str.split()
            if len(parts) >= 2:
                table_part = parts[0]  # 表名部分
                alias_part = parts[-1]  # 别名部分（最后一个部分）
                
                # 确保别名不是SQL关键字
                if alias_part.upper() not in ['AS', 'ON', 'WHERE', 'GROUP', 'ORDER', 'HAVING']:
                    aliases[alias_part] = table_part
                    logger.info(f"sqlparse complex identifier: {alias_part} -> {table_part}")
            
        except Exception as e:
            logger.debug(f"Failed to parse complex identifier: {str(e)}")
    
    def _parse_identifiers_for_aliases(self, identifiers: List, aliases: Dict[str, str]):
        """解析标识符列表，提取表别名"""
        current_table = None
        
        for token in identifiers:
            if token.is_whitespace or str(token).strip() == ',':
                continue
            
            token_str = str(token).strip()
            
            # 如果是标识符且包含点号，可能是schema.table格式
            if '.' in token_str and not token_str.startswith('('):
                current_table = token_str
            # 如果是简单标识符
            elif token_str and not token_str.upper() in ['AS', 'ON', 'USING']:
                if current_table is None:
                    current_table = token_str
                else:
                    # 这是别名
                    aliases[token_str] = current_table
                    logger.info(f"sqlparse found alias: {token_str} -> {current_table}")
                    current_table = None
    
    def _extract_alias_from_identifier(self, identifier, aliases: Dict[str, str]):
        """从单个标识符中提取别名"""
        try:
            # 先尝试标准方法
            real_name = identifier.get_real_name()
            alias = identifier.get_alias()
            
            if real_name and alias:
                aliases[alias] = real_name
                logger.info(f"sqlparse identifier alias: {alias} -> {real_name}")
                return
            
            # 如果标准方法失败，手动解析token
            if hasattr(identifier, 'tokens') and identifier.tokens:
                tokens = [t for t in identifier.tokens if not t.is_whitespace]
                
                # 寻找模式：name1.name2 name3 或 name1 name2
                if len(tokens) >= 2:
                    # 最后一个非空白token通常是别名
                    last_token = tokens[-1]
                    if isinstance(last_token, sql.Identifier):
                        # 嵌套标识符的情况
                        alias_str = str(last_token).strip()
                    else:
                        alias_str = str(last_token).strip()
                    
                    # 前面的tokens组成表名
                    table_parts = []
                    for token in tokens[:-1]:
                        if not token.is_whitespace:
                            table_parts.append(str(token).strip())
                    
                    if table_parts and alias_str:
                        table_name = ''.join(table_parts)  # 拼接表名部分
                        # 确保别名不是SQL关键字或标点符号
                        if (alias_str.upper() not in ['AS', 'ON', 'WHERE', 'GROUP', 'ORDER', 'HAVING'] and
                            alias_str.isalnum()):
                            aliases[alias_str] = table_name
                            logger.info(f"sqlparse manual alias extraction: {alias_str} -> {table_name}")
            
        except Exception as e:
            logger.debug(f"Failed to extract alias from identifier: {str(e)}")
    
    def _extract_table_aliases_regex_fallback(self, sql_text: str) -> Dict[str, str]:
        """正则表达式回退方法（保留原有逻辑作为备选）"""
        aliases = {}
        
        # 简化模式：FROM table alias (忽略AS关键字)
        simple_pattern = r'(?:FROM|JOIN)\s+(\S+)\s+([a-zA-Z_][a-zA-Z0-9_]*)'
        cleaned_sql = re.sub(r'\s+', ' ', sql_text.strip())
        
        matches = re.finditer(simple_pattern, cleaned_sql, re.IGNORECASE)
        for match in matches:
            table_name = match.group(1).strip()
            alias = match.group(2).strip()
            # 确保别名不是SQL关键字
            if alias.upper() not in ['WHERE', 'GROUP', 'ORDER', 'HAVING', 'LIMIT', 'UNION', 'INNER', 'LEFT', 'RIGHT', 'FULL', 'JOIN']:
                aliases[alias] = table_name
                logger.info(f"regex fallback alias: {alias} -> {table_name}")
        
        return aliases
    
    def _extract_table_aliases(self, sql_text: str) -> Dict[str, str]:
        """提取SQL中的表别名映射（主入口方法）"""
        # 优先使用sqlparse方法
        return self._extract_table_aliases_with_sqlparse(sql_text)
    
    def _is_table_referenced(self, sql_text: str, table_name: str) -> bool:
        """检查表是否在SQL中被引用"""
        # 简单检查表名是否出现在FROM或JOIN子句中
        pattern = r'(?:FROM|JOIN)\s+' + re.escape(table_name) + r'(?:\s|$|,)'
        return bool(re.search(pattern, sql_text, re.IGNORECASE))
    
    def _find_referenced_tables(self, sql_text: str) -> List[str]:
        """找出SQL中引用的所有表"""
        referenced_tables = []
        
        # 匹配FROM和JOIN子句中的表名
        pattern = r'(?:FROM|JOIN)\s+([^\s\(,]+)'
        matches = re.findall(pattern, sql_text, re.IGNORECASE)
        
        for match in matches:
            # 清理表名（移除可能的别名）
            table_name = match.strip()
            if table_name not in referenced_tables:
                referenced_tables.append(table_name)
        
        return referenced_tables
    
    def _get_sql_keyword_suggestions(self) -> List[Dict]:
        """获取SQL关键字建议"""
        keywords = [
            ('SELECT', 'SQL关键字 - 选择查询语句'),
            ('FROM', 'SQL关键字 - 指定数据来源表'),
            ('WHERE', 'SQL关键字 - 条件过滤'),
            ('GROUP BY', 'SQL关键字 - 分组聚合'),
            ('ORDER BY', 'SQL关键字 - 结果排序'),
            ('HAVING', 'SQL关键字 - 分组条件过滤'),
            ('JOIN', 'SQL关键字 - 表连接'),
            ('INNER JOIN', 'SQL关键字 - 内连接'),
            ('LEFT JOIN', 'SQL关键字 - 左连接'),
            ('RIGHT JOIN', 'SQL关键字 - 右连接'),
            ('FULL JOIN', 'SQL关键字 - 全连接'),
            ('CASE WHEN', 'SQL关键字 - 条件表达式'),
            ('UNION', 'SQL关键字 - 联合查询'),
            ('UNION ALL', 'SQL关键字 - 联合查询(包含重复)'),
            ('DISTINCT', 'SQL关键字 - 去重'),
            ('AS', 'SQL关键字 - 别名'),
            ('AND', 'SQL关键字 - 逻辑与'),
            ('OR', 'SQL关键字 - 逻辑或'),
            ('NOT', 'SQL关键字 - 逻辑非'),
            ('IN', 'SQL关键字 - 包含判断'),
            ('EXISTS', 'SQL关键字 - 存在判断'),
            ('LIKE', 'SQL关键字 - 模糊匹配'),
            ('BETWEEN', 'SQL关键字 - 范围判断'),
            ('IS NULL', 'SQL关键字 - 空值判断'),
            ('IS NOT NULL', 'SQL关键字 - 非空判断'),
        ]
        
        return [
            {
                'label': keyword[0],
                'kind': 14,  # Keyword
                'detail': keyword[1],
                'documentation': f"SQL关键字: {keyword[0]}\n说明: {keyword[1]}",
                'insertText': keyword[0],
                'sortText': f"1_{keyword[0]}"  # 提高关键字优先级，使用1_前缀
            }
            for keyword in keywords
        ]
    
    def _get_keyword_continuations(self, last_keyword: str) -> List[Dict]:
        """获取关键字继续建议"""
        continuations = []
        
        if last_keyword == 'GROUP':
            continuations.append({
                'label': 'GROUP BY',
                'kind': 14,  # Keyword
                'detail': 'SQL关键字 - 分组聚合',
                'documentation': 'GROUP BY子句用于将结果集分组',
                'insertText': 'BY',
                'sortText': '0_GROUP_BY'
            })
        elif last_keyword == 'ORDER':
            continuations.append({
                'label': 'ORDER BY',
                'kind': 14,  # Keyword
                'detail': 'SQL关键字 - 结果排序',
                'documentation': 'ORDER BY子句用于对结果集排序',
                'insertText': 'BY',
                'sortText': '0_ORDER_BY'
            })
        elif last_keyword == 'WHERE':
            # WHERE后可能跟的关键字
            where_continuations = [
                ('EXISTS', 'EXISTS(子查询) - 存在性检查'),
                ('NOT', 'NOT - 逻辑非'),
                ('IN', 'IN(值列表) - 包含检查'),
                ('LIKE', 'LIKE 模式 - 模糊匹配'),
                ('BETWEEN', 'BETWEEN 值1 AND 值2 - 范围检查'),
            ]
            for keyword, desc in where_continuations:
                continuations.append({
                    'label': keyword,
                    'kind': 14,
                    'detail': f'SQL关键字 - {desc}',
                    'insertText': keyword,
                    'sortText': f'0_{keyword}'
                })
        elif last_keyword == 'HAVING':
            # HAVING后的关键字与WHERE类似
            having_continuations = [
                ('COUNT', 'COUNT(*) - 计数聚合'),
                ('SUM', 'SUM(字段) - 求和聚合'),
                ('AVG', 'AVG(字段) - 平均值聚合'),
                ('MAX', 'MAX(字段) - 最大值'),
                ('MIN', 'MIN(字段) - 最小值'),
            ]
            for keyword, desc in having_continuations:
                continuations.append({
                    'label': keyword,
                    'kind': 14,
                    'detail': f'SQL函数 - {desc}',
                    'insertText': keyword,
                    'sortText': f'0_{keyword}'
                })
        
        return continuations
    
    def _get_sql_function_suggestions(self) -> List[Dict]:
        """获取SQL函数建议"""
        functions = [
            {'name': 'COUNT', 'detail': 'COUNT(*) - 计数函数'},
            {'name': 'SUM', 'detail': 'SUM(column) - 求和函数'},
            {'name': 'AVG', 'detail': 'AVG(column) - 平均值函数'},
            {'name': 'MAX', 'detail': 'MAX(column) - 最大值函数'},
            {'name': 'MIN', 'detail': 'MIN(column) - 最小值函数'},
            {'name': 'CONCAT', 'detail': 'CONCAT(str1, str2) - 字符串连接'},
            {'name': 'SUBSTR', 'detail': 'SUBSTR(string, start, length) - 字符串截取'},
            {'name': 'UPPER', 'detail': 'UPPER(string) - 转大写'},
            {'name': 'LOWER', 'detail': 'LOWER(string) - 转小写'},
            {'name': 'TRIM', 'detail': 'TRIM(string) - 去除空格'},
            {'name': 'COALESCE', 'detail': 'COALESCE(value1, value2, ...) - 返回第一个非空值'},
            {'name': 'CASE', 'detail': 'CASE WHEN condition THEN result END - 条件表达式'},
        ]
        
        return [
            {
                'label': func['name'],
                'kind': 3,  # Function
                'detail': func['detail'],
                'insertText': func['name'],
                'sortText': f"3_{func['name']}"
            }
            for func in functions
        ]
    
    def provide_hover(self, document_text: str, line: int, character: int) -> Optional[Dict]:
        """提供悬停信息"""
        try:
            tables_cache, _ = self._get_metadata_cache()
            
            # 获取光标位置的单词
            lines = document_text.split('\n')
            if line >= len(lines):
                return None
            
            current_line = lines[line]
            word = self._get_word_at_position(current_line, character)
            
            if not word:
                return None
            
            # 检查是否是表名
            for table_name, table_info in tables_cache.items():
                if word.lower() == table_name.lower() or word.lower() == table_info['name'].lower():
                    columns_info = '\n'.join([
                        f"- {col['name']}: {col['type']} {col['comment']}"
                        for col in table_info['columns'][:10]  # 限制显示数量
                    ])
                    
                    hover_text = f"**表: {table_name}**\n\n"
                    hover_text += f"数据库: {table_info['database']}\n"
                    hover_text += f"说明: {table_info['comment']}\n\n"
                    hover_text += f"**字段信息:**\n{columns_info}"
                    
                    if len(table_info['columns']) > 10:
                        hover_text += f"\n\n... 还有 {len(table_info['columns']) - 10} 个字段"
                    
                    return {
                        'contents': {
                            'kind': 'markdown',
                            'value': hover_text
                        }
                    }
            
            # 检查是否是字段名
            for table_name, table_info in tables_cache.items():
                for col in table_info['columns']:
                    if word.lower() == col['name'].lower():
                        hover_text = f"**字段: {col['name']}**\n\n"
                        hover_text += f"表: {table_name}\n"
                        hover_text += f"类型: {col['type']}\n"
                        hover_text += f"说明: {col['comment']}"
                        
                        return {
                            'contents': {
                                'kind': 'markdown',
                                'value': hover_text
                            }
                        }
            
            return None
            
        except Exception as e:
            logger.error(f"Error in provide_hover: {str(e)}")
            return None
    
    def _get_word_at_position(self, line: str, character: int) -> str:
        """获取指定位置的单词"""
        if character > len(line):
            return ""
        
        # 查找单词边界
        start = character
        end = character
        
        # 向前查找
        while start > 0 and (line[start - 1].isalnum() or line[start - 1] in '_.$'):
            start -= 1
        
        # 向后查找
        while end < len(line) and (line[end].isalnum() or line[end] in '_.$'):
            end += 1
        
        return line[start:end]
    
    def provide_diagnostics(self, document_text: str) -> List[Dict]:
        """提供语法诊断"""
        try:
            diagnostics = []
            lines = document_text.split('\n')
            
            # 基本的语法检查
            for i, line in enumerate(lines):
                line_stripped = line.strip()
                if not line_stripped or line_stripped.startswith('--'):
                    continue
                
                # 检查SQL语法错误
                if self._check_sql_syntax_error(line_stripped):
                    diagnostics.append({
                        'range': {
                            'start': {'line': i, 'character': 0},
                            'end': {'line': i, 'character': len(line)}
                        },
                        'severity': 1,  # Error
                        'message': '可能的SQL语法错误',
                        'source': 'sql-language-server'
                    })
            
            return diagnostics
            
        except Exception as e:
            logger.error(f"Error in provide_diagnostics: {str(e)}")
            return []
    
    def _check_sql_syntax_error(self, line: str) -> bool:
        """检查基本的SQL语法错误"""
        # 简单的语法检查规则
        line_upper = line.upper().strip()
        
        # 检查不匹配的括号
        if line.count('(') != line.count(')'):
            return True
        
        # 检查不匹配的引号
        if line.count("'") % 2 != 0:
            return True
        
        return False
    
    def refresh_metadata(self):
        """刷新元数据缓存"""
        self._refresh_metadata_cache()
        return {"status": "success", "message": "Metadata cache refreshed"}


# 全局LSP服务器实例
sql_language_server = SQLLanguageServer()