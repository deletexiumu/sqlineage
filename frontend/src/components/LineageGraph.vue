<template>
  <div 
    ref="lineageContainer" 
    :class="['lineage-graph', { 'fullscreen': isFullscreen }]"
  >
    <el-card>
      <template #header>
        <div class="card-header">
          <span>数据血缘可视化</span>
          <div class="header-actions">
            <!-- 分析模式切换 -->
            <el-radio-group v-model="analysisMode" size="small">
              <el-radio-button value="table">表查询</el-radio-button>
              <el-radio-button value="sql">SQL解析</el-radio-button>
            </el-radio-group>
            <!-- 全屏按钮 -->
            <el-button 
              size="small" 
              @click="toggleFullscreen"
              :icon="isFullscreen ? 'CloseFull' : 'FullScreen'"
            >
              {{ isFullscreen ? '退出全屏' : '全屏显示' }}
            </el-button>
          </div>
        </div>
      </template>

      <!-- 表查询模式 -->
      <div v-if="analysisMode === 'table'" class="table-search-mode">
        <div class="search-controls">
          <el-input
            v-model="searchTable"
            placeholder="输入表名搜索血缘关系 (如: database.table_name)"
            style="width: 400px"
            @keyup.enter="searchLineage"
          >
            <template #append>
              <el-button @click="searchLineage" :loading="loading">
                <el-icon><Search /></el-icon>
              </el-button>
            </template>
          </el-input>
          <el-select v-model="depth" placeholder="血缘深度" style="width: 100px">
            <el-option label="1层" :value="1" />
            <el-option label="2层" :value="2" />
            <el-option label="3层" :value="3" />
          </el-select>
        </div>
      </div>

      <!-- SQL解析模式 -->
      <div v-else class="sql-parse-mode">
        <div class="sql-editor-section">
          <div class="sql-editor-header">
            <div class="header-left">
              <span>输入SQL语句进行血缘分析</span>
              <el-tag type="info" size="small" class="preview-tag">
                <el-icon><View /></el-icon>
                预览模式
              </el-tag>
            </div>
            <div class="sql-actions">
              <el-button 
                type="primary" 
                @click="parseSqlLineage" 
                :loading="sqlParsing"
                size="small"
              >
                解析血缘
              </el-button>
              <el-button @click="clearSqlEditor" size="small">清空</el-button>
            </div>
          </div>
          <div class="sql-editor-container">
            <vue-monaco-editor
              v-model:value="sqlCode"
              language="sql"
              theme="vs-light"
              :options="editorOptions"
              style="height: 200px; border: 1px solid #dcdfe6; border-radius: 4px;"
            />
          </div>
        </div>
      </div>

      <div v-if="loading" class="loading-container">
        <el-loading :loading="loading" text="正在分析血缘关系..." />
      </div>

      <div v-else-if="error" class="error-container">
        <el-alert :title="error" type="error" show-icon />
      </div>

      <div v-else-if="showColumnGraph && columnGraph" class="column-graph-container">
        <div class="graph-mode-indicator">
          <el-tag type="success" size="large">
            <el-icon><Share /></el-icon>
            字段级血缘关系图
          </el-tag>
        </div>
        <ColumnLineageGraph 
          :column-graph="columnGraph" 
          :loading="sqlParsing" 
          :error="error" 
        />
      </div>

      <div v-else-if="graphData" class="graph-container">
        <div class="graph-mode-indicator">
          <el-tag type="primary" size="large">
            <el-icon><DataBoard /></el-icon>
            表级血缘关系图
          </el-tag>
        </div>
        <div ref="graphContainer" class="graph-canvas"></div>
        
        <div class="graph-info">
          <el-row :gutter="16">
            <el-col :span="6">
              <el-statistic title="节点数量" :value="graphData.nodes.length" />
            </el-col>
            <el-col :span="6">
              <el-statistic title="关系数量" :value="graphData.edges.length" />
            </el-col>
            <el-col :span="6">
              <el-statistic title="血缘深度" :value="depth" />
            </el-col>
            <el-col :span="6">
              <div class="graph-actions">
                <el-button size="small" @click="resetGraphView">
                  <el-icon><RefreshLeft /></el-icon>
                  重置视角
                </el-button>
                <el-button size="small" @click="downloadGraphPNG">
                  <el-icon><Download /></el-icon>
                  下载图形
                </el-button>
              </div>
            </el-col>
          </el-row>
        </div>
      </div>

      <div v-else class="empty-container">
        <el-empty description="请输入表名搜索血缘关系" />
      </div>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, nextTick } from 'vue'
