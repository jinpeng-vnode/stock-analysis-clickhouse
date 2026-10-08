<template>
    <div class="money-flow-page">
        <a-page-header title="资金流向分析" sub-title="股票资金流向数据统计与分析" class="page-header">
            <template #extra>
                <a-space>
                    <a-button type="primary" :loading="loading" @click="refreshData">
                        <template #icon>
                            <ReloadOutlined />
                        </template>
                        刷新数据
                    </a-button>
                </a-space>
            </template>
        </a-page-header>

        <div class="content">
            <!-- 统计概览 -->
            <a-row :gutter="[16, 16]" class="stats-cards">
                <a-col :span="6">
                    <a-card class="stat-card">
                        <a-statistic title="总记录数" :value="statsData.total_records" :loading="loading">
                            <template #prefix>
                                <DatabaseOutlined style="color: #1890ff" />
                            </template>
                        </a-statistic>
                    </a-card>
                </a-col>

                <a-col :span="6">
                    <a-card class="stat-card">
                        <a-statistic title="有数据股票数" :value="statsData.stocks_with_data" :loading="loading">
                            <template #prefix>
                                <StockOutlined style="color: #52c41a" />
                            </template>
                        </a-statistic>
                    </a-card>
                </a-col>

                <a-col :span="6">
                    <a-card class="stat-card">
                        <a-statistic title="数据起始日期" :value="statsData.date_range.min_date" :loading="loading">
                            <template #prefix>
                                <CalendarOutlined style="color: #faad14" />
                            </template>
                        </a-statistic>
                    </a-card>
                </a-col>

                <a-col :span="6">
                    <a-card class="stat-card">
                        <a-statistic title="最新更新" :value="statsData.latest_update" :loading="loading">
                            <template #prefix>
                                <ClockCircleOutlined style="color: #f5222d" />
                            </template>
                        </a-statistic>
                    </a-card>
                </a-col>
            </a-row>

            <!-- 主要内容区域 -->
            <a-row :gutter="[16, 16]" class="main-content">
                <!-- 左侧：股票搜索和详情 -->
                <a-col :span="12">
                    <FlowCard :code="selectedStockCode" />
                </a-col>

                <!-- 右侧：排行榜 -->
                <a-col :span="12">
                    <a-card title="资金流向排行榜" class="ranking-card">
                        <template #extra>
                            <a-space>
                                <a-date-picker v-model:value="rankingDate" placeholder="选择日期"
                                    @change="loadRankingData" />
                                <a-button type="primary" size="small" :loading="rankingLoading"
                                    @click="loadRankingData">
                                    刷新
                                </a-button>
                            </a-space>
                        </template>

                        <a-tabs v-model:activeKey="activeTab" @change="handleTabChange">
                            <a-tab-pane key="inflow" tab="净流入">
                                <a-table :columns="rankingColumns" :data-source="rankingData.top_inflow"
                                    :pagination="false" size="small">
                                    <template #bodyCell="{ column, record, index }">
                                        <template v-if="column.key === 'rank'">
                                            <a-tag :color="index < 3 ? 'red' : 'blue'">
                                                {{ index + 1 }}
                                            </a-tag>
                                        </template>
                                        <template v-else-if="column.key === 'code'">
                                            <a @click="selectedStockCode = record.code" style="cursor: pointer; color: #1890ff;">
                                                {{ record.code }}
                                            </a>
                                        </template>
                                        <template v-else-if="column.key === 'main_net_inflow_amount'">
                                            <span class="positive">
                                                {{ formatAmount(record.main_net_inflow_amount) }}
                                            </span>
                                        </template>
                                        <template v-else-if="column.key === 'change_pct'">
                                            <span :class="record.change_pct >= 0 ? 'positive' : 'negative'">
                                                {{ record.change_pct >= 0 ? '+' : '' }}{{ record.change_pct.toFixed(2)
                                                }}%
                                            </span>
                                        </template>
                                    </template>
                                </a-table>
                            </a-tab-pane>

                            <a-tab-pane key="outflow" tab="净流出">
                                <a-table :columns="rankingColumns" :data-source="rankingData.top_outflow"
                                    :pagination="false" size="small">
                                    <template #bodyCell="{ column, record, index }">
                                        <template v-if="column.key === 'rank'">
                                            <a-tag :color="index < 3 ? 'red' : 'blue'">
                                                {{ index + 1 }}
                                            </a-tag>
                                        </template>
                                        <template v-else-if="column.key === 'code'">
                                            <a @click="selectedStockCode = record.code" style="cursor: pointer; color: #1890ff;">
                                                {{ record.code }}
                                            </a>
                                        </template>
                                        <template v-else-if="column.key === 'main_net_inflow_amount'">
                                            <span class="negative">
                                                {{ formatAmount(record.main_net_inflow_amount) }}
                                            </span>
                                        </template>
                                        <template v-else-if="column.key === 'change_pct'">
                                            <span :class="record.change_pct >= 0 ? 'positive' : 'negative'">
                                                {{ record.change_pct >= 0 ? '+' : '' }}{{ record.change_pct.toFixed(2)
                                                }}%
                                            </span>
                                        </template>
                                    </template>
                                </a-table>
                            </a-tab-pane>
                        </a-tabs>
                    </a-card>
                </a-col>
            </a-row>
        </div>

    </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { message } from 'ant-design-vue'
