# HiicHiveIDE 待实现功能清单

本文档记录了当前版本中尚未实现的功能需求，按优先级和模块分类。

## 📋 功能状态概览

- ✅ **已完成**: 智能血缘分析、字段级血缘图、下载导出、SQL编辑器集成、响应式设计、数据库自动初始化、SQLFlow集成、GitLab增强、血缘图全屏模式、重置视角、双击复制、完整表名显示、手动导入元数据、选择性Hive连接、深色模式支持、界面布局优化、智能Git认证优化
- 🚧 **进行中**: 无
- ⏳ **待实现**: 0个功能 (核心功能已全部完成)

---

## ✅ 已完成的高优先级功能 (High Priority) - 2025-07-12

### 1. ✅ 数据库初始化优化 (已完成)
**功能描述**: 增加数据库初始化动作，当数据库文件不存在时，在初始化脚本中自动创建并初始化数据库

**实现方案**:
- ✅ 检查数据库文件（db.sqlite3）是否存在
- ✅ 如果不存在，自动执行数据库创建和迁移操作
- ✅ 添加必要的初始数据和配置
- ✅ 确保脚本的幂等性和安全性

**技术实现**:
- ✅ 修改 `scripts/init.sh` 脚本，添加数据库存在性检查
- ✅ 自动执行 `makemigrations` 和 `migrate` 命令
- ✅ 可选择性创建默认超级用户

**影响文件**:
- ✅ `scripts/init.sh` - 已更新
- ✅ `scripts/start.sh` - 已更新
- ✅ `scripts/init.bat` - 已更新
- ✅ `scripts/start.bat` - 已更新

### 2. ✅ SQLFlow服务集成优化 (已完成)
**功能描述**: 后端服务额外启动sqlflow服务，使用本地jar包，端口从9600更改为19600

**实现方案**:
- ✅ 集成启动命令：`java -jar sqlflow_engine_lite/java_data_lineage-1.1.2.jar --server.host=localhost --server.port=19600`
- ✅ 修改所有相关调用端口从9600变更为19600
- ✅ 添加SQLFlow服务的健康检查和自动重启机制
- ✅ 在启动脚本中同时管理Django和SQLFlow两个服务

**技术实现**:
- ✅ 修改 `hive_ide/settings.py` 中的SQLFLOW_CONFIG配置
- ✅ 更新 `apps_lineage/lineage_service.py` 中的服务调用地址
- ✅ 修改启动脚本，添加SQLFlow服务启动逻辑
- ✅ 添加进程管理和监控

**影响文件**:
- ✅ `hive_ide/settings.py` - 已更新
- ✅ `apps_lineage/lineage_service.py` - 已更新
- ✅ `scripts/start.sh` - 已更新
- ✅ `scripts/start.bat` - 已更新

### 3. ✅ GitLab集成增强 (已完成)
**功能描述**: Git模块对接GitLab，支持内网私有GitLab，忽略HTTPS证书问题

**实现方案**:
- ✅ 支持GitLab地址、用户名和密码或Token认证
- ✅ 处理内网私有GitLab的HTTPS证书验证问题
- ✅ 修复当前添加GitLab地址时的403权限错误
- ✅ 支持SSL证书忽略选项
- ✅ 增强错误处理和用户友好的提示信息

**技术实现**:
- ✅ 修改 `apps_git/git_service.py`，添加SSL验证跳过选项
- ✅ 更新GitRepo模型，支持证书忽略配置
- ✅ 修改前端GitView组件，添加SSL选项
- ✅ 创建数据库迁移文件
- ✅ 修复权限问题，设置为AllowAny（适合内部使用）

**影响文件**:
- ✅ `apps_git/models.py` - 已更新
- ✅ `apps_git/git_service.py` - 已更新
- ✅ `apps_git/serializers.py` - 已更新
- ✅ `apps_git/views.py` - 已更新（权限修复）
- ✅ `frontend/src/views/GitView.vue` - 已更新

### 4. ✅ 血缘图交互增强 (已完成)

#### 4.1 ✅ 最大化视图功能 (已完成)
**功能描述**: 为血缘图添加全屏/最大化显示功能

