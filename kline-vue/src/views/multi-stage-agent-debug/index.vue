<template>
  <div class="multi-stage-agent-debug-page">
    <a-page-header
      title="多阶段Agent调试"
      sub-title="测试规划-执行-汇总流程"
      class="page-header"
    />

    <div class="content">
      <a-card class="debug-card">
        <!-- 输入区域 -->
        <div class="input-section">
          <a-input
            v-model:value="inputText"
            placeholder="请输入问题，例如：帮我搜索一下平安银行"
            size="large"
            @press-enter="handleSend"
            :disabled="loading"
          >
            <template #suffix>
              <a-button
                type="primary"
                :loading="loading"
                @click="handleSend"
                :disabled="!inputText.trim()"
              >
                发送
              </a-button>
            </template>
          </a-input>
        </div>

        <!-- 结果展示区域 -->
        <div class="result-section" v-if="result || loading">
          <a-divider>执行结果</a-divider>
          
          <!-- 加载中 -->
          <div v-if="loading" class="loading-section">
            <a-spin size="large" />
            <div style="margin-top: 16px; color: #666;">正在处理中...</div>
          </div>

          <!-- 结果显示 -->
          <div v-else-if="result" class="result-content">
            <!-- 最终结果 -->
            <a-card v-if="result.finalResult?.content" size="small">
              <div class="content-text">
                <div v-html="formatMessage(result.finalResult.content)"></div>
              </div>
            </a-card>
            
            <!-- 错误信息 -->
            <a-alert
              v-else-if="result.error"
              type="error"
              :message="result.error"
              :description="result.stack"
              show-icon
              style="margin-top: 16px;"
            />
          </div>
        </div>

        <!-- 空状态 -->
        <a-empty
          v-else
          description="输入问题开始调试"
          style="margin: 40px 0;"
        >
          <template #image>
            <RobotOutlined style="font-size: 48px; color: #1890ff" />
          </template>
        </a-empty>
      </a-card>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { message } from 'ant-design-vue'
import { RobotOutlined } from '@ant-design/icons-vue'
import { multiStageAgentWithReflection } from '@/utils/multiStageAgent'
import { setAIProvider, AIProvider } from '@/utils/aiClient'
import MarkdownIt from 'markdown-it'

const md = new MarkdownIt({
  html: true,
  linkify: true,
  typographer: true
})

// 状态
const inputText = ref('')
const loading = ref(false)
const result = ref(null)

// 格式化消息（Markdown 转 HTML）
const formatMessage = (text) => {
  if (!text) return ''
  return md.render(text)
}

// 发送消息
const handleSend = async () => {
  if (!inputText.value.trim() || loading.value) return

  const question = inputText.value.trim()
  loading.value = true
  result.value = null

  try {
    // 使用 Ollama 本地模型
    const finalResult = await multiStageAgentWithReflection(
      question,
      {
        aiProvider: 'ollama', // 使用本地 Ollama 模型
        maxRetries: 3
      }
    )

    // 只保存最终结果
    result.value = {
      finalResult: {
        content: finalResult.content || ''
      }
    }

    message.success('执行完成')
  } catch (error) {
    console.error('执行失败:', error)
    message.error(`执行失败: ${error.message || '未知错误'}`)
    result.value = {
      error: error.message || '未知错误',
      stack: error.stack
    }
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.multi-stage-agent-debug-page {
  height: 100vh;
  display: flex;
  flex-direction: column;
  background: #f0f2f5;
}

.page-header {
  background: white;
  padding: 16px 24px;
  border-bottom: 1px solid #e8e8e8;
}

.content {
  flex: 1;
  padding: 24px;
  overflow-y: auto;
}

.debug-card {
  max-width: 1200px;
  margin: 0 auto;
  min-height: 500px;
}

.input-section {
  margin-bottom: 24px;
}

.result-section {
  min-height: 400px;
}

.loading-section {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 60px 0;
}

.result-content {
  margin-top: 16px;
}

.content-text {
  line-height: 1.8;
}

.content-text :deep(pre) {
  background: #f5f5f5;
  padding: 8px 12px;
  border-radius: 4px;
  overflow-x: auto;
}

.content-text :deep(code) {
  background: #f5f5f5;
  padding: 2px 6px;
  border-radius: 3px;
  font-family: 'Courier New', monospace;
}
</style>

