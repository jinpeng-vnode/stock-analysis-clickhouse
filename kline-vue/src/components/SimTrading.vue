<template>
  <div class="sim-trading">
    <div class="summary-cards">
      <a-card size="small" title="资金">
        <div class="funds">
          <a-statistic title="初始资金" :value="initialCash" :precision="2" />
          <a-statistic title="可用资金" :value="availableCash" :precision="2" />
          <a-statistic title="持仓市值" :value="positionsValue" :precision="2" />
          <a-statistic title="总资产" :value="totalEquity" :precision="2" />
        </div>
        <div class="funds-actions">
          <a-input-number v-model:value="cashAdjust" :min="-100000000" :step="100" style="width: 160px" />
          <a-button size="small" @click="onAdjustCash">调整资金</a-button>
          <a-popconfirm title="确认清空所有本地数据？" ok-text="确定" cancel-text="取消" @confirm="resetAll">
            <a-button size="small" danger>清空本地数据</a-button>
          </a-popconfirm>
        </div>
        <div class="funds" style="margin-top: 8px">
          <a-statistic title="已实现盈亏" :value="realizedPnl" :precision="2" :value-style="{ color: realizedPnl >= 0 ? '#cf1322' : '#3f8600' }" />
          <a-statistic title="未实现盈亏" :value="unrealizedPnl" :precision="2" :value-style="{ color: unrealizedPnl >= 0 ? '#cf1322' : '#3f8600' }" />
          <a-statistic title="总盈亏" :value="totalPnl" :precision="2" :value-style="{ color: totalPnl >= 0 ? '#cf1322' : '#3f8600' }" />
          <a-statistic title="收益率%" :value="pnlPercent" :precision="2" :suffix="'%'" :value-style="{ color: pnlPercent >= 0 ? '#cf1322' : '#3f8600' }" />
        </div>
      </a-card>

      <a-card size="small" :title="`下单 (${displaySymbol})`">
        <div class="order-form">
          <div class="row">
            <span class="label">股票:</span>
            <span class="value">{{ displaySymbol }}</span>
          </div>
          <div class="row">
            <span class="label">时间:</span>
            <span class="value">{{ currentTime || '-' }}</span>
          </div>
          <div class="row">
            <span class="label">价格:</span>
            <a-input-number v-model:value="price" :min="0" :step="0.01" style="width: 160px" />
          </div>
          <div class="row">
            <span class="label">数量(股):</span>
            <a-input-number v-model:value="quantity" :min="1" :step="100" style="width: 160px" />
          </div>
          
          <div class="row">
            <a-button type="primary" @click="onQuickBuy">买入</a-button>
            <a-button danger @click="onQuickSell">卖出</a-button>
          </div>
        </div>
      </a-card>
    </div>

    <a-card size="small" title="当前持仓" style="margin-top: 12px">
      <a-table :data-source="positionRows" :columns="positionColumns" size="small" :pagination="false" row-key="symbol" />
    </a-card>

    <a-card size="small" title="成交/历史" style="margin-top: 12px">
      <template #extra>
        <a-button type="primary" @click="onExportHistory">导出</a-button>
      </template>
      <a-table :data-source="historyRows" :columns="historyColumns" size="small" :pagination="false" row-key="id" />
    </a-card>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, h } from 'vue'
import { message, Statistic as AStatistic, Card as ACard, Button as AButton, InputNumber as AInputNumber, Table as ATable, Tag as ATag, Popconfirm as APopconfirm } from 'ant-design-vue'

// 常量配置（移除 props）
const STORAGE_KEY = 'simtrading_v1'
const DEFAULT_INITIAL_CASH = 100000

// 基本状态和存储结构
type Position = {
  symbol: string
  name?: string
  quantity: number
  avgPrice: number
}

type Trade = {
  id: string
  time: string
  symbol: string
  name?: string
  side: 'buy' | 'sell'
  price: number
  quantity: number
  amount: number
  fee: number
  netCash: number
  realized?: number
}

type Store = {
  cash: number
  positions: Record<string, Position>
  history: Trade[]
  realizedPnl?: number
  settings?: {
    commissionBps: number
    minCommission: number
    taxPermilleSell: number
  }
}

const store = ref<Store>({ cash: DEFAULT_INITIAL_CASH, positions: {}, history: [], realizedPnl: 0, settings: { commissionBps: 3, minCommission: 5, taxPermilleSell: 1 } })

// 当前上下文（由对外 buy/sell 设置）
const currentSymbol = ref<string>('')
const currentName = ref<string>('')
const currentTime = ref<string>('')

// 价格与下单
const latestName = computed(() => currentName.value || '')
const displaySymbol = computed(() => (latestName.value ? `${currentSymbol.value} - ${latestName.value}` : (currentSymbol.value || '未选择'))) 

