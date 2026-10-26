<template>
  <div class="single-value-display" :style="{ width: width, height: height }">
    <div class="metric-name">{{ metric.name }}</div>
    <div class="metric-value">{{ formattedValue }}</div>
    <div class="metric-type">{{ metricTypeText }}</div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { SaveMode } from '../types'
import type { MetricItem } from '../types'

const props = defineProps({
  metric: {
    type: Object as () => MetricItem,
    required: true
  },
  width: {
    type: String,
    default: '200px'
  },
  height: {
    type: String,
    default: '100px'
  }
})

const saveModeMap: Record<string, string> = {
  [SaveMode.Latest]: '最新值',
  [SaveMode.Max]: '最大值',
  [SaveMode.Min]: '最小值',
  [SaveMode.Series]: '序列数据'
}

const metricTypeText = computed(() => saveModeMap[props.metric.save_mode] || '')

const formattedValue = computed(() => {
  const val = props.metric.value
  if (val === null || val === undefined) {
    return '--'
  }
  return typeof val === 'number' ? val.toFixed(2) : String(val)
})
</script>

<style scoped>
.single-value-display {
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  border-radius: 8px;
  padding: 12px;
  box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
  transition: transform 0.2s ease;
}

.single-value-display:hover {
  transform: translateY(-2px);
}

.metric-name {
  font-size: 14px;
  font-weight: 600;
  opacity: 0.9;
  margin-bottom: 4px;
}

.metric-value {
  font-size: 24px;
  font-weight: 700;
  margin-bottom: 2px;
}

.metric-type {
  font-size: 12px;
  opacity: 0.7;
}
</style>
