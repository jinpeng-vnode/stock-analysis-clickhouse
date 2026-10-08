import { defineStore } from 'pinia'

export interface CandidateStock {
  code: string
  name: string
}

export const useCandidateListStore = defineStore('candidateList', {
  state: () => ({
    stocks: [] as CandidateStock[]
  }),

  getters: {
    stockCount: (state) => state.stocks.length,
    hasStock: (state) => (code: string) => state.stocks.some(stock => stock.code === code)
  },

  actions: {
    // 从localStorage加载候选列表
    loadFromStorage() {
      try {
        const stored = localStorage.getItem('stock_candidate_list')
        if (stored) {
          this.stocks = JSON.parse(stored)
        }
      } catch (error) {
        console.error('加载候选列表失败:', error)
        this.stocks = []
      }
    },

    // 保存到localStorage
    saveToStorage() {
      try {
        localStorage.setItem('stock_candidate_list', JSON.stringify(this.stocks))
      } catch (error) {
        console.error('保存候选列表失败:', error)
        throw error
      }
    },

    // 添加股票到候选列表（自动过滤重复项）
    addStock(stock: CandidateStock) {
      // 首次添加时自动加载存储数据
      if (this.stocks.length === 0) {
        this.loadFromStorage()
      }
      
      // 如果已存在，先移除
      if (this.hasStock(stock.code)) {
        this.removeStock(stock.code)
      }
      
      this.stocks.push(stock)
      this.saveToStorage()
    },

    // 从候选列表移除股票
    removeStock(code: string) {
      const index = this.stocks.findIndex(stock => stock.code === code)
      if (index > -1) {
        this.stocks.splice(index, 1)
        this.saveToStorage()
        return true
      }
      return false
    },

    // 清空候选列表
    clearAll() {
      this.stocks = []
      this.saveToStorage()
    }
  }
})
