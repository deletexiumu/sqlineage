from rest_framework import serializers
from .models import HiveTable, BusinessMapping, HiveAuthConfig, HiveJarFile


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


class HiveJarFileSerializer(serializers.ModelSerializer):
    """Hive JAR文件序列化器"""
    file_size = serializers.SerializerMethodField()
    file_url = serializers.SerializerMethodField()
    
    class Meta:
        model = HiveJarFile
        fields = ['id', 'name', 'file', 'file_size', 'file_url', 'description', 'version', 'is_active', 'created_at', 'updated_at']
        read_only_fields = ['created_at', 'updated_at']
    
    def get_file_size(self, obj):
        """获取文件大小（字节）"""
        try:
            return obj.file.size if obj.file else 0
        except:
            return 0
    
    def get_file_url(self, obj):
        """获取文件URL"""
        return obj.file.url if obj.file else None
    
    def validate_file(self, value):
        """验证JAR文件"""
        if not value.name.endswith('.jar'):
            raise serializers.ValidationError("只能上传JAR文件")
        
        # 限制文件大小为50MB
        if value.size > 50 * 1024 * 1024:
            raise serializers.ValidationError("JAR文件大小不能超过50MB")
        
        return value


class HiveAuthConfigSerializer(serializers.ModelSerializer):
    """Hive认证配置序列化器"""
    custom_jar_list = serializers.JSONField(read_only=True)
    keytab_file_url = serializers.SerializerMethodField()
    krb5_conf_file_url = serializers.SerializerMethodField()
    
    class Meta:
        model = HiveAuthConfig
        fields = [
            'id', 'name', 'host', 'port', 'auth_type', 'username', 'password',
            'kerberos_service_name', 'principal', 'keytab_file', 'keytab_file_url',
            'krb5_conf_file', 'krb5_conf_file_url', 'custom_jar_files', 'custom_jar_list',
            'default_database', 'connection_timeout', 'is_active', 'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']
        extra_kwargs = {
            'password': {'write_only': True, 'required': False},
        }
    
    def get_keytab_file_url(self, obj):
        """获取keytab文件URL"""
        return obj.keytab_file.url if obj.keytab_file else None
    
    def get_krb5_conf_file_url(self, obj):
        """获取krb5.conf文件URL"""
        return obj.krb5_conf_file.url if obj.krb5_conf_file else None
    
    def validate_keytab_file(self, value):
        """验证keytab文件"""
        if value and not value.name.endswith('.keytab'):
            raise serializers.ValidationError("Keytab文件应以.keytab结尾")
        
        # 限制文件大小为1MB
        if value and value.size > 1024 * 1024:
            raise serializers.ValidationError("Keytab文件大小不能超过1MB")
        
        return value
    
    def validate_krb5_conf_file(self, value):
        """验证krb5.conf文件"""
        if value and not (value.name.endswith('.conf') or value.name == 'krb5.conf'):
            raise serializers.ValidationError("配置文件应以.conf结尾或命名为krb5.conf")
        
        # 限制文件大小为100KB
        if value and value.size > 100 * 1024:
            raise serializers.ValidationError("配置文件大小不能超过100KB")
        
        return value
    
    def validate(self, attrs):
        """交叉验证"""
        auth_type = attrs.get('auth_type')
        
        if auth_type == 'KERBEROS':
            # Kerberos认证需要principal
            if not attrs.get('principal'):
                raise serializers.ValidationError("Kerberos认证需要提供principal")
        
        elif auth_type == 'LDAP':
            # LDAP认证需要用户名和密码
            if not attrs.get('username') or not attrs.get('password'):
                raise serializers.ValidationError("LDAP认证需要提供用户名和密码")
        
        return attrs
    
    def create(self, validated_data):
        """创建认证配置"""
        # 设置用户
        validated_data['user'] = self.context['request'].user
        return super().create(validated_data)


class EnhancedHiveConnectionTestSerializer(serializers.Serializer):
    """增强的Hive连接测试序列化器（支持认证配置）"""
    # 可以使用已保存的配置或手动输入
    auth_config_id = serializers.IntegerField(required=False, help_text="使用已保存的认证配置ID")
    
    # 手动输入的连接参数
    host = serializers.CharField(max_length=255, required=False, help_text="Hive服务器地址")
    port = serializers.IntegerField(default=10000, required=False, help_text="Hive端口")
    database = serializers.CharField(max_length=255, default='default', required=False, help_text="默认数据库")
    auth_type = serializers.ChoiceField(
        choices=[
            ('NONE', '无认证'),
            ('KERBEROS', 'Kerberos认证'),
            ('LDAP', 'LDAP认证'),
        ],
        default='NONE',
        required=False,
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
    principal = serializers.CharField(max_length=255, required=False, help_text="Kerberos principal")
    
    def validate(self, attrs):
        """验证参数"""
        auth_config_id = attrs.get('auth_config_id')
        host = attrs.get('host')
        
        if not auth_config_id and not host:
            raise serializers.ValidationError("必须提供auth_config_id或手动输入连接参数")
        
        return attrs