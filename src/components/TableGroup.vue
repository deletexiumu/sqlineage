<template>
  <div class="table-group">
    <div class="group-header">
      <h4 class="group-title">
        <el-icon class="title-icon">
          <Document v-if="type === 'source'" />
          <Folder v-else />
        </el-icon>
        {{ title }}
        <el-tag :type="type === 'source' ? 'success' : 'danger'" size="small">
          {{ tables.length }}
        </el-tag>
      </h4>
    </div>
    
    <div class="group-content">
      <div 
        v-for="table in tables" 
        :key="table.name"
        class="table-item"
        :class="{
          'table-item-source': type === 'source',
          'table-item-target': type === 'target'
        }"
        @mouseenter="handleTableHover(table)"
        @mouseleave="handleTableLeave"
        @click="handleTableClick(table)"
      >
        <div class="table-item-header">
          <div class="table-name">
            <el-icon class="table-icon">
              <Grid />
            </el-icon>
            <span class="name-text">{{ table.name }}</span>
          </div>
          <el-tag 
            :type="getTableTagType(table.type)" 
            size="small"
            effect="plain"
          >
            {{ getTableTypeLabel(table.type) }}
          </el-tag>
        </div>
        
        <div class="table-item-info">
          <div class="info-item">
            <el-icon class="info-icon"><Document /></el-icon>
            <span>{{ table.columns?.length || 0 }} 字段</span>
          </div>
          <div v-if="table.database" class="info-item">
            <el-icon class="info-icon"><Folder /></el-icon>
            <span>{{ table.database }}</span>
          </div>
        </div>
        
        <div v-if="table.columns && table.columns.length > 0" class="table-columns">
          <div class="columns-header">
            <span>字段列表</span>
            <el-tag size="small" type="info">{{ table.columns.length }}</el-tag>
          </div>
          <div class="columns-list">
            <div 
              v-for="column in table.columns.slice(0, 5)" 
              :key="column.name"
              class="column-item"
            >
              <span class="column-name">{{ column.name }}</span>
              <span class="column-type">{{ column.type || 'string' }}</span>
            </div>
            <div v-if="table.columns.length > 5" class="more-columns">
              <span>... 还有 {{ table.columns.length - 5 }} 个字段</span>
            </div>
          </div>
        </div>
      </div>
      
      <div v-if="tables.length === 0" class="empty-group">
        <el-empty 
          :description="`暂无${getTableTypeLabel(type)}`" 
          :image-size="80"
        />
      </div>
    </div>
  </div>
</template>

<script setup>
import { defineEmits } from 'vue';
import { Document, Folder, Grid } from '@element-plus/icons-vue';

const props = defineProps({
  title: {
    type: String,
    required: true
  },
  tables: {
    type: Array,
    default: () => []
  },
  type: {
    type: String,
    required: true,
    validator: (value) => ['source', 'target', 'stage'].includes(value)
  }
});

const emit = defineEmits(['table-hover', 'table-click', 'table-leave']);

function handleTableHover(table) {
  emit('table-hover', table);
}

function handleTableClick(table) {
  emit('table-click', table);
}

function handleTableLeave() {
  emit('table-leave');
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
.table-group {
  margin-bottom: 20px;
}

.group-header {
  margin-bottom: 10px;
}

.group-title {
  display: flex;
  align-items: center;
  gap: 8px;
  margin: 0;
  font-size: 14px;
  color: #303133;
  font-weight: 500;
}

.title-icon {
  color: #909399;
}

.group-content {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.table-item {
  background: white;
  border: 1px solid #e4e7ed;
  border-radius: 8px;
  padding: 12px;
  cursor: pointer;
  transition: all 0.2s ease;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
}

.table-item:hover {
  border-color: #409eff;
  box-shadow: 0 2px 8px rgba(64, 158, 255, 0.2);
  transform: translateY(-1px);
}

.table-item-source:hover {
  border-color: #4CAF50;
  box-shadow: 0 2px 8px rgba(76, 175, 80, 0.2);
}

.table-item-target:hover {
  border-color: #FF5722;
  box-shadow: 0 2px 8px rgba(255, 87, 34, 0.2);
}

.table-item-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.table-name {
  display: flex;
  align-items: center;
  gap: 6px;
  flex: 1;
}

.table-icon {
  color: #909399;
  font-size: 14px;
}

.name-text {
  font-weight: 500;
  color: #303133;
  font-size: 13px;
}

.table-item-info {
  display: flex;
  gap: 12px;
  margin-bottom: 8px;
}

.info-item {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 12px;
  color: #666;
}

.info-icon {
  font-size: 12px;
  color: #909399;
}

.table-columns {
  margin-top: 8px;
  padding-top: 8px;
  border-top: 1px solid #f0f0f0;
}

.columns-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 6px;
  font-size: 12px;
  color: #666;
}

.columns-list {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.column-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 2px 0;
  font-size: 11px;
}

.column-name {
  color: #303133;
  font-weight: 400;
}

.column-type {
  color: #909399;
  font-size: 10px;
  background: #f5f7fa;
  padding: 1px 4px;
  border-radius: 2px;
}

.more-columns {
  text-align: center;
  color: #909399;
  font-size: 11px;
  padding: 4px 0;
  font-style: italic;
}

.empty-group {
  padding: 20px;
  text-align: center;
}
</style> 