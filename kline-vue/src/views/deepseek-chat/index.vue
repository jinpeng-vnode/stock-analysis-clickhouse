<template>
  <div class="deepseek-chat-page">
    <a-page-header
      title="DeepSeek 股票分析助手"
      sub-title="基于函数调用的智能股票分析"
      class="page-header"
    >
      <template #extra>
        <a-space>
          <a-button 
            type="default"
            @click="showSettings = true"
          >
            <template #icon>
              <SettingOutlined />
            </template>
            设置
          </a-button>
          <a-button 
            type="default"
            @click="clearHistory"
            :disabled="messages.length === 0"
          >
            <template #icon>
              <ClearOutlined />
            </template>
            清空历史
          </a-button>
        </a-space>
      </template>
    </a-page-header>

    <div class="content">
      <!-- API Key 设置对话框 -->
      <a-modal
        v-model:open="showSettings"
        title="DeepSeek API 设置"
        @ok="saveSettings"
      >
        <a-form layout="vertical">
          <a-form-item label="API Key">
            <a-input-password
              v-model:value="settings.apiKey"
              placeholder="请输入 DeepSeek API Key"
            />
            <template #help>
              <a-typography-text type="secondary">
                请从 DeepSeek 官网获取 API Key
              </a-typography-text>
            </template>
          </a-form-item>
          <a-form-item label="使用流式输出">
            <a-switch v-model:checked="settings.stream" />
          </a-form-item>
          <a-form-item label="显示原始思考过程文本">
            <a-switch v-model:checked="settings.showReasoningText" />
            <template #help>
              <a-typography-text type="secondary">
                开启后可查看 AI 的原始思考过程文本
              </a-typography-text>
            </template>
          </a-form-item>
          <a-form-item label="使用多阶段Agent（规划-执行-汇总）">
            <a-switch v-model:checked="settings.useMultiStage" />
            <template #help>
              <a-typography-text type="secondary">
                开启后使用三层架构：先规划任务，再执行（带反思机制），最后汇总分析
              </a-typography-text>
            </template>
          </a-form-item>
        </a-form>
      </a-modal>

      <!-- 聊天区域 -->
      <a-card class="chat-card">
        <!-- 消息列表 -->
        <div class="messages-container" ref="messagesContainer">
          <div v-if="messages.length === 0" class="welcome-message">
            <a-empty description="开始对话吧！支持多轮对话，AI 会记住之前的对话内容">
              <template #image>
                <RobotOutlined style="font-size: 48px; color: #1890ff" />
              </template>
              <div class="example-questions">
                <a-typography-title :level="5">示例问题：</a-typography-title>
                <a-space direction="vertical" style="width: 100%">
                  <a-button 
                    type="text" 
                    block 
                    @click="sendMessage('帮我搜索一下平安银行')"
                  >
                    💡 帮我搜索一下平安银行
                  </a-button>
                  <a-button 
                    type="text" 
                    block 
                    @click="sendMessage('分析一下000001这只股票的多维度数据')"
                  >
                    💡 分析一下000001这只股票的多维度数据
                  </a-button>
                  <a-button 
                    type="text" 
                    block 
                    @click="sendMessage('获取600519的资金流向和财务数据')"
                  >
                    💡 获取600519的资金流向和财务数据
                  </a-button>
                  <a-button 
                    type="text" 
                    block 
                    @click="sendMessage('分析贵州茅台的资讯、公告情况')"
                  >
                    💡 分析贵州茅台的资讯、公告情况
                  </a-button>
                </a-space>
              </div>
            </a-empty>
          </div>

          <template v-for="(message, index) in messages" :key="`${message.role}-${index}-${message.id || ''}`">
            <!-- 用户消息 -->
            <div v-if="message.role === 'user'" class="message-item user">
              <div class="message-content user-message">
                <a-avatar :style="{ backgroundColor: '#1890ff' }">
                  <UserOutlined />
                </a-avatar>
                <div class="message-bubble">
                  <a-typography-text>{{ message.content }}</a-typography-text>
                </div>
              </div>
            </div>

            <!-- 助手消息 -->
            <div v-else-if="message.role === 'assistant'" class="message-item assistant">
              <div class="message-content assistant-message">
                <a-avatar :style="{ backgroundColor: '#52c41a' }">
                  <RobotOutlined />
                </a-avatar>
                <div class="message-bubble">
                  <!-- 思考过程 -->
                  <div v-if="message.reasoning_content" class="reasoning-content">
                    <a-tag color="purple">
                      <BulbOutlined /> 思考过程
                    </a-tag>
                    
                    <!-- 原始思考过程文本（可折叠）- 仅在设置中开启时显示 -->
                    <a-collapse v-if="settings.showReasoningText === true" style="margin-top: 12px;">
                      <a-collapse-panel key="text" header="查看思考过程文本">
                        <pre style="white-space: pre-wrap; word-wrap: break-word; font-size: 12px; max-height: 200px; overflow-y: auto;">{{ message.reasoning_content }}</pre>
                      </a-collapse-panel>
                    </a-collapse>
                  </div>

                  <!-- 执行摘要 -->
                  <div v-if="message.executionSummary" class="execution-summary">
                    <a-descriptions title="执行摘要" :column="3" size="small" bordered>
                      <a-descriptions-item label="总任务数">{{ message.executionSummary.total }}</a-descriptions-item>
                      <a-descriptions-item label="成功">
                        <a-tag color="success">{{ message.executionSummary.success }}</a-tag>
                      </a-descriptions-item>
                      <a-descriptions-item label="失败">
                        <a-tag color="error">{{ message.executionSummary.failed }}</a-tag>
                      </a-descriptions-item>
                      <a-descriptions-item label="跳过">
                        <a-tag color="default">{{ message.executionSummary.skipped }}</a-tag>
                      </a-descriptions-item>
                    </a-descriptions>
                  </div>

                  <!-- 函数调用标签（简要提示） -->
                  <div v-if="message.tool_calls && message.tool_calls.length > 0" class="tool-calls">
                    <a-tag color="blue" v-for="(toolCall, idx) in message.tool_calls" :key="idx">
                      <ToolOutlined /> {{ toolCall.function.name }}
                    </a-tag>
                  </div>

                  <!-- 回复内容 -->
                  <div v-if="message.content" class="assistant-content">
                    <a-typography-paragraph>
                      <div v-html="formatMessage(message.content)"></div>
                    </a-typography-paragraph>
                  </div>

                  <!-- 加载中 -->
                  <div v-if="message.loading" class="loading-indicator">
                    <a-spin size="small" />
                    <span style="margin-left: 8px">正在思考...</span>
                  </div>
                </div>
              </div>
            </div>

            <!-- 函数调用结果（tool 消息） -->
            <div v-else-if="message.role === 'tool'" class="message-item tool">
              <div class="message-content tool-message">
                <a-avatar :style="{ backgroundColor: '#722ed1' }">
                  <ApiOutlined />
                </a-avatar>
                <div class="message-bubble">
                  <a-collapse>
                    <a-collapse-panel :header="`函数调用结果: ${message.tool_call_id}`" :key="index">
                      <pre>{{ message.content }}</pre>
                    </a-collapse-panel>
                  </a-collapse>
                </div>
              </div>
            </div>
          </template>

          <!-- 流式输出显示 -->
          <div v-if="streamingContent" class="message-item assistant">
            <div class="message-content assistant-message">
              <a-avatar :style="{ backgroundColor: '#52c41a' }">
                <RobotOutlined />
              </a-avatar>
              <div class="message-bubble">
                <div class="assistant-content">
                  <a-typography-paragraph>
                    <div v-html="formatMessage(streamingContent)"></div>
                  </a-typography-paragraph>
                  <a-spin size="small" style="margin-top: 8px" />
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- 输入区域 -->
        <div class="input-area">
          <a-input
            v-model:value="inputText"
            placeholder="输入您的问题..."
            :disabled="loading"
            @press-enter="handleSend"
            size="large"
          >
            <template #suffix>
              <a-button
                type="primary"
                :loading="loading"
                @click="handleSend"
                :disabled="!inputText.trim()"
              >
                <template #icon>
                  <SendOutlined />
                </template>
                发送
              </a-button>
            </template>
          </a-input>
        </div>
      </a-card>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, nextTick, onMounted } from 'vue'