import {
  ReloadOutlined,
  DatabaseOutlined,
  StockOutlined,
  CalendarOutlined,
  ClockCircleOutlined
} from '@ant-design/icons-vue'
import { getMoneyFlowStats, getTopMoneyFlow } from '@/api/stocks'
import type {
    MoneyFlowStatsResponse,
    MoneyFlowTopResponse
} from '@/types'
import FlowCard from './FlowCard.vue'

// 响应式数据
const loading = ref(false)
const rankingLoading = ref(false)
const rankingDate = ref()
const activeTab = ref('inflow')
const selectedStockCode = ref<string>('')

// 统计数据
const statsData = reactive<MoneyFlowStatsResponse>({
    total_records: 0,
    date_range: { min_date: null, max_date: null },
    stocks_with_data: 0,
    latest_update: null
})

// 排行榜数据
const rankingData = reactive<MoneyFlowTopResponse>({
  date: '',
  total_stocks: 0,
  top_inflow: [],
  top_outflow: []
})

const rankingColumns = [
    { title: '排名', key: 'rank', width: 60 },
    { title: '代码', dataIndex: 'code', key: 'code', width: 80 },
    { title: '名称', dataIndex: 'name', key: 'name', width: 100 },
    { title: '收盘价', dataIndex: 'close_price', key: 'close_price', width: 80 },
    { title: '涨跌幅', dataIndex: 'change_pct', key: 'change_pct', width: 80 },
    { title: '主力净流入', dataIndex: 'main_net_inflow_amount', key: 'main_net_inflow_amount', width: 120 }
]

// 方法
const loadStatsData = async () => {
    try {
        loading.value = true
        const response = await getMoneyFlowStats()
        console.log('统计数据响应:', response)

        // 确保数据正确赋值
        statsData.total_records = response.total_records || 0
        statsData.stocks_with_data = response.stocks_with_data || 0
        statsData.date_range = response.date_range || { min_date: null, max_date: null }
        statsData.latest_update = response.latest_update || null

        console.log('更新后的统计数据:', statsData)
    } catch (error) {
        console.error('加载统计数据失败:', error)
        message.error('加载统计数据失败')
    } finally {
        loading.value = false
    }
}

const loadRankingData = async () => {
    try {
        rankingLoading.value = true
        const params: any = { limit: 20 }
        if (rankingDate.value) {
            params.trade_date = rankingDate.value.format('YYYY-MM-DD')
        }

        const response = await getTopMoneyFlow(params)
        Object.assign(rankingData, response)
    } catch (error) {
        console.error('加载排行榜数据失败:', error)
        message.error('加载排行榜数据失败')
    } finally {
        rankingLoading.value = false
    }
}

const handleTabChange = (key: string) => {
    activeTab.value = key
}

const refreshData = () => {
    loadStatsData()
    loadRankingData()
}

const formatAmount = (amount: number) => {
    if (Math.abs(amount) >= 100000000) {
        return (amount / 100000000).toFixed(2) + '亿'
    } else if (Math.abs(amount) >= 10000) {
        return (amount / 10000).toFixed(2) + '万'
    }
    return amount.toFixed(2)
}

// 生命周期
onMounted(() => {
    loadStatsData()
    loadRankingData()
})
</script>

<style scoped>
.money-flow-page {
    padding: 24px;


}

.page-header {
    background: white;
    margin-bottom: 16px;
    border-radius: 8px;
}

.content {

    padding: 24px;
    border-radius: 8px;
}

.stats-cards {
    margin-bottom: 24px;
}

.stat-card {
    text-align: center;
}

.main-content {
    margin-top: 24px;
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

:deep(.ant-statistic-content) {
    font-size: 20px;
}
</style>