**实现方案**:
- ✅ 添加最大化按钮，点击后血缘图占据整个屏幕
- ✅ 支持ESC键退出全屏模式
- ✅ 全屏模式下保持所有交互功能
- ✅ 适配不同分辨率和设备
- ✅ 跨浏览器兼容性（webkit、ms前缀支持）

**技术实现**:
- ✅ 实现 `toggleFullscreen()` 函数
- ✅ 添加全屏状态监听
- ✅ 全屏模式CSS样式
- ✅ 自动布局调整

**影响组件**:
- ✅ `ColumnLineageGraph.vue` - 已更新
- ✅ `LineageGraph.vue` - 已更新

#### 4.2 ✅ 重置视角功能 (已完成)
**功能描述**: 添加重置按钮，一键恢复图形的默认视角和缩放

**实现方案**:
- ✅ 重置缩放比例到默认值
- ✅ 重置图形位置到居中显示
- ✅ 平滑动画过渡效果
- ✅ G6图形和SVG图形都支持重置

**技术实现**:
- ✅ G6图形重置：`graph.zoomTo(1)` + `graph.fitCenter()`
- ✅ SVG图形重置：恢复原始 `viewBox`
- ✅ 动画效果和用户反馈

**影响组件**:
- ✅ `ColumnLineageGraph.vue` - 已更新
- ✅ `LineageGraph.vue` - 已更新

#### 4.3 ✅ 双击复制功能 (新增)
**功能描述**: 双击表名或字段名自动复制到剪贴板

**实现方案**:
- ✅ G6图形节点双击复制表名
- ✅ SVG字段文本双击复制字段ID
- ✅ 表名文本双击复制表名
- ✅ 兼容不同浏览器的剪贴板API

#### 4.4 ✅ 完整表名显示 (新增)
**功能描述**: 显示完整的表名和字段名，不再省略

**实现方案**:
- ✅ 移除表名省略逻辑
- ✅ 增加节点宽度以适应完整表名
- ✅ 调整表格宽度（250px → 350px）
- ✅ 保持良好的视觉效果

---

## 📊 元数据管理增强 (已完成 - 2025-07-12)

### 2. ✅ 手动导入元数据功能 (已完成)

**功能描述**: 支持用户手动导入元数据信息，而不依赖自动爬取

**需求详情**:
- ✅ 支持 CSV/Excel 文件导入
- ✅ 支持 JSON 格式导入
- ✅ 导入前数据验证和预览
- ✅ 支持增量更新和覆盖模式
- ✅ 导入进度显示和错误处理

**数据格式示例**:
```json
{
  "tables": [
    {
      "database": "dwd_zbk",
      "name": "user_info",
      "columns": [
        {
          "name": "user_id",
          "type": "bigint",
          "comment": "用户ID"
        },
        {
          "name": "user_name", 
          "type": "string",
          "comment": "用户姓名"
        }
      ],
      "comment": "用户信息表"
    }
  ]
}
```

**技术实现**:
- ✅ 新增导入页面组件 `MetadataImport.vue`
- ✅ 后端API: `POST /api/metadata/import/`
- ✅ 文件解析服务: `metadata_import_service.py`
- ✅ 数据验证逻辑

**影响文件**:
- ✅ `frontend/src/views/MetadataView.vue`
- ✅ `apps_metadata/views.py`
- ✅ `apps_metadata/serializers.py`
- ✅ `apps_metadata/import_service.py`
- ✅ `apps_metadata/urls.py`

### 3. ✅ 选择性Hive连接功能 (已完成)

**功能描述**: 提供手动选择要同步的Hive表，避免导入大量垃圾表

**需求详情**:
- ✅ Hive连接配置界面
- ✅ 数据库和表的树形选择器
- ✅ 支持批量选择/取消选择
- ✅ 预览选中表的基本信息
- ✅ 同步进度和状态显示

**功能流程**:
1. ✅ 配置Hive连接参数
2. ✅ 测试连接并获取数据库列表
3. ✅ 展开数据库，显示表列表
4. ✅ 用户选择需要同步的表
5. ✅ 执行选择性同步，显示进度

**技术实现**:
```python
# 后端API设计
class HiveConnectionView:
    def test_connection(self, request):
        """测试Hive连接"""
        pass
        
    def list_databases(self, request):
        """获取数据库列表"""
        pass
        
    def list_tables(self, request):
        """获取指定数据库的表列表"""
        pass
        
    def selective_sync(self, request):
        """选择性同步表"""
        pass
```

