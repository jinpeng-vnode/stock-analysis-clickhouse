/**
 * DeepSeek API 包装器 Vue 组合式函数
 * 在 Vue 组件中使用此函数来集成 DeepSeek 函数调用功能
 */
import { ref } from 'vue'
import { 
  getFunctionDefinitions, 
  executeFunction, 
  initialize,
  clearCache 
} from '@/utils/deepseekApiWrapper'

/**
 * DeepSeek API 组合式函数
 */
export function useDeepSeekApi() {
  // 状态
  const functions = ref([])
  const loading = ref(false)
  const error = ref(null)
  const initialized = ref(false)

  /**
   * 加载函数定义
   */
  const loadFunctions = async () => {
    loading.value = true
    error.value = null
    try {
      functions.value = await getFunctionDefinitions()
      initialized.value = true
      return functions.value
    } catch (err) {
      error.value = err.message
      console.error('加载函数定义失败:', err)
      throw err
    } finally {
      loading.value = false
    }
  }

  /**
   * 初始化包装器（预加载）
   */
  const init = async () => {
    try {
      await initialize()
      await loadFunctions()
    } catch (err) {
      error.value = err.message
      throw err
    }
  }

  /**
   * 执行函数调用
   * @param {string} functionName - 函数名称
   * @param {object} args - 函数参数
   */
  const callFunction = async (functionName, args = {}) => {
    try {
      const result = await executeFunction(functionName, args)
      if (result.success) {
        return result.data
      } else {
        throw new Error(JSON.stringify(result.error))
      }
    } catch (err) {
      error.value = err.message
      console.error('执行函数调用失败:', err)
      throw err
    }
  }

  /**
   * 清除缓存并重新加载
   */
  const reload = async () => {
    clearCache()
    initialized.value = false
    await loadFunctions()
  }

  return {
    // 状态
    functions,
    loading,
    error,
    initialized,
    // 方法
    loadFunctions,
    init,
    callFunction,
    reload
  }
}

export default useDeepSeekApi
