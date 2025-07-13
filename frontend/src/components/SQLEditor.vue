<template>
  <div class="sql-editor">
    <el-card>
      <template #header>
        <div class="card-header">
          <div class="header-left">
            <span>SQL编辑器</span>
            <!-- LSP状态指示器 -->
            <el-tag
              v-if="lspEnabled"
              :type="lspStatus === 'connected' ? 'success' : lspStatus === 'error' ? 'danger' : 'info'"
              size="small"
              class="lsp-status"
            >
              <el-icon>
                <Loading v-if="lspStatus === 'connecting'" />
                <Check v-else-if="lspStatus === 'connected'" />
                <Close v-else-if="lspStatus === 'error'" />
                <Warning v-else />
              </el-icon>
              {{ 
                lspStatus === 'connected' ? '智能提示已启用' : 
                lspStatus === 'connecting' ? '连接中...' :
                lspStatus === 'error' ? '智能提示异常' : '智能提示未连接'
              }}
            </el-tag>
          </div>
          <div class="header-actions">
            <el-button 
              v-if="lspEnabled && lspStatus === 'connected'" 
              size="small" 
              @click="refreshLSPMetadata"
              title="刷新智能提示元数据"
            >
              <el-icon><Refresh /></el-icon>
              刷新元数据
            </el-button>
            <el-button type="primary" @click="formatSql" :loading="formatting">
              一键格式化
            </el-button>
            <el-button @click="copySql" :loading="copying">
              一键复制
            </el-button>
            <el-button @click="clearEditor">清空</el-button>
          </div>
        </div>
      </template>
      
      <div class="editor-container">
        <vue-monaco-editor
          v-model:value="sqlCode"
          language="sql"
          theme="vs-dark"
          :options="editorOptions"
          @mount="handleEditorMount"
          @change="handleEditorChange"
          style="height: 400px"
        />
      </div>

    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, computed } from 'vue'
import { VueMonacoEditor } from '@guolao/vue-monaco-editor'
import { metadataAPI } from '@/services/api'
import { ElMessage } from 'element-plus'
import { format } from 'sql-formatter'
import { LSPClient, MonacoLSPIntegration } from '@/services/lspClient'
import { Loading, Check, Close, Warning, Refresh } from '@element-plus/icons-vue'

const sqlCode = ref(`-- 示例SQL
CREATE TABLE if not exists dwt_capital.dim_investment_event_df
(
    \`bk_investment_event_id\`           STRING COMMENT '主键-投资事件ID',
    \`sk_investment_event_id\`           BIGINT COMMENT '代理键-投资事件ID',
    \`investment_event_name\`            STRING COMMENT '投资事件名称'
) COMMENT '维度表-投资事件'
PARTITIONED BY ( \`dt\` string COMMENT '分区列-日期,yyyyMMdd')
stored as orc;

insert overwrite table dwt_capital.dim_investment_event_df partition (dt = '20250625')
select logic_id                         as bk_investment_event_id,
       shared_udf_prod.xxhash(logic_id) as sk_investment_event_id,
       investment_event_name            as investment_event_name
from dwd_zbk.dwd_zbk_investor_project_information;`)

const formatting = ref(false)
const copying = ref(false)
const editor = ref<any>(null)

// LSP客户端相关
const lspClient = ref<LSPClient | null>(null)
const lspIntegration = ref<MonacoLSPIntegration | null>(null)
const lspEnabled = ref(true) // 可以通过配置控制是否启用LSP
const lspStatus = ref<'disconnected' | 'connecting' | 'connected' | 'error'>('disconnected')

const editorOptions = {
  automaticLayout: true,
  fontSize: 14,
  minimap: { enabled: false },
  scrollBeyondLastLine: false,
  wordWrap: 'on' as const,
  lineNumbers: 'on' as const,
  glyphMargin: true,
  folding: true,
}

const handleEditorMount = (editorInstance: any) => {
  editor.value = editorInstance
  
  // 根据配置决定使用LSP还是传统自动补全
  if (lspEnabled.value) {
    setupLSPIntegration()
  } else {
    setupAutocompletion()
  }
}

const handleEditorChange = () => {
  // 编辑器内容改变时的处理
}

