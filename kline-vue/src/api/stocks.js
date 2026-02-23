/**
 * 股票相关 API 接口统一管理
 * 从 @/utils/api 导入 axios 实例，基于请求路径生成函数名
 */
import api from '@/utils/api'

// 统计信息相关接口
export const getStats = () => api.get('/stats')
export const getPartitions = () => api.get('/stats/partitions')
export const getPerformance = () => api.get('/stats/performance')
export const optimizeTables = () => api.post('/stats/optimize')

// 股票基础接口
export const getStocks = (params = {}) => api.get('/stocks', { params })
export const searchStocks = (keyword, params = {}) => api.get('/stocks/search', { 
  params: { keyword, ...params } 
})

// 资金流向相关接口
export const getMoneyFlowStats = () => api.get('/money-flow/stats')
export const getStockMoneyFlow = (code, params = {}) => api.get(`/money-flow/${code}`, { params })
export const getBatchMoneyFlow = (codes, params = {}) => api.get('/money-flow/batch', { 
  params: { codes, ...params } 
})
export const getTopMoneyFlow = (params = {}) => api.get('/money-flow/top', { params })
export const getMoneyFlowAnalysis = (code, params = {}) => api.get(`/money-flow/analysis/${code}`, { params })

// 股票数据相关接口
export const getStockDailyData = (code, params = {}) => api.get(`/stocks/${code}/daily`, { params })
export const getStockDailyLocalData = (code, params = {}) => api.get(`/stocks/${code}/daily-local`, { params })
export const getStockDayMinuteData = (code, date) => api.get(`/stocks/${code}/day/${date}`)

// 信号分析相关接口
export const getStockSignalsAnalysis = (params = {}) => api.get('/stocks/signals/analysis', { params })

// 回测查询相关接口
export const queryByJsonLogic = (payload) => api.post('/json-logic/query', payload)

// 规则命中相关接口
export const getRuleTags = (days = 3000) => api.get('/rule-hits/tags', { params: { days } })
export const getRuleHitStocks = (rule_name, days = 3000) =>
  api.get('/rule-hits/stocks', { params: { rule_name, days } })

// stock_info 管理相关接口
export const getStockInfoList = (params = {}) => api.get('/stock-info', { params })
export const getStockInfoDetail = (code) => api.get(`/stock-info/${code}`)
export const createStockInfo = (payload) => api.post('/stock-info', payload)
export const updateStockInfo = (code, payload) => api.put(`/stock-info/${code}`, payload)
export const deleteStockInfo = (code) => api.delete(`/stock-info/${code}`)
export const batchDeleteStockInfo = (codes) => api.post('/stock-info/batch-delete', { codes })