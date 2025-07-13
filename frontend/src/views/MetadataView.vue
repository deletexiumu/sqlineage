<template>
  <div class="metadata-view">
    <!-- 功能导航卡片 -->
    <el-card class="function-nav">
      <el-row :gutter="20">
        <el-col :span="8">
          <el-card shadow="hover" class="function-card" @click="activeTab = 'metadata'">
            <div class="function-content">
              <el-icon size="24"><Grid /></el-icon>
              <h3>元数据浏览</h3>
              <p>查看和管理数据库表信息</p>
            </div>
          </el-card>
        </el-col>
        <el-col :span="8">
          <el-card shadow="hover" class="function-card" @click="activeTab = 'import'">
            <div class="function-content">
              <el-icon size="24"><Upload /></el-icon>
              <h3>手动导入</h3>
              <p>从文件导入元数据信息</p>
            </div>
          </el-card>
        </el-col>
        <el-col :span="8">
          <el-card shadow="hover" class="function-card" @click="activeTab = 'hive'">
            <div class="function-content">
              <el-icon size="24"><Connection /></el-icon>
              <h3>Hive连接</h3>
              <p>连接Hive并选择性同步表</p>
            </div>
          </el-card>
        </el-col>
      </el-row>
    </el-card>

    <!-- 元数据管理标签页 -->
    <el-card v-show="activeTab === 'metadata'">
      <template #header>
        <div class="card-header">
          <span>元数据浏览</span>
          <div class="header-actions">
            <el-select v-model="selectedDatabase" placeholder="选择数据库" @change="loadTables" clearable>
              <el-option v-for="db in databases" :key="db" :label="db" :value="db" />
            </el-select>
            <el-input
              v-model="searchText"
              placeholder="搜索表名"
              @input="searchTables"
              style="width: 200px"
            >
              <template #prefix>
                <el-icon><Search /></el-icon>
              </template>
            </el-input>
            <el-button @click="loadDatabases" :loading="loading">
              <el-icon><Refresh /></el-icon>
              刷新
            </el-button>
            <el-dropdown @command="handleDeleteCommand">
              <el-button type="danger">
                <el-icon><Delete /></el-icon>
                删除操作
                <el-icon><ArrowDown /></el-icon>
              </el-button>
              <template #dropdown>
                <el-dropdown-menu>
                  <el-dropdown-item command="clearAll">清空所有元数据</el-dropdown-item>
                  <el-dropdown-item command="deleteDatabase" :disabled="!selectedDatabase">
                    删除数据库: {{ selectedDatabase || '请先选择数据库' }}
                  </el-dropdown-item>
                </el-dropdown-menu>
              </template>
            </el-dropdown>
          </div>
        </div>
      </template>

      <el-table :data="filteredTables" v-loading="loading" style="width: 100%">
        <el-table-column prop="database" label="数据库" width="150" />
        <el-table-column prop="name" label="表名" width="200" />
        <el-table-column label="列信息" min-width="300">
          <template #default="scope">
            <el-tag
              v-for="column in scope.row.columns.slice(0, 3)"
              :key="column.name"
              size="small"
              style="margin-right: 5px; margin-bottom: 5px"
            >
              {{ column.name }}:{{ column.type }}
            </el-tag>
            <span v-if="scope.row.columns.length > 3" class="more-columns">
              +{{ scope.row.columns.length - 3 }} more...
            </span>
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="创建时间" width="180">
          <template #default="scope">
            {{ formatDate(scope.row.created_at) }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="280">
          <template #default="scope">
            <div class="action-buttons">
              <el-button type="info" size="small" @click="viewTableDetails(scope.row)">
                查看详情
              </el-button>
              <el-button type="primary" size="small" @click="viewLineage(scope.row.full_name)">
                查看血缘
              </el-button>
              <el-button type="danger" size="small" @click="deleteTable(scope.row)" :loading="deletingTable">
                删除
              </el-button>
            </div>
          </template>
        </el-table-column>
      </el-table>

      <el-pagination
        v-if="tables.length > pageSize"
        v-model:current-page="currentPage"
        :page-size="pageSize"
        :total="tables.length"
        layout="total, prev, pager, next"
        style="margin-top: 20px; text-align: center"
      />
    </el-card>

    <!-- 手动导入标签页 -->
    <div v-show="activeTab === 'import'">
      <MetadataImport />
    </div>

    <!-- Hive连接标签页 -->
    <div v-show="activeTab === 'hive'">
      <HiveConnection />
    </div>

    <!-- 表详情弹窗 -->
    <el-dialog
      v-model="tableDetailsVisible"
      :title="`表详情: ${selectedTable?.full_name || ''}`"
      width="80%"
      :close-on-click-modal="false"
    >
      <div v-if="selectedTable" class="table-details">
        <el-descriptions :column="2" border>
          <el-descriptions-item label="表名">{{ selectedTable.name }}</el-descriptions-item>
          <el-descriptions-item label="数据库">{{ selectedTable.database }}</el-descriptions-item>
          <el-descriptions-item label="完整名称">{{ selectedTable.full_name }}</el-descriptions-item>
          <el-descriptions-item label="字段数量">{{ selectedTable.columns.length }}</el-descriptions-item>
          <el-descriptions-item label="创建时间">{{ formatDate(selectedTable.created_at) }}</el-descriptions-item>
          <el-descriptions-item label="更新时间">{{ formatDate(selectedTable.updated_at) }}</el-descriptions-item>
        </el-descriptions>

        <div class="columns-section">
          <h3>字段信息</h3>
          <el-input
            v-model="columnSearchText"
            placeholder="搜索字段名称或类型"
            style="width: 300px; margin-bottom: 15px"
          >
            <template #prefix>
              <el-icon><Search /></el-icon>
            </template>
          </el-input>
          
          <el-table :data="filteredColumns" style="width: 100%" height="400">
            <el-table-column prop="name" label="字段名" width="200" />
            <el-table-column prop="type" label="类型" width="150" />
            <el-table-column prop="comment" label="备注" min-width="300">
              <template #default="scope">
                <span v-if="scope.row.comment" class="column-comment">
                  {{ scope.row.comment }}
                </span>
                <span v-else class="no-comment">无备注</span>
              </template>
            </el-table-column>
          </el-table>
        </div>
      </div>
      
      <template #footer>
        <span class="dialog-footer">
          <el-button @click="tableDetailsVisible = false">关闭</el-button>
          <el-button type="primary" @click="copyTableSchema">复制表结构</el-button>
        </span>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { metadataAPI, type HiveTable } from '@/services/api'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Search, Refresh, Grid, Upload, Connection, Delete, ArrowDown } from '@element-plus/icons-vue'
