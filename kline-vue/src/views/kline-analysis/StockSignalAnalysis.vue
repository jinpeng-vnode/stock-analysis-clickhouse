<template>
  <a-card title="股票信号分析">
    <a-form :model="form" layout="horizontal" :label-col="{ style: { width: '100px' } }">
      <!-- 其他参数设置 -->
      <a-form-item name="today" label="Today日期">
        <a-date-picker v-model:value="form.today" placeholder="选择Today日期" style="width: 140px" format="YYYY-MM-DD"
          value-format="YYYY-MM-DD" @change="handleTodayChange" />
      </a-form-item>
      <a-form-item name="minSignals" label="最小信号数">
        <a-input-number v-model:value="form.minSignals" :min="0" :max="1000" style="width: 100px" />
      </a-form-item>
      <a-form-item name="showDays" label="展示天数">
        <a-input-number v-model:value="form.showDays" :min="5" :max="300" style="width: 100px" />
      </a-form-item>

      <!-- 信号类型选择 -->
      <a-form-item name="signalType" label="信号类型">
        <a-radio-group v-model:value="form.signalType">
          <a-radio-button value="all">全部</a-radio-button>
          <a-radio-button value="buy">买点</a-radio-button>
          <a-radio-button value="sell">卖点</a-radio-button>
        </a-radio-group>
      </a-form-item>

      <!-- 最后一天信号选择 -->
      <a-form-item name="lastDaySignal" label="最后一天信号">
        <a-radio-group v-model:value="form.lastDaySignal">
          <a-radio-button value="any">不限</a-radio-button>
          <a-radio-button value="buy">买点</a-radio-button>
          <a-radio-button value="sell">卖点</a-radio-button>
        </a-radio-group>
      </a-form-item>

      <!-- 威廉指数过滤 -->
      <a-form-item name="wrCondition" label="威廉指数过滤">
        <a-radio-group v-model:value="form.wrCondition" @change="handleWrConditionChange">
          <a-radio-button value="none">不限</a-radio-button>
          <a-radio-button value="lt">小于</a-radio-button>
          <a-radio-button value="gt">大于</a-radio-button>
          <a-radio-button value="lte">小于等于</a-radio-button>
          <a-radio-button value="gte">大于等于</a-radio-button>
        </a-radio-group>
      </a-form-item>

      <a-form-item v-if="form.wrCondition !== 'none'" name="wrValue" label="威廉指数阈值">
        <a-input-number v-model:value="form.wrValue" :min="0" :max="100" :step="0.1" style="width: 120px"
          placeholder="输入阈值" />
        <span style="margin-left: 8px; color: #666;">同时检查WR6和WR10</span>
      </a-form-item>



      <!-- 价格范围过滤 -->
      <a-form-item name="priceRange" label="价格范围">
        <a-space>
          <a-input-number v-model:value="form.priceMin" :min="0" :max="1000" :step="0.01" style="width: 120px"
            placeholder="最低价" :precision="2" />
          <span style="color: #666;">至</span>
          <a-input-number v-model:value="form.priceMax" :min="0" :max="1000" :step="0.01" style="width: 120px"
            placeholder="最高价" :precision="2" />
          <a-button size="small" @click="clearPriceRange">清除</a-button>
        </a-space>
        <div style="margin-top: 4px; color: #666; font-size: 12px;">
          可选设置，用于过滤股票价格范围
        </div>
      </a-form-item>

      <!-- 斜率过滤 -->
      <a-form-item name="slopeDirection" label="斜率方向">
        <a-radio-group v-model:value="form.slopeDirection" @change="handleSlopeDirectionChange">
          <a-radio-button value="any">不限</a-radio-button>
          <a-radio-button value="up">上升</a-radio-button>
          <a-radio-button value="down">下降</a-radio-button>
        </a-radio-group>
      </a-form-item>

      <a-form-item v-if="form.slopeDirection !== 'any'" name="slopeSettings" label="斜率设置">
        <a-space>
          <span>计算周期:</span>
          <a-input-number v-model:value="form.slopePeriod" :min="2" style="width: 80px" placeholder="天数" />
          <span>天</span>
          <span style="margin-left: 16px;">阈值:</span>
          <a-input-number v-model:value="form.slopeThreshold" :min="0" :max="10" :step="0.01" style="width: 100px"
            placeholder="可选" :precision="3" />
        </a-space>
        <div style="margin-top: 4px; color: #666; font-size: 12px;">
          基于最近N天收盘价计算线性回归斜率
        </div>
      </a-form-item>

      <!-- 分析按钮 -->
      <a-form-item>
        <a-button type="primary" @click="onSearch" :loading="loading" style="width: 100%">
          分析信号
        </a-button>
      </a-form-item>

      <!-- 统计区域 -->
      <a-form-item label="">
        <div class="summary">
          <a-statistic title="分析股票数" :value="analysisResult.total_stocks_analyzed" />
          <a-statistic title="符合条件股票数" :value="analysisResult.stocks.length" />
          <a-statistic title="当前选择" :value="`${currentIndex + 1}/${analysisResult.stocks.length}`" />
        
        </div>
        <div class="summary">
          <StockSelector
            v-model:value="form.code"
            :stocks="analysisResult.stocks"
            placeholder="选择股票"
            width="300px"
            :show-signals="true"
            @change="handleStockChange"
          />
        </div>
        <!-- 选中股票信息区域 -->

        <div v-if="selectedStock" class="selected-stock-info">
          <a-card size="small" title="选中股票信息">
            <template #extra>
              <a-button type="primary" @click="addToCandidateList" :disabled="!selectedStock">
                加入候选列表
              </a-button>
            </template>
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
      </a-form-item>


    </a-form>
  </a-card>
