/**
 * Ollama API 客户端
 * 用于调用本地 Ollama API 进行对话和函数调用
 */
import axios from 'axios'
import { getFunctionDefinitions, executeFunction } from './deepseekApiWrapper'

// Ollama API 配置（直接写死）
let OLLAMA_BASE_URL = 'http://localhost:11434'
let OLLAMA_MODEL = 'deepseek-r1:8b'

/**
 * 设置 Ollama 配置
 */
export function setOllamaConfig(baseUrl, model) {
  if (baseUrl) OLLAMA_BASE_URL = baseUrl
  if (model) OLLAMA_MODEL = model
}

/**
 * 获取 Ollama 配置
 */
export function getOllamaConfig() {
  return {
    baseUrl: OLLAMA_BASE_URL,
    model: OLLAMA_MODEL
  }
}

/**
 * 调用 Ollama API
 * @param {Array} messages - 消息列表
 * @param {Array} tools - 工具（函数）定义列表
 * @param {boolean} stream - 是否使用流式输出
 * @param {Function} onChunk - 流式输出的回调函数
 */
export async function callOllamaAPI(messages, tools = [], stream = false, onChunk = null) {
  const url = `${OLLAMA_BASE_URL}/api/chat`

  const requestData = {
    model: OLLAMA_MODEL,
    messages: messages,
    tools: tools.length > 0 ? tools : undefined,
    stream: stream,
    options: {
      temperature: 0.7
    }
  }

  if (stream) {
    // 流式输出
    return await callOllamaStream(url, requestData, onChunk)
  } else {
    // 非流式输出
    const response = await axios.post(url, requestData)
    return response.data
  }
}

/**
 * 流式调用 Ollama API
 */
async function callOllamaStream(url, requestData, onChunk) {
  return new Promise((resolve, reject) => {
    // 使用 fetch 进行流式请求
    fetch(url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(requestData)
    })
      .then(response => {
        if (!response.ok) {
          throw new Error(`HTTP error! status: ${response.status}`)
        }

        const reader = response.body.getReader()
        const decoder = new TextDecoder()
        let buffer = ''
        let fullResponse = {
          content: '',
          tool_calls: [],
          reasoning_content: ''
        }

        function readStream() {
          reader.read().then(({ done, value }) => {
            if (done) {
              resolve(fullResponse)
              return
            }

            buffer += decoder.decode(value, { stream: true })
            const lines = buffer.split('\n')
            buffer = lines.pop() || ''

            for (const line of lines) {
              if (!line.trim()) continue

              try {
                const json = JSON.parse(line)
                
                // 处理内容
                if (json.message?.content) {
                  fullResponse.content += json.message.content
                  if (onChunk) {
                    onChunk({ type: 'content', content: json.message.content })
                  }
                }

                // 处理工具调用（Ollama 可能在 message 或 tool_calls 字段中）
                if (json.message?.tool_calls) {
                  fullResponse.tool_calls = json.message.tool_calls
                }

                // 处理推理内容（如果 Ollama 支持）
                if (json.message?.reasoning_content) {
                  fullResponse.reasoning_content += json.message.reasoning_content
                  if (onChunk) {
                    onChunk({ type: 'reasoning', content: json.message.reasoning_content })
                  }
                }

                // 如果是最后一条消息，获取完整的工具调用
                if (json.done && json.message) {
                  if (json.message.tool_calls) {
                    fullResponse.tool_calls = json.message.tool_calls
                  }
                }
              } catch (e) {
                // 忽略 JSON 解析错误（可能是部分数据）
                console.warn('解析流式数据失败:', e, line)
              }
            }

            readStream()
          }).catch(reject)
        }

        readStream()
      })
      .catch(reject)
  })
}

/**
 * 将函数定义转换为 Ollama 工具格式
 */
function convertFunctionsToTools(functions) {
  return functions.map(func => ({
    type: 'function',
    function: {
      name: func.name,
      description: func.description,
      parameters: func.parameters
    }
  }))
}

