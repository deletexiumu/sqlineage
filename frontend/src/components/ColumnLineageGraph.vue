<template>
  <div class="column-lineage-graph">
    <div v-if="loading" class="loading-container">
      <el-loading :loading="loading" text="正在渲染字段血缘图..." />
    </div>
    
    <div v-else-if="error" class="error-container">
      <el-alert :title="error" type="error" show-icon />
    </div>
    
    <div v-else-if="columnGraph && columnGraph.tables && columnGraph.tables.length > 0" class="graph-container">
      <div ref="graphContainer" class="graph-canvas"></div>
      
      <div class="graph-legend">
        <div class="legend-item">
          <div class="legend-color source"></div>
          <span>源表</span>
        </div>
        <div class="legend-item">
          <div class="legend-color target"></div>
          <span>目标表</span>
        </div>
        <div class="legend-item">
          <div class="legend-line"></div>
          <span>字段血缘关系</span>
        </div>
        <div class="legend-actions">
          <el-button size="small" @click="downloadPNG">
            <el-icon><Download /></el-icon>
            下载PNG
          </el-button>
          <el-button size="small" @click="downloadSVG">
            <el-icon><Download /></el-icon>
            下载SVG
          </el-button>
        </div>
      </div>
      
      <div class="graph-stats">
        <el-row :gutter="16">
          <el-col :span="8">
            <el-statistic title="表数量" :value="columnGraph.tables.length" />
          </el-col>
          <el-col :span="8">
            <el-statistic title="字段总数" :value="totalColumns" />
          </el-col>
          <el-col :span="8">
            <el-statistic title="血缘关系" :value="columnGraph.relationships.length" />
          </el-col>
        </el-row>
      </div>
    </div>
    
    <div v-else class="empty-container">
      <el-empty description="暂无字段血缘关系数据" />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, nextTick, computed, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { Download } from '@element-plus/icons-vue'

interface ColumnGraphTable {
  name: string
  type: 'source' | 'target'
  columns: string[]
}

interface ColumnGraphRelationship {
  id: string
  source_table: string
  source_column: string
  target_table: string
  target_column: string
  relation_type: string
}

interface ColumnGraphData {
  tables: ColumnGraphTable[]
  relationships: ColumnGraphRelationship[]
}

// Props
const props = defineProps<{
  columnGraph: ColumnGraphData | null
  loading?: boolean
  error?: string
}>()

// Refs
const graphContainer = ref<HTMLElement>()
const highlightedElements = ref<Set<string>>(new Set())

// Computed
const totalColumns = computed(() => {
  return props.columnGraph?.tables.reduce((total, table) => total + table.columns.length, 0) || 0
})

