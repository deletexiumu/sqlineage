#!/usr/bin/env python
"""
跨平台测试脚本 - 用于测试Windows和macOS下的Git操作
不需要执行，仅提供测试框架
"""
import os
import sys
import platform
import tempfile
from pathlib import Path


def get_platform_info():
    """获取平台信息"""
    return {
        'system': platform.system(),
        'release': platform.release(),
        'version': platform.version(),
        'machine': platform.machine(),
        'processor': platform.processor(),
        'python_version': platform.python_version(),
        'temp_dir': tempfile.gettempdir()
    }


def test_path_handling():
    """测试路径处理"""
    print("=== 路径处理测试 ===")
    
    # 模拟不同平台的路径
    if platform.system() == 'Windows':
        base_paths = [
            r'C:\temp\hiic_git_repos',
            os.path.join(tempfile.gettempdir(), 'hiic_git_repos'),
            r'C:\Users\Administrator\AppData\Local\Temp\hiic_git_repos'
        ]
    else:
        base_paths = [
            '/tmp/hiic_git_repos',
            '/var/tmp/hiic_git_repos',
            os.path.expanduser('~/tmp/hiic_git_repos')
        ]
    
    for base_path in base_paths:
        test_path = os.path.join(base_path, '1', 'DataWarehouse')
        print(f"测试路径: {test_path}")
        print(f"  - 标准化路径: {os.path.normpath(test_path)}")
        print(f"  - 绝对路径: {os.path.abspath(test_path)}")
        print(f"  - 路径存在: {os.path.exists(test_path)}")
        print()


def test_file_permissions():
    """测试文件权限处理"""
    print("=== 文件权限测试 ===")
    
    # 创建测试目录
    test_dir = os.path.join(tempfile.gettempdir(), 'hiic_test_perms')
    
    try:
        # 创建目录
        os.makedirs(test_dir, exist_ok=True)
        print(f"创建测试目录: {test_dir}")
        
        # 创建测试文件
        test_file = os.path.join(test_dir, 'test.txt')
        with open(test_file, 'w') as f:
            f.write('test content')
        
        # 测试权限设置
        import stat
        
        if platform.system() == 'Windows':
            print("Windows权限测试:")
            try:
                # Windows下的权限设置
                os.chmod(test_dir, stat.S_IRWXU | stat.S_IRWXG | stat.S_IRWXO)
                os.chmod(test_file, stat.S_IRUSR | stat.S_IWUSR | stat.S_IRGRP | stat.S_IROTH)
                print("  - 权限设置成功")
            except PermissionError as e:
                print(f"  - 权限设置失败: {e}")
        else:
            print("Unix/Linux权限测试:")
            try:
                os.chmod(test_dir, 0o755)
                os.chmod(test_file, 0o644)
                print("  - 权限设置成功")
            except PermissionError as e:
                print(f"  - 权限设置失败: {e}")
        
        # 清理测试文件
        import shutil
        if platform.system() == 'Windows':
            def remove_readonly_handler(func, path, exc_info):
                if os.path.exists(path):
                    os.chmod(path, stat.S_IWRITE)
                    func(path)
            shutil.rmtree(test_dir, onerror=remove_readonly_handler)
        else:
            shutil.rmtree(test_dir)
        
        print("  - 清理测试目录成功")
        
    except Exception as e:
        print(f"文件权限测试失败: {e}")


def test_git_auth_formats():
    """测试Git认证格式"""
    print("=== Git认证格式测试 ===")
    
    test_cases = [
        {
            'name': 'GitLab Token 格式1',
            'url': 'http://10.11.1.100:9191/user/repo.git',
            'token': 'glpat-xxxxxxxxxxxxxxxxxxxx',
            'formats': [
                'token:@host',
                'gitlab-ci-token:token@host',
                'oauth2:token@host',
                'git:token@host'
            ]
        },
        {
            'name': 'GitHub Token',
            'url': 'https://github.com/user/repo.git',
            'token': 'ghp_xxxxxxxxxxxxxxxxxxxx',
            'formats': [
                'token:@host',
                'x-access-token:token@host',
                'oauth2:token@host'
            ]
        }
    ]
    
    for case in test_cases:
        print(f"\n{case['name']}:")
        for i, format_desc in enumerate(case['formats']):
            # 模拟URL构建
            from urllib.parse import urlparse, urlunparse
            parsed = urlparse(case['url'])
            
            if format_desc == 'token:@host':
                auth_netloc = f"{case['token']}:@{parsed.netloc}"
            elif format_desc == 'gitlab-ci-token:token@host':
                auth_netloc = f"gitlab-ci-token:{case['token']}@{parsed.netloc}"
            elif format_desc == 'oauth2:token@host':
                auth_netloc = f"oauth2:{case['token']}@{parsed.netloc}"
            elif format_desc == 'git:token@host':
                auth_netloc = f"git:{case['token']}@{parsed.netloc}"
            elif format_desc == 'x-access-token:token@host':
                auth_netloc = f"x-access-token:{case['token']}@{parsed.netloc}"
            else:
                auth_netloc = f"unknown:{case['token']}@{parsed.netloc}"
            
            auth_url = urlunparse((
                parsed.scheme,
                auth_netloc,
                parsed.path,
                parsed.params,
                parsed.query,
                parsed.fragment
            ))
            
            # 隐藏token显示
            display_url = auth_url.replace(case['token'], '***TOKEN***')
            print(f"  格式{i+1}: {display_url}")


