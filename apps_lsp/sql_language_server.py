"""
SQL Language Server Protocol 实现
提供SQL语法分析、自动补全、语法检查等功能
"""
import json
import logging
import re
from typing import Dict, List, Optional, Any
from django.conf import settings
from apps_metadata.models import HiveTable

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
            tables = HiveTable.objects.select_related().all()
            self._cached_tables = {}
            self._cached_schemas = set()
            
            for table in tables:
                full_name = f"{table.database}.{table.name}"
                self._cached_tables[full_name] = {
                    'database': table.database,
                    'name': table.name,
                    'full_name': full_name,
                    'comment': table.comment or '',
                    'columns': [
                        {
                            'name': col.name,
                            'type': col.type,
                            'comment': col.comment or ''
                        }
                        for col in table.columns.all()
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
                table_aliases = self._extract_table_aliases(full_text_before)
                
                # 如果有表别名前缀，只显示该表的字段
                if context.get('table_prefix'):
                    target_table = table_aliases.get(context['table_prefix'])
                    if target_table and target_table in tables_cache:
                        table_info = tables_cache[target_table]
                        for col in table_info['columns']:
                            suggestions.append({
                                'label': col['name'],
                                'kind': 5,  # Field (字段)
                                'detail': f"字段: {col['type']} - {col['comment']}",
                                'documentation': f"表: {target_table}\n类型: {col['type']}\n说明: {col['comment']}",
                                'insertText': col['name'],
                                'sortText': f"0_{col['name']}"
                            })
                else:
                    # 显示所有可能的字段，按表分组
                    for table_name, table_info in tables_cache.items():
                        # 检查该表是否在当前SQL中被引用
                        if self._is_table_referenced(full_text_before, table_name):
                            for col in table_info['columns']:
                                suggestions.append({
                                    'label': col['name'],
                                    'kind': 5,  # Field
                                    'detail': f"{table_name}.{col['name']} - {col['type']}",
                                    'documentation': f"表: {table_name}\n字段: {col['name']}\n类型: {col['type']}\n说明: {col['comment']}",
                                    'insertText': col['name'],
                                    'sortText': f"0_{col['name']}"
                                })
                                
                # 添加通用SQL函数建议
                suggestions.extend(self._get_sql_function_suggestions())
                
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
                
                # SQL关键字建议
                suggestions.extend(self._get_sql_keyword_suggestions())
                
                # SQL函数建议
                suggestions.extend(self._get_sql_function_suggestions())
            
            # 限制建议数量，避免性能问题
            return suggestions[:50]
            
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
        
        # 检查是否在表别名.字段的位置
        dot_match = re.search(r'(\w+)\.(\w*)$', text_before_cursor)
        if dot_match:
            return {
                'type': 'column_reference',
                'table_prefix': dot_match.group(1),
                'partial_column': dot_match.group(2)
            }
        
        # 根据最后的关键字确定上下文
        if last_keyword in ['FROM', 'JOIN', 'INNER JOIN', 'LEFT JOIN', 'RIGHT JOIN']:
            return {'type': 'table_reference', 'keyword': last_keyword}
        elif last_keyword in ['SELECT', 'GROUP BY', 'ORDER BY']:
            return {'type': 'column_reference', 'keyword': last_keyword}
        else:
            return {'type': 'general'}
    
    def _extract_table_aliases(self, sql_text: str) -> Dict[str, str]:
        """提取SQL中的表别名映射"""
        aliases = {}
        
        # 匹配 "table_name alias" 或 "table_name AS alias" 模式
        alias_pattern = r'(?:FROM|JOIN)\s+([^\s\(]+)(?:\s+AS)?\s+([a-zA-Z_][a-zA-Z0-9_]*)'
        matches = re.finditer(alias_pattern, sql_text, re.IGNORECASE)
        
        for match in matches:
            table_name = match.group(1).strip()
            alias = match.group(2).strip()
            aliases[alias] = table_name
            
        return aliases
    
    def _is_table_referenced(self, sql_text: str, table_name: str) -> bool:
        """检查表是否在SQL中被引用"""
        # 简单检查表名是否出现在FROM或JOIN子句中
        pattern = r'(?:FROM|JOIN)\s+' + re.escape(table_name) + r'(?:\s|$|,)'
        return bool(re.search(pattern, sql_text, re.IGNORECASE))
    
    def _get_sql_keyword_suggestions(self) -> List[Dict]:
        """获取SQL关键字建议"""
        keywords = [
            'SELECT', 'FROM', 'WHERE', 'GROUP BY', 'ORDER BY', 'HAVING',
            'JOIN', 'INNER JOIN', 'LEFT JOIN', 'RIGHT JOIN', 'FULL JOIN',
            'UNION', 'UNION ALL', 'INSERT', 'UPDATE', 'DELETE',
            'CREATE', 'DROP', 'ALTER', 'AND', 'OR', 'NOT', 'IN', 'EXISTS',
            'CASE', 'WHEN', 'THEN', 'ELSE', 'END', 'DISTINCT', 'AS'
        ]
        
        return [
            {
                'label': keyword,
                'kind': 14,  # Keyword
                'detail': f"SQL关键字: {keyword}",
                'insertText': keyword,
                'sortText': f"2_{keyword}"
            }
            for keyword in keywords
        ]
    
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