import { message } from 'ant-design-vue'
import {
  SettingOutlined,
  ClearOutlined,
  RobotOutlined,
  UserOutlined,
  SendOutlined,
  ToolOutlined
} from '@ant-design/icons-vue'
import { chatWithDeepSeek, setApiKey, getApiKey } from '@/utils/deepseekClient'
import { multiStageAgentWithReflection } from '@/utils/multiStageAgent'
import MarkdownIt from 'markdown-it'

const md = new MarkdownIt({
  html: true,
  linkify: true,
  typographer: true
})

// 状态
const messages = ref([])
const inputText = ref('')
const loading = ref(false)
const showSettings = ref(false)
const streamingContent = ref('')
const messagesContainer = ref(null)
const functionCalls = ref([]) // 存储函数调用状态

// 设置
const settings = ref({
  apiKey: getApiKey() || 'sk-c35de7fafa0444039a570de87402fe2c',
  stream: true,
  showReasoningText: true, // 是否显示原始思考过程文本
  useMultiStage: true // 是否使用多阶段Agent（规划-执行-汇总）
})

// 系统提示
const systemPrompt = `你是一个专业的股票分析助手。你可以通过调用函数来获取股票的多维度数据并进行分析。

你可以获取以下维度的数据（数据通过本地API获取）：
1. 股票搜索和基本信息
2. 日K线数据：开盘价、收盘价、最高价、最低价、成交量、涨跌幅等
3. 资金流向数据：主力净流入、各类型资金流向、多日累计净流入
4. 公告数据：公告类型、标题、发布时间、内容摘要
5. 财务数据：盈利能力、偿债能力、成长性指标

当用户询问股票相关信息时，你应该：
1. 如果用户提到股票名称或代码，先搜索或获取股票信息
2. 根据用户需求调用相应的数据读取函数获取各维度数据
3. 基于获取的多维度原始数据进行综合分析，给出专业的投资建议`

