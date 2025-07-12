<script setup lang="ts">
import { RouterView } from 'vue-router'
import { ref, onMounted, onUnmounted } from 'vue'
import { 
  House, Edit, Share, DataBoard, Folder, 
  Menu as MenuIcon, Close 
} from '@element-plus/icons-vue'

const isMobile = ref(false)
const mobileMenuVisible = ref(false)

const checkScreenSize = () => {
  isMobile.value = window.innerWidth <= 768
  if (!isMobile.value) {
    mobileMenuVisible.value = false
  }
}

const toggleMobileMenu = () => {
  mobileMenuVisible.value = !mobileMenuVisible.value
}

onMounted(() => {
  checkScreenSize()
  window.addEventListener('resize', checkScreenSize)
})

onUnmounted(() => {
  window.removeEventListener('resize', checkScreenSize)
})
</script>

<template>
  <div class="app">
    <el-container>
      <el-header>
        <div class="header">
          <div class="logo">
            <h2>HiicHive IDE</h2>
          </div>
          
          <!-- 桌面端菜单 -->
          <el-menu
            v-if="!isMobile"
            :default-active="$route.path"
            mode="horizontal"
            router
            background-color="#409eff"
            text-color="#fff"
            active-text-color="#ffd04b"
            class="desktop-menu"
          >
            <el-menu-item index="/">
              <el-icon><House /></el-icon>
              <span class="menu-text">首页</span>
            </el-menu-item>
            <el-menu-item index="/editor">
              <el-icon><Edit /></el-icon>
              <span class="menu-text">SQL编辑器</span>
            </el-menu-item>
            <el-menu-item index="/lineage">
              <el-icon><Share /></el-icon>
              <span class="menu-text">血缘可视化</span>
            </el-menu-item>
            <el-menu-item index="/metadata">
              <el-icon><DataBoard /></el-icon>
              <span class="menu-text">元数据管理</span>
            </el-menu-item>
            <el-menu-item index="/git">
              <el-icon><Folder /></el-icon>
              <span class="menu-text">Git仓库</span>
            </el-menu-item>
          </el-menu>
          
          <!-- 移动端菜单按钮 -->
          <el-button 
            v-if="isMobile"
            type="primary" 
            :icon="mobileMenuVisible ? Close : MenuIcon"
            @click="toggleMobileMenu"
            class="mobile-menu-toggle"
            circle
          />
        </div>
      </el-header>
      
      <!-- 移动端抽屉菜单 -->
      <el-drawer
        v-model="mobileMenuVisible"
        direction="ltr"
        size="280px"
        :with-header="false"
      >
        <el-menu
          :default-active="$route.path"
          mode="vertical"
          router
          @select="mobileMenuVisible = false"
          class="mobile-menu"
        >
          <el-menu-item index="/">
            <el-icon><House /></el-icon>
            <span>首页</span>
          </el-menu-item>
          <el-menu-item index="/editor">
            <el-icon><Edit /></el-icon>
            <span>SQL编辑器</span>
          </el-menu-item>
          <el-menu-item index="/lineage">
            <el-icon><Share /></el-icon>
            <span>血缘可视化</span>
          </el-menu-item>
          <el-menu-item index="/metadata">
            <el-icon><DataBoard /></el-icon>
            <span>元数据管理</span>
          </el-menu-item>
          <el-menu-item index="/git">
            <el-icon><Folder /></el-icon>
            <span>Git仓库</span>
          </el-menu-item>
        </el-menu>
      </el-drawer>
      
      <el-main class="main-content">
        <RouterView />
      </el-main>
    </el-container>
  </div>
</template>

<style scoped>
.app {
  height: 100vh;
  width: 100vw;
  display: flex;
  flex-direction: column;
}

.header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  height: 100%;
  width: 100%;
}

.logo {
  flex-shrink: 0;
}

.logo h2 {
  color: white;
  margin: 0;
  font-size: 20px;
  white-space: nowrap;
}

.desktop-menu {
  flex: 1;
  justify-content: flex-start;
  margin-left: 20px;
}

.mobile-menu-toggle {
  display: none;
}

.main-content {
  flex: 1;
  overflow: auto;
  height: calc(100vh - 60px);
}

/* Element Plus 样式覆盖 */
:deep(.el-container) {
  height: 100%;
  width: 100%;
}

:deep(.el-header) {
  padding: 0 20px;
  background-color: #409eff;
  height: 60px !important;
  line-height: 60px;
  flex-shrink: 0;
}

:deep(.el-main) {
  padding: 0;
  background-color: #f5f7fa;
  overflow: auto;
}

:deep(.el-menu.el-menu--horizontal) {
  border-bottom: none;
  background-color: transparent !important;
}

:deep(.el-menu--horizontal .el-menu-item) {
  border-bottom: none !important;
}

/* 移动端菜单样式 */
.mobile-menu {
  height: 100%;
  border-right: none;
}

:deep(.el-drawer__body) {
  padding: 0;
}

/* 响应式样式 */
@media (max-width: 768px) {
  .desktop-menu {
    display: none !important;
  }
  
  .mobile-menu-toggle {
    display: block !important;
  }
  
  .logo h2 {
    font-size: 16px;
  }
  
  :deep(.el-header) {
    padding: 0 15px;
  }
}

@media (max-width: 480px) {
  .logo h2 {
    font-size: 14px;
  }
  
  :deep(.el-header) {
    padding: 0 10px;
  }
}

/* 小屏幕下菜单文本隐藏 */
@media (max-width: 1024px) {
  .menu-text {
    display: none;
  }
  
  :deep(.el-menu--horizontal .el-menu-item) {
    padding: 0 15px;
  }
}

@media (min-width: 1025px) {
  .menu-text {
    margin-left: 5px;
  }
}
</style>