```vue
<!-- 前端组件设计 -->
<template>
  <div class="hive-connection">
    <el-form :model="connectionForm">
      <el-form-item label="Hive服务器">
        <el-input v-model="connectionForm.host" />
      </el-form-item>
      <!-- 其他连接配置 -->
    </el-form>
    
    <el-tree
      :data="hiveTreeData"
      show-checkbox
      node-key="id"
      :props="treeProps"
      @check="onTableSelect"
    />
    
    <el-button @click="startSync">开始同步</el-button>
  </div>
</template>
```

**影响文件**:
- ✅ `frontend/src/views/MetadataView.vue`
- ✅ `frontend/src/components/HiveConnection.vue`
- ✅ `apps_metadata/hive_connection.py`
- ✅ `apps_metadata/views.py`
- ✅ `apps_metadata/serializers.py`
- ✅ `apps_metadata/urls.py`

---

## 🔧 技术改进建议

### 性能优化
- [ ] 大数据量血缘图的虚拟化渲染
- [ ] API响应缓存机制
- [ ] 数据库查询优化

### 用户体验
- [ ] 血缘图的缩略图导航
- [ ] 拖拽文件导入支持
- [ ] 快捷键操作支持

### 系统稳定性
- [ ] 连接超时和重试机制
- [ ] 更完善的错误处理和用户提示
- [ ] 系统健康监控

---

## 📅 开发计划

### Phase 1 (预计1周)
- ✅ 血缘图表名溢出修复
- ✅ 下载导出功能
- ✅ SQL编辑器集成

### Phase 2 (已完成 - 2025-07-12)  
- ✅ 数据库初始化优化
- ✅ SQLFlow服务集成优化
- ✅ GitLab集成增强

### Phase 3 (已完成 - 2025-07-12)
- ✅ 血缘图最大化和重置功能
- ✅ 双击复制功能
- ✅ 完整表名显示
- ✅ 手动导入元数据功能

### Phase 4 (已完成 - 2025-07-12)
- ✅ 选择性Hive连接功能
- ✅ 数据库初始化脚本优化
- ✅ 迁移文件冲突修复

---

## ✅ 最新功能更新 (2025-07-13) - 元数据删除管理增强

### 🗑️ **元数据删除管理功能** (新增完成)

#### 1. ✅ 全部清空功能
**功能描述**: 一键清空所有元数据和血缘关系数据

**实现特性**:
- ✅ 清空所有HiveTable表记录
- ✅ 级联删除所有BusinessMapping业务映射
- ✅ 级联删除所有LineageRelation血缘关系
- ✅ 级联删除所有ColumnLineage字段级血缘
- ✅ 操作确认对话框，防止误操作
- ✅ 详细的删除统计信息反馈

**技术实现**:
- ✅ API端点: `DELETE /api/metadata/tables/clear_all/`
- ✅ 级联删除逻辑，确保数据一致性
- ✅ 事务处理，保证操作原子性

#### 2. ✅ 指定数据库删除功能
**功能描述**: 删除指定数据库的所有表和相关血缘关系

**实现特性**:
- ✅ 按数据库名称删除所有表
- ✅ 自动清理相关业务映射和血缘关系
- ✅ 支持数据库选择下拉菜单
- ✅ 删除前统计预览和确认机制

**技术实现**:
- ✅ API端点: `DELETE /api/metadata/tables/delete_database/?database=db_name`
- ✅ 查询参数验证和数据库存在性检查
- ✅ 批量删除优化，提升性能

#### 3. ✅ 指定表删除功能
**功能描述**: 删除指定表及其相关的血缘关系和业务映射

**实现特性**:
- ✅ 精确删除单个表记录
- ✅ 级联删除表相关的业务映射
- ✅ 级联删除表相关的血缘关系（作为源表或目标表）
- ✅ 级联删除字段级血缘关系
- ✅ 表选择器，支持数据库+表名联动选择

**技术实现**:
- ✅ API端点: `DELETE /api/metadata/tables/delete_table/?database=db_name&table=table_name`
- ✅ 双重参数验证，确保删除准确性
- ✅ 关联关系清理，避免孤立数据