// 格式化消息（Markdown 转 HTML）
const formatMessage = (text) => {
  if (!text) return ''
  return md.render(text)
}



// 滚动到底部
const scrollToBottom = () => {
  nextTick(() => {
    if (messagesContainer.value) {
      messagesContainer.value.scrollTop = messagesContainer.value.scrollHeight
    }
  })
}

// 发送消息
const sendMessage = async (text) => {
  if (!text.trim() || loading.value) return

  // 添加用户消息到消息历史（支持多轮对话）
  messages.value.push({
    role: 'user',
    content: text
  })

  inputText.value = ''
  loading.value = true
  streamingContent.value = ''

  // 添加加载中的助手消息
  const loadingMessageIndex = messages.value.length
  messages.value.push({
    role: 'assistant',
    content: '',
    loading: true
  })

  scrollToBottom()

  try {
    // 如果启用多阶段Agent，使用新的流程（后台执行，不显示进度）
    if (settings.value.useMultiStage) {
      const result = await multiStageAgentWithReflection(
        text,
        {
          onProgress: (progress) => {
            // 后台处理进度，不在界面上显示
            // 可以根据需要在这里添加日志记录等操作
          },
          onFunctionCall: (funcCall) => {
            // 后台处理函数调用，不在界面上显示
            // 可以根据需要在这里添加日志记录等操作
          },
          maxRetries: 3
        }
      )

      // 移除加载中的消息和所有后台消息
      messages.value = messages.value.filter(m => !m.loading && m.role !== 'progress' && m.role !== 'reflection' && m.role !== 'function_call')

      // 添加最终回复
      if (result.content || result.reasoning_content) {
        messages.value.push({
          role: 'assistant',
          content: result.content || '',
          reasoning_content: result.reasoning_content || '',
          executionSummary: result.executionSummary
        })
      }

      scrollToBottom()
    } else {
      // 原有的单阶段流程
      const messageHistory = [
        {
          role: 'system',
          content: systemPrompt
        },
        ...messages.value
          .filter(m => {
            return (m.role !== 'assistant' || !m.loading) && m.role !== 'function_call' && m.role !== 'progress' && m.role !== 'reflection'
          })
          .map(m => {
            const msg = {
              role: m.role,
              content: m.content
            }
            if (m.tool_calls) {
              msg.tool_calls = m.tool_calls
            }
            if (m.tool_call_id) {
              msg.tool_call_id = m.tool_call_id
            }
            return msg
          })
      ]

      const result = await chatWithDeepSeek(
        messageHistory,
        settings.value.stream,
        (chunk) => {
          if (chunk.type === 'content') {
            streamingContent.value += chunk.content
            scrollToBottom()
          }
        },
        (funcCall) => {
          if (funcCall.type === 'start') {
            const loadingIndex = messages.value.findIndex(m => m.loading)
            const insertIndex = loadingIndex !== -1 ? loadingIndex : messages.value.length
            
            messages.value.splice(insertIndex, 0, {
              role: 'function_call',
              id: funcCall.id,
              name: funcCall.name,
              arguments: funcCall.arguments,
              status: 'running',
              result: null,
              error: null
            })
            
            functionCalls.value.push({
              id: funcCall.id,
              name: funcCall.name,
              arguments: funcCall.arguments,
              status: 'running',
              result: null,
              error: null
            })
            scrollToBottom()
          } else if (funcCall.type === 'end') {
            const messageIndex = messages.value.findIndex(m => m.role === 'function_call' && m.id === funcCall.id)
            if (messageIndex !== -1) {
              messages.value[messageIndex] = {
                ...messages.value[messageIndex],
                status: funcCall.error ? 'error' : 'completed',
                result: funcCall.result,
                error: funcCall.error
              }
            }
            
            const index = functionCalls.value.findIndex(fc => fc.id === funcCall.id)
            if (index !== -1) {
              functionCalls.value[index] = {
                ...functionCalls.value[index],
                status: funcCall.error ? 'error' : 'completed',
                result: funcCall.result,
                error: funcCall.error
              }
            }
            scrollToBottom()
          }
        }
      )

      messages.value = messages.value.filter(m => !m.loading)

      if (result.content || result.reasoning_content) {
        messages.value.push({
          role: 'assistant',
          content: result.content || '',
          reasoning_content: result.reasoning_content || '',
          tool_calls: result.tool_calls
        })
      }

      streamingContent.value = ''
      scrollToBottom()
    }

  } catch (error) {
    console.error('发送消息失败:', error)
    message.error('发送失败: ' + error.message)

    // 移除加载中的消息
    messages.value = messages.value.filter(m => !m.loading)

    // 添加错误消息
    messages.value.push({
      role: 'assistant',
      content: `抱歉，发生了错误：${error.message}`
    })
  } finally {
    loading.value = false
    streamingContent.value = ''
  }
}

