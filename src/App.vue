<template>
  <div class="app-container">
    <el-container>
      <!-- 顶部导航 -->
      <el-header class="app-header">
        <div class="header-left">
          <h1 class="app-title">SQL血缘关系分析工具</h1>
        </div>
        <div class="header-right">
          <el-button-group>
            <el-button @click="toggleConfig" icon="Setting">配置</el-button>
            <el-button @click="exportResults" icon="Download">导出</el-button>
            <el-button @click="clearAll" icon="Delete">清空</el-button>
          </el-button-group>
        </div>
      </el-header>

      <el-container>
        <!-- 左侧面板 -->
        <el-aside class="left-panel">
          <el-tabs v-model="leftActiveTab" type="border-card" class="left-tabs">
            <!-- SQL编辑器 -->
            <el-tab-pane label="SQL编辑" name="editor">
              <div class="tab-panel">
                <div class="panel-toolbar">
                  <el-button @click="analyzeSQL" type="primary" :loading="analyzing">
                    <el-icon><Search /></el-icon>
                    分析血缘
                  </el-button>
                  <el-button @click="loadFromGitlab" icon="Folder">GitLab</el-button>
                </div>
                <SqlEditor 
                  v-model="sqlContent"
                  @change="onSqlChange"
                  @execute="onSqlExecute"
                  class="sql-editor"
                />
              </div>
            </el-tab-pane>

            <!-- GitLab浏览器 -->
            <el-tab-pane label="GitLab" name="gitlab">
              <div class="tab-panel">
                <div class="gitlab-browser">
                  <el-input 
                    v-model="gitlabSearch" 
                    placeholder="搜索SQL文件..."
                    prefix-icon="Search"
                    @input="searchGitlabFiles"
                  />
                  <div class="file-list">
                    <el-tree 
                      :data="gitlabFiles"
                      :props="treeProps"
                      @node-click="loadGitlabFile"
                      class="gitlab-tree"
                    />
                  </div>
                </div>
              </div>
            </el-tab-pane>

            <!-- 配置面板 -->
            <el-tab-pane label="配置" name="config" v-if="showConfig">
              <ConfigPanel @configChange="onConfigChange" />
            </el-tab-pane>
          </el-tabs>
        </el-aside>

        <!-- 主内容区域 -->
        <el-main class="main-content">
          <!-- 分析结果显示 -->
          <div v-if="lineageData && Object.keys(lineageData).length > 0" class="lineage-container">
            <!-- 结果摘要 -->
            <div class="result-summary">
              <el-row :gutter="20">
                <el-col :span="6">
                  <el-statistic title="表数量" :value="lineageData.summary?.totalTables || 0" />
                </el-col>
                <el-col :span="6">
                  <el-statistic title="关系数量" :value="lineageData.summary?.totalRelationships || 0" />
                </el-col>
                <el-col :span="6">
                  <el-statistic title="字段映射" :value="lineageData.summary?.totalFieldMappings || 0" />
                </el-col>
                <el-col :span="6">
                  <el-statistic title="SQL语句" :value="sqlStatementCount" />
                </el-col>
              </el-row>
            </div>

            <!-- 血缘关系图 -->
            <div class="graph-container">
              <LineageGraph 
                :lineageData="lineageData"
                :showFieldLevel="showFieldLevel"
                :highlightedTables="highlightedTables"
                @nodeClick="onNodeClick"
                @nodeHover="onNodeHover"
              />
            </div>
          </div>

          <!-- 空状态 -->
          <div v-else class="empty-state">
            <el-empty description="请输入SQL语句并点击分析血缘">
              <el-button @click="loadSampleSQL" type="primary">加载示例</el-button>
            </el-empty>
          </div>
        </el-main>

        <!-- 右侧面板 -->
        <el-aside class="right-panel" v-if="showRightPanel">
          <el-tabs v-model="rightActiveTab" type="border-card" class="right-tabs">
            <!-- 表血缘浏览 -->
            <el-tab-pane label="表列表" name="tables" v-if="lineageData && Object.keys(lineageData).length > 0">
              <TableListPanel 
                :lineageData="lineageData"
                @table-hover="onTableHover"
                @table-click="onTableClick"
                @table-leave="onTableLeave"
                @highlight-lineage="onHighlightLineage"
              />
            </el-tab-pane>

            <!-- 节点详情 -->
            <el-tab-pane label="详细信息" name="details" v-if="selectedNode">
              <div class="node-details">
                <h4>{{ selectedNode.name }}</h4>
                <el-descriptions :column="1" border>
                  <el-descriptions-item label="类型">{{ selectedNode.type }}</el-descriptions-item>
                  <el-descriptions-item label="数据库">{{ selectedNode.database || 'default' }}</el-descriptions-item>
                  <el-descriptions-item v-if="selectedNode.columns" label="字段数量">
                    {{ selectedNode.columns.length }}
                  </el-descriptions-item>
                </el-descriptions>
                
                <div v-if="selectedNode.columns" class="columns-section">
                  <h5>字段列表</h5>
                  <el-table :data="selectedNode.columns" size="small" max-height="300">
                    <el-table-column prop="name" label="字段名" width="120"></el-table-column>
                    <el-table-column prop="type" label="类型"></el-table-column>
                  </el-table>
                </div>
              </div>

              <!-- 表结构信息 -->
              <div v-if="tableSchema" class="schema-section">
                <h4>表结构</h4>
                <el-table :data="tableSchema.columns" size="small" max-height="400">
                  <el-table-column prop="name" label="字段名"></el-table-column>
                  <el-table-column prop="type" label="类型"></el-table-column>
                  <el-table-column prop="comment" label="注释"></el-table-column>
                </el-table>
              </div>
            </el-tab-pane>
          </el-tabs>
        </el-aside>
      </el-container>
    </el-container>

    <!-- 加载遮罩 -->
    <el-loading v-if="globalLoading" :text="loadingText" element-loading-background="rgba(0, 0, 0, 0.8)" />
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue';
import { ElMessage, ElLoading } from 'element-plus';
import { Search } from '@element-plus/icons-vue';

