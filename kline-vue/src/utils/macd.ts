/**
 * MACD utilities: EMA, EMA for series with nulls, and MACD (DIF/DEA/BAR).
 */

export function ema(values: number[], period: number): (number | null)[] {
  const n = Array.isArray(values) ? values.length : 0
  if (!n || period <= 0) return []
  const k = 2 / (period + 1)
  const out: (number | null)[] = new Array(n).fill(null)
  let prev: number | null = null
  for (let i = 0; i < n; i++) {
    const v = Number(values[i])
    if (!Number.isFinite(v)) { out[i] = prev; continue }
    if (prev === null) {
      prev = v
    } else {
      prev = v * k + prev * (1 - k)
    }
    out[i] = prev
  }
  return out
}

export function emaSeriesAllowNull(values: Array<number | null>, period: number): (number | null)[] {
  const n = Array.isArray(values) ? values.length : 0
  if (!n || period <= 0) return []
  const k = 2 / (period + 1)
  const out: (number | null)[] = new Array(n).fill(null)
  let prev: number | null = null
  for (let i = 0; i < n; i++) {
    const v = values[i]
    if (v == null || !Number.isFinite(v)) {
      out[i] = prev
      continue
    }
    if (prev === null) {
      prev = v
    } else {
      prev = v * k + prev * (1 - k)
    }
    out[i] = prev
  }
  return out
}

export function calculateMACDSeries(closes: number[]): {
  dif: (number | null)[]
  dea: (number | null)[]
  bar: (number | null)[]
} {
  if (!Array.isArray(closes) || closes.length === 0) {
    return { dif: [], dea: [], bar: [] }
  }
  const ema12 = ema(closes as number[], 12)
  const ema26 = ema(closes as number[], 26)
  const dif = ema12.map((e12, i) => {
    const e26 = ema26[i]
    if (e12 == null || e26 == null) return null
    return (e12 as number) - (e26 as number)
  })
  const dea = emaSeriesAllowNull(dif, 9)
  const bar = dif.map((d, i) => {
    const e = dea[i]
    if (d == null || e == null) return null
    return 2 * ((d as number) - (e as number))
  })
  return { dif, dea, bar }
}