// 处理发送
const handleSend = () => {
  sendMessage(inputText.value)
}

// 清空历史
const clearHistory = () => {
  messages.value = []
  functionCalls.value = []
  message.success('对话历史已清空')
}

// 保存设置
const saveSettings = () => {
  setApiKey(settings.value.apiKey)
  message.success('设置已保存')
  showSettings.value = false
}

onMounted(() => {
 
  
  // 初始化 API Key
  if (settings.value.apiKey) {
    setApiKey(settings.value.apiKey)
  }
})
</script>

<style scoped>
.deepseek-chat-page {
  padding: 24px;
  background: #f0f2f5;
  min-height: 100vh;
}

.page-header {
  background: white;
  margin-bottom: 16px;
  padding: 16px 24px;
  border-radius: 4px;
}

.content {
  background: transparent;
}

.chat-card {
  height: calc(100vh - 200px);
  display: flex;
  flex-direction: column;
}

.messages-container {
  flex: 1;
  overflow-y: auto;
  padding: 16px;
  background: #fafafa;
}

.welcome-message {
  text-align: center;
  padding: 40px 20px;
}

.example-questions {
  margin-top: 24px;
  text-align: left;
  max-width: 600px;
  margin-left: auto;
  margin-right: auto;
}

.message-item {
  margin-bottom: 16px;
}

