// 股票数据相关类型
export interface StockData {
  日期: string
  开盘: number
  收盘: number
  最高: number
  最低: number
  成交量: number
  成交额?: number
  WR6?: number
  WR10?: number
  最佳买点?: number
  最佳卖点?: number
  名称?: string
  // 新增趋势指标
  '7日斜率'?: number
  '7日拟合值'?: number
  '180日拟合值'?: number
}

export interface StockInfo {
  code: string
  name: string
  date?: string
}

export interface ApiResponse {
  code: string
  name: string
  date?: string
  data: StockData[]
}

// 图表数据相关类型
export interface KlineData {
  category: string[]
  values: number[][]
  volumes: number[]
  highs: number[]
  lows: number[]
  closes: number[]
  wr6Backend?: number[]
  wr10Backend?: number[]
  buyPointsBackend?: [string, number][]
  sellPointsBackend?: [string, number][]
}

export interface ThresholdPoint {
  date: string
  value: number
}

export interface ThresholdPoints {
  buyPoints: [string, number][]
  sellPoints: [string, number][]
}

// 搜索相关类型
export interface StockSuggestion {
  code: string
  name: string
}

// 配置相关类型
export interface AppConfig {
  apiBase: string
  defaultCode: string
  wrN: number
}

// 页面类型
export type PageType = 'day' | 'day-local' | 'min'

// 分钟图相关类型
export interface MinChartConfig {
  date: string
  recentDays: number
}

// 信号分析相关类型
export interface StockSignalInfo {
  code: string
  name: string
  buy_signals: number
  sell_signals: number
  total_signals: number
  data_rows: number
}

export interface SignalAnalysisResponse {
  start_date: string
  end_date: string
  min_signals: number
  total_stocks_analyzed: number
  matching_stocks: number
  stocks: StockSignalInfo[]
}

export interface SignalAnalysisConfig {
  startDate: string
  endDate: string
  minSignals: number
}

// 资金流向相关类型
export interface MoneyFlowData {
  code: string
  trade_date: string
  close_price: number
  change_pct: number
  main_net_inflow_amount: number
  main_net_inflow_ratio: number
  super_large_net_inflow_amount: number
  super_large_net_inflow_ratio: number
  large_net_inflow_amount: number
  large_net_inflow_ratio: number
  medium_net_inflow_amount: number
  medium_net_inflow_ratio: number
  small_net_inflow_amount: number
  small_net_inflow_ratio: number
}

export interface MoneyFlowResponse {
  code: string
  name: string
  total_records: number
  data: MoneyFlowData[]
}

export interface MoneyFlowStatsResponse {
  total_records: number
  date_range: {
    min_date: string | null
    max_date: string | null
  }
  stocks_with_data: number
  latest_update: string | null
}

export interface MoneyFlowTopItem {
  code: string
  name: string
  trade_date: string
  close_price: number
  change_pct: number
  main_net_inflow_amount: number
  main_net_inflow_ratio: number
}

export interface MoneyFlowTopResponse {
  date: string
  total_stocks: number
  top_inflow: MoneyFlowTopItem[]
  top_outflow: MoneyFlowTopItem[]
}

export interface MoneyFlowAnalysisResponse {
  code: string
  name: string
  analysis_days: number
  total_records: number
  data: Array<MoneyFlowData & {
    net_inflow_3d: number
    net_inflow_5d: number
    net_inflow_10d: number
    net_inflow_20d: number
  }>
}