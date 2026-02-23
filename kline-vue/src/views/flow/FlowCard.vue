<template>
    <a-card title="股票资金流向详情" class="detail-card">

        <div v-if="selectedStock" class="stock-detail">
            <div v-if="showSections.info" class="stock-info">
                <h3>{{ selectedStock.name }} ({{ selectedStock.code }})</h3>
                <p>总记录数: {{ selectedStock.total_records }}</p>
            </div>

            <!-- 资金流向图表区域 -->
            <div v-if="showSections.charts" class="charts-section">
                <div class="charts-container">
                    <div class="chart-item">
                        <a-card title="资金成交分布" size="small">
                            <template #extra>
                                <a-tooltip title="显示各单类型的买入卖出分布">
                                    <InfoCircleOutlined />
                                </a-tooltip>
                            </template>
                            <div ref="moneyFlowPieChart" style="height: 300px;"></div>
                        </a-card>
                    </div>
                    <div class="chart-item">
                        <a-card title="主力动向" size="small">
                            <template #extra>
                                <a-tooltip title="显示各单类型的净流入情况">
                                    <InfoCircleOutlined />
                                </a-tooltip>
                            </template>
                            <div ref="mainForceBarChart" style="height: 300px;"></div>
                        </a-card>
                    </div>
                </div>
            </div>

            <!-- 多日净流入统计 -->
            <div v-if="showSections.stats" class="net-inflow-stats">
                <a-card title="多日净流入统计" size="small">
                    <div class="stats-container">
                        <div class="stat-item">
                            <div class="statistic-wrapper">
                                <div class="statistic-title">20日净流入</div>
                                <div class="statistic-value" :style="{ color: multiDayStats.net20d >= 0 ? '#ff4d4f' : '#52c41a' }">
                                    {{ formatAmount(multiDayStats.net20d) }}
                                </div>
                            </div>
                        </div>
                        <div class="stat-item">
                            <div class="statistic-wrapper">
                                <div class="statistic-title">10日净流入</div>
                                <div class="statistic-value" :style="{ color: multiDayStats.net10d >= 0 ? '#ff4d4f' : '#52c41a' }">
                                    {{ formatAmount(multiDayStats.net10d) }}
                                </div>
                            </div>
                        </div>
                        <div class="stat-item">
                            <div class="statistic-wrapper">
                                <div class="statistic-title">5日净流入</div>
                                <div class="statistic-value" :style="{ color: multiDayStats.net5d >= 0 ? '#ff4d4f' : '#52c41a' }">
                                    {{ formatAmount(multiDayStats.net5d) }}
                                </div>
                            </div>
                        </div>
                        <div class="stat-item">
                            <div class="statistic-wrapper">
                                <div class="statistic-title">3日净流入</div>
                                <div class="statistic-value" :style="{ color: multiDayStats.net3d >= 0 ? '#ff4d4f' : '#52c41a' }">
                                    {{ formatAmount(multiDayStats.net3d) }}
                                </div>
                            </div>
                        </div>
                    </div>
                </a-card>
            </div>

            <a-table v-if="showSections.table" :columns="detailColumns" :data-source="selectedStock.data"
                :pagination="{ pageSize: 10 }" size="small">
                <template #bodyCell="{ column, record }">
                    <template v-if="column.key === 'trade_date'">
                        {{ record.trade_date }}
                    </template>
                    <template v-else-if="column.key === 'close_price'">
                        ¥{{ record.close_price.toFixed(2) }}
                    </template>
                    <template v-else-if="column.key === 'change_pct'">
                        <span :class="record.change_pct >= 0 ? 'positive' : 'negative'">
                            {{ record.change_pct >= 0 ? '+' : '' }}{{ record.change_pct.toFixed(2) }}%
                        </span>
                    </template>
                    <template v-else-if="column.key === 'main_net_inflow_amount'">
                        <span :class="record.main_net_inflow_amount >= 0 ? 'positive' : 'negative'">
                            {{ formatAmount(record.main_net_inflow_amount) }}
                        </span>
                    </template>
                    <template v-else-if="column.key === 'main_net_inflow_ratio'">
                        <span :class="record.main_net_inflow_ratio >= 0 ? 'positive' : 'negative'">
                            {{ record.main_net_inflow_ratio >= 0 ? '+' : '' }}{{
                            record.main_net_inflow_ratio.toFixed(2) }}%
                        </span>
                    </template>
                </template>
            </a-table>
        </div>

        <div v-else class="no-selection">
            <a-empty :description="props.code ? '正在加载股票数据...' : '请选择一只股票查看资金流向详情'" :loading="loading" />
        </div>
    </a-card>