import MetadataImport from '../components/MetadataImport.vue'
import HiveConnection from '../components/HiveConnection.vue'

const router = useRouter()

const activeTab = ref('metadata')
const loading = ref(false)
const tables = ref<HiveTable[]>([])
const databases = ref<string[]>([])
const selectedDatabase = ref('')
const searchText = ref('')
const currentPage = ref(1)
const pageSize = ref(20)
const deletingTable = ref(false)

// 表详情相关状态
const tableDetailsVisible = ref(false)
const selectedTable = ref<HiveTable | null>(null)
const columnSearchText = ref('')

const filteredTables = computed(() => {
  let filtered = tables.value
  
  if (selectedDatabase.value) {
    filtered = filtered.filter(table => table.database === selectedDatabase.value)
  }
  
  if (searchText.value) {
    filtered = filtered.filter(table => 
      table.name.toLowerCase().includes(searchText.value.toLowerCase()) ||
      table.database.toLowerCase().includes(searchText.value.toLowerCase())
    )
  }
  
  const start = (currentPage.value - 1) * pageSize.value
  const end = start + pageSize.value
  return filtered.slice(start, end)
})

// 过滤后的字段列表
const filteredColumns = computed(() => {
  if (!selectedTable.value || !selectedTable.value.columns) return []
  
  if (!columnSearchText.value) {
    return selectedTable.value.columns
  }
  
  return selectedTable.value.columns.filter(column => 
    column.name.toLowerCase().includes(columnSearchText.value.toLowerCase()) ||
    column.type.toLowerCase().includes(columnSearchText.value.toLowerCase()) ||
    (column.comment && column.comment.toLowerCase().includes(columnSearchText.value.toLowerCase()))
  )
})

