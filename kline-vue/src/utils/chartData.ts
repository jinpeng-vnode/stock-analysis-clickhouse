import type { StockData, KlineData } from '@/types'

/**
 * 将股票数据转换为K线图数据格式
 * @param data 股票数据数组
 * @returns K线图数据对象
 */
export function toKline(data: StockData[]): KlineData {
  const category: string[] = []
  const values: number[][] = []
  const volumes: number[] = []
  const highs: number[] = []
  const lows: number[] = []
  const closes: number[] = []
  const wr6Backend: number[] = []
  const wr10Backend: number[] = []
  const buyPointsBackend: [string, number][] = []
  const sellPointsBackend: [string, number][] = []
  
  for (const row of data) {
    category.push(row['日期'])
    values.push([row['开盘'], row['收盘'], row['最低'], row['最高']])
    volumes.push(row['成交量'])
    highs.push(row['最高'])
    lows.push(row['最低'])
    closes.push(row['收盘'])
    
    // 后端WR列（若存在）
    const v6 = row['WR6']
    const v10 = row['WR10']
    wr6Backend.push(
      (v6 === null || v6 === undefined || isNaN(Number(v6))) ? 0 : Number(v6)
    )
    wr10Backend.push(
      (v10 === null || v10 === undefined || isNaN(Number(v10))) ? 0 : Number(v10)
    )
    
    // 后端买点卖点标记（若存在）
    const buyPoint = row['最佳买点']
    const sellPoint = row['最佳卖点']
    const wr6Value = (v6 === null || v6 === undefined || isNaN(Number(v6))) ? 0 : Number(v6)
    
    if (buyPoint === 1 && wr6Value > 0) {
      buyPointsBackend.push([row['日期'], wr6Value])
    }
    if (sellPoint === 1 && wr6Value > 0) {
      sellPointsBackend.push([row['日期'], wr6Value])
    }
  }
  
  return {
    category,
    values,
    volumes,
    highs,
    lows,
    closes,
    wr6Backend,
    wr10Backend,
    buyPointsBackend,
    sellPointsBackend
  }
}

/**
 * 格式化日期为YYYY-MM-DD格式
 * @param date 日期对象
 * @returns 格式化后的日期字符串
 */
export function formatDate(date: Date): string {
  const y = date.getFullYear()
  const m = String(date.getMonth() + 1).padStart(2, '0')
  const day = String(date.getDate()).padStart(2, '0')
  return `${y}-${m}-${day}`
}

/**
 * 计算最近N个月的日期范围
 * @param category 日期数组
 * @param months 月数，默认3
 * @returns 开始和结束日期
 */
export function calculateDateRange(
  category: string[],
  months: number = 3
): { startValue?: string; endValue?: string } {
  if (!category || category.length === 0) {
    return {}
  }
  
  const lastDateStr = category[category.length - 1]
  const lastDate = new Date(lastDateStr)
  
  if (isNaN(lastDate.getTime())) {
    return {}
  }
  
  const targetDate = new Date(lastDate)
  targetDate.setMonth(targetDate.getMonth() - months)
  
  let startIdx = 0
  for (let i = 0; i < category.length; i++) {
    const d = new Date(category[i])
    if (!isNaN(d.getTime()) && d >= targetDate) {
      startIdx = i
      break
    }
  }
  
  return {
    startValue: category[startIdx],
    endValue: category[category.length - 1]
  }
}

/**
 * 合并多天数据并排序
 * @param dataArrays 多天数据数组
 * @returns 合并并排序后的数据
 */
export function mergeAndSortData(dataArrays: StockData[][]): StockData[] {
  const merged: StockData[] = []
  
  for (const data of dataArrays) {
    if (Array.isArray(data)) {
      merged.push(...data)
    }
  }
  
  // 按日期排序
  merged.sort((a, b) => {
    const ta = new Date(a['日期']).getTime()
    const tb = new Date(b['日期']).getTime()
    if (!isNaN(ta) && !isNaN(tb)) return ta - tb
    return 0
  })
  
  return merged
}
