<template>
  <div class="hive-connection">
    <el-card class="connection-card">
      <template #header>
        <span>Hive连接配置</span>
      </template>

      <el-form :model="connectionForm" :rules="connectionRules" ref="connectionFormRef" label-width="120px">
        <el-row :gutter="20">
          <el-col :span="12">
            <el-form-item label="服务器地址" prop="host">
              <el-input v-model="connectionForm.host" placeholder="localhost" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="端口" prop="port">
              <el-input-number v-model="connectionForm.port" :min="1" :max="65535" style="width: 100%" />
            </el-form-item>
          </el-col>
        </el-row>

        <el-row :gutter="20">
          <el-col :span="12">
            <el-form-item label="默认数据库" prop="database">
              <el-input v-model="connectionForm.database" placeholder="default" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="认证方式" prop="auth">
              <el-select v-model="connectionForm.auth" style="width: 100%">
                <el-option label="无认证" value="NONE" />
                <el-option label="Kerberos认证" value="KERBEROS" />
                <el-option label="LDAP认证" value="LDAP" />
              </el-select>
            </el-form-item>
          </el-col>
        </el-row>

        <el-row v-if="connectionForm.auth === 'LDAP'" :gutter="20">
          <el-col :span="12">
            <el-form-item label="用户名" prop="username">
              <el-input v-model="connectionForm.username" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="密码" prop="password">
              <el-input v-model="connectionForm.password" type="password" show-password />
            </el-form-item>
          </el-col>
        </el-row>

        <el-row v-if="connectionForm.auth === 'KERBEROS'">
          <el-col :span="12">
            <el-form-item label="服务名" prop="kerberos_service_name">
              <el-input v-model="connectionForm.kerberos_service_name" placeholder="hive" />
            </el-form-item>
          </el-col>
        </el-row>

        <el-form-item>
          <el-button type="primary" @click="testConnection" :loading="testing">
            测试连接
          </el-button>
          <el-button type="success" @click="loadDatabaseTree" :loading="loading" :disabled="!connectionTested">
            加载数据库结构
          </el-button>
        </el-form-item>
      </el-form>

      <!-- 连接测试结果 -->
      <el-alert
        v-if="connectionResult"
        :title="connectionResult.success ? '连接成功' : '连接失败'"
        :type="connectionResult.success ? 'success' : 'error'"
        :description="connectionResult.message || connectionResult.error"
        :closable="false"
        style="margin-top: 10px"
      />
    </el-card>

    <!-- 数据库结构树 -->
    <el-card v-if="treeData.length > 0" class="tree-card">
      <template #header>
        <div class="tree-header">
          <span>数据库结构</span>
          <div>
            <el-button size="small" @click="expandAll">全部展开</el-button>
            <el-button size="small" @click="collapseAll">全部收起</el-button>
            <el-button type="primary" size="small" @click="openSyncDialog" :disabled="selectedTables.length === 0">
              同步选中的表 ({{ selectedTables.length }})
            </el-button>
          </div>
        </div>
      </template>

      <el-tree
        ref="treeRef"
        :data="treeData"
        :props="treeProps"
        show-checkbox
        node-key="id"
        @check="handleTreeCheck"
        default-expand-all
      >
        <template #default="{ node, data }">
          <span class="tree-node">
            <el-icon v-if="data.type === 'database'">
              <Folder />
            </el-icon>
            <el-icon v-else>
              <Grid />
            </el-icon>
            {{ node.label }}
          </span>
        </template>
      </el-tree>
    </el-card>

    <!-- 同步对话框 -->
    <el-dialog v-model="syncDialogVisible" title="选择性同步元数据" width="600px">
      <el-form :model="syncForm" label-width="120px">
        <el-form-item label="同步模式">
          <el-radio-group v-model="syncForm.sync_mode">
            <el-radio value="add_only">仅添加新表</el-radio>
            <el-radio value="update_existing">更新已存在的表</el-radio>
            <el-radio value="full_sync">完全同步</el-radio>
          </el-radio-group>
        </el-form-item>

        <el-form-item label="选中的表">
          <el-tag
            v-for="table in selectedTables"
            :key="`${table.database}.${table.table}`"
            :closable="true"
            @close="removeSelectedTable(table)"
            style="margin: 2px"
          >
            {{ table.database }}.{{ table.table }}
          </el-tag>
        </el-form-item>
      </el-form>

      <template #footer>
        <div class="dialog-footer">
          <el-button @click="syncDialogVisible = false">取消</el-button>
          <el-button type="primary" @click="startSync" :loading="syncing">开始同步</el-button>
        </div>
      </template>
    </el-dialog>

    <!-- 同步结果对话框 -->
    <el-dialog v-model="syncResultDialogVisible" title="同步结果" width="500px">
      <el-result
        :icon="syncResult?.success ? 'success' : 'error'"
        :title="syncResult?.success ? '同步成功' : '同步失败'"
      >
        <template #sub-title>
          <div v-if="syncResult?.success && syncResult?.stats">
            <p>总计: {{ syncResult.stats.total }} 张表</p>
            <p>成功: {{ syncResult.stats.success }} 张表</p>
            <p>失败: {{ syncResult.stats.failed }} 张表</p>
            <p>跳过: {{ syncResult.stats.skipped }} 张表</p>
          </div>
        </template>
      </el-result>

      <!-- 错误信息 -->
      <div v-if="syncResult?.stats?.errors && syncResult.stats.errors.length > 0" class="sync-errors">
        <h4>同步错误：</h4>
        <el-alert
          v-for="(error, index) in syncResult.stats.errors"
          :key="index"
          :title="error"
          type="error"
          :closable="false"
          style="margin-bottom: 8px"
        />
      </div>

      <template #footer>
        <el-button type="primary" @click="syncResultDialogVisible = false">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive } from 'vue'
