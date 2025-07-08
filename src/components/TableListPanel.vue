<template>
  <div class="table-list-panel">
    <div class="panel-header">
      <h3>表血缘浏览</h3>
      <div class="header-actions">
        <el-input
          v-model="searchText"
          placeholder="搜索表名..."
          prefix-icon="Search"
          size="small"
          clearable
          @input="handleSearch"
        />
      </div>
    </div>

    <div class="panel-content">
      <!-- 统计信息 -->
      <div class="summary-cards">
        <el-row :gutter="10">
          <el-col :span="8">
            <div class="summary-card source">
              <div class="card-header">
                <el-icon><Document /></el-icon>
                <span>源表</span>
              </div>
              <div class="card-value">{{ filteredSourceTables.length }}</div>
            </div>
          </el-col>
          <el-col :span="8">
            <div class="summary-card target">
              <div class="card-header">
                <el-icon><Folder /></el-icon>
                <span>目标表</span>
              </div>
              <div class="card-value">{{ filteredTargetTables.length }}</div>
            </div>
          </el-col>
          <el-col :span="8">
            <div class="summary-card mapping">
              <div class="card-header">
                <el-icon><Connection /></el-icon>
                <span>映射</span>
              </div>
              <div class="card-value">{{ totalMappings }}</div>
            </div>
          </el-col>
        </el-row>
      </div>

      <!-- 表类型切换 -->
      <div class="type-tabs">
        <el-tabs v-model="activeTab" @tab-change="handleTabChange">
          <el-tab-pane label="全部" name="all">
            <div class="table-section">
              <TableGroup
                title="源表"
                :tables="filteredSourceTables"
                type="source"
                @table-hover="handleTableHover"
                @table-click="handleTableClick"
                @table-leave="handleTableLeave"
              />
              <TableGroup
                title="目标表"
                :tables="filteredTargetTables"
                type="target"
                @table-hover="handleTableHover"
                @table-click="handleTableClick"
                @table-leave="handleTableLeave"
              />
            </div>
          </el-tab-pane>
          <el-tab-pane label="源表" name="source">
            <TableGroup
              title="源表"
              :tables="filteredSourceTables"
              type="source"
              @table-hover="handleTableHover"
              @table-click="handleTableClick"
              @table-leave="handleTableLeave"
            />
          </el-tab-pane>
          <el-tab-pane label="目标表" name="target">
            <TableGroup
              title="目标表"
              :tables="filteredTargetTables"
              type="target"
              @table-hover="handleTableHover"
              @table-click="handleTableClick"
              @table-leave="handleTableLeave"
            />
          </el-tab-pane>
        </el-tabs>
      </div>
    </div>

    <!-- 血缘关系弹窗 -->
    <el-dialog
      v-model="showLineageDialog"
      :title="`${selectedTable?.name} 的血缘关系`"
      width="60%"
      :before-close="handleCloseDialog"
    >
      <div class="lineage-dialog-content">
        <div v-if="selectedTable" class="table-info">
          <div class="table-details">
            <h4>表信息</h4>
            <el-descriptions :column="2" border>
              <el-descriptions-item label="表名">{{ selectedTable.name }}</el-descriptions-item>
              <el-descriptions-item label="类型">{{ getTableTypeLabel(selectedTable.type) }}</el-descriptions-item>
              <el-descriptions-item label="字段数量">{{ selectedTable.columns?.length || 0 }}</el-descriptions-item>
              <el-descriptions-item label="数据库">{{ selectedTable.database || 'default' }}</el-descriptions-item>
            </el-descriptions>
          </div>

          <div class="lineage-details">
            <h4>血缘关系</h4>
            <el-tabs v-model="lineageTab">
              <el-tab-pane label="上游依赖" name="upstream">
                <div v-if="upstreamTables.length > 0" class="related-tables">
                  <div v-for="table in upstreamTables" :key="table.name" class="related-table-item">
                    <el-tag :type="getTableTagType(table.type)" size="small">{{ getTableTypeLabel(table.type) }}</el-tag>
                    <span class="table-name">{{ table.name }}</span>
                    <span class="field-count">({{ table.columns?.length || 0 }} 字段)</span>
                  </div>
                </div>
                <el-empty v-else description="无上游依赖" :image-size="60" />
              </el-tab-pane>
              <el-tab-pane label="下游影响" name="downstream">
                <div v-if="downstreamTables.length > 0" class="related-tables">
                  <div v-for="table in downstreamTables" :key="table.name" class="related-table-item">
                    <el-tag :type="getTableTagType(table.type)" size="small">{{ getTableTypeLabel(table.type) }}</el-tag>
                    <span class="table-name">{{ table.name }}</span>
                    <span class="field-count">({{ table.columns?.length || 0 }} 字段)</span>
                  </div>
                </div>
                <el-empty v-else description="无下游影响" :image-size="60" />
              </el-tab-pane>
              <el-tab-pane label="字段映射" name="mappings">
                <div v-if="relatedMappings.length > 0" class="field-mappings">
                  <div v-for="mapping in relatedMappings" :key="`${mapping.sourceTable}.${mapping.sourceField}-${mapping.targetTable}.${mapping.targetField}`" class="mapping-item">
                    <div class="mapping-row">
                      <span class="source-field">{{ mapping.sourceTable }}.{{ mapping.sourceField }}</span>
                      <el-icon class="arrow-icon"><Right /></el-icon>
                      <span class="target-field">{{ mapping.targetTable }}.{{ mapping.targetField }}</span>
                    </div>
                    <div v-if="mapping.expression" class="mapping-expression">
                      <el-tag size="small" type="info">{{ mapping.expression }}</el-tag>
                    </div>
                  </div>
                </div>
                <el-empty v-else description="无字段映射" :image-size="60" />
              </el-tab-pane>
            </el-tabs>
          </div>
        </div>
      </div>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, watch, defineEmits } from 'vue';
