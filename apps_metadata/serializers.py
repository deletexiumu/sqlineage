from rest_framework import serializers
from .models import HiveTable, BusinessMapping


class HiveTableSerializer(serializers.ModelSerializer):
    columns = serializers.JSONField(read_only=True)
    full_name = serializers.CharField(read_only=True)

    class Meta:
        model = HiveTable
        fields = ['id', 'name', 'database', 'columns', 'full_name', 'created_at', 'updated_at']


class BusinessMappingSerializer(serializers.ModelSerializer):
    table_name = serializers.CharField(source='table.full_name', read_only=True)

    class Meta:
        model = BusinessMapping
        fields = ['id', 'table', 'table_name', 'application_name', 'module_name', 'description', 'created_at', 'updated_at']


class AutocompleteSerializer(serializers.Serializer):
    query = serializers.CharField(max_length=100)
    limit = serializers.IntegerField(default=10, min_value=1, max_value=50)