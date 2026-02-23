<template>
  <a-card title="模拟交易" style="margin-top: 16px;">
    <template #extra>
      <a-switch v-model:checked="isAutoTrade" />
    </template>

    <a-form :model="trade" layout="vertical">
      <a-form-item label="日期范围" name="beginDate">
        <a-space direction="vertical" style="width: 100%">
          <a-space>
            <a-date-picker v-model:value="trade.beginDate" placeholder="选择开始日期" format="YYYY-MM-DD"
              value-format="YYYY-MM-DD" />
            <a-date-picker v-model:value="trade.endDate" placeholder="选择结束日期" format="YYYY-MM-DD"
              value-format="YYYY-MM-DD" />
          </a-space>
          <a-space>
            <a-button size="small" @click="setDateRange(3)">最近3个月</a-button>
            <a-button size="small" @click="setDateRange(6)">最近半年</a-button>
            <a-button size="small" @click="setDateRange(12)">最近一年</a-button>
            <a-button size="small" @click="setDateRange(24)">最近两年</a-button>
            <a-button size="small" @click="setDateRange(120)">最近10年</a-button>
          </a-space>
        </a-space>
      </a-form-item>
      <a-form-item>
        <a-button type="primary" @click="handleTrade">开始模拟交易</a-button>
      </a-form-item>
    </a-form>

    <a-table :dataSource="trade.history" :columns="expandedTradeColumns" :pagination="{ pageSize: 10 }"
      size="small">
      <template #bodyCell="{ column, record }">
        <template v-if="column.key === 'profit'">
          <span v-if="record.type === '卖出'" :style="{ color: record.profit >= 0 ? '#f5222d' : '#52c41a' }">
            {{ record.profit.toFixed(2) }}
          </span>
          <span v-else>-</span>
        </template>
        <template v-if="column.key === 'profitRate'">
          <span v-if="record.type === '卖出'"
            :style="{ color: parseFloat(record.profitRate) >= 0 ? '#f5222d' : '#52c41a' }">
            {{ record.profitRate }}
          </span>
          <span v-else>-</span>
        </template>
      </template>
    </a-table>
  </a-card>
</template>

<script>
import { getStockDailyData } from '@/api/stocks';