// 渲染字段级血缘图
const renderColumnGraph = () => {
  if (!graphContainer.value || !props.columnGraph || props.columnGraph.tables.length === 0) {
    return
  }

  const container = graphContainer.value
  container.innerHTML = '' // 清空容器

  const containerWidth = container.clientWidth || 1200
  const containerHeight = 600
  
  // 创建SVG
  const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg')
  svg.setAttribute('width', containerWidth.toString())
  svg.setAttribute('height', containerHeight.toString())
  svg.setAttribute('viewBox', `0 0 ${containerWidth} ${containerHeight}`)
  svg.style.background = '#fafafa'
  svg.style.border = '1px solid #d9d9d9'
  svg.style.borderRadius = '4px'

  // 定义箭头标记
  const defs = document.createElementNS('http://www.w3.org/2000/svg', 'defs')
  const marker = document.createElementNS('http://www.w3.org/2000/svg', 'marker')
  marker.setAttribute('id', 'arrowhead')
  marker.setAttribute('markerWidth', '10')
  marker.setAttribute('markerHeight', '7')
  marker.setAttribute('refX', '9')
  marker.setAttribute('refY', '3.5')
  marker.setAttribute('orient', 'auto')
  
  const polygon = document.createElementNS('http://www.w3.org/2000/svg', 'polygon')
  polygon.setAttribute('points', '0 0, 10 3.5, 0 7')
  polygon.setAttribute('fill', '#91d5ff')
  
  marker.appendChild(polygon)
  defs.appendChild(marker)
  svg.appendChild(defs)

  // 分离源表和目标表
  const sourceTables = props.columnGraph.tables.filter(t => t.type === 'source')
  const targetTables = props.columnGraph.tables.filter(t => t.type === 'target')
  
  // 计算布局参数
  const tableWidth = 250
  const tableHeaderHeight = 40
  const columnHeight = 25
  const tableSpacing = 100
  
  const maxColumns = Math.max(
    ...props.columnGraph.tables.map(t => t.columns.length)
  )
  const tableHeight = tableHeaderHeight + maxColumns * columnHeight + 20
  
  const leftColumnX = 50
  const rightColumnX = containerWidth - tableWidth - 50
  
  // 渲染表格的函数
  const renderTable = (table: ColumnGraphTable, x: number, y: number, tableIndex: number) => {
    const tableGroup = document.createElementNS('http://www.w3.org/2000/svg', 'g')
    tableGroup.setAttribute('class', `table-${table.type}`)
    
    // 表头背景
    const headerRect = document.createElementNS('http://www.w3.org/2000/svg', 'rect')
    headerRect.setAttribute('x', x.toString())
    headerRect.setAttribute('y', y.toString())
    headerRect.setAttribute('width', tableWidth.toString())
    headerRect.setAttribute('height', tableHeaderHeight.toString())
    headerRect.setAttribute('fill', table.type === 'source' ? '#e6f7ff' : '#f6ffed')
    headerRect.setAttribute('stroke', table.type === 'source' ? '#1890ff' : '#52c41a')
    headerRect.setAttribute('stroke-width', '2')
    headerRect.setAttribute('rx', '4')
    
    // 表名处理 - 自适应文本和省略库名
    const getDisplayTableName = (fullName: string, maxWidth: number) => {
      // 先尝试只显示表名（去掉库名）
      const parts = fullName.split('.')
      const tableName = parts.length > 1 ? parts[parts.length - 1] : fullName
      
      // 如果表名仍然太长，进行省略
      if (tableName.length > 20) {
        return tableName.substring(0, 17) + '...'
      }
      
      return tableName
    }
    
    const displayName = getDisplayTableName(table.name, tableWidth - 20)
    
    const tableName = document.createElementNS('http://www.w3.org/2000/svg', 'text')
    tableName.setAttribute('x', (x + tableWidth / 2).toString())
    tableName.setAttribute('y', (y + tableHeaderHeight / 2 + 5).toString())
    tableName.setAttribute('text-anchor', 'middle')
    tableName.setAttribute('font-size', '12')
    tableName.setAttribute('font-weight', 'bold')
    tableName.setAttribute('fill', '#333')
    tableName.textContent = displayName
    
    // 添加完整表名的tooltip
    const tableNameTitle = document.createElementNS('http://www.w3.org/2000/svg', 'title')
    tableNameTitle.textContent = table.name
    tableName.appendChild(tableNameTitle)
    
    tableGroup.appendChild(headerRect)
    tableGroup.appendChild(tableName)
    
    // 字段列表背景
    const bodyRect = document.createElementNS('http://www.w3.org/2000/svg', 'rect')
    bodyRect.setAttribute('x', x.toString())
    bodyRect.setAttribute('y', (y + tableHeaderHeight).toString())
    bodyRect.setAttribute('width', tableWidth.toString())
    bodyRect.setAttribute('height', (table.columns.length * columnHeight + 10).toString())
    bodyRect.setAttribute('fill', '#fff')
    bodyRect.setAttribute('stroke', table.type === 'source' ? '#1890ff' : '#52c41a')
    bodyRect.setAttribute('stroke-width', '1')
    
    tableGroup.appendChild(bodyRect)
    
    // 渲染字段
    table.columns.forEach((column, columnIndex) => {
      const columnY = y + tableHeaderHeight + 15 + columnIndex * columnHeight
      const columnId = `${table.name}.${column}`
      
      // 字段背景（用于高亮）
      const columnBg = document.createElementNS('http://www.w3.org/2000/svg', 'rect')
      columnBg.setAttribute('x', (x + 5).toString())
      columnBg.setAttribute('y', (columnY - 12).toString())
      columnBg.setAttribute('width', (tableWidth - 10).toString())
      columnBg.setAttribute('height', '20')
      columnBg.setAttribute('fill', 'transparent')
      columnBg.setAttribute('rx', '2')
      columnBg.setAttribute('id', `bg-${columnId}`)
      columnBg.style.cursor = 'pointer'
      
      // 字段文本
      const columnText = document.createElementNS('http://www.w3.org/2000/svg', 'text')
      columnText.setAttribute('x', (x + 15).toString())
      columnText.setAttribute('y', columnY.toString())
      columnText.setAttribute('font-size', '12')
      columnText.setAttribute('fill', '#666')
      columnText.setAttribute('id', `text-${columnId}`)
      columnText.style.cursor = 'pointer'
      columnText.textContent = column
      
      // 连接点（圆点）
      const connectionPoint = document.createElementNS('http://www.w3.org/2000/svg', 'circle')
      const pointX = table.type === 'source' ? x + tableWidth : x
      connectionPoint.setAttribute('cx', pointX.toString())
      connectionPoint.setAttribute('cy', columnY.toString())
      connectionPoint.setAttribute('r', '4')
      connectionPoint.setAttribute('fill', table.type === 'source' ? '#1890ff' : '#52c41a')
      connectionPoint.setAttribute('id', `point-${columnId}`)
      
      // 鼠标事件
      const handleMouseEnter = () => highlightColumn(columnId)
      const handleMouseLeave = () => clearHighlight()
      
      columnBg.addEventListener('mouseenter', handleMouseEnter)
      columnBg.addEventListener('mouseleave', handleMouseLeave)
      columnText.addEventListener('mouseenter', handleMouseEnter)
      columnText.addEventListener('mouseleave', handleMouseLeave)
      connectionPoint.addEventListener('mouseenter', handleMouseEnter)
      connectionPoint.addEventListener('mouseleave', handleMouseLeave)
      
      tableGroup.appendChild(columnBg)
      tableGroup.appendChild(columnText)
      tableGroup.appendChild(connectionPoint)
    })
    
    return tableGroup
  }
  
  // 渲染源表（左侧）
  sourceTables.forEach((table, index) => {
    const y = 50 + index * (tableHeight + 30)
    const tableElement = renderTable(table, leftColumnX, y, index)
    svg.appendChild(tableElement)
  })
  
  // 渲染目标表（右侧）
  targetTables.forEach((table, index) => {
    const y = 50 + index * (tableHeight + 30)
    const tableElement = renderTable(table, rightColumnX, y, index)
    svg.appendChild(tableElement)
  })
  
  // 渲染连线
  props.columnGraph.relationships.forEach((rel) => {
    const sourceColumnId = `${rel.source_table}.${rel.source_column}`
    const targetColumnId = `${rel.target_table}.${rel.target_column}`
    
    // 计算连线位置
    const sourceTable = sourceTables.find(t => t.name === rel.source_table)
    const targetTable = targetTables.find(t => t.name === rel.target_table)
    
    if (!sourceTable || !targetTable) return
    
    const sourceTableIndex = sourceTables.indexOf(sourceTable)
    const targetTableIndex = targetTables.indexOf(targetTable)
    const sourceColumnIndex = sourceTable.columns.indexOf(rel.source_column)
    const targetColumnIndex = targetTable.columns.indexOf(rel.target_column)
    
    if (sourceColumnIndex === -1 || targetColumnIndex === -1) return
    
    const sourceY = 50 + sourceTableIndex * (tableHeight + 30) + tableHeaderHeight + 15 + sourceColumnIndex * columnHeight
    const targetY = 50 + targetTableIndex * (tableHeight + 30) + tableHeaderHeight + 15 + targetColumnIndex * columnHeight
    
    const sourceX = leftColumnX + tableWidth
    const targetX = rightColumnX
    
    // 创建连线路径
    const path = document.createElementNS('http://www.w3.org/2000/svg', 'path')
    const midX = (sourceX + targetX) / 2
    const pathData = `M ${sourceX} ${sourceY} C ${midX} ${sourceY}, ${midX} ${targetY}, ${targetX} ${targetY}`
    
    path.setAttribute('d', pathData)
    path.setAttribute('stroke', '#91d5ff')
    path.setAttribute('stroke-width', '2')
    path.setAttribute('fill', 'none')
    path.setAttribute('marker-end', 'url(#arrowhead)')
    path.setAttribute('id', `line-${rel.id}`)
    path.setAttribute('class', `relationship-line`)
    path.setAttribute('data-source', sourceColumnId)
    path.setAttribute('data-target', targetColumnId)
    
    svg.appendChild(path)
  })
  
  container.appendChild(svg)
}

