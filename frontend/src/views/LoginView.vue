<template>
  <div class="login-container">
    <div class="login-card">
      <div class="login-header">
        <h1>HiicHive IDE</h1>
        <p>数据血缘分析工具</p>
      </div>
      
      <el-form 
        :model="loginForm" 
        :rules="rules" 
        ref="loginFormRef"
        class="login-form"
        @submit.prevent="handleLogin"
      >
        <el-form-item prop="username">
          <el-input
            v-model="loginForm.username"
            placeholder="用户名"
            prefix-icon="User"
            size="large"
            @keyup.enter="handleLogin"
          />
        </el-form-item>
        
        <el-form-item prop="password">
          <el-input
            v-model="loginForm.password"
            type="password"
            placeholder="密码"
            prefix-icon="Lock"
            size="large"
            show-password
            @keyup.enter="handleLogin"
          />
        </el-form-item>
        
        <el-form-item>
          <el-button 
            type="primary" 
            size="large" 
            :loading="loading"
            @click="handleLogin"
            class="login-btn"
          >
            登录
          </el-button>
        </el-form-item>
      </el-form>
      
      <div class="login-footer">
        <p>使用Django管理员账户登录</p>
        <el-link type="primary" @click="showHelp = true">
          <el-icon><QuestionFilled /></el-icon>
          需要帮助？
        </el-link>
      </div>
    </div>
    
    <!-- 帮助对话框 -->
    <el-dialog v-model="showHelp" title="登录帮助" width="400px">
      <div class="help-content">
        <h4>如何获取登录账户？</h4>
        <ol>
          <li>使用Django超级用户账户登录</li>
          <li>如果没有账户，请联系管理员创建</li>
          <li>或者运行命令创建超级用户：<code>python manage.py createsuperuser</code></li>
        </ol>
        
        <h4>需要登录的功能：</h4>
        <ul>
          <li>Git仓库管理</li>
          <li>元数据手动导入</li>
          <li>Hive连接配置</li>
          <li>删除操作</li>
        </ul>
        
        <p><strong>注意：</strong>浏览和查看功能无需登录。</p>
      </div>
      
      <template #footer>
        <el-button @click="showHelp = false">知道了</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { User, Lock, QuestionFilled } from '@element-plus/icons-vue'
import { authAPI } from '@/services/api'
import type { FormInstance, FormRules } from 'element-plus'

const router = useRouter()
const loading = ref(false)
const showHelp = ref(false)
const loginFormRef = ref<FormInstance>()

const loginForm = reactive({
  username: '',
  password: ''
})

const rules: FormRules = {
  username: [
    { required: true, message: '请输入用户名', trigger: 'blur' }
  ],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' },
    { min: 6, message: '密码长度不能少于6位', trigger: 'blur' }
  ]
}

const handleLogin = async () => {
  if (!loginFormRef.value) return
  
  try {
    const valid = await loginFormRef.value.validate()
    if (!valid) return
    
    loading.value = true
    
    // 调用登录API
    const response = await authAPI.login(loginForm.username, loginForm.password)
    
    // 保存token和用户信息
    localStorage.setItem('authToken', response.data.token)
    localStorage.setItem('userInfo', JSON.stringify(response.data.user))
    
    ElMessage.success('登录成功')
    
    // 跳转到首页或之前的页面
    const redirect = router.currentRoute.value.query.redirect as string || '/'
    router.push(redirect)
    
  } catch (error: any) {
    console.error('Login error:', error)
    const errorMessage = error?.response?.data?.message || '登录失败，请检查用户名和密码'
    ElMessage.error(errorMessage)
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.login-container {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  padding: 20px;
}

.login-card {
  width: 400px;
  background: white;
  border-radius: 12px;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
  padding: 40px;
  backdrop-filter: blur(10px);
  border: 1px solid rgba(255, 255, 255, 0.2);
}

.login-header {
  text-align: center;
  margin-bottom: 30px;
}

.login-header h1 {
  margin: 0;
  font-size: 28px;
  font-weight: 600;
  background: linear-gradient(135deg, #667eea, #764ba2);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

.login-header p {
  margin: 8px 0 0 0;
  color: #666;
  font-size: 14px;
}

.login-form {
  margin-bottom: 20px;
}

.login-form .el-form-item {
  margin-bottom: 20px;
}

.login-btn {
  width: 100%;
  height: 45px;
  font-size: 16px;
  font-weight: 500;
}

.login-footer {
  text-align: center;
  border-top: 1px solid #eee;
  padding-top: 20px;
}

.login-footer p {
  margin: 0 0 10px 0;
  color: #666;
  font-size: 13px;
}

.help-content h4 {
  color: #409eff;
  margin: 0 0 10px 0;
}

.help-content ol, .help-content ul {
  margin: 10px 0;
  padding-left: 20px;
}

.help-content li {
  margin: 5px 0;
  line-height: 1.5;
}

.help-content code {
  background: #f5f5f5;
  padding: 2px 6px;
  border-radius: 3px;
  font-family: 'Courier New', monospace;
  font-size: 12px;
}

/* 深色模式适配 */
:deep(.dark) .login-card {
  background: rgba(30, 41, 59, 0.9);
  border: 1px solid rgba(255, 255, 255, 0.1);
}

:deep(.dark) .login-header h1 {
  background: linear-gradient(135deg, #60a5fa, #a78bfa);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

:deep(.dark) .login-header p {
  color: #cbd5e1;
}

:deep(.dark) .login-footer p {
  color: #94a3b8;
}

:deep(.dark) .help-content code {
  background: #374151;
  color: #f3f4f6;
}

/* 响应式设计 */
@media (max-width: 480px) {
  .login-container {
    padding: 10px;
  }
  
  .login-card {
    width: 100%;
    max-width: 360px;
    padding: 30px 20px;
  }
  
  .login-header h1 {
    font-size: 24px;
  }
}
</style>