<template>
  <div class="stock-selector">
    <a-select 
      :value="value" 
      :placeholder="placeholder" 
      :style="{ width: width }" 
      show-search
      :filter-option="filterOption" 
      @change="handleStockChange"
      :disabled="disabled"
    >
      <a-select-option 
        v-for="stock in stocks" 
        :key="stock.code" 
        :value="stock.code"
        :label="`${stock.code} - ${stock.name}`"
      >
        <div class="stock-option">
          <div class="stock-info">
            <span class="code">{{ stock.code }}</span>
            <span class="name">{{ stock.name }}</span>
          </div>
          <div v-if="showSignals" class="signal-info">
            <span class="buy">买点: {{ stock.buy_signals || 0 }}</span>
            <span class="sell">卖点: {{ stock.sell_signals || 0 }}</span>
            <span class="total">总计: {{ stock.total_signals || 0 }}</span>
          </div>
        </div>
      </a-select-option>
    </a-select>
    <a-space style="margin-left: 8px">
      <a-button @click="prevStock" :disabled="isFirstStock || disabled">上一个</a-button>
      <a-button @click="nextStock" :disabled="isLastStock || disabled">下一个</a-button>
    </a-space>
  </div>
</template>

<script>
export default {
  name: 'StockSelector',
  props: {
    // 股票列表数据
    stocks: {
      type: Array,
      default: () => []
    },
    // 当前选中的股票代码
    value: {
      type: String,
      default: ''
    },
    // 选择器占位符
    placeholder: {
      type: String,
      default: '选择股票'
    },
    // 是否显示信号信息
    showSignals: {
      type: Boolean,
      default: true
    },
    // 选择器宽度
    width: {
      type: String,
      default: '300px'
    },
    // 是否禁用
    disabled: {
      type: Boolean,
      default: false
    }
  },
  emits: ['update:value', 'change'],
  computed: {
    // 当前选中的股票对象
    selectedStock() {
      if (!this.value || !this.stocks.length) return null
      return this.stocks.find(stock => stock.code === this.value) || null
    },
    // 当前股票在列表中的索引
    currentIndex() {
      if (!this.value || !this.stocks.length) return 0
      const idx = this.stocks.findIndex(stock => stock.code === this.value)
      return idx >= 0 ? idx : 0
    },
    // 判断是否是第一个股票
    isFirstStock() {
      return this.currentIndex === 0
    },
    // 判断是否是最后一个股票
    isLastStock() {
      return this.currentIndex === this.stocks.length - 1
    }
  },
  methods: {
    // 过滤选项
    filterOption(input, option) {
      const label = (option?.label ?? '').toString().toLowerCase()
      return label.includes(input.toLowerCase())
    },
    // 处理股票选择变化
    handleStockChange(value) {
      this.$emit('update:value', value)
      this.$emit('change', this.selectedStock)
    },
    // 切换到上一个股票
    prevStock() {
      if (!this.stocks.length) return
      
      // 直接计算当前索引
      const currentIdx = this.stocks.findIndex(stock => stock.code === this.value)
      if (currentIdx <= 0) return // 已经是第一个或未找到
      
      const prevIdx = currentIdx - 1
      const prevStock = this.stocks[prevIdx]
      
      this.$emit('update:value', prevStock.code)
      this.$emit('change', prevStock)
    },
    // 切换到下一个股票
    nextStock() {
      if (!this.stocks.length) return
      
      // 直接计算当前索引
      const currentIdx = this.stocks.findIndex(stock => stock.code === this.value)
      if (currentIdx < 0 || currentIdx >= this.stocks.length - 1) return // 未找到或已经是最后一个
      
      const nextIdx = currentIdx + 1
      const nextStock = this.stocks[nextIdx]
      
      this.$emit('update:value', nextStock.code)
      this.$emit('change', nextStock)
    },
    // 外部调用方法：设置选中的股票
    setSelectedStock(code) {
      this.$emit('update:value', code)
      this.$emit('change', this.selectedStock)
    }
  }
}
</script>

<style scoped>
.stock-selector {
  display: flex;
  gap: 12px;
  align-items: center;
  flex-wrap: wrap;
}

.stock-option {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.stock-option .stock-info .code {
  font-weight: 600;
  margin-right: 8px;
  color: #1890ff;
}

.stock-option .stock-info .name {
  color: #666;
}

.stock-option .signal-info span {
  margin-left: 8px;
}

.stock-option .signal-info .buy {
  color: #52c41a;
}

.stock-option .signal-info .sell {
  color: #f5222d;
}

.stock-option .signal-info .total {
  color: #1890ff;
}
</style>
