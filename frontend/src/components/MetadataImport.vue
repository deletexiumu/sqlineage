<template>
  <div class="metadata-import">
    <el-card class="import-card">
      <template #header>
        <div class="card-header">
          <span>元数据导入</span>
          <el-button type="primary" size="small" @click="downloadTemplate">下载模板</el-button>
        </div>
      </template>

      <el-form :model="importForm" :rules="importRules" ref="importFormRef" label-width="120px">
        <el-form-item label="文件格式" prop="fileFormat">
          <el-radio-group v-model="importForm.fileFormat">
            <el-radio value="json">JSON格式</el-radio>
            <el-radio value="csv">CSV格式</el-radio>
            <el-radio value="excel">Excel格式</el-radio>
          </el-radio-group>
        </el-form-item>

        <el-form-item label="导入模式" prop="importMode">
          <el-radio-group v-model="importForm.importMode">
            <el-radio value="merge">合并模式 - 更新已存在的表</el-radio>
            <el-radio value="skip">跳过模式 - 跳过已存在的表</el-radio>
          </el-radio-group>
        </el-form-item>

        <el-form-item label="选择文件" prop="file">
          <el-upload
            ref="uploadRef"
            class="upload-demo"
            :auto-upload="false"
            :on-change="handleFileChange"
            :before-remove="handleFileRemove"
            :limit="1"
            :accept="getAcceptTypes()"
          >
            <el-button type="primary" plain>点击选择文件</el-button>
            <template #tip>
              <div class="el-upload__tip">
                支持 {{ importForm.fileFormat.toUpperCase() }} 格式，文件大小不超过10MB
              </div>
            </template>
          </el-upload>
        </el-form-item>

        <el-form-item>
          <el-button 
            type="info" 
            @click="previewData" 
            :loading="loading"
            :disabled="!selectedFile"
          >
            预览数据
          </el-button>
          <el-button 
            type="primary" 
            @click="importData" 
            :loading="loading"
            :disabled="!selectedFile"
          >
            开始导入
          </el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <!-- 预览结果 -->
    <el-card v-if="previewResult" class="preview-card">
      <template #header>
        <span>数据预览</span>
      </template>

      <el-descriptions :column="2" border>
        <el-descriptions-item label="总表数量">{{ previewResult.total_tables }}</el-descriptions-item>
        <el-descriptions-item label="有效表数量">{{ previewResult.valid_tables }}</el-descriptions-item>
        <el-descriptions-item label="无效表数量">{{ previewResult.invalid_tables }}</el-descriptions-item>
        <el-descriptions-item label="状态">
          <el-tag :type="previewResult.invalid_tables > 0 ? 'warning' : 'success'">
            {{ previewResult.invalid_tables > 0 ? '存在错误' : '验证通过' }}
          </el-tag>
        </el-descriptions-item>
      </el-descriptions>

      <!-- 验证错误 -->
      <div v-if="previewResult.validation_errors.length > 0" class="validation-errors">
        <h4>验证错误：</h4>
        <el-alert
          v-for="(error, index) in previewResult.validation_errors"
          :key="index"
          :title="error"
          type="error"
          :closable="false"
          style="margin-bottom: 8px"
        />
      </div>

      <!-- 示例数据 -->
      <div v-if="previewResult.sample_table" class="sample-data">
        <h4>示例表结构：</h4>
        <el-descriptions :column="1" border>
          <el-descriptions-item label="数据库">{{ previewResult.sample_table.database }}</el-descriptions-item>
          <el-descriptions-item label="表名">{{ previewResult.sample_table.name }}</el-descriptions-item>
          <el-descriptions-item label="字段列表">
            <el-table :data="previewResult.sample_table.columns" size="small" style="width: 100%">
              <el-table-column prop="name" label="字段名" width="150" />
              <el-table-column prop="type" label="类型" width="120" />
              <el-table-column prop="comment" label="注释" />
            </el-table>
          </el-descriptions-item>
        </el-descriptions>
      </div>
    </el-card>

    <!-- 导入结果 -->
    <el-card v-if="importResult" class="result-card">
      <template #header>
        <span>导入结果</span>
      </template>

      <el-result
        :icon="importResult.success ? 'success' : 'error'"
        :title="importResult.success ? '导入成功' : '导入失败'"
      >
        <template #sub-title>
          <div v-if="importResult.success && importResult.stats">
            <p>总计: {{ importResult.stats.total }} 张表</p>
            <p>新增: {{ importResult.stats.created }} 张表</p>
            <p>更新: {{ importResult.stats.updated }} 张表</p>
            <p>跳过: {{ importResult.stats.skipped }} 张表</p>
            <p>错误: {{ importResult.stats.errors }} 张表</p>
          </div>
        </template>
        
        <template #extra>
          <el-button type="primary" @click="resetForm">重新导入</el-button>
        </template>
      </el-result>

      <!-- 错误信息 -->
      <div v-if="importResult.errors && importResult.errors.length > 0" class="import-errors">
        <h4>导入错误：</h4>
        <el-alert
          v-for="(error, index) in importResult.errors"
          :key="index"
          :title="error"
          type="error"
          :closable="false"
          style="margin-bottom: 8px"
        />
      </div>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive } from 'vue'