// 下载PNG功能
const downloadPNG = () => {
  const svg = graphContainer.value?.querySelector('svg')
  if (!svg) {
    ElMessage.error('没有可下载的图形')
    return
  }

  try {
    // 创建canvas
    const canvas = document.createElement('canvas')
    const ctx = canvas.getContext('2d')
    if (!ctx) return

    const svgData = new XMLSerializer().serializeToString(svg)
    const svgBlob = new Blob([svgData], { type: 'image/svg+xml;charset=utf-8' })
    const svgUrl = URL.createObjectURL(svgBlob)

    const img = new Image()
    img.onload = () => {
      canvas.width = img.width * 2  // 提高分辨率
      canvas.height = img.height * 2
      ctx.scale(2, 2)
      ctx.fillStyle = 'white'
      ctx.fillRect(0, 0, canvas.width, canvas.height)
      ctx.drawImage(img, 0, 0)

      // 下载
      const link = document.createElement('a')
      link.download = `字段血缘图_${new Date().getTime()}.png`
      link.href = canvas.toDataURL('image/png')
      link.click()

      URL.revokeObjectURL(svgUrl)
      ElMessage.success('图形已下载')
    }
    img.src = svgUrl
  } catch (error) {
    console.error('下载失败:', error)
    ElMessage.error('下载失败，请重试')
  }
}