const loadDatabases = async () => {
  try {
    const response = await metadataAPI.getDatabases()
    databases.value = response.data
  } catch (error) {
    console.error('Load databases error:', error)
    ElMessage.error('加载数据库列表失败')
  }
}

const loadTables = async () => {
  loading.value = true
  try {
    const params: any = {}
    if (selectedDatabase.value) {
      params.database = selectedDatabase.value
    }
    
    const response = await metadataAPI.getTables(params)
    tables.value = response.data
  } catch (error) {
    console.error('Load tables error:', error)
    ElMessage.error('加载表列表失败')
  } finally {
    loading.value = false
  }
}

const searchTables = async () => {
  if (searchText.value.length >= 2) {
    await loadTables()
  }
}

const viewLineage = (tableName: string) => {
  router.push({ name: 'lineage', query: { table: tableName } })
}

const formatDate = (dateString: string) => {
  return new Date(dateString).toLocaleString()
}

// 删除操作处理
const handleDeleteCommand = (command: string) => {
  if (command === 'clearAll') {
    clearAllMetadata()
  } else if (command === 'deleteDatabase') {
    deleteDatabase()
  }
}

const clearAllMetadata = async () => {
  ElMessageBox.confirm(
    '确定要清空所有元数据吗？这将删除所有表信息、业务映射和血缘关系，操作不可逆！',
    '清空所有元数据',
    {
      confirmButtonText: '确定清空',
      cancelButtonText: '取消',
      type: 'warning',
      dangerouslyUseHTMLString: false,
    }
  ).then(async () => {
    try {
      loading.value = true
      const response = await metadataAPI.clearAllMetadata()
      
      if (response.data.success) {
        ElMessage.success(`清空成功！删除了 ${response.data.deleted_counts.tables} 个表，${response.data.deleted_counts.lineage_relations} 条血缘关系`)
        await loadDatabases()
        await loadTables()
      } else {
        ElMessage.error(response.data.error || '清空失败')
      }
    } catch (error: any) {
      console.error('Clear all metadata error:', error)
      ElMessage.error(error?.response?.data?.error || '清空失败')
    } finally {
      loading.value = false
    }
  }).catch(() => {
    ElMessage.info('已取消清空操作')
  })
}

const deleteDatabase = async () => {
  if (!selectedDatabase.value) {
    ElMessage.warning('请先选择要删除的数据库')
    return
  }

  ElMessageBox.confirm(
    `确定要删除数据库 "${selectedDatabase.value}" 的所有表信息和相关血缘关系吗？操作不可逆！`,
    '删除数据库',
    {
      confirmButtonText: '确定删除',
      cancelButtonText: '取消',
      type: 'warning',
    }
  ).then(async () => {
    try {
      loading.value = true
      const response = await metadataAPI.deleteDatabase(selectedDatabase.value)
      
      if (response.data.success) {
        ElMessage.success(`删除成功！删除了 ${response.data.deleted_counts.tables} 个表，${response.data.deleted_counts.lineage_relations} 条血缘关系`)
        selectedDatabase.value = ''
        await loadDatabases()
        await loadTables()
      } else {
        ElMessage.error(response.data.error || '删除失败')
      }
    } catch (error: any) {
      console.error('Delete database error:', error)
      ElMessage.error(error?.response?.data?.error || '删除失败')
    } finally {
      loading.value = false
    }
  }).catch(() => {
    ElMessage.info('已取消删除操作')
  })
}

const deleteTable = async (table: HiveTable) => {
  ElMessageBox.confirm(
    `确定要删除表 "${table.full_name}" 和相关血缘关系吗？操作不可逆！`,
    '删除表',
    {
      confirmButtonText: '确定删除',
      cancelButtonText: '取消',
      type: 'warning',
    }
  ).then(async () => {
    try {
      deletingTable.value = true
      const response = await metadataAPI.deleteTable(table.database, table.name)
      
      if (response.data.success) {
        ElMessage.success(`删除成功！删除了表和 ${response.data.deleted_counts.lineage_relations} 条血缘关系`)
        await loadTables()
        await loadDatabases()
      } else {
        ElMessage.error(response.data.error || '删除失败')
      }
    } catch (error: any) {
      console.error('Delete table error:', error)
      ElMessage.error(error?.response?.data?.error || '删除失败')
    } finally {
      deletingTable.value = false
    }
  }).catch(() => {
    ElMessage.info('已取消删除操作')
  })
}

