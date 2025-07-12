# HiicHiveIDE 待实现功能清单

本文档记录了当前版本中尚未实现的功能需求，按优先级和模块分类。

## 📋 功能状态概览

- ✅ **已完成**: 智能血缘分析、字段级血缘图、下载导出、SQL编辑器集成、响应式设计、数据库自动初始化、SQLFlow集成、GitLab增强、血缘图全屏模式、重置视角、双击复制、完整表名显示
- 🚧 **进行中**: 无
- ⏳ **待实现**: 0个高优先级功能 (已全部完成)

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

## 📊 元数据管理增强 (Medium Priority)

### 2. 手动导入元数据功能

**功能描述**: 支持用户手动导入元数据信息，而不依赖自动爬取

**需求详情**:
- 支持 CSV/Excel 文件导入
- 支持 JSON 格式导入
- 导入前数据验证和预览
- 支持增量更新和覆盖模式
- 导入进度显示和错误处理

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
- 新增导入页面组件 `MetadataImport.vue`
- 后端API: `POST /api/metadata/import/`
- 文件解析服务: `metadata_import_service.py`
- 数据验证逻辑

**影响文件**:
- `frontend/src/views/MetadataView.vue`
- `apps_metadata/views.py`
- `apps_metadata/serializers.py`

**预估工时**: 3-4天

### 3. 选择性Hive连接功能

**功能描述**: 提供手动选择要同步的Hive表，避免导入大量垃圾表

**需求详情**:
- Hive连接配置界面
- 数据库和表的树形选择器
- 支持批量选择/取消选择
- 预览选中表的基本信息
- 同步进度和状态显示

**功能流程**:
1. 配置Hive连接参数
2. 测试连接并获取数据库列表
3. 展开数据库，显示表列表
4. 用户选择需要同步的表
5. 执行选择性同步，显示进度

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
- `frontend/src/views/MetadataView.vue`
- `frontend/src/components/HiveConnection.vue`
- `apps_metadata/hive_crawler.py`
- `apps_metadata/views.py`

**预估工时**: 4-5天

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
- ⏳ 手动导入元数据功能

### Phase 4 (预计1-2周)
- ⏳ 选择性Hive连接功能
- ⏳ 性能优化和用户体验改进

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

*最后更新时间: 2025-07-12*
*文档维护者: AI Assistant*