import { Graph } from '@antv/g6'
import { VueMonacoEditor } from '@guolao/vue-monaco-editor'
import { lineageAPI } from '@/services/api'
import { ElMessage } from 'element-plus'
import { Search, Share, DataBoard, Download, RefreshLeft, View } from '@element-plus/icons-vue'
import ColumnLineageGraph from './ColumnLineageGraph.vue'

// 基础状态
const analysisMode = ref('table') // 'table' | 'sql'
const searchTable = ref('')
const depth = ref(2)
const loading = ref(false)
const error = ref('')
const graphData = ref<any>(null)
const graph = ref<Graph | null>(null)
const graphContainer = ref<HTMLElement>()
const lineageContainer = ref<HTMLElement>()

// 全屏状态
const isFullscreen = ref(false)

// SQL 解析相关状态
const sqlCode = ref(`-- 示例SQL：分析血缘关系
CREATE TABLE dwt_capital.dim_investment_event_df AS
SELECT 
    logic_id as bk_investment_event_id,
    investment_event_name,
    project_operational_status
FROM dwd_zbk.dwd_zbk_investor_project_information
WHERE dt = '20250625';`)

const sqlParsing = ref(false)
const parseResult = ref<any>(null)
const columnGraph = ref<any>(null)
const showColumnGraph = ref(false)

// Monaco Editor 配置
const editorOptions = {
  automaticLayout: true,
  fontSize: 14,
  minimap: { enabled: false },
  scrollBeyondLastLine: false,
  wordWrap: 'on' as const,
  lineNumbers: 'on' as const,
  glyphMargin: true,
  folding: true,
}

// SQL解析血缘关系
const parseSqlLineage = async () => {
  if (!sqlCode.value.trim()) {
    ElMessage.warning('请输入SQL代码')
    return
  }

  sqlParsing.value = true
  loading.value = true
  error.value = ''
  graphData.value = null
  parseResult.value = null

  try {
    // 调用SQL解析预览API（不保存到数据库）
    const response = await lineageAPI.parseSQLPreview(sqlCode.value)
    parseResult.value = response.data
    
    if (response.data.status === 'success') {
      // 处理字段级血缘图数据
      columnGraph.value = response.data.column_graph || null
      
      // 检查是否有血缘关系数据
      const relations = response.data.relations || []
      
      if (relations.length > 0 || (columnGraph.value && columnGraph.value.tables && columnGraph.value.tables.length > 0)) {
        // 如果有字段级血缘数据，优先显示字段级血缘图
        if (columnGraph.value && columnGraph.value.tables && columnGraph.value.tables.length > 0) {
          showColumnGraph.value = true
          ElMessage.success(`预览解析成功！发现 ${columnGraph.value.tables.length} 个表，${columnGraph.value.relationships.length} 个字段血缘关系（结果未保存）`)
        } else {
          // 否则显示表级血缘图
          showColumnGraph.value = false
          
          // 转换解析结果为图数据
          const graphNodes = new Set<string>()
          const graphEdges: any[] = []
          
          relations.forEach((relation: any) => {
            // 处理关系数据结构
            const sourceTable = relation.source_table?.full_name || relation.source_table?.name || 
                               (typeof relation.source_table === 'string' ? relation.source_table : '')
            const targetTable = relation.target_table?.full_name || relation.target_table?.name ||
                               (typeof relation.target_table === 'string' ? relation.target_table : '')
            
            if (sourceTable && targetTable) {
              graphNodes.add(sourceTable)
              graphNodes.add(targetTable)
              
              graphEdges.push({
                source: sourceTable,
                target: targetTable,
                type: relation.relation_type || 'insert'
              })
            }
          })

          if (graphNodes.size > 0) {
            graphData.value = {
              nodes: Array.from(graphNodes).map(nodeId => ({
                id: nodeId,
                label: nodeId
              })),
              edges: graphEdges
            }

            await nextTick()
            renderGraph()
            
            ElMessage.success(`预览解析成功！发现 ${graphNodes.size} 个表，${graphEdges.length} 个血缘关系（结果未保存）`)
          } else {
            error.value = 'SQL中未发现表级血缘关系'
            ElMessage.warning(error.value)
          }
        }
      } else {
        error.value = 'SQL解析成功，但未发现血缘关系'
        ElMessage.warning(error.value)
      }
    } else {
      error.value = response.data.message || 'SQL解析失败'
      ElMessage.error(error.value)
    }
  } catch (err: any) {
    console.error('Parse SQL lineage error:', err)
    error.value = err.response?.data?.error || err.response?.data?.message || 'SQL解析失败'
    ElMessage.error(error.value)
  } finally {
    sqlParsing.value = false
    loading.value = false
  }
}