</template>

<script setup lang="ts">
import { ref, reactive, onBeforeUnmount, nextTick, watch, computed, withDefaults } from 'vue'
import { message } from 'ant-design-vue'
import { InfoCircleOutlined } from '@ant-design/icons-vue'
import { getStockMoneyFlow } from '@/api/stocks'
import type { MoneyFlowResponse } from '@/types'
import * as echarts from 'echarts'

// Props
const props = withDefaults(defineProps<{
    code?: string
    displayMode?: 'all' | 'charts'
}>(), {
    displayMode: 'all'
})

// 根据 displayMode 计算显示哪些区域
const showSections = computed(() => {
    if (props.displayMode === 'charts') {
        return {
            info: false,
            charts: true,
            stats: false,
            table: false
        }
    }
    // 默认显示全部
    return {
        info: true,
        charts: true,
        stats: true,
        table: true
    }
})

// 响应式数据
const loading = ref(false)

// 图表相关
const moneyFlowPieChart = ref<HTMLElement>()
const mainForceBarChart = ref<HTMLElement>()
let pieChartInstance: echarts.ECharts | null = null
let barChartInstance: echarts.ECharts | null = null

// 选中的股票数据
const selectedStock = ref<MoneyFlowResponse | null>(null)

// 多日净流入统计数据
const multiDayStats = reactive({
  net20d: 0,
  net10d: 0,
  net5d: 0,
  net3d: 0
})

// 表格列定义
const detailColumns = [
    { title: '日期', dataIndex: 'trade_date', key: 'trade_date', width: 100 },
    { title: '收盘价', dataIndex: 'close_price', key: 'close_price', width: 80 },
    { title: '涨跌幅', dataIndex: 'change_pct', key: 'change_pct', width: 80 },
    { title: '主力净流入', dataIndex: 'main_net_inflow_amount', key: 'main_net_inflow_amount', width: 120 },
    { title: '净占比', dataIndex: 'main_net_inflow_ratio', key: 'main_net_inflow_ratio', width: 80 }
]

// 加载股票数据
const loadStockData = async (code: string) => {
  if (!code) {
    selectedStock.value = null
    return
  }

  try {
    loading.value = true
    const response = await getStockMoneyFlow(code, { limit: 30 })
    selectedStock.value = response
    
    // 加载股票数据后初始化资金流向图表
    await initMoneyFlowCharts()
  } catch (error) {
    console.error('加载股票数据失败:', error)
    message.error('加载股票数据失败')
    selectedStock.value = null
  } finally {
    loading.value = false
  }
}

// 监听 code prop 变化，自动加载数据
watch(() => props.code, (newCode) => {
  if (newCode) {
    loadStockData(newCode)
  } else {
    selectedStock.value = null
  }
}, { immediate: true })

// 格式化金额
const formatAmount = (amount: number) => {
    if (amount === null || amount === undefined || isNaN(amount)) {
        return '0.00'
    }
    const absAmount = Math.abs(amount)
    if (absAmount >= 100000000) {
        return (amount / 100000000).toFixed(2) + '亿'
    } else if (absAmount >= 10000) {
        return (amount / 10000).toFixed(2) + '万'
    }
    return amount.toFixed(2)
}

