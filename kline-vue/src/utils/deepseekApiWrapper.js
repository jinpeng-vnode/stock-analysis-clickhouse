/**
 * DeepSeek 函数调用 API 包装器
 * 自动读取 FastAPI OpenAPI 文档并转换为函数调用格式
 */
import axios from 'axios'

// API 基础地址
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:9010'

// 缓存 OpenAPI 文档
let openApiCache = null
let functionsCache = null

/**
 * 获取 OpenAPI 文档
 */
async function fetchOpenApiSpec() {
  if (openApiCache) {
    return openApiCache
  }

  try {
    const response = await axios.get(`${API_BASE_URL}/openapi.json`)
    openApiCache = response.data
    return openApiCache
  } catch (error) {
    console.error('获取 OpenAPI 文档失败:', error)
    throw new Error(`无法获取 API 文档: ${error.message}`)
  }
}

/**
 * 将 OpenAPI Schema 转换为 JSON Schema（函数调用格式）
 */
function convertOpenApiSchemaToJsonSchema(schema, definitions = {}) {
  if (!schema) {
    return { type: 'object' }
  }

  // 处理引用
  if (schema.$ref) {
    const refPath = schema.$ref.replace('#/components/schemas/', '')
    const refSchema = definitions[refPath]
    if (refSchema) {
      return convertOpenApiSchemaToJsonSchema(refSchema, definitions)
    }
  }

  // 处理 allOf
  if (schema.allOf) {
    const merged = { type: 'object', properties: {}, required: [] }
    schema.allOf.forEach(item => {
      const converted = convertOpenApiSchemaToJsonSchema(item, definitions)
      if (converted.properties) {
        Object.assign(merged.properties, converted.properties)
      }
      if (converted.required) {
        merged.required.push(...converted.required)
      }
    })
    return merged
  }

  // 处理基本类型
  const jsonSchema = {
    type: schema.type || 'object'
  }

  // 处理枚举
  if (schema.enum) {
    jsonSchema.enum = schema.enum
    return jsonSchema
  }

  // 处理对象类型
  if (schema.type === 'object' || schema.properties) {
    jsonSchema.properties = {}
    jsonSchema.required = schema.required || []

    if (schema.properties) {
      Object.keys(schema.properties).forEach(key => {
        jsonSchema.properties[key] = convertOpenApiSchemaToJsonSchema(
          schema.properties[key],
          definitions
        )
      })
    }
  }

  // 处理数组类型
  if (schema.type === 'array') {
    jsonSchema.items = convertOpenApiSchemaToJsonSchema(schema.items, definitions)
  }

  // 处理描述
  if (schema.description) {
    jsonSchema.description = schema.description
  }

  // 处理标题
  if (schema.title) {
    jsonSchema.title = schema.title
  }

  // 处理默认值
  if (schema.default !== undefined) {
    jsonSchema.default = schema.default
  }

  // 处理格式
  if (schema.format) {
    jsonSchema.format = schema.format
  }

  // 处理数值范围
  if (schema.minimum !== undefined) {
    jsonSchema.minimum = schema.minimum
  }
  if (schema.maximum !== undefined) {
    jsonSchema.maximum = schema.maximum
  }

  // 处理字符串长度
  if (schema.minLength !== undefined) {
    jsonSchema.minLength = schema.minLength
  }
  if (schema.maxLength !== undefined) {
    jsonSchema.maxLength = schema.maxLength
  }

  return jsonSchema
}

/**
 * 将 OpenAPI 路径参数转换为函数参数
 */
function convertParametersToProperties(parameters, definitions) {
  const properties = {}
  const required = []

  parameters.forEach(param => {
    const prop = {
      type: param.schema?.type || 'string',
      description: param.description || ''
    }

    // 处理枚举
    if (param.schema?.enum) {
      prop.enum = param.schema.enum
    }

    // 处理引用
    if (param.schema?.$ref) {
      const refPath = param.schema.$ref.replace('#/components/schemas/', '')
      const refSchema = definitions[refPath]
      if (refSchema) {
        Object.assign(prop, convertOpenApiSchemaToJsonSchema(refSchema, definitions))
      }
    }

    properties[param.name] = prop

    if (param.required) {
      required.push(param.name)
    }
  })

  return { properties, required }
}

