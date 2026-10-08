/**
 * AI 客户端抽象层
 * 统一不同 AI 后端的接口，支持切换 DeepSeek 和 Ollama
 */
import { chatWithDeepSeek } from './deepseekClient'
import { chatWithOllama } from './ollamaClient'

/**
 * AI 后端类型枚举
 */
export const AIProvider = {
  DEEPSEEK: 'deepseek',
  OLLAMA: 'ollama'
}

// 当前使用的 AI 后端（默认 DeepSeek）
let currentProvider = AIProvider.DEEPSEEK

/**
 * 设置 AI 后端
 * @param {string} provider - AI 后端类型 (AIProvider.DEEPSEEK 或 AIProvider.OLLAMA)
 */
export function setAIProvider(provider) {
  if (Object.values(AIProvider).includes(provider)) {
    currentProvider = provider
    console.log(`已切换到 AI 后端: ${provider}`)
  } else {
    console.warn(`不支持的 AI 后端: ${provider}，保持当前后端: ${currentProvider}`)
  }
}

/**
 * 获取当前 AI 后端
 * @returns {string} 当前使用的 AI 后端
 */
export function getAIProvider() {
  return currentProvider
}

/**
 * 统一的 AI 对话接口
 * @param {Array} messages - 消息历史
 * @param {boolean} stream - 是否使用流式输出
 * @param {Function} onChunk - 流式输出回调
 * @param {Function} onFunctionCall - 函数调用回调
 * @param {boolean} enableFunctionCall - 是否启用函数调用（默认false，规划/汇总阶段不需要）
 * @returns {Promise<Object>} AI 回复结果
 */
export async function chatWithAI(messages, stream = false, onChunk = null, onFunctionCall = null, enableFunctionCall = false) {
  switch (currentProvider) {
    case AIProvider.DEEPSEEK:
      return await chatWithDeepSeek(messages, stream, onChunk, enableFunctionCall ? onFunctionCall : null, enableFunctionCall)
    
    case AIProvider.OLLAMA:
      return await chatWithOllama(messages, stream, onChunk, enableFunctionCall ? onFunctionCall : null, enableFunctionCall)
    
    default:
      throw new Error(`不支持的 AI 后端: ${currentProvider}`)
  }
}

export default {
  AIProvider,
  setAIProvider,
  getAIProvider,
  chatWithAI
}