const price = ref<number>(0)
const quantity = ref<number>(100)

// 价格值直接使用输入框的 price

// 资金与资产
const initialCash = computed(() => loadStore().cash_initial ?? DEFAULT_INITIAL_CASH)
const availableCash = computed(() => store.value.cash)
const positionsValue = computed(() => {
  return Object.values(store.value.positions).reduce((acc, p) => {
    const mkt = price.value > 0 && p.symbol === currentSymbol.value ? Number(price.value) : p.avgPrice
    return acc + p.quantity * mkt
  }, 0)
})
const totalEquity = computed(() => availableCash.value + positionsValue.value)
const unrealizedPnl = computed(() => {
  return Object.values(store.value.positions).reduce((acc, p) => {
    const mkt = price.value > 0 && p.symbol === currentSymbol.value ? Number(price.value) : p.avgPrice
    return acc + (mkt - p.avgPrice) * p.quantity
  }, 0)
})
const realizedPnl = computed(() => store.value.realizedPnl || 0)
const totalPnl = computed(() => realizedPnl.value + unrealizedPnl.value)
const pnlPercent = computed(() => {
  const base = Number(initialCash.value || 0)
  if (!base) return 0
  return (totalPnl.value / base) * 100
})

// 表格数据
const positionColumns = [
  { title: '代码', dataIndex: 'symbol' },
  { title: '名称', dataIndex: 'name' },
  { title: '数量', dataIndex: 'quantity' },
  { title: '持仓均价', dataIndex: 'avgPrice', customRender: ({ text }: any) => Number(text).toFixed(2) },
  { title: '市值', dataIndex: 'marketValue', customRender: ({ text }: any) => Number(text).toFixed(2) }
]
const historyColumns = [
  { title: '时间', dataIndex: 'time' },
  { 
    title: '方向', 
    dataIndex: 'side',
    customRender: ({ text }: any) => {
      const isBuy = String(text) === 'buy'
      const color = isBuy ? 'red' : 'green'
      const label = isBuy ? '买入' : '卖出'
      return h(ATag, { color }, () => label)
    }
  },
  { title: '代码', dataIndex: 'symbol' },
  { title: '名称', dataIndex: 'name' },
  { title: '价格', dataIndex: 'price', customRender: ({ text }: any) => Number(text).toFixed(2) },
  { title: '数量', dataIndex: 'quantity' },
  { title: '成交额', dataIndex: 'amount', customRender: ({ text }: any) => Number(text).toFixed(2) },
  { title: '手续费/税', dataIndex: 'fee', customRender: ({ text }: any) => Number(text).toFixed(2) },
  { 
    title: '净入金', 
    dataIndex: 'netCash', 
    customRender: ({ text }: any) => {
      const value = Number(text)
      const color = value >= 0 ? '#cf1322' : '#3f8600'
      return h('span', { style: { color } }, Number.isFinite(value) ? value.toFixed(2) : '-')
    }
  },
  { 
    title: '本次盈亏', 
    dataIndex: 'realized', 
    customRender: ({ text }: any) => {
      if (text === undefined) return '-'
      const value = Number(text)
      const color = value >= 0 ? '#cf1322' : '#3f8600'
      return h('span', { style: { color } }, Number.isFinite(value) ? value.toFixed(2) : '-')
    }
  }
]

const positionRows = computed(() => {
  const list = Object.values(store.value.positions)
  return list.map(p => ({
    ...p,
    marketValue: (p.symbol === currentSymbol.value ? Number(price.value || 0) : p.avgPrice) * p.quantity
  }))
})

const historyRows = computed(() => store.value.history.slice().reverse())

// 本地存储
function loadStore(): Store & { cash_initial?: number } {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (!raw) return { cash: DEFAULT_INITIAL_CASH, positions: {}, history: [], cash_initial: DEFAULT_INITIAL_CASH }
    const parsed = JSON.parse(raw)
    return {
      cash: parsed.cash ?? DEFAULT_INITIAL_CASH,
      positions: parsed.positions ?? {},
      history: parsed.history ?? [],
      cash_initial: parsed.cash_initial ?? DEFAULT_INITIAL_CASH,
      realizedPnl: parsed.realizedPnl ?? 0,
      settings: parsed.settings ?? { commissionBps: 3, minCommission: 5, taxPermilleSell: 1 }
    }
  } catch {
    return { cash: DEFAULT_INITIAL_CASH, positions: {}, history: [], cash_initial: DEFAULT_INITIAL_CASH }
  }
}

function saveStore(extra?: Partial<Store> & { cash_initial?: number }) {
  const data = { cash: store.value.cash, positions: store.value.positions, history: store.value.history, cash_initial: initialCash.value, realizedPnl: store.value.realizedPnl || 0, settings: store.value.settings, ...(extra || {}) }
  localStorage.setItem(STORAGE_KEY, JSON.stringify(data))
}

