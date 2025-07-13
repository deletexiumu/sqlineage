from django.db import models
from django.contrib.auth.models import User
import json
import os


class HiveTable(models.Model):
    name = models.CharField(max_length=255)
    database = models.CharField(max_length=255)
    columns_json = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['name', 'database']

    def __str__(self):
        return f"{self.database}.{self.name}"

    @property
    def columns(self):
        try:
            return json.loads(self.columns_json)
        except json.JSONDecodeError:
            return []

    @columns.setter
    def columns(self, value):
        self.columns_json = json.dumps(value)

    @property
    def full_name(self):
        return f"{self.database}.{self.name}"


class BusinessMapping(models.Model):
    table = models.ForeignKey(HiveTable, on_delete=models.CASCADE)
    application_name = models.CharField(max_length=255)
    module_name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['table', 'application_name', 'module_name']

    def __str__(self):
        return f"{self.table.full_name} -> {self.application_name}.{self.module_name}"


def hive_auth_file_upload_path(instance, filename):
    """Hive认证文件上传路径"""
    # 文件保存到 media/hive_auth/user_id/ 目录下
    return f"hive_auth/{instance.user.id}/{filename}"


class HiveAuthConfig(models.Model):
    """Hive认证配置模型"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='hive_auth_configs')
    name = models.CharField(max_length=255, help_text='配置名称')
    host = models.CharField(max_length=255)
    port = models.IntegerField(default=10000)
    auth_type = models.CharField(
        max_length=20,
        choices=[
            ('NONE', '无认证'),
            ('LDAP', 'LDAP认证'),
            ('KERBEROS', 'Kerberos认证'),
        ],
        default='NONE'
    )
    
    # LDAP认证字段
    username = models.CharField(max_length=255, blank=True)
    password = models.CharField(max_length=255, blank=True)  # 应该加密存储
    
    # Kerberos认证字段
    kerberos_service_name = models.CharField(max_length=255, default='hive', blank=True)
    principal = models.CharField(max_length=255, blank=True, help_text='Kerberos principal')
    keytab_file = models.FileField(
        upload_to=hive_auth_file_upload_path, 
        blank=True, 
        null=True,
        help_text='Keytab文件'
    )
    krb5_conf_file = models.FileField(
        upload_to=hive_auth_file_upload_path,
        blank=True,
        null=True,
        help_text='krb5.conf配置文件'
    )
    
    # 自定义JAR包
    custom_jar_files = models.TextField(
        blank=True,
        help_text='自定义JAR包文件路径列表，JSON格式存储'
    )
    
    # 其他配置
    default_database = models.CharField(max_length=255, default='default')
    connection_timeout = models.IntegerField(default=30, help_text='连接超时时间（秒）')
    is_active = models.BooleanField(default=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['user', 'name']
        ordering = ['-updated_at']
    
    def __str__(self):
        return f"{self.user.username} - {self.name} ({self.auth_type})"
    
    @property
    def custom_jar_list(self):
        """获取自定义JAR包列表"""
        try:
            return json.loads(self.custom_jar_files) if self.custom_jar_files else []
        except json.JSONDecodeError:
            return []
    
    @custom_jar_list.setter
    def custom_jar_list(self, value):
        """设置自定义JAR包列表"""
        self.custom_jar_files = json.dumps(value)
    
    def delete(self, *args, **kwargs):
        """删除时同时删除关联的文件"""
        # 删除keytab文件
        if self.keytab_file:
            if os.path.isfile(self.keytab_file.path):
                os.remove(self.keytab_file.path)
        
        # 删除krb5.conf文件
        if self.krb5_conf_file:
            if os.path.isfile(self.krb5_conf_file.path):
                os.remove(self.krb5_conf_file.path)
        
        super().delete(*args, **kwargs)


class HiveJarFile(models.Model):
    """Hive JAR文件管理"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='hive_jar_files')
    name = models.CharField(max_length=255, help_text='JAR文件显示名称')
    file = models.FileField(
        upload_to=hive_auth_file_upload_path,
        help_text='JAR文件'
    )
    description = models.TextField(blank=True, help_text='文件描述')
    version = models.CharField(max_length=50, blank=True, help_text='版本号')
    is_active = models.BooleanField(default=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['user', 'name']
        ordering = ['-updated_at']
    
    def __str__(self):
        return f"{self.user.username} - {self.name}"
    
    def delete(self, *args, **kwargs):
        """删除时同时删除文件"""
        if self.file:
            if os.path.isfile(self.file.path):
                os.remove(self.file.path)
        super().delete(*args, **kwargs)
