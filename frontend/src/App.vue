<script setup lang="ts">
import { RouterView, useRouter } from 'vue-router'
import { ref, onMounted, onUnmounted, computed } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { 
  House, Edit, Share, DataBoard, Folder, 
  Menu as MenuIcon, Close, Moon, Sunny, User, SwitchButton
} from '@element-plus/icons-vue'
import { authAPI } from '@/services/api'

const router = useRouter()
const isMobile = ref(false)
const mobileMenuVisible = ref(false)
const isDark = ref(false)

// 用户认证状态
const userInfo = ref<any>(null)
const isLoggedIn = computed(() => !!userInfo.value)

// 初始化用户状态
const initUserState = () => {
  const savedUserInfo = localStorage.getItem('userInfo')
  if (savedUserInfo) {
    try {
      userInfo.value = JSON.parse(savedUserInfo)
    } catch (error) {
      console.error('Failed to parse user info:', error)
      localStorage.removeItem('userInfo')
      localStorage.removeItem('authToken')
    }
  }
}

// 退出登录
const handleLogout = async () => {
  try {
    await ElMessageBox.confirm('确定要退出登录吗？', '退出登录', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning',
    })
    
    try {
      await authAPI.logout()
    } catch (error) {
      console.error('Logout API error:', error)
    }
    
    // 清除本地存储
    localStorage.removeItem('authToken')
    localStorage.removeItem('userInfo')
    userInfo.value = null
    
    ElMessage.success('已退出登录')
    
    // 如果当前页面需要登录，跳转到首页
    const currentRoute = router.currentRoute.value.path
    if (['/git', '/metadata'].includes(currentRoute)) {
      router.push('/')
    }
  } catch (error) {
    // 用户取消退出
  }
}

// 跳转到登录页
const goToLogin = () => {
  router.push('/login')
}

// 主题切换功能
const toggleTheme = () => {
  isDark.value = !isDark.value
  const htmlElement = document.documentElement
  
  if (isDark.value) {
    htmlElement.classList.add('dark')
  } else {
    htmlElement.classList.remove('dark')
  }
  
  // 保存主题偏好到localStorage
  localStorage.setItem('theme', isDark.value ? 'dark' : 'light')
}

// 初始化主题
const initTheme = () => {
  const savedTheme = localStorage.getItem('theme')
  const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches
  
  isDark.value = savedTheme ? savedTheme === 'dark' : prefersDark
  
  if (isDark.value) {
    document.documentElement.classList.add('dark')
  }
}

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
  initTheme()
  initUserState()
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
            background-color="var(--header-bg)"
            text-color="var(--header-text)"
            active-text-color="#60a5fa"
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
          
          <!-- 桌面端控制按钮 -->
          <div v-if="!isMobile" class="theme-controls">
            <!-- 用户信息 -->
            <div v-if="isLoggedIn" class="user-info">
              <el-dropdown trigger="click">
                <el-button type="primary" plain>
                  <el-icon><User /></el-icon>
                  <span>{{ userInfo?.username }}</span>
                </el-button>
                <template #dropdown>
                  <el-dropdown-menu>
                    <el-dropdown-item>
                      <div class="user-details">
                        <div><strong>{{ userInfo?.username }}</strong></div>
                        <div class="user-email">{{ userInfo?.email || '无邮箱' }}</div>
                      </div>
                    </el-dropdown-item>
                    <el-dropdown-item divided @click="handleLogout">
                      <el-icon><SwitchButton /></el-icon>
                      退出登录
                    </el-dropdown-item>
                  </el-dropdown-menu>
                </template>
              </el-dropdown>
            </div>
            
            <!-- 登录按钮 -->
            <el-button v-else type="primary" @click="goToLogin" plain>
              <el-icon><User /></el-icon>
              登录
            </el-button>
            
            <!-- 主题切换按钮 -->
            <el-button
              type="primary"
              :icon="isDark ? Sunny : Moon"
              @click="toggleTheme"
              circle
              size="default"
              plain
            />
          </div>
          
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
          
          <!-- 移动端用户信息 -->
          <div class="mobile-user-section">
            <div v-if="isLoggedIn" class="mobile-user-info">
              <div class="user-card">
                <el-icon><User /></el-icon>
                <div class="user-text">
                  <div class="username">{{ userInfo?.username }}</div>
                  <div class="user-email">{{ userInfo?.email || '无邮箱' }}</div>
                </div>
              </div>
              <el-button
                type="danger"
                @click="handleLogout"
                size="small"
                plain
                style="width: 100%; margin-top: 8px;"
              >
                <el-icon><SwitchButton /></el-icon>
                退出登录
              </el-button>
            </div>
            
            <el-button v-else
              type="primary"
              @click="goToLogin"
              size="default"
              style="width: 100%; margin-top: 10px;"
            >
              <el-icon><User /></el-icon>
              登录
            </el-button>
          </div>
          
          <!-- 移动端主题切换 -->
          <div class="mobile-theme-toggle">
            <el-button
              type="primary"
              :icon="isDark ? Sunny : Moon"
              @click="toggleTheme"
              size="default"
              plain
              style="width: 100%; margin-top: 10px;"
            >
              {{ isDark ? '浅色模式' : '深色模式' }}
            </el-button>
          </div>
        </el-menu>
      </el-drawer>
      
      <el-main class="main-content">
        <RouterView />
      </el-main>
    </el-container>
  </div>