</template>

<script>
import dayjs from "dayjs";
import 'dayjs/locale/zh-cn';
import { useCandidateListStore } from '@/stores/candidateList';
import { getStockSignalsAnalysis } from '@/api/stocks';
import StockSelector from '@/components/StockSelector.vue';

dayjs.locale('zh-cn');

export default {
  name: 'StockSignalAnalysis',
  components: {
    StockSelector
  },
  emits: ['stockSelect', 'analysisComplete'],
  setup() {
    const candidateListStore = useCandidateListStore()
    return { candidateListStore }
  },
  data() {
    return {
      // 本地存储键名
      STORAGE_KEY: 'STOCK_SIGNAL_FORM_DATA',
      form: {
        code: '000001',
        showDays: 180,
        today: '2025-10-09',
        minSignals: 3,
        signalType: 'buy',
        lastDaySignal: 'buy',
        wrCondition: 'none',
        wrValue: 0.0,
        // 后置过滤条件
        priceMin: null,
        priceMax: null,
        slopeDirection: 'any',
        slopePeriod: 10,
        slopeThreshold: null
      },
      loading: false,
      currentIndex: 0,
      analysisResult: {
        start_date: '',
        end_date: '',
        min_signals: 10,
        total_stocks_analyzed: 0,
        matching_stocks: 0,
        stocks: []
      }
    }
  },
  computed: {
    selectedStock() {
      if (!this.form.code || !this.analysisResult.stocks.length) return null
      return this.analysisResult.stocks.find(stock => stock.code === this.form.code) || null
    },
    // 判断是否是第一个股票
    isFirstStock() {
      return this.currentIndex === 0
    },
    // 判断是否是最后一个股票
    isLastStock() {
      return this.currentIndex === this.analysisResult.stocks.length - 1
    }
  },
  watch: {
    // 监听表单数据变化，自动保存到本地存储
    form: {
      handler(newVal) {
        this.saveFormData()
      },
      deep: true
    },
    // 监听股票代码变化，更新当前索引
    'form.code'(newCode) {
      this.updateCurrentIndex()
    }
  },
  methods: {
    // 加载本地存储的表单数据
    loadFormData() {
      try {
        const savedData = localStorage.getItem(this.STORAGE_KEY)
        if (savedData) {
          const parsedData = JSON.parse(savedData)
          // 合并保存的数据到form中，保持默认值作为后备
          this.form = { ...this.form, ...parsedData }
          console.log('已加载本地存储的表单数据:', parsedData)
        }
      } catch (error) {
        console.warn('加载本地存储数据失败:', error)
        // 如果解析失败，清除损坏的数据
        localStorage.removeItem(this.STORAGE_KEY)
      }
    },
    // 保存表单数据到本地存储
    saveFormData() {
      try {
        const formData = { ...this.form }
        localStorage.setItem(this.STORAGE_KEY, JSON.stringify(formData))
        console.log('已保存表单数据到本地存储:', formData)
      } catch (error) {
        console.warn('保存表单数据失败:', error)
      }
    },
    handleTodayChange(value, dateString) {
      // AntD v-model:value 已绑定，这里同步字符串更安全
      this.form.today = Array.isArray(dateString) ? dateString[0] : dateString
    },
    handleWrConditionChange(value) {
      // 当威廉指数比较条件改变时，重置阈值
      if (value === 'none') {
        this.form.wrValue = 0.0
      }
    },
    handleSlopeDirectionChange(value) {
      // 当斜率方向改变时，重置阈值
      if (value === 'any') {
        this.form.slopeThreshold = null
      }
    },
    clearPriceRange() {
      // 清除价格范围设置
      this.form.priceMin = null
      this.form.priceMax = null
    },
    clearAllPostFilters() {
      // 清除所有后置过滤条件
      this.form.priceMin = null
      this.form.priceMax = null
      this.form.slopeDirection = 'any'
      this.form.slopePeriod = 10
      this.form.slopeThreshold = null
    },
    addToCandidateList() {
      if (!this.selectedStock) return

      this.candidateListStore.addStock({
        code: this.selectedStock.code,
        name: this.selectedStock.name
      })

      this.$message.success(`已将 ${this.selectedStock.name}(${this.selectedStock.code}) 加入候选列表`)
    },
    async onSearch() {
      this.loading = true
      try {
        const params = new URLSearchParams({
          start_date: dayjs(this.form.today).subtract(14, 'day').format('YYYY-MM-DD'),
          end_date: this.form.today,
          min_signals: this.form.minSignals.toString(),
          signal_type: this.form.signalType,
          last_day_signal: this.form.lastDaySignal,
          wr_condition: this.form.wrCondition,
          wr_value: this.form.wrValue.toString(),
          // 后置过滤参数
          price_min: this.form.priceMin ? this.form.priceMin.toString() : '',
          price_max: this.form.priceMax ? this.form.priceMax.toString() : '',
          slope_direction: this.form.slopeDirection,
          slope_period: this.form.slopePeriod.toString(),
          slope_threshold: this.form.slopeThreshold ? this.form.slopeThreshold.toString() : ''
        })
        const data = await getStockSignalsAnalysis(Object.fromEntries(params.entries()))

        // 直接使用API响应数据
        this.analysisResult = data

        // 如果有股票数据，自动选择第一个股票
        if (data.stocks && data.stocks.length > 0) {
          this.form.code = data.stocks[0].code
          this.updateCurrentIndex()

          console.log('自动选择第一个股票:', this.form.code)
          console.log('selectedStock:', this.selectedStock)

          // 确保 selectedStock 不为 null 再发送事件
          if (this.selectedStock) {
            this.$emit('stockSelect', this.selectedStock)
          }
        }

        // 发送分析完成事件
        this.$emit('analysisComplete', {
          analysisResult: data,
          selectedStock: this.selectedStock
        })
      } finally {
        this.loading = false
      }
    },
    handleStockChange(selectedStock) {
      // 股票选择变化时的处理
      this.updateCurrentIndex()
      // 发送股票选择事件
      this.$emit('stockSelect', selectedStock)
    },
    updateCurrentIndex() {
      const list = this.analysisResult?.stocks || []
      const idx = list.findIndex(s => s.code === this.form.code)
      this.currentIndex = idx >= 0 ? idx : 0
      console.log('更新当前索引:', { code: this.form.code, index: this.currentIndex, total: list.length })
    },
    // 外部调用方法：设置选中的股票
    setSelectedStock(code) {
      this.form.code = code
      this.updateCurrentIndex()
      this.$emit('stockSelect', this.selectedStock)
    },
    // 外部调用方法：获取当前表单数据
    getFormData() {
      return { ...this.form }
    },
    // 外部调用方法：获取分析结果
    getAnalysisResult() {
      return { ...this.analysisResult }
    }
  },
  mounted() {
    // 先设置默认的today值
    this.form.today = dayjs().format('YYYY-MM-DD')
    // 然后加载本地存储的数据（会覆盖默认值）
    this.loadFormData()
  },
}
</script>

<style scoped>
.summary {
  display: flex;
  gap: 24px;
  padding: 16px;
  background: #fafafa;
  border-radius: 6px;
}

.selected-stock-info {
  margin-top: 16px;
}
</style>
