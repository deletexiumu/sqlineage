# HiicHiveIDE 待实现功能清单

本文档记录了当前版本中尚未实现的功能需求，按优先级和模块分类。

## 📋 功能状态概览

- ✅ **已完成**: 智能血缘分析、字段级血缘图、下载导出、SQL编辑器集成、响应式设计
- 🚧 **进行中**: 无
- ⏳ **待实现**: 3个高优先级功能

---

## 🎯 高优先级功能 (High Priority)

### 1. 血缘图交互增强

#### 1.1 最大化视图功能
**功能描述**: 为血缘图添加全屏/最大化显示功能

**需求详情**:
- 添加最大化按钮，点击后血缘图占据整个屏幕
- 支持ESC键退出全屏模式
- 全屏模式下保持所有交互功能
- 适配不同分辨率和设备

**技术实现**:
```javascript
// 实现思路
const toggleFullscreen = () => {
  if (isFullscreen.value) {
    document.exitFullscreen()
  } else {
    graphContainer.value.requestFullscreen()
  }
}
```

**影响组件**:
- `ColumnLineageGraph.vue`
- `LineageGraph.vue`

**预估工时**: 1-2天

#### 1.2 重置视角功能  
**功能描述**: 添加重置按钮，一键恢复图形的默认视角和缩放

**需求详情**:
- 重置缩放比例到默认值
- 重置图形位置到居中显示
- 平滑动画过渡效果
- 支持快捷键操作

**技术实现**:
```javascript
// G6图形重置
const resetView = () => {
  graph.value.zoomTo(1, {
    animate: true,
    animateCfg: { duration: 500 }
  })
  graph.value.fitCenter(true)
}

// SVG图形重置
const resetSVGView = () => {
  const svg = graphContainer.value?.querySelector('svg')
  svg.setAttribute('viewBox', `0 0 ${originalWidth} ${originalHeight}`)
}
```

**影响组件**:
- `ColumnLineageGraph.vue` 
- `LineageGraph.vue`

**预估工时**: 0.5-1天

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

### Phase 2 (预计1周)  
- ⏳ 血缘图最大化和重置功能
- ⏳ 手动导入元数据功能

### Phase 3 (预计1-2周)
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