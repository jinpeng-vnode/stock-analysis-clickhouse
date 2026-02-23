<template>
  <div class="day-chart">
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
      
      <label style="margin-left: 12px;">Williams周期 n:</label>
      <a-input-number
        v-model:value="wrN"
        :min="2"
        :max="200"
        style="width: 80px"
        @change="handleWrChange"
      />
    </div>
    
    <KLineChart
      :data="chartData"
      :wr6="wr6"
      :wr10="wr10"
      :threshold-points="thresholdPoints"
      :title="chartTitle"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { message, Input as AInput, Button as AButton, InputNumber as AInputNumber } from 'ant-design-vue'
import KLineChart from '@/components/KLineChart.vue'
import StockSearch from '@/components/StockSearch.vue'
import { toKline } from '@/utils/chartData'
import { computeWilliamsR, computeThresholdPointsWithNear } from '@/utils/williamsR'
import type { StockData, ApiResponse, KlineData, ThresholdPoints, StockSuggestion } from '@/types'
import { getStockDailyData } from '@/api/stocks'

const code = ref('000001')
const start = ref('')
const end = ref('')
const wrN = ref(14)
const searchQuery = ref('')

const lastRows = ref<StockData[]>([])
const chartData = ref<KlineData>({
  category: [],
  values: [],
  volumes: [],
  highs: [],
  lows: [],
  closes: []
})

const wr6 = ref<number[]>([])
const wr10 = ref<number[]>([])
const thresholdPoints = ref<ThresholdPoints>({
  buyPoints: [],
  sellPoints: []
})

const chartTitle = computed(() => {
  if (lastRows.value.length === 0) return 'K线图'
  // 这里可以根据实际API响应调整
  return `${code.value} 日线图`
})

// 处理股票选择
const handleStockSelect = (suggestion: StockSuggestion) => {
  code.value = suggestion.code
}

// 处理WR周期变化
const handleWrChange = (value: number | string | null) => {
  const numValue = typeof value === 'string' ? Number(value) : value
  if (numValue !== null && !isNaN(numValue)) {
    wrN.value = numValue
  }
}

// 加载数据
const loadData = async () => {
  if (!code.value) {
    message.warning('请输入股票代码')
    return
  }
  
  try {
    const json: ApiResponse = await getStockDailyData(code.value, { start: start.value, end: end.value })
    lastRows.value = Array.isArray(json.data) ? json.data : []
    
    // 转换数据
    chartData.value = toKline(lastRows.value)
    
    // 计算Williams R指标
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

// 重新计算WR指标
const recalcWR = () => {
  if (!lastRows.value || lastRows.value.length === 0) return
  
  const { highs, lows, closes } = chartData.value
  wr10.value = computeWilliamsR(highs, lows, closes, 10)
  wr6.value = computeWilliamsR(highs, lows, closes, 6)
  
  thresholdPoints.value = computeThresholdPointsWithNear(
    chartData.value.category,
    wr6.value,
    wr10.value,
    80,
    20,
    1
  )
}

// 监听WR周期变化
watch(() => wrN.value, () => {
  recalcWR()
})
</script>

<style scoped>
.day-chart {
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
