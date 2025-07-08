<template>
  <div class="lineage-graph-container" ref="containerRef">
    <div class="graph-toolbar">
      <el-button-group>
        <el-button @click="resetZoom" icon="Refresh" size="small">重置视图</el-button>
        <el-button @click="fitToScreen" icon="FullScreen" size="small">适应屏幕</el-button>
        <el-button @click="toggleFieldLevel" size="small" :type="showFieldLevel ? 'primary' : ''">
          字段级血缘
        </el-button>
      </el-button-group>
      
      <div class="legend">
        <span class="legend-item">
          <span class="legend-color source" style="background-color: #4CAF50;"></span>源表 Source
        </span>
        <span class="legend-item">
          <span class="legend-color target" style="background-color: #FF5722;"></span>目标表 Target
        </span>
        <span class="legend-item">
          <span class="legend-color stage" style="background-color: #2196F3;"></span>中间表 Stage
        </span>
        <span class="legend-item">
          <span class="legend-color field" style="background-color: #1976D2; width: 20px; height: 2px; border-radius: 1px;"></span>字段连线
        </span>
      </div>
    </div>
    
    <div class="graph-area" ref="graphRef">
      <svg ref="svgRef" class="lineage-svg">
        <defs>
          <marker id="arrowhead" markerWidth="10" markerHeight="7" 
                  refX="9" refY="3.5" orient="auto">
            <polygon points="0 0, 10 3.5, 0 7" fill="#666" />
          </marker>
          <marker id="arrowhead-field" markerWidth="8" markerHeight="6" 
                  refX="7" refY="3" orient="auto">
            <polygon points="0 0, 8 3, 0 6" fill="#2196F3" />
          </marker>
          <filter id="glow" x="-20%" y="-20%" width="140%" height="140%">
            <feGaussianBlur stdDeviation="3" result="coloredBlur"/>
            <feMerge> 
              <feMergeNode in="coloredBlur"/>
              <feMergeNode in="SourceGraphic"/>
            </feMerge>
          </filter>
        </defs>
        <g class="zoom-container">
          <g class="links-container"></g>
          <g class="field-links-container"></g>
          <g class="nodes-container"></g>
        </g>
      </svg>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, watch, nextTick } from 'vue';
import * as d3 from 'd3';

const props = defineProps({
  lineageData: {
    type: Object,
    default: () => ({})
  },
  showFieldLevel: {
    type: Boolean,
    default: true
  },
  highlightedTables: {
    type: Set,
    default: () => new Set()
  }
});

const emit = defineEmits(['nodeClick', 'nodeHover']);

// DOM引用
const containerRef = ref(null);
const graphRef = ref(null);
const svgRef = ref(null);

// 内部状态
const showFieldLevel = ref(props.showFieldLevel);
const simulation = ref(null);
const svg = ref(null);
const zoom = ref(null);

// 图形尺寸
let width = 0;
let height = 0;

onMounted(() => {
  initGraph();
  renderGraph();
});

watch(() => props.lineageData, () => {
  renderGraph();
}, { deep: true });

watch(() => props.showFieldLevel, (newVal) => {
  showFieldLevel.value = newVal;
  updateFieldLevelDisplay();
});

watch(() => props.highlightedTables, () => {
  updateHighlight();
}, { deep: true });

function initGraph() {
  const container = containerRef.value;
  if (!container) return;
  
  // 获取容器尺寸
  const rect = container.getBoundingClientRect();
  width = rect.width - 40; // 减去padding
  height = rect.height - 80; // 减去toolbar高度
  
  // 初始化SVG
  svg.value = d3.select(svgRef.value)
    .attr('width', width)
    .attr('height', height);
  
  // 初始化缩放
  zoom.value = d3.zoom()
    .scaleExtent([0.1, 3])
    .on('zoom', (event) => {
      svg.value.select('.zoom-container')
        .attr('transform', event.transform);
    });
  
  svg.value.call(zoom.value);
  
  // 监听窗口大小变化
  window.addEventListener('resize', handleResize);
}

function handleResize() {
  const container = containerRef.value;
  if (!container) return;
  
  const rect = container.getBoundingClientRect();
  width = rect.width - 40;
  height = rect.height - 80;
  
  svg.value
    .attr('width', width)
    .attr('height', height);
  
  renderGraph();
}

function renderGraph() {
  if (!svg.value || !props.lineageData.tables) return;
  
  const data = processLineageData();
  drawGraph(data);
  
  // 延迟调用适应屏幕，确保渲染完成
  setTimeout(() => {
    fitToScreen();
  }, 500);
}

