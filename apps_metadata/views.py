from rest_framework import viewsets, status
from rest_framework.decorators import action
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
        
        tables = HiveTable.objects.filter(
            Q(name__icontains=query) | Q(database__icontains=query)
        )[:limit]
        
        suggestions = []
        for table in tables:
            suggestions.append({
                'type': 'table',
                'label': table.full_name,
                'value': table.full_name,
                'database': table.database,
                'table': table.name
            })
            
            for column in table.columns:
                if query.lower() in column['name'].lower():
                    suggestions.append({
                        'type': 'column',
                        'label': f"{table.full_name}.{column['name']}",
                        'value': column['name'],
                        'table': table.full_name,
                        'dataType': column.get('type', '')
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
