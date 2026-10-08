/**
 * 多阶段Agent（带反思机制）
 * 实现：规划 → 执行（带反思） → 汇总 的三层架构
 * 支持切换不同的 AI 后端（DeepSeek、Ollama 等）
 */
import { chatWithAI, AIProvider } from './aiClient'
import { executeFunction as executeApiFunction, getFunctionDefinitions } from './deepseekApiWrapper'

/**
 * 本地函数注册表
 * 格式：{ functionName: { handler: Function, description: string } }
 */
const localFunctions = {}

/**
 * 注册本地函数
 * @param {string} name - 函数名称
 * @param {Function} handler - 函数处理器
 * @param {string} description - 函数描述（可选）
 */
export function registerLocalFunction(name, handler, description = '') {
  if (typeof handler !== 'function') {
    throw new Error(`注册函数失败: ${name} 的处理器必须是函数`)
  }
  localFunctions[name] = {
    handler,
    description: description || `本地函数: ${name}`
  }
  console.log(`✅ [函数注册] 已注册本地函数: ${name}`)
}

/**
 * 注销本地函数
 * @param {string} name - 函数名称
 */
export function unregisterLocalFunction(name) {
  if (localFunctions[name]) {
    delete localFunctions[name]
    console.log(`🗑️ [函数注销] 已注销本地函数: ${name}`)
  }
}

/**
 * 获取所有已注册的本地函数列表
 * @returns {Array} 函数列表
 */
export function getLocalFunctions() {
  return Object.keys(localFunctions).map(name => ({
    name,
    description: localFunctions[name].description
  }))
}

/**
 * 执行函数（优先使用本地函数，否则调用后端API）
 * @param {string} functionName - 函数名称
 * @param {object} args - 函数参数
 * @returns {Promise<object>} 执行结果
 */
async function executeFunction(functionName, args = {}) {
  // 优先查找本地函数
  if (localFunctions[functionName]) {
    console.log(`🔧 [本地函数] 执行本地函数: ${functionName}`)
    try {
      const result = await localFunctions[functionName].handler(args)
      // 统一返回格式
      if (result && typeof result === 'object' && 'success' in result) {
        return result
      } else {
        return {
          success: true,
          data: result
        }
      }
    } catch (error) {
      console.error(`❌ [本地函数] 执行失败: ${functionName}`, error)
      return {
        success: false,
        error: error.message || String(error)
      }
    }
  }
  
  // 如果本地函数不存在，调用后端API
  console.log(`🌐 [API函数] 调用后端API: ${functionName}`)
  return await executeApiFunction(functionName, args)
}

/**
 * 初始化默认的本地函数（包括简单对话处理函数）
 */
function initializeDefaultLocalFunctions() {
  // 注册简单对话处理函数
  if (!localFunctions['chat']) {
    registerLocalFunction('chat', async (args) => {
      const { message, userQuestion } = args
      const question = message || userQuestion || ''
      
      // 使用AI直接回答问题
      const messages = [
        {
          role: 'system',
          content: '你是一个专业的AI助手。请用简洁、自然、友好的方式直接回答用户的问题。回答要准确、有用，不要过于冗长。'
        },
        {
          role: 'user',
          content: question
        }
      ]
      
      const result = await chatWithAI(messages, false, null, null, false)
      return {
        response: result.content,
        reasoning_content: result.reasoning_content
      }
    }, '处理所有不需要多阶段调用、不需要查询数据或执行操作的问题，直接返回AI的回答')
  }
}

/**
 * 任务状态枚举
 */
export const TaskStatus = {
  PENDING: 'pending',      // 待执行
  RUNNING: 'running',       // 执行中
  SUCCESS: 'success',       // 成功
  FAILED: 'failed',         // 失败
  RETRYING: 'retrying',     // 重试中
  SKIPPED: 'skipped'        // 已跳过
}

/**
 * 反思结果类型
 */
export const ReflectionAction = {
  RETRY: 'retry',           // 重试（可调整参数）
  SKIP: 'skip',             // 跳过此任务
  REPLACE: 'replace',       // 替换为其他方法
  CONTINUE: 'continue'      // 继续（部分失败但可接受）
}

/**
 * 阶段1: 规划层 - 任务拆分
 * @param {string} userQuestion - 用户问题
 * @param {Function} onProgress - 进度回调
 * @param {string} aiProvider - AI 后端类型（可选，默认使用全局设置）
 */