function processLineageData() {
  const tables = props.lineageData.tables || {};
  const relationships = props.lineageData.relationships || [];
  const fieldMappings = props.lineageData.fieldMappings || [];
  
  console.log('前端处理血缘数据，表信息:', tables);
  console.log('字段映射信息:', fieldMappings);
  
  // 处理节点数据 - 按类型分组布局
  const sourceNodes = [];
  const targetNodes = [];
  const stageNodes = [];
  
  Object.entries(tables).forEach(([name, table]) => {
    const node = {
      id: name,
      name: table.table || name,
      type: table.type || 'stage',
      database: table.database || 'default',
      columns: table.columns || [],
      sqlType: table.sqlType || ''
    };
    
    console.log(`处理表 ${name}: 类型=${table.type}, 字段数=${node.columns.length}`, node.columns);
    
    switch (table.type) {
      case 'source':
        sourceNodes.push(node);
        break;
      case 'target':
        targetNodes.push(node);
        break;
      default:
        stageNodes.push(node);
        break;
    }
  });
  
  // 智能布局算法：动态计算节点大小和位置，避免碰撞
  const nodeWidth = 220;
  const baseNodeHeight = 50; // 基础高度（不包含字段）
  const fieldHeight = 24; // 每个字段的高度
  const padding = 60; // 减少padding以节省空间
  const minSpacing = 40; // 节点间最小间距
  
  const nodes = [];
  
  // 计算每个节点的实际高度
  const calculateNodeHeight = (node) => {
    const fieldCount = showFieldLevel.value ? (node.columns?.length || 0) : 0;
    return baseNodeHeight + fieldCount * fieldHeight;
  };
  
  // 智能垂直布局函数
  const layoutNodesVertically = (nodeList, startX) => {
    let currentY = padding;
    const maxContainerHeight = height - 2 * padding;
    
    // 计算所有节点的总高度
    const totalHeight = nodeList.reduce((sum, node) => {
      return sum + calculateNodeHeight(node) + minSpacing;
    }, 0) - minSpacing; // 减去最后一个节点的spacing
    
    // 如果总高度超过容器高度，使用紧凑布局
    const useCompactLayout = totalHeight > maxContainerHeight;
    let spacing = minSpacing;
    
    if (useCompactLayout) {
      // 压缩间距以适应容器
      spacing = Math.max(20, (maxContainerHeight - nodeList.reduce((sum, node) => sum + calculateNodeHeight(node), 0)) / (nodeList.length - 1 || 1));
    }
    
    nodeList.forEach((node, index) => {
      node.x = startX;
      node.y = currentY;
      nodes.push(node);
      
      const nodeHeight = calculateNodeHeight(node);
      currentY += nodeHeight + spacing;
      
      console.log(`布局节点 ${node.name}: x=${node.x}, y=${node.y}, height=${nodeHeight}`);
    });
  };
  
  // 为不同类型的节点分配X坐标
  const sourceX = padding;
  const targetX = width - nodeWidth - padding;
  const stageX = width / 2 - nodeWidth / 2;
  
  // 分别布局各类型节点
  if (sourceNodes.length > 0) {
    console.log(`布局 ${sourceNodes.length} 个源表节点`);
    layoutNodesVertically(sourceNodes, sourceX);
  }
  
  if (targetNodes.length > 0) {
    console.log(`布局 ${targetNodes.length} 个目标表节点`);
    layoutNodesVertically(targetNodes, targetX);
  }
  
  if (stageNodes.length > 0) {
    console.log(`布局 ${stageNodes.length} 个中间表节点`);
    layoutNodesVertically(stageNodes, stageX);
  }
  
  // 处理字段级连接 - 基于字段映射
  const fieldLinks = [];
  
  // 从relationships中提取字段映射
  relationships.forEach(rel => {
    if (rel.columns && rel.columns.length > 0) {
      rel.columns.forEach(colMapping => {
        fieldLinks.push({
          source: rel.source,
          target: rel.target,
          sourceField: colMapping.source,
          targetField: colMapping.target,
          expression: colMapping.expression || '',
          level: 'field'
        });
      });
    }
  });
  
  // 从fieldMappings中提取字段映射
  fieldMappings.forEach(mapping => {
    fieldLinks.push({
      source: mapping.sourceTable,
      target: mapping.targetTable,
      sourceField: mapping.sourceField,
      targetField: mapping.targetField,
      expression: mapping.expression || '',
      level: 'field'
    });
  });
  
  // 去重字段连接
  const uniqueFieldLinks = fieldLinks.filter((link, index) => {
    return fieldLinks.findIndex(l => 
      l.source === link.source && 
      l.target === link.target && 
      l.sourceField === link.sourceField && 
      l.targetField === link.targetField
    ) === index;
  });
  
  return { nodes, fieldLinks: uniqueFieldLinks };
}

