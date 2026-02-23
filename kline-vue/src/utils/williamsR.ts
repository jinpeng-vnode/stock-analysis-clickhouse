/**
 * Williams %R 指标计算工具
 */

/**
 * 计算Williams %R指标
 * @param highs 最高价数组
 * @param lows 最低价数组
 * @param closes 收盘价数组
 * @param n 计算周期，默认14
 * @returns Williams %R值数组（0-100，数值越小越接近超买，越大越接近超卖）
 */
export function computeWilliamsR(
  highs: number[],
  lows: number[],
  closes: number[],
  n: number = 14
): number[] {
  const len = closes.length
  const result = new Array(len).fill(null)
  
  if (!highs || !lows || !closes || len === 0 || n <= 1) {
    return result
  }
  
  for (let i = 0; i < len; i++) {
    if (i < n - 1) {
      result[i] = null
      continue
    }
    
    let highest = -Infinity
    let lowest = Infinity
    
    // 计算n周期内的最高价和最低价
    for (let j = i - n + 1; j <= i; j++) {
      if (highs[j] > highest) highest = highs[j]
      if (lows[j] < lowest) lowest = lows[j]
    }
    
    const denom = highest - lowest
    if (denom === 0 || !isFinite(denom)) {
      result[i] = null
      continue
    }
    
    // 计算Williams %R（正数区间 0~100）
    const wrPositive = (highest - closes[i]) / denom * 100
    result[i] = wrPositive
  }
  
  return result
}

/**
 * 计算阈值点（买卖点）
 * @param category 日期数组
 * @param wr Williams %R值数组
 * @param buyThreshold 买入阈值，默认80
 * @param sellThreshold 卖出阈值，默认20
 * @returns 买卖点数组
 */
export function computeThresholdPoints(
  category: string[],
  wr: number[],
  buyThreshold: number = 80,
  sellThreshold: number = 20
): { buyPoints: [string, number][]; sellPoints: [string, number][] } {
  const buyPoints: [string, number][] = []
  const sellPoints: [string, number][] = []
  const len = Math.min(category.length, wr.length)
  
  for (let i = 0; i < len; i++) {
    const v = wr[i]
    if (v == null) continue
    
    if (v >= buyThreshold) {
      buyPoints.push([category[i], v])
    } else if (v <= sellThreshold) {
      sellPoints.push([category[i], v])
    }
  }
  
  return { buyPoints, sellPoints }
}

/**
 * 计算接近阈值点（WR6和WR10差值小于near的买卖点）
 * @param category 日期数组
 * @param wr6 WR6值数组
 * @param wr10 WR10值数组
 * @param buyThreshold 买入阈值，默认80
 * @param sellThreshold 卖出阈值，默认20
 * @param near 接近阈值，默认1
 * @returns 买卖点数组
 */
export function computeThresholdPointsWithNear(
  category: string[],
  wr6: number[],
  wr10: number[],
  buyThreshold: number = 80,
  sellThreshold: number = 20,
  near: number = 1
): { buyPoints: [string, number][]; sellPoints: [string, number][] } {
  const buyPoints: [string, number][] = []
  const sellPoints: [string, number][] = []
  const len = Math.min(category.length, wr6.length, wr10.length)
  
  for (let i = 0; i < len; i++) {
    const a = wr6[i]
    const b = wr10[i]
    if (a == null || b == null) continue
    
    const diff = Math.abs(a - b)
    if (diff < near && a >= buyThreshold) {
      buyPoints.push([category[i], a])
    } else if (diff < near && a <= sellThreshold) {
      sellPoints.push([category[i], a])
    }
  }
  
  return { buyPoints, sellPoints }
}

/**
 * 计算接近点（WR6和WR10差值小于threshold的点）
 * @param category 日期数组
 * @param wr6 WR6值数组
 * @param wr10 WR10值数组
 * @param threshold 接近阈值，默认1
 * @returns 接近点数组
 */
export function computeClosePoints(
  category: string[],
  wr6: number[],
  wr10: number[],
  threshold: number = 1
): [string, number][] {
  const points: [string, number][] = []
  const len = Math.min(category.length, wr6.length, wr10.length)
  
  for (let i = 0; i < len; i++) {
    const a = wr6[i]
    const b = wr10[i]
    if (a == null || b == null) continue
    
    if (Math.abs(a - b) < threshold) {
      points.push([category[i], a])
    }
  }
  
  return points
}