// 查看表详情
const viewTableDetails = (table: HiveTable) => {
  selectedTable.value = table
  columnSearchText.value = ''
  tableDetailsVisible.value = true
}

// 复制表结构
const copyTableSchema = async () => {
  if (!selectedTable.value) return
  
  try {
    const schema = selectedTable.value.columns.map(column => 
      `${column.name}\t${column.type}\t${column.comment || ''}`
    ).join('\n')
    
    const tableInfo = `表名: ${selectedTable.value.full_name}\n数据库: ${selectedTable.value.database}\n字段数量: ${selectedTable.value.columns.length}\n\n字段信息:\n字段名\t类型\t备注\n${schema}`
    
    await navigator.clipboard.writeText(tableInfo)
    ElMessage.success('表结构已复制到剪贴板')
  } catch (error) {
    console.error('Copy table schema error:', error)
    // 降级到传统方法
    try {
      const textArea = document.createElement('textarea')
      const schema = selectedTable.value!.columns.map(column => 
        `${column.name}\t${column.type}\t${column.comment || ''}`
      ).join('\n')
      const tableInfo = `表名: ${selectedTable.value!.full_name}\n数据库: ${selectedTable.value!.database}\n字段数量: ${selectedTable.value!.columns.length}\n\n字段信息:\n字段名\t类型\t备注\n${schema}`
      
      textArea.value = tableInfo
      document.body.appendChild(textArea)
      textArea.select()
      document.execCommand('copy')
      document.body.removeChild(textArea)
      ElMessage.success('表结构已复制到剪贴板')
    } catch (fallbackError) {
      ElMessage.error('复制失败，请手动复制')
    }
  }
}

onMounted(() => {
  loadDatabases()
  loadTables()
})
</script>

<style scoped>
.metadata-view {
  padding: 20px;
  height: 100%;
  overflow: auto;
}

.function-nav {
  margin-bottom: 20px;
}

.function-card {
  cursor: pointer;
  transition: all 0.3s ease;
  height: 120px;
}

.function-card:hover {
  transform: translateY(-5px);
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.1);
}

.function-content {
  text-align: center;
  padding: 10px;
}

.function-content h3 {
  margin: 10px 0 5px 0;
  color: #303133;
  font-size: 16px;
}

.function-content p {
  margin: 0;
  color: #909399;
  font-size: 12px;
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

.more-columns {
  color: #909399;
  font-size: 12px;
}

.action-buttons {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

/* 表详情弹窗样式 */
.table-details {
  padding: 10px 0;
}

.columns-section {
  margin-top: 20px;
}

.columns-section h3 {
  margin-bottom: 15px;
  color: #303133;
  font-size: 16px;
  font-weight: 600;
}

.column-comment {
  color: #606266;
  word-break: break-all;
}

.no-comment {
  color: #c0c4cc;
  font-style: italic;
}

.dialog-footer {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
}

/* 响应式设计 */
@media (max-width: 768px) {
  .metadata-view {
    padding: 10px;
  }
  
  .card-header {
    flex-direction: column;
    align-items: stretch;
  }
  
  .header-actions {
    justify-content: center;
  }
  
  :deep(.el-table) {
    font-size: 12px;
  }
  
  :deep(.el-table th) {
    padding: 8px 5px;
  }
  
  :deep(.el-table td) {
    padding: 8px 5px;
  }
}

@media (max-width: 480px) {
  .metadata-view {
    padding: 5px;
  }
  
  .header-actions {
    flex-direction: column;
    align-items: stretch;
  }
  
  .header-actions .el-select,
  .header-actions .el-input {
    width: 100% !important;
  }
  
  :deep(.el-table) {
    font-size: 11px;
  }
  
  :deep(.el-table .el-table__cell) {
    padding: 6px 3px;
  }
  
  :deep(.el-tag) {
    margin: 2px;
    font-size: 10px;
  }
  
  :deep(.el-button--small) {
    padding: 4px 8px;
    font-size: 11px;
  }
}

/* 隐藏部分列在小屏幕上 */
@media (max-width: 576px) {
  :deep(.el-table__column:nth-child(4)) {
    display: none;
  }
}
</style>