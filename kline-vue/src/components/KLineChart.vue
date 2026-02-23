<template>
  <div ref="chartRef" class="kline-chart"></div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, watch, nextTick } from 'vue'
import * as echarts from 'echarts'
import type { KlineData, ThresholdPoints } from '@/types'

interface Props {
  data: KlineData
  thresholdPoints?: ThresholdPoints
  wr6?: number[]
  wr10?: number[]
  wr6Backend?: number[]
  wr10Backend?: number[]
  title?: string
  showBackendWR?: boolean
  // 新增：按照日期聚焦
  focusStartDate?: string
  focusEndDate?: string
  // 每次父组件需要强制尝试聚焦时递增
  focusTriggerKey?: number
  // 是否显示拟合趋势线（基于收盘价的线性回归）
  showTrendLine?: boolean
  // 预留：拟合窗口（未使用，未来可用于仅拟合最近N根）
  trendWindow?: number
}

const props = withDefaults(defineProps<Props>(), {
  showBackendWR: true,
  focusStartDate: '',
  focusEndDate: '',
  focusTriggerKey: 0,
  showTrendLine: true,
  trendWindow: 0
})

const chartRef = ref<HTMLDivElement>()
let chart: echarts.ECharts | null = null

// 记录用户是否通过拖动/缩放交互过
let userZoomed = false
let lastAppliedTriggerKey = -1

// 防抖定时器
let debounceTimer: ReturnType<typeof setTimeout> | null = null

// 向上提交柱/蜡烛点击事件和日期范围变化事件
interface Emits {
  (e: 'bar-click', payload: { index: number; date: string }): void
  (e: 'date-range-change', payload: { startDate: string; endDate: string }): void
}
const emit = defineEmits<Emits>()

// 初始化图表
const initChart = () => {
  if (!chartRef.value) return
  
  chart = echarts.init(chartRef.value)
  
  // 监听窗口大小变化
  window.addEventListener('resize', handleResize)

  // 监听用户缩放交互
  chart.on('datazoom', () => {
    userZoomed = true
    // 防抖提交当前可视的日期范围
    if (debounceTimer) {
      clearTimeout(debounceTimer)
    }
    debounceTimer = setTimeout(() => {
      const dateRange = getCurrentVisibleDateRange()
      if (dateRange) {
        emit('date-range-change', {
          startDate: dateRange.startDate,
          endDate: dateRange.endDate
        })
      }
    }, 300) // 300ms防抖延迟
  })

  // 监听点击蜡烛/柱子事件并向上提交索引与日期
  chart.on('click', (params: any) => {
    try {
      if (!props.data || !props.data.category) return
      const idx = typeof params?.dataIndex === 'number' ? params.dataIndex : -1
      if (idx < 0 || idx >= props.data.category.length) return
      const date = String(props.data.category[idx] || '')
      emit('bar-click', { index: idx, date })
    } catch {
      // ignore
    }
  })
}

// 处理窗口大小变化
const handleResize = () => {
  if (chart) {
    chart.resize()
  }
}

// 根据日期或默认逻辑计算需要的 dataZoom 范围
const buildDataZoom = (category: string[]) => {
  if (!category || category.length === 0) return undefined

  // 如果用户已交互，则不再覆盖视图
  if (userZoomed) return undefined

  // 优先使用外部指定的日期范围
  const start = props.focusStartDate || ''
  const end = props.focusEndDate || ''

  if (start || end) {
    const { startValue, endValue } = calculateRangeByDates(category, start, end)
    if (startValue && endValue) {
      return [{ type: 'inside', xAxisIndex: [0, 1, 2], startValue, endValue }]
    }
  }

  // 回退：最近三个月
  const { startValue, endValue } = calculateDateRange(category)
  if (startValue && endValue) {
    return [{ type: 'inside', xAxisIndex: [0, 1, 2], startValue, endValue }]
  }
  return [{ type: 'inside', xAxisIndex: [0, 1, 2], start: 0, end: 100 }]
}

