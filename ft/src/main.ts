import { createApp } from 'vue'
import App from './App.vue'
import { register, unregister } from './metricRegistry'

const app = createApp(App)

// 顶层注入 register / unregister，所有子组件可通过 inject 使用
app.provide('metricRegister', register)
app.provide('metricUnregister', unregister)

app.mount('#app')