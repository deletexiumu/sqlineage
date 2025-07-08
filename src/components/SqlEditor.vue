<template>
  <div class="sql-editor-container">
    <div class="editor-toolbar">
      <el-button-group>
        <el-button @click="formatSql" icon="Edit">格式化</el-button>
        <el-button @click="clearEditor" icon="Delete">清空</el-button>
        <el-button @click="loadExample" icon="Document">示例</el-button>
      </el-button-group>
      
      <div class="editor-info">
        <span>行: {{ currentLine }}</span>
        <span>列: {{ currentColumn }}</span>
        <span>长度: {{ sqlContent.length }}</span>
      </div>
    </div>
    
    <div class="editor-wrapper">
      <textarea
        ref="editor"
        v-model="sqlContent"
        class="sql-textarea"
        :placeholder="placeholder"
        @input="onInput"
        @keydown="onKeyDown"
        @keyup="onKeyUp"
        @click="updateCursorPosition"
      ></textarea>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, nextTick, onMounted } from 'vue';

const props = defineProps({
  modelValue: {
    type: String,
    default: ''
  },
  placeholder: {
    type: String,
    default: '请输入SQL语句...'
  }
});

const emit = defineEmits(['update:modelValue', 'change']);

// 响应式数据
const editor = ref(null);
const sqlContent = ref(props.modelValue);
const currentLine = ref(1);
const currentColumn = ref(1);

// 监听器
watch(() => props.modelValue, (newValue) => {
  if (newValue !== sqlContent.value) {
    sqlContent.value = newValue;
  }
});

watch(sqlContent, (newValue) => {
  emit('update:modelValue', newValue);
  emit('change', newValue);
});

function onInput() {
  updateCursorPosition();
}

function onKeyDown(event) {
  if (event.key === 'Tab') {
    event.preventDefault();
    insertTab();
  }
}

function onKeyUp() {
  updateCursorPosition();
}

function updateCursorPosition() {
  if (!editor.value) return;
  const textarea = editor.value;
  const cursorPos = textarea.selectionStart;
  const textBeforeCursor = sqlContent.value.substring(0, cursorPos);
  const lines = textBeforeCursor.split('\n');
  
  currentLine.value = lines.length;
  currentColumn.value = lines[lines.length - 1].length + 1;
}

function insertTab() {
  if (!editor.value) return;
  
  const textarea = editor.value;
  const start = textarea.selectionStart;
  const end = textarea.selectionEnd;
  
  const before = sqlContent.value.substring(0, start);
  const after = sqlContent.value.substring(end);
  
  sqlContent.value = before + '    ' + after;
  
  nextTick(() => {
    textarea.setSelectionRange(start + 4, start + 4);
  });
}

function formatSql() {
  let formatted = sqlContent.value;
  const keywords = ['SELECT', 'FROM', 'WHERE', 'JOIN', 'GROUP BY', 'ORDER BY', 'INSERT', 'CREATE'];
  
  keywords.forEach(keyword => {
    const regex = new RegExp(`\\b${keyword}\\b`, 'gi');
    formatted = formatted.replace(regex, `\n${keyword}`);
  });
  
  formatted = formatted.replace(/\n\s*\n/g, '\n').trim();
  sqlContent.value = formatted;
}

function clearEditor() {
  sqlContent.value = '';
}

function loadExample() {
  const example = `-- 示例SQL
CREATE TABLE user_summary AS
SELECT 
    user_id,
    COUNT(*) as activity_count
FROM user_events 
WHERE event_date = '2024-01-01'
GROUP BY user_id;`;
  
  sqlContent.value = example;
}
</script>

<style scoped>
.sql-editor-container {
  display: flex;
  flex-direction: column;
  height: 100%;
  border: 1px solid #dcdfe6;
  border-radius: 8px;
  background: white;
}

.editor-toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 10px 15px;
  border-bottom: 1px solid #ebeef5;
  background: #fafafa;
  border-radius: 8px 8px 0 0;
}

.editor-info {
  display: flex;
  gap: 15px;
  font-size: 12px;
  color: #666;
}

.editor-wrapper {
  position: relative;
  flex: 1;
  display: flex;
  min-height: 0; /* 允许flex子元素缩小 */
  overflow: hidden; /* 防止内容溢出 */
}

.sql-textarea {
  flex: 1;
  border: none;
  outline: none;
  padding: 15px;
  font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', monospace;
  font-size: 14px;
  line-height: 1.6;
  resize: none;
  background: transparent;
  color: #2c3e50;
  white-space: pre-wrap; /* 保持空格和换行 */
  word-wrap: break-word; /* 长单词换行 */
  overflow-wrap: break-word; /* 备用属性 */
  overflow-x: auto; /* 水平滚动 */
  overflow-y: auto; /* 垂直滚动 */
  min-height: 300px; /* 最小高度 */
  width: 100%; /* 确保宽度 */
  box-sizing: border-box; /* 包含padding在内的盒模型 */
}
</style>