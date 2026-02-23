# DeepSeek API 包装器使用说明

这个包装器可以自动读取 FastAPI 的 OpenAPI 文档，并将其转换为 DeepSeek 函数调用格式。

## 功能特性

- ✅ 自动读取 FastAPI OpenAPI 文档（`/openapi.json`）
- ✅ 自动转换为 DeepSeek 函数调用格式
- ✅ 支持所有 HTTP 方法（GET、POST、PUT、DELETE、PATCH）
- ✅ 自动处理路径参数、查询参数和请求体
- ✅ 缓存机制，避免重复请求
- ✅ Vue 组合式函数支持

## 快速开始

### 1. 基础使用

```javascript
import { getFunctionDefinitions, executeFunction } from '@/utils/deepseekApiWrapper'

// 获取所有函数定义（用于配置 DeepSeek）
const functions = await getFunctionDefinitions()
console.log(functions)
// 输出: [{ name: 'get_stocks', description: '...', parameters: {...} }, ...]

// 执行函数调用
const result = await executeFunction('get_stocks', { code: '000001' })
console.log(result)
```

### 2. 在 Vue 组件中使用

```vue
<template>
  <div>
    <a-button @click="loadFunctions">加载函数</a-button>
    <a-button @click="testCall">测试调用</a-button>
    <div v-if="loading">加载中...</div>
    <div v-if="error">错误: {{ error }}</div>
    <div>已加载 {{ functions.length }} 个函数</div>
  </div>
</template>

<script setup>
import { useDeepSeekApi } from '@/composables/useDeepSeekApi'

const { functions, loading, error, loadFunctions, callFunction } = useDeepSeekApi()

const testCall = async () => {
  try {
    const result = await callFunction('get_stocks', { code: '000001' })
    console.log('调用结果:', result)
  } catch (err) {
    console.error('调用失败:', err)
  }
}

// 组件挂载时加载函数
onMounted(() => {
  loadFunctions()
})
</script>
```

### 3. 与 DeepSeek API 集成

```javascript
import { getFunctionDefinitions, executeFunction } from '@/utils/deepseekApiWrapper'

// 1. 获取函数定义
const functions = await getFunctionDefinitions()

// 2. 配置 DeepSeek 客户端（示例）
const deepseekClient = {
  chat: {
    completions: {
      create: async (options) => {
        // 发送请求到 DeepSeek API
        // ...
      }
    }
  }
}

// 3. 发送消息给 DeepSeek
const response = await deepseekClient.chat.completions.create({
  model: 'deepseek-chat',
  messages: [
    {
      role: 'user',
      content: '请查询股票代码为000001的股票信息'
    }
  ],
  functions: functions, // 传入函数定义
  function_call: 'auto'
})

// 4. 处理函数调用
if (response.choices[0].message.function_call) {
  const functionCall = response.choices[0].message.function_call
  const functionResult = await executeFunction(
    functionCall.name,
    JSON.parse(functionCall.arguments)
  )

  // 5. 将结果发送回 DeepSeek
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
        content: JSON.stringify(functionResult)
      }
    ]
  })
}
```

## API 说明

### `getFunctionDefinitions()`

获取所有可用的函数定义，返回格式符合 DeepSeek 函数调用规范。

**返回:**
```javascript
[
  {
    name: 'get_stocks',              // 函数名称
    description: '获取股票列表',      // 函数描述
    parameters: {                     // 参数定义（JSON Schema）
      type: 'object',
      properties: {
        code: {
          type: 'string',
          description: '股票代码'
        }
      },
      required: ['code']
    }
  },
  // ...
]
```

### `executeFunction(functionName, args)`

执行函数调用。

**参数:**
- `functionName` (string): 函数名称
- `args` (object): 函数参数

**返回:**
```javascript
{
  success: true,
  data: { ... }  // API 返回的数据
}
```

### `clearCache()`

清除缓存，强制重新加载 OpenAPI 文档。

### `initialize()`

初始化包装器，预加载 API 文档。

## 函数命名规则

函数名称由以下规则生成：

1. 优先使用 OpenAPI 中的 `operationId`
2. 如果没有 `operationId`，则使用 `{method}_{path}` 格式
   - 例如：`GET /api/stocks` → `get_api_stocks`
   - 例如：`POST /api/stocks` → `post_api_stocks`

## 注意事项

1. **API 地址配置**: 确保 `VITE_API_BASE_URL` 环境变量正确配置，或默认为 `http://localhost:9010`
2. **CORS**: 确保后端已配置 CORS，允许前端访问
3. **缓存**: 函数定义会被缓存，如果 API 有更新，需要调用 `clearCache()` 重新加载
4. **错误处理**: 所有函数调用都应该使用 try-catch 处理错误

## 示例：完整的 DeepSeek 集成

```javascript
import { getFunctionDefinitions, executeFunction } from '@/utils/deepseekApiWrapper'

class DeepSeekApiHandler {
  constructor() {
    this.functions = null
  }

  async init() {
    // 初始化时加载函数定义
    this.functions = await getFunctionDefinitions()
    return this.functions
  }

  async handleMessage(userMessage) {
    // 1. 发送消息给 DeepSeek
    const response = await this.callDeepSeek({
      messages: [{ role: 'user', content: userMessage }],
      functions: this.functions
    })

    // 2. 检查是否有函数调用
    const message = response.choices[0].message
    if (message.function_call) {
      // 3. 执行函数调用
      const functionResult = await executeFunction(
        message.function_call.name,
        JSON.parse(message.function_call.arguments)
      )

      // 4. 将结果发送回 DeepSeek
      const finalResponse = await this.callDeepSeek({
        messages: [
          { role: 'user', content: userMessage },
          { role: 'assistant', content: null, function_call: message.function_call },
          { role: 'function', name: message.function_call.name, content: JSON.stringify(functionResult) }
        ],
        functions: this.functions
      })

      return finalResponse.choices[0].message.content
    }

    return message.content
  }

  async callDeepSeek(options) {
    // 这里实现实际的 DeepSeek API 调用
    // 使用你选择的 HTTP 客户端（axios、fetch 等）
    const response = await fetch('https://api.deepseek.com/v1/chat/completions', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': 'Bearer YOUR_API_KEY'
      },
      body: JSON.stringify({
        model: 'deepseek-chat',
        ...options
      })
    })
    return await response.json()
  }
}

// 使用示例
const handler = new DeepSeekApiHandler()
await handler.init()

const result = await handler.handleMessage('请查询股票代码为000001的股票信息')
console.log(result)
```

## 故障排除

### 问题：无法获取 OpenAPI 文档

**解决方案:**
1. 确保后端服务正在运行（端口 9010）
2. 检查 `VITE_API_BASE_URL` 环境变量配置
3. 确认后端 `/openapi.json` 端点可访问

### 问题：函数调用失败

**解决方案:**
1. 检查函数名称是否正确
2. 检查参数格式是否符合 API 要求
3. 查看浏览器控制台的错误信息
4. 确认后端 API 正常工作

### 问题：函数定义未更新

**解决方案:**
调用 `clearCache()` 清除缓存，然后重新加载函数定义。

## 文件结构

```
src/
├── utils/
│   ├── deepseekApiWrapper.js      # 核心包装器
│   └── deepseekApiExample.js      # 使用示例
├── composables/
│   └── useDeepSeekApi.js          # Vue 组合式函数
└── ...
```