// 更新图表配置
const updateChart = () => {
  if (!chart || !props.data) return
  
  const { category, values, volumes } = props.data
  const closes: number[] = (props.data as any).closes || []
  const visible = getCurrentVisibleIndexRange(category)
  const trendLineData = props.showTrendLine ? computeLinearTrendOnRange(closes, visible) : []

  const maybeDataZoom = buildDataZoom(category)
  
  const option: echarts.EChartsOption = {
    title: [
      { 
        text: props.title || 'K线图', 
        left: 16, 
        top: 8 
      },
      { 
        text: 'K线(日)', 
        left: 60, 
        top: 34, 
        textStyle: { 
          fontSize: 12, 
          fontWeight: 'normal', 
          color: '#666' 
        } 
      },
      { 
        text: '成交量', 
        left: 60, 
        top: 670, 
        textStyle: { 
          fontSize: 12, 
          fontWeight: 'normal', 
          color: '#666' 
        } 
      },
      { 
        text: props.showBackendWR 
          ? 'Williams %R 前端(10,6) vs 后端(10,6)' 
          : 'Williams %R (n=10, 6)', 
        left: 60, 
        top: 920, 
        textStyle: { 
          fontSize: 12, 
          fontWeight: 'normal', 
          color: '#666' 
        } 
      }
    ],
    tooltip: { 
      trigger: 'axis',
      axisPointer: {
        type: 'cross',
        label: { backgroundColor: '#777' }
      }
    },
    axisPointer: { 
      show: true,
      triggerTooltip: true,
      link: [{ xAxisIndex: 'all' }]
    },
    grid: [
      { left: 60, right: 20, top: 70, height: 460 },
      { left: 60, right: 20, top: 600, height: 150 },
      { left: 60, right: 20, top: 820, height: 150 }
    ],
    xAxis: [
      { 
        type: 'category', 
        data: category, 
        boundaryGap: true, 
        axisLine: { onZero: false }, 
        axisTick: { show: false } 
      },
      { 
        type: 'category', 
        data: category, 
        gridIndex: 1, 
        boundaryGap: true, 
        axisTick: { show: false } 
      },
      { 
        type: 'category', 
        data: category, 
        gridIndex: 2, 
        boundaryGap: true, 
        axisTick: { show: false } 
      }
    ],
    yAxis: [
      { scale: true },
      { gridIndex: 1 },
      { gridIndex: 2, min: 0, max: 100 }
    ],
    // 仅当需要时设置 dataZoom，以避免覆盖用户拖动后的视图
    ...(maybeDataZoom ? { dataZoom: maybeDataZoom } as any : {}),
    series: [
      { 
        name: 'K线', 
        type: 'candlestick', 
        data: values 
      },
      // 拟合趋势线（基于收盘价的全量线性回归）
      ...(props.showTrendLine && trendLineData && trendLineData.length > 0 ? [{
        name: '拟合趋势线',
        type: 'line',
        xAxisIndex: 0,
        yAxisIndex: 0,
        data: trendLineData,
        showSymbol: false,
        smooth: false,
        lineStyle: { width: 1.5, color: '#fa8c16', type: 'dashed' },
        emphasis: { focus: 'series' }
      }] : []),
      { 
        name: '成交量', 
        type: 'bar', 
        xAxisIndex: 1, 
        yAxisIndex: 1, 
        data: volumes 
      },
      ...(props.wr10 ? [{
        name: props.showBackendWR ? 'WR(10) 前端' : 'Williams %R (10)',
        type: 'line',
        xAxisIndex: 2,
        yAxisIndex: 2,
        data: props.wr10,
        showSymbol: false,
        smooth: false,
        lineStyle: { width: 1, color: '#2f7ed8' }
      }] : []),
      // 后端买点（从 data 中读取，避免修改 Props）
      ...(props.data && (props.data as any).buyPointsBackend && (props.data as any).buyPointsBackend.length > 0 ? [{
        name: '后端买点',
        type: 'scatter',
        xAxisIndex: 2,
        yAxisIndex: 2,
        data: (props.data as any).buyPointsBackend,
        symbol: 'triangle',
        symbolSize: 12,
        itemStyle: { color: '#52c41a' },
        label: {
          show: true,
          formatter: () => '买',
          color: '#52c41a',
          fontWeight: 'bold',
          position: 'top',
          fontSize: 10
        }
      }] : []),
      // 后端卖点（从 data 中读取，避免修改 Props）
      ...(props.data && (props.data as any).sellPointsBackend && (props.data as any).sellPointsBackend.length > 0 ? [{
        name: '后端卖点',
        type: 'scatter',
        xAxisIndex: 2,
        yAxisIndex: 2,
        data: (props.data as any).sellPointsBackend,
        symbol: 'diamond',
        symbolSize: 12,
        itemStyle: { color: '#ff4d4f' },
        label: {
          show: true,
          formatter: () => '卖',
          color: '#ff4d4f',
          fontWeight: 'bold',
          position: 'bottom',
          fontSize: 10
        }
      }] : []),
      ...(props.wr6 ? [{
        name: props.showBackendWR ? 'WR(6) 前端' : 'Williams %R (6)',
        type: 'line',
        xAxisIndex: 2,
        yAxisIndex: 2,
        data: props.wr6,
        showSymbol: false,
        smooth: false,
        lineStyle: { width: 1, color: '#d82f7e' }
      }] : []),
      ...(props.showBackendWR && props.wr10Backend ? [{
        name: 'WR(10) 后端',
        type: 'line',
        xAxisIndex: 2,
        yAxisIndex: 2,
        data: props.wr10Backend,
        showSymbol: false,
        smooth: false,
        lineStyle: { width: 1, color: '#7cb5ec', type: 'dashed' }
      }] : []),
      ...(props.showBackendWR && props.wr6Backend ? [{
        name: 'WR(6) 后端',
        type: 'line',
        xAxisIndex: 2,
        yAxisIndex: 2,
        data: props.wr6Backend,
        showSymbol: false,
        smooth: false,
        lineStyle: { width: 1, color: '#ec7caa', type: 'dashed' }
      }] : []),
      ...(props.thresholdPoints?.buyPoints ? [{
        name: '>80 且差值<1 买',
        type: 'scatter',
        xAxisIndex: 2,
        yAxisIndex: 2,
        data: props.thresholdPoints.buyPoints,
        symbol: 'circle',
        symbolSize: 9,
        itemStyle: { color: '#52c41a' },
        label: { 
          show: true, 
          formatter: () => '买', 
          color: '#52c41a', 
          fontWeight: 'bold', 
          position: 'top' 
        }
      }] : []),
      ...(props.thresholdPoints?.sellPoints ? [{
        name: '<20 且差值<1 卖',
        type: 'scatter',
        xAxisIndex: 2,
        yAxisIndex: 2,
        data: props.thresholdPoints.sellPoints,
        symbol: 'rect',
        symbolSize: 9,
        itemStyle: { color: '#f5222d' },
        label: { 
          show: true, 
          formatter: () => '卖', 
          color: '#f5222d', 
          fontWeight: 'bold', 
          position: 'bottom' 
        }
      }] : [])
    ]
  }
  
  chart.setOption(option, true)
}

