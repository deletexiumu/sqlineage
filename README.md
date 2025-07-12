# HiicHiveIDE - 轻量级数据血缘工具

## 项目概述

HiicHiveIDE 是一个专为内部团队使用的轻量级数据血缘分析工具，支持 5-20 人的小型团队。主要功能包括 Hive SQL 血缘关系分析、元数据管理和代码开发功能。

## 核心特性

- 🔍 **智能血缘分析**: 实时解析 Hive SQL 语句，自动提取表级和字段级血缘关系
- 📊 **元数据管理**: 自动爬取并管理 Hive 表和列信息，提供实时统计数据
- 🔧 **Git 集成**: 连接 GitLab/GitHub，支持代码管理和批量分析
- ✏️ **SQL 编辑器**: 基于 Monaco Editor 的智能 SQL 编辑器，支持自动补全和实时血缘图展示
- 📈 **双层可视化**: 表级血缘图（基于 AntV G6）+ 字段级血缘图（自定义SVG渲染）
- 🎯 **交互式血缘图**: 字段高亮、连线跟踪、鼠标悬停效果、表名智能省略
- 📥 **血缘图导出**: 支持 PNG/SVG 格式下载，便于文档制作和分享
- 📱 **响应式设计**: 完美适配移动端和小屏幕设备
- 👥 **用户管理**: 支持多用户独立配置 Git 仓库

## 技术架构

### 后端架构
- **框架**: Django 5.2.4 + Django REST Framework
- **数据库**: SQLite（适合小团队快速部署）
- **认证**: Django 内置用户系统 + Token 认证
- **血缘解析**: 外部 SQL 解析服务（Gudu SQLFlow）
- **Git 集成**: GitPython
- **Hive 连接**: PyHive + Kerberos 认证

### 前端架构
- **框架**: Vue.js 3 + TypeScript + Composition API
- **UI 组件**: Element Plus（完全响应式）
- **代码编辑器**: Monaco Editor（支持语法高亮和自动补全）
- **图表可视化**: 
  - 表级血缘图: AntV G6
  - 字段级血缘图: 自定义SVG渲染引擎
- **HTTP 客户端**: Axios
- **响应式布局**: 支持移动端和多尺寸屏幕

## 项目结构

```
HiicHiveIDE/
├── hive_ide/                 # Django 主项目配置
├── apps_core/               # 核心应用（认证等）
├── apps_metadata/           # 元数据管理应用
│   ├── models.py           # HiveTable, BusinessMapping 模型
│   ├── hive_crawler.py     # Hive 元数据爬虫
│   ├── views.py            # API 视图（包含自动补全）
│   └── management/commands/ # 管理命令
├── apps_git/               # Git 集成应用
│   ├── models.py          # GitRepo 模型
│   ├── git_service.py     # Git 操作服务
│   └── views.py           # Git API 视图
├── apps_lineage/          # 血缘分析应用
│   ├── models.py         # LineageRelation, ColumnLineage 模型
│   ├── lineage_service.py # 血缘分析服务
│   └── views.py          # 血缘 API 视图
├── frontend/             # Vue.js 前端应用
│   ├── src/components/   # Vue 组件
│   │   ├── LineageGraph.vue      # 血缘可视化主组件
│   │   └── ColumnLineageGraph.vue # 字段级血缘图组件
│   ├── src/views/       # 页面视图（完全响应式）
│   └── src/services/    # API 服务层
└── requirements.txt     # Python 依赖
```

## 安装部署

### 环境要求
- Python 3.8+
- Node.js 16+
- Kerberos 客户端（如需连接 Hive）

### 快速开始

1. **克隆项目**
```bash
git clone <repository-url>
cd HiicHiveIDE
```

2. **安装后端依赖**
```bash
pip install -r requirements.txt
```

3. **数据库初始化**
```bash
python manage.py makemigrations
python manage.py migrate
python manage.py createsuperuser
```

4. **安装前端依赖**
```bash
cd frontend
npm install
```

5. **启动服务**

后端服务：
```bash
python manage.py runserver
```

前端开发服务器：
```bash
cd frontend
npm run dev
```

## 配置说明

### Hive 连接配置
在 `hive_ide/settings.py` 中配置 Hive 连接信息：

```python
HIVE_CONFIG = {
    'host': 'your-hive-host',
    'port': 10000,
    'database': 'default',
    'auth': 'KERBEROS',
    'kerberos_service_name': 'hive',
}
```

### SQL 解析服务配置
配置外部 SQL 解析服务地址：

```python
SQLFLOW_CONFIG = {
    'url': 'http://localhost:9600/sqlflow/datalineage',
    'timeout': 30,
}
```

## 使用指南

### 1. 元数据管理

**爬取 Hive 元数据**
```bash
python manage.py crawl_metadata
```

**API 端点**
- `GET /api/metadata/tables/` - 获取表列表
- `GET /api/metadata/tables/autocomplete/` - 自动补全接口
- `GET /api/metadata/business-mappings/` - 业务映射管理

### 2. Git 集成