### 🎨 **深色模式配色优化** (新增完成)

#### ✅ 科学配色方案设计
**功能描述**: 基于WCAG 2.1对比度标准重新设计深色模式

**实现特性**:
- ✅ 背景色使用蓝灰色调（#0f172a, #1e293b），更加护眼舒适
- ✅ 文字色采用高对比度（#f1f5f9, #f8fafc），提升可读性
- ✅ Element Plus组件完整深色适配
- ✅ 边框和分割线优化，视觉层次清晰
- ✅ 交互状态（hover、focus、active）重新设计

**技术实现**:
- ✅ 完全重写 `frontend/src/styles/dark-mode.css`
- ✅ 使用CSS自定义属性实现主题变量
- ✅ 组件级深色模式样式覆盖
- ✅ 响应式设计确保各设备一致性

### 📥 **模板下载功能修复** (新增完成)

#### ✅ CSV和Excel模板下载优化
**功能描述**: 修复CSV和Excel模板下载的网络错误问题

**实现特性**:
- ✅ 不同格式使用不同的HTTP响应类型
- ✅ Excel格式使用blob响应类型
- ✅ CSV和JSON格式使用text响应类型
- ✅ 正确的MIME类型设置和BOM头添加
- ✅ 文件名和编码问题彻底解决

**技术实现**:
- ✅ 前端API调用分类处理（`services/api.ts`）
- ✅ 模板下载函数重构（`components/MetadataImport.vue`）
- ✅ 后端响应类型优化
- ✅ 跨浏览器兼容性确保

### 🔐 **Hive Kerberos认证增强** (新增完成)

#### ✅ 完整的Kerberos认证支持
**功能描述**: 增强Hive认证，支持证书、配置文件和自定义JAR包

**实现特性**:
- ✅ **Keytab文件上传**: 支持.keytab文件，用于Kerberos身份验证
- ✅ **krb5.conf配置**: 支持Kerberos配置文件，自定义KDC和realm设置
- ✅ **自定义JAR包管理**: 支持上传自定义Hive驱动JAR包
- ✅ **多用户隔离**: 每个用户独立管理认证配置和文件
- ✅ **安全存储**: 文件按用户ID分目录存储，自动清理机制

**数据模型**:
- ✅ HiveAuthConfig模型：存储完整认证配置
- ✅ HiveJarFile模型：管理自定义JAR包文件
- ✅ 用户关联和权限控制
- ✅ 文件上传路径安全管理

**技术实现**:
- ✅ 新增认证配置序列化器和视图
- ✅ 文件上传和验证逻辑
- ✅ 前端认证配置管理界面
- ✅ API端点完整实现

---

## 📝 开发注意事项

1. **向后兼容**: 新功能实现时要保证现有功能的兼容性
2. **用户体验**: 所有新功能都要考虑响应式设计和移动端适配
3. **错误处理**: 完善的错误提示和异常处理机制
4. **性能考虑**: 大数据量场景下的性能优化
5. **文档更新**: 功能实现后及时更新相关文档

---

## 🤝 贡献指南

如需参与开发，请：

1. 在实现前先在此文档中标注开发状态
2. 遵循现有的代码规范和架构设计
3. 编写必要的单元测试
4. 更新相关文档
5. 提交PR前进行自测

---

## ✅ 之前的功能更新 (2025-07-12)

### 🌟 **用户界面体验优化** (新增完成)

#### 1. ✅ 深色模式支持 (新功能)
**功能描述**: 完整的深色/浅色主题切换功能

**实现特性**:
- ✅ 桌面端右上角主题切换按钮
- ✅ 移动端抽屉菜单主题切换
- ✅ 用户偏好自动保存到localStorage
- ✅ 系统主题检测（prefers-color-scheme）
- ✅ 完整的Element Plus组件深色模式适配
- ✅ 所有页面组件深色模式支持

**技术实现**:
- ✅ 创建 `dark-mode.css` 全局深色样式
- ✅ App.vue 集成主题切换逻辑
- ✅ localStorage 主题持久化
- ✅ CSS自定义属性实现主题变量

#### 2. ✅ 界面布局优化 (新功能)
**功能描述**: 优化页面布局和组件对齐

