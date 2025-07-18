from django.db import models
from django.contrib.auth.models import User
from cryptography.fernet import Fernet
from django.conf import settings
import base64
import os


class GitRepo(models.Model):
    AUTH_TYPE_CHOICES = [
        ('password', '用户名密码'),
        ('token', 'Token认证'),
    ]
    
    ACCESS_MODE_CHOICES = [
        ('clone', '本地克隆'),
        ('api', 'API访问'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    name = models.CharField(max_length=255)
    repo_url = models.URLField()
    local_path = models.CharField(max_length=500, blank=True)
    username = models.CharField(max_length=255)
    encrypted_password = models.TextField()
    auth_type = models.CharField(max_length=10, choices=AUTH_TYPE_CHOICES, default='password', help_text='认证方式：密码或Token')
    access_mode = models.CharField(max_length=10, choices=ACCESS_MODE_CHOICES, default='clone', help_text='访问模式：本地克隆或API访问')
    branch = models.CharField(max_length=100, default='main')
    ssl_verify = models.BooleanField(default=True, help_text='是否验证SSL证书，内网私有GitLab建议设为False')
    successful_auth_format = models.CharField(max_length=50, blank=True, help_text='记录最后一次成功的认证格式，用于优化后续认证')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_sync = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ['user', 'repo_url']

    def __str__(self):
        return f"{self.user.username} - {self.name}"

    def _get_encryption_key(self):
        key = getattr(settings, 'GIT_ENCRYPTION_KEY', None)
        if not key:
            # 生成新的密钥
            key = Fernet.generate_key()
            print(f"Generated new encryption key: {key.decode()}")
            print("Add this to your settings.py: GIT_ENCRYPTION_KEY = '{}'".format(key.decode()))
        
        if isinstance(key, str):
            key = key.encode()
        
        # 验证密钥格式
        try:
            Fernet(key)  # 测试密钥是否有效
        except Exception as e:
            # 如果密钥无效，生成新的
            print(f"Invalid encryption key: {e}")
            key = Fernet.generate_key()
            print(f"Generated new encryption key: {key.decode()}")
            
        return key

    def set_password(self, password):
        f = Fernet(self._get_encryption_key())
        self.encrypted_password = f.encrypt(password.encode()).decode()

    def get_password(self):
        if not self.encrypted_password:
            return ""
        try:
            f = Fernet(self._get_encryption_key())
            return f.decrypt(self.encrypted_password.encode()).decode()
        except Exception:
            return ""

    @property
    def repo_local_path(self):
        if not self.local_path:
            import platform
            safe_name = "".join(c for c in self.name if c.isalnum() or c in (' ', '-', '_')).rstrip()
            
            # 跨平台路径处理
            if platform.system() == 'Windows':
                # Windows: 使用用户临时目录
                import tempfile
                base_dir = os.path.join(tempfile.gettempdir(), 'hiic_git_repos')
            else:
                # Unix/Linux/macOS: 使用/tmp目录
                base_dir = '/tmp/hiic_git_repos'
            
            self.local_path = os.path.join(base_dir, str(self.user.id), safe_name)
            self.save()
        return self.local_path
