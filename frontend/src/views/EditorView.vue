<template>
  <div class="editor-view">
    <SQLEditor />
  </div>
</template>

<script setup lang="ts">
import SQLEditor from '@/components/SQLEditor.vue'
</script>

<style scoped>
.editor-view {
  height: 100%;
  overflow: auto;
}

/* 响应式设计 */
@media (max-width: 768px) {
  .editor-view {
    height: calc(100vh - 60px);
  }
}
</style>