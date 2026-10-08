/**
 * 从思考过程和函数调用构建知识图谱数据（实时更新）
 * @param {string} reasoningContent - AI 的思考过程文本
 * @param {Array} toolCalls - 函数调用列表
 * @param {Array} functionCalls - 实时函数调用状态列表
 * @param {string} userQuestion - 用户的问题
 * @returns {Object} 知识图谱数据 { nodes: [], links: [] }
 */
export function buildKnowledgeGraphFromReasoning(reasoningContent, toolCalls = [], functionCalls = [], userQuestion = '') {
  const nodes = []
  const links = []
  const nodeIdMap = new Map() // 用于去重和快速查找

  // 1. 添加主节点（用户问题）
  const mainNodeId = 'main'
  if (userQuestion) {
    nodes.push({
      id: mainNodeId,
      label: userQuestion.length > 30 ? userQuestion.substring(0, 30) + '...' : userQuestion,
      status: 'pending',
      type: 'start'
    })
    nodeIdMap.set(mainNodeId, true)
  }

  // 2. 从实时函数调用状态中提取节点（优先使用实时状态）
  const functionCallMap = new Map()
  functionCalls.forEach(fc => {
    functionCallMap.set(fc.id, fc)
  })

  // 3. 合并 toolCalls 和 functionCalls，优先使用 functionCalls 中的实时状态
  const allCalls = []
  
  // 先处理 toolCalls（如果存在）
  toolCalls.forEach((toolCall, index) => {
    const callId = toolCall.id || `tool_${index}`
    const funcName = toolCall.function?.name || toolCall.name || `function_${index}`
    const funcArgs = toolCall.function?.arguments || toolCall.arguments || {}
    
    // 检查是否有对应的实时状态
    const realtimeCall = functionCallMap.get(callId)
    
    allCalls.push({
      id: callId,
      name: funcName,
      arguments: funcArgs,
      status: realtimeCall?.status || 'pending', // 使用实时状态
      error: realtimeCall?.error || null
    })
  })

  // 如果没有 toolCalls，使用 functionCalls
  if (allCalls.length === 0) {
    functionCalls.forEach((fc, index) => {
      allCalls.push({
        id: fc.id || `func_${index}`,
        name: fc.name || `function_${index}`,
        arguments: fc.arguments || {},
        status: fc.status || 'running',
        error: fc.error || null
      })
    })
  }

  // 4. 为每个函数调用创建节点
  allCalls.forEach((call, index) => {
    const funcName = call.name
    const funcArgs = call.arguments
    const callStatus = call.status
    
    // 解析函数参数，提取关键信息
    let label = funcName
    try {
      const args = typeof funcArgs === 'string' ? JSON.parse(funcArgs) : funcArgs
      
      // 根据函数名和参数生成节点标签
      if (funcName.includes('search') || funcName.includes('查询') || funcName.includes('搜索')) {
        const keyword = args.keyword || args.stock_name || args.name || '股票搜索'
        label = `搜索: ${keyword}`
      } else if (funcName.includes('kline') || funcName.includes('K线') || funcName.includes('k_line')) {
        const code = args.stock_code || args.code || '股票'
        label = `${code} K线数据`
      } else if (funcName.includes('finance') || funcName.includes('财务')) {
        const code = args.stock_code || args.code || '股票'
        label = `${code} 财务数据`
      } else if (funcName.includes('fund') || funcName.includes('资金')) {
        const code = args.stock_code || args.code || '股票'
        label = `${code} 资金流向`
      } else if (funcName.includes('announcement') || funcName.includes('公告')) {
        const code = args.stock_code || args.code || '股票'
        label = `${code} 公告信息`
      } else {
        const keyParams = Object.keys(args).slice(0, 2).map(k => args[k]).filter(v => v).join(', ')
        label = keyParams ? `${funcName}(${keyParams})` : funcName
      }
    } catch (e) {
      label = funcName
    }

    const nodeId = call.id || `func_${index}_${funcName}`
    
    // 根据状态确定节点状态
    let nodeStatus = 'pending'
    if (callStatus === 'completed' && !call.error) {
      nodeStatus = 'clear' // 完成且无错误 -> 结论明确
    } else if (callStatus === 'running') {
      nodeStatus = 'pending' // 执行中 -> 结论待完善
    } else if (call.error || callStatus === 'error') {
      nodeStatus = 'missing' // 错误 -> 信息缺失
    }

    nodes.push({
      id: nodeId,
      label: label.length > 40 ? label.substring(0, 40) + '...' : label,
      status: nodeStatus,
      type: 'search'
    })
    nodeIdMap.set(nodeId, true)

    // 连接到主节点
    if (userQuestion) {
      links.push({
        source: mainNodeId,
        target: nodeId,
        label: callStatus === 'running' ? '执行中' : '已调用'
      })
    }
  })

  // 5. 如果没有节点，创建一个默认的
  if (nodes.length === 0) {
    nodes.push({
      id: 'thinking',
      label: '正在思考...',
      status: 'pending',
      type: 'start'
    })
  }

  return {
    nodes,
    links
  }
}

