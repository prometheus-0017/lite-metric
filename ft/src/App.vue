<template>
  <div class="app">
    <header class="header">
      <h1>指标监控系统</h1>
    </header>

    <Tabs v-model="activeTab">
      <TabPane name="time" label="时间倒计时">
        <div class="countdown-grid">
          <Countdown title="距离 2077 年" target-date="2077-01-01" />
          <Countdown title="距离 2078 年" target-date="2078-01-01" />
        </div>
      </TabPane>
      <TabPane name="cpu" label="CPU 指标">
        <div class="metrics-grid">
          <AutoComponent metric-id="cpu_usage_percent" />
          <AutoComponent metric-id="cpu_freq_current" />
          <AutoComponent metric-id="cpu_per_core" />
        </div>
      </TabPane>
    </Tabs>
  </div>
</template>

<script setup lang="ts">
import { ref, provide, onMounted, onUnmounted, reactive } from 'vue'
import AutoComponent from './components/AutoComponent.vue'
import Countdown from './components/Countdown.vue'
import Tabs from './components/Tabs.vue'
import TabPane from './components/TabPane.vue'
import { createMain } from '@xuri-rpc/websocket-sender'
import type { IMetricHandler, IMetricSubscriber, MetricItem, MetricUpdatePayload } from './types.ts'

const activeTab = ref('time')

// ─── 核心状态 ────────────────────────────────────────────────────────────────

/** 指标 ID → 元数据映射 */
const metricMetaMap = reactive<Record<string, MetricItem>>({})

/** 指标 ID → 真实数据映射 */
const metricDataMap = reactive<Record<string, any>>({})

// ─── RPC Handler（模块级单例，防止 HMR 重复初始化）─────────────────────────────

let metricHandler: IMetricHandler | null = null
let subscriber: IMetricSubscriber | null = null
let initPromise: Promise<void> | null = null

async function ensureInitialized(): Promise<void> {
  if (metricHandler) return
  if (initPromise) return initPromise

  initPromise = (async () => {
    
    const [_client, main] = await createMain('frontend-'+Math.random(), 'localhost', 13333, '/')
    metricHandler = main as IMetricHandler
    subscriber = await metricHandler.createSubscriber(onMetricUpdate)
    console.log('[init] subscriber created:', subscriber)
    // await subscriber.addCallback(onMetricUpdate)
    console.log('[init] callback added')
  })()
  return initPromise
}

// ─── 订阅回调 ────────────────────────────────────────────────────────────────

async function onMetricUpdate(metricId: string, payload: MetricUpdatePayload) {
  // 更新真实数据：series 模式用 series 数组，其他用 value
  console.log('[onMetricUpdate] received:', metricId, payload)
  if (payload.series) {
    metricDataMap[metricId] = payload.series
  } else {
    metricDataMap[metricId] = payload.value
  }
}

// ─── Register / Unregister ───────────────────────────────────────────────────

async function register(metricId: string) {
  await ensureInitialized()
  console.log('[register] calling subscriber.register for:', metricId)
  await subscriber?.register(metricId)
  console.log('[register] subscriber.register completed for:', metricId)

  // 注册后立即请求一次全量数据
  if (metricHandler) {
    const data = await metricHandler.queryMetrics([metricId])
    const item = data[metricId]
    if (item) {
      metricMetaMap[metricId] = {
        id: item.id,
        name: item.name,
        data_type: item.data_type,
        save_mode: item.save_mode,
        persist: item.persist,
        timestamp: item.timestamp,
      }
      if (item.save_mode === 'series') {
        metricDataMap[metricId] = item.data
      } else {
        metricDataMap[metricId] = item.value
      }
    }
  }
}

async function unregister(metricId: string) {
  await subscriber?.unregister(metricId)
  delete metricMetaMap[metricId]
  delete metricDataMap[metricId]
}

provide('register', register)
provide('unregister', unregister)
provide('metricMetaMap', metricMetaMap)
provide('metricDataMap', metricDataMap)

// ─── 生命周期 ────────────────────────────────────────────────────────────────

onMounted(async () => {
  await ensureInitialized()
})

onUnmounted(() => {
  subscriber = null
})

// HMR 清理：Vite 热更新时重置状态，避免下次挂载重复初始化
if (import.meta.hot) {
  import.meta.hot.dispose(() => {
    metricHandler = null
    subscriber = null
    initPromise = null
  })
}
</script>

<style scoped>
.app {
  min-height: 100vh;
  background: #f5f7fa;
}

.header {
  background: #409EFF;
  color: white;
  padding: 20px;
  text-align: center;
}

.header h1 {
  margin: 0;
  font-size: 24px;
}

.metrics-grid {
  display: flex;
  flex-wrap: wrap;
  gap: 20px;
}

.countdown-grid {
  display: flex;
  flex-wrap: wrap;
  gap: 20px;
}
</style>