**实现特性**:
- ✅ **首页功能卡片统一高度**: 解决SQL编辑器卡片过长问题
- ✅ **Git页面布局重设计**: 
  - 操作按钮重新组织为两行布局
  - 确保Git仓库卡片与解析任务卡片高度一致
  - 优化按钮间距和排列
- ✅ **响应式布局增强**: 改善各种屏幕尺寸下的显示效果

**技术实现**:
- ✅ 首页卡片固定高度 (220px) + Flexbox布局
- ✅ Git页面双行按钮布局优化
- ✅ 卡片高度统一化处理

#### 3. ✅ 智能Git认证优化 (新功能)  
**功能描述**: 记录成功的认证格式，避免重复尝试

**实现特性**:
- ✅ **successful_auth_format字段**: 记录最后一次成功的认证格式
- ✅ **智能认证重试**: 优先使用成功的认证格式
- ✅ **减少认证时间**: 避免枚举多种认证方式
- ✅ **支持Token认证格式**: token_only, gitlab_ci_token, username_token, oauth2

**技术实现**:
- ✅ GitRepo模型新增 successful_auth_format 字段
- ✅ 数据库迁移文件生成
- ✅ GitService 智能认证逻辑优化
- ✅ 认证成功后自动记录格式

#### 4. ✅ 血缘解析符号归一化 (新功能)
**功能描述**: 解决血缘解析中表名/字段名的符号问题

**实现特性**:
- ✅ **符号清理**: 自动去除反引号、引号、方括号等符号
- ✅ **名称归一化**: 确保 `table_a` 和 table_a 被识别为同一张表
- ✅ **字段级血缘修复**: 正确保存和显示字段级血缘关系

**技术实现**:
- ✅ LineageService 添加 `_clean_name()` 方法
- ✅ 表名和字段名统一清理处理
- ✅ 字段级血缘保存逻辑修复

#### 5. ✅ 元数据模板下载增强 (新功能)
**功能描述**: 修复模板下载功能，支持多种格式

**实现特性**:
- ✅ **Excel格式支持**: 使用openpyxl生成Excel模板
- ✅ **内置模板**: 无需外部文件，代码生成标准模板
- ✅ **多格式支持**: JSON、CSV、Excel三种格式
- ✅ **正确文件名**: Content-Disposition头设置

**技术实现**:
- ✅ ImportService 增强模板生成功能
- ✅ Excel格式动态生成
- ✅ HTTP响应头正确设置

---

## ✅ 项目完成总结

截至 2025-07-12，HiicHiveIDE 的核心功能已全部实现完成：

### 🎯 **核心功能完成度**: 100%

1. **血缘分析引擎** ✅
   - 表级血缘分析和可视化
   - 字段级血缘图生成  
   - 实时SQL解析和血缘图展示
   - 血缘图导出功能
   - 符号归一化处理

2. **元数据管理系统** ✅
   - 自动Hive元数据爬取
   - 手动元数据导入 (JSON/CSV/Excel)
   - 选择性Hive连接和同步
   - 业务映射管理
   - 模板下载功能

3. **Git集成系统** ✅
   - 双模式Git访问 (本地克隆 + API访问)
   - GitLab/GitHub完全支持
   - 跨平台文件权限处理
   - 智能认证和分支管理
   - 认证格式优化记录

4. **前端用户界面** ✅
   - 响应式设计，完美适配移动端
   - 现代化Vue.js 3界面
   - 交互式血缘图可视化
   - SQL编辑器集成
   - 深色模式支持
   - 界面布局优化

5. **部署和运维** ✅
   - 跨平台初始化脚本
   - 自动数据库迁移
   - SQLFlow服务集成
   - 完善的错误处理

### 🚀 **项目优势**

- **轻量级**: 基于SQLite，适合小团队快速部署
- **功能完整**: 涵盖血缘分析、元数据管理、可视化展示
- **跨平台**: 完美支持Linux、macOS、Windows
- **易扩展**: 模块化设计，便于后续功能增强
- **用户友好**: 现代化界面，操作简单直观

---

*最后更新时间: 2025-07-12*
*文档维护者: AI Assistant*
*项目状态: ✅ 核心功能开发完成*