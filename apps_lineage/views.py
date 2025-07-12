from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from apps_git.models import GitRepo
from .models import LineageRelation, LineageParseJob
from .serializers import (
    LineageRelationSerializer, LineageParseJobSerializer,
    ParseSQLSerializer, ImpactAnalysisSerializer, LineageGraphSerializer
)
from .lineage_service import LineageService


class LineageRelationViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = LineageRelation.objects.all()
    serializer_class = LineageRelationSerializer

    def get_queryset(self):
        queryset = LineageRelation.objects.select_related(
            'source_table', 'target_table'
        ).prefetch_related('column_lineages')
        
        source_table = self.request.query_params.get('source_table', None)
        target_table = self.request.query_params.get('target_table', None)
        
        if source_table:
            queryset = queryset.filter(source_table__full_name=source_table)
        
        if target_table:
            queryset = queryset.filter(target_table__full_name=target_table)
        
        return queryset.order_by('-created_at')

    @action(detail=False, methods=['post'])
    def parse_sql(self, request):
        try:
            serializer = ParseSQLSerializer(data=request.data)
            if not serializer.is_valid():
                return Response({
                    'status': 'error',
                    'message': 'Invalid request data',
                    'errors': serializer.errors
                }, status=status.HTTP_400_BAD_REQUEST)
            
            sql_text = serializer.validated_data['sql_text']
            file_path = serializer.validated_data.get('file_path', '')
            
            lineage_service = LineageService()
            
            # 首先解析SQL获取原始数据
            parsed_data = lineage_service.parse_sql(sql_text)
            if not parsed_data:
                return Response({
                    'status': 'error',
                    'message': 'Failed to parse SQL'
                })
            
            # 提取表级血缘关系并保存到数据库
            relations = lineage_service.extract_lineage_relations(parsed_data, file_path)
            
            # 获取字段级血缘图形化数据
            column_graph = lineage_service.get_column_lineage_graph(parsed_data)
            
            if relations or column_graph['tables']:
                relation_serializer = LineageRelationSerializer(relations, many=True)
                return Response({
                    'status': 'success',
                    'relations_count': len(relations),
                    'relations': relation_serializer.data,
                    'column_graph': column_graph
                })
            else:
                return Response({
                    'status': 'error',
                    'message': 'Failed to parse SQL or no relations found'
                })
                
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"SQL parsing error: {str(e)}", exc_info=True)
            return Response({
                'status': 'error',
                'message': f'Internal server error: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['post'])
    def parse_repo(self, request, repo_id=None):
        if not repo_id:
            repo_id = request.data.get('repo_id')
        
        if not repo_id:
            return Response(
                {'error': 'repo_id is required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            git_repo = get_object_or_404(GitRepo, id=repo_id)
            
            lineage_service = LineageService()
            job = lineage_service.batch_parse_repository(git_repo)
            
            serializer = LineageParseJobSerializer(job)
            return Response({
                'status': 'success',
                'job': serializer.data
            })
            
        except Exception as e:
            return Response(
                {'error': str(e)}, 
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=False, methods=['get'])
    def impact(self, request):
        table_name = request.query_params.get('table_name')
        if not table_name:
            return Response(
                {'error': 'table_name parameter is required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        lineage_service = LineageService()
        impact_data = lineage_service.get_downstream_impact(table_name)
        
        if 'error' in impact_data:
            return Response(impact_data, status=status.HTTP_404_NOT_FOUND)
        
        return Response(impact_data)

    @action(detail=False, methods=['get'])
    def graph(self, request):
        table_name = request.query_params.get('table_name')
        depth = int(request.query_params.get('depth', 2))
        
        if not table_name:
            return Response(
                {'error': 'table_name parameter is required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            nodes = set()
            edges = []
            visited = set()
            
            def build_graph(current_table, current_depth):
                if current_depth > depth or current_table in visited:
                    return
                
                visited.add(current_table)
                nodes.add(current_table)
                
                # Get outgoing relations
                outgoing = LineageRelation.objects.filter(
                    source_table__full_name=current_table
                ).select_related('target_table')
                
                for relation in outgoing:
                    target_name = relation.target_table.full_name
                    edges.append({
                        'source': current_table,
                        'target': target_name,
                        'type': relation.relation_type
                    })
                    build_graph(target_name, current_depth + 1)
                
                # Get incoming relations
                incoming = LineageRelation.objects.filter(
                    target_table__full_name=current_table
                ).select_related('source_table')
                
                for relation in incoming:
                    source_name = relation.source_table.full_name
                    edges.append({
                        'source': source_name,
                        'target': current_table,
                        'type': relation.relation_type
                    })
                    build_graph(source_name, current_depth + 1)
            
            build_graph(table_name, 0)
            
            graph_data = {
                'nodes': [{'id': node, 'label': node} for node in nodes],
                'edges': edges
            }
            
            return Response(graph_data)
            
        except Exception as e:
            return Response(
                {'error': str(e)}, 
                status=status.HTTP_400_BAD_REQUEST
            )


class LineageParseJobViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = LineageParseJob.objects.all()
    serializer_class = LineageParseJobSerializer

    def get_queryset(self):
        return LineageParseJob.objects.select_related('git_repo').order_by('-created_at')
