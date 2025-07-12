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
}

.hero-section {
  text-align: center;
  margin-bottom: 60px;
}

.hero-section h1 {
  font-size: 48px;
  font-weight: bold;
  color: #303133;
  margin-bottom: 16px;
}

.subtitle {
  font-size: 24px;
  color: #606266;
  margin-bottom: 20px;
}

.description {
  font-size: 16px;
  color: #909399;
  line-height: 1.6;
  max-width: 600px;
  margin: 0 auto;
}

.features {
  margin-bottom: 60px;
}

.feature-card {
  cursor: pointer;
  transition: transform 0.3s ease;
  height: 220px; /* 固定卡片高度 */
  display: flex;
  flex-direction: column;
}

.feature-card:hover {
  transform: translateY(-5px);
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
