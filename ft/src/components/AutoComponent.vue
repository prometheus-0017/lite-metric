<template>
  <div class="metric-card" v-if="metric">
    <!-- 序列数据 -->
    <div v-if="metric.save_mode === SaveMode.Series" class="chart-wrapper">
      <h3>{{ metric.name }}</h3>
      <LineChart
        :data="((metric.data || []) as any) as Array<{ timestamp: number; value: number }>"
        :title="metric.name"
        width="100%"
        height="180px"
      />
    </div>

    <!-- 对象列表类型 -->
    <div v-else-if="metric.data_type === DataType.ObjectList" class="object-list-wrapper">
      <h3>{{ metric.name }}</h3>
      <div class="object-list">
        <div v-for="item in (metric.value as ObjectItem[] || [])" :key="item.key" class="object-item">
          <span class="obj-key">{{ item.key }}</span>
          <span class="obj-value">{{ item.value }}</span>
        </div>
      </div>
    </div>

    <!-- 单值类型 (string / number) -->
    <div v-else class="single-value-wrapper">
      <SingleValueDisplay :metric="metric as any" width="180px" height="90px" />
    </div>

  </div>

  <div class="metric-card metric-loading" v-else>
    <span>加载中: {{ metricId }}</span>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, onUnmounted, inject } from 'vue'
// import { metricsApi } from '../api/metrics.ts'
import { DataType, SaveMode } from '../types.ts'
import type { MetricItem, ObjectItem, DataPoint } from '../types.ts'
import SingleValueDisplay from './SingleValueDisplay.vue'
import LineChart from './LineChart.vue'

const props = defineProps<{
  metricId: string
}>()

// ─── 从 App.vue 注入 ─────────────────────────────────────────────────────────

const register = inject<(id: string) => void>('register')!
const unregister = inject<(id: string) => void>('unregister')!
const metricMetaMap = inject<Record<string, MetricItem>>('metricMetaMap')!
const metricDataMap = inject<Record<string, any>>('metricDataMap')!

// ─── 响应式组装：元数据 + 真实数据 → 完整 metric ─────────────────────────────

const metric = computed<MetricItem | null>(() => {
  const meta = metricMetaMap[props.metricId]
  if (!meta) return null

  return {
    ...meta,
    // series 模式数据在 metricDataMap 中是 DataPoint[]，其它模式是 value
    ...(meta.save_mode === SaveMode.Series
      ? { data: metricDataMap[props.metricId] as DataPoint[] | undefined }
      : { value: metricDataMap[props.metricId] }),
  }
})

// ─── 操作 ─────────────────────────────────────────────────────────────────────

// const onPersistChange = async () => {
//   if (!metric.value) return
//   const newPersist = !metric.value.persist
//   try {
//     // await metricsApi.togglePersist(props.metricId, newPersist)
//     metricMetaMap[props.metricId].persist = newPersist
//   } catch (error) {
//     console.error('切换持久化失败:', error)
//   }
// }

// ─── 生命周期 ─────────────────────────────────────────────────────────────────

onMounted(() => {
  register(props.metricId)
})

onUnmounted(() => {
  unregister(props.metricId)
})
</script>

<style scoped>
.metric-card {
  background: white;
  border-radius: 8px;
  padding: 16px;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
  min-width: 200px;
  position: relative;
}

.metric-loading {
  display: flex;
  align-items: center;
  justify-content: center;
  color: #999;
  font-size: 14px;
  min-height: 80px;
}

.chart-wrapper h3 {
  margin: 0 0 12px 0;
  font-size: 16px;
  color: #333;
}

.object-list-wrapper h3 {
  margin: 0 0 12px 0;
  font-size: 16px;
  color: #333;
}

.object-list {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.object-item {
  display: flex;
  justify-content: space-between;
  padding: 4px 8px;
  background: #f5f7fa;
  border-radius: 4px;
}

.obj-key {
  font-weight: 600;
  color: #606266;
}

.obj-value {
  color: #409EFF;
  font-weight: 500;
}

.single-value-wrapper {
  margin-bottom: 12px;
}

.card-actions {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: 8px;
}

.persist-label {
  font-size: 12px;
  color: #666;
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 4px;
}

.delete-btn {
  padding: 4px 8px;
  background: #ff4d4f;
  color: white;
  border: none;
  border-radius: 4px;
  font-size: 12px;
  cursor: pointer;
}

.delete-btn:hover {
  background: #ff1a1a;
}
</style>