import { ElMessage, ElMessageBox, type UploadInstance, type UploadFile } from 'element-plus'
import { metadataAPI } from '../services/api'

const uploadRef = ref<UploadInstance>()
const importFormRef = ref()
const loading = ref(false)
const selectedFile = ref<File | null>(null)
const previewResult = ref<any>(null)
const importResult = ref<any>(null)

const importForm = reactive({
  fileFormat: 'json',
  importMode: 'merge',
  file: null
})

const importRules = {
  fileFormat: [
    { required: true, message: '请选择文件格式', trigger: 'change' }
  ],
  importMode: [
    { required: true, message: '请选择导入模式', trigger: 'change' }
  ]
}

const getAcceptTypes = () => {
  const acceptMap = {
    json: '.json',
    csv: '.csv',
    excel: '.xlsx,.xls'
  }
  return acceptMap[importForm.fileFormat] || ''
}

const handleFileChange = (file: UploadFile) => {
  selectedFile.value = file.raw || null
  previewResult.value = null
  importResult.value = null
}

const handleFileRemove = () => {
  selectedFile.value = null
  previewResult.value = null
  importResult.value = null
  return true
}

const downloadTemplate = async () => {
  try {
    const response = await metadataAPI.getImportTemplate(importForm.fileFormat)
    
    // 根据格式设置正确的文件名和扩展名
    let filename = 'metadata_template.json'
    if (importForm.fileFormat === 'excel') {
      filename = 'metadata_template.xlsx'
    } else if (importForm.fileFormat === 'csv') {
      filename = 'metadata_template.csv'
    } else if (importForm.fileFormat === 'json') {
      filename = 'metadata_template.json'
    }
    
    // 创建下载链接
    const blob = new Blob([response.data])
    const url = window.URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = filename
    document.body.appendChild(link) // 添加到DOM以确保兼容性
    link.click()
    document.body.removeChild(link) // 清理DOM
    window.URL.revokeObjectURL(url)
    
    ElMessage.success(`${importForm.fileFormat.toUpperCase()}模板下载成功`)
  } catch (error) {
    console.error('下载模板失败:', error)
    ElMessage.error('模板下载失败，请检查网络连接')
  }
}

const previewData = async () => {
  if (!selectedFile.value) {
    ElMessage.warning('请先选择文件')
    return
  }

  loading.value = true
  try {
    const formData = new FormData()
    formData.append('file', selectedFile.value)
    formData.append('file_format', importForm.fileFormat)
    formData.append('preview_only', 'true')

    const response = await metadataAPI.previewImport(formData)
    previewResult.value = response.data.result
    importResult.value = null
    
    ElMessage.success('数据预览成功')
  } catch (error: any) {
    console.error('预览失败:', error)
    ElMessage.error(error.response?.data?.error || '预览失败')
  } finally {
    loading.value = false
  }
}

const importData = async () => {
  if (!selectedFile.value) {
    ElMessage.warning('请先选择文件')
    return
  }

  try {
    await ElMessageBox.confirm(
      '确认要导入元数据吗？此操作将修改数据库中的表信息。',
      '确认导入',
      {
        confirmButtonText: '确认',
        cancelButtonText: '取消',
        type: 'warning',
      }
    )
  } catch {
    return
  }

  loading.value = true
  try {
    const formData = new FormData()
    formData.append('file', selectedFile.value)
    formData.append('file_format', importForm.fileFormat)
    formData.append('import_mode', importForm.importMode)
    formData.append('preview_only', 'false')

    const response = await metadataAPI.importMetadata(formData)
    importResult.value = response.data
    previewResult.value = null
    
    if (response.data.success) {
      ElMessage.success('元数据导入成功')
    } else {
      ElMessage.error('元数据导入失败')
    }
  } catch (error: any) {
    console.error('导入失败:', error)
    ElMessage.error(error.response?.data?.error || '导入失败')
  } finally {
    loading.value = false
  }
}

const resetForm = () => {
  uploadRef.value?.clearFiles()
  selectedFile.value = null
  previewResult.value = null
  importResult.value = null
}
</script>

<style scoped>
.metadata-import {
  padding: 20px;
}

.import-card,
.preview-card,
.result-card {
  margin-bottom: 20px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.validation-errors,
.sample-data,
.import-errors {
  margin-top: 20px;
}

.validation-errors h4,
.sample-data h4,
.import-errors h4 {
  margin-bottom: 10px;
  color: #606266;
}

.upload-demo {
  width: 100%;
}
</style>