// 计算资金流向图表数据
const calculateMoneyFlowData = (stockData: MoneyFlowResponse) => {
  if (!stockData.data || stockData.data.length === 0) {
    return { pieData: [], barData: [] }
  }
  
  // 获取最新日期的数据
  const latestData = stockData.data[0]
  
  // 计算各单类型的买入卖出金额（基于净流入金额）
  const superLargeBuy = Math.max(0, latestData.super_large_net_inflow_amount)
  const superLargeSell = Math.max(0, -latestData.super_large_net_inflow_amount)
  const largeBuy = Math.max(0, latestData.large_net_inflow_amount)
  const largeSell = Math.max(0, -latestData.large_net_inflow_amount)
  const mediumBuy = Math.max(0, latestData.medium_net_inflow_amount)
  const mediumSell = Math.max(0, -latestData.medium_net_inflow_amount)
  const smallBuy = Math.max(0, latestData.small_net_inflow_amount)
  const smallSell = Math.max(0, -latestData.small_net_inflow_amount)
  
  // 饼图数据：资金成交分布
  const pieData = [
    { value: superLargeBuy, name: '特大单买入', itemStyle: { color: '#ff4d4f' } },
    { value: superLargeSell, name: '特大单卖出', itemStyle: { color: '#52c41a' } },
    { value: largeBuy, name: '大单买入', itemStyle: { color: '#ff7875' } },
    { value: largeSell, name: '大单卖出', itemStyle: { color: '#73d13d' } },
    { value: mediumBuy, name: '中单买入', itemStyle: { color: '#ffa39e' } },
    { value: mediumSell, name: '中单卖出', itemStyle: { color: '#95de64' } },
    { value: smallBuy, name: '小单买入', itemStyle: { color: '#ffccc7' } },
    { value: smallSell, name: '小单卖出', itemStyle: { color: '#b7eb8f' } }
  ].filter(item => item.value > 0) // 只显示有数据的项
  
  // 柱状图数据：主力动向（净流入）
  const barData = [
    { name: '特大单', value: latestData.super_large_net_inflow_amount },
    { name: '大单', value: latestData.large_net_inflow_amount },
    { name: '中单', value: latestData.medium_net_inflow_amount },
    { name: '小单', value: latestData.small_net_inflow_amount }
  ]
  
  return { pieData, barData }
}

// 计算多日净流入统计
const calculateMultiDayStats = (stockData: MoneyFlowResponse) => {
  if (!stockData.data || stockData.data.length === 0) {
    multiDayStats.net20d = 0
    multiDayStats.net10d = 0
    multiDayStats.net5d = 0
    multiDayStats.net3d = 0
    return
  }
  
  // 计算各日期的净流入总和
  const data = stockData.data
  
  // 20日净流入（最多取20天数据）
  const net20d = data.slice(0, Math.min(20, data.length))
    .reduce((sum, item) => sum + item.main_net_inflow_amount, 0)
  
  // 10日净流入（最多取10天数据）
  const net10d = data.slice(0, Math.min(10, data.length))
    .reduce((sum, item) => sum + item.main_net_inflow_amount, 0)
  
  // 5日净流入（最多取5天数据）
  const net5d = data.slice(0, Math.min(5, data.length))
    .reduce((sum, item) => sum + item.main_net_inflow_amount, 0)
  
  // 3日净流入（最多取3天数据）
  const net3d = data.slice(0, Math.min(3, data.length))
    .reduce((sum, item) => sum + item.main_net_inflow_amount, 0)
  
  // 保持原始金额（元），使用 formatAmount 函数自动格式化单位
  multiDayStats.net20d = net20d
  multiDayStats.net10d = net10d
  multiDayStats.net5d = net5d
  multiDayStats.net3d = net3d
}

