<template>
  <div class="signal-analysis-with-chart">
    <a-row :gutter="16">
      <!-- 左侧：信号分析 -->
      <a-col :span="8">
        <a-card title="信号分析" size="small" class="analysis-card">
          <SignalAnalysis ref="signalAnalysisRef" @stock-select="handleStockSelect" @dateChange="handleDateChange"
            @analysisLoaded="handleAnalysisLoaded" />
        </a-card>




        <a-card title="自动交易" size="small" class="analysis-card">
          <AutoTrading :data="AnalysisedInfo" :anylysi-ref="signalAnalysisRef"
            :sim-trading-ref="simRef" :began-date="focusStart" :end-date="focusEnd" />
        </a-card>






        <a-card title="模拟交易" size="small" class="analysis-card">
          <SimTrading ref="simRef" />
        </a-card>

        <a-card title="WR计算设置" size="small" class="analysis-card">
          <div class="wr-settings">
            <a-row :gutter="16" align="middle">
              <a-col :span="16">
                <span>启用前端WR计算</span>
                <div class="setting-desc">开启后将在前端实时计算Williams %R指标</div>
              </a-col>
              <a-col :span="8">
                <a-switch v-model:checked="enableFrontendWR" @change="handleWRSettingChange" />
              </a-col>
            </a-row>
          </div>
        </a-card>





      </a-col>

      <!-- 右侧：K线图 -->
      <a-col :span="16">
        <a-card title="K线图" size="small" class="chart-card">
          <KLineChart :data="chartData" :wr6="wr6" :wr10="wr10" :wr6-backend="wr6Backend" :wr10-backend="wr10Backend"
            :buy-points-backend="chartData.buyPointsBackend" :sell-points-backend="chartData.sellPointsBackend"
            :threshold-points="thresholdPoints" :title="chartTitle" :show-backend-wr="true"
            :focus-start-date="focusStart" :focus-end-date="focusEnd" :focus-trigger-key="focusTriggerKey"
            @bar-click="handleBarClick" @date-range-change="handleDateRangeChange" />
        </a-card>
      </a-col>
    </a-row>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, nextTick } from 'vue'
import { message, Card as ACard, Row as ARow, Col as ACol } from 'ant-design-vue'
import KLineChart from '@/components/KLineChart.vue'
import SignalAnalysis from '@/components/SignalAnalysis.vue'
import SimTrading from '@/components/SimTrading.vue'
import AutoTrading from '@/components/AutoTrading.vue'
import { toKline } from '@/utils/chartData'
import { computeWilliamsR, computeThresholdPointsWithNear } from '@/utils/williamsR'
import type { StockData, ApiResponse, KlineData, ThresholdPoints, StockSignalInfo } from '@/types'
import { getStockDailyLocalData } from '@/api/stocks'

const code = ref('000001')
const start = ref('')
const end = ref('')

const focusStart = ref('')
const focusEnd = ref('')
const focusTriggerKey = ref(0)

// 前端WR计算开关，默认关闭
const enableFrontendWR = ref(false)

const lastRows = ref<StockData[]>([])
const selectedRow = ref<StockData | null>(null)
const simRef = ref<any>(null)
const signalAnalysisRef = ref<any>(null)
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
  const base = selectedRow.value ? String((selectedRow.value as any).名称 || '') : (lastRows.value[0]?.名称 || '')
  const nameDisplay = base ? ` - ${base}` : ''
  return `${code.value}${nameDisplay} 日线图(本地数据)`
})

// 处理股票选择
const handleStockSelect = (stock: StockSignalInfo) => {
  code.value = stock.code
  // 自动加载数据
  loadData()
}

const AnalysisedInfo = ref<any>({
  start: '',
  end: '',
  minSignals: 0,
  signalType: '',
  stocks: []
})

// 接收信号分析完成事件
const handleAnalysisLoaded = (payload: { start: string; end: string; minSignals: number; signalType: string; stocks: StockSignalInfo[] }) => {
  console.log('信号分析完成:', payload)
  AnalysisedInfo.value = payload
}

