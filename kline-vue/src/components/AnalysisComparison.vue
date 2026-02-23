<template>
  <a-card title="分析结果对比" style="margin-top: 16px;" v-if="jsonLogicResults.results.length > 0">
    <template #extra>
      <a-tag color="blue">传统分析</a-tag>
      <a-tag color="green">JSONLogic分析</a-tag>
    </template>
    
    <a-row :gutter="16">
      <a-col :span="12">
        <h4>传统信号分析</h4>
        <a-descriptions size="small" :column="2">
          <a-descriptions-item label="分析方式">基于预定义规则</a-descriptions-item>
          <a-descriptions-item label="规则类型">固定条件组合</a-descriptions-item>
          <a-descriptions-item label="灵活性">中等</a-descriptions-item>
          <a-descriptions-item label="可配置性">有限</a-descriptions-item>
        </a-descriptions>
      </a-col>
      <a-col :span="12">
        <h4>JSONLogic 分析</h4>
        <a-descriptions size="small" :column="2">
          <a-descriptions-item label="分析方式">基于 JSONLogic 规则</a-descriptions-item>
          <a-descriptions-item label="规则类型">动态条件组合</a-descriptions-item>
          <a-descriptions-item label="灵活性">高</a-descriptions-item>
          <a-descriptions-item label="可配置性">完全可配置</a-descriptions-item>
        </a-descriptions>
      </a-col>
    </a-row>

    <a-divider />

    <a-row :gutter="16">
      <a-col :span="12">
        <h4>JSONLogic 分析结果</h4>
        <a-statistic-group>
          <a-statistic title="总股票数" :value="jsonLogicResults.summary.totalStocks" />
          <a-statistic title="符合条件" :value="jsonLogicResults.summary.matchedStocks" />
          <a-statistic title="匹配率" :value="jsonLogicResults.summary.matchRate" suffix="%" :precision="2" />
          <a-statistic title="分析时间" :value="jsonLogicResults.summary.analysisTime" suffix="ms" />
        </a-statistic-group>
      </a-col>
            <a-col :span="12">
              <h4>规则配置</h4>
              <a-collapse size="small">
                <a-collapse-panel key="signal" header="信号分析规则">
                  <pre style="font-size: 12px; background: #f5f5f5; padding: 8px; border-radius: 4px;">{{ JSON.stringify(jsonLogicResults.rules.signal, null, 2) }}</pre>
                </a-collapse-panel>
              </a-collapse>
            </a-col>
    </a-row>
  </a-card>
</template>

<script setup>
defineProps({
  jsonLogicResults: {
    type: Object,
    default: () => ({
      results: [],
      summary: {},
      rules: {}
    })
  }
});
</script>

<style scoped>
h4 {
  margin-bottom: 12px;
  color: #1890ff;
}
</style>