**配置 Git 仓库**
1. 登录系统
2. 在前端界面配置 Git 仓库信息
3. 同步仓库代码

**API 端点**
- `POST /api/git/repos/` - 创建 Git 仓库配置
- `POST /api/git/repos/{id}/sync/` - 同步仓库
- `GET /api/git/repos/{id}/files/` - 获取 SQL 文件列表

### 3. 血缘分析

**解析单个 SQL（支持实时字段级血缘）**
```bash
POST /api/lineage/parse-sql/
{
    "sql_text": "INSERT INTO target_table SELECT * FROM source_table",
    "file_path": "optional/file/path.sql"
}
```

返回结果包含：
- 表级血缘关系
- 字段级血缘图数据（column_graph）
- 表统计信息

**批量解析仓库**
```bash
POST /api/lineage/parse-repo/
{
    "repo_id": 1
}
```

**影响分析**
```bash
GET /api/lineage/impact/?table_name=database.table_name
```

**统计数据获取**
```bash
GET /api/metadata/tables/statistics/
```

### 4. SQL 编辑器与可视化

前端提供基于 Monaco Editor 的 SQL 编辑器，支持：
- 语法高亮和错误检查
- 自动补全（表名、列名）
- 实时 SQL 解析和血缘分析
- **集成血缘图展示**: 解析成功后自动显示字段级血缘图
- 双模式可视化：
  - **表级血缘图**: 基于 AntV G6 的节点连线图，支持图形下载
  - **字段级血缘图**: 自定义 SVG 渲染，源表在左，目标表在右
  - **智能表名处理**: 自动省略库名，长表名智能截断，悬停显示完整名称
  - **交互功能**: 鼠标悬停字段高亮相关连线和依赖字段
  - **导出功能**: 支持 PNG 和 SVG 格式下载

### 5. 响应式设计

系统完全支持响应式布局：
- **桌面端** (>1200px): 完整功能展示
- **平板端** (768px-1200px): 优化布局，保持核心功能
- **手机端** (<768px): 移动优先设计，抽屉式导航

## API 文档

### 认证
使用 Token 认证：
```bash
POST /api/auth/login/
{
    "username": "your_username",
    "password": "your_password"
}
```

返回 Token 后，在后续请求头中添加：
```
Authorization: Token your_token_here
```

### 主要 API 端点

#### 元数据 API
```
GET /api/metadata/tables/                    # 表列表
GET /api/metadata/tables/databases/          # 数据库列表  
GET /api/metadata/tables/autocomplete/       # 自动补全
GET /api/metadata/tables/statistics/         # 统计数据（数据库、表、字段、血缘关系数量）
POST /api/metadata/business-mappings/        # 创建业务映射
```

#### Git API
```
GET /api/git/repos/                          # 用户的仓库列表
POST /api/git/repos/                         # 创建仓库配置
POST /api/git/repos/{id}/sync/               # 同步仓库
GET /api/git/repos/{id}/files/               # 获取文件列表
```

#### 血缘 API
```
POST /api/lineage/parse-sql/                 # 解析单个SQL（返回表级+字段级血缘）
POST /api/lineage/parse-repo/{repo_id}/      # 批量解析仓库
GET /api/lineage/impact/                     # 影响分析
GET /api/lineage/graph/                      # 血缘图数据
```

**parse-sql API 返回格式**:
```json
{
  "status": "success",
  "relations_count": 3,
  "relations": [...],
  "column_graph": {
    "tables": [
      {
        "name": "source_table",
        "type": "source",
        "columns": ["col1", "col2"]
      }
    ],
    "relationships": [
      {
        "source_table": "source_table",
        "source_column": "col1",
        "target_table": "target_table", 
        "target_column": "col1",
        "relation_type": "insert"
      }
    ]
  }
}
```

## 开发指南

### 添加新功能

1. **后端开发**
   - 在对应 app 中添加模型、视图、序列化器
   - 更新 URL 配置
   - 编写单元测试

2. **前端开发**
   - 在 `frontend/src/components/` 中添加组件
   - 在 `frontend/src/services/api.ts` 中添加 API 调用
   - 更新路由配置

### 代码风格
- 后端：遵循 Django 和 PEP 8 规范
- 前端：使用 TypeScript，遵循 Vue 3 最佳实践

## 故障排除

### 常见问题

1. **Hive 连接失败**
   - 检查 Kerberos 配置
   - 验证网络连通性
   - 确认用户权限

2. **Git 同步失败**
   - 检查用户名密码
   - 验证仓库地址
   - 确认网络访问

3. **SQL 解析失败**
   - 确认解析服务可用
   - 检查 SQL 语法
   - 验证服务配置

### 日志查看
```bash
# Django 日志
tail -f logs/django.log

# 前端开发日志
npm run dev
```

## 许可证

本项目仅供内部使用，不涉及商业用途。

## 贡献指南

1. Fork 项目
2. 创建功能分支
3. 提交更改
4. 发起 Pull Request

## 联系方式

如有问题，请联系开发团队或提交 Issue。