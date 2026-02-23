<template>
  <div class="stock-search">
    <a-input-search
      v-model:value="keyword"
      placeholder="输入股票代码/名称"
      @search="onSearch"
      allow-clear
    />
  </div>
  </template>

<script setup lang="ts">
import { ref } from 'vue'

const keyword = ref('')
const emit = defineEmits<{ (e: 'search', value: string): void }>()

const onSearch = (v: string) => {
  emit('search', (v ?? '').trim())
}
</script>

<style scoped>
.stock-search {
  display: flex;
  gap: 8px;
}
</style>


