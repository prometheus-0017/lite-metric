<template>
  <div class="countdown-card">
    <h3>{{ title }}</h3>
    <div class="target-date">目标: {{ formattedTarget }}</div>

    <div v-if="currentTime === null" class="loading">等待时间数据...</div>
    <div v-else-if="remaining <= 0" class="expired">已到达!</div>
    <div v-else class="remaining">
      <div class="time-block">
        <span class="value">{{ days }}</span>
        <span class="label">天</span>
      </div>
      <div class="time-block">
        <span class="value">{{ hours }}</span>
        <span class="label">时</span>
      </div>
      <div class="time-block">
        <span class="value">{{ minutes }}</span>
        <span class="label">分</span>
      </div>
      <div class="time-block">
        <span class="value">{{ seconds }}</span>
        <span class="label">秒</span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, inject, onMounted, onUnmounted } from 'vue'

const props = defineProps<{
  targetDate: string  // ISO 日期字符串，如 "2077-01-01"
  title?: string
}>()

const METRIC_ID = 'time'

// ─── 从 App.vue 注入 ─────────────────────────────────────────────────────────

const register = inject<(id: string) => void>('register')!
const unregister = inject<(id: string) => void>('unregister')!
const metricDataMap = inject<Record<string, any>>('metricDataMap')!

// ─── 目标时间 ─────────────────────────────────────────────────────────────────

const targetTimestamp = new Date(props.targetDate).getTime() / 1000 // 转为秒级时间戳
const formattedTarget = new Date(props.targetDate).toLocaleDateString('zh-CN', {
  year: 'numeric', month: 'long', day: 'numeric'
})

// ─── 响应式数据 ───────────────────────────────────────────────────────────────

const currentTime = computed<number | null>(() => {
  const val = metricDataMap[METRIC_ID]
  return typeof val === 'number' ? val : null
})

const remaining = computed(() => {
  if (currentTime.value === null) return 0
  return targetTimestamp - currentTime.value
})

const days = computed(() => Math.floor(remaining.value / 86400))
const hours = computed(() => Math.floor((remaining.value % 86400) / 3600))
const minutes = computed(() => Math.floor((remaining.value % 3600) / 60))
const seconds = computed(() => Math.floor(remaining.value % 60))

// ─── 生命周期 ─────────────────────────────────────────────────────────────────

onMounted(() => {
  register(METRIC_ID)
})

onUnmounted(() => {
  unregister(METRIC_ID)
})
</script>

<style scoped>
.countdown-card {
  background: white;
  border-radius: 12px;
  padding: 24px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
  min-width: 280px;
  text-align: center;
}

.countdown-card h3 {
  margin: 0 0 8px 0;
  font-size: 18px;
  color: #333;
}

.target-date {
  font-size: 13px;
  color: #999;
  margin-bottom: 16px;
}

.loading, .expired {
  font-size: 16px;
  color: #999;
  padding: 20px 0;
}

.expired {
  color: #e6a23c;
  font-weight: bold;
}

.remaining {
  display: flex;
  justify-content: center;
  gap: 12px;
}

.time-block {
  display: flex;
  flex-direction: column;
  align-items: center;
}

.time-block .value {
  font-size: 36px;
  font-weight: bold;
  color: #409EFF;
  line-height: 1;
  min-width: 50px;
}

.time-block .label {
  font-size: 12px;
  color: #999;
  margin-top: 4px;
}
</style>
