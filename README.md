# SQL血缘关系分析系统

> 🤖 **本项目由AI自动生成** - 这是一个完全由Claude AI和Cursor编程助手协作开发的SQL血缘关系分析工具，展示了AI在复杂软件开发中的能力。

一个专业的SQL血缘关系分析工具，支持Hive SQL解析、字段级血缘分析、表血缘浏览和可视化展示。

## 🌟 功能特性

### ✅ SQL解析与分析
- 🔍 支持Hive SQL语法解析  
- 📝 多语句解析（DDL + ETL组合）
- 🧹 自动过滤注释和解释性文字
- ⚠️ 语法验证和错误提示
- 📊 复杂SQL语句结构分析

### ✅ 血缘关系可视化
- 🔗 字段级别的连线关系展示
- 📋 **表列表浏览器** - 分类展示源表和目标表
- 🔍 **血缘关系过滤** - 支持表名搜索和筛选
- 🎯 **hover高亮显示** - 鼠标悬停自动高亮相关血缘
- 💡 **智能布局算法** - 动态计算节点高度，避免重叠
- 🖱️ **拖拽边界限制** - 防止节点拖出可视区域
- 🎨 多种视觉效果（高亮、发光、透明度）

### ✅ 表血缘交互功能
- 📊 **表统计面板** - 显示源表、目标表和映射数量
- 🔍 **表搜索功能** - 快速定位特定表名
- 📂 **分类浏览** - 按表类型（源表/目标表）分组显示
- 💬 **hover血缘窗口** - 鼠标悬停显示相关血缘关系
- 📋 **详细血缘对话框** - 查看上游依赖、下游影响和字段映射
- ⭐ **相关血缘高亮** - 动态高亮显示相关表和连接线

### ✅ 数据库集成
- 🗄️ 支持从数据库读取表结构
- 📝 DDL语句解析和存储
- 🔌 多数据库类型支持
- 📚 本地DDL历史记录

### ✅ GitLab集成
- 📁 浏览GitLab上的SQL文件
- 🔍 文件搜索和版本管理
- 📦 批量文件分析
- 🔄 文件内容同步

## 🚀 快速开始

### 安装依赖
```bash
npm install
```

### 启动开发服务器
```bash
npm run dev
```

浏览器访问: http://localhost:5173

### 构建生产版本
```bash
npm run build
```

## 📖 使用指南

### 1. 基础SQL分析
```sql
-- 示例SQL：用户行为数据血缘分析
CREATE TABLE IF NOT EXISTS ods.user_events (
    event_id BIGINT COMMENT '事件ID',
    user_id BIGINT COMMENT '用户ID', 
    session_id STRING COMMENT '会话ID',
    event_type STRING COMMENT '事件类型',
    event_time TIMESTAMP COMMENT '事件时间'
) COMMENT '用户行为事件表'
PARTITIONED BY (dt STRING COMMENT '分区日期');

CREATE TABLE IF NOT EXISTS dw.user_behavior_summary (
    user_id BIGINT COMMENT '用户ID',
    activity_date DATE COMMENT '活动日期',
    page_views INT COMMENT '页面浏览数',
    click_count INT COMMENT '点击次数'
) COMMENT '用户行为汇总表'
PARTITIONED BY (dt STRING COMMENT '分区日期');

INSERT OVERWRITE TABLE dw.user_behavior_summary PARTITION(dt='2024-01-01')
SELECT 
    u.user_id AS user_id,
    DATE(u.event_time) AS activity_date,
    COUNT(CASE WHEN u.event_type = 'page_view' THEN 1 END) AS page_views,
    COUNT(CASE WHEN u.event_type = 'click' THEN 1 END) AS click_count
FROM ods.user_events u
WHERE DATE(u.event_time) = '2024-01-01'
    AND u.user_id IS NOT NULL
GROUP BY u.user_id, DATE(u.event_time);
```

### 2. 表血缘浏览功能
1. **分析SQL** - 在左侧编辑器输入SQL后点击"分析血缘"
2. **查看表列表** - 右侧面板自动显示表分类统计
3. **搜索表** - 使用搜索框快速定位特定表
4. **hover查看血缘** - 鼠标悬停在表上查看相关血缘高亮
5. **点击查看详情** - 点击表名打开详细血缘关系对话框

### 3. 血缘关系探索
- 🎯 **上游依赖** - 查看当前表依赖的源表
- 📊 **下游影响** - 查看当前表影响的目标表  
- 🔗 **字段映射** - 查看具体的字段级血缘关系
- 💡 **智能高亮** - 自动高亮相关的表和连接线

