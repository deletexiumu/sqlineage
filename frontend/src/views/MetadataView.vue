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
        <el-table-column label="操作" width="150">
          <template #default="scope">
            <el-button type="primary" size="small" @click="viewLineage(scope.row.full_name)">
              查看血缘
            </el-button>
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
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { metadataAPI, type HiveTable } from '@/services/api'
import { ElMessage } from 'element-plus'
import { Search, Refresh, Grid, Upload, Connection } from '@element-plus/icons-vue'
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