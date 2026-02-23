<template>
  <div class="result-detail">
    <!-- 绩效指标 -->
    <a-row :gutter="16" style="margin-bottom: 24px">
      <a-col :span="6">
        <a-statistic title="总收益率" :value="(result.total_return * 100).toFixed(2)" suffix="%"
          :value-style="{ color: result.total_return >= 0 ? '#3f8600' : '#cf1322' }" />
      </a-col>
      <a-col :span="6">
        <a-statistic title="最大回撤" :value="(result.max_drawdown * 100).toFixed(2)" suffix="%"
          :value-style="{ color: '#cf1322' }" />
      </a-col>
      <a-col :span="6">
        <a-statistic title="胜率" :value="(result.win_rate * 100).toFixed(2)" suffix="%"
          :value-style="{ color: result.win_rate >= 0.5 ? '#3f8600' : '#cf1322' }" />
      </a-col>
      <a-col :span="6">
        <a-statistic title="交易次数" :value="result.total_trades" />
      </a-col>
    </a-row>

    <a-row :gutter="16" style="margin-bottom: 24px">
      <a-col :span="6">
        <a-statistic title="初始资金" :value="result.initial_capital.toFixed(2)" prefix="¥" />
      </a-col>
      <a-col :span="6">
        <a-statistic title="最终资金" :value="result.final_capital.toFixed(2)" prefix="¥"
          :value-style="{ color: result.final_capital >= result.initial_capital ? '#3f8600' : '#cf1322' }" />
      </a-col>
      <a-col :span="6">
        <a-statistic title="盈利交易" :value="result.win_trades" :value-style="{ color: '#3f8600' }" />
      </a-col>
      <a-col :span="6">
        <a-statistic title="亏损交易" :value="result.loss_trades" :value-style="{ color: '#cf1322' }" />
      </a-col>
    </a-row>

    <a-row :gutter="16" style="margin-bottom: 24px">
      <a-col :span="6">
        <a-statistic title="最大使用资金" :value="maxUsedCapital.toFixed(2)" prefix="¥" />
      </a-col>
      <a-col :span="6">
        <a-statistic title="平均每日使用资金" :value="avgDailyUsedCapital.toFixed(2)" prefix="¥" />
      </a-col>
    </a-row>

    <!-- 资金曲线图 -->
    <a-card title="资金曲线" style="margin-bottom: 24px">
      <div ref="chartRef" style="width: 100%; height: 400px"></div>
    </a-card>

    <!-- 交易规则配置 -->
    <a-card title="交易规则配置" style="margin-bottom: 24px" v-if="result.buy_rule || result.sell_rule">
      <template #extra>
        <a-tag color="blue">策略规则</a-tag>
      </template>
      
      <!-- 使用规则编辑器显示规则 -->
      <RuleEditor 
        :buy-rule="result.buy_rule || {}" 
        :sell-rule="result.sell_rule || {}"
      />
      
      <!-- 仓位配置 -->
      <div v-if="result.position_config" style="margin-top: 24px; padding-top: 16px; border-top: 1px solid #f0f0f0;">
        <h4 style="margin-bottom: 12px; color: #1890ff;">
          <a-icon type="pie-chart" style="margin-right: 4px;" />
          仓位配置
        </h4>
        <a-descriptions :column="3" size="small">
          <a-descriptions-item label="分配方法">
            <a-tag :color="getPositionMethodColor(result.position_config.method)">
              {{ getPositionMethodText(result.position_config.method) }}
            </a-tag>
          </a-descriptions-item>
          <a-descriptions-item label="固定比例" v-if="result.position_config.method === 'fixed_ratio'">
            {{ (result.position_config.ratio * 100).toFixed(1) }}%
          </a-descriptions-item>
          <a-descriptions-item label="固定金额" v-if="result.position_config.method === 'fixed_amount'">
            ¥{{ result.position_config.fixed_amount.toLocaleString() }}
          </a-descriptions-item>
          <a-descriptions-item label="固定股数" v-if="result.position_config.method === 'fixed_quantity'">
            {{ result.position_config.fixed_quantity }}股
          </a-descriptions-item>
          <a-descriptions-item label="单股最大仓位">
            {{ (result.position_config.max_position_per_stock * 100).toFixed(1) }}%
          </a-descriptions-item>
          <a-descriptions-item label="最大持仓股票数">
            {{ result.position_config.max_stocks }}只
          </a-descriptions-item>
        </a-descriptions>
      </div>
    </a-card>


    <!-- 股票维度统计 -->
    <a-card title="股票维度统计" style="margin-bottom: 24px">
      <template #extra>
        <a-space>
          <a-tag color="blue">总股票数: {{ stockStatsData.length }}</a-tag>
          <a-tag color="green">盈利股票: {{stockStatsData.filter(s => s.totalProfit > 0).length}}</a-tag>
          <a-tag color="red">亏损股票: {{stockStatsData.filter(s => s.totalProfit < 0).length}}</a-tag>
        </a-space>
      </template>
      <a-table :columns="stockStatsColumns" :data-source="processedStockStatsData" size="small"
        :row-key="record => record.code">
        <template #bodyCell="{ column, record }">
          <template v-if="column.key === 'totalProfit'">
            <span :style="{ color: record.totalProfit >= 0 ? '#cf1322' : '#3f8600', fontWeight: 'bold' }">
              {{ record.totalProfit.toFixed(2) }}
            </span>
          </template>
          <template v-else-if="column.key === 'profitRate'">
            <span :style="{ color: record.profitRate >= 0 ? '#cf1322' : '#3f8600', fontWeight: 'bold' }">
              {{ record.profitRate.toFixed(2) }}%
            </span>
          </template>
          <template v-else-if="column.key === 'winRate'">
            <a-tag :color="record.winRate >= 0.5 ? 'red' : 'green'">
              {{ (record.winRate * 100).toFixed(1) }}%
            </a-tag>
          </template>
          <template v-else-if="column.key === 'profitTrades'">
            <a-tag color="red">{{ record.profitTrades }}</a-tag>
          </template>
          <template v-else-if="column.key === 'lossTrades'">
            <a-tag color="green">{{ record.lossTrades }}</a-tag>
          </template>
          <template v-else-if="column.key === 'avgHoldingDays'">
            <span v-if="record.avgHoldingDays > 0">{{ record.avgHoldingDays }}天</span>
            <span v-else>-</span>
          </template>
          <template v-else-if="column.key === 'maxHoldingDays'">
            <span v-if="record.maxHoldingDays > 0">{{ record.maxHoldingDays }}天</span>
            <span v-else>-</span>
          </template>
        </template>
      </a-table>
    </a-card>

     <!-- 交易明细 -->
     <a-card title="交易明细">
      <a-table :columns="tradeColumns" :data-source="processedTradeData" size="small">
        <template #bodyCell="{ column, record }">
          <template v-if="column.key === 'direction'">
            <a-tag :color="record.direction === 'buy' ? 'green' : 'red'">
              {{ record.direction === 'buy' ? '买入' : '卖出' }}
            </a-tag>
          </template>
          <template v-else-if="column.key === 'profit_pct'">
            <span v-if="record.profit_pct !== undefined"
              :style="{ color: record.profit_pct >= 0 ? '#3f8600' : '#cf1322' }">
              {{ (record.profit_pct * 100).toFixed(2) }}%
            </span>
            <span v-else>-</span>
          </template>
        </template>
      </a-table>
    </a-card>

    <!-- 每日交易统计 -->
    <a-card title="每日交易统计" style="margin-bottom: 24px">
      <a-table :columns="dailyBuyColumns" :data-source="processedDailyBuyData" size="small">
        <template #bodyCell="{ column, record }">
          <template v-if="column.key === 'buy_count'">
            <a-tag :color="record.buy_count > 0 ? 'red' : 'default'">
              {{ record.buy_count }}
            </a-tag>
          </template>
          <template v-else-if="column.key === 'sell_count'">
            <a-tag :color="record.sell_count > 0 ? 'green' : 'default'">
              {{ record.sell_count }}
            </a-tag>
          </template>
          <template v-else-if="column.key === 'total_value'">
            {{ record.total_value.toFixed(2) }}
          </template>
          <template v-else-if="column.key === 'total_return'">
            <span :style="{ color: record.total_return >= 0 ? '#ff4d4f' : '#52c41a' }">
              {{ (record.total_return * 100).toFixed(2) }}%
            </span>
          </template>
        </template>
      </a-table>
    </a-card>

    <!-- 股票交易详情模态框 -->
    <a-modal
      v-model:open="modalVisible"
      :title="selectedStock ? `${selectedStock.code} ${selectedStock.name} - 交易详情` : '交易详情'"
      width="90%"
      :footer="null"
      :destroy-on-close="true"
      :body-style="{ padding: '16px' }"
    >
      <div class="modal-content">
        <!-- K线图区域 -->
        <div class="kline-section" v-if="selectedStock">
          <a-card title="K线图" size="small" style="margin-bottom: 16px;">
            <vue2-kline-chart 
              :code="selectedStock.code" 
              :show-days="180" 
              :today="selectedStockLastTradeDate"
              :buy-points="selectedStockBuyPoints"
              :sell-points="selectedStockSellPoints"
            />
          </a-card>
        </div>
        
        <!-- 交易详情表格 -->
        <div class="trade-detail-section">
          <a-table
            :columns="tradeColumns"
            :data-source="selectedStockTrades"
            :pagination="{ pageSize: 10, showSizeChanger: true, showQuickJumper: true }"
            :scroll="{ x: 1400 }"
            size="small"
            row-key="date"
          >
            <template #bodyCell="{ column, record }">
              <template v-if="column.key === 'direction'">
                <a-tag :color="record.direction === 'buy' ? 'green' : 'red'">
                  {{ record.direction === 'buy' ? '买入' : '卖出' }}
                </a-tag>
              </template>
              <template v-else-if="column.key === 'profit_pct'">
                <span v-if="record.profit_pct !== undefined"
                  :style="{ color: record.profit_pct >= 0 ? '#3f8600' : '#cf1322' }">
                  {{ (record.profit_pct * 100).toFixed(2) }}%
                </span>
                <span v-else>-</span>
              </template>
              <template v-else-if="column.key === 'sell_reason'">
                <span v-if="record.direction === 'sell' && record.sell_reason">
                  {{ record.sell_reason }}
                </span>
                <span v-else>-</span>
              </template>
            </template>
          </a-table>
        </div>
      </div>
    </a-modal>

   
  </div>