// 组件导入
import SqlEditor from './components/SqlEditor.vue';
import LineageGraph from './components/LineageGraph.vue';
import ConfigPanel from './components/ConfigPanel.vue';
import TableListPanel from './components/TableListPanel.vue';

// 工具类导入
import HiveSqlParser from './utils/sqlParser.js';
import LineageAnalyzer from './utils/lineageAnalyzer.js';
import DatabaseManager from './utils/databaseManager.js';
import GitlabIntegration from './utils/gitlabIntegration.js';

// 响应式数据
const leftActiveTab = ref('editor');
const rightActiveTab = ref('tables');
const showConfig = ref(false);
const showRightPanel = ref(false);
const analyzing = ref(false);
const globalLoading = ref(false);
const loadingText = ref('');

const sqlContent = ref('');
const lineageData = ref({});
const selectedNode = ref(null);
const tableSchema = ref(null);
const showFieldLevel = ref(true);
const highlightedTables = ref(new Set());

const gitlabSearch = ref('');
const gitlabFiles = ref([]);

// 工具实例
const sqlParser = new HiveSqlParser();
const lineageAnalyzer = new LineageAnalyzer();
const databaseManager = new DatabaseManager();
const gitlabIntegration = new GitlabIntegration();

// 计算属性
const sqlStatementCount = computed(() => {
  if (!sqlContent.value) return 0;
  return sqlParser.splitSqlStatements(sqlContent.value).length;
});

// GitLab树形结构配置
const treeProps = {
  children: 'children',
  label: 'name'
};

onMounted(() => {
  initializeApp();
});

function initializeApp() {
  // 加载保存的配置
  loadSavedConfigs();
  
  // 初始化DDL历史
  databaseManager.loadDDLFromLocalStorage();
}

