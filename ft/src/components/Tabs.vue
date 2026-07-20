<template>
  <div class="tabs">
    <div class="tab-bar">
      <div
        v-for="tab in tabList"
        :key="tab.name"
        class="tab-item"
        :class="{ active: modelValue === tab.name }"
        @click="modelValue = tab.name"
      >
        {{ tab.label }}
      </div>
    </div>
    <div class="tab-content">
      <slot />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, provide, useSlots, watch } from 'vue'

const props = defineProps<{
  modelValue: string
}>()

const emit = defineEmits<{
  'update:modelValue': [value: string]
}>()

const modelValue = ref(props.modelValue)

watch(() => props.modelValue, (v) => { modelValue.value = v })
watch(modelValue, (v) => { emit('update:modelValue', v) })

// 从 slot 中收集 TabPane 的 name 和 label
const slots = useSlots()

const tabList = ref<{ name: string; label: string }[]>([])

function collectTabs() {
  const children = slots.default?.() || []
  const list: { name: string; label: string }[] = []
  for (const vnode of children) {
    const p = vnode.props
    if (p && p.name && p.label) {
      list.push({ name: p.name, label: p.label })
    }
  }
  tabList.value = list
}

collectTabs()

// 提供给 TabPane 的响应式 activeTab
const activeTab = ref(modelValue.value)
watch(modelValue, (v) => { activeTab.value = v })
provide('tabs:active', activeTab)
</script>

<style scoped>
.tab-bar {
  display: flex;
  background: white;
  border-bottom: 1px solid #e4e7ed;
  padding: 0 20px;
}

.tab-item {
  padding: 12px 24px;
  cursor: pointer;
  font-size: 14px;
  color: #606266;
  border-bottom: 2px solid transparent;
  transition: all 0.2s;
  user-select: none;
}

.tab-item:hover {
  color: #409EFF;
}

.tab-item.active {
  color: #409EFF;
  border-bottom-color: #409EFF;
  font-weight: 500;
}

.tab-content {
  padding: 20px;
}
</style>
