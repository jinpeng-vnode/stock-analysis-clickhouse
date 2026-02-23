<template>
  <div class="deepseek-api-wrapper-demo">
    <a-card title="DeepSeek API 包装器演示">
      <a-space direction="vertical" style="width: 100%">
        <a-button type="primary" @click="loadFunctions" :loading="loading">
          加载 API 函数定义
        </a-button>
        
        <a-alert
          v-if="error"
          type="error"
          :message="error"
          show-icon
          closable
          @close="error = null"
        />
        
        <a-alert
          v-if="functions.length > 0"
          type="success"
          :message="`已加载 ${functions.length} 个函数`"
          show-icon
        />
        
        <a-divider>函数列表</a-divider>
        
        <a-list
          v-if="functions.length > 0"
          :data-source="functions"
          :pagination="{ pageSize: 10 }"
        >
          <template #renderItem="{ item }">
            <a-list-item>
              <a-list-item-meta>
                <template #title>
                  <a-typography-text code>{{ item.name }}</a-typography-text>
                </template>
                <template #description>
                  {{ item.description }}
                </template>
              </a-list-item-meta>
              <template #actions>
                <a-button size="small" @click="testFunction(item)">
                  测试调用
                </a-button>
              </template>
            </a-list-item>
          </template>
        </a-list>
        
        <a-divider>测试调用</a-divider>
        
        <a-form
          v-if="selectedFunction"
          :model="testForm"
          layout="vertical"
        >
          <a-form-item label="函数名称">
            <a-input v-model:value="selectedFunction.name" disabled />
          </a-form-item>
          <a-form-item label="参数 (JSON)">
            <a-textarea
              v-model:value="testForm.args"
              :rows="6"
              placeholder='{"code": "000001"}'
            />
          </a-form-item>
          <a-form-item>
            <a-space>
              <a-button type="primary" @click="executeTest" :loading="executing">
                执行调用
              </a-button>
              <a-button @click="selectedFunction = null">取消</a-button>
            </a-space>
          </a-form-item>
        </a-form>
        
        <a-divider>调用结果</a-divider>
        
        <a-typography-paragraph v-if="testResult">
          <pre style="background: #f5f5f5; padding: 16px; border-radius: 4px; overflow-x: auto;">{{ JSON.stringify(testResult, null, 2) }}</pre>
        </a-typography-paragraph>
      </a-space>
    </a-card>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { message } from 'ant-design-vue'
import { useDeepSeekApi } from '@/composables/useDeepSeekApi'

const { functions, loading, error, loadFunctions, callFunction } = useDeepSeekApi()

const selectedFunction = ref(null)
const testForm = ref({
  args: '{}'
})
const executing = ref(false)
const testResult = ref(null)

const testFunction = (func) => {
  selectedFunction.value = func
  testForm.value.args = '{}'
  testResult.value = null
}

const executeTest = async () => {
  if (!selectedFunction.value) {
    message.error('请先选择要测试的函数')
    return
  }

  executing.value = true
  testResult.value = null

  try {
    const args = JSON.parse(testForm.value.args || '{}')
    const result = await callFunction(selectedFunction.value.name, args)
    testResult.value = result
    message.success('调用成功')
  } catch (err) {
    testResult.value = {
      error: err.message,
      stack: err.stack
    }
    message.error('调用失败: ' + err.message)
  } finally {
    executing.value = false
  }
}

onMounted(() => {
  // 组件挂载时自动加载函数定义
  // loadFunctions()
})
</script>

<style scoped>
.deepseek-api-wrapper-demo {
  padding: 24px;
}
</style>