// 初始化
;(function init() {
  const s = loadStore()
  store.value.cash = s.cash
  store.value.positions = s.positions
  store.value.history = s.history
  store.value.realizedPnl = s.realizedPnl || 0
  store.value.settings = s.settings || { commissionBps: 3, minCommission: 5, taxPermilleSell: 1 }
})()

// 资金调整
const cashAdjust = ref<number>(0)
function onAdjustCash() {
  const v = Number(cashAdjust.value || 0)
  if (v === 0) {
    message.info('调整金额为0')
    return
  }
  store.value.cash += v
  cashAdjust.value = 0
  saveStore()
  message.success('资金已调整')
}

// 费用计算
// 雪球规则：佣金万3（最低5）+ 过户费0.01‰ 双向 + 卖出印花税千分之一
function feeOnBuy(amount: number): number {
  const commission = Math.max(amount * 0.0003, 5)
  const transfer = amount * 0.00001
  const total = commission + transfer
  return Number.isFinite(total) ? total : 0
}
function feeOnSell(amount: number): number {
  const commission = Math.max(amount * 0.0003, 5)
  const transfer = amount * 0.00001
  const stamp = amount * 0.001
  const total = commission + transfer + stamp
  return Number.isFinite(total) ? total : 0
}

// 统一的下单执行逻辑，便于对外方法复用
function executeOrder(sideArg: 'buy' | 'sell', pIn: number, qIn: number, timeIn?: string) {
  const p = Number(pIn)
  const q = Number(qIn)
  if (!currentSymbol.value) {
    message.warning('未选择股票')
    return
  }
  if (p <= 0 || q <= 0) {
    message.warning('价格与数量需大于0')
    return
  }
  const amount = p * q
  const symbol = currentSymbol.value
  const name = latestName.value

  if (sideArg === 'buy') {
    const fee = feeOnBuy(amount)
    const totalCost = amount + fee
    if (totalCost > store.value.cash) {
      message.error('可用资金不足')
      return
    }
    store.value.cash -= totalCost
    const old = store.value.positions[symbol]
    if (!old) {
      const avgWithFee = totalCost / q
      store.value.positions[symbol] = { symbol, name, quantity: q, avgPrice: avgWithFee }
    } else {
      const newQty = old.quantity + q
      const newAvg = (old.avgPrice * old.quantity + (amount + fee)) / newQty
      store.value.positions[symbol] = { symbol, name: old.name || name, quantity: newQty, avgPrice: newAvg }
    }
    const trade: Trade = {
      id: `${Date.now()}_${Math.random().toString(16).slice(2)}`,
      time: String(timeIn || new Date().toISOString().slice(0, 19).replace('T', ' ')),
      symbol,
      name,
      side: sideArg,
      price: p,
      quantity: q,
      amount,
      fee,
      netCash: -(amount + fee)
    }
    store.value.history.push(trade)
  } else {
    const old = store.value.positions[symbol]
    const holdQty = old?.quantity || 0
    if (q > holdQty) {
      message.error('卖出数量超过持仓')
      return
    }
    const fee = feeOnSell(amount)
    const netIn = amount - fee
    store.value.cash += netIn
    const remain = holdQty - q
    if (remain <= 0) {
      delete store.value.positions[symbol]
    } else {
      store.value.positions[symbol] = { symbol, name: old?.name || name, quantity: remain, avgPrice: old!.avgPrice }
    }
    const avg = old!.avgPrice
    const realized = netIn - avg * q
    store.value.realizedPnl = (store.value.realizedPnl || 0) + realized
    const trade: Trade = {
      id: `${Date.now()}_${Math.random().toString(16).slice(2)}`,
      time: String(timeIn || new Date().toISOString().slice(0, 19).replace('T', ' ')),
      symbol,
      name,
      side: sideArg,
      price: p,
      quantity: q,
      amount,
      fee,
      netCash: netIn,
      realized
    }
    store.value.history.push(trade)
  }
  saveStore()
  message.success('下单成功（本地模拟）')
}

// 下单逻辑（保留按钮触发入口）
function onQuickBuy() {
  if (!currentSymbol.value) {
    message.warning('未选择股票（请通过 ref.setValue/买入/卖出 设置代码）')
    return
  }
  executeOrder('buy', Number(price.value), Number(quantity.value), currentTime.value || undefined)
}
function onQuickSell() {
  if (!currentSymbol.value) {
    message.warning('未选择股票（请通过 ref.setValue/买入/卖出 设置代码）')
    return
  }
  executeOrder('sell', Number(price.value), Number(quantity.value), currentTime.value || undefined)
}