function loadSavedConfigs() {
  // 加载数据库配置
  const dbConfig = localStorage.getItem('sqllineage_db_config');
  if (dbConfig) {
    const config = JSON.parse(dbConfig);
    databaseManager.addConnection('default', config);
  }
  
  // 加载GitLab配置
  const gitlabConfig = localStorage.getItem('sqllineage_gitlab_config');
  if (gitlabConfig) {
    const config = JSON.parse(gitlabConfig);
    gitlabIntegration.configure(config);
  }
  
  // 加载分析配置
  const analysisConfig = localStorage.getItem('sqllineage_analysis_config');
  if (analysisConfig) {
    const config = JSON.parse(analysisConfig);
    showFieldLevel.value = config.fieldLevel;
  }
}

async function analyzeSQL() {
  if (!sqlContent.value.trim()) {
    ElMessage.warning('请输入SQL语句');
    return;
  }
  
  analyzing.value = true;
  try {
    // 获取表结构
    await loadTableSchemas();
    
    // 分析血缘关系
    const result = lineageAnalyzer.analyzeLineage(sqlContent.value);
    lineageData.value = result;
    
    // 自动显示右侧面板和表列表
    showRightPanel.value = true;
    rightActiveTab.value = 'tables';
    
    ElMessage.success('血缘分析完成');
  } catch (error) {
    ElMessage.error('分析失败: ' + error.message);
    console.error('Analysis error:', error);
  } finally {
    analyzing.value = false;
  }
}

async function loadTableSchemas() {
  // 如果有数据库连接，尝试加载表结构
  const connections = databaseManager.listConnections();
  if (connections.length === 0) return;
  
  const defaultConnection = connections[0];
  
  try {
    // 解析SQL获取涉及的表
    const statements = sqlParser.parseMultipleStatements(sqlContent.value);
    const tableNames = new Set();
    
    statements.forEach(stmt => {
      if (stmt.success) {
        const tables = sqlParser.extractTablesFromAst(stmt.ast);
        tables.forEach(table => tableNames.add(table));
      }
    });
    
    // 批量获取表结构
    const schemas = await databaseManager.batchGetTableSchemas(
      defaultConnection.id, 
      Array.from(tableNames)
    );
    
    // 设置到血缘分析器
    lineageAnalyzer.setTableSchemas(schemas);
  } catch (error) {
    console.warn('Failed to load table schemas:', error);
  }
}

function onSqlChange(newContent) {
  // SQL内容变化时的处理
  if (lineageData.value && Object.keys(lineageData.value).length > 0) {
    // 如果有分析结果，提示重新分析
    ElMessage.info('SQL内容已修改，请重新分析');
  }
}

function onSqlExecute(statement) {
  // 执行单个SQL语句
  ElMessage.info('执行语句: ' + statement.substring(0, 50) + '...');
}

function onNodeClick(node) {
  selectedNode.value = node;
  showRightPanel.value = true;
  rightActiveTab.value = 'details';
  loadNodeDetails(node);
}

function onNodeHover(node) {
  // 节点悬停时的处理
}

// 表列表面板的交互处理
function onTableHover(table) {
  // 高亮显示相关表
  const relatedTables = findRelatedTables(table);
  highlightedTables.value = new Set([table.name, ...relatedTables]);
}

function onTableClick(table) {
  // 点击表时切换到详情tab并显示表信息
  selectedNode.value = {
    name: table.name,
    type: table.type,
    database: table.database,
    columns: table.columns,
    nodeType: 'table'
  };
  rightActiveTab.value = 'details';
  loadNodeDetails(selectedNode.value);
}

function onTableLeave() {
  // 清除高亮
  highlightedTables.value = new Set();
}

function onHighlightLineage(data) {
  if (data) {
    highlightedTables.value = new Set(data.relatedTables);
  } else {
    highlightedTables.value = new Set();
  }
}

