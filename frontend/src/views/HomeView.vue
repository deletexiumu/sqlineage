<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { metadataAPI } from '@/services/api'
import { ElMessage } from 'element-plus'
import { Edit, Share, DataBoard, Folder, Coin, Menu, List, Connection } from '@element-plus/icons-vue'

const router = useRouter()

// 统计数据
const statistics = ref({
  database_count: 0,
  table_count: 0,
  column_count: 0,
  lineage_count: 0
})

const loading = ref(false)

const navigateTo = (path: string) => {
  router.push(path)
}

// 获取统计数据
const fetchStatistics = async () => {
  loading.value = true
  try {
    const response = await metadataAPI.getStatistics()
    statistics.value = response.data
  } catch (error) {
    console.error('Failed to fetch statistics:', error)
    ElMessage.error('获取统计数据失败')
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  fetchStatistics()
})
</script>

<template>
  <div class="home-view">
    <div class="hero-section">
      <h1>HiicHive IDE</h1>
      <p class="subtitle">轻量级数据血缘分析工具</p>
      <p class="description">
        提供Hive SQL血缘分析、元数据管理、Git集成等功能，
        帮助您快速理解数据流转关系和影响分析。
      </p>
    </div>

    <div class="features">
      <el-row :gutter="20">
        <el-col :span="6">
          <el-card shadow="hover" class="feature-card" @click="navigateTo('/editor')">
            <div class="feature-content">
              <el-icon size="48" color="#409eff"><Edit /></el-icon>
              <h3>SQL编辑器</h3>
              <p>智能SQL编辑器，支持语法高亮、自动补全和实时血缘分析</p>
            </div>
          </el-card>
        </el-col>
        
        <el-col :span="6">
          <el-card shadow="hover" class="feature-card" @click="navigateTo('/lineage')">
            <div class="feature-content">
              <el-icon size="48" color="#67c23a"><Share /></el-icon>
              <h3>血缘可视化</h3>
              <p>直观的血缘关系图谱，支持多层级影响分析和图形导出</p>
            </div>
          </el-card>
        </el-col>
        
        <el-col :span="6">
          <el-card shadow="hover" class="feature-card" @click="navigateTo('/metadata')">
            <div class="feature-content">
              <el-icon size="48" color="#e6a23c"><DataBoard /></el-icon>
              <h3>元数据管理</h3>
              <p>Hive表结构管理，支持搜索、导入和业务映射功能</p>
            </div>
          </el-card>
        </el-col>
        
        <el-col :span="6">
          <el-card shadow="hover" class="feature-card" @click="navigateTo('/git')">
            <div class="feature-content">
              <el-icon size="48" color="#f56c6c"><Folder /></el-icon>
              <h3>Git集成</h3>
              <p>Git仓库管理，支持多种认证方式和批量SQL分析</p>
            </div>
          </el-card>
        </el-col>
      </el-row>
    </div>

    <div class="stats">
      <el-row :gutter="20" v-loading="loading">
        <el-col :span="6">
          <el-statistic title="数据库" :value="statistics.database_count" suffix="个">
            <template #title>
              <div style="display: flex; align-items: center;">
                <el-icon style="margin-right: 4px;"><Coin /></el-icon>
                数据库
              </div>
            </template>
          </el-statistic>
        </el-col>
        <el-col :span="6">
          <el-statistic title="数据表" :value="statistics.table_count" suffix="张">
            <template #title>
              <div style="display: flex; align-items: center;">
                <el-icon style="margin-right: 4px;"><Menu /></el-icon>
                数据表
              </div>
            </template>
          </el-statistic>
        </el-col>
        <el-col :span="6">
          <el-statistic title="字段" :value="statistics.column_count" suffix="个">
            <template #title>
              <div style="display: flex; align-items: center;">
                <el-icon style="margin-right: 4px;"><List /></el-icon>
                字段
              </div>
            </template>
          </el-statistic>
        </el-col>
        <el-col :span="6">
          <el-statistic title="血缘关系" :value="statistics.lineage_count" suffix="条">
            <template #title>
              <div style="display: flex; align-items: center;">
                <el-icon style="margin-right: 4px;"><Connection /></el-icon>
                血缘关系
              </div>
            </template>
          </el-statistic>
        </el-col>
      </el-row>
    </div>
  </div>
</template>

<style scoped>
.home-view {
  padding: 40px;
  max-width: 1200px;
  margin: 0 auto;
  height: 100%;
  overflow: auto;
  background: linear-gradient(135deg, rgba(248, 250, 252, 0.9) 0%, rgba(241, 245, 249, 0.7) 50%, rgba(226, 232, 240, 0.8) 100%);
  background-attachment: fixed;
  position: relative;
}

.home-view::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: 
    radial-gradient(circle at 20% 20%, rgba(59, 130, 246, 0.03) 0%, transparent 50%),
    radial-gradient(circle at 80% 80%, rgba(168, 85, 247, 0.03) 0%, transparent 50%),
    radial-gradient(circle at 40% 60%, rgba(34, 197, 94, 0.02) 0%, transparent 50%);
  pointer-events: none;
  z-index: -1;
}

.hero-section {
  text-align: center;
  margin-bottom: 60px;
}