// 初始化资金流向图表
const initMoneyFlowCharts = async () => {
  if (!selectedStock.value) return
  
  await nextTick()
  
  // 计算多日净流入统计
  calculateMultiDayStats(selectedStock.value)
  
  const { pieData, barData } = calculateMoneyFlowData(selectedStock.value)
  
  // 初始化饼图
  if (moneyFlowPieChart.value) {
    if (pieChartInstance) {
      pieChartInstance.dispose()
    }
    pieChartInstance = echarts.init(moneyFlowPieChart.value)
    
    const pieOption = {
      title: {
        text: '资金成交分布',
        left: 'center',
        textStyle: {
          fontSize: 14
        }
      },
      tooltip: {
        trigger: 'item',
        formatter: (params: any) => {
          const value = (params.value / 10000).toFixed(2)
          return `${params.name}<br/>金额: ${value}万元<br/>占比: ${params.percent}%`
        }
      },
      legend: {
        orient: 'vertical',
        left: 'left',
        top: 'middle',
        textStyle: {
          fontSize: 10
        }
      },
      series: [
        {
          name: '资金成交',
          type: 'pie',
          radius: ['40%', '70%'],
          center: ['60%', '50%'],
          data: pieData,
          emphasis: {
            itemStyle: {
              shadowBlur: 10,
              shadowOffsetX: 0,
              shadowColor: 'rgba(0, 0, 0, 0.5)'
            }
          },
          label: {
            show: false
          },
          labelLine: {
            show: false
          }
        }
      ]
    }
    
    pieChartInstance.setOption(pieOption)
  }
  
  // 初始化柱状图
  if (mainForceBarChart.value) {
    if (barChartInstance) {
      barChartInstance.dispose()
    }
    barChartInstance = echarts.init(mainForceBarChart.value)
    
    const barOption = {
      title: {
        text: '主力动向',
        left: 'center',
        textStyle: {
          fontSize: 14
        }
      },
      tooltip: {
        trigger: 'axis',
        axisPointer: {
          type: 'shadow'
        },
        formatter: (params: any) => {
          const data = params[0]
          const value = (data.value / 10000).toFixed(2)
          const color = data.value >= 0 ? '流入' : '流出'
          return `${data.name}<br/>净${color}: ${Math.abs(parseFloat(value))}万元`
        }
      },
      grid: {
        left: '10%',
        right: '10%',
        bottom: '15%',
        top: '20%',
        containLabel: true
      },
      xAxis: {
        type: 'category',
        data: barData.map(item => item.name),
        axisTick: {
          alignWithLabel: true
        },
        axisLabel: {
          fontSize: 10
        }
      },
      yAxis: {
        type: 'value',
        axisLabel: {
          formatter: (value: number) => (value / 10000).toFixed(0) + '万',
          fontSize: 10
        }
      },
      series: [
        {
          name: '净流入',
          type: 'bar',
          barWidth: '60%',
          data: barData.map(item => ({
            value: item.value,
            itemStyle: {
              color: item.value >= 0 ? '#ff4d4f' : '#52c41a'
            }
          })),
          label: {
            show: true,
            position: 'top',
            formatter: (params: any) => {
              const value = (params.value / 10000).toFixed(1)
              return value + '万'
            },
            fontSize: 10
          }
        }
      ]
    }
    
    barChartInstance.setOption(barOption)
  }
}

// 销毁图表实例
const destroyCharts = () => {
    if (pieChartInstance) {
        pieChartInstance.dispose()
        pieChartInstance = null
    }
    if (barChartInstance) {
        barChartInstance.dispose()
        barChartInstance = null
    }
}

// 生命周期
onBeforeUnmount(() => {
    destroyCharts()
})
</script>

<style scoped>
.stock-detail {
    height: 100%;
}

.stock-info {
    margin-bottom: 16px;
    padding-bottom: 16px;
    border-bottom: 1px solid #f0f0f0;
}

.stock-info h3 {
    margin: 0 0 8px 0;
    color: #1890ff;
}

.no-selection {
    display: flex;
    align-items: center;
    justify-content: center;
    height: 400px;
}

.positive {
    color: #f5222d;
    font-weight: 500;
}

.negative {
    color: #52c41a;
    font-weight: 500;
}

:deep(.ant-table-tbody > tr > td) {
    padding: 8px;
}

.charts-section {
    margin: 16px 0;
}

.charts-container {
    display: flex;
    flex-wrap: wrap;
    gap: 16px;
}

.chart-item {
    flex: 1;
    min-width: 300px;
}

.charts-section .ant-card {
  margin-bottom: 0;
}

.net-inflow-stats {
  margin: 16px 0;
}

.stats-container {
  display: flex;
  flex-wrap: wrap;
  gap: 16px;
}

.stat-item {
  flex: 1;
  min-width: 120px;
}

.statistic-wrapper {
  text-align: center;
}

.statistic-title {
  font-size: 11px;
  color: #666;
  margin-bottom: 4px;
}

.statistic-value {
  font-size: 14px;
  font-weight: 600;
}
</style>

