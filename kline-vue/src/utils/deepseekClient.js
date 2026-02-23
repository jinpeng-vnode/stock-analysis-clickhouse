/**
 * DeepSeek API 客户端
 * 用于调用 DeepSeek API 进行对话和函数调用
 */
import axios from 'axios'
import { getFunctionDefinitions, executeFunction } from './deepseekApiWrapper'

// DeepSeek API 配置
const DEEPSEEK_BASE_URL = 'https://api.deepseek.com/v1'
const DEEPSEEK_MODEL = 'deepseek-chat' // 支持函数调用的模型

// API Key（从环境变量或配置中获取，建议使用环境变量）
let DEEPSEEK_API_KEY = import.meta.env.VITE_DEEPSEEK_API_KEY || 'sk-c35de7fafa0444039a570de87402fe2c'

/**
 * 设置 API Key
 */
export function setApiKey(apiKey) {
  DEEPSEEK_API_KEY = apiKey
}

/**
 * 获取 API Key
 */
export function getApiKey() {
  return DEEPSEEK_API_KEY
}

/**
 * 调用 DeepSeek API
 * @param {Array} messages - 消息列表
 * @param {Array} tools - 工具（函数）定义列表
 * @param {boolean} stream - 是否使用流式输出
 * @param {Function} onChunk - 流式输出的回调函数
 */
export async function callDeepSeekAPI(messages, tools = [], stream = false, onChunk = null) {
  const url = `${DEEPSEEK_BASE_URL}/chat/completions`

  const requestData = {
    model: DEEPSEEK_MODEL,
    messages: messages,
    tools: tools.length > 0 ? tools : undefined,
    tool_choice: tools.length > 0 ? 'auto' : undefined,
    stream: stream,
    temperature: 0.7
  }

  const headers = {
    'Content-Type': 'application/json',
    'Authorization': `Bearer ${DEEPSEEK_API_KEY}`
  }

  if (stream) {
    // 流式输出
    return await callDeepSeekStream(url, requestData, headers, onChunk)
  } else {
    // 非流式输出
    const response = await axios.post(url, requestData, { headers })
    return response.data
  }
}

/**
 * 流式调用 DeepSeek API
 */
async function callDeepSeekStream(url, requestData, headers, onChunk) {
  return new Promise((resolve, reject) => {
    // 使用 fetch 进行流式请求
    fetch(url, {
      method: 'POST',
      headers: headers,
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
              if (line.startsWith('data: ')) {
                const data = line.slice(6)
                if (data === '[DONE]') {
                  resolve(fullResponse)
                  return
                }

                try {
                  const json = JSON.parse(data)
                  const delta = json.choices?.[0]?.delta

                  if (delta) {
                    // 处理内容
                    if (delta.content) {
                      fullResponse.content += delta.content
                      if (onChunk) {
                        onChunk({ type: 'content', content: delta.content })
                      }
                    }

                    // 处理思考过程
                    if (delta.reasoning_content) {
                      fullResponse.reasoning_content += delta.reasoning_content
                      if (onChunk) {
                        onChunk({ type: 'reasoning', content: delta.reasoning_content })
                      }
                    }

                    // 处理工具调用
                    if (delta.tool_calls) {
                      for (const toolCallDelta of delta.tool_calls) {
                        const idx = toolCallDelta.index || 0
                        if (!fullResponse.tool_calls[idx]) {
                          fullResponse.tool_calls[idx] = {
                            id: toolCallDelta.id || '',
                            type: 'function',
                            function: {
                              name: '',
                              arguments: ''
                            }
                          }
                        }

                        if (toolCallDelta.function) {
                          if (toolCallDelta.function.name) {
                            fullResponse.tool_calls[idx].function.name = toolCallDelta.function.name
                          }
                          if (toolCallDelta.function.arguments) {
                            fullResponse.tool_calls[idx].function.arguments += toolCallDelta.function.arguments
                          }
                        }
                      }
                    }
                  }
                } catch (e) {
                  console.error('解析流式数据失败:', e)
                }
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
 * 将函数定义转换为 DeepSeek 工具格式
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
 * 与 DeepSeek 对话，支持函数调用
 * @param {Array} messages - 消息历史
 * @param {boolean} stream - 是否使用流式输出
 * @param {Function} onChunk - 流式输出回调
 * @param {Function} onFunctionCall - 函数调用回调
 * @param {boolean} enableFunctionCall - 是否启用函数调用（默认true）
 */
export async function chatWithDeepSeek(messages, stream = false, onChunk = null, onFunctionCall = null, enableFunctionCall = true) {
  const maxIterations = 10 // 最大迭代次数
  let iteration = 0

  // 只有在启用函数调用时才获取函数定义
  let tools = []
  if (enableFunctionCall) {
    const functions = await getFunctionDefinitions()
    tools = convertFunctionsToTools(functions)
    console.log('deepseek函数列表', tools)
  }

  // 创建一个新的消息数组副本，避免修改原数组
  let currentMessages = [...messages]

  while (iteration < maxIterations) {
    iteration++

    try {
      // 调用 DeepSeek API
      let response
      if (stream) {
        response = await callDeepSeekAPI(currentMessages, tools, true, onChunk)
      } else {
        const apiResponse = await callDeepSeekAPI(currentMessages, tools, false)
        response = {
          content: apiResponse.choices?.[0]?.message?.content || '',
          tool_calls: apiResponse.choices?.[0]?.message?.tool_calls || [],
          reasoning_content: apiResponse.choices?.[0]?.message?.reasoning_content || ''
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
            id: tc.id,
            type: tc.type,
            function: {
              name: tc.function.name,
              arguments: tc.function.arguments
            }
          }))
        })

        // 执行每个函数调用
        for (const toolCall of toolCalls) {
          const functionName = toolCall.function.name
          let functionArgs = {}

          try {
            functionArgs = JSON.parse(toolCall.function.arguments)
          } catch (e) {
            console.error('解析函数参数失败:', e)
          }

          // 回调通知函数调用开始
          if (onFunctionCall) {
            onFunctionCall({
              type: 'start',
              name: functionName,
              arguments: functionArgs,
              id: toolCall.id
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
              id: toolCall.id
            })
          }

          // 添加函数执行结果到消息历史
          currentMessages.push({
            role: 'tool',
            tool_call_id: toolCall.id,
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
      console.error('DeepSeek API 调用失败:', error)
      throw error
    }
  }

  throw new Error('达到最大迭代次数，可能存在问题')
}

export default {
  callDeepSeekAPI,
  chatWithDeepSeek,
  setApiKey,
  getApiKey
}
