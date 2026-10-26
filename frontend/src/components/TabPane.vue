<template>
  <div class="tab-pane" v-show="visible">
    <slot />
  </div>
</template>

<script setup lang="ts">
import { inject, computed } from 'vue'

const props = defineProps<{
  name: string
  label: string
}>()

const activeTab = inject<{ value: string }>('tabs:active')!

const visible = computed(() => activeTab.value === props.name)
</script>
