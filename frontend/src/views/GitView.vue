<template>
  <div class="git-view">
    <el-row :gutter="20">
      <!-- Git仓库列表 -->
      <el-col :span="12">
        <el-card>
          <template #header>
            <div class="card-header">
              <span>Git仓库</span>
              <el-button type="primary" @click="showAddRepo = true">
                <el-icon><Plus /></el-icon>
                添加仓库
              </el-button>
            </div>
          </template>

          <el-table :data="repos" v-loading="loading">
            <el-table-column prop="name" label="仓库名称" />
            <el-table-column prop="branch" label="分支" width="100" />
            <el-table-column label="状态" width="80">
              <template #default="scope">
                <el-tag :type="scope.row.is_active ? 'success' : 'danger'">
                  {{ scope.row.is_active ? '活跃' : '禁用' }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column label="最后同步" width="180">
              <template #default="scope">
                {{ scope.row.last_sync ? formatDate(scope.row.last_sync) : '未同步' }}
              </template>
            </el-table-column>
            <el-table-column label="操作" width="200">
              <template #default="scope">
                <el-button size="small" @click="syncRepo(scope.row)" :loading="syncingRepos.has(scope.row.id)">
                  同步
                </el-button>
                <el-button size="small" @click="parseRepo(scope.row)" :loading="parsingRepos.has(scope.row.id)">
                  解析血缘
                </el-button>
              </template>
            </el-table-column>
          </el-table>
        </el-card>
      </el-col>

      <!-- 解析任务 -->
      <el-col :span="12">
        <el-card>
          <template #header>
            <div class="card-header">
              <span>解析任务</span>
              <el-button @click="loadJobs" :loading="jobsLoading">
                <el-icon><Refresh /></el-icon>
                刷新
              </el-button>
            </div>
          </template>

          <el-table :data="jobs" v-loading="jobsLoading">
            <el-table-column prop="git_repo_name" label="仓库" />
            <el-table-column label="状态" width="100">
              <template #default="scope">
                <el-tag :type="getJobStatusType(scope.row.status)">
                  {{ getJobStatusText(scope.row.status) }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column label="进度" width="150">
              <template #default="scope">
                <el-progress 
                  :percentage="scope.row.progress_percentage" 
                  :status="scope.row.status === 'failed' ? 'exception' : undefined"
                  size="small"
                />
                <div style="font-size: 12px; color: #666;">
                  {{ scope.row.processed_files }}/{{ scope.row.total_files }}
                </div>
              </template>
            </el-table-column>
            <el-table-column prop="created_at" label="创建时间" width="150">
              <template #default="scope">
                {{ formatDate(scope.row.created_at) }}
              </template>
            </el-table-column>
          </el-table>
        </el-card>
      </el-col>
    </el-row>

    <!-- 添加仓库对话框 -->
    <el-dialog v-model="showAddRepo" title="添加Git仓库" width="500px">
      <el-form :model="newRepo" label-width="100px">
        <el-form-item label="仓库名称">
          <el-input v-model="newRepo.name" placeholder="输入仓库名称" />
        </el-form-item>
        <el-form-item label="仓库URL">
          <el-input v-model="newRepo.repo_url" placeholder="https://github.com/user/repo.git" />
        </el-form-item>
        <el-form-item label="用户名">
          <el-input v-model="newRepo.username" placeholder="Git用户名" />
        </el-form-item>
        <el-form-item label="密码">
          <el-input v-model="newRepo.password" type="password" placeholder="Git密码或Token" />
        </el-form-item>
        <el-form-item label="分支">
          <el-input v-model="newRepo.branch" placeholder="main" />
        </el-form-item>
        <el-form-item label="SSL验证">
          <el-switch 
            v-model="newRepo.ssl_verify" 
            active-text="启用"
            inactive-text="禁用"
          />
          <div style="font-size: 12px; color: #666; margin-top: 5px;">
            内网私有GitLab建议禁用SSL验证
          </div>
        </el-form-item>
      </el-form>
      
      <template #footer>
        <el-button @click="showAddRepo = false">取消</el-button>
        <el-button type="primary" @click="addRepo" :loading="adding">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { gitAPI, lineageAPI, type GitRepo, type LineageParseJob } from '@/services/api'
import { ElMessage } from 'element-plus'
import { Plus, Refresh } from '@element-plus/icons-vue'

const loading = ref(false)
const jobsLoading = ref(false)
const adding = ref(false)
const showAddRepo = ref(false)
const repos = ref<GitRepo[]>([])
const jobs = ref<LineageParseJob[]>([])
const syncingRepos = ref(new Set<number>())
const parsingRepos = ref(new Set<number>())

const newRepo = ref({
  name: '',
  repo_url: '',
  username: '',
  password: '',
  branch: 'main',
  ssl_verify: true,
})

const loadRepos = async () => {
  loading.value = true
  try {
    const response = await gitAPI.getRepos()
    repos.value = response.data
  } catch (error) {
    console.error('Load repos error:', error)
    ElMessage.error('加载仓库列表失败')
  } finally {
    loading.value = false
  }
}

const loadJobs = async () => {
  jobsLoading.value = true
  try {
    const response = await lineageAPI.getJobs()
    jobs.value = response.data
  } catch (error) {
    console.error('Load jobs error:', error)
    ElMessage.error('加载任务列表失败')
  } finally {
    jobsLoading.value = false
  }
}

const addRepo = async () => {
  if (!newRepo.value.name || !newRepo.value.repo_url || !newRepo.value.username || !newRepo.value.password) {
    ElMessage.warning('请填写完整信息')
    return
  }

  adding.value = true
  try {
    await gitAPI.createRepo(newRepo.value)
    ElMessage.success('仓库添加成功')
    showAddRepo.value = false
    newRepo.value = { name: '', repo_url: '', username: '', password: '', branch: 'main', ssl_verify: true }
    await loadRepos()
  } catch (error) {
    console.error('Add repo error:', error)
    ElMessage.error('添加仓库失败')
  } finally {
    adding.value = false
  }
}

const syncRepo = async (repo: GitRepo) => {
  syncingRepos.value.add(repo.id)
  try {
    await gitAPI.syncRepo(repo.id)
    ElMessage.success('仓库同步成功')
    await loadRepos()
  } catch (error) {
    console.error('Sync repo error:', error)
    ElMessage.error('仓库同步失败')
  } finally {
    syncingRepos.value.delete(repo.id)
  }
}

const parseRepo = async (repo: GitRepo) => {
  parsingRepos.value.add(repo.id)
  try {
    await lineageAPI.parseRepo(repo.id)
    ElMessage.success('血缘解析任务已启动')
    await loadJobs()
  } catch (error) {
    console.error('Parse repo error:', error)
    ElMessage.error('启动血缘解析失败')
  } finally {
    parsingRepos.value.delete(repo.id)
  }
}

const getJobStatusType = (status: string) => {
  switch (status) {
    case 'completed': return 'success'
    case 'failed': return 'danger'
    case 'running': return 'warning'
    default: return 'info'
  }
}

const getJobStatusText = (status: string) => {
  switch (status) {
    case 'pending': return '等待中'
    case 'running': return '运行中'
    case 'completed': return '已完成'
    case 'failed': return '失败'
    default: return status
  }
}

const formatDate = (dateString: string) => {
  return new Date(dateString).toLocaleString()
}

onMounted(() => {
  loadRepos()
  loadJobs()
})
</script>

<style scoped>
.git-view {
  padding: 20px;
  height: 100%;
  overflow: auto;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 10px;
}

/* 响应式设计 */
@media (max-width: 768px) {
  .git-view {
    padding: 10px;
  }
  
  :deep(.el-row) {
    flex-direction: column;
  }
  
  :deep(.el-col) {
    width: 100% !important;
    flex: 0 0 100% !important;
    max-width: 100% !important;
    margin-bottom: 20px;
  }
  
  .card-header {
    flex-direction: column;
    align-items: stretch;
  }
  
  :deep(.el-table) {
    font-size: 12px;
  }
  
  :deep(.el-table th),
  :deep(.el-table td) {
    padding: 8px 4px;
  }
  
  :deep(.el-dialog) {
    width: 90% !important;
    margin: 5vh auto;
  }
}

@media (max-width: 480px) {
  .git-view {
    padding: 5px;
  }
  
  :deep(.el-table) {
    font-size: 11px;
  }
  
  :deep(.el-table .el-table__cell) {
    padding: 6px 2px;
  }
  
  :deep(.el-button--small) {
    padding: 4px 6px;
    font-size: 10px;
  }
  
  :deep(.el-tag) {
    font-size: 10px;
    padding: 2px 4px;
  }
  
  :deep(.el-progress) {
    margin-bottom: 2px;
  }
  
  :deep(.el-dialog) {
    width: 95% !important;
    margin: 2vh auto;
  }
  
  :deep(.el-form-item__label) {
    font-size: 12px;
  }
}

/* 隐藏部分列在小屏幕上 */
@media (max-width: 576px) {
  /* 隐藏最后同步时间列 */
  :deep(.el-table__column:nth-child(4)) {
    display: none;
  }
}

@media (max-width: 480px) {
  /* 在超小屏幕上隐藏分支列 */
  :deep(.el-table__column:nth-child(2)) {
    display: none;
  }
}
</style>