import { Document, Folder, Connection, Right } from '@element-plus/icons-vue';
import TableGroup from './TableGroup.vue';

const props = defineProps({
  lineageData: {
    type: Object,
    default: () => ({})
  }
});

const emit = defineEmits(['table-hover', 'table-click', 'table-leave', 'highlight-lineage']);

// 响应式数据
const searchText = ref('');
const activeTab = ref('all');
const lineageTab = ref('upstream');
const showLineageDialog = ref(false);
const selectedTable = ref(null);

// 计算属性
const allTables = computed(() => {
  const tables = props.lineageData.tables || {};
  return Object.entries(tables).map(([name, table]) => ({
    name,
    ...table,
    id: name
  }));
});

const sourceTables = computed(() => {
  return allTables.value.filter(table => table.type === 'source');
});

const targetTables = computed(() => {
  return allTables.value.filter(table => table.type === 'target');
});

const filteredSourceTables = computed(() => {
  if (!searchText.value) return sourceTables.value;
  return sourceTables.value.filter(table => 
    table.name.toLowerCase().includes(searchText.value.toLowerCase())
  );
});

const filteredTargetTables = computed(() => {
  if (!searchText.value) return targetTables.value;
  return targetTables.value.filter(table => 
    table.name.toLowerCase().includes(searchText.value.toLowerCase())
  );
});

const totalMappings = computed(() => {
  return props.lineageData.fieldMappings?.length || 0;
});

const relationships = computed(() => {
  return props.lineageData.relationships || [];
});

const fieldMappings = computed(() => {
  return props.lineageData.fieldMappings || [];
});

// 选中表的上游表
const upstreamTables = computed(() => {
  if (!selectedTable.value) return [];
  
  const upstreamNames = new Set();
  
  // 从关系中查找上游
  relationships.value.forEach(rel => {
    if (rel.target === selectedTable.value.name) {
      upstreamNames.add(rel.source);
    }
  });
  
  // 从字段映射中查找上游
  fieldMappings.value.forEach(mapping => {
    if (mapping.targetTable === selectedTable.value.name) {
      upstreamNames.add(mapping.sourceTable);
    }
  });
  
  return allTables.value.filter(table => upstreamNames.has(table.name));
});

// 选中表的下游表
const downstreamTables = computed(() => {
  if (!selectedTable.value) return [];
  
  const downstreamNames = new Set();
  
  // 从关系中查找下游
  relationships.value.forEach(rel => {
    if (rel.source === selectedTable.value.name) {
      downstreamNames.add(rel.target);
    }
  });
  
  // 从字段映射中查找下游
  fieldMappings.value.forEach(mapping => {
    if (mapping.sourceTable === selectedTable.value.name) {
      downstreamNames.add(mapping.targetTable);
    }
  });
  
  return allTables.value.filter(table => downstreamNames.has(table.name));
});