// 存储当前数据以供拖拽时使用
let currentGraphData = null;

function drawGraph(data) {
  currentGraphData = data; // 存储数据
  const { nodes, fieldLinks } = data;
  
  // 清除现有元素
  svg.value.select('.links-container').selectAll('*').remove();
  svg.value.select('.field-links-container').selectAll('*').remove();
  svg.value.select('.nodes-container').selectAll('*').remove();
  
  // 不使用力导向图，直接使用固定位置布局
  // 因为我们已经在processLineageData中计算了位置
  
  // 绘制字段级连接线 - 改进样式
  const fieldLinksSelection = svg.value.select('.field-links-container')
    .selectAll('.field-link')
    .data(fieldLinks)
    .enter()
    .append('path')
    .attr('class', 'field-link')
    .attr('stroke', '#1976D2')
    .attr('stroke-width', 2)
    .attr('fill', 'none')
    .attr('marker-end', 'url(#arrowhead-field)')
    .attr('opacity', showFieldLevel.value ? 0.9 : 0)
    .attr('stroke-dasharray', '5,3');
  
  // 绘制表节点
  const nodeGroups = svg.value.select('.nodes-container')
    .selectAll('.node-group')
    .data(nodes)
    .enter()
    .append('g')
    .attr('class', 'node-group')
    .attr('transform', d => `translate(${d.x},${d.y})`)
    .call(d3.drag()
      .on('start', dragStarted)
      .on('drag', dragged)
      .on('end', dragEnded));
  
  // 表节点背景 - 动态计算高度
  nodeGroups.append('rect')
    .attr('class', 'table-node')
    .attr('width', 220)
    .attr('height', d => {
      const columns = d.columns || [];
      return 50 + (showFieldLevel.value ? columns.length * 24 : 0);
    })
    .attr('rx', 8)
    .attr('fill', d => getTableColor(d.type))
    .attr('stroke', d => getTableBorderColor(d.type))
    .attr('stroke-width', d => props.highlightedTables.has(d.name) ? 5 : 3)
    .attr('opacity', d => props.highlightedTables.size === 0 || props.highlightedTables.has(d.name) ? 1 : 0.3)
    .attr('filter', d => props.highlightedTables.has(d.name) ? 'url(#glow)' : 'none');
  
  // 表名
  nodeGroups.append('text')
    .attr('class', 'table-name')
    .attr('x', 110)
    .attr('y', 25)
    .attr('text-anchor', 'middle')
    .attr('fill', 'white')
    .attr('font-weight', 'bold')
    .attr('font-size', '14px')
    .text(d => d.name.length > 28 ? d.name.substring(0, 25) + '...' : d.name);
  
  // 表类型标签
  nodeGroups.append('text')
    .attr('class', 'table-type')
    .attr('x', 110)
    .attr('y', 40)
    .attr('text-anchor', 'middle')
    .attr('fill', 'rgba(255,255,255,0.8)')
    .attr('font-size', '10px')
    .text(d => getTableTypeLabel(d.type));
  
  // 字段列表 - 优化显示
  nodeGroups.each(function(d) {
    const group = d3.select(this);
    
    // 确保字段数据存在
    const columns = d.columns || [];
    
    // 总是显示字段，但根据showFieldLevel控制可见性
    columns.forEach((column, i) => {
      // 字段背景
      group.append('rect')
        .attr('class', 'field-row')
        .attr('data-field', column.name)
        .attr('x', 4)
        .attr('y', 55 + i * 24)
        .attr('width', 212)
        .attr('height', 22)
        .attr('fill', i % 2 === 0 ? 'rgba(255,255,255,0.15)' : 'rgba(255,255,255,0.08)')
        .attr('rx', 3)
        .attr('stroke', 'rgba(255,255,255,0.2)')
        .attr('stroke-width', 0.5)
        .style('display', showFieldLevel.value ? 'block' : 'none');
      
      // 字段名
      group.append('text')
        .attr('class', 'field-name')
        .attr('data-field', column.name)
        .attr('x', 10)
        .attr('y', 69 + i * 24)
        .attr('fill', 'white')
        .attr('font-size', '11px')
        .attr('font-family', 'monospace')
        .style('display', showFieldLevel.value ? 'block' : 'none')
        .text(() => {
          const fieldText = `${column.name}: ${column.type || 'unknown'}`;
          return fieldText.length > 32 ? fieldText.substring(0, 29) + '...' : fieldText;
        });
    });
  });
  
  // 添加点击事件
  nodeGroups.on('click', (event, d) => {
    emit('nodeClick', d);
  }).on('mouseenter', (event, d) => {
    emit('nodeHover', d);
  });
  
  // 绘制字段级连接线路径 - 使用统一的计算逻辑
  updateInitialFieldLinks();
  
  function updateInitialFieldLinks() {
    fieldLinksSelection
      .attr('d', d => {
        const sourceNode = nodes.find(n => n.id === d.source);
        const targetNode = nodes.find(n => n.id === d.target);
        
        if (!sourceNode || !targetNode) {
          console.warn(`初始绘制找不到节点: source=${d.source}, target=${d.target}`);
          return '';
        }
        
        const sourceColumns = sourceNode.columns || [];
        const targetColumns = targetNode.columns || [];
        
        const sourceFieldIndex = sourceColumns.findIndex(col => col.name === d.sourceField);
        const targetFieldIndex = targetColumns.findIndex(col => col.name === d.targetField);
        
        if (sourceFieldIndex === -1 || targetFieldIndex === -1) {
          console.warn(`初始绘制找不到字段: sourceField=${d.sourceField}(${sourceFieldIndex}), targetField=${d.targetField}(${targetFieldIndex})`);
          return '';
        }
        
        // 使用与拖动时相同的计算逻辑
        const nodeWidth = 220;
        const headerHeight = 50;
        const fieldHeight = 24;
        
        const sourceX = sourceNode.x + nodeWidth;
        const sourceY = sourceNode.y + headerHeight + sourceFieldIndex * fieldHeight + fieldHeight / 2;
        const targetX = targetNode.x;
        const targetY = targetNode.y + headerHeight + targetFieldIndex * fieldHeight + fieldHeight / 2;
        
        const dx = targetX - sourceX;
        const controlOffset = Math.max(50, Math.abs(dx) * 0.3);
        
        const cp1X = sourceX + controlOffset;
        const cp1Y = sourceY;
        const cp2X = targetX - controlOffset;
        const cp2Y = targetY;
        
        return `M ${sourceX},${sourceY} C ${cp1X},${cp1Y} ${cp2X},${cp2Y} ${targetX},${targetY}`;
      });
  }
}