def test_api_vs_clone_modes():
    """测试API模式vs克隆模式"""
    print("=== API vs Clone 模式对比 ===")
    
    modes = {
        'clone': {
            'name': '本地克隆模式',
            'pros': [
                '支持完整Git功能',
                '可离线工作',
                '性能较好（本地文件访问）',
                '支持Git历史和分支切换'
            ],
            'cons': [
                '占用本地磁盘空间',
                'Windows权限问题',
                '需要处理Git认证',
                '可能遇到网络连接问题'
            ],
            '适用场景': [
                '开发环境',
                '需要频繁访问文件',
                '需要Git历史信息',
                '稳定的网络环境'
            ]
        },
        'api': {
            'name': 'API访问模式',
            'pros': [
                '无需本地存储',
                '避免文件权限问题',
                '适合Windows环境',
                '实时获取最新内容'
            ],
            'cons': [
                '依赖网络连接',
                'API请求限制',
                '功能受限（只读）',
                '性能可能较慢'
            ],
            '适用场景': [
                'Windows部署环境',
                '只需读取文件内容',
                '磁盘空间有限',
                '权限受限环境'
            ]
        }
    }
    
    for mode_key, mode_info in modes.items():
        print(f"\n{mode_info['name']}:")
        print("  优势:")
        for pro in mode_info['pros']:
            print(f"    + {pro}")
        print("  劣势:")
        for con in mode_info['cons']:
            print(f"    - {con}")
        print("  适用场景:")
        for scenario in mode_info['适用场景']:
            print(f"    • {scenario}")


def test_windows_specific_issues():
    """测试Windows特有问题"""
    if platform.system() != 'Windows':
        print("=== Windows特有问题测试（当前非Windows环境，仅显示测试项） ===")
    else:
        print("=== Windows特有问题测试 ===")
    
    test_items = [
        {
            'name': '长路径支持',
            'description': 'Windows默认路径限制260字符',
            'test': 'os.path.join() 生成超长路径测试',
            'solution': '启用长路径支持或使用较短的路径'
        },
        {
            'name': '文件权限',
            'description': '只读文件删除问题',
            'test': '创建只读文件并尝试删除',
            'solution': '使用onerror回调处理权限问题'
        },
        {
            'name': '凭据管理器',
            'description': 'Windows凭据管理器缓存Git凭据',
            'test': 'cmdkey命令清理凭据',
            'solution': '自动清理凭据或禁用凭据助手'
        },
        {
            'name': '反斜杠路径',
            'description': 'Windows使用反斜杠作为路径分隔符',
            'test': 'os.path.normpath() 路径标准化',
            'solution': '使用os.path.join()或pathlib'
        },
        {
            'name': '临时目录',
            'description': 'Windows临时目录权限和清理',
            'test': 'tempfile.gettempdir() 获取临时目录',
            'solution': '确保临时目录有写权限'
        }
    ]
    
    for item in test_items:
        print(f"\n{item['name']}:")
        print(f"  问题: {item['description']}")
        print(f"  测试: {item['test']}")
        print(f"  解决: {item['solution']}")


def generate_test_report():
    """生成测试报告"""
    print("=== 测试环境报告 ===")
    
    info = get_platform_info()
    print(f"操作系统: {info['system']} {info['release']}")
    print(f"架构: {info['machine']}")
    print(f"Python版本: {info['python_version']}")
    print(f"临时目录: {info['temp_dir']}")
    print()
    
    # 检查关键模块
    modules_to_check = [
        'git',
        'requests', 
        'cryptography',
        'django',
        'pathlib',
        'tempfile',
        'shutil',
        'stat'
    ]
    
    print("模块可用性检查:")
    for module_name in modules_to_check:
        try:
            __import__(module_name)
            print(f"  ✓ {module_name}")
        except ImportError:
            print(f"  ✗ {module_name} (未安装)")
    
    print()
    
    # 生成建议
    print("=== 部署建议 ===")
    if info['system'] == 'Windows':
        print("Windows环境建议:")
        print("  1. 使用API访问模式避免权限问题")
        print("  2. 配置Token认证而非用户名密码")
        print("  3. 禁用SSL验证（内网环境）")
        print("  4. 使用系统临时目录存储数据")
        print("  5. 定期清理Windows凭据管理器")
    else:
        print("Unix/Linux/macOS环境建议:")
        print("  1. 本地克隆模式性能更好")
        print("  2. 注意文件权限设置")
        print("  3. 使用/tmp目录存储临时文件")
        print("  4. 配置适当的Git环境变量")


def main():
    """主测试函数"""
    print("HiicHiveIDE 跨平台兼容性测试")
    print("=" * 50)
    
    # 执行各项测试
    generate_test_report()
    test_path_handling()
    test_file_permissions()
    test_git_auth_formats()
    test_api_vs_clone_modes()
    test_windows_specific_issues()
    
    print("\n=== 测试完成 ===")
    print("注意: 此脚本仅用于测试框架展示，实际部署时请根据具体环境调整配置")


if __name__ == "__main__":
    main()