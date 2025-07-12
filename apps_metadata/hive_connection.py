import logging
from typing import Dict, List, Any, Optional, Tuple
from django.conf import settings
import json
from .models import HiveTable

logger = logging.getLogger(__name__)


class HiveConnectionManager:
    """Hive连接管理器"""
    
    def __init__(self):
        self.connection = None
        self.cursor = None
        self.is_connected = False
        
    def test_connection(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """测试Hive连接"""
        try:
            # 尝试导入PyHive
            try:
                from pyhive import hive
                from thrift.transport import TSocket
                from thrift.transport import TTransport
                from thrift.protocol import TBinaryProtocol
            except ImportError:
                return {
                    'success': False,
                    'error': 'PyHive库未安装，请先安装pyhive依赖'
                }
            
            # 构建连接参数
            connection_params = {
                'host': config['host'],
                'port': config['port'],
                'database': config.get('database', 'default')
            }
            
            # 添加认证参数
            if config['auth'] == 'KERBEROS':
                connection_params['auth'] = 'KERBEROS'
                connection_params['kerberos_service_name'] = config.get('kerberos_service_name', 'hive')
            elif config['auth'] == 'LDAP':
                connection_params['auth'] = 'LDAP'
                connection_params['username'] = config.get('username', '')
                connection_params['password'] = config.get('password', '')
            elif config['auth'] == 'NONE':
                connection_params['auth'] = 'NONE'
            
            # 测试连接
            conn = hive.Connection(**connection_params)
            cursor = conn.cursor()
            
            # 执行简单查询测试
            cursor.execute("SHOW DATABASES")
            databases = [row[0] for row in cursor.fetchall()]
            
            cursor.close()
            conn.close()
            
            return {
                'success': True,
                'message': f'连接成功，找到 {len(databases)} 个数据库',
                'databases': databases[:10]  # 只返回前10个数据库
            }
            
        except Exception as e:
            logger.error(f"Hive连接测试失败: {str(e)}")
            return {
                'success': False,
                'error': f'连接失败: {str(e)}'
            }
    
    def get_databases(self, config: Dict[str, Any]) -> List[str]:
        """获取数据库列表"""
        try:
            from pyhive import hive
            
            connection_params = self._build_connection_params(config)
            conn = hive.Connection(**connection_params)
            cursor = conn.cursor()
            
            cursor.execute("SHOW DATABASES")
            databases = [row[0] for row in cursor.fetchall()]
            
            cursor.close()
            conn.close()
            
            return databases
            
        except Exception as e:
            logger.error(f"获取数据库列表失败: {str(e)}")
            return []
    
    def get_tables(self, config: Dict[str, Any], database: str) -> List[str]:
        """获取指定数据库的表列表"""
        try:
            from pyhive import hive
            
            connection_params = self._build_connection_params(config)
            connection_params['database'] = database
            
            conn = hive.Connection(**connection_params)
            cursor = conn.cursor()
            
            cursor.execute(f"USE {database}")
            cursor.execute("SHOW TABLES")
            tables = [row[0] for row in cursor.fetchall()]
            
            cursor.close()
            conn.close()
            
            return tables
            
        except Exception as e:
            logger.error(f"获取表列表失败: {str(e)}")
            return []
    
    def get_table_schema(self, config: Dict[str, Any], database: str, table: str) -> List[Dict[str, str]]:
        """获取表结构信息"""
        try:
            from pyhive import hive
            
            connection_params = self._build_connection_params(config)
            connection_params['database'] = database
            
            conn = hive.Connection(**connection_params)
            cursor = conn.cursor()
            
            cursor.execute(f"USE {database}")
            cursor.execute(f"DESCRIBE {table}")
            
            columns = []
            for row in cursor.fetchall():
                # Hive DESCRIBE 返回格式: (column_name, data_type, comment)
                if len(row) >= 2 and row[0] and row[1]:
                    columns.append({
                        'name': row[0].strip(),
                        'type': row[1].strip(),
                        'comment': row[2].strip() if len(row) > 2 and row[2] else ''
                    })
            
            cursor.close()
            conn.close()
            
            return columns
            
        except Exception as e:
            logger.error(f"获取表结构失败: {str(e)}")
            return []
    
    def selective_sync(self, config: Dict[str, Any], selected_tables: List[Dict[str, str]], sync_mode: str = 'add_only') -> Dict[str, Any]:
        """选择性同步元数据"""
        sync_stats = {
            'total': len(selected_tables),
            'success': 0,
            'failed': 0,
            'skipped': 0,
            'errors': []
        }
        
        try:
            for table_info in selected_tables:
                database = table_info['database']
                table_name = table_info['table']
                
                try:
                    # 获取表结构
                    columns = self.get_table_schema(config, database, table_name)
                    
                    if not columns:
                        sync_stats['failed'] += 1
                        sync_stats['errors'].append(f"{database}.{table_name}: 无法获取表结构")
                        continue
                    
                    # 检查表是否已存在
                    existing_table = HiveTable.objects.filter(
                        database=database,
                        name=table_name
                    ).first()
                    
                    if existing_table:
                        if sync_mode == 'add_only':
                            sync_stats['skipped'] += 1
                            continue
                        elif sync_mode in ['update_existing', 'full_sync']:
                            # 更新已存在的表
                            existing_table.columns = columns
                            existing_table.save()
                            sync_stats['success'] += 1
                    else:
                        # 创建新表
                        HiveTable.objects.create(
                            database=database,
                            name=table_name,
                            columns_json=json.dumps(columns)
                        )
                        sync_stats['success'] += 1
                        
                except Exception as e:
                    sync_stats['failed'] += 1
                    sync_stats['errors'].append(f"{database}.{table_name}: {str(e)}")
                    continue
            
            return {
                'success': sync_stats['failed'] == 0,
                'stats': sync_stats
            }
            
        except Exception as e:
            return {
                'success': False,
                'stats': sync_stats,
                'error': str(e)
            }
    
    def get_database_tree(self, config: Dict[str, Any]) -> List[Dict[str, Any]]:
        """获取数据库树形结构"""
        try:
            databases = self.get_databases(config)
            tree_data = []
            
            for db_name in databases:
                tables = self.get_tables(config, db_name)
                
                db_node = {
                    'id': f"db_{db_name}",
                    'label': f"{db_name} ({len(tables)} 张表)",
                    'type': 'database',
                    'database': db_name,
                    'children': []
                }
                
                for table_name in tables:
                    table_node = {
                        'id': f"table_{db_name}_{table_name}",
                        'label': table_name,
                        'type': 'table',
                        'database': db_name,
                        'table': table_name
                    }
                    db_node['children'].append(table_node)
                
                tree_data.append(db_node)
            
            return tree_data
            
        except Exception as e:
            logger.error(f"获取数据库树失败: {str(e)}")
            return []
    
    def _build_connection_params(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """构建连接参数"""
        connection_params = {
            'host': config['host'],
            'port': config['port'],
            'database': config.get('database', 'default')
        }
        
        # 添加认证参数
        if config['auth'] == 'KERBEROS':
            connection_params['auth'] = 'KERBEROS'
            connection_params['kerberos_service_name'] = config.get('kerberos_service_name', 'hive')
        elif config['auth'] == 'LDAP':
            connection_params['auth'] = 'LDAP'
            connection_params['username'] = config.get('username', '')
            connection_params['password'] = config.get('password', '')
        elif config['auth'] == 'NONE':
            connection_params['auth'] = 'NONE'
        
        return connection_params


class MockHiveConnectionManager(HiveConnectionManager):
    """模拟Hive连接管理器（用于测试）"""
    
    def test_connection(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """模拟连接测试"""
        return {
            'success': True,
            'message': '模拟连接成功，找到 3 个数据库',
            'databases': ['default', 'dwd_zbk', 'ads_report']
        }
    
    def get_databases(self, config: Dict[str, Any]) -> List[str]:
        """模拟获取数据库列表"""
        return ['default', 'dwd_zbk', 'ads_report']
    
    def get_tables(self, config: Dict[str, Any], database: str) -> List[str]:
        """模拟获取表列表"""
        if database == 'dwd_zbk':
            return ['user_info', 'order_detail', 'product_info']
        elif database == 'ads_report':
            return ['daily_report', 'monthly_summary']
        else:
            return ['sample_table']
    
    def get_table_schema(self, config: Dict[str, Any], database: str, table: str) -> List[Dict[str, str]]:
        """模拟获取表结构"""
        if table == 'user_info':
            return [
                {'name': 'user_id', 'type': 'bigint', 'comment': '用户ID'},
                {'name': 'user_name', 'type': 'string', 'comment': '用户姓名'},
                {'name': 'age', 'type': 'int', 'comment': '年龄'},
                {'name': 'email', 'type': 'string', 'comment': '邮箱'}
            ]
        else:
            return [
                {'name': 'id', 'type': 'bigint', 'comment': '主键ID'},
                {'name': 'name', 'type': 'string', 'comment': '名称'},
                {'name': 'create_time', 'type': 'timestamp', 'comment': '创建时间'}
            ]


def get_hive_connection_manager() -> HiveConnectionManager:
    """获取Hive连接管理器实例"""
    # 根据配置决定使用真实连接还是模拟连接
    mock_mode = getattr(settings, 'HIVE_MOCK_MODE', True)
    
    if mock_mode:
        return MockHiveConnectionManager()
    else:
        return HiveConnectionManager()