// 清空SQL编辑器
const clearSqlEditor = () => {
  sqlCode.value = ''
  parseResult.value = null
  graphData.value = null
  columnGraph.value = null
  showColumnGraph.value = false
  error.value = ''
}

// 表查询血缘关系
const searchLineage = async () => {
  if (!searchTable.value.trim()) {
    ElMessage.warning('请输入表名')
    return
  }

  loading.value = true
  error.value = ''
  graphData.value = null

  try {
    const response = await lineageAPI.getGraph(searchTable.value, depth.value)
    graphData.value = response.data
    
    if (graphData.value.nodes.length === 0) {
      error.value = '未找到相关的血缘关系'
      return
    }

    await nextTick()
    renderGraph()
    
    ElMessage.success(`发现 ${graphData.value.nodes.length} 个相关表`)
  } catch (err: any) {
    console.error('Search lineage error:', err)
    error.value = err.response?.data?.error || '搜索血缘关系失败'
    ElMessage.error(error.value)
  } finally {
    loading.value = false
  }
}

const renderGraph = () => {
  if (!graphContainer.value || !graphData.value) return

  // Clear existing graph
  if (graph.value) {
    graph.value.destroy()
  }

  const container = graphContainer.value
  const width = container.clientWidth || 800
  const height = 600

  // 表名处理函数 - 显示完整名称，不再省略
  const getDisplayTableName = (fullName: string) => {
    return fullName // 直接返回完整名称
  }

  // Process data for G6
  const nodes = graphData.value.nodes.map((node: any) => ({
    id: node.id,
    label: getDisplayTableName(node.label),
    originalLabel: node.label, // 保存原始完整名称
    type: 'rect',
    style: {
      fill: node.id === searchTable.value ? '#1890ff' : '#5B8FF9',
      stroke: '#1890ff',
      lineWidth: 2,
    },
    labelCfg: {
      style: {
        fill: '#000',
        fontSize: 12,
      },
    },
  }))

  const edges = graphData.value.edges.map((edge: any, index: number) => ({
    id: `edge-${index}`,
    source: edge.source,
    target: edge.target,
    type: 'line',
    style: {
      stroke: '#91d5ff',
      lineWidth: 2,
      endArrow: {
        path: 'M 0,0 L 8,4 L 8,-4 Z',
        fill: '#91d5ff',
      },
    },
    label: edge.type,
    labelCfg: {
      style: {
        fill: '#666',
        fontSize: 10,
      },
    },
  }))

  graph.value = new Graph({
    container: container,
    width,
    height,
    modes: {
      default: ['drag-canvas', 'zoom-canvas', 'drag-node'],
    },
    defaultNode: {
      size: [200, 50], // 增加节点宽度和高度以适应完整表名
      style: {
        fill: '#5B8FF9',
        stroke: '#5B8FF9',
        lineWidth: 1,
      },
      labelCfg: {
        style: {
          fill: '#fff',
          fontSize: 12,
        },
      },
    },
    defaultEdge: {
      style: {
        stroke: '#e2e2e2',
        lineWidth: 1,
      },
    },
    layout: {
      type: 'dagre',
      direction: 'TB',
      align: 'UL',
      nodesep: 20,
      ranksep: 50,
    },
  })

  graph.value.data({
    nodes,
    edges,
  })

  graph.value.render()

  // 复制到剪贴板的函数
  const copyToClipboard = (text: string) => {
    if (navigator.clipboard && window.isSecureContext) {
      navigator.clipboard.writeText(text).then(() => {
        ElMessage.success(`已复制: ${text}`)
      }).catch(() => {
        ElMessage.error('复制失败')
      })
    } else {
      // 降级方案
      const textArea = document.createElement('textarea')
      textArea.value = text
      document.body.appendChild(textArea)
      textArea.select()
      try {
        document.execCommand('copy')
        ElMessage.success(`已复制: ${text}`)
      } catch {
        ElMessage.error('复制失败')
      }
      document.body.removeChild(textArea)
    }
  }

  // Add event listeners
  graph.value.on('node:click', (e) => {
    const node = e.item
    const model = node?.getModel()
    if (model) {
      // 显示完整的表名
      const fullName = model.originalLabel || model.id
      ElMessage.info(`点击了表: ${fullName}`)
    }
  })

  // 添加双击复制功能
  graph.value.on('node:dblclick', (e) => {
    const node = e.item
    const model = node?.getModel()
    if (model) {
      const fullName = model.originalLabel || model.id
      copyToClipboard(fullName)
    }
  })

  graph.value.on('edge:click', (e) => {
    const edge = e.item
    const model = edge?.getModel()
    if (model) {
      ElMessage.info(`血缘关系: ${model.source} -> ${model.target}`)
    }
  })
}

