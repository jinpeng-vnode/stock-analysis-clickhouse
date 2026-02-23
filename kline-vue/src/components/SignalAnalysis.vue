<template>
  <a-config-provider :locale="zhCN">
  <div class="signal-analysis">
    <div class="toolbar">
      <div class="toolbar-row">
        <label>API:</label>
        <a-input v-model:value="apiBase" style="width: 260px" />
        <label>Today日期:</label>
        <a-date-picker 
          v-model:value="today" 
          placeholder="选择Today日期"
          style="width: 140px"
          format="YYYY-MM-DD"
          value-format="YYYY-MM-DD"
          @change="handleTodayChange"
        />
      </div>
      
      <div class="toolbar-row">
        <label>开始日期:</label>
        <a-date-picker 
          v-model:value="startDate" 
          placeholder="选择开始日期"
          style="width: 140px"
          format="YYYY-MM-DD"
          value-format="YYYY-MM-DD"
        />
        <label>结束日期:</label>
        <a-date-picker 
          v-model:value="endDate" 
          placeholder="选择结束日期"
          style="width: 140px"
          format="YYYY-MM-DD"
          value-format="YYYY-MM-DD"
        />
        
        <a-button-group style="margin-left: 8px;">
          <a-button size="small" @click="setDateRange(0.25)">近7天</a-button>
          <a-button size="small" @click="setDateRange(1)">近1个月</a-button>
          <a-button size="small" @click="setDateRange(3)">近3个月</a-button>
          <a-button size="small" @click="setDateRange(12)">近1年</a-button>
        </a-button-group>
      </div>
      
      <div class="toolbar-row">
        <label>最小信号数:</label>
        <a-input-number
          v-model:value="minSignals"
          :min="1"
          :max="1000"
          style="width: 100px"
        />
      </div>
      
    
      
      <div class="toolbar-row">
        <label>信号类型:</label>
        <a-radio-group v-model:value="signalType">
          <a-radio-button value="all">全部</a-radio-button>
          <a-radio-button value="buy">买点</a-radio-button>
          <a-radio-button value="sell">卖点</a-radio-button>
        </a-radio-group>
      </div>
      <div class="toolbar-row">
        <a-button type="primary" @click="loadSignalData" :loading="loading">
          分析信号
        </a-button>
      </div>
    </div>
    
    <div class="analysis-result">
      <div class="summary">
        <a-statistic title="分析股票数" :value="analysisResult.total_stocks_analyzed" />
        <a-statistic title="符合条件股票数" :value="analysisResult.stocks.length" />
        <a-statistic title="当前选择" :value="`${currentIndex + 1}/${analysisResult.stocks.length}`" />
      </div>
      
      <div class="stock-selector">
        <label>选择股票:</label>
        <a-select
          v-model:value="selectedStockCode"
          placeholder="选择股票"
          style="width: 300px"
          show-search
          :filter-option="filterOption"
          @change="handleStockChange"
        >
          <a-select-option
            v-for="stock in analysisResult.stocks"
            :key="stock.code"
            :value="stock.code"
            :label="`${stock.code} - ${stock.name}`"
          >
            <div class="stock-option">
              <div class="stock-info">
                <span class="code">{{ stock.code }}</span>
                <span class="name">{{ stock.name }}</span>
              </div>
              <div class="signal-info">
                <span class="buy">买点: {{ stock.buy_signals }}</span>
                <span class="sell">卖点: {{ stock.sell_signals }}</span>
                <span class="total">总计: {{ stock.total_signals }}</span>
              </div>
            </div>
          </a-select-option>
        </a-select>
        
        <div class="navigation">
          <a-button 
            :disabled="currentIndex <= 0" 
            @click="selectPrevious"
            :icon="h(LeftOutlined)"
          >
            上一个
          </a-button>
          <a-button 
            :disabled="currentIndex >= analysisResult.stocks.length - 1" 
            @click="selectNext"
            :icon="h(RightOutlined)"
          >
            下一个
          </a-button>
        </div>
      </div>
      
      <div v-if="selectedStock" class="selected-stock-info">
        <a-card size="small" title="选中股票信息">
          <a-descriptions :column="2" size="small">
            <a-descriptions-item label="股票代码">{{ selectedStock.code }}</a-descriptions-item>
            <a-descriptions-item label="股票名称">{{ selectedStock.name }}</a-descriptions-item>
            <a-descriptions-item label="买点数量">
              <a-tag color="green">{{ selectedStock.buy_signals }}</a-tag>
            </a-descriptions-item>
            <a-descriptions-item label="卖点数量">
              <a-tag color="red">{{ selectedStock.sell_signals }}</a-tag>
            </a-descriptions-item>
            <a-descriptions-item label="总信号数">
              <a-tag color="blue">{{ selectedStock.total_signals }}</a-tag>
            </a-descriptions-item>
            <a-descriptions-item label="数据行数">{{ selectedStock.data_rows }}</a-descriptions-item>
          </a-descriptions>
        </a-card>
      </div>
    </div>
  </div>
  </a-config-provider>
