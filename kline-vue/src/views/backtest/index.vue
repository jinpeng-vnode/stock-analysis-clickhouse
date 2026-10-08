<template>
  <div class="backtest-container">
    <ConfigPage @run-backtest="handleRunBacktest" />
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue';
import { message } from 'ant-design-vue';
import { useRouter } from 'vue-router';
import { BarChartOutlined } from '@ant-design/icons-vue';
import ConfigPage from './config/index.vue';

const router = useRouter();

// 处理运行回测事件
const handleRunBacktest = () => {
  // 回测完成后跳转到结果页面
  goToResults();
};

// 跳转到回测结果页面
const goToResults = () => {
  router.push('/backtest/results');
};


onMounted(() => {
  console.log('🚀 回测系统已加载');
  console.log('💡 可以访问 http://localhost:9000/backtest 查看回测系统');
});
</script>

<style scoped>
.backtest-container {
  padding: 20px;
}
</style>