// 设置LSP集成
const setupLSPIntegration = () => {
  if (!editor.value) return
  
  try {
    lspStatus.value = 'connecting'
    
    // 创建LSP客户端
    lspClient.value = new LSPClient({
      onDiagnostics: (diagnostics) => {
        console.log('Received diagnostics:', diagnostics)
        // 诊断信息会通过MonacoLSPIntegration自动显示
      },
      onError: (error) => {
        console.error('LSP Error:', error)
        lspStatus.value = 'error'
        ElMessage.warning(`SQL智能提示服务异常: ${error}`)
        
        // 如果LSP失败，回退到传统自动补全
        if (!lspIntegration.value) {
          setupAutocompletion()
        }
      },
      onConnectionChange: (connected) => {
        lspStatus.value = connected ? 'connected' : 'disconnected'
        if (connected) {
          ElMessage.success('SQL智能提示服务已连接')
          // 刷新元数据缓存
          lspClient.value?.refreshMetadata()
        }
      }
    })
    
    // 创建Monaco LSP集成
    lspIntegration.value = new MonacoLSPIntegration(editor.value, lspClient.value)
    
    lspStatus.value = 'connected'
    console.log('LSP integration setup completed')
    
  } catch (error) {
    console.error('Failed to setup LSP integration:', error)
    lspStatus.value = 'error'
    
    // 回退到传统自动补全
    setupAutocompletion()
  }
}

const setupAutocompletion = () => {
  if (!editor.value) return

  const monaco = (window as any).monaco
  if (!monaco) return

  // Register autocomplete provider
  monaco.languages.registerCompletionItemProvider('sql', {
    provideCompletionItems: async (model: any, position: any) => {
      const word = model.getWordUntilPosition(position)
      const range = {
        startLineNumber: position.lineNumber,
        endLineNumber: position.lineNumber,
        startColumn: word.startColumn,
        endColumn: word.endColumn,
      }

      try {
        // 分析SQL上下文
        const sqlContext = analyzeSQLContext(model, position)
        
        // 构建API请求参数
        const params: any = {
          query: word.word,
          limit: 20,
          context: sqlContext.contextType,
        }
        
        if (sqlContext.schema) {
          params.schema = sqlContext.schema
        }
        
        if (sqlContext.tableAlias && sqlContext.relatedTables.length > 0) {
          params.table_alias = sqlContext.tableAlias
          params.related_tables = sqlContext.relatedTables.join(',')
        }

        const response = await metadataAPI.getAutocomplete(params.query, params.limit, params)
        const suggestions = response.data.map((item: any) => ({
          label: item.label,
          kind: item.type === 'table' ? monaco.languages.CompletionItemKind.Class : monaco.languages.CompletionItemKind.Field,
          insertText: item.value,
          detail: item.detail || (item.dataType || item.database),
          documentation: item.documentation || (item.comment || ''),
          range: range,
          sortText: item.type === 'table' ? '1' + item.label : '2' + item.label, // 表优先排序
        }))

        return { suggestions }
      } catch (error) {
        console.error('Autocomplete error:', error)
        return { suggestions: [] }
      }
    },
  })
}

// SQL上下文分析函数
const analyzeSQLContext = (model: any, position: any) => {
  const text = model.getValue()
  const lines = text.split('\n')
  const currentLine = lines[position.lineNumber - 1]
  const beforeCursor = currentLine.substring(0, position.column - 1)
  
  // 获取当前光标前的完整SQL文本
  const textBeforeCursor = lines.slice(0, position.lineNumber - 1).join('\n') + '\n' + beforeCursor
  
  // 分析当前所在的SQL语句段落
  const context = {
    contextType: 'mixed' as 'mixed' | 'table' | 'column',
    schema: '',
    tableAlias: '',
    relatedTables: [] as string[],
  }
  
  // 检查是否在FROM或JOIN语句中（应该补全表名）
  const fromJoinPattern = /\b(from|join)\s+[\w.]*$/i
  if (fromJoinPattern.test(beforeCursor)) {
    context.contextType = 'table'
  }
  
  // 检查是否在SELECT语句中（应该补全字段名）
  const selectPattern = /\bselect\s+(?:[^,\s]+,\s*)*[\w.]*$/i
  if (selectPattern.test(beforeCursor) && !fromJoinPattern.test(beforeCursor)) {
    context.contextType = 'column'
  }
  
  // 检查是否有表别名的字段引用（如 t1.）
  const aliasFieldPattern = /(\w+)\.[\w]*$/
  const aliasMatch = beforeCursor.match(aliasFieldPattern)
  if (aliasMatch) {
    context.contextType = 'column'
    context.tableAlias = aliasMatch[1]
    
    // 查找该别名对应的表名
    const aliasTablePattern = new RegExp(`\\b(?:from|join)\\s+([\\w.]+)\\s+(?:as\\s+)?${context.tableAlias}\\b`, 'i')
    const tableMatch = textBeforeCursor.match(aliasTablePattern)
    if (tableMatch) {
      context.relatedTables = [tableMatch[1]]
    }
  }
  
  // 提取指定的schema（如 dwd_zlk.）
  const schemaPattern = /\b(\w+)\.[\w]*$/
  const schemaMatch = beforeCursor.match(schemaPattern)
  if (schemaMatch && !aliasMatch) {
    context.schema = schemaMatch[1]
    // 检查这是否真的是schema而不是表别名
    const isSchema = /\b(?:from|join)\s+\w+\.[\w]*$/i.test(beforeCursor)
    if (isSchema) {
      context.contextType = 'table'
    }
  }
  
  // 如果没有找到表别名的字段引用，但在SELECT中，尝试找到相关的表
  if (context.contextType === 'column' && !context.tableAlias && !context.schema) {
    // 查找FROM和JOIN中的所有表
    const tablePattern = /\b(?:from|join)\s+([\w.]+)(?:\s+(?:as\s+)?(\w+))?\b/gi
    let match
    while ((match = tablePattern.exec(textBeforeCursor)) !== null) {
      context.relatedTables.push(match[1])
    }
  }
  
  return context
}