// 重置图形视角
const resetGraphView = () => {
  if (!graph.value) {
    ElMessage.warning('没有可重置的图形')
    return
  }

  try {
    // 重置缩放比例到1
    graph.value.zoomTo(1, {
      animate: true,
      animateCfg: {
        duration: 500,
        easing: 'easeInOut'
      }
    })
    
    // 居中显示图形
    graph.value.fitCenter(true)
    
    ElMessage.success('视角已重置')
  } catch (error) {
    console.error('重置视角失败:', error)
    ElMessage.error('重置视角失败，请重试')
  }
}

// 下载表级血缘图
const downloadGraphPNG = () => {
  if (!graph.value) {
    ElMessage.error('没有可下载的图形')
    return
  }

  try {
    // 使用G6的下载功能
    graph.value.downloadFullImage('表级血缘图', 'image/png', {
      backgroundColor: '#fff',
      padding: 20
    })
    ElMessage.success('图形已下载')
  } catch (error) {
    console.error('下载失败:', error)
    ElMessage.error('下载失败，请重试')
  }
}

const resizeGraph = () => {
  if (graph.value && graphContainer.value) {
    const width = graphContainer.value.clientWidth
    const height = 600
    graph.value.changeSize(width, height)
  }
}

onMounted(() => {
  window.addEventListener('resize', resizeGraph)
})

onUnmounted(() => {
  if (graph.value) {
    graph.value.destroy()
  }
  window.removeEventListener('resize', resizeGraph)
  document.removeEventListener('keydown', handleEscKey)
})

// 全屏功能
const toggleFullscreen = async () => {
  if (!lineageContainer.value) return

  try {
    if (!isFullscreen.value) {
      // 进入全屏
      if (lineageContainer.value.requestFullscreen) {
        await lineageContainer.value.requestFullscreen()
      } else if ((lineageContainer.value as any).webkitRequestFullscreen) {
        await (lineageContainer.value as any).webkitRequestFullscreen()
      } else if ((lineageContainer.value as any).msRequestFullscreen) {
        await (lineageContainer.value as any).msRequestFullscreen()
      }
      isFullscreen.value = true
    } else {
      // 退出全屏
      if (document.exitFullscreen) {
        await document.exitFullscreen()
      } else if ((document as any).webkitExitFullscreen) {
        await (document as any).webkitExitFullscreen()
      } else if ((document as any).msExitFullscreen) {
        await (document as any).msExitFullscreen()
      }
      isFullscreen.value = false
    }
    
    // 延迟重新渲染图形以适应新尺寸
    setTimeout(() => {
      resizeGraph()
    }, 300)
  } catch (error) {
    console.error('全屏切换失败:', error)
    ElMessage.error('全屏功能不被支持或发生错误')
  }
}

// 监听全屏状态变化
const handleFullscreenChange = () => {
  const isCurrentlyFullscreen = !!(
    document.fullscreenElement ||
    (document as any).webkitFullscreenElement ||
    (document as any).msFullscreenElement
  )
  
  if (isCurrentlyFullscreen !== isFullscreen.value) {
    isFullscreen.value = isCurrentlyFullscreen
    // 延迟重新渲染图形
    setTimeout(() => {
      resizeGraph()
    }, 300)
  }
}

// 处理ESC键退出全屏
const handleEscKey = (event: KeyboardEvent) => {
  if (event.key === 'Escape' && isFullscreen.value) {
    toggleFullscreen()
  }
}

onMounted(() => {
  window.addEventListener('resize', resizeGraph)
  document.addEventListener('fullscreenchange', handleFullscreenChange)
  document.addEventListener('webkitfullscreenchange', handleFullscreenChange)
  document.addEventListener('msfullscreenchange', handleFullscreenChange)
  document.addEventListener('keydown', handleEscKey)
})