export default {
  name: 'SimulatedTrading',
  props: {
    selectedCode: {
      type: String,
      default: '000001'
    },
    today: {
      type: String,
      default: '2025-10-09'
    }
  },
  data() {
    return {
      trade: {
        beginDate: null,
        endDate: null,
        history: []
      },
      isAutoTrade: false,
      expandedTradeColumns: [
        {
          title: '类型',
          dataIndex: 'type',
          key: 'type',
          width: 60
        },
        {
          title: '日期',
          dataIndex: 'date',
          key: 'date',
          width: 100
        },
        {
          title: '价格',
          dataIndex: 'price',
          key: 'price',
          width: 80
        },
        {
          title: '股数',
          dataIndex: 'shares',
          key: 'shares',
          width: 60
        },
        {
          title: '收益',
          dataIndex: 'profit',
          key: 'profit',
          width: 80
        },
        {
          title: '收益率',
          dataIndex: 'profitRate',
          key: 'profitRate',
          width: 80
        }
      ]
    }
  },
  watch: {
    // 监听自动执行开关变化
    isAutoTrade(newVal) {
      if (newVal && this.selectedCode && this.trade.beginDate && this.trade.endDate) {
        console.log('自动执行开关打开，立即执行模拟交易')
        this.handleTrade()
      }
    },
    // 监听选中股票变化，如果自动执行开关打开，且有日期范围，则自动执行
    selectedCode(newVal) {
      if (newVal && this.isAutoTrade && this.trade.beginDate && this.trade.endDate) {
        console.log('股票变化，自动执行模拟交易')
        this.handleTrade()
      }
    }
  },
  methods: {
    async handleTrade() {
      console.log('模拟交易参数:', this.trade)

      if (!this.trade.beginDate || !this.trade.endDate) {
        this.$message.warning('请选择开始日期和结束日期')
        return
      }

      if (!this.selectedCode) {
        this.$message.warning('请先选择股票')
        return
      }

      try {
        this.$message.loading('正在执行模拟交易...', 0)

        // 获取股票日线数据
        const data = await getStockDailyData(this.selectedCode, {
          start: this.trade.beginDate,
          end: this.trade.endDate
        })
        const dailyData = data.data || []

        if (dailyData.length === 0) {
          this.$message.error('未获取到股票数据')
          return
        }

        // 执行模拟交易逻辑
        const trades = []
        let currentPosition = null // 当前持仓
        let totalProfit = 0

        // 按日期排序
        const sortedData = dailyData.sort((a, b) => new Date(a.日期) - new Date(b.日期))
        console.log(`开始模拟交易，数据范围: ${sortedData[0]?.日期} 到 ${sortedData[sortedData.length - 1]?.日期}`)

        let i = 0
        while (i < sortedData.length) {
          const currentDay = sortedData[i]
          console.log(`处理日期: ${currentDay.日期}, 持仓状态: ${currentPosition ? '有持仓' : '无持仓'}`)

          // 如果没有持仓，寻找买入机会
          if (!currentPosition) {
            // 寻找三个连续的买入信号
            let consecutiveCount = 0
            let buySignalIndex = -1

            for (let j = i; j < sortedData.length; j++) {
              const day = sortedData[j]
              const isBuySignal = day['最佳买点'] || false

              if (isBuySignal) {
                consecutiveCount++
                if (consecutiveCount === 3) {
                  // 找到第三个连续买入信号
                  buySignalIndex = j
                  break
                }
              } else {
                // 重置计数
                consecutiveCount = 0
              }
            }

            if (buySignalIndex !== -1) {
              const buySignal = sortedData[buySignalIndex]
              // 在第三个买入信号处买入
              const buyPrice = parseFloat(buySignal.收盘)
              const buyDate = buySignal.日期
              currentPosition = {
                buyPrice,
                buyDate,
                shares: 100 // 固定买入100股
              }
              console.log(`买入信号: ${buyDate}, 价格: ${buyPrice}`)

              // 添加买入记录
              trades.push({
                type: '买入',
                date: buyDate,
                price: buyPrice,
                shares: 100,
                profit: '',
                profitRate: ''
              })

              // 更新索引到买入日期之后
              i = buySignalIndex + 1
            } else {
              // 没有找到买入信号，继续下一日
              i++
            }
          } else {
            // 有持仓，寻找卖出机会
            let sellSignalIndex = -1

            // 从当前位置开始，寻找第一个卖出信号
            for (let j = i; j < sortedData.length; j++) {
              const day = sortedData[j]
              const isSellSignal = day['最佳卖点'] || false

              if (isSellSignal) {
                sellSignalIndex = j
                break
              }
            }

            if (sellSignalIndex !== -1) {
              const sellSignal = sortedData[sellSignalIndex]
              // 卖出
              const sellPrice = parseFloat(sellSignal.收盘)
              const sellDate = sellSignal.日期
              const profit = (sellPrice - currentPosition.buyPrice) * currentPosition.shares

              // 添加卖出记录
              trades.push({
                type: '卖出',
                date: sellDate,
                price: sellPrice,
                shares: currentPosition.shares,
                profit: profit,
                profitRate: ((sellPrice - currentPosition.buyPrice) / currentPosition.buyPrice * 100).toFixed(2) + '%'
              })

              totalProfit += profit

              console.log(`卖出信号: ${sellDate}, 价格: ${sellPrice}, 收益: ${profit.toFixed(2)}`)

              // 清空持仓
              currentPosition = null
              // 更新索引到卖出日期之后
              i = sellSignalIndex + 1
            } else {
              // 没有找到卖出信号，继续下一日
              i++
            }
          }
        }

        // 更新交易历史
        this.trade.history = trades

        this.$message.destroy()

        // 检查是否有未完成的持仓
        if (currentPosition) {
          const lastDay = sortedData[sortedData.length - 1]
          const currentPrice = parseFloat(lastDay.收盘)
          const unrealizedProfit = (currentPrice - currentPosition.buyPrice) * currentPosition.shares
          console.log(`当前持仓: ${currentPosition.buyDate} 买入 ${currentPosition.buyPrice}, 当前价格: ${currentPrice}, 未实现收益: ${unrealizedProfit.toFixed(2)}`)

          this.$message.success(`模拟交易完成！共执行 ${trades.length} 笔交易，总收益: ${totalProfit.toFixed(2)}。当前仍有持仓，未实现收益: ${unrealizedProfit.toFixed(2)}`)
        } else {
          this.$message.success(`模拟交易完成！共执行 ${trades.length} 笔交易，总收益: ${totalProfit.toFixed(2)}`)
        }

      } catch (error) {
        this.$message.destroy()
        this.$message.error('模拟交易失败: ' + error.message)
        console.error('模拟交易错误:', error)
      }
    },

    // 设置日期范围快捷选择
    setDateRange(months) {
      // 使用 this.today 作为结束日期
      const todayDate = new Date(this.today)
      const endDate = new Date(todayDate.getFullYear(), todayDate.getMonth(), todayDate.getDate())
      const startDate = new Date(todayDate.getFullYear(), todayDate.getMonth() - months, todayDate.getDate())

      // 格式化日期为 YYYY-MM-DD
      const formatDate = (date) => {
        const year = date.getFullYear()
        const month = String(date.getMonth() + 1).padStart(2, '0')
        const day = String(date.getDate()).padStart(2, '0')
        return `${year}-${month}-${day}`
      }

      this.trade.beginDate = formatDate(startDate)
      this.trade.endDate = formatDate(endDate)

      // 显示提示信息
      const monthNames = {
        3: '3个月',
        6: '半年',
        12: '一年',
        24: '两年',
        120: '10年'
      }
      this.$message.success(`已选择最近${monthNames[months]}的数据`)
    }
  }
}
</script>

<style scoped>
/* 减小表单项的底部间距 */
:deep(.ant-form-item) {
  margin-bottom: 12px;
}
</style>