export async function planningStage(userQuestion, onProgress = null, aiProvider = null) {
  console.log('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━')
  console.log('📋 [规划阶段] 开始规划任务')
  console.log('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━')
  console.log('用户问题:', userQuestion)
  console.log('AI后端:', aiProvider || '默认')
  
    // 获取所有可用的函数列表
  let availableFunctions = []
  
  // 获取本地函数
  const localFunctions = getLocalFunctions()
  availableFunctions.push(...localFunctions.map(f => ({
    name: f.name,
    description: f.description,
    type: 'local'
  })))
  
  // 获取API函数
  try {
    const apiFunctions = await getFunctionDefinitions()
    availableFunctions.push(...apiFunctions.map(f => ({
      name: f.name,
      description: f.description,
      parameters: f.parameters,
      type: 'api'
    })))
    console.log(`📚 [规划阶段] 获取到 ${apiFunctions.length} 个API函数`)
    
    // 打印函数的详细信息
    console.log('\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━')
    console.log('📋 [规划阶段] API函数详细信息:')
    console.log('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━')
    apiFunctions.forEach((func, index) => {
      console.log(`\n${index + 1}. 函数名: ${func.name}`)
      console.log(`   描述: ${func.description || '无描述'}`)
      if (func.parameters) {
        console.log(`   参数类型: ${func.parameters.type || 'object'}`)
        if (func.parameters.properties) {
          console.log(`   参数列表:`)
          Object.keys(func.parameters.properties).forEach(paramName => {
            const param = func.parameters.properties[paramName]
            const isRequired = func.parameters.required && func.parameters.required.includes(paramName)
            console.log(`     - ${paramName}${isRequired ? ' (必需)' : ' (可选)'}`)
            console.log(`       类型: ${param.type || 'unknown'}`)
            if (param.description) {
              console.log(`       说明: ${param.description}`)
            }
            if (param.enum) {
              console.log(`       可选值: ${JSON.stringify(param.enum)}`)
            }
            if (param.default !== undefined) {
              console.log(`       默认值: ${JSON.stringify(param.default)}`)
            }
          })
        }
        if (func.parameters.required && func.parameters.required.length > 0) {
          console.log(`   必需参数: ${func.parameters.required.join(', ')}`)
        }
      } else {
        console.log(`   参数: 无`)
      }
    })
    console.log('\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n')
  } catch (error) {
    console.warn('⚠️ [规划阶段] 获取API函数列表失败:', error.message)
  }
  
  console.log(`📚 [规划阶段] 共 ${availableFunctions.length} 个可用函数`)
  
  // 构建函数列表说明（简化版，只显示函数名和简短描述）
  const functionsListText = availableFunctions.length > 0
    ? `\n\n系统中可用的函数列表（请从以下函数中选择）：\n${availableFunctions.map((f, index) => {
        let funcDesc = `${index + 1}. "${f.name}" - ${f.description || '无描述'}`
        if (f.parameters && f.parameters.properties) {
          const paramNames = Object.keys(f.parameters.properties)
          if (paramNames.length > 0) {
            funcDesc += ` [参数: ${paramNames.join(', ')}]`
          }
        }
        return funcDesc
      }).join('\n')}`
    : '\n\n注意：当前只有 chat 本地函数可用。'
  
  const plannerPrompt = `你是一个任务规划专家。你的任务是分析用户问题并返回JSON格式的任务列表。

⚠️ 重要：你必须只返回JSON数组，不要有任何其他文字说明、问候语或解释！

你的工作流程：
1. 分析用户问题的类型
2. 选择合适的函数来完成任务
3. 返回JSON格式的任务列表

函数选择原则：
- "chat" 函数：用于处理所有不需要多阶段调用、不需要查询数据或执行操作的问题。这类问题只需要直接回答即可，包括但不限于：
  * 问候、闲聊、简单对话
  * 不需要数据支撑的一般性问题回答
  * 不需要调用其他函数的咨询类问题
  * 任何可以用一句话或简单对话回答的问题
  调用方式：function_name 设为 "chat"，function_args 为 {"message": "用户的完整问题内容"}
  
- 数据查询/操作函数：只有当问题需要获取数据、执行操作、需要多步骤处理时，才调用相应的数据查询或操作函数（如 get_stock_info 等）

要求：
1. 仔细分析用户的问题，理解其真实意图
2. 判断问题是否需要多阶段处理：
   - 如果问题只需要简单回答，不需要查询数据、不需要执行操作、不需要多步骤处理，则调用 "chat" 函数，参数为 {"message": "用户的完整问题"}
   - 如果问题需要获取数据、执行操作、需要多步骤处理，则调用相应的数据查询或操作函数，并拆分为多个子任务
3. 对于需要多步骤处理的问题，将问题拆分为多个独立的、可执行的子任务
4. 子任务之间可以有依赖关系（通过 depends_on 字段标识）
5. 每个子任务需要指定：描述、优先级、所需的函数名称、函数参数、预期结果
6. function_name 必须是系统中可用的函数名（如 "chat"、"get_stock_info" 等）
7. function_args 是传递给函数的参数字典
8. 如果某个任务的参数需要依赖前一个任务的结果，在 function_args 中用特殊标记（如"从task-1获取"），并在 depends_on 中指定依赖
9. ⚠️ 必须返回有效的JSON数组格式
10. ⚠️ 只返回JSON，不要有任何前缀、后缀、解释或其他文字

返回格式示例（直接复制格式，替换内容）：

示例1：需要调用函数的任务
[
  {
    "id": "task-1",
    "description": "获取股票数据",
    "priority": 1,
    "function_name": "get_stock_info",
    "function_args": {"code": "000001"},
    "depends_on": [],
    "expected_result": "返回股票基本信息"
  }
]

示例2：不需要多阶段调用的问题（使用 chat 函数）
[
  {
    "id": "task-1",
    "description": "直接回答用户问题",
    "priority": 1,
    "function_name": "chat",
    "function_args": {"message": "你好，今天天气怎么样？"},
    "depends_on": [],
    "expected_result": "返回友好的回答"
  }
]

示例3：需要数据查询的复杂问题
[
  {
    "id": "task-1",
    "description": "获取股票数据",
    "priority": 1,
    "function_name": "get_stock_info",
    "function_args": {"code": "000001"},
    "depends_on": [],
    "expected_result": "返回股票基本信息"
  }
]${functionsListText}`

  const messages = [
    {
      role: 'system',
      content: plannerPrompt
    },
    {
      role: 'user',
      content: userQuestion
    }
  ]

  if (onProgress) {
    onProgress({ 
      stage: 'planning', 
      status: 'running', 
      message: '正在规划任务...',
      requestMessages: messages,
      requestDetails: {
        prompt: plannerPrompt,
        userQuestion: userQuestion
      }
    })
  }

  // 规划阶段不需要函数调用，只需要AI返回JSON格式的任务列表
  // 注意：不需要在这里切换AI后端，应该由主函数统一管理
  console.log('📤 [规划阶段] 发送请求给AI...')
  console.log('请求消息:', JSON.stringify(messages, null, 2))
  
  const result = await chatWithAI(messages, false, null, null, false)
  
  console.log('📥 [规划阶段] 收到AI响应')
  console.log('AI响应内容:', result.content)
  
  if (onProgress) {
    onProgress({ 
      stage: 'planning', 
      status: 'running', 
      message: '收到规划结果，正在解析...',
      response: result
    })
  }
  
  // 解析任务列表
  let tasks = []
  try {
    // 清理响应内容，移除可能的markdown代码块标记
    let content = result.content.trim()
    
    // 移除可能的markdown代码块标记
    content = content.replace(/^```json\s*/i, '').replace(/^```\s*/i, '').replace(/\s*```$/i, '')
    
    // 尝试提取JSON数组
    let jsonMatch = content.match(/\[[\s\S]*\]/)
    if (jsonMatch) {
      tasks = JSON.parse(jsonMatch[0])
    } else {
      // 尝试提取JSON对象（单个任务）
      jsonMatch = content.match(/\{[\s\S]*\}/)
      if (jsonMatch) {
        tasks = [JSON.parse(jsonMatch[0])]
      } else {
        // 直接解析整个内容
        tasks = JSON.parse(content)
      }
    }
    
    // 确保tasks是数组
    if (!Array.isArray(tasks)) {
      tasks = [tasks]
    }
    
    console.log('✅ [规划阶段] 成功解析任务列表')
    console.log('任务数量:', tasks.length)
    console.log('任务列表:', JSON.stringify(tasks, null, 2))
  } catch (e) {
    console.error('❌ [规划阶段] 解析任务列表失败:', e)
    console.error('原始内容:', result.content)
    console.log('⚠️ [规划阶段] AI返回的不是JSON格式，自动创建chat任务')
    
    // 如果AI返回的不是JSON（比如直接回答了问题），说明这是简单对话，创建chat任务
    tasks = [{
      id: 'task-1',
      description: userQuestion,
      priority: 1,
      function_name: 'chat', // 默认使用 chat 函数
      function_args: { message: userQuestion },
      depends_on: [],
      expected_result: '回答用户问题'
    }]
  }

  // 为每个任务添加状态
  tasks = tasks.map(task => ({
    ...task,
    status: TaskStatus.PENDING,
    retryCount: 0,
    maxRetries: 3,
    result: null,
    error: null,
    reflection: null
  }))

  if (onProgress) {
    onProgress({ 
      stage: 'planning', 
      status: 'success', 
      tasks,
      parsedTasks: tasks
    })
  }

  console.log('✅ [规划阶段] 规划完成')
  console.log('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n')

  return tasks
}

/**
 * 反思层 - 分析错误并决定下一步
 * @param {Object} task - 任务对象
 * @param {Error} error - 错误对象
 * @param {Array} executionHistory - 执行历史
 * @param {Function} onProgress - 进度回调
 * @param {string} aiProvider - AI 后端类型（可选，默认使用全局设置）
 */
export async function reflectionStage(task, error, executionHistory = [], onProgress = null, aiProvider = null) {
  console.log('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━')
  console.log('🤔 [反思阶段] 开始反思分析')
  console.log('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━')
  console.log('任务ID:', task.id)
  console.log('任务描述:', task.description)
  console.log('函数名称:', task.function_name)
  console.log('函数参数:', JSON.stringify(task.function_args, null, 2))
  console.log('重试次数:', task.retryCount, '/', task.maxRetries)
  
  const errorMessage = error?.message || error?.error || JSON.stringify(error)
  const errorStack = error?.stack || ''
  
  console.log('错误信息:', errorMessage)
  
  const reflectionPrompt = `你是一个问题诊断专家。当任务执行失败时，你需要分析原因并决定下一步行动。

当前任务：
- ID: ${task.id}
- 描述: ${task.description}
- 函数: ${task.function_name || '未指定'}
- 参数: ${JSON.stringify(task.function_args, null, 2)}
- 重试次数: ${task.retryCount}/${task.maxRetries}

错误信息：
${errorMessage}
${errorStack ? `\n错误堆栈:\n${errorStack}` : ''}

执行历史（最近3次）：
${JSON.stringify(executionHistory.slice(-3), null, 2)}

重要判断规则：
1. 如果错误是"未找到函数"且任务是简单的日常对话（如问候、闲聊），应该选择 "skip"，因为这类问题不需要调用函数，可以在汇总阶段直接回答
2. 如果错误是"未找到函数"且已经重试多次（重试次数 >= 2），应该选择 "skip" 而不是 "replace"，避免无限重试
3. 如果错误是临时性的（网络问题、超时等），可以选择 "retry"
4. 如果错误是参数问题，可以选择 "retry" 并调整参数
5. 如果函数不存在但任务需要获取数据，可以考虑 "replace" 或 "skip"

请分析：
1. 错误原因是什么？（网络问题、参数错误、数据不存在、权限问题、API限制、函数不存在等）
2. 任务类型是什么？（数据获取、日常对话、信息查询等）
3. 是否可以重试？如果可以，应该调整哪些参数？
4. 如果无法重试，是否有替代方案？
5. 这个任务对整体目标是否关键？

返回JSON格式（只返回JSON，不要有其他文字）：
{
  "analysis": "错误原因分析",
  "action": "retry|skip|replace|continue",
  "reason": "选择该行动的原因",
  "adjusted_args": {}, // 如果action是retry，提供调整后的参数（如果没有需要调整的，保持原参数）
  "alternative_method": "", // 如果action是replace，提供替代方法（必须是系统中存在的函数名）
  "is_critical": true // 该任务是否关键
}`

  const messages = [
    {
      role: 'system',
      content: reflectionPrompt
    },
    {
      role: 'user',
      content: `请分析任务失败的原因并给出处理建议。`
    }
  ]

  if (onProgress) {
    onProgress({ 
      stage: 'reflection', 
      status: 'running', 
      taskId: task.id,
      message: '正在分析错误原因...',
      requestMessages: messages,
      requestDetails: {
        task: {
          id: task.id,
          description: task.description,
          function_name: task.function_name,
          function_args: task.function_args,
          retryCount: task.retryCount,
          maxRetries: task.maxRetries
        },
        error: errorMessage,
        executionHistory: executionHistory.slice(-3)
      }
    })
  }

  // 反思阶段不需要函数调用，只需要AI返回JSON格式的反思结果
  // 注意：不需要在这里切换AI后端，应该由主函数统一管理
  console.log('📤 [反思阶段] 发送反思请求给AI...')
  const result = await chatWithAI(messages, false, null, null, false)
  
  console.log('📥 [反思阶段] 收到AI响应')
  console.log('AI响应内容:', result.content)
  
  if (onProgress) {
    onProgress({ 
      stage: 'reflection', 
      status: 'running', 
      taskId: task.id,
      message: '收到反思结果，正在解析...',
      response: result
    })
  }
  
  let reflection = null
  try {
    const jsonMatch = result.content.match(/\{[\s\S]*\}/)
    if (jsonMatch) {
      reflection = JSON.parse(jsonMatch[0])
    } else {
      reflection = JSON.parse(result.content)
    }
    console.log('✅ [反思阶段] 成功解析反思结果')
    console.log('反思决策:', JSON.stringify(reflection, null, 2))
  } catch (e) {
    console.error('❌ [反思阶段] 解析反思结果失败:', e)
    console.error('原始内容:', result.content)
    // 如果解析失败，使用默认策略
    reflection = {
      analysis: '无法解析反思结果',
      action: task.retryCount < task.maxRetries ? ReflectionAction.RETRY : ReflectionAction.SKIP,
      reason: '解析失败，使用默认策略',
      adjusted_args: task.function_args,
      is_critical: false
    }
  }

  if (onProgress) {
    onProgress({ 
      stage: 'reflection', 
      status: 'success', 
      taskId: task.id,
      reflection 
    })
  }

  console.log('✅ [反思阶段] 反思完成')
  console.log('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n')

  return reflection
}

/**
 * 验证执行结果
 */
function validateResult(task, result) {
  // 基础验证：检查是否有错误
  if (result && result.success === false) {
    return { valid: false, reason: result.error || '执行返回失败状态' }
  }

  // 检查是否为空结果
  if (!result || (typeof result === 'object' && Object.keys(result).length === 0)) {
    return { valid: false, reason: '返回结果为空' }
  }

  // 检查数据格式是否符合预期
  if (task.expected_result) {
    // 这里可以根据 expected_result 进行更详细的验证
    // 例如：检查是否包含特定字段
  }

  return { valid: true }
}

/**
 * 解析依赖任务的参数
 */
function resolveDependentArgs(task, executionResults) {
  const args = { ...task.function_args }
  
  // 遍历参数，查找需要从依赖任务获取的值
  for (const [key, value] of Object.entries(args)) {
    if (typeof value === 'string' && value.includes('从task-')) {
      // 例如: "从task-1获取code" 或 "task-1的code字段"
      const taskIdMatch = value.match(/task-(\d+)/)
      if (taskIdMatch) {
        const depTaskId = `task-${taskIdMatch[1]}`
        const depResult = executionResults.find(r => r.task.id === depTaskId)
        
        if (depResult && depResult.result) {
          // 尝试从结果中提取需要的值
          if (depResult.result.data) {
            // 尝试提取code字段
            if (depResult.result.data.code) {
              args[key] = depResult.result.data.code
            } else if (depResult.result.data.length > 0 && depResult.result.data[0].code) {
              // 如果是数组，取第一个
              args[key] = depResult.result.data[0].code
            } else {
              args[key] = depResult.result.data
            }
          } else if (depResult.result.code) {
            args[key] = depResult.result.code
          }
        }
      }
    }
  }
  
  return args
}

/**
 * 按依赖关系排序任务
 */
function sortTasksByDependency(tasks) {
  const sorted = []
  const visited = new Set()

  function visit(task) {
    if (visited.has(task.id)) return
    
    // 先访问依赖任务
    if (task.depends_on && task.depends_on.length > 0) {
      task.depends_on.forEach(depId => {
        const depTask = tasks.find(t => t.id === depId)
        if (depTask) visit(depTask)
      })
    }
    
    visited.add(task.id)
    sorted.push(task)
  }

  // 按优先级排序后访问
  const prioritySorted = [...tasks].sort((a, b) => (a.priority || 999) - (b.priority || 999))
  prioritySorted.forEach(visit)

  return sorted
}

/**
 * 执行单个任务的函数调用
 */
async function executeTaskFunction(task, onFunctionCall = null) {
  console.log(`  🔧 [执行函数] 任务ID: ${task.id}`)
  console.log(`  函数名称: ${task.function_name}`)
  console.log(`  函数参数:`, JSON.stringify(task.function_args, null, 2))
  
  // 如果 function_name 为 null 或空字符串，表示不需要调用函数
  // 这种情况下，直接返回成功结果，由汇总阶段处理
  if (!task.function_name || task.function_name === 'null') {
    console.log(`  ⏭️ [执行函数] 跳过函数调用（不需要调用函数）`)
    return {
      success: true,
      data: {
        message: '该任务不需要调用函数，将在汇总阶段处理',
        task_description: task.description,
        function_name: null
      }
    }
  }

  if (onFunctionCall) {
    onFunctionCall({
      type: 'start',
      name: task.function_name,
      arguments: task.function_args,
      id: `task-${task.id}`
    })
  }

  let result
  try {
    console.log(`  ⏳ [执行函数] 开始调用函数...`)
    result = await executeFunction(task.function_name, task.function_args)
    console.log(`  ✅ [执行函数] 函数调用成功`)
    console.log(`  返回结果:`, JSON.stringify(result, null, 2).substring(0, 500) + (JSON.stringify(result).length > 500 ? '...' : ''))
  } catch (error) {
    console.error(`  ❌ [执行函数] 函数调用失败:`, error.message)
    // 如果executeFunction抛出异常，包装成结果格式
    result = {
      success: false,
      error: error.message || String(error)
    }
  }

  if (onFunctionCall) {
    onFunctionCall({
      type: 'end',
      name: task.function_name,
      arguments: task.function_args,
      result: result,
      error: result.success === false ? result.error : null,
      id: `task-${task.id}`
    })
  }

  // 如果执行失败，抛出错误以便反思层处理
  if (result.success === false) {
    throw new Error(result.error || '函数执行失败')
  }

  return result
}

/**
 * 阶段2: 执行层 - 执行任务（带反思机制）
 * @param {Array} tasks - 任务列表
 * @param {Function} onProgress - 进度回调
 * @param {Function} onFunctionCall - 函数调用回调
 * @param {string} aiProvider - AI 后端类型（可选，默认使用全局设置）
 */
export async function executionStage(tasks, onProgress = null, onFunctionCall = null, aiProvider = null) {
  console.log('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━')
  console.log('⚙️ [执行阶段] 开始执行任务')
  console.log('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━')
  console.log('任务总数:', tasks.length)
  
  const executionResults = []
  const executionHistory = [] // 记录执行历史，用于反思

  // 按优先级和依赖关系排序任务
  const sortedTasks = sortTasksByDependency(tasks)
  console.log('排序后的任务列表:', sortedTasks.map(t => ({ id: t.id, description: t.description, priority: t.priority, depends_on: t.depends_on })))

  for (const task of sortedTasks) {
    console.log(`\n  📌 [执行任务] ${task.id}: ${task.description}`)
    // 检查依赖任务是否完成
    if (task.depends_on && task.depends_on.length > 0) {
      const allDepsCompleted = task.depends_on.every(depId => {
        const depTask = executionResults.find(r => r.task.id === depId)
        return depTask && depTask.task.status === TaskStatus.SUCCESS
      })

      if (!allDepsCompleted) {
        task.status = TaskStatus.SKIPPED
        task.error = '依赖任务未完成'
        executionResults.push({ task, result: null })
        continue
      }

      // 从依赖任务中获取参数值
      task.function_args = resolveDependentArgs(task, executionResults)
    }

    // 执行任务（带重试和反思）
    let executed = false
    let lastError = null

    while (!executed && task.retryCount <= task.maxRetries) {
      try {
        task.status = task.retryCount > 0 ? TaskStatus.RETRYING : TaskStatus.RUNNING
        console.log(`    尝试次数: ${task.retryCount + 1}/${task.maxRetries + 1}`)
        if (task.retryCount > 0) {
          console.log(`    🔄 正在重试...`)
        }

        if (onProgress) {
          onProgress({ 
            stage: 'execution', 
            status: 'running', 
            taskId: task.id, // 添加taskId用于区分不同任务
            task,
            attempt: task.retryCount + 1,
            executionDetails: {
              functionName: task.function_name,
              functionArgs: task.function_args,
              isRetry: task.retryCount > 0
            }
          })
        }

        // 执行函数调用
        const result = await executeTaskFunction(task, onFunctionCall)
        
        if (onProgress) {
          onProgress({ 
            stage: 'execution', 
            status: 'running', 
            taskId: task.id, // 添加taskId用于区分不同任务
            task,
            attempt: task.retryCount + 1,
            executionResult: result,
            executionDetails: {
              functionName: task.function_name,
              functionArgs: task.function_args,
              result: result
            }
          })
        }

        // 验证结果
        const validation = validateResult(task, result)
        
        if (validation.valid) {
          task.status = TaskStatus.SUCCESS
          task.result = result
          executed = true
          
          console.log(`    ✅ [执行任务] ${task.id} 执行成功`)
          
          executionHistory.push({
            taskId: task.id,
            attempt: task.retryCount + 1,
            success: true,
            result
          })

          if (onProgress) {
            onProgress({ 
              stage: 'execution', 
              status: 'success', 
              taskId: task.id, // 添加taskId
              task 
            })
          }
        } else {
          // 结果验证失败，触发反思
          console.log(`    ⚠️ [执行任务] ${task.id} 结果验证失败: ${validation.reason}`)
          lastError = new Error(validation.reason)
          task.retryCount++
          
          executionHistory.push({
            taskId: task.id,
            attempt: task.retryCount,
            success: false,
            error: validation.reason
          })
        }

      } catch (error) {
        console.error(`    ❌ [执行任务] ${task.id} 执行失败:`, error.message)
        lastError = error
        task.retryCount++
        task.error = error.message

        executionHistory.push({
          taskId: task.id,
          attempt: task.retryCount,
          success: false,
          error: error.message
        })

        // 如果还有重试机会，进行反思
        if (task.retryCount <= task.maxRetries) {
          console.log(`    🤔 [执行任务] ${task.id} 触发反思机制...`)
          const reflection = await reflectionStage(
            task, 
            error, 
            executionHistory.filter(h => h.taskId === task.id),
            onProgress,
            aiProvider
          )

          task.reflection = reflection

          // 根据反思结果决定下一步
          console.log(`    📋 [执行任务] ${task.id} 反思决策: ${reflection.action}`)
          if (reflection.action === ReflectionAction.RETRY) {
            // 使用调整后的参数重试
            if (reflection.adjusted_args && Object.keys(reflection.adjusted_args).length > 0) {
              console.log(`    🔄 [执行任务] ${task.id} 调整参数后重试`)
              task.function_args = { ...task.function_args, ...reflection.adjusted_args }
            }
            // 继续循环重试
          } else if (reflection.action === ReflectionAction.SKIP) {
            console.log(`    ⏭️ [执行任务] ${task.id} 跳过任务`)
            task.status = TaskStatus.SKIPPED
            executed = true // 标记为已处理，不再重试
          } else if (reflection.action === ReflectionAction.REPLACE) {
            // 替换为替代方法
            if (reflection.alternative_method && reflection.alternative_method.trim().length > 0) {
              // 检查替代方法是否是有效的函数名（不是描述性文本）
              const alternativeMethod = reflection.alternative_method.trim()
              // 如果替代方法看起来像函数名（不包含中文，没有长句子），才使用
              if (alternativeMethod.length < 50 && !alternativeMethod.includes('，') && !alternativeMethod.includes('。')) {
                console.log(`    🔄 [执行任务] ${task.id} 替换方法: ${alternativeMethod}`)
                task.function_name = alternativeMethod
                // 继续重试，使用新方法
              } else {
                console.log(`    ⚠️ [执行任务] ${task.id} 替代方法无效，跳过任务`)
                task.status = TaskStatus.SKIPPED
                executed = true
              }
            } else {
              console.log(`    ⚠️ [执行任务] ${task.id} 没有有效的替代方法，跳过任务`)
              task.status = TaskStatus.SKIPPED
              executed = true
            }
          } else if (reflection.action === ReflectionAction.CONTINUE) {
            // 部分失败但可接受，标记为成功但记录警告
            console.log(`    ⚠️ [执行任务] ${task.id} 部分成功，继续执行`)
            task.status = TaskStatus.SUCCESS
            task.result = { partial: true, warning: reflection.reason, data: null }
            executed = true
          }
        } else {
          // 超过最大重试次数
          console.error(`    ❌ [执行任务] ${task.id} 超过最大重试次数，任务失败`)
          task.status = TaskStatus.FAILED
          executed = true
        }
      }
    }

    // 如果最终失败，进行最终反思
    if (task.status === TaskStatus.FAILED && task.reflection === null) {
      const finalReflection = await reflectionStage(
        task,
        lastError || new Error('执行失败'),
        executionHistory.filter(h => h.taskId === task.id),
        onProgress,
        aiProvider
      )
      task.reflection = finalReflection
    }

    executionResults.push({ task, result: task.result })
    console.log(`  📊 [执行任务] ${task.id} 最终状态: ${task.status}`)
  }

  console.log('\n✅ [执行阶段] 所有任务执行完成')
  console.log('执行结果统计:', {
    总数: executionResults.length,
    成功: executionResults.filter(r => r.task.status === TaskStatus.SUCCESS).length,
    失败: executionResults.filter(r => r.task.status === TaskStatus.FAILED).length,
    跳过: executionResults.filter(r => r.task.status === TaskStatus.SKIPPED).length
  })
  console.log('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n')

  return executionResults
}

/**
 * 阶段3: 汇总层 - 综合分析
 * @param {string} userQuestion - 用户问题
 * @param {Array} executionResults - 执行结果列表
 * @param {Function} onProgress - 进度回调
 * @param {string} aiProvider - AI 后端类型（可选，默认使用全局设置）
 */
export async function synthesisStage(userQuestion, executionResults, onProgress = null, aiProvider = null) {
  console.log('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━')
  console.log('📊 [汇总阶段] 开始综合分析')
  console.log('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━')
  console.log('原始问题:', userQuestion)
  console.log('执行结果数量:', executionResults.length)
  
  const synthesisPrompt = `你是一个专业的数据分析专家。请基于所有子任务的执行结果，进行综合分析并给出最终结论。

原始问题：${userQuestion}

执行结果汇总：
${JSON.stringify(executionResults.map(r => ({
  taskId: r.task.id,
  description: r.task.description,
  status: r.task.status,
  result: r.result ? (r.result.data ? r.result.data : r.result) : null,
  error: r.task.error,
  reflection: r.task.reflection ? {
    analysis: r.task.reflection.analysis,
    action: r.task.reflection.action,
    reason: r.task.reflection.reason
  } : null
})), null, 2)}

请根据用户的问题和执行结果：
1. 总结所有成功的任务及其结果
2. 分析失败的任务及其影响（如果有）
3. 基于可用数据给出专业的分析和建议，直接回答用户的问题
4. 如果有关键任务失败，说明限制和可能的影响
5. 用中文回答，格式清晰易读，确保回答与用户的问题相关`

  const messages = [
    {
      role: 'system',
      content: synthesisPrompt
    },
    {
      role: 'user',
      content: '请基于以上执行结果给出最终分析。'
    }
  ]

  if (onProgress) {
    onProgress({ 
      stage: 'synthesis', 
      status: 'running', 
      message: '正在综合分析...',
      requestMessages: messages,
      requestDetails: {
        userQuestion: userQuestion,
        executionResults: executionResults.map(r => ({
          taskId: r.task.id,
          description: r.task.description,
          status: r.task.status,
          result: r.result ? (r.result.data ? r.result.data : r.result) : null,
          error: r.task.error
        }))
      }
    })
  }

  // 汇总阶段不需要函数调用，只需要AI基于执行结果进行分析
  // 注意：不需要在这里切换AI后端，应该由主函数统一管理
  console.log('📤 [汇总阶段] 发送汇总请求给AI...')
  console.log('执行结果摘要:', JSON.stringify(executionResults.map(r => ({
    taskId: r.task.id,
    description: r.task.description,
    status: r.task.status
  })), null, 2))
  
  const result = await chatWithAI(messages, false, null, null, false)
  
  console.log('📥 [汇总阶段] 收到AI响应')
  console.log('汇总结果长度:', result.content?.length || 0, '字符')
  
  if (onProgress) {
    onProgress({ 
      stage: 'synthesis', 
      status: 'running', 
      message: '收到汇总结果',
      response: result
    })
  }

  if (onProgress) {
    onProgress({ stage: 'synthesis', status: 'success' })
  }
  
  console.log('✅ [汇总阶段] 汇总完成')
  console.log('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n')

  return {
    content: result.content,
    reasoning_content: result.reasoning_content,
    executionSummary: {
      total: executionResults.length,
      success: executionResults.filter(r => r.task.status === TaskStatus.SUCCESS).length,
      failed: executionResults.filter(r => r.task.status === TaskStatus.FAILED).length,
      skipped: executionResults.filter(r => r.task.status === TaskStatus.SKIPPED).length
    },
    executionResults
  }
}

/**
 * 主函数：多阶段Agent（带反思机制）
 * @param {string} userQuestion - 用户问题
 * @param {Object} options - 配置选项
 * @param {Function} options.onProgress - 进度回调
 * @param {Function} options.onFunctionCall - 函数调用回调
 * @param {number} options.maxRetries - 最大重试次数
 * @param {string} options.aiProvider - AI 后端类型（'deepseek' 或 'ollama'），可选
 */
export async function multiStageAgentWithReflection(
  userQuestion,
  options = {}
) {
  console.log('\n')
  console.log('╔═══════════════════════════════════════════════════════╗')
  console.log('║       多阶段Agent开始执行                             ║')
  console.log('╚═══════════════════════════════════════════════════════╝')
  console.log('用户问题:', userQuestion)
  
  const {
    onProgress = null,
    onFunctionCall = null,
    maxRetries = 3,
    aiProvider = null // 支持在调用时指定 AI 后端
  } = options

  console.log('配置选项:', { maxRetries, aiProvider: aiProvider || '默认' })

  // 初始化默认的本地函数（包括简单对话处理函数）
  initializeDefaultLocalFunctions()

  // 如果指定了 AI 后端，直接切换并使用（不恢复）
  if (aiProvider) {
    const { setAIProvider, AIProvider: AIType } = await import('./aiClient')
    
    // 验证并设置 AI 后端
    const targetProvider = aiProvider === 'deepseek' || aiProvider === AIType.DEEPSEEK 
      ? AIType.DEEPSEEK 
      : aiProvider === 'ollama' || aiProvider === AIType.OLLAMA 
        ? AIType.OLLAMA 
        : null
    
    if (targetProvider) {
      setAIProvider(targetProvider)
      console.log(`使用 ${targetProvider === AIType.DEEPSEEK ? 'DeepSeek' : 'Ollama'} 后端`)
    } else {
      console.warn(`不支持的 AI 后端: ${aiProvider}，使用当前默认后端`)
    }
  }

  try {
    // 阶段1: 规划
    const tasks = await planningStage(userQuestion, onProgress, aiProvider)

    // 检查是否所有任务都是调用 chat 函数
    const allTasksAreChat = tasks.length > 0 && tasks.every(task => 
      task.function_name === 'chat' || task.function_name === null
    )

    // 如果所有任务都是 chat 函数，直接执行并返回，跳过执行和汇总阶段
    if (allTasksAreChat && tasks.length === 1) {
      console.log('💬 [快速路径] 检测到 chat 函数，直接执行并返回...')
      
      const task = tasks[0]
      const chatArgs = task.function_args?.message || task.function_args?.userQuestion || userQuestion
      
      if (onProgress) {
        onProgress({ 
          stage: 'chat', 
          status: 'running', 
          message: '正在处理...',
          task
        })
      }
      
      // 直接调用 chat 函数
      const chatResult = await executeFunction('chat', { 
        message: chatArgs,
        userQuestion: chatArgs 
      })
      
      if (onProgress) {
        onProgress({ 
          stage: 'chat', 
          status: 'success', 
          message: '处理完成'
        })
      }
      
      console.log('✅ [快速路径] chat 函数执行完成')
      
      // 返回格式与完整流程保持一致
      return {
        content: chatResult.data?.response || chatResult.data?.content || chatResult.data || '收到',
        reasoning_content: chatResult.data?.reasoning_content,
        executionSummary: {
          total: 1,
          success: chatResult.success ? 1 : 0,
          failed: chatResult.success ? 0 : 1,
          skipped: 0
        },
        executionResults: [{
          task: {
            ...task,
            status: chatResult.success ? TaskStatus.SUCCESS : TaskStatus.FAILED,
            result: chatResult
          },
          result: chatResult
        }],
        isDirectChat: true
      }
    }

    // 设置最大重试次数
    tasks.forEach(task => {
      task.maxRetries = maxRetries
    })

    // 阶段2: 执行（带反思）
    const executionResults = await executionStage(tasks, onProgress, onFunctionCall, aiProvider)

    // 阶段3: 汇总
    const finalResult = await synthesisStage(userQuestion, executionResults, onProgress, aiProvider)

    console.log('\n')
    console.log('╔═══════════════════════════════════════════════════════╗')
    console.log('║       多阶段Agent执行完成                             ║')
    console.log('╚═══════════════════════════════════════════════════════╝')
    console.log('最终结果摘要:', {
      内容长度: finalResult.content?.length || 0,
      执行摘要: finalResult.executionSummary
    })

    return finalResult

  } catch (error) {
    console.error('\n')
    console.error('╔═══════════════════════════════════════════════════════╗')
    console.error('║       多阶段Agent执行失败                             ║')
    console.error('╚═══════════════════════════════════════════════════════╝')
    console.error('错误信息:', error.message)
    console.error('错误堆栈:', error.stack)
    throw error
  }
}

/**
 * ============================================================================
 * 示例：如何注册本地函数
 * ============================================================================
 * 
 * // 示例1: 注册一个简单的计算函数
 * registerLocalFunction('calculate', async (args) => {
 *   const { a, b, operation } = args
 *   let result
 *   switch (operation) {
 *     case 'add': result = a + b; break
 *     case 'subtract': result = a - b; break
 *     case 'multiply': result = a * b; break
 *     case 'divide': result = b !== 0 ? a / b : null; break
 *     default: throw new Error(`不支持的操作: ${operation}`)
 *   }
 *   return { result }
 * }, '执行数学计算（加、减、乘、除）')
 * 
 * // 示例2: 注册一个获取当前时间的函数
 * registerLocalFunction('get_current_time', async (args) => {
 *   const { format = 'iso' } = args
 *   const now = new Date()
 *   let result
 *   switch (format) {
 *     case 'iso': result = now.toISOString(); break
 *     case 'local': result = now.toLocaleString('zh-CN'); break
 *     case 'timestamp': result = now.getTime(); break
 *     default: result = now.toISOString()
 *   }
 *   return { time: result, timestamp: now.getTime() }
 * }, '获取当前时间')
 * 
 * // 示例3: 注册一个数据转换函数
 * registerLocalFunction('format_data', async (args) => {
 *   const { data, format } = args
 *   if (format === 'json') {
 *     return { formatted: JSON.stringify(data, null, 2) }
 *   } else if (format === 'array') {
 *     return { formatted: Array.isArray(data) ? data : [data] }
 *   }
 *   return { formatted: data }
 * }, '格式化数据')
 * 
 * // 使用示例：
 * // const result = await multiStageAgentWithReflection('帮我计算 10 + 20', {})
 * 
 * ============================================================================
 */