</template>

<script setup>
import { ref, onMounted, nextTick, computed, reactive, h } from 'vue';
import * as echarts from 'echarts';
import Vue2KlineChart from '../../kline-analysis/vue2-kline-chart.vue';
import RuleEditor from '../config/RuleEditor.vue';

const props = defineProps({
  result: {
    type: Object,
    required: true
  }
});

const chartRef = ref(null);

// 排序状态管理
const dailyBuySort = reactive({
  field: null,
  order: null
});

const stockStatsSort = reactive({
  field: null,
  order: null
});

const tradeSort = reactive({
  field: null,
  order: null
});

// 模态框状态管理
const modalVisible = ref(false);
const selectedStock = ref(null);

// 计算每日买入卖出数据
const dailyBuyData = computed(() => {
  return props.result.account_snapshots.map(snapshot => ({
    date: snapshot.date,
    buy_count: snapshot.daily_buy_count || 0,
    sell_count: snapshot.daily_sell_count || 0,
    total_value: snapshot.total_value,
    total_return: snapshot.total_return,
    cash: snapshot.cash,
    position_value: snapshot.position_value
  }));
});

// 计算最大使用资金（所有快照中最大的持仓价值）
const maxUsedCapital = computed(() => {
  if (!props.result.account_snapshots || props.result.account_snapshots.length === 0) {
    return 0;
  }
  return Math.max(...props.result.account_snapshots.map(snapshot => snapshot.position_value || 0));
});

