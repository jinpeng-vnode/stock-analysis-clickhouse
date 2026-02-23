<template>
  <div class="day-local-chart">
    <div class="toolbar">
      <label>API:</label>
      <a-input v-model:value="apiBase" style="width: 260px" />
      
      <StockSearch
        v-model="searchQuery"
        :api-base="apiBase"
        @select="handleStockSelect"
      />
      
      <label>代码:</label>
      <a-input v-model:value="code" style="width: 100px" />
      
      <!-- 日线图参数 -->
      <label>开始日期:</label>
      <a-input 
        v-model:value="start" 
        placeholder="YYYY-MM-DD" 
        style="width: 120px" 
      />
      <label>结束日期:</label>
      <a-input 
        v-model:value="end" 
        placeholder="YYYY-MM-DD" 
        style="width: 120px" 
      />
      
      <a-button type="primary" @click="loadData">加载</a-button>
      
      
    </div>
    
    <KLineChart
      :data="chartData"
      :wr6="wr6"
      :wr10="wr10"
      :wr6-backend="wr6Backend"
      :wr10-backend="wr10Backend"
      :threshold-points="thresholdPoints"
      :title="chartTitle"
      :show-backend-wr="true"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { message, Input as AInput, Button as AButton } from 'ant-design-vue'
import KLineChart from '@/components/KLineChart.vue'
import StockSearch from '@/components/StockSearch.vue'
import { toKline } from '@/utils/chartData'
import { computeWilliamsR, computeThresholdPointsWithNear } from '@/utils/williamsR'
import type { StockData, ApiResponse, KlineData, ThresholdPoints, StockSuggestion } from '@/types'
import { getStockDailyLocalData } from '@/api/stocks'

const code = ref('000001')
const start = ref('')
const end = ref('')
const searchQuery = ref('')

const lastRows = ref<StockData[]>([])
const chartData = ref<KlineData>({
  category: [],
  values: [],
  volumes: [],
  highs: [],
  lows: [],
  closes: [],
  wr6Backend: [],
  wr10Backend: []
})

const wr6 = ref<number[]>([])
const wr10 = ref<number[]>([])
const wr6Backend = ref<number[]>([])
const wr10Backend = ref<number[]>([])
const thresholdPoints = ref<ThresholdPoints>({
  buyPoints: [],
  sellPoints: []
})

const chartTitle = computed(() => {
  if (lastRows.value.length === 0) return 'K线图(本地数据)'
  return `${code.value} 日线图(本地数据)`
})

// 处理股票选择
const handleStockSelect = (suggestion: StockSuggestion) => {
  code.value = suggestion.code
}


// 加载数据
const loadData = async () => {
  if (!code.value) {
    message.warning('请输入股票代码')
    return
  }
  
  try {
    const json: ApiResponse = await getStockDailyLocalData(code.value, { start: start.value, end: end.value })
    lastRows.value = Array.isArray(json.data) ? json.data : []
    
    // 转换数据
    chartData.value = toKline(lastRows.value)
    
    // 提取后端WR数据
    wr6Backend.value = chartData.value.wr6Backend || []
    wr10Backend.value = chartData.value.wr10Backend || []
    
    // 计算前端Williams R指标
    const { highs, lows, closes } = chartData.value
    wr10.value = computeWilliamsR(highs, lows, closes, 10)
    wr6.value = computeWilliamsR(highs, lows, closes, 6)
    
    // 计算买卖点
    thresholdPoints.value = computeThresholdPointsWithNear(
      chartData.value.category,
      wr6.value,
      wr10.value,
      80,
      20,
      1
    )
    
    message.success('数据加载成功')
  } catch (error) {
    console.error('加载数据失败:', error)
    message.error('加载数据失败')
  }
}

// WR 指标固定使用 6 天与 10 天，已在加载时计算


</script>

<style scoped>
.day-local-chart {
  padding: 16px;
}

.toolbar {
  display: flex;
  gap: 12px;
  align-items: center;
  margin-bottom: 12px;
  flex-wrap: wrap;
}

.toolbar label {
  white-space: nowrap;
  font-weight: 500;
}
</style>
