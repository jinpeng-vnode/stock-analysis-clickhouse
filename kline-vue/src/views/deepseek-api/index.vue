<template>
  <div class="deepseek-api-page">
    <a-page-header
      title="DeepSeek API 包装器"
      sub-title="自动读取 FastAPI 文档并转换为函数调用格式"
      class="page-header"
    >
      <template #extra>
        <a-space>
          <a-button 
            type="primary" 
            :loading="loading"
            @click="loadFunctions"
          >
            <template #icon>
              <ReloadOutlined />
            </template>
            重新加载
          </a-button>
          <a-button 
            type="default"
            @click="clearCacheAndReload"
          >
            <template #icon>
              <ClearOutlined />
            </template>
            清除缓存
          </a-button>
        </a-space>
      </template>
    </a-page-header>

    <div class="content">
      <!-- 状态提示 -->
      <a-alert
        v-if="error"
        type="error"
        :message="error"
        show-icon
        closable
        @close="error = null"
        style="margin-bottom: 16px"
      />
      
      <a-alert
        v-if="initialized && functions.length > 0"
        type="success"
        :message="`已成功加载 ${functions.length} 个 API 函数`"
        show-icon
        style="margin-bottom: 16px"
      />

      <!-- 统计信息 -->
      <a-row :gutter="[16, 16]" style="margin-bottom: 24px">
        <a-col :span="6">
          <a-card>
            <a-statistic
              title="函数总数"
              :value="functions.length"
              :loading="loading"
            >
              <template #prefix>
                <ApiOutlined style="color: #1890ff" />
              </template>
            </a-statistic>
          </a-card>
        </a-col>
        <a-col :span="6">
          <a-card>
            <a-statistic
              title="已测试"
              :value="testedFunctions.size"
            >
              <template #prefix>
                <CheckCircleOutlined style="color: #52c41a" />
              </template>
            </a-statistic>
          </a-card>
        </a-col>
        <a-col :span="6">
          <a-card>
            <a-statistic
              title="API 地址"
              :value="apiBaseUrl"
            >
              <template #prefix>
                <GlobalOutlined style="color: #722ed1" />
              </template>
            </a-statistic>
          </a-card>
        </a-col>
        <a-col :span="6">
          <a-card>
            <a-statistic
              title="状态"
              :value="initialized ? '已初始化' : '未初始化'"
            >
              <template #prefix>
                <CheckCircleOutlined v-if="initialized" style="color: #52c41a" />
                <ApiOutlined v-else style="color: #ff4d4f" />
              </template>
            </a-statistic>
          </a-card>
        </a-col>
      </a-row>

      <a-row :gutter="[16, 16]">
        <!-- 左侧：函数列表 -->
        <a-col :span="12">
          <a-card title="API 函数列表" :loading="loading">
            <template #extra>
              <a-input-search
                v-model:value="searchKeyword"
                placeholder="搜索函数..."
                style="width: 200px"
                allow-clear
              />
            </template>

            <a-list
              :data-source="filteredFunctions"
              :pagination="{ 
                pageSize: 10,
                showSizeChanger: true,
                showTotal: (total) => `共 ${total} 个函数`
              }"
              style="max-height: 600px; overflow-y: auto"
            >
              <template #renderItem="{ item }">
                <a-list-item>
                  <a-list-item-meta>
                    <template #title>
                      <a-space>
                        <a-typography-text code strong>{{ item.name }}</a-typography-text>
                        <a-tag v-if="testedFunctions.has(item.name)" color="success">
                          已测试
                        </a-tag>
                      </a-space>
                    </template>
                    <template #description>
                      <div>
                        <div style="margin-bottom: 4px">{{ item.description }}</div>
                        <a-tag v-if="item.parameters?.required?.length" color="orange" size="small">
                          必填参数: {{ item.parameters.required.join(', ') }}
                        </a-tag>
                      </div>
                    </template>
                  </a-list-item-meta>
                  <template #actions>
                    <a-button 
                      type="link" 
                      size="small" 
                      @click="showFunctionDetail(item)"
                    >
                      详情
                    </a-button>
                    <a-button 
                      type="link" 
                      size="small" 
                      @click="testFunction(item)"
                    >
                      测试
                    </a-button>
                  </template>
                </a-list-item>
              </template>
            </a-list>
          </a-card>
        </a-col>

        <!-- 右侧：函数详情和测试 -->
        <a-col :span="12">
          <!-- 函数详情 -->
          <a-card 
            v-if="selectedFunction" 
            title="函数详情"
            style="margin-bottom: 16px"
          >
            <template #extra>
              <a-button type="text" @click="selectedFunction = null">
                <CloseOutlined />
              </a-button>
            </template>
            
            <a-descriptions :column="1" bordered size="small">
              <a-descriptions-item label="函数名称">
                <a-typography-text code>{{ selectedFunction.name }}</a-typography-text>
              </a-descriptions-item>
              <a-descriptions-item label="描述">
                {{ selectedFunction.description }}
              </a-descriptions-item>
              <a-descriptions-item label="参数定义">
                <pre style="background: #f5f5f5; padding: 12px; border-radius: 4px; overflow-x: auto; margin: 0;">{{ JSON.stringify(selectedFunction.parameters, null, 2) }}</pre>
              </a-descriptions-item>
            </a-descriptions>
          </a-card>

          <!-- 函数测试 -->
          <a-card title="函数测试" :loading="executing">
            <a-form
              :model="testForm"
              layout="vertical"
            >
              <a-form-item label="选择函数">
              <a-select
                v-model:value="testForm.functionName"
                placeholder="选择要测试的函数"
                show-search
                :filter-option="(input, option) => {
                  const label = option.label || option.children?.[0]?.children || ''
                  return String(label).toLowerCase().includes(input.toLowerCase())
                }"
                @change="onFunctionSelectChange"
              >
                  <a-select-option 
                    v-for="func in functions" 
                    :key="func.name" 
                    :value="func.name"
                  >
                    {{ func.name }}
                  </a-select-option>
                </a-select>
              </a-form-item>

              <a-form-item label="参数 (JSON 格式)">
                <a-textarea
                  v-model:value="testForm.args"
                  :rows="8"
                  placeholder='{"code": "000001", "page": 1, "size": 10}'
                  :disabled="!testForm.functionName"
                />
                <template #help>
                  <a-typography-text type="secondary">
                    请输入 JSON 格式的参数，例如: {"code": "000001"}
                  </a-typography-text>
                </template>
              </a-form-item>

              <a-form-item>
                <a-space>
                  <a-button 
                    type="primary" 
                    @click="executeTest" 
                    :loading="executing"
                    :disabled="!testForm.functionName"
                  >
                    <template #icon>
                      <PlayCircleOutlined />
                    </template>
                    执行调用
                  </a-button>
                  <a-button @click="resetTestForm">
                    重置
                  </a-button>
                </a-space>
              </a-form-item>
            </a-form>

            <!-- 测试结果 -->
            <a-divider>调用结果</a-divider>
            
            <a-empty 
              v-if="!testResult && !executing"
              description="暂无调用结果"
            />

            <div v-if="testResult">
              <a-space style="margin-bottom: 8px">
                <a-tag :color="testResult.success ? 'success' : 'error'">
                  {{ testResult.success ? '成功' : '失败' }}
                </a-tag>
                <a-typography-text type="secondary" v-if="testResult.duration">
                  耗时: {{ testResult.duration }}ms
                </a-typography-text>
              </a-space>
              
              <a-typography-paragraph>
                <pre style="background: #f5f5f5; padding: 16px; border-radius: 4px; overflow-x: auto; max-height: 400px; overflow-y: auto; margin: 0;">{{ JSON.stringify(testResult.data || testResult.error, null, 2) }}</pre>
              </a-typography-paragraph>
            </div>
          </a-card>
        </a-col>
      </a-row>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { message } from 'ant-design-vue'