// 接收日期变化（用于聚焦）：改为 [end-3个月, end]
const handleDateChange = ({ end }: { start: string; end: string }) => {
  const endStr = end || ''
  let startMinus3 = ''
  if (endStr) {
    const d = new Date(endStr)
    if (!isNaN(d.getTime())) {
      const m = new Date(d)
      m.setMonth(m.getMonth() - 6)
      const y = m.getFullYear()
      const mm = String(m.getMonth() + 1).padStart(2, '0')
      const dd = String(m.getDate()).padStart(2, '0')
      startMinus3 = `${y}-${mm}-${dd}`
    }
  }
  focusStart.value = startMinus3
  focusEnd.value = endStr
  // 修改 key 以便强制子组件在未被用户拖动时聚焦一次
  focusTriggerKey.value++
  console.log('focusStart:', focusStart.value)
  console.log('focusEnd:', focusEnd.value)
}

// 点击K线/柱子：设置选中行
const handleBarClick = ({ index }: { index: number; date: string }) => {
  if (!lastRows.value || lastRows.value.length === 0) return
  const idx = Math.min(Math.max(0, index), lastRows.value.length - 1)
  selectedRow.value = lastRows.value[idx]
  // 同步到模拟交易面板
  try {
    const row: any = selectedRow.value || {}
    const name = String(row.名称 || '')
    const close = Number(row['收盘'] || 0)
    const time = String(row['日期'] || '')
    nextTick(() => simRef.value?.setValue(code.value, name, close, time))
  } catch { }
}



// 处理日期范围变化
const handleDateRangeChange = ({ startDate, endDate }: { startDate: string; endDate: string }) => {
  console.log('当前查看的日期范围:', { startDate, endDate })
  // 仅用于前端聚焦展示，不再影响后端趋势计算
}

// 加载数据
const loadData = async () => {
  if (!code.value) {
    message.warning('请输入股票代码')
    return
  }

  try {
    // daily-local 始终加载全量历史，忽略 start/end，不拼接查询参数
    const json: ApiResponse = await getStockDailyLocalData(code.value)
    lastRows.value = Array.isArray(json.data) ? json.data : []
    selectedRow.value = lastRows.value.length > 0 ? lastRows.value[lastRows.value.length - 1] : null

    // 转换数据
    chartData.value = toKline(lastRows.value)

    // 提取后端WR数据
    wr6Backend.value = chartData.value.wr6Backend || []
    wr10Backend.value = chartData.value.wr10Backend || []

    // 根据开关状态决定是否计算前端Williams R指标
    if (enableFrontendWR.value) {
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
    } else {
      // 开关关闭时，清空前端WR数据
      wr10.value = []
      wr6.value = []
      thresholdPoints.value = {
        buyPoints: [],
        sellPoints: []
      }
    }


    message.success('数据加载成功')
  } catch (error) {
    console.error('加载数据失败:', error)
    message.error('加载数据失败')
  }
}

// WR 指标固定使用 6 天与 10 天

// 处理WR设置变化
const handleWRSettingChange = () => {
  // 如果当前有数据，重新计算或清空WR数据
  if (lastRows.value && lastRows.value.length > 0) {
    if (enableFrontendWR.value) {
      // 开启时重新计算前端WR
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
    } else {
      // 关闭时清空前端WR数据
      wr10.value = []
      wr6.value = []
      thresholdPoints.value = {
        buyPoints: [],
        sellPoints: []
      }
    }
  }
}




</script>

<style scoped>
.signal-analysis-with-chart {
  padding: 16px;

}

.analysis-card {

  overflow-y: auto;
  margin-bottom: 16px;
}

.chart-card {

  overflow-y: auto;
}

.chart-toolbar {
  display: flex;
  gap: 12px;
  align-items: center;
  margin-bottom: 12px;
  flex-wrap: wrap;
}

.chart-toolbar label {
  white-space: nowrap;
  font-weight: 500;
}

:deep(.ant-card-body) {
  height: calc(100% - 57px);
  overflow: hidden;
}

.wr-settings {
  padding: 8px 0;
}

.setting-desc {
  font-size: 12px;
  color: #666;
  margin-top: 4px;
}
</style>