/**
 * 将 OpenAPI 操作转换为函数定义
 */
function convertPathToFunctions(openApiSpec) {
  const functions = []
  const paths = openApiSpec.paths || {}
  const components = openApiSpec.components || {}
  const schemas = components.schemas || {}

  Object.keys(paths).forEach(path => {
    const pathItem = paths[path]
    
    // 跳过健康检查和根路径
    if (path === '/health' || path === '/') {
      return
    }

    // 跳过不允许的股票信号分析 API
    if (path === '/stocks/signals/analysis' || path === '/stocks/signals/stats') {
      return
    }

    Object.keys(pathItem).forEach(method => {
      if (!['get', 'post', 'put', 'delete', 'patch'].includes(method.toLowerCase())) {
        return
      }

      // 跳过创建和删除类的 API（POST 和 DELETE）
      const methodLower = method.toLowerCase()
      if (methodLower === 'post' || methodLower === 'delete') {
        return
      }

      const operation = pathItem[method]
      if (!operation) return

      // 生成函数名称（从 operationId 或路径和方法生成）
      // 优先使用 operationId，否则从路径生成更友好的名称
      let functionName = operation.operationId
      if (!functionName) {
        // 清理路径，移除前导斜杠和参数占位符
        const cleanPath = path
          .replace(/^\//, '')
          .replace(/\{([^}]+)\}/g, '$1') // 将 {id} 转换为 id
          .replace(/[^a-zA-Z0-9]/g, '_')
          .replace(/_+/g, '_')
          .replace(/^_+|_+$/g, '')
        functionName = `${method.toLowerCase()}_${cleanPath || 'root'}`
      }

      // 构建参数
      const parameters = operation.parameters || []
      const requestBody = operation.requestBody

      const paramProperties = convertParametersToProperties(parameters, schemas)
      let properties = { ...paramProperties.properties }
      let required = [...paramProperties.required]

  // 处理请求体
  if (requestBody && requestBody.content) {
    // 尝试多种 content-type
    const contentTypes = ['application/json', 'application/x-www-form-urlencoded', 'multipart/form-data']
    let content = null
    for (const contentType of contentTypes) {
      if (requestBody.content[contentType]) {
        content = requestBody.content[contentType]
        break
      }
    }
    
    if (content && content.schema) {
      const bodySchema = convertOpenApiSchemaToJsonSchema(content.schema, schemas)
      if (bodySchema.properties) {
        properties = { ...properties, ...bodySchema.properties }
        if (bodySchema.required) {
          required = [...new Set([...required, ...bodySchema.required])]
        }
      }
    }
  }

      // 生成函数定义
      const functionDef = {
        name: functionName,
        description: operation.summary || operation.description || `调用 ${method.toUpperCase()} ${path} 接口`,
        parameters: {
          type: 'object',
          properties,
          required: required.length > 0 ? required : undefined
        }
      }

      // 移除空的 required 字段
      if (!functionDef.parameters.required || functionDef.parameters.required.length === 0) {
        delete functionDef.parameters.required
      }

      functions.push(functionDef)
    })
  })

  return functions
}

/**
 * 获取所有函数定义（用于 DeepSeek 函数调用）
 */
export async function getFunctionDefinitions() {
  if (functionsCache) {
    return functionsCache
  }

  const openApiSpec = await fetchOpenApiSpec()
  functionsCache = convertPathToFunctions(openApiSpec)
  return functionsCache
}

/**
 * 执行函数调用
 * @param {string} functionName - 函数名称
 * @param {object} arguments - 函数参数
 */