import {
  ReloadOutlined,
  ClearOutlined,
  ApiOutlined,
  CheckCircleOutlined,
  GlobalOutlined,
  CloseOutlined,
  PlayCircleOutlined
} from '@ant-design/icons-vue'
import { useDeepSeekApi } from '@/composables/useDeepSeekApi'
import { clearCache } from '@/utils/deepseekApiWrapper'

// 使用组合式函数
const { 
  functions, 
  loading, 
  error, 
  initialized,
  loadFunctions, 
  callFunction,
  reload
} = useDeepSeekApi()

// 状态
const selectedFunction = ref(null)
const searchKeyword = ref('')
const testedFunctions = ref(new Set())
const executing = ref(false)
const testResult = ref(null)
const apiBaseUrl = ref(import.meta.env.VITE_API_BASE_URL || 'http://localhost:9010')

// 测试表单
const testForm = ref({
  functionName: '',
  args: '{}'
})

// 过滤后的函数列表
const filteredFunctions = computed(() => {
  if (!searchKeyword.value) {
    return functions.value
  }
  const keyword = searchKeyword.value.toLowerCase()
  return functions.value.filter(func => 
    func.name.toLowerCase().includes(keyword) ||
    func.description?.toLowerCase().includes(keyword)
  )
})

// 显示函数详情
const showFunctionDetail = (func) => {
  selectedFunction.value = func
}