// 选中表的相关字段映射
const relatedMappings = computed(() => {
  if (!selectedTable.value) return [];
  
  return fieldMappings.value.filter(mapping => 
    mapping.sourceTable === selectedTable.value.name || 
    mapping.targetTable === selectedTable.value.name
  );
});

// 方法
function handleSearch() {
  // 搜索逻辑已在计算属性中处理
}

function handleTabChange(tabName) {
  activeTab.value = tabName;
}

function handleTableHover(table) {
  emit('table-hover', table);
  // 计算该表的相关血缘表
  const relatedTableNames = findRelatedTables(table);
  emit('highlight-lineage', { table, relatedTables: [...relatedTableNames, table.name] });
}

function findRelatedTables(table) {
  const relatedTables = [];
  const relationships = props.lineageData.relationships || [];
  const fieldMappings = props.lineageData.fieldMappings || [];
  
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

function handleTableClick(table) {
  selectedTable.value = table;
  showLineageDialog.value = true;
  emit('table-click', table);
}

function handleTableLeave() {
  emit('table-leave');
  emit('highlight-lineage', null); // 清除高亮
}

function handleCloseDialog() {
  showLineageDialog.value = false;
  selectedTable.value = null;
}

function getTableTypeLabel(type) {
  switch (type) {
    case 'source': return '源表';
    case 'target': return '目标表';
    case 'stage': return '中间表';
    default: return '未知';
  }
}

function getTableTagType(type) {
  switch (type) {
    case 'source': return 'success';
    case 'target': return 'danger';
    case 'stage': return 'primary';
    default: return 'info';
  }
}
</script>

<style scoped>
.table-list-panel {
  height: 100%;
  display: flex;
  flex-direction: column;
  background: white;
  border-radius: 8px;
}

.panel-header {
  padding: 15px 20px;
  border-bottom: 1px solid #ebeef5;
  background: #f8f9fa;
  border-radius: 8px 8px 0 0;
}

.panel-header h3 {
  margin: 0 0 10px 0;
  color: #303133;
  font-size: 16px;
}

.header-actions {
  display: flex;
  gap: 10px;
}

.panel-content {
  flex: 1;
  padding: 15px 20px;
  overflow-y: auto;
}

.summary-cards {
  margin-bottom: 20px;
}

.summary-card {
  padding: 15px;
  border-radius: 8px;
  text-align: center;
  border: 2px solid;
}

.summary-card.source {
  background: #f0f9ff;
  border-color: #4CAF50;
  color: #2E7D32;
}

.summary-card.target {
  background: #fff7ed;
  border-color: #FF5722;
  color: #D84315;
}

.summary-card.mapping {
  background: #f3f4f6;
  border-color: #2196F3;
  color: #1565C0;
}

.card-header {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 5px;
  font-size: 12px;
  margin-bottom: 8px;
}

.card-value {
  font-size: 20px;
  font-weight: bold;
}

.type-tabs {
  flex: 1;
}

.table-section {
  max-height: 400px;
  overflow-y: auto;
}

.lineage-dialog-content {
  max-height: 500px;
  overflow-y: auto;
}

.table-details {
  margin-bottom: 20px;
}

.table-details h4,
.lineage-details h4 {
  margin: 0 0 15px 0;
  color: #303133;
  font-size: 14px;
}

.related-tables {
  max-height: 200px;
  overflow-y: auto;
}

.related-table-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 0;
  border-bottom: 1px solid #f0f0f0;
}

.related-table-item:last-child {
  border-bottom: none;
}

.table-name {
  font-weight: 500;
  color: #303133;
}

.field-count {
  color: #909399;
  font-size: 12px;
}

.field-mappings {
  max-height: 300px;
  overflow-y: auto;
}

.mapping-item {
  padding: 10px 0;
  border-bottom: 1px solid #f0f0f0;
}

.mapping-item:last-child {
  border-bottom: none;
}

.mapping-row {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 5px;
}

.source-field {
  color: #4CAF50;
  font-weight: 500;
}

.target-field {
  color: #FF5722;
  font-weight: 500;
}

.arrow-icon {
  color: #909399;
}

.mapping-expression {
  font-size: 12px;
  color: #666;
}
</style> 