</template>

<script setup lang="ts">
// @ts-nocheck
import { ref, computed, h, onMounted, onUnmounted, watch } from 'vue'
import { 
  message, 
  Input as AInput, 
  Button as AButton, 
  InputNumber as AInputNumber,
  DatePicker as ADatePicker,
  Select as ASelect,
  SelectOption as ASelectOption,
  Statistic as AStatistic,
  Card as ACard,
  Descriptions as ADescriptions,
  DescriptionsItem as ADescriptionsItem,
  Tag as ATag
} from 'ant-design-vue'
// @ts-ignore
import zhCN from 'ant-design-vue/es/locale/zh_CN'
import dayjs from 'dayjs'
import 'dayjs/locale/zh-cn'
import { LeftOutlined, RightOutlined } from '@ant-design/icons-vue'
import type { StockSignalInfo, SignalAnalysisResponse } from '@/types'
import { getStockSignalsAnalysis } from '@/api/stocks'

interface Emits {
  (e: 'stockSelect', stock: StockSignalInfo): void
  (e: 'dateChange', payload: { start: string; end: string }): void
  (e: 'analysisLoaded', payload: { start: string; end: string; minSignals: number; signalType: string; stocks: StockSignalInfo[] }): void
}

const emit = defineEmits<Emits>()

dayjs.locale('zh-cn')

const startDate = ref('')
const endDate = ref('')
const minSignals = ref(3)
const loading = ref(false)
const defaultAnalysisResult: SignalAnalysisResponse = {
  start_date: '',
  end_date: '',
  min_signals: 10,
  total_stocks_analyzed: 0,
  matching_stocks: 0,
  stocks: []
}
const analysisResult = ref<SignalAnalysisResponse>(defaultAnalysisResult)
const selectedStockCode = ref('')
const currentIndex = ref(0)
const signalType = ref<'all' | 'buy' | 'sell'>('all')
const activeQuickRange = ref<number>(12)
const today = ref('2025-05-01')

// 计算当前选中的股票
const selectedStock = computed(() => {
  if (!selectedStockCode.value) return null
  return analysisResult.value.stocks.find(stock => stock.code === selectedStockCode.value) || null
})


//
const setSelectedStockByCode = (code: string) => {
  selectedStockCode.value = code
  selectStockByIndex(analysisResult.value.stocks.findIndex(stock => stock.code === code) || 0)
  
}

// 移除前端过滤，统一使用后端已过滤结果

// 初始化默认日期
const initDefaultDates = () => {
  const todayDate = new Date(today.value)
  const oneYearAgo = new Date(todayDate.getFullYear() - 1, todayDate.getMonth(), todayDate.getDate())
  
  endDate.value = today.value
  startDate.value = oneYearAgo.toISOString().split('T')[0]
  activeQuickRange.value = 12
}

// 设置日期范围
const setDateRange = (months: number) => {
  let start: Date
  const todayDate = new Date(today.value)
  
  if (months < 1) {
    // 处理天数（0.25个月 ≈ 7天）
    const days = Math.round(months * 30)
    start = new Date(todayDate.getTime() - days * 24 * 60 * 60 * 1000)
  } else {
    // 处理月份
    start = new Date(todayDate.getFullYear(), todayDate.getMonth() - months, todayDate.getDate())
  }
  
  endDate.value = today.value
  startDate.value = start.toISOString().split('T')[0]
  activeQuickRange.value = months
  
  if (months < 1) {
    const days = Math.round(months * 30)
    message.success(`已选择近${days}天的数据`)
  } else {
    message.success(`已选择近${months}个月的数据`)
  }
}