import { ElMessage, ElMessageBox, type ElTree } from 'element-plus'
import { Folder, Grid } from '@element-plus/icons-vue'
import { metadataAPI } from '../services/api'

const connectionFormRef = ref()
const treeRef = ref<InstanceType<typeof ElTree>>()
const testing = ref(false)
const loading = ref(false)
const syncing = ref(false)
const connectionTested = ref(false)
const connectionResult = ref<any>(null)
const treeData = ref<any[]>([])
const selectedTables = ref<any[]>([])
const syncDialogVisible = ref(false)
const syncResultDialogVisible = ref(false)
const syncResult = ref<any>(null)

const connectionForm = reactive({
  host: 'localhost',
  port: 10000,
  database: 'default',
  auth: 'NONE',
  username: '',
  password: '',
  kerberos_service_name: 'hive'
})

const syncForm = reactive({
  sync_mode: 'add_only'
})

const connectionRules = {
  host: [
    { required: true, message: '请输入服务器地址', trigger: 'blur' }
  ],
  port: [
    { required: true, message: '请输入端口号', trigger: 'blur' }
  ]
}

const treeProps = {
  children: 'children',
  label: 'label'
}

const testConnection = async () => {
  try {
    await connectionFormRef.value.validate()
  } catch {
    return
  }

  testing.value = true
  try {
    const response = await metadataAPI.testHiveConnection(connectionForm)
    connectionResult.value = response.data
    connectionTested.value = response.data.success
    
    if (response.data.success) {
      ElMessage.success('连接测试成功')
    } else {
      ElMessage.error('连接测试失败')
    }
  } catch (error: any) {
    console.error('连接测试失败:', error)
    connectionResult.value = {
      success: false,
      error: error.response?.data?.error || '连接测试失败'
    }
    ElMessage.error('连接测试失败')
  } finally {
    testing.value = false
  }
}

const loadDatabaseTree = async () => {
  loading.value = true
  try {
    const response = await metadataAPI.getHiveDatabaseTree(connectionForm)
    treeData.value = response.data.tree_data
    selectedTables.value = []
    ElMessage.success('数据库结构加载成功')
  } catch (error: any) {
    console.error('加载失败:', error)
    ElMessage.error(error.response?.data?.error || '数据库结构加载失败')
  } finally {
    loading.value = false
  }
}

const handleTreeCheck = (data: any, checked: any) => {
  // 只处理表级别的选择
  if (data.type === 'table') {
    const tableInfo = {
      database: data.database,
      table: data.table
    }
    
    if (checked.checkedKeys.includes(data.id)) {
      // 添加到选中列表
      const exists = selectedTables.value.some(
        t => t.database === tableInfo.database && t.table === tableInfo.table
      )
      if (!exists) {
        selectedTables.value.push(tableInfo)
      }
    } else {
      // 从选中列表移除
      selectedTables.value = selectedTables.value.filter(
        t => !(t.database === tableInfo.database && t.table === tableInfo.table)
      )
    }
  }
}

const expandAll = () => {
  const keys = []
  const getAllKeys = (nodes: any[]) => {
    nodes.forEach(node => {
      keys.push(node.id)
      if (node.children) {
        getAllKeys(node.children)
      }
    })
  }
  getAllKeys(treeData.value)
  treeRef.value?.setExpandedKeys(keys)
}

const collapseAll = () => {
  treeRef.value?.setExpandedKeys([])
}

const openSyncDialog = () => {
  syncDialogVisible.value = true
}

const removeSelectedTable = (table: any) => {
  selectedTables.value = selectedTables.value.filter(
    t => !(t.database === table.database && t.table === table.table)
  )
  
  // 同时取消树形控件中的选中状态
  const tableId = `table_${table.database}_${table.table}`
  const checkedKeys = treeRef.value?.getCheckedKeys() || []
  const newCheckedKeys = checkedKeys.filter(key => key !== tableId)
  treeRef.value?.setCheckedKeys(newCheckedKeys)
}

const startSync = async () => {
  if (selectedTables.value.length === 0) {
    ElMessage.warning('请先选择要同步的表')
    return
  }

  try {
    await ElMessageBox.confirm(
      `确认要同步 ${selectedTables.value.length} 张表吗？`,
      '确认同步',
      {
        confirmButtonText: '确认',
        cancelButtonText: '取消',
        type: 'warning',
      }
    )
  } catch {
    return
  }

  syncing.value = true
  try {
    const syncData = {
      connection_config: connectionForm,
      selected_tables: selectedTables.value,
      sync_mode: syncForm.sync_mode
    }

    const response = await metadataAPI.selectiveHiveSync(syncData)
    syncResult.value = response.data
    syncDialogVisible.value = false
    syncResultDialogVisible.value = true
    
    if (response.data.success) {
      ElMessage.success('元数据同步成功')
    } else {
      ElMessage.error('元数据同步失败')
    }
  } catch (error: any) {
    console.error('同步失败:', error)
    ElMessage.error(error.response?.data?.error || '同步失败')
  } finally {
    syncing.value = false
  }
}
</script>

<style scoped>
.hive-connection {
  padding: 20px;
}

.connection-card,
.tree-card {
  margin-bottom: 20px;
}

.tree-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.tree-header > div {
  display: flex;
  gap: 8px;
}

.tree-node {
  display: flex;
  align-items: center;
  gap: 6px;
}

.sync-errors {
  margin-top: 20px;
}

.sync-errors h4 {
  margin-bottom: 10px;
  color: #606266;
}

.dialog-footer {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
}
</style>