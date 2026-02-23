import { createApp } from 'vue'
import App from './App.vue'
import router from './router'
import { createPinia } from 'pinia'

// Ant Design Vue
import Antd from 'ant-design-vue'
import 'ant-design-vue/dist/reset.css'

// Optional: global icon components from @ant-design/icons-vue if needed in templates
import * as Icons from '@ant-design/icons-vue'

// MateChat
import MateChat from '@matechat/core'
import '@devui-design/icons/icomoon/devui-icon.css'

const app = createApp(App)
const pinia = createPinia()

// register icons globally
Object.entries(Icons).forEach(([key, component]) => {
  // @ts-ignore
  app.component(key, component)
})

app.use(pinia)
app.use(router)
app.use(Antd)
app.use(MateChat)

app.mount('#app')


