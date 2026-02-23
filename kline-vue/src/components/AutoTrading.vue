<template>
    <div class="auto-trading">

        <div>开始日期：{{ beganDate }}</div>
        <div>结束日期：{{ endDate }}</div>
        <div>股票代码： </div>



        <a-button @click="anylysiRef.prev()">上一个</a-button>
        <a-button @click="anylysiRef.next()">下一个</a-button>
       

        <a-button @click="autoTrade()">自动交易</a-button>
        <a-button v-if="!isAutoLoop" type="primary" @click="startContinuous()">连续自动</a-button>
        <a-button v-else danger @click="stopContinuous()">暂停</a-button>


    </div>
</template>

<script>
import { getStockDailyLocalData } from '@/api/stocks'

export default {
    name: 'AutoTrading',
    props: {
        simTradingRef: {
            type: Object,
            required: true
        },
        anylysiRef: {
            type: Object,
            required: true
        },
        beganDate: {
            type: String,
            required: true
        },
        endDate: {
            type: String,
            required: true
        },
        data: {
            type: Object,
            required: true
        }
    },
    data() {
        return {
            // 记录当前遍历到的索引，便于多次点击从上次位置继续
            currentIndex: 0,
            isAutoLoop: false,
            loopDelayMs: 1000,
            loopTimeoutId: null
        }
    },
    methods: {
        // 启动连续自动
        startContinuous() {
            if (this.isAutoLoop) return
            this.isAutoLoop = true
            this.scheduleNextLoop()
        },
        // 停止连续自动
        stopContinuous() {
            this.isAutoLoop = false
            if (this.loopTimeoutId) {
                clearTimeout(this.loopTimeoutId)
                this.loopTimeoutId = null
            }
        },
        // 调度下一次自动交易
        scheduleNextLoop() {
            if (!this.isAutoLoop) return
            this.loopTimeoutId = setTimeout(async () => {
                try {
                    // 记录本轮开始时的索引，用于检测是否已经回绕到新一轮
                    const startIdx = this.currentIndex
                    await this.autoTrade()
                    // 若已停止，则不再继续
                    if (!this.isAutoLoop) return
                    // 若索引回到起点或更小，说明完成了一整轮，自动停止，避免进入第二轮
                    if (this.currentIndex <= startIdx) {
                        this.stopContinuous()
                        return
                    }
                } finally {
                    if (this.isAutoLoop) {
                        this.scheduleNextLoop()
                    }
                }
            }, this.loopDelayMs)
        },
        //   计算日期范围内的斜率
        calculateSlope(dates = [], values = [], startDate = '', endDate = '') {
            if (!Array.isArray(dates) || !Array.isArray(values)) return 0
            const n = Math.min(dates.length, values.length)
            if (n === 0) return 0

            const toTs = (s) => {
                if (!s) return NaN
                const t = new Date(String(s))
                return t.getTime()
            }

            const sTs = toTs(startDate)
            const eTs = toTs(endDate)

            // 保持原始顺序，按区间过滤
            const ys = []
            for (let i = 0; i < n; i++) {
                const ts = toTs(dates[i])
                const y = Number(values[i])
                if (isNaN(ts) || !Number.isFinite(y)) continue
                if (!isNaN(sTs) && ts < sTs) continue
                if (!isNaN(eTs) && ts > eTs) continue
                ys.push(y)
            }

            // 若区间内不足两点，回退到全量（仍保持原顺序）
            const series = ys.length > 1 ? ys : (function(){
                const all = []
                for (let i = 0; i < n; i++) {
                    const y = Number(values[i])
                    if (Number.isFinite(y)) all.push(y)
                }
                return all
            })()

            const m = series.length
            if (m <= 1) return 0

            let sumX = 0
            let sumY = 0
            let sumXY = 0
            let sumXX = 0
            for (let i = 0; i < m; i++) {
                const x = i
                const y = series[i]
                sumX += x
                sumY += y
                sumXY += x * y
                sumXX += x * x
            }
            const denominator = m * sumXX - sumX * sumX
            if (denominator === 0) return 0
            return (m * sumXY - sumX * sumY) / denominator
        },

        //  获取股票的日线数据
        async getStockDailyData(code) {
            if (!code) return []
            const json = await getStockDailyLocalData(code)
            const rows = Array.isArray(json?.data) ? json.data : []
            return rows
        },

        //autoTrade：从 currentIndex 开始，遇到斜率>0即停止；再次点击从上次位置继续
        async autoTrade() {
            if (!this.data || !Array.isArray(this.data.stocks)) return
            const stocks = this.data.stocks
            if (!stocks.length) return

            // 防御：索引越界时回绕
            if (this.currentIndex < 0 || this.currentIndex >= stocks.length) {
                this.currentIndex = 0
            }

            let found = false
            for (let i = this.currentIndex; i < stocks.length; i++) {
                const item = stocks[i]
                const rows = await this.getStockDailyData(item.code)
                if (!Array.isArray(rows) || rows.length === 0) {
                    console.warn('no rows for', item.code)
                    continue
                }
                const dates = rows.map(r => String(r['日期'] ?? r.date ?? ''))
                const closes = rows.map(r => Number(r['收盘'] ?? r.close ?? NaN))
                const slope = this.calculateSlope(dates, closes, this.beganDate || '', this.endDate || '')
                console.log('index:', i, 'code:', item.code, 'name:', item.name, '正向增长斜率:', slope)
                if (slope > 0) {
                    this.anylysiRef.setSelectedStockByCode(item.code)

                    //todo 自动交易购买100股,
                    // 规则：近7个交易日出现≥3个买入信号，且最后一天为买点，则买入
                    try {
                        // 确定窗口结束索引（不超过 endDate）
                        const toTs = (s) => {
                            if (!s) return NaN
                            const t = new Date(String(s))
                            return t.getTime()
                        }
                        const endTs = toTs(this.endDate)
                        let endIdx = rows.length - 1
                        if (!isNaN(endTs)) {
                            for (let k = rows.length - 1; k >= 0; k--) {
                                const d = String(rows[k]['日期'] ?? rows[k].date ?? '')
                                const ts = toTs(d)
                                if (isNaN(ts) || ts > endTs) continue
                                endIdx = k
                                break
                            }
                        }
                        if (endIdx < 0) endIdx = rows.length - 1
                        // 先做“近5天全绿”过滤：收盘 < 开盘 视为绿K，若近5天全部为绿则跳过
                        const last5Start = Math.max(0, endIdx - 4)
                        const last5Rows = rows.slice(last5Start, endIdx + 1)
                        const allGreen5 = last5Rows.length === 5 && last5Rows.every(r => {
                            const open = Number(r['开盘'] ?? r.open ?? 0)
                            const close = Number(r['收盘'] ?? r.close ?? 0)
                            return Number.isFinite(open) && Number.isFinite(close) && close < open
                        })
                        if (allGreen5) {
                            console.log('[AutoTrading] 近5天全部为绿K，跳过买入', { code: item.code })
                            continue
                        }

                        const startIdx = Math.max(0, endIdx - 6) // 近7个交易日
                        const windowRows = rows.slice(startIdx, endIdx + 1)

                        // 提取买点标记：后端列名为“最佳买点”，兜底 buySignal
                        const buyFlags = windowRows.map(r => Number(r['最佳买点'] ?? r.buySignal ?? 0) === 1)
                        const buyCount = buyFlags.reduce((acc, v) => acc + (v ? 1 : 0), 0)
                        const lastIsBuy = buyFlags.length > 0 ? buyFlags[buyFlags.length - 1] : false

                        if (buyCount >= 3 && lastIsBuy) {
                            const last = windowRows[windowRows.length - 1] || {}
                            const lastClose = Number(last['收盘'] ?? last.close ?? 0)
                            const lastDate = String(last['日期'] ?? last.date ?? '')
                            if (Number.isFinite(lastClose) && lastClose > 0) {
                                // 触发模拟下单：买入100股
                                this.simTradingRef?.buy(item.code, lastClose, 100, item.name, lastDate)
                                console.log('[AutoTrading] 规则满足，已下单买入100股', { code: item.code, name: item.name, price: lastClose, date: lastDate, buyCount })

                                // 从买入当日之后开始，向后查找首个“最佳卖点”，以该日收盘价卖出同等数量
                                try {
                                    // 找到买入在全量 rows 中的下标 buyIdx
                                    let buyIdx = -1
                                    for (let k = 0; k < rows.length; k++) {
                                        const d = String(rows[k]['日期'] ?? rows[k].date ?? '')
                                        if (d === lastDate) {
                                            buyIdx = k
                                            break
                                        }
                                    }
                                    if (buyIdx >= 0 && buyIdx < rows.length - 1) {
                                        let sellIdx = -1
                                        for (let k = buyIdx + 1; k < rows.length; k++) {
                                            const isSell = Number(rows[k]['最佳卖点'] ?? rows[k].sellSignal ?? 0) === 1
                                            if (isSell) {
                                                sellIdx = k
                                                break
                                            }
                                        }
                                        if (sellIdx >= 0) {
                                            // 规则修正：以“卖点当日的收盘价”作为卖出价格；
                                            // 使用“卖点次日的开盘价”验证能否成交（若开盘价 >= 卖点收盘价，则在次日按卖点收盘价成交），否则等待下一个卖点。
                                            let executed = false
                                            for (let m = sellIdx; m < rows.length && !executed; m++) {
                                                const isSellPoint = Number(rows[m]['最佳卖点'] ?? rows[m].sellSignal ?? 0) === 1
                                                if (!isSellPoint) continue
                                                const nextDay = m + 1
                                                if (nextDay >= rows.length) {
                                                    // 无下一交易日，无法在该卖点第二天卖出，继续找下一个卖点
                                                    continue
                                                }
                                                const sellRow = rows[m]
                                                const sellClosePx = Number(sellRow['收盘'] ?? sellRow.close ?? 0)
                                                const nextRow = rows[nextDay]
                                                const highNext = Number(nextRow['最高'] ?? nextRow.high ?? 0)
                                                const dateNext = String(nextRow['日期'] ?? nextRow.date ?? '')
                                                if (Number.isFinite(sellClosePx) && sellClosePx > 0 && Number.isFinite(highNext) && highNext > 0 && highNext >= sellClosePx) {
                                                    // 校验通过：在次日以“卖点收盘价”成交
                                                    this.simTradingRef?.sell(item.code, sellClosePx, 100, item.name, dateNext)
                                                    console.log('[AutoTrading] 卖点次日最高价>=卖点收盘价，按卖点收盘价卖出100股', { code: item.code, name: item.name, price: sellClosePx, date: dateNext })
                                                    executed = true
                                                    break
                                                } else {
                                                    console.warn('[AutoTrading] 次日最高价不足以在卖点收盘价成交，继续等待下一个卖点', { code: item.code, dateNext, highNext, sellClosePx })
                                                    // 继续外层 for 循环，寻找后续卖点
                                                    continue
                                                }
                                            }
                                            if (!executed) {
                                                console.log('[AutoTrading] 买入后找到卖点但无法在次日卖出，继续等待未来卖点')
                                            }
                                        } else {
                                            console.log('[AutoTrading] 买入后未找到后续卖点')
                                        }
                                    }
                                } catch (e) {
                                    console.warn('[AutoTrading] 自动卖出规则执行异常', e)
                                }
                            } else {
                                console.warn('[AutoTrading] 价格异常，跳过下单', { code: item.code, lastClose })
                            }
                        } else {
                            console.log('[AutoTrading] 规则不满足，跳过下单', { code: item.code, buyCount, lastIsBuy })
                        }
                    } catch (err) {
                        console.warn('[AutoTrading] 自动下单规则执行异常', err)
                    }
                  








                    // 下次从命中项的下一个开始
                    this.currentIndex = i + 1
                    if (this.currentIndex >= stocks.length) {
                        this.currentIndex = 0
                    }
                    found = true
                    break
                }
            }

            // 若本轮未命中并且已到末尾，下次从0开始
            if (!found) {
                this.currentIndex = 0
            }
        }



    }
    ,
    beforeUnmount() {
        if (this.loopTimeoutId) {
            clearTimeout(this.loopTimeoutId)
            this.loopTimeoutId = null
        }
        this.isAutoLoop = false
    }
}
</script>

<style scoped></style>
