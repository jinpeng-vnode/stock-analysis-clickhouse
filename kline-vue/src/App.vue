<template>
  <a-config-provider :locale="zhCN">
    <div id="app">
      <a-layout>
        <a-layout-header class="header">
          <div class="logo">
            <h2>K线图分析系统</h2>
          </div>
          <a-menu
            v-model:selectedKeys="selectedKeys"
            mode="horizontal"
            theme="dark"
            :overflowedIndicator="null"
            @click="handleMenuClick"
          >
            <a-menu-item 
              v-for="route in menuRoutes" 
              :key="route.path.replace('/', '')"
            >
              <template #icon>
                <component :is="route.meta?.icon" />
              </template>
              {{ route.meta?.title }}
            </a-menu-item>
          </a-menu>
        </a-layout-header>
        
        <a-layout-content class="content">
          <router-view />
        </a-layout-content>
      </a-layout>
    </div>
  </a-config-provider>
</template>

<script setup lang="ts">
import { ref, watch, computed } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import zhCN from 'ant-design-vue/es/locale/zh_CN'

const router = useRouter()
const route = useRoute()

const selectedKeys = ref<string[]>([])

// 从路由配置中获取需要显示在菜单中的路由
const menuRoutes = computed(() => {
  return router.getRoutes().filter(route => 
    route.meta?.showInMenu === true && route.path !== '/'
  )
})

// 根据当前路由设置选中的菜单项
const updateSelectedKeys = () => {
  const path = route.path
  const currentRoute = menuRoutes.value.find(r => r.path === path)
  if (currentRoute) {
    selectedKeys.value = [path.replace('/', '')]
  } else {
    selectedKeys.value = ['day'] // 默认选中第一个菜单项
  }
}

// 处理菜单点击
const handleMenuClick = ({ key }: { key: string }) => {
  router.push(`/${key}`)
}

// 监听路由变化
watch(() => route.path, updateSelectedKeys, { immediate: true })
</script>

<style scoped>
#app {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, 'Noto Sans', 'PingFang SC', 'Hiragino Sans GB', 'Microsoft YaHei', sans-serif;
}

.header {
  display: flex;
  align-items: center;
  padding: 0 24px;
  background: #001529;
  min-width: 100%;
  overflow: visible;
}

.logo {
  margin: 0 24px;
}

.logo h2 {
  color: white;
  margin: 0;
  font-size: 18px;
}

.content {
  min-height: calc(100vh - 64px);
  background: #f0f2f5;
}

:deep(.ant-layout-header) {
  padding: 0;
}

:deep(.ant-menu-horizontal) {
  border-bottom: none;
  flex: 1;
  min-width: 0;
}

:deep(.ant-menu-horizontal .ant-menu-item) {
  white-space: nowrap;
}

:deep(.ant-menu-horizontal .ant-menu-overflow) {
  display: flex !important;
}

:deep(.ant-menu-horizontal .ant-menu-overflow-item) {
  display: inline-block !important;
}
</style>