const formatSql = async () => {
  if (!sqlCode.value.trim()) {
    ElMessage.warning('请输入SQL代码')
    return
  }

  formatting.value = true

  try {
    const formattedSql = format(sqlCode.value, {
      language: 'hive',
      keywordCase: 'upper',
      functionCase: 'upper',
      linesBetweenQueries: 2
    })
    sqlCode.value = formattedSql
    ElMessage.success('SQL格式化成功')
  } catch (error) {
    console.error('Format SQL error:', error)
    ElMessage.error('SQL格式化失败，请检查语法')
  } finally {
    formatting.value = false
  }
}

const copySql = async () => {
  if (!sqlCode.value.trim()) {
    ElMessage.warning('没有可复制的内容')
    return
  }

  copying.value = true

  try {
    await navigator.clipboard.writeText(sqlCode.value)
    ElMessage.success('SQL代码已复制到剪贴板')
  } catch (error) {
    console.error('Copy SQL error:', error)
    // 降级到传统方法
    try {
      const textArea = document.createElement('textarea')
      textArea.value = sqlCode.value
      document.body.appendChild(textArea)
      textArea.select()
      document.execCommand('copy')
      document.body.removeChild(textArea)
      ElMessage.success('SQL代码已复制到剪贴板')
    } catch (fallbackError) {
      ElMessage.error('复制失败，请手动复制')
    }
  } finally {
    copying.value = false
  }
}

const clearEditor = () => {
  sqlCode.value = ''
}

// 刷新LSP元数据缓存
const refreshLSPMetadata = async () => {
  if (lspClient.value && lspStatus.value === 'connected') {
    try {
      await lspClient.value.refreshMetadata()
      ElMessage.success('智能提示元数据已刷新')
    } catch (error) {
      console.error('Failed to refresh LSP metadata:', error)
      ElMessage.error('刷新智能提示元数据失败')
    }
  }
}

onMounted(() => {
  // Load Monaco Editor
  import('monaco-editor/esm/vs/editor/editor.api').then(() => {
    console.log('Monaco Editor loaded')
    // 自定义Monaco Editor建议框样式
    const style = document.createElement('style')
    style.textContent = `
      .monaco-editor .suggest-widget {
        width: 500px !important;
        max-width: 500px !important;
      }
      .monaco-editor .suggest-widget .monaco-list .monaco-list-row {
        height: auto !important;
        min-height: 28px !important;
      }
      .monaco-editor .suggest-widget .details {
        width: 200px !important;
        max-width: 200px !important;
      }
      .monaco-editor .suggest-widget .monaco-list .monaco-list-row .suggest-icon {
        width: 20px !important;
      }
      .monaco-editor .suggest-widget .monaco-list .monaco-list-row .contents {
        padding-right: 10px !important;
      }
    `
    document.head.appendChild(style)
  })
})

onUnmounted(() => {
  // 清理LSP资源
  if (lspIntegration.value) {
    lspIntegration.value.dispose()
    lspIntegration.value = null
  }
  
  if (lspClient.value) {
    lspClient.value.dispose()
    lspClient.value = null
  }
})
</script>

<style scoped>
.sql-editor {
  height: 100%;
  padding: 20px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 10px;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}

.lsp-status {
  font-size: 11px;
  display: flex;
  align-items: center;
  gap: 4px;
}

.lsp-status .el-icon {
  font-size: 12px;
}

.header-actions {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.editor-container {
  border: 1px solid #dcdfe6;
  border-radius: 4px;
  overflow: hidden;
  height: 60vh;
  min-height: 400px;
}


/* 响应式设计 */
@media (max-width: 768px) {
  .sql-editor {
    padding: 10px;
  }
  
  .card-header {
    flex-direction: column;
    align-items: stretch;
  }
  
  .header-actions {
    justify-content: center;
  }
  
  .editor-container {
    height: 50vh;
    min-height: 300px;
  }
}

@media (max-width: 480px) {
  .sql-editor {
    padding: 5px;
  }
  
  .header-actions {
    flex-direction: column;
  }
  
  .header-actions .el-button {
    width: 100%;
  }
  
  .editor-container {
    height: 45vh;
    min-height: 250px;
  }
}
</style>