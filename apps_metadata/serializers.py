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


class MetadataImportSerializer(serializers.Serializer):
    """元数据导入序列化器"""
    
    IMPORT_MODES = [
        ('merge', '合并模式 - 更新已存在的表'),
        ('skip', '跳过模式 - 跳过已存在的表'),
    ]
    
    FILE_FORMATS = [
        ('json', 'JSON格式'),
        ('csv', 'CSV格式'),
        ('excel', 'Excel格式'),
    ]
    
    file = serializers.FileField(
        help_text="导入的元数据文件"
    )
    file_format = serializers.ChoiceField(
        choices=FILE_FORMATS,
        help_text="文件格式"
    )
    import_mode = serializers.ChoiceField(
        choices=IMPORT_MODES,
        default='merge',
        help_text="导入模式"
    )
    preview_only = serializers.BooleanField(
        default=False,
        help_text="是否仅预览，不实际导入"
    )
    
    def validate_file(self, value):
        """验证文件大小和类型"""
        # 限制文件大小为10MB
        if value.size > 10 * 1024 * 1024:
            raise serializers.ValidationError("文件大小不能超过10MB")
        
        return value
    
    def validate(self, attrs):
        """交叉验证"""
        file_format = attrs.get('file_format')
        file = attrs.get('file')
        
        if file_format == 'json' and not file.name.endswith('.json'):
            raise serializers.ValidationError("JSON格式文件应以.json结尾")
        elif file_format == 'csv' and not file.name.endswith('.csv'):
            raise serializers.ValidationError("CSV格式文件应以.csv结尾")
        elif file_format == 'excel' and not file.name.endswith(('.xlsx', '.xls')):
            raise serializers.ValidationError("Excel格式文件应以.xlsx或.xls结尾")
        
        return attrs


class HiveConnectionTestSerializer(serializers.Serializer):
    """Hive连接测试序列化器"""
    host = serializers.CharField(max_length=255, help_text="Hive服务器地址")
    port = serializers.IntegerField(default=10000, help_text="Hive端口")
    database = serializers.CharField(max_length=255, default='default', help_text="默认数据库")
    auth = serializers.ChoiceField(
        choices=[
            ('NONE', '无认证'),
            ('KERBEROS', 'Kerberos认证'),
            ('LDAP', 'LDAP认证'),
        ],
        default='NONE',
        help_text="认证方式"
    )
    username = serializers.CharField(max_length=255, required=False, help_text="用户名")
    password = serializers.CharField(max_length=255, required=False, help_text="密码")
    kerberos_service_name = serializers.CharField(
        max_length=255, 
        default='hive', 
        required=False,
        help_text="Kerberos服务名"
    )


class SelectiveSyncSerializer(serializers.Serializer):
    """选择性同步序列化器"""
    connection_config = HiveConnectionTestSerializer()
    selected_tables = serializers.ListField(
        child=serializers.DictField(),
        help_text="选中的表列表，格式: [{'database': 'db1', 'table': 'table1'}, ...]"
    )
    sync_mode = serializers.ChoiceField(
        choices=[
            ('add_only', '仅添加新表'),
            ('update_existing', '更新已存在的表'),
            ('full_sync', '完全同步'),
        ],
        default='add_only',
        help_text="同步模式"
    )
    
    def validate_selected_tables(self, value):
        """验证选中的表格式"""
        for table in value:
            if 'database' not in table or 'table' not in table:
                raise serializers.ValidationError("每个表项必须包含 database 和 table 字段")
        return value