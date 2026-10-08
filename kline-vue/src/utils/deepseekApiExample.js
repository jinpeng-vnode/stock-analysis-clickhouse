/**
 * DeepSeek API 包装器使用示例
 * 展示如何在 DeepSeek 函数调用中使用此包装器
 */
import { getFunctionDefinitions, executeFunction, initialize } from './deepseekApiWrapper'

/**
 * 示例：获取所有可用的函数定义并发送给 DeepSeek
 */
export async function setupDeepSeekFunctions() {
  try {
    // 初始化包装器（预加载 API 文档）
    await initialize()

    // 获取所有函数定义
    const functions = await getFunctionDefinitions()

    console.log(`共找到 ${functions.length} 个 API 函数`)

    // 返回函数定义，可以直接用于 DeepSeek 的函数调用配置
    return functions
  } catch (error) {
    console.error('设置 DeepSeek 函数失败:', error)
    throw error
  }
}

/**
 * 示例：处理 DeepSeek 的函数调用请求
 * @param {string} functionName - 函数名称
 * @param {object} functionArguments - 函数参数
 */
export async function handleDeepSeekFunctionCall(functionName, functionArguments) {
  try {
    console.log(`调用函数: ${functionName}`, functionArguments)
    
    const result = await executeFunction(functionName, functionArguments)
    
    if (result.success) {
      return JSON.stringify(result.data, null, 2)
    } else {
      return `错误: ${JSON.stringify(result.error)}`
    }
  } catch (error) {
    console.error('处理函数调用失败:', error)
    return `错误: ${error.message}`
  }
}

/**
 * 示例：完整的 DeepSeek 集成示例
 * 假设你使用 DeepSeek API，可以这样配置：
 */
export async function exampleDeepSeekIntegration() {
  // 1. 获取函数定义
  const functions = await setupDeepSeekFunctions()

  // 2. 配置 DeepSeek 客户端（示例代码，实际使用时需要根据你的 DeepSeek SDK 调整）
  /*
  const deepseekClient = new DeepSeekClient({
    apiKey: 'your-api-key',
    functions: functions, // 传入函数定义
    functionCall: 'auto' // 或 'required'
  })

  // 3. 发送消息，DeepSeek 会自动调用函数
  const response = await deepseekClient.chat.completions.create({
    model: 'deepseek-chat',
    messages: [
      {
        role: 'user',
        content: '请查询股票代码为000001的股票信息'
      }
    ]
  })

  // 4. 检查是否有函数调用
  if (response.choices[0].message.function_call) {
    const functionCall = response.choices[0].message.function_call
    const functionResult = await handleDeepSeekFunctionCall(
      functionCall.name,
      JSON.parse(functionCall.arguments)
    )

    // 5. 将函数结果发送回 DeepSeek
    const finalResponse = await deepseekClient.chat.completions.create({
      model: 'deepseek-chat',
      messages: [
        {
          role: 'user',
          content: '请查询股票代码为000001的股票信息'
        },
        {
          role: 'assistant',
          content: null,
          function_call: functionCall
        },
        {
          role: 'function',
          name: functionCall.name,
          content: functionResult
        }
      ]
    })

    return finalResponse
  }
  */

  return functions
}

/**
 * Vue 组合式函数示例
 * 在 Vue 组件中使用
 * 注意：需要从 vue 导入 ref
 */
/*
import { ref } from 'vue'

export function useDeepSeekApi() {
  const functions = ref([])
  const loading = ref(false)
  const error = ref(null)

  const loadFunctions = async () => {
    loading.value = true
    error.value = null
    try {
      functions.value = await setupDeepSeekFunctions()
    } catch (err) {
      error.value = err.message
    } finally {
      loading.value = false
    }
  }

  const callFunction = async (functionName, args) => {
    try {
      return await handleDeepSeekFunctionCall(functionName, args)
    } catch (err) {
      error.value = err.message
      throw err
    }
  }

  return {
    functions,
    loading,
    error,
    loadFunctions,
    callFunction
  }
}
*/

export default {
  setupDeepSeekFunctions,
  handleDeepSeekFunctionCall,
  exampleDeepSeekIntegration,
  useDeepSeekApi
}
