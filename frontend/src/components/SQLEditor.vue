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
            <el-button 
              size="small" 
              @click="toggleLSP"
              :type="lspEnabled ? 'success' : 'info'"
              title="切换智能提示模式"
            >
              {{ lspEnabled ? 'LSP模式' : '传统模式' }}
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
  // 优化补全性能
  quickSuggestions: {
    other: true,
    comments: false,
    strings: false
  },
  quickSuggestionsDelay: 500,
  suggestOnTriggerCharacters: true,
  acceptSuggestionOnCommitCharacter: true,
  acceptSuggestionOnEnter: 'on' as const,
  tabCompletion: 'on' as const,
  // 补全提示配置
  suggest: {
    showDetails: true,        // 默认显示详细信息
    showDocumentation: true,  // 显示文档
    insertMode: 'replace' as const,  // 替换模式，避免重复文本
    filterGraceful: true,     // 优雅过滤
    snippetsPreventQuickSuggestions: false,
    detailsVisible: true,     // 确保详情默认可见
    documentationVisible: true  // 确保文档默认可见
  }
}

const handleEditorMount = (editorInstance: any) => {
  editor.value = editorInstance
  
  // 简化的详情展开函数
  const ensureDetailsVisible = () => {
    try {
      const suggestController = editorInstance.getContribution('editor.contrib.suggestController')
      if (suggestController && suggestController.widget && suggestController.widget.value) {
        const widget = suggestController.widget.value
        
        // 如果详情未显示，则切换显示
        if (widget.toggleDetails && !widget.showsDetails) {
          widget.toggleDetails()
        }
        
        // 添加CSS类确保样式正确
        setTimeout(() => {
          const suggestWidgetElement = document.querySelector('.monaco-editor .suggest-widget')
          if (suggestWidgetElement) {
            suggestWidgetElement.classList.add('docs-side')
          }
        }, 10)
      }
    } catch (e) {
      console.debug('Failed to ensure details visible:', e)
    }
  }
  
  // 当建议框显示时触发
  editorInstance.onDidChangeCursorPosition(() => {
    setTimeout(ensureDetailsVisible, 100)
  })
  
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

  // 添加防抖变量
  let lastRequestTime = 0
  const debounceMs = 300
  
  // Register autocomplete provider
  monaco.languages.registerCompletionItemProvider('sql', {
    provideCompletionItems: async (model: any, position: any, context: any, token: any) => {
      // 防抖处理
      const now = Date.now()
      if (now - lastRequestTime < debounceMs) {
        return { suggestions: [] }
      }
      lastRequestTime = now
      
      // 检查取消令牌
      if (token?.isCancellationRequested) {
        return { suggestions: [] }
      }
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

        const response = await metadataAPI.getAutocomplete(params.query, 10, params) // 限制为10个
        
        // 再次检查取消令牌
        if (token?.isCancellationRequested) {
          return { suggestions: [] }
        }
        
        const suggestions = response.data.slice(0, 10).map((item: any) => ({
          label: item.label,
          kind: item.type === 'table' ? monaco.languages.CompletionItemKind.Class : monaco.languages.CompletionItemKind.Field,
          insertText: item.value,
          detail: item.detail || (item.dataType || item.database),
          documentation: item.documentation || (item.comment || ''),
          range: range,  // range已经在上面正确计算了word范围
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

// 切换LSP模式
const toggleLSP = () => {
  lspEnabled.value = !lspEnabled.value
  
  if (editor.value) {
    // 清理现有的提供者
    if (lspIntegration.value) {
      lspIntegration.value.dispose()
      lspIntegration.value = null
    }
    
    if (lspClient.value) {
      lspClient.value.dispose()
      lspClient.value = null
    }
    
    // 重新设置补全方式
    if (lspEnabled.value) {
      setupLSPIntegration()
      ElMessage.success('已切换到LSP智能模式')
    } else {
      setupAutocompletion()
      ElMessage.success('已切换到传统补全模式')
    }
  }
}

onMounted(() => {
  // Load Monaco Editor
  import('monaco-editor/esm/vs/editor/editor.api').then(() => {
    console.log('Monaco Editor loaded')
    
    // 配置Monaco Editor强制显示详情
    const monaco = (window as any).monaco
    if (monaco && monaco.editor) {
      // 修改全局建议配置
      const originalCreate = monaco.editor.create
      monaco.editor.create = function(container: any, options: any, override?: any) {
        const editor = originalCreate.call(this, container, {
          ...options,
          suggest: {
            ...options.suggest,
            showDetails: true,
            showDocumentation: true,
            detailsVisible: true
          }
        }, override)
        
        // 简单的DOM监控
        const setupSuggestWidget = () => {
          setTimeout(() => {
            const suggestWidget = document.querySelector('.monaco-editor .suggest-widget')
            if (suggestWidget) {
              suggestWidget.classList.add('docs-side')
            }
          }, 200)
        }
        
        // 监听建议显示事件
        editor.onDidCreateModel(() => {
          setupSuggestWidget()
        })
        
        return editor
      }
    }
    
    // 自定义Monaco Editor建议框样式
    const style = document.createElement('style')
    style.textContent = `
      .monaco-editor .suggest-widget {
        width: 900px !important;
        max-width: 900px !important;
        font-size: 13px !important;
        line-height: 1.4 !important;
        min-height: 300px !important;
      }
      .monaco-editor .suggest-widget.docs-side {
        width: 900px !important;
        max-width: 900px !important;
        min-height: 300px !important;
      }
      /* 强制显示详情面板 */
      .monaco-editor .suggest-widget .monaco-list {
        width: 500px !important;
        max-width: 500px !important;
      }
      .monaco-editor .suggest-widget .monaco-list .monaco-list-row {
        height: 34px !important;
        min-height: 34px !important;
        max-height: 34px !important;
        line-height: 34px !important;
        padding: 0 4px !important;
        display: flex !important;
        align-items: center !important;
        box-sizing: border-box !important;
        overflow: hidden !important;
      }
      .monaco-editor .suggest-widget .details {
        width: 380px !important;
        max-width: 380px !important;
        min-width: 380px !important;
        min-height: 280px !important;
        white-space: pre-wrap !important;
        word-wrap: break-word !important;
        font-size: 13px !important;
        line-height: 1.5 !important;
        padding: 15px !important;
        border-left: 1px solid #e1e4e8 !important;
        background-color: #f8f9fa !important;
        display: block !important;
        visibility: visible !important;
        opacity: 1 !important;
      }
      .monaco-editor.vs-dark .suggest-widget .details {
        border-left-color: #444 !important;
        background-color: #2d2d30 !important;
        color: #cccccc !important;
      }
      /* 强制显示详情 */
      .monaco-editor .suggest-widget .details-label {
        display: none !important;
      }
      /* 确保详情内容始终可见 */
      .monaco-editor .suggest-widget .details,
      .monaco-editor .suggest-widget.docs-side .details {
        display: block !important;
        visibility: visible !important;
        opacity: 1 !important;
        overflow-y: auto !important;
      }
      .monaco-editor .suggest-widget .details .docs,
      .monaco-editor .suggest-widget .details .header,
      .monaco-editor .suggest-widget .details .body {
        display: block !important;
        visibility: visible !important;
      }
      /* 确保详情框始终可见 */
      .monaco-editor .suggest-widget .tree {
        width: 500px !important;
      }
      .monaco-editor .suggest-widget .details {
        flex: 0 0 380px !important;
      }
      /* 移除右侧箭头，因为详情总是显示的 */
      .monaco-editor .suggest-widget .monaco-list .monaco-list-row .suggest-more-info {
        display: none !important;
      }
      /* 确保布局稳定 */
      .monaco-editor .suggest-widget {
        display: flex !important;
        flex-direction: row !important;
      }
      .monaco-editor .suggest-widget .monaco-list {
        flex: 1 1 500px !important;
        border-right: 1px solid #e1e4e8 !important;
      }
      .monaco-editor.vs-dark .suggest-widget .monaco-list {
        border-right-color: #444 !important;
      }
      /* 当详情显示时的特殊样式 */
      .monaco-editor .suggest-widget.docs-side {
        display: flex !important;
        flex-direction: row !important;
      }
      .monaco-editor .suggest-widget.docs-side .monaco-list {
        flex: 1 1 500px !important;
      }
      .monaco-editor .suggest-widget.docs-side .details {
        flex: 0 0 380px !important;
        display: block !important;
        visibility: visible !important;
        opacity: 1 !important;
      }
      .monaco-editor .suggest-widget .monaco-list .monaco-list-row .suggest-icon {
        width: 20px !important;
        height: 20px !important;
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
        flex-shrink: 0 !important;
        margin-right: 8px !important;
      }
      .monaco-editor .suggest-widget .monaco-list .monaco-list-row .contents {
        padding-right: 8px !important;
        flex: 1 !important;
        display: flex !important;
        flex-direction: column !important;
        justify-content: center !important;
        min-height: 34px !important;
        max-height: 34px !important;
        overflow: hidden !important;
      }
      .monaco-editor .suggest-widget .monaco-list .monaco-list-row .contents .main {
        font-size: 13px !important;
        line-height: 16px !important;
        font-weight: 500 !important;
        overflow: hidden !important;
        text-overflow: ellipsis !important;
        white-space: nowrap !important;
        margin-bottom: 1px !important;
        height: 16px !important;
      }
      .monaco-editor .suggest-widget .monaco-list .monaco-list-row .contents .main .monaco-highlighted-label {
        font-weight: 600 !important;
      }
      .monaco-editor .suggest-widget .monaco-list .monaco-list-row .contents .qualifier {
        color: #666 !important;
        font-size: 11px !important;
        line-height: 12px !important;
        height: 12px !important;
        margin: 0 !important;
        overflow: hidden !important;
        text-overflow: ellipsis !important;
        white-space: nowrap !important;
        max-width: 100% !important;
      }
      /* 深色主题适配 */
      .monaco-editor.vs-dark .suggest-widget .monaco-list .monaco-list-row .contents .qualifier {
        color: #cccccc !important;
      }
      /* 选中状态样式 */
      .monaco-editor .suggest-widget .monaco-list .monaco-list-row.focused {
        background-color: rgba(0, 120, 215, 0.1) !important;
        border: none !important;
        outline: none !important;
        margin: 0 !important;
      }
      .monaco-editor.vs-dark .suggest-widget .monaco-list .monaco-list-row.focused {
        background-color: rgba(0, 120, 215, 0.2) !important;
        border: none !important;
        outline: none !important;
        margin: 0 !important;
      }
      /* 确保list容器没有额外间距 */
      .monaco-editor .suggest-widget .monaco-list {
        padding: 0 !important;
        margin: 0 !important;
      }
      .monaco-editor .suggest-widget .monaco-list .monaco-scrollable-element {
        padding: 0 !important;
        margin: 0 !important;
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