## 🎬 系统截图

### 主界面
- 左侧：SQL编辑器和GitLab浏览器
- 中间：血缘关系可视化图形
- 右侧：表列表浏览器和详细信息面板

### 表血缘浏览器
- 📊 表统计卡片（源表/目标表/映射数量）
- 🔍 表搜索和分类切换
- 📋 表详细信息（字段列表、数据库等）
- 💬 血缘关系对话框

访问 http://localhost:5173 查看完整界面

## 🏗️ 技术架构

- **前端框架**: Vue 3 + Composition API
- **UI组件**: Element Plus
- **图形可视化**: D3.js + SVG
- **SQL解析**: node-sql-parser (自定义扩展)
- **构建工具**: Vite
- **代码风格**: ESLint + Prettier

## 📦 核心模块

### 前端组件
- `App.vue` - 主应用入口，布局管理
- `SqlEditor.vue` - SQL编辑器组件  
- `LineageGraph.vue` - 血缘关系可视化图形
- `TableListPanel.vue` - **表列表浏览面板**
- `TableGroup.vue` - **表分组展示组件**
- `ConfigPanel.vue` - 系统配置面板

### 核心工具类
- `sqlParser.js` - SQL解析核心引擎
- `lineageAnalyzer.js` - 血缘关系分析算法
- `databaseManager.js` - 数据库连接管理
- `gitlabIntegration.js` - GitLab API集成

### 关键算法
- **智能布局算法** - 动态计算节点位置，避免碰撞
- **血缘关系计算** - 字段级依赖关系分析
- **拖拽边界控制** - 防止节点超出可视区域
- **高亮渲染优化** - 高性能的视觉反馈系统

## ⚙️ 配置说明

### 数据库配置
```javascript
{
  type: 'hive',
  host: 'localhost', 
  port: '10000',
  username: 'hive',
  password: '',
  database: 'default'
}
```

### GitLab配置
```javascript
{
  baseUrl: 'https://gitlab.example.com',
  accessToken: 'your-access-token',
  projectId: '123'
}
```

### 分析配置
```javascript
{
  fieldLevel: true,        // 是否显示字段级血缘
  autoLayout: true,        // 是否启用智能布局
  dragBoundary: true,      // 是否启用拖拽边界
  highlightRelated: true   // 是否启用相关血缘高亮
}
```

## 📁 项目结构

```
src/
├── components/
│   ├── SqlEditor.vue         # SQL编辑器组件
│   ├── LineageGraph.vue      # 血缘关系图组件
│   ├── TableListPanel.vue    # 🆕 表列表浏览面板
│   ├── TableGroup.vue        # 🆕 表分组展示组件  
│   └── ConfigPanel.vue       # 配置面板组件
├── utils/
│   ├── sqlParser.js          # SQL解析器
│   ├── lineageAnalyzer.js    # 血缘分析器
│   ├── databaseManager.js    # 数据库管理器
│   └── gitlabIntegration.js  # GitLab集成工具
├── App.vue                   # 主应用组件
└── main.js                   # 应用入口
```

## 🤖 AI开发说明

本项目完全由AI驱动开发，展示了以下AI能力：

### 代码生成能力
- ✅ 复杂Vue组件架构设计
- ✅ D3.js图形算法实现  
- ✅ SQL解析器逻辑构建
- ✅ 数据库集成方案设计

### 问题解决能力  
- ✅ 节点碰撞检测和避免算法
- ✅ 拖拽边界控制实现
- ✅ 血缘关系高亮优化
- ✅ 性能优化和内存管理

### 用户体验设计
- ✅ 直观的表血缘浏览界面
- ✅ 流畅的交互动画效果
- ✅ 智能的搜索和过滤功能
- ✅ 友好的错误处理机制

## 🔮 未来规划

- [ ] 支持更多SQL方言（MySQL、PostgreSQL等）
- [ ] 添加血缘关系导出功能
- [ ] 集成数据质量检查
- [ ] 支持实时数据血缘监控
- [ ] 添加血缘影响分析报告

## 🤝 贡献

欢迎提交Issue和Pull Request来改进这个项目。

### 开发约定
- 使用Vue 3 Composition API
- 遵循Element Plus设计规范  
- 保持代码注释完整性
- 确保组件可复用性

## 📄 许可证

MIT License

---

**🤖 AI生成项目声明**: 本项目展示了AI在软件开发领域的强大能力，从需求分析到代码实现，再到文档编写，均由AI自主完成。这为未来AI辅助开发提供了宝贵的实践经验。