// 计算平均每日使用资金（所有快照的持仓价值平均值）
const avgDailyUsedCapital = computed(() => {
  if (!props.result.account_snapshots || props.result.account_snapshots.length === 0) {
    return 0;
  }
  const totalUsedCapital = props.result.account_snapshots.reduce((sum, snapshot) => {
    return sum + (snapshot.position_value || 0);
  }, 0);
  return totalUsedCapital / props.result.account_snapshots.length;
});

// 每日交易统计的排序数据处理
const processedDailyBuyData = computed(() => {
  let data = [...dailyBuyData.value];

  // 排序处理
  if (dailyBuySort.field && dailyBuySort.order) {
    data.sort((a, b) => {
      const aVal = a[dailyBuySort.field];
      const bVal = b[dailyBuySort.field];

      if (typeof aVal === 'string' && typeof bVal === 'string') {
        return dailyBuySort.order === 'ascend'
          ? aVal.localeCompare(bVal)
          : bVal.localeCompare(aVal);
      }

      const result = aVal - bVal;
      return dailyBuySort.order === 'ascend' ? result : -result;
    });
  }

  return data;
});

// 计算股票维度统计数据
const stockStatsData = computed(() => {
  const stockMap = new Map();

  // 遍历所有交易记录，按股票分组统计
  props.result.trades.forEach(trade => {
    const code = trade.code;
    if (!stockMap.has(code)) {
      stockMap.set(code, {
        code: code,
        name: trade.name,
        buyCount: 0,
        sellCount: 0,
        totalTrades: 0,
        totalProfit: 0,
        totalCommission: 0,
        totalStampDuty: 0,
        totalCost: 0,
        totalInvestment: 0, // 总投入成本
        totalRevenue: 0, // 总收入
        totalBuyQuantity: 0, // 总买入股数
        profitTrades: 0,
        lossTrades: 0,
        holdingDays: [],
        buyDates: [],
        sellDates: []
      });
    }

    const stock = stockMap.get(code);
    stock.totalTrades++;

    if (trade.direction === 'buy') {
      stock.buyCount++;
      stock.buyDates.push(trade.date);
      stock.totalCommission += trade.commission || 0;
      stock.totalCost += trade.total_cost || 0;
      stock.totalInvestment += trade.amount || 0; // 买入金额计入投入成本
      stock.totalBuyQuantity += trade.quantity || 0; // 买入股数累加
    } else if (trade.direction === 'sell') {
      stock.sellCount++;
      stock.sellDates.push(trade.date);
      stock.totalCommission += trade.commission || 0;
      stock.totalStampDuty += trade.stamp_duty || 0;
      stock.totalCost += trade.total_cost || 0;
      stock.totalRevenue += trade.amount || 0; // 卖出金额计入收入

      if (trade.profit !== undefined) {
        stock.totalProfit += trade.profit;
        if (trade.profit > 0) {
          stock.profitTrades++;
        } else if (trade.profit < 0) {
          stock.lossTrades++;
        }
        // 如果 profit === 0，不算盈利也不算亏损
      }
    }
  });

  // 计算平均持仓天数 - 需要正确匹配买入和卖出交易
  stockMap.forEach(stock => {
    const holdingDays = [];

    // 获取该股票的所有交易记录，按日期排序
    const stockTrades = props.result.trades
      .filter(trade => trade.code === stock.code)
      .sort((a, b) => new Date(a.date) - new Date(b.date));

    // 匹配买入和卖出交易
    let buyTrade = null;
    for (const trade of stockTrades) {
      if (trade.direction === 'buy') {
        buyTrade = trade;
      } else if (trade.direction === 'sell' && buyTrade) {
        // 计算持仓天数
        const days = Math.floor((new Date(trade.date) - new Date(buyTrade.date)) / (1000 * 60 * 60 * 24));
        holdingDays.push(days);
        buyTrade = null; // 重置，等待下一次买入
      }
    }

    stock.holdingDays = holdingDays;
  });

  // 转换为数组并计算最终指标
  return Array.from(stockMap.values()).map(stock => {
    // 胜率 = 盈利交易次数 / (盈利交易次数 + 亏损交易次数)
    const totalProfitLossTrades = stock.profitTrades + stock.lossTrades;
    const winRate = totalProfitLossTrades > 0 ? stock.profitTrades / totalProfitLossTrades : 0;
    const avgHoldingDays = stock.holdingDays.length > 0
      ? stock.holdingDays.reduce((sum, days) => sum + days, 0) / stock.holdingDays.length
      : 0;
    const maxHoldingDays = stock.holdingDays.length > 0 ? Math.max(...stock.holdingDays) : 0;

    // 计算净值（总投入成本）
    const netValue = stock.totalInvestment;

    // 计算盈亏比例
    const profitRate = netValue > 0 ? (stock.totalProfit / netValue) * 100 : 0;

    return {
      ...stock,
      winRate: winRate,
      avgHoldingDays: Math.round(avgHoldingDays),
      maxHoldingDays: maxHoldingDays,
      netValue: netValue,
      profitRate: profitRate,
      totalBuyQuantity: stock.totalBuyQuantity
    };
  }).sort((a, b) => b.totalProfit - a.totalProfit); // 按盈亏金额降序排列
});