/**
 * 与 Ollama 对话，支持函数调用
 * @param {Array} messages - 消息历史
 * @param {boolean} stream - 是否使用流式输出
 * @param {Function} onChunk - 流式输出回调
 * @param {Function} onFunctionCall - 函数调用回调
 * @param {boolean} enableFunctionCall - 是否启用函数调用（默认true）
 */
export async function chatWithOllama(messages, stream = false, onChunk = null, onFunctionCall = null, enableFunctionCall = true) {
  const maxIterations = 10 // 最大迭代次数
  let iteration = 0

  // 只有在启用函数调用时才获取函数定义
  let tools = []
  if (enableFunctionCall) {
    const functions = await getFunctionDefinitions()
    tools = convertFunctionsToTools(functions)
    console.log('ollama函数列表', tools)
  }

  // 创建一个新的消息数组副本，避免修改原数组
  let currentMessages = [...messages]

  while (iteration < maxIterations) {
    iteration++

    try {
      // 调用 Ollama API
      let response
      if (stream) {
        response = await callOllamaAPI(currentMessages, tools, true, onChunk)
      } else {
        const apiResponse = await callOllamaAPI(currentMessages, tools, false)
        // Ollama 返回格式: { message: { content, tool_calls }, done: true }
        response = {
          content: apiResponse.message?.content || '',
          tool_calls: apiResponse.message?.tool_calls || [],
          reasoning_content: apiResponse.message?.reasoning_content || ''
        }
      }

      // 检查是否有函数调用
      if (response.tool_calls && response.tool_calls.length > 0) {
        // 处理函数调用
        const toolCalls = response.tool_calls

        // 添加助手消息（包含函数调用）
        currentMessages.push({
          role: 'assistant',
          content: response.content || null,
          tool_calls: toolCalls.map(tc => ({
            id: tc.id || `call_${Date.now()}_${Math.random()}`,
            type: tc.type || 'function',
            function: {
              name: tc.function?.name || tc.name,
              arguments: typeof tc.function?.arguments === 'string' 
                ? tc.function.arguments 
                : JSON.stringify(tc.function?.arguments || {})
            }
          }))
        })

        // 执行每个函数调用
        for (const toolCall of toolCalls) {
          const functionName = toolCall.function?.name || toolCall.name
          let functionArgs = {}

          try {
            const argsStr = typeof toolCall.function?.arguments === 'string'
              ? toolCall.function.arguments
              : JSON.stringify(toolCall.function?.arguments || {})
            functionArgs = JSON.parse(argsStr)
          } catch (e) {
            console.error('解析函数参数失败:', e)
          }

          // 回调通知函数调用开始
          if (onFunctionCall) {
            onFunctionCall({
              type: 'start',
              name: functionName,
              arguments: functionArgs,
              id: toolCall.id || `call_${Date.now()}_${Math.random()}`
            })
          }

          // 执行函数
          let functionResult
          let functionError = null
          try {
            const result = await executeFunction(functionName, functionArgs)
            functionResult = JSON.stringify(result, null, 2)
          } catch (error) {
            functionError = error
            functionResult = JSON.stringify({
              error: error.message,
              stack: error.stack
            }, null, 2)
          }

          // 回调通知函数调用完成
          if (onFunctionCall) {
            onFunctionCall({
              type: 'end',
              name: functionName,
              arguments: functionArgs,
              result: functionResult,
              error: functionError,
              id: toolCall.id || `call_${Date.now()}_${Math.random()}`
            })
          }

          // 添加函数执行结果到消息历史
          // Ollama 使用 tool 角色
          currentMessages.push({
            role: 'tool',
            tool_call_id: toolCall.id || `call_${Date.now()}_${Math.random()}`,
            content: functionResult
          })
        }

        // 继续循环，让 AI 基于函数结果生成回复
        continue
      }

      // 没有函数调用，返回最终回复
      return {
        content: response.content || '',
        reasoning_content: response.reasoning_content || '',
        tool_calls: response.tool_calls || [],
        iteration: iteration
      }

    } catch (error) {
      console.error('Ollama API 调用失败:', error)
      throw error
    }
  }

  throw new Error('达到最大迭代次数，可能存在问题')
}

export default {
  callOllamaAPI,
  chatWithOllama,
  setOllamaConfig,
  getOllamaConfig
}