function findRelatedTables(table) {
  const relatedTables = [];
  const relationships = lineageData.value.relationships || [];
  const fieldMappings = lineageData.value.fieldMappings || [];
  
  // 从表关系中查找相关表
  relationships.forEach(rel => {
    if (rel.source === table.name) {
      relatedTables.push(rel.target);
    }
    if (rel.target === table.name) {
      relatedTables.push(rel.source);
    }
  });
  
  // 从字段映射中查找相关表
  fieldMappings.forEach(mapping => {
    if (mapping.sourceTable === table.name) {
      relatedTables.push(mapping.targetTable);
    }
    if (mapping.targetTable === table.name) {
      relatedTables.push(mapping.sourceTable);
    }
  });
  
  return [...new Set(relatedTables)];
}

async function loadNodeDetails(node) {
  if (node.nodeType === 'table') {
    try {
      const connections = databaseManager.listConnections();
      if (connections.length > 0) {
        const schema = await databaseManager.getTableSchema(
          connections[0].id, 
          node.name, 
          node.database
        );
        tableSchema.value = schema;
      }
    } catch (error) {
      console.warn('Failed to load table details:', error);
    }
  }
}

function onConfigChange(event) {
  const { type, config } = event;
  
  if (type === 'database') {
    databaseManager.addConnection('default', config);
  } else if (type === 'gitlab') {
    gitlabIntegration.configure(config);
    loadGitlabFiles();
  } else if (type === 'analysis') {
    showFieldLevel.value = config.fieldLevel;
  }
}

async function loadFromGitlab() {
  leftActiveTab.value = 'gitlab';
  await loadGitlabFiles();
}

async function loadGitlabFiles() {
  try {
    globalLoading.value = true;
    loadingText.value = '加载GitLab文件...';
    
    const files = await gitlabIntegration.searchSqlFiles();
    gitlabFiles.value = buildFileTree(files);
  } catch (error) {
    ElMessage.error('加载GitLab文件失败: ' + error.message);
  } finally {
    globalLoading.value = false;
  }
}

function buildFileTree(files) {
  const tree = {};
  
  files.forEach(file => {
    const pathParts = file.path.split('/');
    let current = tree;
    
    pathParts.forEach((part, index) => {
      if (!current[part]) {
        current[part] = {
          name: part,
          path: pathParts.slice(0, index + 1).join('/'),
          type: index === pathParts.length - 1 ? 'file' : 'folder',
          children: {}
        };
      }
      current = current[part].children;
    });
  });
  
  return Object.values(tree).map(convertTreeNode);
}

function convertTreeNode(node) {
  const result = {
    name: node.name,
    path: node.path,
    type: node.type
  };
  
  if (Object.keys(node.children).length > 0) {
    result.children = Object.values(node.children).map(convertTreeNode);
  }
  
  return result;
}

async function loadGitlabFile(data) {
  if (data.type !== 'file') return;
  
  try {
    globalLoading.value = true;
    loadingText.value = '加载文件内容...';
    
    const fileContent = await gitlabIntegration.getFileContent(data.path);
    sqlContent.value = fileContent.decodedContent;
    leftActiveTab.value = 'editor';
    
    ElMessage.success('文件加载成功');
  } catch (error) {
    ElMessage.error('加载文件失败: ' + error.message);
  } finally {
    globalLoading.value = false;
  }
}

function searchGitlabFiles() {
  // 实现GitLab文件搜索
  // 这里可以添加搜索逻辑
}