// 股票维度统计的排序数据处理
const processedStockStatsData = computed(() => {
  let data = [...stockStatsData.value];

  // 排序处理
  if (stockStatsSort.field && stockStatsSort.order) {
    data.sort((a, b) => {
      const aVal = a[stockStatsSort.field];
      const bVal = b[stockStatsSort.field];

      if (typeof aVal === 'string' && typeof bVal === 'string') {
        return stockStatsSort.order === 'ascend'
          ? aVal.localeCompare(bVal)
          : bVal.localeCompare(aVal);
      }

      const result = aVal - bVal;
      return stockStatsSort.order === 'ascend' ? result : -result;
    });
  }

  return data;
});

// 交易明细的排序数据处理
const processedTradeData = computed(() => {
  let data = [...props.result.trades];

  // 排序处理
  if (tradeSort.field && tradeSort.order) {
    data.sort((a, b) => {
      const aVal = a[tradeSort.field];
      const bVal = b[tradeSort.field];

      if (typeof aVal === 'string' && typeof bVal === 'string') {
        return tradeSort.order === 'ascend'
          ? aVal.localeCompare(bVal)
          : bVal.localeCompare(aVal);
      }

      const result = aVal - bVal;
      return tradeSort.order === 'ascend' ? result : -result;
    });
  }

  return data;
});