// 下载SVG功能
const downloadSVG = () => {
  const svg = graphContainer.value?.querySelector('svg')
  if (!svg) {
    ElMessage.error('没有可下载的图形')
    return
  }

  try {
    const svgData = new XMLSerializer().serializeToString(svg)
    const svgBlob = new Blob([svgData], { type: 'image/svg+xml;charset=utf-8' })
    const svgUrl = URL.createObjectURL(svgBlob)

    const link = document.createElement('a')
    link.download = `字段血缘图_${new Date().getTime()}.svg`
    link.href = svgUrl
    link.click()

    URL.revokeObjectURL(svgUrl)
    ElMessage.success('SVG文件已下载')
  } catch (error) {
    console.error('下载失败:', error)
    ElMessage.error('下载失败，请重试')
  }
}

// 高亮字段及相关连线
const highlightColumn = (columnId: string) => {
  clearHighlight()
  
  // 高亮当前字段
  const columnBg = document.getElementById(`bg-${columnId}`)
  const columnText = document.getElementById(`text-${columnId}`)
  const connectionPoint = document.getElementById(`point-${columnId}`)
  
  if (columnBg) {
    columnBg.setAttribute('fill', '#e6f7ff')
    highlightedElements.value.add(`bg-${columnId}`)
  }
  if (columnText) {
    columnText.setAttribute('fill', '#1890ff')
    columnText.setAttribute('font-weight', 'bold')
    highlightedElements.value.add(`text-${columnId}`)
  }
  if (connectionPoint) {
    connectionPoint.setAttribute('r', '6')
    highlightedElements.value.add(`point-${columnId}`)
  }
  
  // 高亮相关连线和字段
  const lines = document.querySelectorAll('.relationship-line')
  lines.forEach((line) => {
    const sourceColumn = line.getAttribute('data-source')
    const targetColumn = line.getAttribute('data-target')
    
    if (sourceColumn === columnId || targetColumn === columnId) {
      // 高亮连线
      line.setAttribute('stroke', '#ff7875')
      line.setAttribute('stroke-width', '3')
      highlightedElements.value.add(line.id)
      
      // 高亮相关字段
      const relatedColumnId = sourceColumn === columnId ? targetColumn : sourceColumn
      if (relatedColumnId) {
        const relatedBg = document.getElementById(`bg-${relatedColumnId}`)
        const relatedText = document.getElementById(`text-${relatedColumnId}`)
        const relatedPoint = document.getElementById(`point-${relatedColumnId}`)
        
        if (relatedBg) {
          relatedBg.setAttribute('fill', '#fff2e8')
          highlightedElements.value.add(`bg-${relatedColumnId}`)
        }
        if (relatedText) {
          relatedText.setAttribute('fill', '#fa8c16')
          relatedText.setAttribute('font-weight', 'bold')
          highlightedElements.value.add(`text-${relatedColumnId}`)
        }
        if (relatedPoint) {
          relatedPoint.setAttribute('r', '6')
          highlightedElements.value.add(`point-${relatedColumnId}`)
        }
      }
    }
  })
}

