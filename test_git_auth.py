#!/usr/bin/env python
"""
测试脚本：验证GitLab Token认证修复
"""
import os
import sys
import django

# 设置Django环境
sys.path.append('/Users/cookie/PycharmProjects/PythonProject/HiicHiveIDE')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hive_ide.settings')
django.setup()

from apps_git.models import GitRepo
from apps_git.git_service import GitService
from django.contrib.auth.models import User
import logging

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_auth_formats():
    """测试不同的GitLab Token认证格式"""
    
    print("=== GitLab Token 认证格式测试 ===")
    print("这个脚本会测试不同的Token认证格式")
    print("注意：需要提供有效的GitLab Token才能完成实际测试")
    print()
    
    # 模拟认证URL构建测试
    test_cases = [
        {"auth_type": "token", "password": "test-token-123", "username": ""},
        {"auth_type": "password", "password": "test-password", "username": "testuser"},
    ]
    
    for i, case in enumerate(test_cases):
        print(f"测试用例 {i+1}: {case['auth_type']} 认证")
        
        # 创建临时GitRepo对象（不保存到数据库）
        repo = GitRepo(
            name=f"test-repo-{i+1}",
            repo_url="http://10.11.1.100:9191/test/repo.git",
            username=case['username'],
            auth_type=case['auth_type'],
            branch="main",
            ssl_verify=False
        )
        
        # 手动设置密码（避免加密）
        repo.encrypted_password = case['password']
        
        # 创建GitService并测试URL构建
        service = GitService(repo)
        
        # 测试不同的认证格式
        for format_idx in range(4):
            if hasattr(service, '_auth_format_tried'):
                service._auth_format_tried = format_idx
            else:
                service._auth_format_tried = format_idx
                
            try:
                auth_url = service._get_auth_url()
                # 隐藏实际凭据的URL显示
                display_url = auth_url.replace(case['password'], '***TOKEN***')
                print(f"  格式 {format_idx}: {display_url}")
            except Exception as e:
                print(f"  格式 {format_idx}: 错误 - {e}")
        
        print()
    
    print("=== 建议的GitLab Token使用方法 ===")
    print("1. 在GitLab中创建Personal Access Token:")
    print("   - 权限: read_repository")
    print("   - 有效期: 根据需要设置")
    print()
    print("2. 在HiicHiveIDE中配置:")
    print("   - 认证方式: 选择 'Token认证'")
    print("   - Token: 粘贴刚创建的Personal Access Token")
    print("   - SSL验证: 内网建议关闭")
    print()
    print("3. 系统会自动尝试以下认证格式:")
    print("   - 格式1: token作为用户名")
    print("   - 格式2: gitlab-ci-token:token")
    print("   - 格式3: 自定义用户名:token")
    print("   - 格式4: oauth2:token")
    print()

if __name__ == "__main__":
    test_auth_formats()