// 测试函数
const testFunction = (func) => {
  selectedFunction.value = func
  testForm.value.functionName = func.name
  testForm.value.args = '{}'
  testResult.value = null
}

// 函数选择变化
const onFunctionSelectChange = (functionName) => {
  const func = functions.value.find(f => f.name === functionName)
  if (func) {
    selectedFunction.value = func
    // 生成示例参数
    if (func.parameters?.properties) {
      const exampleArgs = {}
      Object.keys(func.parameters.properties).forEach(key => {
        const prop = func.parameters.properties[key]
        if (prop.type === 'string') {
          exampleArgs[key] = ''
        } else if (prop.type === 'number' || prop.type === 'integer') {
          exampleArgs[key] = 0
        } else if (prop.type === 'boolean') {
          exampleArgs[key] = false
        } else if (prop.type === 'array') {
          exampleArgs[key] = []
        } else {
          exampleArgs[key] = {}
        }
      })
      testForm.value.args = JSON.stringify(exampleArgs, null, 2)
    } else {
      testForm.value.args = '{}'
    }
  }
}

// 执行测试
const executeTest = async () => {
  if (!testForm.value.functionName) {
    message.error('请先选择要测试的函数')
    return
  }

  executing.value = true
  testResult.value = null
  const startTime = Date.now()

  try {
    // 解析参数
    let args = {}
    try {
      args = JSON.parse(testForm.value.args || '{}')
    } catch (e) {
      message.error('参数格式错误，请输入有效的 JSON')
      executing.value = false
      return
    }

    // 执行函数调用
    const result = await callFunction(testForm.value.functionName, args)
    const duration = Date.now() - startTime

    testResult.value = {
      success: true,
      data: result,
      duration
    }

    // 标记为已测试
    testedFunctions.value.add(testForm.value.functionName)
    message.success('调用成功')
  } catch (err) {
    const duration = Date.now() - startTime
    testResult.value = {
      success: false,
      error: {
        message: err.message,
        stack: err.stack
      },
      duration
    }
    message.error('调用失败: ' + err.message)
  } finally {
    executing.value = false
  }
}

// 重置测试表单
const resetTestForm = () => {
  testForm.value = {
    functionName: '',
    args: '{}'
  }
  testResult.value = null
  selectedFunction.value = null
}

// 清除缓存
const clearCacheAndReload = async () => {
  clearCache()
  message.success('缓存已清除')
  await reload()
}

// 组件挂载时加载函数
onMounted(async () => {
  if (!initialized.value) {
    await loadFunctions()
  }
})
</script>

<style scoped>
.deepseek-api-page {
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

:deep(.ant-card) {
  border-radius: 4px;
}

:deep(.ant-list-item) {
  padding: 12px 0;
}

:deep(.ant-descriptions-item-label) {
  font-weight: 500;
}

pre {
  font-family: 'Courier New', Courier, monospace;
  font-size: 12px;
  line-height: 1.5;
}
</style>