function loadSampleSQL() {
  sqlContent.value = `-- 示例：用户行为数据血缘分析
-- 源表定义
CREATE TABLE IF NOT EXISTS ods.user_events (
    event_id BIGINT COMMENT '事件ID',
    user_id BIGINT COMMENT '用户ID', 
    session_id STRING COMMENT '会话ID',
    event_type STRING COMMENT '事件类型',
    event_time TIMESTAMP COMMENT '事件时间',
    page_url STRING COMMENT '页面URL',
    device_type STRING COMMENT '设备类型'
) COMMENT '用户行为事件表'
PARTITIONED BY (dt STRING COMMENT '分区日期');

CREATE TABLE IF NOT EXISTS dim.user_sessions (
    session_id STRING COMMENT '会话ID',
    user_id BIGINT COMMENT '用户ID',
    session_duration INT COMMENT '会话时长毫秒',
    start_time TIMESTAMP COMMENT '开始时间',
    end_time TIMESTAMP COMMENT '结束时间',
    ip_address STRING COMMENT 'IP地址'
) COMMENT '用户会话维度表';

-- 目标表定义  
CREATE TABLE IF NOT EXISTS dw.user_behavior_summary (
    user_id BIGINT COMMENT '用户ID',
    activity_date DATE COMMENT '活动日期',
    page_views INT COMMENT '页面浏览数',
    click_count INT COMMENT '点击次数', 
    session_duration DOUBLE COMMENT '会话时长（秒）',
    unique_pages INT COMMENT '唯一页面数',
    device_type STRING COMMENT '主要设备类型'
) COMMENT '用户行为汇总表'
PARTITIONED BY (dt STRING COMMENT '分区日期');

-- ETL数据处理
INSERT OVERWRITE TABLE dw.user_behavior_summary PARTITION(dt='2024-01-01')
SELECT 
    u.user_id AS user_id,
    DATE(u.event_time) AS activity_date,
    COUNT(CASE WHEN u.event_type = 'page_view' THEN 1 END) AS page_views,
    COUNT(CASE WHEN u.event_type = 'click' THEN 1 END) AS click_count,
    AVG(s.session_duration) / 1000.0 AS session_duration,
    COUNT(DISTINCT u.page_url) AS unique_pages,
    FIRST_VALUE(u.device_type) AS device_type
FROM ods.user_events u
LEFT JOIN dim.user_sessions s ON u.session_id = s.session_id  
WHERE DATE(u.event_time) = '2024-01-01'
    AND u.user_id IS NOT NULL
GROUP BY u.user_id, DATE(u.event_time);`;
}

function exportResults() {
  if (!lineageData.value || Object.keys(lineageData.value).length === 0) {
    ElMessage.warning('没有可导出的分析结果');
    return;
  }
  
  const dataStr = JSON.stringify(lineageData.value, null, 2);
  const dataBlob = new Blob([dataStr], { type: 'application/json' });
  const url = URL.createObjectURL(dataBlob);
  
  const link = document.createElement('a');
  link.href = url;
  link.download = 'lineage-analysis.json';
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  URL.revokeObjectURL(url);
  
  ElMessage.success('分析结果已导出');
}

function toggleConfig() {
  showConfig.value = !showConfig.value;
  if (showConfig.value) {
    // 当显示配置时，自动切换到配置tab
    leftActiveTab.value = 'config';
  } else {
    // 当隐藏配置时，切换回编辑器tab
    leftActiveTab.value = 'editor';
  }
}

function clearAll() {
  sqlContent.value = '';
  lineageData.value = {};
  selectedNode.value = null;
  tableSchema.value = null;
  showRightPanel.value = false;
  highlightedTables.value = new Set();
  rightActiveTab.value = 'tables';
  
  ElMessage.success('已清空所有内容');
}
</script>

<style scoped>
.app-container {
  height: 100vh;
  width: 100vw;
  background: #f5f7fa;
  overflow: hidden;
}

.app-header {
  background: white;
  border-bottom: 1px solid #e4e7ed;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 20px;
  height: 60px;
  flex-shrink: 0;
}

.app-title {
  margin: 0;
  color: #303133;
  font-size: 20px;
  font-weight: 500;
}

.left-panel {
  background: white;
  border-right: 1px solid #e4e7ed;
  width: min(400px, 25vw);
  min-width: 320px;
  flex-shrink: 0;
}

.left-tabs {
  height: 100%;
  border: none;
  display: flex;
  flex-direction: column;
}

.left-tabs :deep(.el-tabs__content) {
  flex: 1;
  overflow: hidden;
  padding: 0;
}

.left-tabs :deep(.el-tab-pane) {
  height: 100%;
}