function getTableColor(type) {
  switch (type) {
    case 'source': return '#4CAF50'; // 绿色 - 源表
    case 'target': return '#FF5722'; // 橙红色 - 目标表
    case 'stage': return '#2196F3';  // 蓝色 - 中间表
    default: return '#757575';       // 灰色 - 未知类型
  }
}

function getTableBorderColor(type) {
  switch (type) {
    case 'source': return '#2E7D32'; // 深绿色边框
    case 'target': return '#D84315'; // 深橙色边框
    case 'stage': return '#1565C0';  // 深蓝色边框
    default: return '#424242';       // 深灰色边框
  }
}

function getTableTypeLabel(type) {
  switch (type) {
    case 'source': return '源表 Source';
    case 'target': return '目标表 Target';
    case 'stage': return '中间表 Stage';
    default: return '未知 Unknown';
  }
}

function dragStarted(event, d) {
  // 拖拽开始时的逻辑
}

function dragged(event, d) {
  // 添加边界限制，防止节点拖出可视区域
  const nodeWidth = 220;
  const nodeHeight = 50 + (showFieldLevel.value ? (d.columns?.length || 0) * 24 : 0);
  const margin = 20;
  
  // 限制拖动范围
  d.x = Math.max(margin, Math.min(width - nodeWidth - margin, event.x));
  d.y = Math.max(margin, Math.min(height - nodeHeight - margin, event.y));
  
  // 更新节点位置
  const nodeGroup = d3.select(event.sourceEvent.target.parentNode);
  nodeGroup.attr('transform', `translate(${d.x},${d.y})`);
  
  // 重新绘制连接线 - 改进版本
  updateFieldConnections();
}

