/**
 * 公告相关 API 接口统一管理
 * 从 @/utils/api 导入 axios 实例，基于请求路径生成函数名
 */
import api from '@/utils/api'

// 获取指定股票的公告列表（支持分页、日期范围筛选）
export const getStockAnnouncements = (code, params = {}) => 
  api.get(`/announcements/${code}`, { params })

// 查询公告列表（支持多股票、多条件筛选）
export const listAnnouncements = (params = {}) => 
  api.get('/announcements', { params })

// 创建单条公告
export const createAnnouncement = (payload) => 
  api.post('/announcements', payload)

// 批量创建公告
export const batchCreateAnnouncements = (payload) => 
  api.post('/announcements/batch', payload)