// 选中股票的交易详情数据
const selectedStockTrades = computed(() => {
  if (!selectedStock.value) return [];
  
  return props.result.trades
    .filter(trade => trade.code === selectedStock.value.code)
    .sort((a, b) => new Date(a.date) - new Date(b.date));
});

// 获取当前选中股票的最后一次交易日期
const selectedStockLastTradeDate = computed(() => {
  if (!selectedStock.value || selectedStockTrades.value.length === 0) {
    return new Date().toISOString().split('T')[0]; // 默认返回今天
  }
  
  // 获取最后一次交易日期
  const lastTrade = selectedStockTrades.value[selectedStockTrades.value.length - 1];
  return lastTrade.date;
});

// 计算选中股票的买入点数据
const selectedStockBuyPoints = computed(() => {
  if (!selectedStock.value || selectedStockTrades.value.length === 0) {
    return [];
  }
  
  return selectedStockTrades.value
    .filter(trade => trade.direction === 'buy')
    .map(trade => [trade.date, trade.price]);
});

// 计算选中股票的卖出点数据
const selectedStockSellPoints = computed(() => {
  if (!selectedStock.value || selectedStockTrades.value.length === 0) {
    return [];
  }
  
  return selectedStockTrades.value
    .filter(trade => trade.direction === 'sell')
    .map(trade => [trade.date, trade.price]);
});

const tradeColumns = [
  { title: '日期', dataIndex: 'date', key: 'date', width: 120, sorter: (a, b) => new Date(a.date) - new Date(b.date) },
  { title: '股票代码', dataIndex: 'code', key: 'code', width: 100, sorter: (a, b) => a.code.localeCompare(b.code) },
  { title: '股票名称', dataIndex: 'name', key: 'name', width: 120, sorter: (a, b) => a.name.localeCompare(b.name) },
  { title: '方向', dataIndex: 'direction', key: 'direction', width: 80, sorter: (a, b) => a.direction.localeCompare(b.direction) },
  { title: '价格', dataIndex: 'price', key: 'price', width: 100, sorter: (a, b) => a.price - b.price },
  { title: '数量', dataIndex: 'quantity', key: 'quantity', width: 100, sorter: (a, b) => a.quantity - b.quantity },
  { title: '金额', dataIndex: 'amount', key: 'amount', width: 120, sorter: (a, b) => a.amount - b.amount, customRender: ({ text }) => text.toFixed(2) },
  { title: '佣金', dataIndex: 'commission', key: 'commission', width: 100, sorter: (a, b) => a.commission - b.commission, customRender: ({ text }) => text.toFixed(2) },
  { title: '印花税', dataIndex: 'stamp_duty', key: 'stamp_duty', width: 100, sorter: (a, b) => a.stamp_duty - b.stamp_duty, customRender: ({ text }) => text.toFixed(2) },
  { title: '总成本', dataIndex: 'total_cost', key: 'total_cost', width: 100, sorter: (a, b) => a.total_cost - b.total_cost, customRender: ({ text }) => text.toFixed(2) },
  { title: '盈亏比例', dataIndex: 'profit_pct', key: 'profit_pct', width: 100, sorter: (a, b) => (a.profit_pct || 0) - (b.profit_pct || 0) },
  { title: '卖出原因', dataIndex: 'sell_reason', key: 'sell_reason', width: 200, sorter: (a, b) => (a.sell_reason || '').localeCompare(b.sell_reason || '') }
];