export async function executeFunction(functionName, args = {}) {
  const openApiSpec = await fetchOpenApiSpec()
  const paths = openApiSpec.paths || {}

  // 查找对应的路径和方法
  let targetPath = null
  let targetMethod = null
  let targetOperation = null

  for (const path in paths) {
    const pathItem = paths[path]
    for (const method in pathItem) {
      if (!['get', 'post', 'put', 'delete', 'patch'].includes(method.toLowerCase())) {
        continue
      }

      const operation = pathItem[method]
      // 生成与 convertPathToFunctions 相同的函数名
      let opId = operation.operationId
      if (!opId) {
        const cleanPath = path
          .replace(/^\//, '')
          .replace(/\{([^}]+)\}/g, '$1')
          .replace(/[^a-zA-Z0-9]/g, '_')
          .replace(/_+/g, '_')
          .replace(/^_+|_+$/g, '')
        opId = `${method.toLowerCase()}_${cleanPath || 'root'}`
      }

      if (opId === functionName) {
        targetPath = path
        targetMethod = method.toLowerCase()
        targetOperation = operation
        break
      }
    }
    if (targetPath) break
  }

  if (!targetPath) {
    throw new Error(`未找到函数: ${functionName}`)
  }

  // 构建请求
  const parameters = targetOperation.parameters || []
  const pathParams = {}
  const queryParams = {}
  const bodyParams = {}

  // 分离路径参数、查询参数和请求体参数
  parameters.forEach(param => {
    const value = args[param.name]
    if (value !== undefined) {
      if (param.in === 'path') {
        pathParams[param.name] = value
      } else if (param.in === 'query') {
        queryParams[param.name] = value
      }
    }
  })

  // 处理请求体
  if (targetOperation.requestBody) {
    // 尝试多种 content-type
    const contentTypes = ['application/json', 'application/x-www-form-urlencoded', 'multipart/form-data']
    let content = null
    for (const contentType of contentTypes) {
      if (targetOperation.requestBody.content && targetOperation.requestBody.content[contentType]) {
        content = targetOperation.requestBody.content[contentType]
        break
      }
    }
    
    if (content && content.schema) {
      // 获取请求体的 schema 属性
      const bodySchema = content.schema
      if (bodySchema.properties) {
        Object.keys(bodySchema.properties).forEach(key => {
          if (args[key] !== undefined) {
            bodyParams[key] = args[key]
          }
        })
      } else {
        // 如果没有 properties，尝试将所有未使用的参数放入 body
        Object.keys(args).forEach(key => {
          if (!pathParams[key] && !queryParams[key]) {
            bodyParams[key] = args[key]
          }
        })
      }
    } else {
      // 如果没有明确的 schema，将所有未使用的参数放入 body
      Object.keys(args).forEach(key => {
        if (!pathParams[key] && !queryParams[key]) {
          bodyParams[key] = args[key]
        }
      })
    }
  }

  // 替换路径参数
  let finalPath = targetPath
  Object.keys(pathParams).forEach(key => {
    finalPath = finalPath.replace(`{${key}}`, pathParams[key])
  })

  // 构建请求配置
  const config = {
    method: targetMethod,
    url: `${API_BASE_URL}${finalPath}`,
    params: queryParams
  }

  // 添加请求体（POST、PUT、PATCH）
  if (['post', 'put', 'patch'].includes(targetMethod) && Object.keys(bodyParams).length > 0) {
    config.data = bodyParams
  }

  try {
    const response = await axios(config)
    return {
      success: true,
      data: response.data
    }
  } catch (error) {
    console.error(`执行函数 ${functionName} 失败:`, error)
    return {
      success: false,
      error: error.response?.data || error.message
    }
  }
}

/**
 * 清除缓存（用于重新加载 API 文档）
 */
export function clearCache() {
  openApiCache = null
  functionsCache = null
}

/**
 * 初始化包装器（可选，用于预加载）
 */
export async function initialize() {
  try {
    await getFunctionDefinitions()
    console.log('DeepSeek API 包装器初始化成功')
    return true
  } catch (error) {
    console.error('DeepSeek API 包装器初始化失败:', error)
    return false
  }
}

export default {
  getFunctionDefinitions,
  executeFunction,
  clearCache,
  initialize
}