// 旧的全量拟合方法已不再使用；如需恢复，可从版本历史中查阅

// 获取当前可视范围的索引（startIndex, endIndex），若不可用则返回全量
function getCurrentVisibleIndexRange(category: string[]): { startIndex: number; endIndex: number } {
  try {
    if (!chart || !category || category.length === 0) {
      return { startIndex: 0, endIndex: Math.max(0, category.length - 1) }
    }
    const option = chart.getOption() as any
    const dz = Array.isArray(option.dataZoom) && option.dataZoom.length > 0 ? option.dataZoom[0] : null
    if (!dz) return { startIndex: 0, endIndex: category.length - 1 }
    // ECharts 内部会把 startValue/endValue 表示为索引
    const start = typeof dz.startValue === 'number' ? dz.startValue : 0
    const end = typeof dz.endValue === 'number' ? dz.endValue : category.length - 1
    const startIndex = Math.max(0, Math.min(start, category.length - 1))
    const endIndex = Math.max(startIndex, Math.min(end, category.length - 1))
    return { startIndex, endIndex }
  } catch {
    return { startIndex: 0, endIndex: Math.max(0, category.length - 1) }
  }
}

// 仅在可视窗口范围内拟合；返回与全量长度一致的数组，不在窗口外的索引填 null 以避免绘图
function computeLinearTrendOnRange(values: number[], range: { startIndex: number; endIndex: number }): (number | null)[] {
  if (!Array.isArray(values) || values.length === 0) return []
  const n = values.length
  const { startIndex, endIndex } = range || { startIndex: 0, endIndex: n - 1 }
  const s = Math.max(0, Math.min(startIndex, n - 1))
  const e = Math.max(s, Math.min(endIndex, n - 1))

  const m = e - s + 1
  if (m <= 1) {
    // 单点或空区间：返回对应点水平线
    const base = Number(values[s] ?? values[0] ?? 0)
    const out: (number | null)[] = new Array(n).fill(null)
    if (Number.isFinite(base)) {
      for (let i = s; i <= e; i++) out[i] = base
    }
    return out
  }

  let sumX = 0
  let sumY = 0
  let sumXY = 0
  let sumXX = 0
  for (let i = s; i <= e; i++) {
    const x = i - s // 窗口内相对索引，提升数值稳定性
    const y = Number(values[i])
    if (!Number.isFinite(y)) continue
    sumX += x
    sumY += y
    sumXY += x * y
    sumXX += x * x
  }
  const nWin = e - s + 1
  const denominator = nWin * sumXX - sumX * sumX
  let slope = 0
  let intercept = 0
  if (denominator === 0) {
    const mean = sumY / (nWin || 1)
    intercept = mean
    slope = 0
  } else {
    slope = (nWin * sumXY - sumX * sumY) / denominator
    intercept = (sumY - slope * sumX) / nWin
  }

  const out: (number | null)[] = new Array(n).fill(null)
  for (let i = s; i <= e; i++) {
    const x = i - s
    out[i] = intercept + slope * x
  }
  return out
}