.message-content {
  display: flex;
  gap: 12px;
  align-items: flex-start;
}

.function-call-item {
  margin-bottom: 16px;
}

.function-call-message {
  flex-direction: row;
}

.function-call-bubble {
  max-width: 85%;
}

.function-call-bubble :deep(.ant-card-head) {
  background: #fafafa;
  border-bottom: 1px solid #e8e8e8;
}

.function-call-running :deep(.ant-card-head) {
  background: #fff7e6;
}

.function-call-success :deep(.ant-card-head) {
  background: #f6ffed;
}

.function-call-error :deep(.ant-card-head) {
  background: #fff1f0;
}

.function-args,
.function-result,
.function-error {
  background: #f5f5f5;
  padding: 8px 12px;
  border-radius: 4px;
  overflow-x: auto;
  margin: 0;
  font-size: 12px;
  font-family: 'Courier New', monospace;
  max-height: 300px;
  overflow-y: auto;
}

.function-error {
  background: #fff1f0;
  color: #ff4d4f;
}

.function-loading {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 16px;
  color: #999;
}

.user-message {
  flex-direction: row-reverse;
}

.assistant-message {
  flex-direction: row;
}

.tool-message {
  flex-direction: row;
}

.message-bubble {
  max-width: 70%;
  padding: 12px 16px;
  border-radius: 8px;
  background: white;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  
  /* 包含知识图谱的消息气泡可以更宽 */
  &:has(.knowledge-graph-view) {
    max-width: 90%;
  }
}

/* 知识图谱容器在消息气泡内正常显示，但可以更宽 */
.message-bubble .knowledge-graph-view {
  max-width: 100% !important;
  width: 100% !important;
  margin-left: 0;
  margin-right: 0;
}

.user-message .message-bubble {
  background: #1890ff;
  color: white;
}

.assistant-content {
  line-height: 1.6;
}

.assistant-content :deep(pre) {
  background: #f5f5f5;
  padding: 8px 12px;
  border-radius: 4px;
  overflow-x: auto;
}

.assistant-content :deep(code) {
  background: #f5f5f5;
  padding: 2px 6px;
  border-radius: 3px;
  font-family: 'Courier New', monospace;
}

.reasoning-content {
  margin-bottom: 12px;
  padding: 12px;
  background: #f0f5ff;
  border-radius: 4px;
}

.reasoning-content pre {
  margin-top: 8px;
  margin-bottom: 0;
  font-size: 12px;
  color: #666;
}

.execution-summary {
  margin-bottom: 12px;
  padding: 12px;
  background: #f6ffed;
  border-radius: 4px;
}

.reflection-message {
  flex-direction: row;
}

.reflection-bubble {
  max-width: 85%;
}

.progress-message {
  flex-direction: row;
}

.progress-bubble {
  max-width: 85%;
}

.execution-log {
  margin-top: 12px;
}

.log-section {
  margin-bottom: 16px;
}

.log-title {
  font-weight: 600;
  margin-bottom: 8px;
  color: #1890ff;
  font-size: 13px;
}

.log-pre {
  background: #f5f5f5;
  padding: 8px 12px;
  border-radius: 4px;
  overflow-x: auto;
  margin: 0;
  font-size: 12px;
  font-family: 'Courier New', monospace;
  max-height: 400px;
  overflow-y: auto;
  white-space: pre-wrap;
  word-wrap: break-word;
}

.error-text {
  color: #ff4d4f;
  background: #fff1f0;
}

.tool-calls {
  margin-bottom: 12px;
}

.loading-indicator {
  display: flex;
  align-items: center;
  color: #999;
}

.input-area {
  padding: 16px;
  border-top: 1px solid #e8e8e8;
  background: white;
}

:deep(.ant-typography) {
  margin-bottom: 0;
}
</style>