// 清除高亮
const clearHighlight = () => {
  highlightedElements.value.forEach((elementId) => {
    const element = document.getElementById(elementId)
    if (element) {
      if (elementId.startsWith('bg-')) {
        element.setAttribute('fill', 'transparent')
      } else if (elementId.startsWith('text-')) {
        element.setAttribute('fill', '#666')
        element.setAttribute('font-weight', 'normal')
      } else if (elementId.startsWith('point-')) {
        element.setAttribute('r', '4')
      } else if (elementId.startsWith('line-')) {
        element.setAttribute('stroke', '#91d5ff')
        element.setAttribute('stroke-width', '2')
      }
    }
  })
  highlightedElements.value.clear()
}

// 响应式调整
const resizeGraph = () => {
  if (props.columnGraph && props.columnGraph.tables.length > 0) {
    nextTick(() => {
      renderColumnGraph()
    })
  }
}

// 监听数据变化
watch(() => props.columnGraph, () => {
  if (props.columnGraph && props.columnGraph.tables.length > 0) {
    nextTick(() => {
      renderColumnGraph()
    })
  }
})

onMounted(() => {
  window.addEventListener('resize', resizeGraph)
  if (props.columnGraph && props.columnGraph.tables.length > 0) {
    nextTick(() => {
      renderColumnGraph()
    })
  }
})

onUnmounted(() => {
  window.removeEventListener('resize', resizeGraph)
})
</script>

<style scoped>
.column-lineage-graph {
  width: 100%;
  height: 100%;
}

.loading-container,
.error-container,
.empty-container {
  height: 400px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.graph-container {
  position: relative;
}

.graph-canvas {
  width: 100%;
  height: 600px;
  overflow: auto;
}

.graph-legend {
  display: flex;
  align-items: center;
  gap: 20px;
  margin: 16px 0;
  padding: 12px;
  background: #f5f7fa;
  border-radius: 4px;
}

.legend-item {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 12px;
  color: #666;
}

.legend-actions {
  margin-left: auto;
  display: flex;
  gap: 8px;
}

.legend-color {
  width: 16px;
  height: 16px;
  border-radius: 2px;
}

.legend-color.source {
  background: #e6f7ff;
  border: 2px solid #1890ff;
}

.legend-color.target {
  background: #f6ffed;
  border: 2px solid #52c41a;
}

.legend-line {
  width: 20px;
  height: 2px;
  background: #91d5ff;
  position: relative;
}

.legend-line::after {
  content: '';
  position: absolute;
  right: -4px;
  top: -2px;
  width: 0;
  height: 0;
  border-left: 4px solid #91d5ff;
  border-top: 3px solid transparent;
  border-bottom: 3px solid transparent;
}

.graph-stats {
  margin-top: 16px;
  padding: 16px;
  background: #f5f7fa;
  border-radius: 4px;
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
  .graph-canvas {
    height: 400px;
  }
  
  .graph-legend {
    flex-wrap: wrap;
    gap: 10px;
  }
  
  .legend-item {
    font-size: 11px;
  }
}

@media (max-width: 480px) {
  .graph-canvas {
    height: 300px;
  }
  
  .graph-legend {
    flex-direction: column;
    align-items: flex-start;
  }
}
</style>