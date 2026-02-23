<template>
  <div class="min-chart">
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
      
      <!-- 分钟图参数 -->
      <label>日期(YYYY-MM-DD):</label>
      <a-input v-model:value="date" style="width: 120px" />
      <label>近几天:</label>
      <a-select v-model:value="recentDays" style="width: 80px">
        <a-select-option :value="1">1天</a-select-option>
        <a-select-option :value="2">2天</a-select-option>
        <a-select-option :value="3">3天</a-select-option>
      </a-select>
      
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
import { message, Input as AInput, Button as AButton, Select as ASelect, SelectOption as ASelectOption, InputNumber as AInputNumber } from 'ant-design-vue'
import KLineChart from '@/components/KLineChart.vue'
import StockSearch from '@/components/StockSearch.vue'
import { toKline, formatDate, mergeAndSortData } from '@/utils/chartData'
import { computeWilliamsR, computeThresholdPointsWithNear } from '@/utils/williamsR'
import type { StockData, ApiResponse, KlineData, ThresholdPoints, StockSuggestion } from '@/types'
import { getStockDayMinuteData } from '@/api/stocks'

const code = ref('000001')
const date = ref('2025-01-02')
const recentDays = ref(1)
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
  if (lastRows.value.length === 0) return 'K线图(分钟)'
  return `${code.value} 分钟图`
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

// 获取单天数据
const fetchDay = async (codeVal: string, dayStr: string): Promise<ApiResponse> => {
  try {
    return await getStockDayMinuteData(codeVal, dayStr)
  } catch {
    return { code: codeVal, name: '', date: dayStr, data: [] }
  }
}

// 加载数据
const loadData = async () => {
  if (!code.value || !date.value) {
    message.warning('请输入股票代码和日期')
    return
  }
  
  const endDate = new Date(date.value)
  if (isNaN(endDate.getTime())) {
    message.error('日期格式无效')
    return
  }
  
  try {
    let merged: StockData[] = []
    let titleName = ''
    
    if (recentDays.value <= 1) {
      // 单天数据
      const json = await fetchDay(code.value, formatDate(endDate))
      titleName = `${json.code || code.value} ${json.name || ''} ${json.date || date.value}`.trim()
      merged = Array.isArray(json.data) ? json.data : []
    } else {
      // 多天数据
      const tasks: Promise<ApiResponse>[] = []
      const dates: string[] = []
      
      for (let i = recentDays.value - 1; i >= 0; i--) {
        const d = new Date(endDate)
        d.setDate(d.getDate() - i)
        const ds = formatDate(d)
        dates.push(ds)
        tasks.push(fetchDay(code.value, ds))
      }
      
      const results = await Promise.all(tasks)
      const dataArrays: StockData[][] = []
      
      for (const r of results) {
        if (r && Array.isArray(r.data)) {
          dataArrays.push(r.data)
        }
        if (!titleName && r) {
          titleName = `${r.code || code.value} ${r.name || ''}`.trim()
        }
      }
      
      merged = mergeAndSortData(dataArrays)
      titleName = `${titleName} ${dates[0]} ~ ${dates[dates.length - 1]}`
    }
    
    lastRows.value = merged
    
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
.min-chart {
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
