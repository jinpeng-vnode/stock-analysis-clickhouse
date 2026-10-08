<template>
    <div class="kline-container">
      <div v-if="loading" class="loading">
        正在加载K线数据...
      </div>
      <div ref="chartRef" class="kline-chart" v-show="!loading"></div>
            <!-- 遮罩层：遮住 K 线图下方的区域，阻止滚轮事件 -->
      <div class="wheel-mask" v-show="!loading"></div>
    </div>
  </template>
  
  <script>
  import * as echarts from 'echarts'
  import { computeWilliamsR, computeThresholdPointsWithNear } from '@/utils/williamsR'
  import { calculateMACDSeries } from '@/utils/macd'
  import { computeLinearTrendOnRange } from '@/utils/trend'
  import { getStockDailyData } from '@/api/stocks'
  
  export default {
    name: 'vue2-kline-chart',
    props: {
      code: {
        type: String,
        required: true
      },
      showDays: {
        type: Number,
        default: 30
      },
      // 用于控制首次显示范围的"今天"日期（YYYY-MM-DD）
      today: {
        type: String,
        default: ''
      },
      // 买入点数据，格式为 [日期, 价格] 的数组
      buyPoints: {
        type: Array,
        default: () => []
      },
      // 卖出点数据，格式为 [日期, 价格] 的数组
      sellPoints: {
        type: Array,
        default: () => []
      }
    },
    data() {
      return {
        klineData: {},
        loading: false,
        // 缓存转换后的数据
        chartData: {
          category: [],
          values: [],
          volumes: [],
          highs: [],
          lows: [],
          closes: [],
          // 威廉指数数据
          wr6: [],
          wr10: [],
          thresholdPoints: {
            buyPoints: [],
            sellPoints: []
          },
          // MACD 指标
          macdDIF: [],
          macdDEA: [],
          macdBAR: []
        }
      }
    },
    methods: {
      async getKlineData() {
        this.loading = true
        try {
          const json = await getStockDailyData(this.code)
          this.klineData = json
          // 转换并缓存数据
          this.chartData = this.convertToEChartsFormat(json)
          this.convertAndRenderChart()
        } catch (error) {
          console.error('获取数据失败:', error)
        } finally {
          this.loading = false
        }
      },
      
      // 转换API数据为ECharts格式
      convertToEChartsFormat(apiData) {
        if (!apiData || !apiData.data || !Array.isArray(apiData.data)) {
          return { category: [], values: [], volumes: [], highs: [], lows: [], closes: [] }
        }
        
        const category = []
        const values = []
        const volumes = []
        const highs = []
        const lows = []
        const closes = []
        
        apiData.data.forEach(item => {
          category.push(item.日期)
          values.push([item.开盘, item.收盘, item.最低, item.最高])
          volumes.push(item.成交量 || 0)
          highs.push(item.最高 || 0)
          lows.push(item.最低 || 0)
          closes.push(item.收盘 || 0)
        })
        
        return { category, values, volumes, highs, lows, closes }
      },
      // 计算 MACD（DIF/DEA/BAR）
      calculateMACD() {
        const { closes } = this.chartData
        if (!Array.isArray(closes) || closes.length === 0) {
          this.chartData.macdDIF = []
          this.chartData.macdDEA = []
          this.chartData.macdBAR = []
          return
        }
        const { dif, dea, bar } = calculateMACDSeries(closes)
        this.chartData.macdDIF = dif
        this.chartData.macdDEA = dea
        this.chartData.macdBAR = bar
      },
      
      // 计算缩放范围（支持 today 控制首次显示的尾部位置）
      calculateZoomRange(category) {
        const total = Array.isArray(category) ? category.length : 0
        console.log('计算缩放范围:', { showDays: this.showDays, totalDataLength: total, today: this.today })
        if (!total || total <= 0) {
          return { startValue: 0, endValue: 0 }
        }
        // 全量显示
        if (this.showDays === 0 || this.showDays >= total) {
          return { startValue: 0, endValue: total - 1 }
        }
        // 计算 endIndex：优先使用 today 对齐到 <= today 的最后一个索引
        let endIndex = total - 1
        if (this.today) {
          const t = new Date(this.today)
          if (!isNaN(t.getTime())) {
            for (let i = total - 1; i >= 0; i--) {
              const d = new Date(category[i])
              if (!isNaN(d.getTime()) && d <= t) { endIndex = i; break }
            }
          }
        }
        const startIndex = Math.max(0, endIndex - this.showDays + 1)
        console.log('计算缩放范围结果:', { startValue: startIndex, endValue: endIndex, showDays: this.showDays })
        return { startValue: startIndex, endValue: endIndex }
      },
      
      // 只更新缩放范围，不重新转换数据
      updateZoom() {
        if (!this._chart || !this.chartData.category.length) return
        
        const zoomRange = this.calculateZoomRange(this.chartData.category)
        console.log('更新缩放范围:', zoomRange, '显示条数:', zoomRange.endValue - zoomRange.startValue + 1)
        
        // 只更新dataZoom配置
        this._chart.dispatchAction({
          type: 'dataZoom',
          startValue: zoomRange.startValue,
          endValue: zoomRange.endValue
        })
  
        // 与 KLineChart.vue 一致：不实时监听，但在缩放参数变更后补一次趋势线计算
        this.$nextTick(() => {
          const { category, closes } = this.chartData
          const visible = this.getCurrentVisibleIndexRange(category)
          const trendData = computeLinearTrendOnRange(closes, visible)
          this._chart.setOption({ series: [{ id: 'trend-line', data: trendData }] })
        })
      },
      
      // 初始化图表
      initChart() {
        if (!this.$refs.chartRef) return
        
        // 将ECharts实例存储在非响应式属性上，避免Vue 3响应式代理
        this._chart = echarts.init(this.$refs.chartRef)
        
        // 监听窗口大小变化
        window.addEventListener('resize', () => {
          if (this._chart) {
            this._chart.resize()
          }
        })
      },
      
      // 渲染图表
      renderChart() {
        if (!this._chart) return
        
        // 使用缓存的数据
        const { category, values, volumes, closes } = this.chartData
        
        // 调试信息
        console.log('买卖点数据:', {
          buyPoints: this.buyPoints,
          sellPoints: this.sellPoints,
          buyPointsLength: this.buyPoints ? this.buyPoints.length : 0,
          sellPointsLength: this.sellPoints ? this.sellPoints.length : 0
        })
        
        // 计算缩放范围
        const zoomRange = this.calculateZoomRange(category)
        console.log('应用缩放范围:', zoomRange, '数据长度:', category.length, '显示条数:', zoomRange.endValue - zoomRange.startValue + 1)
  
        // 基于即将应用的缩放区间计算拟合趋势线（首次渲染更稳妥）
        const trendRange = { startIndex: zoomRange.startValue, endIndex: zoomRange.endValue }
        const trendLineData = computeLinearTrendOnRange(closes, trendRange)
        
        const option = {
          title: {
            text: `${this.klineData.name || 'K线图'} (${this.code})`,
            left: 16,
            top: 8
          },
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
            { left: 80, right: 20, top: 70, height: 500 },
            { left: 80, right: 20, top: 600, height: 200 },
            { 
              left: 'auto', 
              right: 20, 
              top: 0, 
              height: 100, 
              width: 500,
              z: 10,
      
            },
            { left: 80, right: 20, top: 820, height: 150 },
            { left: 80, right: 20, top: 980, height: 160 },
  
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
              axisLine: { show: false },
              axisTick: { show: false },
              axisLabel: { show: false }
            },
            {
              type: 'category',
              data: category,
              gridIndex: 3,
              boundaryGap: true,
              axisTick: { show: false }
            },
            {
              type: 'category',
              data: category,
              gridIndex: 4,
              boundaryGap: true,
              axisTick: { show: false }
            }
          ],
          yAxis: [
            { scale: true },
            { gridIndex: 1 },
            { 
              gridIndex: 2, 
              scale: true,
              axisLine: { show: false },
              axisTick: { show: false },
              axisLabel: { show: false }
            },
            { 
              gridIndex: 3, 
              min: 0, 
              max: 100,
              axisLine: { show: false },
              axisTick: { show: false }
            },
            {
              gridIndex: 4,
              scale: true,
              axisLine: { show: false },
              axisTick: { show: false },
              // 让 0 位于中间，依据当前数据两侧最大绝对值对称取值
              min: function(value) {
                const maxAbs = Math.max(Math.abs(value.min || 0), Math.abs(value.max || 0))
                return maxAbs === 0 ? -0.001 : -maxAbs
              },
              max: function(value) {
                const maxAbs = Math.max(Math.abs(value.min || 0), Math.abs(value.max || 0))
                return maxAbs === 0 ? 0.001 : maxAbs
              },
              splitLine: { show: true }
            }
          ],
          dataZoom: [
            {
              type: 'inside',
              xAxisIndex: [0, 1, 3, 4],
              startValue: zoomRange.startValue,
              endValue: zoomRange.endValue
            }
          ],
          series: [
            {
              name: 'K线',
              type: 'candlestick',
              data: values,
              itemStyle: {
                color: '#ef232a',
                color0: '#14b143',
                borderColor: '#ef232a',
                borderColor0: '#14b143'
              }
            },
            // 拟合趋势线（与 KLineChart.vue 逻辑一致，基于收盘价）
            {
              id: 'trend-line',
              name: '拟合趋势线',
              type: 'line',
              xAxisIndex: 0,
              yAxisIndex: 0,
              data: trendLineData,
              showSymbol: false,
              smooth: false,
              lineStyle: { width: 1.5, color: '#fa8c16', type: 'dashed' },
              emphasis: { focus: 'series' }
            },
            // 买入点标记（在K线图上显示）
            ...(this.buyPoints && this.buyPoints.length > 0 ? [{
              name: '买入点',
              type: 'scatter',
              xAxisIndex: 0,
              yAxisIndex: 0,
              data: this.buyPoints,
              symbol: 'circle',
              symbolSize: 8,
              itemStyle: {
                color: '#52c41a'
              },
              label: {
                show: true,
                formatter: () => '买',
                color: '#52c41a',
                position: 'top',
                fontSize: 12
              }
            }] : []),
            // 卖出点标记（在K线图上显示）
            ...(this.sellPoints && this.sellPoints.length > 0 ? [{
              name: '卖出点',
              type: 'scatter',
              xAxisIndex: 0,
              yAxisIndex: 0,
              data: this.sellPoints,
              symbol: 'circle',
              symbolSize: 8,
              itemStyle: {
                color: '#f5222d'
              },
              label: {
                show: true,
                formatter: () => '卖',
                color: '#f5222d',
                position: 'bottom',
                fontSize: 12
              }
            }] : []),
            {
              name: '成交量',
              type: 'bar',
              xAxisIndex: 1,
              yAxisIndex: 1,
              data: volumes,
              itemStyle: {
                color: '#7fbe9e'
              }
            },
            {
              name: '全部数据',
              type: 'candlestick',
              xAxisIndex: 2,
              yAxisIndex: 2,
              data: values,
              itemStyle: {
                color: '#ef232a',
                color0: '#14b143',
                borderColor: '#ef232a',
                borderColor0: '#14b143'
              },
              emphasis: {
                disabled: true
              }
            },
            // 威廉指数WR10
            ...(this.chartData.wr10 && this.chartData.wr10.length > 0 ? [{
              name: 'Williams %R (10)',
              type: 'line',
              xAxisIndex: 3,
              yAxisIndex: 3,
              data: this.chartData.wr10,
              showSymbol: false,
              smooth: false,
              lineStyle: { width: 1, color: '#2f7ed8' }
            }] : []),
            // 威廉指数WR6
            ...(this.chartData.wr6 && this.chartData.wr6.length > 0 ? [{
              name: 'Williams %R (6)',
              type: 'line',
              xAxisIndex: 3,
              yAxisIndex: 3,
              data: this.chartData.wr6,
              showSymbol: false,
              smooth: false,
              lineStyle: { width: 1, color: '#d82f7e' }
            }] : []),
            // 买入点标记
            ...(this.chartData.thresholdPoints.buyPoints && this.chartData.thresholdPoints.buyPoints.length > 0 ? [{
              name: '>80 且差值<1 买',
              type: 'scatter',
              xAxisIndex: 3,
              yAxisIndex: 3,
              data: this.chartData.thresholdPoints.buyPoints,
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
            // 卖出点标记
            ...(this.chartData.thresholdPoints.sellPoints && this.chartData.thresholdPoints.sellPoints.length > 0 ? [{
              name: '<20 且差值<1 卖',
              type: 'scatter',
              xAxisIndex: 3,
              yAxisIndex: 3,
              data: this.chartData.thresholdPoints.sellPoints,
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
            }] : []),
            // MACD 柱
            ...(this.chartData.macdBAR && this.chartData.macdBAR.length > 0 ? [{
              name: 'MACD BAR',
              type: 'bar',
              xAxisIndex: 4,
              yAxisIndex: 4,
              data: this.chartData.macdBAR,
              barWidth: 2,
              itemStyle: {
                color: (params) => (params.value >= 0 ? '#f5222d' : '#14b143')
              },
              // y=0 参考线
              markLine: {
                symbol: 'none',
                silent: true,
                lineStyle: { color: '#bfbfbf', width: 1 },
                data: [{ yAxis: 0 }]
              }
            }] : []),
            // DIF 线
            ...(this.chartData.macdDIF && this.chartData.macdDIF.length > 0 ? [{
              name: 'DIF',
              type: 'line',
              xAxisIndex: 4,
              yAxisIndex: 4,
              data: this.chartData.macdDIF,
              showSymbol: false,
              smooth: false,
              lineStyle: { width: 1, color: '#fa8c16' }
            }] : []),
            // DEA 线
            ...(this.chartData.macdDEA && this.chartData.macdDEA.length > 0 ? [{
              name: 'DEA',
              type: 'line',
              xAxisIndex: 4,
              yAxisIndex: 4,
              data: this.chartData.macdDEA,
              showSymbol: false,
              smooth: false,
              lineStyle: { width: 1, color: '#2f54eb' }
            }] : [])
          ]
        }
        
        this._chart.setOption(option)
      },
      
      // 获取当前可视范围索引（startIndex, endIndex）
      getCurrentVisibleIndexRange(category) {
        try {
          if (!this._chart || !category || category.length === 0) {
            return { startIndex: 0, endIndex: Math.max(0, (category?.length || 1) - 1) }
          }
          const option = this._chart.getOption() || {}
          const dz = Array.isArray(option.dataZoom) && option.dataZoom.length > 0 ? option.dataZoom[0] : null
          if (!dz) return { startIndex: 0, endIndex: category.length - 1 }
          const start = typeof dz.startValue === 'number' ? dz.startValue : 0
          const end = typeof dz.endValue === 'number' ? dz.endValue : category.length - 1
          const startIndex = Math.max(0, Math.min(start, category.length - 1))
          const endIndex = Math.max(startIndex, Math.min(end, category.length - 1))
          return { startIndex, endIndex }
        } catch (e) {
          return { startIndex: 0, endIndex: Math.max(0, (category?.length || 1) - 1) }
        }
      },
      
      // 趋势线计算已移至 utils/trend.ts
      
      // 计算威廉指数
      calculateWilliamsR() {
        const { highs, lows, closes } = this.chartData
        if (!highs || !lows || !closes || highs.length === 0) {
          this.chartData.wr6 = []
          this.chartData.wr10 = []
          this.chartData.thresholdPoints = { buyPoints: [], sellPoints: [] }
          return
        }
        
        // 计算WR6和WR10
        this.chartData.wr10 = computeWilliamsR(highs, lows, closes, 10)
        this.chartData.wr6 = computeWilliamsR(highs, lows, closes, 6)
        
        // 计算买卖点
        this.chartData.thresholdPoints = computeThresholdPointsWithNear(
          this.chartData.category,
          this.chartData.wr6,
          this.chartData.wr10,
          80,
          20,
          1
        )
      },
      
      // 转换数据并渲染图表
      convertAndRenderChart() {
        this.$nextTick(() => {
          // 计算威廉指数
          this.calculateWilliamsR()
          // 计算 MACD
          this.calculateMACD()
          // 渲染图表
          this.renderChart()
        })
      }
    },
    
    watch: {
      showDays() {
        // 当showDays改变时，只更新缩放范围
        console.log('showDays改变，更新缩放范围:', this.showDays)
        this.$nextTick(() => {
          this.updateZoom()
        })
      },
      code() {
        this.getKlineData()
      }
    },
    
    mounted() {
      this.initChart()
      this.getKlineData()
    },
    
    beforeDestroy() {
      if (this._chart) {
        this._chart.dispose()
        this._chart = null
      }
      window.removeEventListener('resize', () => {})
    }
  }
  
  
  
  </script>
  
  <style scoped>
  .kline-container {
    width: 100%;
    height: 100%;
    display: flex;
    flex-direction: column;
  }
  
  .stock-info {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 10px 16px;
    background-color: #f5f5f5;
    border-bottom: 1px solid #e8e8e8;
  }
  
  .stock-info h3 {
    margin: 0;
    font-size: 16px;
    color: #333;
  }
  
  .refresh-btn {
    padding: 6px 12px;
    background-color: #1890ff;
    color: white;
    border: none;
    border-radius: 4px;
    cursor: pointer;
    font-size: 12px;
  }
  
  .refresh-btn:hover:not(:disabled) {
    background-color: #40a9ff;
  }
  
  .refresh-btn:disabled {
    background-color: #d9d9d9;
    cursor: not-allowed;
  }
  
  .loading {
    display: flex;
    justify-content: center;
    align-items: center;
    height: 400px;
    font-size: 14px;
    color: #666;
  }
  
  .kline-chart {
    width: 100%;
    height: 1200px;
    box-sizing: border-box;
  }
  
  .wheel-mask {
    position: absolute;
    top: 570px; /* K 线图结束位置：top 70 + height 500 */
    left: 0;
    right: 0;
    bottom: 0;
    pointer-events: auto; /* 拦截鼠标事件，阻止滚轮事件穿透 */
    z-index: 1000; /* 确保在图表上方 */
  }
  
  .kline-container {
    position: relative; /* 为遮罩层提供定位上下文 */
  }
  </style>
  