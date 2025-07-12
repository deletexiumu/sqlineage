<template>
  <div class="sql-editor">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>SQL编辑器</span>
          <div class="header-actions">
            <el-button type="primary" @click="parseSql" :loading="parsing">
              解析血缘
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

      <div v-if="parseResult" class="parse-result">
        <div class="result-header">
          <h4>解析结果</h4>
          <div class="result-actions">
            <el-tag v-if="parseResult.status === 'success'" type="success">
              找到 {{ parseResult.relations_count }} 个血缘关系
            </el-tag>
            <el-tag v-else type="danger">
              {{ parseResult.message }}
            </el-tag>
            <el-button 
              v-if="parseResult.status === 'success' && showLineageGraph" 
              size="small" 
              type="primary" 
              @click="toggleLineageView"
            >
              {{ showLineageDetail ? '隐藏血缘图' : '显示血缘图' }}
            </el-button>
          </div>
        </div>
        
        <!-- 血缘图展示区域 -->
        <div v-if="parseResult.status === 'success' && showLineageGraph && showLineageDetail" class="lineage-display">
          <ColumnLineageGraph 
            v-if="parseResult.column_graph && parseResult.column_graph.tables.length > 0"
            :column-graph="parseResult.column_graph" 
            :loading="false" 
            :error="''" 
          />
          <div v-else class="no-lineage">
            <el-empty description="暂无字段级血缘关系可视化" />
          </div>
        </div>
      </div>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { VueMonacoEditor } from '@guolao/vue-monaco-editor'
import { lineageAPI, metadataAPI } from '@/services/api'
import { ElMessage } from 'element-plus'
import ColumnLineageGraph from './ColumnLineageGraph.vue'

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

const parsing = ref(false)
const parseResult = ref<any>(null)
const editor = ref<any>(null)
const showLineageDetail = ref(false)

// 检查是否有血缘图数据可以展示
const showLineageGraph = computed(() => {
  return parseResult.value && 
         parseResult.value.status === 'success' && 
         parseResult.value.column_graph && 
         parseResult.value.column_graph.tables && 
         parseResult.value.column_graph.tables.length > 0
})

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
  setupAutocompletion()
}

const handleEditorChange = () => {
  parseResult.value = null
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
        const response = await metadataAPI.getAutocomplete(word.word, 20)
        const suggestions = response.data.map((item: any) => ({
          label: item.label,
          kind: item.type === 'table' ? monaco.languages.CompletionItemKind.Class : monaco.languages.CompletionItemKind.Field,
          insertText: item.value,
          detail: item.dataType || item.database,
          range: range,
        }))

        return { suggestions }
      } catch (error) {
        console.error('Autocomplete error:', error)
        return { suggestions: [] }
      }
    },
  })
}

const parseSql = async () => {
  if (!sqlCode.value.trim()) {
    ElMessage.warning('请输入SQL代码')
    return
  }

  parsing.value = true
  parseResult.value = null

  try {
    const response = await lineageAPI.parseSQL(sqlCode.value)
    parseResult.value = response.data
    
    if (response.data.status === 'success') {
      ElMessage.success(`成功解析出 ${response.data.relations_count} 个血缘关系`)
      // 如果有血缘图数据，自动显示血缘图
      if (response.data.column_graph && response.data.column_graph.tables && response.data.column_graph.tables.length > 0) {
        showLineageDetail.value = true
      }
    } else {
      ElMessage.error('SQL解析失败')
    }
  } catch (error) {
    console.error('Parse SQL error:', error)
    ElMessage.error('解析失败，请检查SQL语法')
    parseResult.value = { status: 'error', message: '解析服务错误' }
  } finally {
    parsing.value = false
  }
}

const clearEditor = () => {
  sqlCode.value = ''
  parseResult.value = null
  showLineageDetail.value = false
}

const toggleLineageView = () => {
  showLineageDetail.value = !showLineageDetail.value
}

onMounted(() => {
  // Load Monaco Editor
  import('monaco-editor/esm/vs/editor/editor.api').then(() => {
    console.log('Monaco Editor loaded')
  })
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

.parse-result {
  margin-top: 16px;
  padding: 12px;
  background-color: #f5f7fa;
  border-radius: 4px;
}

.result-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
  flex-wrap: wrap;
  gap: 8px;
}

.result-header h4 {
  margin: 0;
  color: #303133;
}

.result-actions {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.lineage-display {
  margin-top: 16px;
  border: 1px solid #e4e7ed;
  border-radius: 4px;
  background: #fff;
}

.no-lineage {
  padding: 20px;
  text-align: center;
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