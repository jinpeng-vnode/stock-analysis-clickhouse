/**
 * 规则命中 API 接口
 */
import api from '@/utils/api'

export const getRuleTags = (days = 3000) => api.get('/rule-hits/tags', { params: { days } })

export const getRuleHitStocks = (rule_name, days = 3000) =>
  api.get('/rule-hits/stocks', { params: { rule_name, days } })