// 加载信号分析数据
const loadSignalData = async () => {
  if (!startDate.value || !endDate.value) {
    message.warning('请选择开始和结束日期')
    return
  }
  
  if (minSignals.value < 1) {
    message.warning('最小信号数必须大于0')
    return
  }
  
  loading.value = true
  
  try {
    const params = new URLSearchParams({
      start_date: startDate.value,
      end_date: endDate.value,
      min_signals: minSignals.value.toString(),
      signal_type: signalType.value
    })
    
    const result: SignalAnalysisResponse = await getStockSignalsAnalysis(Object.fromEntries(params.entries()))
    analysisResult.value = result
    // 向上提交加载完成事件
    emit('analysisLoaded', {
      start: startDate.value,
      end: endDate.value,
      minSignals: minSignals.value,
      signalType: signalType.value,
      stocks: result.stocks
    })
    
    if (result.stocks.length === 0) {
      message.warning('没有找到符合条件的股票')
    } else {
      message.success(`找到 ${result.matching_stocks} 只符合条件的股票`)
      // 默认选择第一只股票
      selectStockByIndex(0)
    }
  } catch (error) {
    console.error('加载信号数据失败:', error)
    message.error('加载信号数据失败')
  } finally {
    loading.value = false
  }
}

// 选择股票
const selectStockByIndex = (index: number) => {
  const list = analysisResult.value.stocks
  if (index < 0 || index >= list.length) return
  currentIndex.value = index
  const stock = list[index]
  selectedStockCode.value = stock.code
  emit('stockSelect', stock)
}

// 选择上一只股票
const selectPrevious = () => {
  if (currentIndex.value > 0) {
    selectStockByIndex(currentIndex.value - 1)
  }
}

// 选择下一只股票
const selectNext = () => {
  if (currentIndex.value < analysisResult.value.stocks.length - 1) {
    selectStockByIndex(currentIndex.value + 1)
  }
}

// 处理股票选择变化
const handleStockChange = (value: any) => {
  const code = String(value || '')
  const list = analysisResult.value.stocks
  const index = list.findIndex(stock => stock.code === code)
  if (index !== -1) {
    selectStockByIndex(index)
  }
}

// 下拉框过滤选项
const filterOption = (input: string, option: any) => {
  const label = option.label || ''
  return label.toLowerCase().includes(input.toLowerCase())
}

// 键盘导航
const handleKeydown = (event: KeyboardEvent) => {
  if (analysisResult.value.stocks.length === 0) return
  
  if (event.key === 'ArrowUp') {
    event.preventDefault()
    selectPrevious()
  } else if (event.key === 'ArrowDown') {
    event.preventDefault()
    selectNext()
  }
}

// 处理Today日期变化
const handleTodayChange = () => {
  // 重新初始化日期范围
  initDefaultDates()
  message.success('Today日期已更新，日期范围已重新计算')
}

// 监听日期变化并向父组件同步
watch([startDate, endDate], ([s, e]) => {
  emit('dateChange', { start: s || '', end: e || '' })
})

onMounted(() => {
  initDefaultDates()
  document.addEventListener('keydown', handleKeydown)
})

onUnmounted(() => {
  document.removeEventListener('keydown', handleKeydown)
})

// 使用按钮组后无需处理 radio change
// 对外暴露“上下一个”
defineExpose({
  next: selectNext,
  prev: selectPrevious,
  selectStockByIndex,
  setSelectedStockByCode,
})
</script>

<style scoped>
.signal-analysis {
  padding: 16px;
}

.toolbar {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin-bottom: 16px;
}
.toolbar-row {
  display: flex;
  gap: 12px;
  align-items: center;
  flex-wrap: wrap;
}

.toolbar label {
  white-space: nowrap;
  font-weight: 500;
}

.analysis-result {
  margin-top: 16px;
}

.summary {
  display: flex;
  gap: 24px;
  margin-bottom: 16px;
  padding: 16px;
  background: #fafafa;
  border-radius: 6px;
}

.stock-selector {
  display: flex;
  gap: 12px;
  align-items: center;
  margin-bottom: 16px;
  flex-wrap: wrap;
}

.stock-selector label {
  font-weight: 500;
  white-space: nowrap;
}

.navigation {
  display: flex;
  gap: 8px;
}

.stock-option {
  display: flex;
  justify-content: space-between;
  align-items: center;
  width: 100%;
}

.stock-info {
  display: flex;
  flex-direction: row;
  gap: 2px;
}

.code {
  font-weight: 500;
  color: #1890ff;
}

.name {
  font-size: 12px;
  color: #666;
}

.signal-info {
  display: flex;
  gap: 8px;
  font-size: 12px;
}

.buy {
  color: #52c41a;
}

.sell {
  color: #ff4d4f;
}

.total {
  color: #1890ff;
  font-weight: 500;
}

.selected-stock-info {
  margin-top: 16px;
}

::deep(.ant-select-item-option-content) {
  width: 100%;
}

::deep(.ant-statistic-title) {
  font-size: 14px;
  color: #666;
}

::deep(.ant-statistic-content) {
  font-size: 18px;
  font-weight: 500;
}
</style>
