#!/usr/bin/env python3
"""
测试Fernet加密密钥生成和验证
"""

import base64
import os
from cryptography.fernet import Fernet

def test_key_generation():
    """测试加密密钥生成"""
    print("=== 测试Fernet密钥生成 ===")
    
    # 方法1: 使用Fernet.generate_key()
    key1 = Fernet.generate_key()
    print(f"Fernet.generate_key(): {key1}")
    print(f"类型: {type(key1)}")
    print(f"长度: {len(key1)} 字节")
    
    # 测试密钥是否有效
    try:
        f = Fernet(key1)
        test_data = "test password"
        encrypted = f.encrypt(test_data.encode())
        decrypted = f.decrypt(encrypted).decode()
        print(f"✅ 加密测试成功: '{test_data}' -> '{decrypted}'")
    except Exception as e:
        print(f"❌ 加密测试失败: {e}")
    
    print()
    
    # 方法2: 使用os.urandom + base64
    key2 = base64.urlsafe_b64encode(os.urandom(32))
    print(f"base64.urlsafe_b64encode(os.urandom(32)): {key2}")
    print(f"类型: {type(key2)}")
    print(f"长度: {len(key2)} 字节")
    
    # 测试密钥是否有效
    try:
        f = Fernet(key2)
        test_data = "test password"
        encrypted = f.encrypt(test_data.encode())
        decrypted = f.decrypt(encrypted).decode()
        print(f"✅ 加密测试成功: '{test_data}' -> '{decrypted}'")
    except Exception as e:
        print(f"❌ 加密测试失败: {e}")
    
    print()
    
    # 测试字符串密钥转换
    key_str = key2.decode()
    print(f"字符串密钥: {key_str}")
    key_bytes = key_str.encode()
    print(f"转换回字节: {key_bytes}")
    
    try:
        f = Fernet(key_bytes)
        test_data = "test password"
        encrypted = f.encrypt(test_data.encode())
        decrypted = f.decrypt(encrypted).decode()
        print(f"✅ 字符串转换测试成功: '{test_data}' -> '{decrypted}'")
    except Exception as e:
        print(f"❌ 字符串转换测试失败: {e}")

if __name__ == "__main__":
    test_key_generation()