const dailyBuyColumns = [
  { title: '日期', dataIndex: 'date', key: 'date', width: 120, sorter: (a, b) => new Date(a.date) - new Date(b.date) },
  { title: '买入数量', dataIndex: 'buy_count', key: 'buy_count', width: 100, sorter: (a, b) => a.buy_count - b.buy_count },
  { title: '卖出数量', dataIndex: 'sell_count', key: 'sell_count', width: 100, sorter: (a, b) => a.sell_count - b.sell_count },
  { title: '账户总值', dataIndex: 'total_value', key: 'total_value', width: 120, sorter: (a, b) => a.total_value - b.total_value },
  { title: '总收益率', dataIndex: 'total_return', key: 'total_return', width: 120, sorter: (a, b) => a.total_return - b.total_return },
  { title: '现金', dataIndex: 'cash', key: 'cash', width: 120, sorter: (a, b) => a.cash - b.cash, customRender: ({ text }) => text.toFixed(2) },
  { title: '持仓价值', dataIndex: 'position_value', key: 'position_value', width: 120, sorter: (a, b) => a.position_value - b.position_value, customRender: ({ text }) => text.toFixed(2) }
];

const stockStatsColumns = [
  { title: '股票代码', dataIndex: 'code', key: 'code', width: 100, fixed: 'left', sorter: (a, b) => a.code.localeCompare(b.code) },
  { title: '股票名称', dataIndex: 'name', key: 'name', width: 120, fixed: 'left', sorter: (a, b) => a.name.localeCompare(b.name) },
  { title: '交易次数', dataIndex: 'totalTrades', key: 'totalTrades', width: 100, sorter: (a, b) => a.totalTrades - b.totalTrades },
  { title: '买入次数', dataIndex: 'buyCount', key: 'buyCount', width: 100, sorter: (a, b) => a.buyCount - b.buyCount },
  { title: '卖出次数', dataIndex: 'sellCount', key: 'sellCount', width: 100, sorter: (a, b) => a.sellCount - b.sellCount },
  { title: '买入股数', dataIndex: 'totalBuyQuantity', key: 'totalBuyQuantity', width: 120, sorter: (a, b) => a.totalBuyQuantity - b.totalBuyQuantity, customRender: ({ text }) => text.toLocaleString() },
  { title: '买入金额', dataIndex: 'totalInvestment', key: 'totalInvestment', width: 120, sorter: (a, b) => a.totalInvestment - b.totalInvestment, customRender: ({ text }) => '¥' + text.toLocaleString() },
  { title: '盈亏金额', dataIndex: 'totalProfit', key: 'totalProfit', width: 120, sorter: (a, b) => a.totalProfit - b.totalProfit },
  { title: '盈亏比例', dataIndex: 'profitRate', key: 'profitRate', width: 100, sorter: (a, b) => a.profitRate - b.profitRate },
  { title: '胜率', dataIndex: 'winRate', key: 'winRate', width: 100, sorter: (a, b) => a.winRate - b.winRate },
  { title: '盈利次数', dataIndex: 'profitTrades', key: 'profitTrades', width: 100, sorter: (a, b) => a.profitTrades - b.profitTrades },
  { title: '亏损次数', dataIndex: 'lossTrades', key: 'lossTrades', width: 100, sorter: (a, b) => a.lossTrades - b.lossTrades },
  { title: '平均持仓天数', dataIndex: 'avgHoldingDays', key: 'avgHoldingDays', width: 120, sorter: (a, b) => a.avgHoldingDays - b.avgHoldingDays },
  { title: '最大持仓天数', dataIndex: 'maxHoldingDays', key: 'maxHoldingDays', width: 120, sorter: (a, b) => a.maxHoldingDays - b.maxHoldingDays },
  { title: '总佣金', dataIndex: 'totalCommission', key: 'totalCommission', width: 100, sorter: (a, b) => a.totalCommission - b.totalCommission, customRender: ({ text }) => text.toFixed(2) },
  { title: '总印花税', dataIndex: 'totalStampDuty', key: 'totalStampDuty', width: 100, sorter: (a, b) => a.totalStampDuty - b.totalStampDuty, customRender: ({ text }) => text.toFixed(2) },
  { title: '总成本', dataIndex: 'totalCost', key: 'totalCost', width: 100, sorter: (a, b) => a.totalCost - b.totalCost, customRender: ({ text }) => text.toFixed(2) },
  { 
    title: '操作', 
    key: 'action', 
    width: 100, 
    fixed: 'right',
    customRender: ({ record }) => {
      return h('a', {
        type: 'link',
        size: 'small',
        onClick: () => showTradeDetail(record)
      }, '查看详情');
    }
  }
];