</template>

<style scoped>
/* 深色模式变量 */
:root {
  --bg-color: #f8fafc;
  --text-color: #1e293b;
  --border-color: #e2e8f0;
  --header-bg: #334155;
  --header-text: #ffffff;
  --card-bg: #ffffff;
  --soft-shadow: 0 1px 3px 0 rgba(0, 0, 0, 0.1), 0 1px 2px 0 rgba(0, 0, 0, 0.06);
}

html.dark {
  --bg-color: #0f172a;
  --text-color: #f1f5f9;
  --border-color: #334155;
  --header-bg: #1e293b;
  --header-text: #f8fafc;
  --card-bg: #1e293b;
  --soft-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.5), 0 2px 4px -1px rgba(0, 0, 0, 0.3);
}

.app {
  height: 100vh;
  width: 100vw;
  display: flex;
  flex-direction: column;
  background: linear-gradient(135deg, var(--bg-color) 0%, rgba(248, 250, 252, 0.8) 100%);
  background-attachment: fixed;
  color: var(--text-color);
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
  color: var(--header-text);
  margin: 0;
  font-size: 20px;
  white-space: nowrap;
  font-weight: 600;
  text-shadow: 0 1px 2px rgba(0, 0, 0, 0.1);
}

.desktop-menu {
  flex: 1;
  justify-content: flex-start;
  margin-left: 20px;
}

.mobile-menu-toggle {
  display: none;
}

.theme-controls {
  margin-left: auto;
  margin-right: 20px;
}

.mobile-theme-toggle {
  padding: 0 20px;
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
  background-color: var(--header-bg);
  height: 60px !important;
  line-height: 60px;
  flex-shrink: 0;
}

:deep(.el-main) {
  padding: 0;
  background-color: var(--bg-color);
  overflow: auto;
}

/* 深色模式下的Element Plus组件样式调整 */
html.dark {
  :deep(.el-main) {
    background-color: #1a1a1a;
  }
  
  :deep(.el-menu--horizontal) {
    background-color: transparent !important;
  }
  
  :deep(.el-drawer__body) {
    background-color: #1a1a1a;
  }
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

/* 用户界面样式 */
.theme-controls {
  display: flex;
  align-items: center;
  gap: 12px;
}

.user-info .el-button {
  max-width: 150px;
}

.user-info .el-button span {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.user-details {
  padding: 5px 0;
  text-align: center;
}

.user-details .user-email {
  font-size: 12px;
  color: #909399;
  margin-top: 2px;
}

/* 移动端用户界面样式 */
.mobile-user-section {
  padding: 15px;
  border-top: 1px solid var(--border-color);
  margin-top: 10px;
}

.mobile-user-info .user-card {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px;
  background: var(--card-bg);
  border-radius: 8px;
  border: 1px solid var(--border-color);
}

.mobile-user-info .user-text {
  flex: 1;
}

.mobile-user-info .username {
  font-weight: 600;
  font-size: 14px;
  color: var(--text-color);
}

.mobile-user-info .user-email {
  font-size: 12px;
  color: #909399;
  margin-top: 2px;
}

.mobile-theme-toggle {
  padding: 0 15px 15px 15px;
}

/* 深色模式用户界面适配 */
html.dark .user-details .user-email {
  color: #94a3b8;
}

html.dark .mobile-user-info .username {
  color: #f8fafc;
}

html.dark .mobile-user-info .user-email {
  color: #94a3b8;
}
</style>
