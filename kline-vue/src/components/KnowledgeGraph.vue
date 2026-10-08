<template>
  <div class="knowledge-graph-wrapper">
    <div class="graph-container">
      <svg ref="svgRef" class="knowledge-graph-svg"></svg>
      <GraphLegend />
    </div>
  </div>
</template>

<script setup>
import { ref, watch, onMounted, onUnmounted, nextTick } from 'vue'
import { initGraph, resetZoom as resetZoomView } from '@/views/knowledge-graph/graphRenderer'

const props = defineProps({
  graphData: {
    type: Object,
    required: true,
    validator: (value) => {
      return value && Array.isArray(value.nodes) && Array.isArray(value.links)
    }
  }
})

const svgRef = ref(null)

// 重置缩放
const resetZoom = () => {
  resetZoomView()
}

// 窗口大小改变时重新初始化
const handleResize = () => {
  if (svgRef.value && props.graphData) {
    setTimeout(() => {
      initChart()
    }, 100)
  }
}

// 初始化图表
const initChart = () => {
  if (!svgRef.value || !props.graphData) return
  
  // 获取容器尺寸
  const viewContainer = svgRef.value.closest('.knowledge-graph-view')
  const wrapper = svgRef.value.closest('.knowledge-graph-wrapper')
  const container = viewContainer || wrapper || svgRef.value.parentElement
  
  let width = 800
  let height = 400
  
  if (container) {
    const rect = container.getBoundingClientRect()
    width = rect.width || container.clientWidth || 800
    height = rect.height || container.clientHeight || 400
  }
  
  // 确保有有效尺寸
  if (width <= 0 || height <= 0) {
    width = 800
    height = 400
  }
  
  // 设置 SVG 尺寸
  svgRef.value.setAttribute('width', width)
  svgRef.value.setAttribute('height', height)
  
  // 初始化图表
  initGraph(svgRef.value, props.graphData)
}

// 监听数据变化，重新渲染
watch(() => props.graphData, (newData) => {
  if (newData && svgRef.value) {
    nextTick(() => {
      setTimeout(() => {
        initChart()
      }, 100)
    })
  }
}, { deep: true })

onMounted(() => {
  if (svgRef.value && props.graphData) {
    nextTick(() => {
      setTimeout(() => {
        initChart()
      }, 100)
    })
  }
  window.addEventListener('resize', handleResize)
})

onUnmounted(() => {
  window.removeEventListener('resize', handleResize)
})

defineExpose({
  resetZoom
})
</script>

<style scoped lang="less">
.knowledge-graph-wrapper {
  width: 100%;
  height: 100%;
  min-height: 400px;
  position: relative;
  display: block;
}

.graph-container {
  width: 100%;
  height: 100%;
  min-height: 400px;
  position: relative;
  background: #fafafa;
  border-radius: 4px;
  overflow: hidden;
  display: block;
}

.knowledge-graph-svg {
  width: 100% !important;
  height: 100% !important;
  min-width: 600px;
  min-height: 400px;
  display: block;
  cursor: grab;

  &:active {
    cursor: grabbing;
  }
}

// 节点样式
:deep(.node) {
  cursor: pointer;
}

// 连线标签样式
:deep(.link-label) {
  font-size: 11px;
  background: rgba(255, 255, 255, 0.9);
  padding: 2px 6px;
  border-radius: 3px;
  pointer-events: none;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
}
</style>

