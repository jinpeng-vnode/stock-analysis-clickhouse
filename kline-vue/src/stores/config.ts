import { defineStore } from 'pinia'
import type { AppConfig } from '@/types'

export const useConfigStore = defineStore('config', {
  state: (): AppConfig => ({
    apiBase: 'http://127.0.0.1:9010',
    defaultCode: '000001',
    wrN: 14
  }),
  
  getters: {
    getApiBase: (state) => state.apiBase,
    getDefaultCode: (state) => state.defaultCode,
    getWrN: (state) => state.wrN
  },
  
  actions: {
    setApiBase(apiBase: string) {
      this.apiBase = apiBase
    },
    
    setDefaultCode(code: string) {
      this.defaultCode = code
    },
    
    setWrN(wrN: number) {
      this.wrN = wrN
    },
    
    reset() {
      this.apiBase = 'http://127.0.0.1:9010'
      this.defaultCode = '000001'
      this.wrN = 14
    }
  }
})
