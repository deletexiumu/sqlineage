# GitLab 认证故障排除指南

## 问题描述
在使用 HiicHiveIDE 连接内网私有 GitLab 时出现 `HTTP Basic: Access denied` 错误。

## 错误分析
根据错误日志，主要问题是：
1. GitLab Token 认证格式不正确
2. 可能的权限配置问题
3. 内网 SSL 证书验证干扰

## 解决方案

### 1. 创建正确的 GitLab Personal Access Token

#### 步骤：
1. 登录到您的 GitLab（如：http://10.11.1.100:9191）
2. 点击右上角头像 → **User Settings**
3. 左侧菜单选择 **Access Tokens**
4. 创建新的 Personal Access Token：
   - **Token name**: `HiicHiveIDE-Access`
   - **Expiration date**: 根据需要设置（建议至少1年）
   - **Scopes**: 必须勾选以下权限：
     - ✅ `read_repository` （必须）
     - ✅ `read_api` （推荐）
5. 点击 **Create personal access token**
6. **重要**: 立即复制生成的 Token，离开页面后无法再次查看

### 2. 在 HiicHiveIDE 中正确配置

#### 配置步骤：
1. 打开 HiicHiveIDE → Git 管理页面
2. 点击 **添加仓库**
3. 填写配置：
   - **仓库名称**: 任意描述性名称
   - **仓库URL**: `http://10.11.1.100:9191/用户名/仓库名.git`
   - **认证方式**: 选择 `Token认证` ⭐
   - **Token**: 粘贴步骤1中复制的 Personal Access Token
   - **分支**: `main` 或 `master`
   - **SSL验证**: `禁用` ⭐（内网环境建议）

### 3. 自动重试机制

系统已内置多种认证格式自动重试：
1. **格式1**: `token:@host` - Token作为用户名
2. **格式2**: `gitlab-ci-token:token@host` - CI Token格式
3. **格式3**: `username:token@host` - 自定义用户名
4. **格式4**: `oauth2:token@host` - OAuth2格式

当第一种格式失败时，系统会自动尝试其他格式。

### 4. 常见问题解决

#### 问题1: Token 权限不足
**错误**: `access denied` 或 `insufficient permissions`
**解决**: 
- 检查 Token 的 `read_repository` 权限
- 确认 Token 未过期
- 重新创建 Token 并更新配置

#### 问题2: SSL 证书问题
**错误**: `certificate verify failed`
**解决**: 
- 禁用 SSL 验证选项
- 或在服务器上配置正确的 SSL 证书

#### 问题3: 网络连接问题
**错误**: `connection refused` 或 `timeout`
**解决**: 
- 检查 GitLab 服务器是否运行
- 确认端口和URL正确
- 测试网络连通性

#### 问题4: 仓库状态异常
**错误**: `repository corrupted` 或 `HEAD reference`
**解决**: 
- 使用界面上的 **重新克隆** 功能
- 系统会自动清理损坏的本地仓库

### 5. 测试验证

创建配置后：
1. 点击 **同步** 按钮
2. 观察状态变化：
   - 成功：显示 "仓库同步成功"
   - 失败：查看具体错误信息

### 6. 高级故障排除

#### 日志查看
```bash
# Django 应用日志
tail -f logs/django.log

# Git 操作详细日志
# 在代码中已启用详细的Git操作日志
```

#### 手动测试 Token
```bash
# 命令行测试 Token 有效性
curl -H "PRIVATE-TOKEN: your-token-here" \
     http://10.11.1.100:9191/api/v4/projects
```

#### Windows 凭据管理器清理
如果在 Windows 上使用，系统会自动清理可能冲突的凭据。
手动清理方法：
1. 打开 控制面板 → 凭据管理器
2. 删除与 Git 相关的通用凭据
3. 重新尝试同步

### 7. 最佳实践建议

1. **内网环境**:
   - 使用 Token 认证而非用户名密码
   - 禁用 SSL 验证
   - 定期更新 Token

2. **安全考虑**:
   - Token 设置合理的过期时间
   - 只授予必要的权限
   - 定期轮换 Token

3. **团队使用**:
   - 每个用户创建自己的 Token
   - 避免共享 Token
   - 文档化配置步骤

### 8. 如果问题仍然存在

请收集以下信息并联系技术支持：
1. GitLab 版本信息
2. 完整的错误日志
3. Token 权限截图
4. 网络环境描述

---

**更新日期**: 2025-07-12  
**版本**: v1.1  
**适用系统**: HiicHiveIDE with GitLab Private Deployment