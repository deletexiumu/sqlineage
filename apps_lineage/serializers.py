from rest_framework import serializers
from .models import LineageRelation, ColumnLineage, LineageParseJob
from apps_metadata.serializers import HiveTableSerializer


class ColumnLineageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ColumnLineage
        fields = ['id', 'source_column', 'target_column', 'transformation']


class LineageRelationSerializer(serializers.ModelSerializer):
    source_table = HiveTableSerializer(read_only=True)
    target_table = HiveTableSerializer(read_only=True)
    column_lineages = ColumnLineageSerializer(many=True, read_only=True)

    class Meta:
        model = LineageRelation
        fields = [
            'id', 'source_table', 'target_table', 'sql_script_path', 
            'relation_type', 'process_id', 'created_at', 'column_lineages'
        ]


class LineageParseJobSerializer(serializers.ModelSerializer):
    git_repo_name = serializers.CharField(source='git_repo.name', read_only=True)
    progress_percentage = serializers.FloatField(read_only=True)

    class Meta:
        model = LineageParseJob
        fields = [
            'id', 'git_repo', 'git_repo_name', 'status', 'total_files', 
            'processed_files', 'failed_files', 'progress_percentage',
            'error_message', 'started_at', 'completed_at', 'created_at'
        ]


class ParseSQLSerializer(serializers.Serializer):
    sql_text = serializers.CharField(max_length=10000)
    file_path = serializers.CharField(max_length=500, required=False, default="", allow_blank=True)


class ImpactAnalysisSerializer(serializers.Serializer):
    table_name = serializers.CharField(max_length=255)


class LineageGraphSerializer(serializers.Serializer):
    nodes = serializers.ListField()
    edges = serializers.ListField()