// 初始化图表
const initChart = () => {
  nextTick(() => {
    if (!chartRef.value) return;

    const chart = echarts.init(chartRef.value);

    const dates = props.result.account_snapshots.map(s => s.date);
    const values = props.result.account_snapshots.map(s => s.total_value);
    const returns = props.result.account_snapshots.map(s => s.total_return * 100);
    const dailyBuyCounts = props.result.account_snapshots.map(s => s.daily_buy_count || 0);
    const dailySellCounts = props.result.account_snapshots.map(s => s.daily_sell_count || 0);

    const option = {
      tooltip: {
        trigger: 'axis',
        axisPointer: {
          type: 'cross'
        }
      },
      legend: {
        data: ['账户总值', '收益率', '当日买入数量', '当日卖出数量']
      },
      xAxis: {
        type: 'category',
        data: dates,
        axisLabel: {
          rotate: 45
        }
      },
      yAxis: [
        {
          type: 'value',
          name: '账户总值',
          position: 'left'
        },
        {
          type: 'value',
          name: '收益率(%)',
          position: 'right'
        },
        {
          type: 'value',
          name: '买入数量',
          position: 'right',
          offset: 60
        }
      ],
      series: [
        {
          name: '账户总值',
          type: 'line',
          data: values,
          smooth: true,
          itemStyle: {
            color: '#1890ff'
          }
        },
        {
          name: '收益率',
          type: 'line',
          yAxisIndex: 1,
          data: returns,
          smooth: true,
          itemStyle: {
            color: '#ff4d4f'
          }
        },
        {
          name: '当日买入数量',
          type: 'bar',
          yAxisIndex: 2,
          data: dailyBuyCounts,
          itemStyle: {
            color: '#ff4d4f'
          }
        },
        {
          name: '当日卖出数量',
          type: 'bar',
          yAxisIndex: 2,
          data: dailySellCounts,
          itemStyle: {
            color: '#52c41a'
          }
        }
      ]
    };

    chart.setOption(option);

    // 响应式
    window.addEventListener('resize', () => {
      chart.resize();
    });
  });
};

// 显示交易详情
const showTradeDetail = (stock) => {
  selectedStock.value = stock;
  modalVisible.value = true;
};

// 关闭模态框
const closeModal = () => {
  modalVisible.value = false;
  selectedStock.value = null;
};


// 获取仓位分配方法文本
const getPositionMethodText = (method) => {
  const methodMap = {
    'fixed_ratio': '固定比例',
    'fixed_amount': '固定金额',
    'fixed_quantity': '固定股数'
  };
  return methodMap[method] || method;
};

// 获取仓位分配方法颜色
const getPositionMethodColor = (method) => {
  const colorMap = {
    'fixed_ratio': 'blue',
    'fixed_amount': 'green',
    'fixed_quantity': 'orange'
  };
  return colorMap[method] || 'default';
};

onMounted(() => {
  initChart();
});
</script>

<style scoped>
.result-detail {
  padding: 16px 0;
}

.modal-content {
  max-height: 80vh;
  overflow-y: auto;
}

.kline-section {
  margin-bottom: 16px;
}

.kline-section .ant-card {
  border: 1px solid #f0f0f0;
}

.trade-detail-section {
  margin-top: 16px;
}

</style>