function updateFieldConnections() {
  if (!currentGraphData || !svg.value) return;
  
  try {
    svg.value.select('.field-links-container')
      .selectAll('.field-link')
      .attr('d', function(linkData) {
        const sourceNode = currentGraphData.nodes.find(n => n.id === linkData.source);
        const targetNode = currentGraphData.nodes.find(n => n.id === linkData.target);
        
        if (!sourceNode || !targetNode) {
          console.warn(`找不到节点: source=${linkData.source}, target=${linkData.target}`);
          return '';
        }
        
        // 查找字段索引
        const sourceColumns = sourceNode.columns || [];
        const targetColumns = targetNode.columns || [];
        
        const sourceFieldIndex = sourceColumns.findIndex(col => col.name === linkData.sourceField);
        const targetFieldIndex = targetColumns.findIndex(col => col.name === linkData.targetField);
        
        if (sourceFieldIndex === -1 || targetFieldIndex === -1) {
          console.warn(`找不到字段: sourceField=${linkData.sourceField}(${sourceFieldIndex}), targetField=${linkData.targetField}(${targetFieldIndex})`);
          return '';
        }
        
        // 计算连接点位置
        const nodeWidth = 220;
        const headerHeight = 50; // 表头高度
        const fieldHeight = 24; // 字段行高度
        
        const sourceX = sourceNode.x + nodeWidth; // 右边缘
        const sourceY = sourceNode.y + headerHeight + sourceFieldIndex * fieldHeight + fieldHeight / 2; // 字段中心
        const targetX = targetNode.x; // 左边缘
        const targetY = targetNode.y + headerHeight + targetFieldIndex * fieldHeight + fieldHeight / 2; // 字段中心
        
        // 生成贝塞尔曲线路径
        const dx = targetX - sourceX;
        const controlOffset = Math.max(50, Math.abs(dx) * 0.3); // 确保最小控制点偏移
        
        const cp1X = sourceX + controlOffset;
        const cp1Y = sourceY;
        const cp2X = targetX - controlOffset;
        const cp2Y = targetY;
        
        const path = `M ${sourceX},${sourceY} C ${cp1X},${cp1Y} ${cp2X},${cp2Y} ${targetX},${targetY}`;
        
        return path;
      });
  } catch (error) {
    console.error('更新字段连接时出错:', error);
  }
}

function dragEnded(event, d) {
  // 拖拽结束时的逻辑
  d.fx = null;
  d.fy = null;
}

function resetZoom() {
  svg.value.transition().duration(750).call(
    zoom.value.transform,
    d3.zoomIdentity
  );
}

function fitToScreen() {
  if (!currentGraphData || !currentGraphData.nodes || currentGraphData.nodes.length === 0) {
    console.warn('没有图形数据可以适应屏幕');
    return;
  }
  
  const nodes = currentGraphData.nodes;
  
  // 计算所有节点的实际边界
  const bounds = nodes.reduce((acc, node) => {
    const nodeHeight = 50 + (showFieldLevel.value ? (node.columns?.length || 0) * 24 : 0);
    const nodeWidth = 220;
    
    return {
      minX: Math.min(acc.minX, node.x),
      maxX: Math.max(acc.maxX, node.x + nodeWidth),
      minY: Math.min(acc.minY, node.y),
      maxY: Math.max(acc.maxY, node.y + nodeHeight)
    };
  }, { minX: Infinity, maxX: -Infinity, minY: Infinity, maxY: -Infinity });
  
  const graphWidth = bounds.maxX - bounds.minX;
  const graphHeight = bounds.maxY - bounds.minY;
  
  // 如果图形为空，使用默认视图
  if (graphWidth <= 0 || graphHeight <= 0) {
    svg.value.transition().duration(750).call(
      zoom.value.transform,
      d3.zoomIdentity
    );
    return;
  }
  
  // 添加边距
  const padding = 40;
  const totalWidth = graphWidth + 2 * padding;
  const totalHeight = graphHeight + 2 * padding;
  
  // 计算缩放比例，确保图形完全可见
  const scaleX = width / totalWidth;
  const scaleY = height / totalHeight;
  const scale = Math.min(scaleX, scaleY, 1); // 不放大，只缩小
  
  // 计算平移量，使图形居中
  const translateX = (width - totalWidth * scale) / 2 - bounds.minX * scale + padding * scale;
  const translateY = (height - totalHeight * scale) / 2 - bounds.minY * scale + padding * scale;
  
  console.log(`适应屏幕: 图形尺寸=${graphWidth}x${graphHeight}, 缩放=${scale}, 平移=(${translateX}, ${translateY})`);
  
  svg.value.transition().duration(750).call(
    zoom.value.transform,
    d3.zoomIdentity.translate(translateX, translateY).scale(scale)
  );
}