// 计算日期范围（默认过去 n 个月）
const calculateDateRange = (category: string[], months: number = 3) => {
  if (!category || category.length === 0) {
    return {}
  }
  
  const lastDateStr = category[category.length - 1]
  const lastDate = new Date(lastDateStr)
  
  if (isNaN(lastDate.getTime())) {
    return {}
  }
  
  const targetDate = new Date(lastDate)
  targetDate.setMonth(targetDate.getMonth() - months)
  
  let startIdx = 0
  for (let i = 0; i < category.length; i++) {
    const d = new Date(category[i])
    if (!isNaN(d.getTime()) && d >= targetDate) {
      startIdx = i
      break
    }
  }
  
  return {
    startValue: category[startIdx],
    endValue: category[category.length - 1]
  }
}

// 按外部给定的开始/结束日期计算范围（若缺失则用边界）
const calculateRangeByDates = (category: string[], start: string, end: string) => {
  if (!category || category.length === 0) return {}
  let startIdx = 0
  let endIdx = category.length - 1

  if (start) {
    const s = new Date(start)
    for (let i = 0; i < category.length; i++) {
      const d = new Date(category[i])
      if (!isNaN(d.getTime()) && d >= s) { startIdx = i; break }
    }
  }
  if (end) {
    const e = new Date(end)
    for (let i = category.length - 1; i >= 0; i--) {
      const d = new Date(category[i])
      if (!isNaN(d.getTime()) && d <= e) { endIdx = i; break }
    }
  }
  if (startIdx > endIdx) {
    // 如果区间无效，回退到默认窗口
    return calculateDateRange(category)
  }
  return { startValue: category[startIdx], endValue: category[endIdx] }
}

// 获取当前可视的日期范围
const getCurrentVisibleDateRange = () => {
  if (!chart || !props.data || !props.data.category) return null
  
  try {
    // 使用getOption获取dataZoom配置
    const option = chart.getOption()
    const dataZoomArray = option.dataZoom as any[]
    
    if (!dataZoomArray || dataZoomArray.length === 0) return null
    
    const dataZoom = dataZoomArray[0]
    if (!dataZoom) return null
    
    const startValue = dataZoom.startValue
    const endValue = dataZoom.endValue
    
    if (startValue === undefined || endValue === undefined) return null
    
    const category = props.data.category
    const startDate = category[startValue] || ''
    const endDate = category[endValue] || ''
    
    return { startDate, endDate }
  } catch (error) {
    console.warn('获取日期范围失败:', error)
    return null
  }
}

// 监听数据变化
watch(() => props.data, () => {
  // 切换数据源时重置用户缩放状态，从而允许新的聚焦区间生效
  userZoomed = false
  nextTick(() => {
    updateChart()
  })
}, { deep: true })

watch(() => [props.wr6, props.wr10, props.thresholdPoints], () => {
  nextTick(() => {
    updateChart()
  })
}, { deep: true })

// 监听外部触发的聚焦请求
watch(() => props.focusTriggerKey, (key) => {
  // 避免重复应用同一个 key
  if (key === undefined || key === null) return
  if (key === lastAppliedTriggerKey) return
  lastAppliedTriggerKey = key as number

  // 仅当用户尚未缩放时应用聚焦
  if (!userZoomed) {
    nextTick(() => updateChart())
  }
})

onMounted(() => {
  nextTick(() => {
    initChart()
    updateChart()
  })
})

onUnmounted(() => {
  if (chart) {
    chart.dispose()
    chart = null
  }
  window.removeEventListener('resize', handleResize)
})
</script>

<style scoped>
.kline-chart {
  width: 100%;
  height: 1200px;
  box-sizing: border-box;
}
</style>
