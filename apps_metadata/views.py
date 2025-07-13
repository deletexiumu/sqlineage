from rest_framework import viewsets, status
from rest_framework.decorators import action, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.db.models import Q, Count
from django.http import HttpResponse
from .models import HiveTable, BusinessMapping
from .serializers import (
    HiveTableSerializer, BusinessMappingSerializer, AutocompleteSerializer,
    MetadataImportSerializer, HiveConnectionTestSerializer, SelectiveSyncSerializer
)
from .import_service import MetadataImportService
from .hive_connection import get_hive_connection_manager


class HiveTableViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = HiveTable.objects.all()
    serializer_class = HiveTableSerializer
    
    def get_queryset(self):
        queryset = HiveTable.objects.all()
        database = self.request.query_params.get('database', None)
        search = self.request.query_params.get('search', None)
        
        if database:
            queryset = queryset.filter(database=database)
        
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) | Q(database__icontains=search)
            )
        
        return queryset.order_by('database', 'name')

    @action(detail=False, methods=['get'])
    def databases(self, request):
        databases = HiveTable.objects.values_list('database', flat=True).distinct()
        return Response(list(databases))

    @action(detail=False, methods=['get'])
    def autocomplete(self, request):
        serializer = AutocompleteSerializer(data=request.query_params)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        query = serializer.validated_data['query']
        limit = serializer.validated_data['limit']
        
        # 获取额外的上下文参数
        context_type = request.query_params.get('context', 'mixed')  # mixed, table, column
        schema = request.query_params.get('schema', '')  # 指定的schema
        table_alias = request.query_params.get('table_alias', '')  # 表别名
        related_tables = request.query_params.get('related_tables', '')  # 相关表列表，逗号分隔
        
        suggestions = []
        
        # 如果指定了schema，优先在该schema下搜索
        if schema:
            tables = HiveTable.objects.filter(
                database=schema,
                name__icontains=query
            )[:limit]
        else:
            tables = HiveTable.objects.filter(
                Q(name__icontains=query) | Q(database__icontains=query)
            )[:limit]
        
        # 根据上下文类型决定返回内容
        if context_type in ['mixed', 'table']:
            for table in tables:
                table_comment = ''
                if table.columns:
                    # 尝试从第一个字段的comment中获取表注释（如果存在）
                    for col in table.columns:
                        if col.get('comment') and 'table comment' in col.get('comment', '').lower():
                            table_comment = col.get('comment', '')
                            break
                
                suggestions.append({
                    'type': 'table',
                    'label': table.full_name,
                    'value': table.full_name,
                    'database': table.database,
                    'table': table.name,
                    'comment': table_comment,
                    'detail': f"数据库: {table.database}",
                    'documentation': table_comment or f"表 {table.full_name}"
                })
        
        # 处理字段补全
        if context_type in ['mixed', 'column']:
            # 如果有表别名，只搜索该表的字段
            if table_alias and related_tables:
                table_list = [t.strip() for t in related_tables.split(',') if t.strip()]
                for table_name in table_list:
                    try:
                        if '.' in table_name:
                            db, tb = table_name.split('.', 1)
                            table = HiveTable.objects.get(database=db, name=tb)
                        else:
                            table = HiveTable.objects.filter(name=table_name).first()
                        
                        if table:
                            for column in table.columns:
                                if query.lower() in column['name'].lower():
                                    suggestions.append({
                                        'type': 'column',
                                        'label': f"{table_alias}.{column['name']}",
                                        'value': column['name'],
                                        'table': table.full_name,
                                        'dataType': column.get('type', ''),
                                        'comment': column.get('comment', ''),
                                        'detail': f"类型: {column.get('type', '')}",
                                        'documentation': column.get('comment', '') or f"字段 {column['name']} ({column.get('type', '')})"
                                    })
                    except HiveTable.DoesNotExist:
                        continue
            else:
                # 通用字段搜索
                for table in tables:
                    for column in table.columns:
                        if query.lower() in column['name'].lower():
                            suggestions.append({
                                'type': 'column',
                                'label': f"{table.full_name}.{column['name']}",
                                'value': column['name'],
                                'table': table.full_name,
                                'dataType': column.get('type', ''),
                                'comment': column.get('comment', ''),
                                'detail': f"类型: {column.get('type', '')} | 表: {table.full_name}",
                                'documentation': column.get('comment', '') or f"字段 {column['name']} ({column.get('type', '')})"
                            })
        
        return Response(suggestions[:limit])

    @action(detail=False, methods=['get'])
    def statistics(self, request):
        """获取数据库统计信息"""
        from apps_lineage.models import LineageRelation
        
        # 计算数据库数量
        database_count = HiveTable.objects.values('database').distinct().count()
        
        # 计算表数量
        table_count = HiveTable.objects.count()
        
        # 计算字段数量
        column_count = 0
        for table in HiveTable.objects.all():
            column_count += len(table.columns)
        
        # 计算血缘关系数量
        lineage_count = LineageRelation.objects.count()
        
        return Response({
            'database_count': database_count,
            'table_count': table_count,
            'column_count': column_count,
            'lineage_count': lineage_count
        })

    @action(detail=False, methods=['delete'])
    @permission_classes([IsAuthenticated])
    def clear_all(self, request):
        """清空所有元数据和血缘关系"""
        try:
            from apps_lineage.models import LineageRelation, ColumnLineage
            
            # 删除所有血缘关系
            column_lineage_count = ColumnLineage.objects.count()
            lineage_count = LineageRelation.objects.count()
            ColumnLineage.objects.all().delete()
            LineageRelation.objects.all().delete()
            
            # 删除所有业务映射
            business_mapping_count = BusinessMapping.objects.count()
            BusinessMapping.objects.all().delete()
            
            # 删除所有表元数据
            table_count = HiveTable.objects.count()
            HiveTable.objects.all().delete()
            
            return Response({
                'success': True,
                'message': '已清空所有元数据',
                'deleted_counts': {
                    'tables': table_count,
                    'business_mappings': business_mapping_count,
                    'lineage_relations': lineage_count,
                    'column_lineages': column_lineage_count
                }
            })
            
        except Exception as e:
            return Response({
                'success': False,
                'error': f'清空失败: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['delete'])
    @permission_classes([IsAuthenticated])
    def delete_database(self, request):
        """删除指定数据库的所有元数据和血缘关系"""
        database = request.query_params.get('database')
        if not database:
            return Response({
                'success': False,
                'error': '缺少database参数'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            from apps_lineage.models import LineageRelation, ColumnLineage
            
            # 获取该数据库的所有表
            tables = HiveTable.objects.filter(database=database)
            table_names = [f"{table.database}.{table.name}" for table in tables]
            
            if not table_names:
                return Response({
                    'success': False,
                    'error': f'数据库 {database} 不存在或没有表'
                }, status=status.HTTP_404_NOT_FOUND)
            
            # 删除相关的字段级血缘
            column_lineage_count = ColumnLineage.objects.filter(
                Q(source_table__in=table_names) | Q(target_table__in=table_names)
            ).count()
            ColumnLineage.objects.filter(
                Q(source_table__in=table_names) | Q(target_table__in=table_names)
            ).delete()
            
            # 删除相关的表级血缘关系
            lineage_count = LineageRelation.objects.filter(
                Q(source_table__in=table_names) | Q(target_table__in=table_names)
            ).count()
            LineageRelation.objects.filter(
                Q(source_table__in=table_names) | Q(target_table__in=table_names)
            ).delete()
            
            # 删除相关的业务映射
            business_mapping_count = BusinessMapping.objects.filter(
                table__in=tables
            ).count()
            BusinessMapping.objects.filter(table__in=tables).delete()
            
            # 删除表元数据
            table_count = tables.count()
            tables.delete()
            
            return Response({
                'success': True,
                'message': f'已删除数据库 {database} 的所有元数据',
                'deleted_counts': {
                    'tables': table_count,
                    'business_mappings': business_mapping_count,
                    'lineage_relations': lineage_count,
                    'column_lineages': column_lineage_count
                }
            })
            
        except Exception as e:
            return Response({
                'success': False,
                'error': f'删除失败: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['delete'])
    @permission_classes([IsAuthenticated])
    def delete_table(self, request):
        """删除指定表的元数据和血缘关系"""
        database = request.query_params.get('database')
        table_name = request.query_params.get('table')
        
        if not database or not table_name:
            return Response({
                'success': False,
                'error': '缺少database或table参数'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            from apps_lineage.models import LineageRelation, ColumnLineage
            
            # 查找表
            try:
                table = HiveTable.objects.get(database=database, name=table_name)
            except HiveTable.DoesNotExist:
                return Response({
                    'success': False,
                    'error': f'表 {database}.{table_name} 不存在'
                }, status=status.HTTP_404_NOT_FOUND)
            
            full_table_name = f"{database}.{table_name}"
            
            # 删除相关的字段级血缘
            column_lineage_count = ColumnLineage.objects.filter(
                Q(source_table=full_table_name) | Q(target_table=full_table_name)
            ).count()
            ColumnLineage.objects.filter(
                Q(source_table=full_table_name) | Q(target_table=full_table_name)
            ).delete()
            
            # 删除相关的表级血缘关系
            lineage_count = LineageRelation.objects.filter(
                Q(source_table=full_table_name) | Q(target_table=full_table_name)
            ).count()
            LineageRelation.objects.filter(
                Q(source_table=full_table_name) | Q(target_table=full_table_name)
            ).delete()
            
            # 删除相关的业务映射
            business_mapping_count = BusinessMapping.objects.filter(table=table).count()
            BusinessMapping.objects.filter(table=table).delete()
            
            # 删除表元数据
            table.delete()
            
            return Response({
                'success': True,
                'message': f'已删除表 {full_table_name} 的所有元数据',
                'deleted_counts': {
                    'tables': 1,
                    'business_mappings': business_mapping_count,
                    'lineage_relations': lineage_count,
                    'column_lineages': column_lineage_count
                }
            })
            
        except Exception as e:
            return Response({
                'success': False,
                'error': f'删除失败: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class BusinessMappingViewSet(viewsets.ModelViewSet):
    queryset = BusinessMapping.objects.all()
    serializer_class = BusinessMappingSerializer
    
    def get_queryset(self):
        queryset = BusinessMapping.objects.select_related('table')
        application = self.request.query_params.get('application', None)
        module = self.request.query_params.get('module', None)
        
        if application:
            queryset = queryset.filter(application_name=application)
        
        if module:
            queryset = queryset.filter(module_name=module)
        
        return queryset.order_by('application_name', 'module_name')


class MetadataImportViewSet(viewsets.ViewSet):
    """元数据导入视图集"""
    permission_classes = [IsAuthenticated]
    
    @action(detail=False, methods=['post'])
    def import_metadata(self, request):
        """导入元数据"""
        serializer = MetadataImportSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        file = serializer.validated_data['file']
        file_format = serializer.validated_data['file_format']
        import_mode = serializer.validated_data['import_mode']
        preview_only = serializer.validated_data['preview_only']
        
        import_service = MetadataImportService()
        
        try:
            # 读取文件内容
            if file_format == 'excel':
                file_content = file.read()
            else:
                file_content = file.read().decode('utf-8')
            
            if preview_only:
                # 仅预览
                result = import_service.preview_import_data(file_content, file_format)
                return Response({
                    'preview': True,
                    'result': result
                })
            else:
                # 实际导入
                result = import_service.import_metadata(file_content, file_format, import_mode)
                return Response(result)
                
        except Exception as e:
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['get'])
    def get_template(self, request):
        """获取导入模板"""
        format_type = request.query_params.get('format', 'json')
        
        import_service = MetadataImportService()
        template = import_service.get_import_template(format_type)
        
        # 设置正确的文件扩展名
        if format_type == 'excel':
            filename = "metadata_template.xlsx"
        elif format_type == 'csv':
            filename = "metadata_template.csv"
        else:
            filename = "metadata_template.json"
        
        response = HttpResponse(
            template['content'],
            content_type=template['content_type']
        )
        
        # 设置下载头部
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        response['Access-Control-Expose-Headers'] = 'Content-Disposition'
        
        return response


class HiveConnectionViewSet(viewsets.ViewSet):
    """Hive连接管理视图集"""
    permission_classes = [IsAuthenticated]
    
    @action(detail=False, methods=['post'])
    def test_connection(self, request):
        """测试Hive连接"""
        serializer = HiveConnectionTestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        hive_manager = get_hive_connection_manager()
        result = hive_manager.test_connection(serializer.validated_data)
        
        if result['success']:
            return Response(result)
        else:
            return Response(result, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['post'])
    def get_databases(self, request):
        """获取数据库列表"""
        serializer = HiveConnectionTestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        hive_manager = get_hive_connection_manager()
        databases = hive_manager.get_databases(serializer.validated_data)
        
        return Response({
            'databases': databases
        })
    
    @action(detail=False, methods=['post'])
    def get_tables(self, request):
        """获取数据库的表列表"""
        serializer = HiveConnectionTestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        database = request.data.get('database')
        if not database:
            return Response({'error': '缺少database参数'}, status=status.HTTP_400_BAD_REQUEST)
        
        hive_manager = get_hive_connection_manager()
        tables = hive_manager.get_tables(serializer.validated_data, database)
        
        return Response({
            'database': database,
            'tables': tables
        })
    
    @action(detail=False, methods=['post'])
    def get_database_tree(self, request):
        """获取数据库树形结构"""
        serializer = HiveConnectionTestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        hive_manager = get_hive_connection_manager()
        tree_data = hive_manager.get_database_tree(serializer.validated_data)
        
        return Response({
            'tree_data': tree_data
        })
    
    @action(detail=False, methods=['post'])
    def selective_sync(self, request):
        """选择性同步元数据"""
        serializer = SelectiveSyncSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        connection_config = serializer.validated_data['connection_config']
        selected_tables = serializer.validated_data['selected_tables']
        sync_mode = serializer.validated_data['sync_mode']
        
        hive_manager = get_hive_connection_manager()
        result = hive_manager.selective_sync(connection_config, selected_tables, sync_mode)
        
        return Response(result)
