/**
 * Linear trend utilities.
 * Compute a linear fit on a specific visible range and fill null outside.
 */

export function computeLinearTrendOnRange(
  values: Array<number | null>,
  range: { startIndex: number; endIndex: number }
): (number | null)[] {
  if (!Array.isArray(values) || values.length === 0) return []
  const n = values.length
  const s = Math.max(0, Math.min(range?.startIndex ?? 0, n - 1))
  const e = Math.max(s, Math.min(range?.endIndex ?? (n - 1), n - 1))
  const m = e - s + 1
  if (m <= 1) {
    const base = Number(values[s] ?? values[0] ?? 0)
    const out: (number | null)[] = new Array(n).fill(null)
    if (Number.isFinite(base)) {
      for (let i = s; i <= e; i++) out[i] = base
    }
    return out
  }
  let sumX = 0
  let sumY = 0
  let sumXY = 0
  let sumXX = 0
  for (let i = s; i <= e; i++) {
    const x = i - s
    const y = Number(values[i])
    if (!Number.isFinite(y)) continue
    sumX += x
    sumY += y
    sumXY += x * y
    sumXX += x * x
  }
  const nWin = e - s + 1
  const denominator = nWin * sumXX - sumX * sumX
  let slope = 0
  let intercept = 0
  if (denominator === 0) {
    const mean = sumY / (nWin || 1)
    intercept = mean
    slope = 0
  } else {
    slope = (nWin * sumXY - sumX * sumY) / denominator
    intercept = (sumY - slope * sumX) / nWin
  }
  const out: (number | null)[] = new Array(n).fill(null)
  for (let i = s; i <= e; i++) {
    const x = i - s
    out[i] = intercept + slope * x
  }
  return out
}