// 对外暴露的方法：buy/sell，可传入价格与数量；不传则用当前输入或最新价
function buy(symbol: string, priceIn: number, qtyIn: number, name?: string, time?: string) {
  currentSymbol.value = String(symbol || '')
  currentName.value = String(name || currentName.value || '')
  price.value = Number(priceIn)
  quantity.value = Number(qtyIn)
  executeOrder('buy', Number(priceIn), Number(qtyIn), time)
}
function sell(symbol: string, priceIn: number, qtyIn: number, name?: string, time?: string) {
  currentSymbol.value = String(symbol || '')
  currentName.value = String(name || currentName.value || '')
  price.value = Number(priceIn)
  quantity.value = Number(qtyIn)
  executeOrder('sell', Number(priceIn), Number(qtyIn), time)
}

// 允许外部设置当前上下文（符号、名称、最新价、时间）以启用面板UI
function setValue(symbol: string, name?: string, latestPriceOpt?: number, time?: string) {
  currentSymbol.value = String(symbol || '')
  currentName.value = String(name || currentName.value || '')
  currentTime.value = String(time || '')
  if (latestPriceOpt !== undefined && latestPriceOpt !== null && Number.isFinite(Number(latestPriceOpt))) {
    price.value = Number(latestPriceOpt)
  }
}

defineExpose({ buy, sell, setValue })

function resetAll() {
  // 移除本地存储，确保彻底清空
  try {
    localStorage.removeItem(STORAGE_KEY)
  } catch {}

  // 重置内存状态到初始值
  store.value.cash = DEFAULT_INITIAL_CASH
  store.value.positions = {}
  store.value.history = []
  store.value.realizedPnl = 0
  store.value.settings = { commissionBps: 3, minCommission: 5, taxPermilleSell: 1 }

  // 重置界面输入状态
  cashAdjust.value = 0
  quantity.value = 100
  // 不再使用最新价，保留价格输入框现值

  // 立即写入一个干净的基线记录，便于刷新的稳定显示
  saveStore({ cash: DEFAULT_INITIAL_CASH, positions: {}, history: [], realizedPnl: 0, cash_initial: DEFAULT_INITIAL_CASH, settings: store.value.settings })
  message.success('已清空本地模拟数据')
}

// 导出历史交易记录为CSV
function onExportHistory() {
  if (!store.value.history || store.value.history.length === 0) {
    message.warning('暂无历史交易记录')
    return
  }

  try {
    // CSV表头
    const headers = ['时间', '方向', '代码', '名称', '价格', '数量', '成交额', '手续费/税', '净入金', '本次盈亏']

    // 转换数据为CSV格式
    const csvRows = [headers.join(',')]

    // 按时间倒序排列（最新的在前）
    const sortedHistory = [...store.value.history].reverse()

    for (const trade of sortedHistory) {
      const row = [
        `"${trade.time}"`, // 时间
        `"${trade.side === 'buy' ? '买入' : '卖出'}"`, // 方向
        `"${trade.symbol}"`, // 代码
        `"${trade.name || ''}"`, // 名称
        Number(trade.price).toFixed(2), // 价格
        trade.quantity.toString(), // 数量
        Number(trade.amount).toFixed(2), // 成交额
        Number(trade.fee).toFixed(2), // 手续费/税
        Number(trade.netCash).toFixed(2), // 净入金
        trade.realized !== undefined ? Number(trade.realized).toFixed(2) : '-' // 本次盈亏
      ]
      csvRows.push(row.join(','))
    }

    // 生成CSV内容，添加BOM头确保Excel正确显示中文
    const csvContent = '\uFEFF' + csvRows.join('\n')

    // 生成文件名
    const now = new Date()
    const timestamp = now.getFullYear().toString() +
                     (now.getMonth() + 1).toString().padStart(2, '0') +
                     now.getDate().toString().padStart(2, '0') + '_' +
                     now.getHours().toString().padStart(2, '0') +
                     now.getMinutes().toString().padStart(2, '0') +
                     now.getSeconds().toString().padStart(2, '0')
    const filename = `模拟交易历史_${timestamp}.csv`

    // 创建Blob并触发下载
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' })
    const link = document.createElement('a')
    const url = URL.createObjectURL(blob)
    link.setAttribute('href', url)
    link.setAttribute('download', filename)
    link.style.visibility = 'hidden'
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    URL.revokeObjectURL(url)

    message.success(`已导出 ${store.value.history.length} 条交易记录`)
  } catch (error) {
    console.error('导出失败:', error)
    message.error('导出失败，请重试')
  }
}
</script>

<style scoped>
.sim-trading {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.summary-cards {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.funds {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 12px;
}

.funds-actions {
  display: flex;
  gap: 8px;
  margin-top: 8px;
}

.order-form {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.row {
  display: flex;
  align-items: center;
  gap: 8px;
}

.label {
  width: 80px;
  text-align: right;
  color: #555;
}

.value {
  font-weight: 500;
}
</style>


