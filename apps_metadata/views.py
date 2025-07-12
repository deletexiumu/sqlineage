from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Q, Count
from .models import HiveTable, BusinessMapping
from .serializers import HiveTableSerializer, BusinessMappingSerializer, AutocompleteSerializer


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
