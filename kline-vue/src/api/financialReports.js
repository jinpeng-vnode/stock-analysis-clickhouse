/**
 * 财报表相关 API 接口统一管理
 * 从 @/utils/api 导入 axios 实例，基于请求路径生成函数名
 */
import api from '@/utils/api'

// 获取指定股票的财报表列表（支持分页、日期范围筛选）
export const getStockFinancialReports = (code, params = {}) => 
  api.get(`/financial-reports/${code}`, { params })

// 查询财报表列表（支持多股票、多条件筛选）
export const listFinancialReports = (params = {}) => 
  api.get('/financial-reports', { params })

// 创建单条财报表
export const createFinancialReport = (payload) => 
  api.post('/financial-reports', payload)

// 批量创建财报表
export const batchCreateFinancialReports = (payload) => 
  api.post('/financial-reports/batch', payload)

