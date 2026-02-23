<template>
  <div class="backtest-results-container">
    <a-card title="回测结果" :bordered="false">
      <template #extra>
        <a-space>
          <a-button @click="goToConfig" type="primary">
            <template #icon><SettingOutlined /></template>
            回测配置
          </a-button>
          <a-button @click="refreshResults">
            <template #icon><ReloadOutlined /></template>
            刷新
          </a-button>
        </a-space>
      </template>
      
      <ResultPage />
    </a-card>
  </div>
</template>

<script setup>
import { onMounted } from 'vue';
import { useRouter } from 'vue-router';
import { SettingOutlined, ReloadOutlined } from '@ant-design/icons-vue';
import ResultPage from './result/index.vue';

const router = useRouter();

// 跳转到回测配置页面
const goToConfig = () => {
  router.push('/backtest');
};

// 刷新结果页面
const refreshResults = () => {
  window.location.reload();
};

onMounted(() => {
  console.log('📊 回测结果页面已加载');
});
</script>

<style scoped>
.backtest-results-container {
  padding: 20px;
}
</style>