function toggleFieldLevel() {
  showFieldLevel.value = !showFieldLevel.value;
  renderGraph();
}

function updateHighlight() {
  if (!svg.value) return;
  
  // 更新节点高亮
  svg.value.selectAll('.table-node')
    .attr('stroke-width', function(d) {
      return props.highlightedTables.has(d.name) ? 5 : 3;
    })
    .attr('opacity', function(d) {
      return props.highlightedTables.size === 0 || props.highlightedTables.has(d.name) ? 1 : 0.3;
    })
    .attr('filter', function(d) {
      return props.highlightedTables.has(d.name) ? 'url(#glow)' : 'none';
    });
  
  // 更新文本高亮
  svg.value.selectAll('.table-name, .table-type, .field-name')
    .attr('opacity', function() {
      const nodeData = d3.select(this.parentNode).datum();
      return props.highlightedTables.size === 0 || props.highlightedTables.has(nodeData.name) ? 1 : 0.5;
    });
  
  // 更新连接线高亮
  svg.value.selectAll('.field-link')
    .attr('opacity', function(d) {
      const sourceHighlighted = props.highlightedTables.has(d.source);
      const targetHighlighted = props.highlightedTables.has(d.target);
      const baseOpacity = showFieldLevel.value ? 0.9 : 0;
      
      if (props.highlightedTables.size === 0) {
        return baseOpacity;
      }
      
      return (sourceHighlighted && targetHighlighted) ? baseOpacity : baseOpacity * 0.2;
    })
    .attr('stroke-width', function(d) {
      const sourceHighlighted = props.highlightedTables.has(d.source);
      const targetHighlighted = props.highlightedTables.has(d.target);
      
      return (sourceHighlighted && targetHighlighted) ? 3 : 2;
    });
}

function updateFieldLevelDisplay() {
  if (!svg.value) return;
  
  // 更新字段连接线的可见性
  svg.value.selectAll('.field-link')
    .transition()
    .duration(300)
    .attr('opacity', showFieldLevel.value ? 0.8 : 0);
  
  // 更新字段行的可见性
  svg.value.selectAll('.field-row')
    .transition()
    .duration(300)
    .style('display', showFieldLevel.value ? 'block' : 'none');
  
  svg.value.selectAll('.field-name')
    .transition()
    .duration(300)
    .style('display', showFieldLevel.value ? 'block' : 'none');
  
  // 更新节点高度
  svg.value.selectAll('.table-node')
    .transition()
    .duration(300)
    .attr('height', d => {
      const columns = d.columns || [];
      return 40 + (showFieldLevel.value ? columns.length * 22 : 0);
    });
}
</script>

<style scoped>
.lineage-graph-container {
  height: 100%;
  width: 100%;
  display: flex;
  flex-direction: column;
  background: white;
  border-radius: 8px;
}

.graph-toolbar {
  padding: 10px 15px;
  border-bottom: 1px solid #eee;
  display: flex;
  justify-content: space-between;
  align-items: center;
  background: #f8f9fa;
}

.legend {
  display: flex;
  gap: 20px;
  font-size: 12px;
}

.legend-item {
  display: flex;
  align-items: center;
  gap: 5px;
}

.legend-color {
  width: 12px;
  height: 12px;
  border-radius: 2px;
}

.legend-color.source {
  background: #4CAF50;
}

.legend-color.target {
  background: #FF5722;
}

.legend-color.stage {
  background: #2196F3;
}

.graph-area {
  flex: 1;
  position: relative;
  overflow: hidden;
}

.lineage-svg {
  width: 100%;
  height: 100%;
}

/* D3图形样式 */
.table-link {
  cursor: pointer;
}

.table-link:hover {
  stroke-width: 3;
  stroke: #409EFF;
}

.field-link {
  cursor: pointer;
}

.field-link:hover {
  stroke-width: 2;
  stroke: #409EFF;
}

.node-group {
  cursor: pointer;
}

.node-group:hover .table-node {
  stroke-width: 2;
  stroke: #409EFF;
}

.table-name {
  pointer-events: none;
}

.field-name {
  pointer-events: none;
}
</style>