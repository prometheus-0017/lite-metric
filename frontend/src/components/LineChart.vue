<template>
  <div ref="chartContainer" class="line-chart-container"></div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, watch, nextTick } from 'vue'
import * as echarts from 'echarts'

interface DataPoint {
  timestamp: number
  value: number
}

interface MarkAreaItem {
  start: number
  end: number
}

const props = defineProps({
  data: {
    type: Array as () => DataPoint[],
    required: true,
    default: () => []
  },
  title: {
    type: String,
    default: ''
  },
  width: {
    type: String,
    default: '100%'
  },
  height: {
    type: String,
    default: '200px'
  },
  markAreas: {
    type: Array as () => MarkAreaItem[],
    default: () => []
  }
})

const chartContainer = ref<HTMLDivElement | null>(null)
let chartInstance: echarts.ECharts | null = null
let resizeObserver: ResizeObserver | null = null

const initChart = () => {
  if (!chartContainer.value) return
  
  // DOM 尺寸为 0 时不初始化，等待 ResizeObserver 触发
  const el = chartContainer.value
  if (el.clientWidth === 0 || el.clientHeight === 0) return
  
  // 销毁现有实例
  if (chartInstance) {
    chartInstance.dispose()
  }
  
  chartInstance = echarts.init(chartContainer.value)
  
  const option = {
    animation: false,
    title: {
      text: props.title,
      textStyle: {
        fontSize: 14,
        fontWeight: 'bold'
      },
      left: 'center',
      top: 8
    },
    tooltip: {
      trigger: 'axis',
      backgroundColor: 'rgba(0, 0, 0, 0.8)',
      borderColor: '#333',
      borderRadius: 4,
      textStyle: {
        color: '#fff'
      }
    },
    grid: {
      left: 20,
      right: 10,
      top: 30,
      bottom: 20,
      containLabel: true
    },
    xAxis: {
      type: 'time',
      axisLabel: {
        fontSize: 10,
        formatter: (value: string | number) => {
          const date = new Date(value)
          return date.toLocaleTimeString()
        }
      },
      axisLine: {
        lineStyle: {
          color: '#ccc'
        }
      },
      splitLine: {
        show: false
      }
    },
    yAxis: {
      type: 'value',
      axisLabel: {
        fontSize: 10
      },
      axisLine: {
        show: false
      },
      splitLine: {
        lineStyle: {
          color: '#eee'
        }
      }
    },
    series: [{
      type: 'line',
      smooth: true,
      symbol: 'circle',
      symbolSize: 4,
      lineStyle: {
        width: 2,
        color: '#409EFF'
      },
      itemStyle: {
        color: '#409EFF'
      },
      areaStyle: {
        color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
          { offset: 0, color: 'rgba(64, 158, 255, 0.3)' },
          { offset: 1, color: 'rgba(64, 158, 255, 0.05)' }
        ])
      },
      data: props.data.map(item => [item.timestamp * 1000, item.value])
    }],
    markArea: {
      silent: true,
      label: {
        show: false
      },
      itemStyle: {
        color: 'rgba(255, 193, 7, 0.1)'
      },
      data: props.markAreas.map(area => [
        { xAxis: area.start * 1000 },
        { xAxis: area.end * 1000 }
      ])
    }
  }
  
  chartInstance.setOption(option)
}

// 监听数据变化
watch(() => props.data, () => {
  nextTick(() => initChart())
  console.log('inited chart')
}, { deep: true })

// 监听窗口大小变化
const resizeChart = () => {
  if (chartInstance) {
    chartInstance.resize()
  }
}

onMounted(() => {
  nextTick(() => initChart())
  window.addEventListener('resize', resizeChart)

  // 监听容器尺寸变化（Tab 切换等场景）
  if (chartContainer.value) {
    resizeObserver = new ResizeObserver(() => {
      if (chartInstance) {
        chartInstance.resize()
      } else {
        // 容器从无尺寸变为有尺寸时，重新初始化
        initChart()
      }
    })
    resizeObserver.observe(chartContainer.value)
  }
})

onUnmounted(() => {
  if (resizeObserver) {
    resizeObserver.disconnect()
    resizeObserver = null
  }
  if (chartInstance) {
    chartInstance.dispose()
  }
  window.removeEventListener('resize', resizeChart)
})
</script>

<style scoped>
.line-chart-container {
  width: v-bind(width);
  height: v-bind(height);
  min-height: 100px;
}
</style>