.hero-section h1 {
  font-size: 48px;
  font-weight: 700;
  background: linear-gradient(135deg, #334155 0%, #475569 50%, #64748b 100%);
  background-clip: text;
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  margin-bottom: 16px;
  text-shadow: none;
  letter-spacing: -0.025em;
}

.subtitle {
  font-size: 24px;
  color: #64748b;
  margin-bottom: 20px;
  font-weight: 500;
}

.description {
  font-size: 16px;
  color: #64748b;
  line-height: 1.6;
  max-width: 600px;
  margin: 0 auto;
  font-weight: 400;
}

.features {
  margin-bottom: 60px;
}

.feature-card {
  cursor: pointer;
  transition: all 0.3s ease;
  height: 220px;
  display: flex;
  flex-direction: column;
  background: rgba(255, 255, 255, 0.8);
  backdrop-filter: blur(10px);
  border: 1px solid rgba(226, 232, 240, 0.6);
  box-shadow: 0 1px 3px 0 rgba(0, 0, 0, 0.1), 0 1px 2px 0 rgba(0, 0, 0, 0.06);
}

.feature-card:hover {
  transform: translateY(-8px);
  box-shadow: 0 10px 25px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05);
  border-color: rgba(59, 130, 246, 0.3);
}

.feature-content {
  text-align: center;
  padding: 20px;
  flex: 1;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  align-items: center;
}

.feature-content h3 {
  margin: 16px 0 12px 0;
  color: #303133;
  font-size: 18px;
  flex-shrink: 0; /* 防止标题被压缩 */
}

.feature-content p {
  color: #606266;
  line-height: 1.5;
  font-size: 14px;
  margin: 0;
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  text-align: center;
  /* 文本省略号处理 */
  overflow: hidden;
  text-overflow: ellipsis;
  word-wrap: break-word;
}

.stats {
  text-align: center;
  padding: 40px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  border-radius: 12px;
  color: white;
}

:deep(.el-statistic) {
  color: white;
}

:deep(.el-statistic__head) {
  color: rgba(255, 255, 255, 0.8);
}

:deep(.el-statistic__content) {
  color: white;
  font-size: 36px;
  font-weight: bold;
}

/* 深色模式专用样式 */
html.dark .home-view {
  background: linear-gradient(135deg, rgba(15, 23, 42, 0.95) 0%, rgba(30, 41, 59, 0.8) 50%, rgba(51, 65, 85, 0.9) 100%) !important;
  background-attachment: fixed;
}

html.dark .home-view::before {
  background: 
    radial-gradient(circle at 20% 20%, rgba(59, 130, 246, 0.08) 0%, transparent 50%),
    radial-gradient(circle at 80% 80%, rgba(168, 85, 247, 0.08) 0%, transparent 50%),
    radial-gradient(circle at 40% 60%, rgba(34, 197, 94, 0.06) 0%, transparent 50%) !important;
}

html.dark .hero-section h1 {
  background: linear-gradient(135deg, #f8fafc 0%, #e2e8f0 50%, #cbd5e1 100%) !important;
  background-clip: text !important;
  -webkit-background-clip: text !important;
  -webkit-text-fill-color: transparent !important;
}

html.dark .subtitle {
  color: #cbd5e1 !important;
}

html.dark .description {
  color: #94a3b8 !important;
}

html.dark .feature-card {
  background: rgba(30, 41, 59, 0.8) !important;
  border-color: rgba(51, 65, 85, 0.6) !important;
  box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.3), 0 2px 4px -1px rgba(0, 0, 0, 0.1) !important;
}

html.dark .feature-card:hover {
  background: rgba(51, 65, 85, 0.9) !important;
  border-color: rgba(59, 130, 246, 0.5) !important;
  box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.4), 0 10px 10px -5px rgba(0, 0, 0, 0.2) !important;
}

html.dark .feature-content h3 {
  color: #f8fafc !important;
}

html.dark .feature-content p {
  color: #cbd5e1 !important;
}

/* 响应式设计 */
@media (max-width: 768px) {
  .home-view {
    padding: 20px;
  }
  
  .hero-section h1 {
    font-size: 32px;
  }
  
  .subtitle {
    font-size: 18px;
  }
  
  .description {
    font-size: 14px;
  }
  
  .features {
    margin-bottom: 40px;
  }
  
  .feature-card {
    height: 200px; /* 在中等屏幕上稍微降低高度 */
  }
  
  .feature-content {
    padding: 15px;
  }
  
  .feature-content h3 {
    font-size: 16px;
  }
  
  .feature-content p {
    font-size: 12px;
  }
  
  .stats {
    padding: 20px;
  }
  
  :deep(.el-statistic__content) {
    font-size: 24px;
  }
}

@media (max-width: 480px) {
  .home-view {
    padding: 10px;
  }
  
  .hero-section {
    margin-bottom: 30px;
  }
  
  .hero-section h1 {
    font-size: 24px;
  }
  
  .subtitle {
    font-size: 16px;
  }
  
  .features {
    margin-bottom: 30px;
  }
  
  .feature-card {
    height: 180px; /* 在小屏幕上进一步降低高度 */
  }
  
  .feature-content {
    padding: 10px;
  }
  
  .feature-content h3 {
    font-size: 14px;
    margin: 8px 0;
  }
  
  .feature-content p {
    font-size: 11px;
    line-height: 1.4;
  }
  
  :deep(.el-col) {
    margin-bottom: 10px;
  }
  
  :deep(.el-statistic__content) {
    font-size: 20px;
  }
}

/* 超小屏幕卡片布局调整 */
@media (max-width: 576px) {
  :deep(.el-row .el-col) {
    width: 100% !important;
    flex: 0 0 100% !important;
    max-width: 100% !important;
  }
}
</style>