onUnmounted(() => {
  if (graph.value) {
    graph.value.destroy()
  }
  window.removeEventListener('resize', resizeGraph)
  document.removeEventListener('fullscreenchange', handleFullscreenChange)
  document.removeEventListener('webkitfullscreenchange', handleFullscreenChange)
  document.removeEventListener('msfullscreenchange', handleFullscreenChange)
  document.removeEventListener('keydown', handleEscKey)
})
</script>

<style scoped>
.lineage-graph {
  height: 100%;
  padding: 20px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 10px;
}

.header-actions {
  display: flex;
  gap: 12px;
  align-items: center;
  flex-wrap: wrap;
}

/* 表查询模式样式 */
.table-search-mode {
  margin-bottom: 20px;
}

.search-controls {
  display: flex;
  gap: 12px;
  align-items: center;
  flex-wrap: wrap;
}

/* SQL解析模式样式 */
.sql-parse-mode {
  margin-bottom: 20px;
}

.sql-editor-section {
  border: 1px solid #e4e7ed;
  border-radius: 4px;
  background: #fff;
}

.sql-editor-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 16px;
  background: #f5f7fa;
  border-bottom: 1px solid #e4e7ed;
  border-radius: 4px 4px 0 0;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 12px;
}

.preview-tag {
  font-size: 11px;
}

.sql-actions {
  display: flex;
  gap: 8px;
}

.sql-editor-container {
  padding: 0;
}

.loading-container,
.error-container,
.empty-container {
  height: 400px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.graph-container,
.column-graph-container {
  position: relative;
}

.graph-mode-indicator {
  margin-bottom: 16px;
  text-align: center;
}

.graph-mode-indicator .el-tag {
  padding: 8px 16px;
  font-size: 14px;
}

.graph-mode-indicator .el-icon {
  margin-right: 8px;
}

.graph-canvas {
  height: 600px;
  border: 1px solid #d9d9d9;
  border-radius: 4px;
  background: #fafafa;
}

.graph-info {
  margin-top: 16px;
  padding: 16px;
  background: #f5f7fa;
  border-radius: 4px;
}

.graph-actions {
  text-align: center;
}

:deep(.el-statistic__content) {
  font-size: 18px;
  font-weight: 600;
}

:deep(.el-statistic__title) {
  font-size: 12px;
  color: #666;
}

/* 响应式设计 */
@media (max-width: 768px) {
  .lineage-graph {
    padding: 10px;
  }
  
  .card-header {
    flex-direction: column;
    align-items: stretch;
  }
  
  .search-controls {
    flex-direction: column;
    align-items: stretch;
  }
  
  .search-controls .el-input {
    width: 100% !important;
  }
  
  .sql-editor-header {
    flex-direction: column;
    gap: 10px;
    align-items: stretch;
  }
  
  .sql-actions {
    justify-content: center;
  }
  
  .graph-canvas {
    height: 400px;
  }
}

@media (max-width: 480px) {
  .lineage-graph {
    padding: 5px;
  }
  
  .sql-actions {
    flex-direction: column;
  }
  
  .sql-actions .el-button {
    width: 100%;
  }
  
  .graph-canvas {
    height: 300px;
  }
  
  :deep(.el-radio-group) {
    width: 100%;
  }
  
  :deep(.el-radio-button) {
    flex: 1;
  }
}

/* 全屏模式样式 */
.lineage-graph.fullscreen {
  position: fixed !important;
  top: 0 !important;
  left: 0 !important;
  width: 100vw !important;
  height: 100vh !important;
  z-index: 9999 !important;
  background: white !important;
  padding: 20px !important;
  box-sizing: border-box !important;
}

.lineage-graph.fullscreen .graph-canvas {
  height: calc(100vh - 250px) !important;
}

.lineage-graph.fullscreen .el-card {
  height: 100% !important;
  display: flex !important;
  flex-direction: column !important;
}

.lineage-graph.fullscreen .el-card__body {
  flex: 1 !important;
  display: flex !important;
  flex-direction: column !important;
  overflow: hidden !important;
}

.lineage-graph.fullscreen .graph-container {
  flex: 1 !important;
  display: flex !important;
  flex-direction: column !important;
}

.lineage-graph.fullscreen .column-graph-container {
  flex: 1 !important;
  display: flex !important;
  flex-direction: column !important;
}
</style>