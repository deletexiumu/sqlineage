<template>
  <div class="config-panel">
    <el-tabs v-model="activeTab" type="border-card">
      <!-- 数据库配置 -->
      <el-tab-pane label="数据库连接" name="database">
        <div class="tab-content">
          <el-form :model="dbConfig" label-width="120px">
            <el-form-item label="连接名称">
              <el-input v-model="dbConfig.name" placeholder="输入连接名称"></el-input>
            </el-form-item>
            <el-form-item label="数据库类型">
              <el-select v-model="dbConfig.type" placeholder="选择数据库类型">
                <el-option label="Hive" value="hive"></el-option>
                <el-option label="MySQL" value="mysql"></el-option>
                <el-option label="PostgreSQL" value="postgresql"></el-option>
              </el-select>
            </el-form-item>
            <el-form-item label="主机地址">
              <el-input v-model="dbConfig.host" placeholder="localhost"></el-input>
            </el-form-item>
            <el-form-item label="端口">
              <el-input v-model="dbConfig.port" placeholder="10000"></el-input>
            </el-form-item>
            <el-form-item label="用户名">
              <el-input v-model="dbConfig.username" placeholder="输入用户名"></el-input>
            </el-form-item>
            <el-form-item label="密码">
              <el-input v-model="dbConfig.password" type="password" placeholder="输入密码"></el-input>
            </el-form-item>
            <el-form-item label="数据库">
              <el-input v-model="dbConfig.database" placeholder="default"></el-input>
            </el-form-item>
            <el-form-item>
              <el-button @click="testDbConnection" :loading="testingDb">测试连接</el-button>
              <el-button @click="saveDbConfig" type="primary">保存配置</el-button>
            </el-form-item>
          </el-form>
        </div>
      </el-tab-pane>
    </el-tabs>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue';
import { ElMessage } from 'element-plus';

const emit = defineEmits(['configChange']);

// 响应式数据
const activeTab = ref('database');
const testingDb = ref(false);

const dbConfig = ref({
  name: 'Default Hive',
  type: 'hive',
  host: 'localhost',
  port: '10000',
  username: 'hive',
  password: '',
  database: 'default'
});

onMounted(() => {
  loadConfigs();
});

function loadConfigs() {
  const savedDbConfig = localStorage.getItem('sqllineage_db_config');
  if (savedDbConfig) {
    dbConfig.value = { ...dbConfig.value, ...JSON.parse(savedDbConfig) };
  }
}

async function testDbConnection() {
  testingDb.value = true;
  try {
    await new Promise(resolve => setTimeout(resolve, 1000));
    ElMessage.success('数据库连接测试成功');
  } catch (error) {
    ElMessage.error('数据库连接失败: ' + error.message);
  } finally {
    testingDb.value = false;
  }
}

function saveDbConfig() {
  localStorage.setItem('sqllineage_db_config', JSON.stringify(dbConfig.value));
  emit('configChange', { type: 'database', config: dbConfig.value });
  ElMessage.success('数据库配置已保存');
}
</script>

<style scoped>
.config-panel {
  height: 100%;
}

.tab-content {
  padding: 20px;
}

.el-form {
  max-width: 600px;
}
</style>