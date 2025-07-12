<template>
  <div class="lineage-view">
    <LineageGraph />
  </div>
</template>

<script setup lang="ts">
import LineageGraph from '@/components/LineageGraph.vue'
</script>

<style scoped>
.lineage-view {
  height: 100%;
  overflow: auto;
}

/* 响应式设计 */
@media (max-width: 768px) {
  .lineage-view {
    height: calc(100vh - 60px);
  }
}
</style>