.tab-panel {
  height: calc(100vh - 100px); /* 调整高度计算 */
  display: flex;
  flex-direction: column;
  overflow: hidden; /* 防止内容溢出 */
}

.panel-toolbar {
  padding: 10px;
  border-bottom: 1px solid #e4e7ed;
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
}

.sql-editor {
  flex: 1;
  min-height: 0;
}

.gitlab-browser {
  height: 100%;
  display: flex;
  flex-direction: column;
  padding: 10px;
}

.file-list {
  flex: 1;
  margin-top: 10px;
  overflow-y: auto;
}

.gitlab-tree {
  height: 100%;
}

.main-content {
  padding: 20px;
  background: #f5f7fa;
  flex: 1;
  min-width: 0;
  overflow: hidden;
}

.lineage-container {
  height: calc(100vh - 100px);
  display: flex;
  flex-direction: column;
}

.result-summary {
  background: white;
  padding: 20px;
  border-radius: 8px;
  margin-bottom: 20px;
  box-shadow: 0 2px 12px rgba(0,0,0,0.1);
  flex-shrink: 0;
}

.graph-container {
  flex: 1;
  background: white;
  border-radius: 8px;
  box-shadow: 0 2px 12px rgba(0,0,0,0.1);
  min-height: 500px;
  overflow: hidden;
}

.empty-state {
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
}

.right-panel {
  background: white;
  border-left: 1px solid #e4e7ed;
  width: min(400px, 25vw);
  min-width: 350px;
  flex-shrink: 0;
  overflow: hidden;
}

.right-tabs {
  height: 100%;
  border: none;
  display: flex;
  flex-direction: column;
}

.right-tabs :deep(.el-tabs__content) {
  flex: 1;
  overflow: hidden;
  padding: 0;
}

.right-tabs :deep(.el-tab-pane) {
  height: 100%;
  overflow-y: auto;
}

.node-details {
  padding: 20px;
  margin-bottom: 20px;
}

.node-details h4 {
  margin: 0 0 15px 0;
  color: #303133;
}

.columns-section {
  margin-top: 20px;
}

.columns-section h5 {
  margin: 0 0 10px 0;
  color: #606266;
}

.schema-section {
  padding: 0 20px 20px 20px;
}

.schema-section h4 {
  margin: 0 0 15px 0;
  color: #303133;
}

/* 大屏幕优化 */
@media (min-width: 1400px) {
  .left-panel {
    width: min(450px, 20vw);
  }
  
  .right-panel {
    width: min(400px, 18vw);
  }
  
  .main-content {
    padding: 30px;
  }
}

/* 中等屏幕 */
@media (max-width: 1200px) {
  .left-panel {
    width: min(350px, 30vw);
  }
  
  .right-panel {
    width: min(300px, 25vw);
  }
}

/* 小屏幕适配 */
@media (max-width: 768px) {
  .app-header {
    flex-direction: column;
    height: auto;
    padding: 10px;
  }
  
  .header-left,
  .header-right {
    width: 100%;
    text-align: center;
  }
  
  .app-title {
    font-size: 16px;
    margin-bottom: 10px;
  }
  
  .left-panel {
    width: 100vw;
    position: absolute;
    top: 0;
    left: 0;
    z-index: 1000;
    transform: translateX(-100%);
    transition: transform 0.3s ease;
    height: 100vh;
  }
  
  .left-panel.active {
    transform: translateX(0);
  }
  
  .right-panel {
    width: 100vw;
    position: absolute;
    top: 0;
    right: 0;
    z-index: 1000;
    transform: translateX(100%);
    transition: transform 0.3s ease;
    height: 100vh;
  }
  
  .right-panel.active {
    transform: translateX(0);
  }
  
  .main-content {
    padding: 10px;
  }
  
  .lineage-container {
    height: calc(100vh - 80px);
  }
  
  .panel-toolbar {
    flex-direction: column;
    gap: 5px;
  }
}
</style>
