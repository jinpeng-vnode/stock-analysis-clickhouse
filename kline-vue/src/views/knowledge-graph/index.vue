<template>
  <div class="knowledge-graph-container">
    <!-- 工具栏 -->
    <a-card title="节点工具" :bordered="false" class="toolbar-card">
      <div class="toolbar-content">
        <div class="toolbar-section">
          <span class="section-title">模拟节点：</span>
          <a-space wrap>
            <a-button 
              v-for="template in nodeTemplates" 
              :key="template.id"
              @click="addNodeFromTemplate(template)"
              size="small"
              type="default"
            >
              {{ template.label }}
            </a-button>
          </a-space>
        </div>
        <div class="toolbar-section">
          <a-space>
            <a-button @click="addRandomNode" size="small" type="dashed">
              添加随机节点
            </a-button>
            <a-button @click="clearAllNodes" size="small" danger>
              清空所有节点
            </a-button>
          </a-space>
        </div>
        <div class="toolbar-section">
          <a-checkbox v-model:checked="autoFocusOnAdd">
            添加节点时自动聚焦
          </a-checkbox>
        </div>
      </div>
    </a-card>

    <a-card title="知识图谱可视化" :bordered="false">
      <template #extra>
        <a-button @click="resetZoom" size="small">重置视图</a-button>
      </template>

      <div class="graph-wrapper">
        <!-- SVG 容器 -->
        <svg ref="svgRef" class="knowledge-graph-svg"></svg>
        
        <!-- 图例 -->
        <GraphLegend />
      </div>
    </a-card>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'
import { message } from 'ant-design-vue'
import GraphLegend from './components/GraphLegend.vue'
import { initGraph, resetZoom as resetZoomView, updateLayoutSmoothly, focusOnNode } from './graphRenderer'
import type { GraphData, Node } from './types'

// SVG 引用
const svgRef = ref<SVGSVGElement>()

// 自动聚焦配置
const autoFocusOnAdd = ref<boolean>(false)

// 示例数据 - 基于玉马科技的分析，按照生成顺序排列
const graphData = ref<GraphData>({
  nodes: [
    {
      id: 'main',
      label: '今天可以买玉马科技吗',
      status: 'pending'
    },
    {
      id: 'price',
      label: '玉马科技股票今日股价是多少？',
      status: 'missing'
    },
    {
      id: 'finance',
      label: '玉马科技最新财务报告摘要',
      status: 'clear'
    },
    {
      id: 'performance',
      label: '玉马科技股票近期表现分析',
      status: 'clear'
    },
    {
      id: 'news',
      label: '玉马科技最新市场新闻',
      status: 'pending'
    },
    {
      id: 'rating',
      label: '分析师评级',
      status: 'pending'
    },
    {
      id: 'q3-report',
      label: '2025年第三季度财务报告',
      status: 'clear'
    },
    {
      id: 'q3-key',
      label: '第三季度关键指标',
      status: 'clear'
    },
    {
      id: 'price-query',
      label: '股价查询',
      status: 'missing'
    },
    {
      id: 'financial-forecast',
      label: '财务预测',
      status: 'clear'
    }
  ],
  links: [
    { source: 'main', target: 'price', label: '直接相关' },
    { source: 'main', target: 'finance', label: '直接相关' },
    { source: 'main', target: 'performance', label: '影响' },
    { source: 'main', target: 'news', label: '影响' },
    { source: 'main', target: 'rating', label: '影响' },
    { source: 'finance', target: 'q3-report', label: '包含' },
    { source: 'q3-report', target: 'q3-key', label: '包含' },
    { source: 'price', target: 'price-query', label: '提供信息' },
    { source: 'finance', target: 'financial-forecast', label: '财务预测' }
  ]
})

// 节点模板 - 用于快速添加模拟节点
const nodeTemplates = ref<Node[]>([
  {
    id: 'template-1',
    label: '技术指标分析',
    status: 'clear'
  },
  {
    id: 'template-2',
    label: '行业对比分析',
    status: 'clear'
  },
  {
    id: 'template-3',
    label: '市场情绪分析',
    status: 'pending'
  },
  {
    id: 'template-4',
    label: '资金流向分析',
    status: 'clear'
  },
  {
    id: 'template-5',
    label: '风险评估',
    status: 'missing'
  },
  {
    id: 'template-6',
    label: '投资建议',
    status: 'pending'
  }
])

// 关系标签选项
const relationLabels = ['相关', '影响', '包含', '提供信息', '基于', '依赖', '支持', '反对']

// 生成唯一ID
let nodeIdCounter = 1000
const generateNodeId = () => {
  return `node-${Date.now()}-${nodeIdCounter++}`
}

// 从模板添加节点
const addNodeFromTemplate = (template: Node) => {
  const newNode: Node = {
    id: generateNodeId(),
    label: template.label,
    status: template.status
  }

  // 添加到节点列表
  graphData.value.nodes.push(newNode)

  // 连接到主节点（如果存在）
  const mainNode = graphData.value.nodes.find(n => n.id === 'main')
  let sourceId = 'main'
  if (!mainNode) {
    // 如果没有主节点，连接到最后一个节点
    const lastNode = graphData.value.nodes[graphData.value.nodes.length - 2]
    if (lastNode) {
      sourceId = lastNode.id
    } else {
      message.error('无法添加节点：没有可连接的节点')
      return
    }
  }

  const randomLabel = relationLabels[Math.floor(Math.random() * relationLabels.length)]
  const newLink = {
    source: sourceId,
    target: newNode.id,
    label: randomLabel
  }
  
  graphData.value.links.push(newLink)

  // 平滑更新布局 - 重新计算所有节点位置并平滑移动
  if (svgRef.value) {
    const success = updateLayoutSmoothly(svgRef.value, graphData.value)
    if (success) {
      message.success(`已添加节点：${newNode.label}`)
      // 如果启用自动聚焦，聚焦到新添加的节点
      if (autoFocusOnAdd.value) {
        // 延迟一下，确保节点位置已经更新
        setTimeout(() => {
          focusOnNode(newNode.id)
        }, 650) // 等待动画完成（600ms）后再聚焦
      }
    } else {
      // 如果更新失败，回退到完全重新初始化
      console.warn('平滑更新失败，回退到完全重新初始化')
      refreshGraph()
      message.success(`已添加节点：${newNode.label}`)
      // 如果启用自动聚焦，聚焦到新添加的节点
      if (autoFocusOnAdd.value) {
        setTimeout(() => {
          focusOnNode(newNode.id)
        }, 100)
      }
    }
  } else {
    refreshGraph()
    message.success(`已添加节点：${newNode.label}`)
    // 如果启用自动聚焦，聚焦到新添加的节点
    if (autoFocusOnAdd.value) {
      setTimeout(() => {
        focusOnNode(newNode.id)
      }, 100)
    }
  }
}

// 添加随机节点
const addRandomNode = () => {
  const randomLabels = [
    '随机分析节点1',
    '随机分析节点2',
    '随机分析节点3',
    '数据挖掘结果',
    'AI分析结果',
    '市场趋势预测',
    '技术面分析',
    '基本面分析'
  ]
  const randomStatuses: Array<'missing' | 'clear' | 'pending'> = ['missing', 'clear', 'pending']
  
  const newNode: Node = {
    id: generateNodeId(),
    label: randomLabels[Math.floor(Math.random() * randomLabels.length)],
    status: randomStatuses[Math.floor(Math.random() * randomStatuses.length)]
  }

  graphData.value.nodes.push(newNode)

  // 随机连接到现有节点
  if (graphData.value.nodes.length > 1) {
    const existingNodes = graphData.value.nodes.filter(n => n.id !== newNode.id)
    const randomSource = existingNodes[Math.floor(Math.random() * existingNodes.length)]
    const randomLabel = relationLabels[Math.floor(Math.random() * relationLabels.length)]
    
    const newLink = {
      source: randomSource.id,
      target: newNode.id,
      label: randomLabel
    }
    
    graphData.value.links.push(newLink)

    // 平滑更新布局 - 重新计算所有节点位置并平滑移动
    if (svgRef.value) {
      const success = updateLayoutSmoothly(svgRef.value, graphData.value)
      if (success) {
        message.success(`已添加随机节点：${newNode.label}`)
        // 如果启用自动聚焦，聚焦到新添加的节点
        if (autoFocusOnAdd.value) {
          // 延迟一下，确保节点位置已经更新
          setTimeout(() => {
            focusOnNode(newNode.id)
          }, 650) // 等待动画完成（600ms）后再聚焦
        }
      } else {
        // 如果更新失败，回退到完全重新初始化
        console.warn('平滑更新失败，回退到完全重新初始化')
        refreshGraph()
        message.success(`已添加随机节点：${newNode.label}`)
        // 如果启用自动聚焦，聚焦到新添加的节点
        if (autoFocusOnAdd.value) {
          setTimeout(() => {
            focusOnNode(newNode.id)
          }, 100)
        }
      }
    } else {
      refreshGraph()
      message.success(`已添加随机节点：${newNode.label}`)
      // 如果启用自动聚焦，聚焦到新添加的节点
      if (autoFocusOnAdd.value) {
        setTimeout(() => {
          focusOnNode(newNode.id)
        }, 100)
      }
    }
  } else {
    refreshGraph()
    message.success(`已添加随机节点：${newNode.label}`)
    // 如果启用自动聚焦，聚焦到新添加的节点
    if (autoFocusOnAdd.value) {
      setTimeout(() => {
        focusOnNode(newNode.id)
      }, 100)
    }
  }
}

// 清空所有节点（保留主节点）
const clearAllNodes = () => {
  const mainNode = graphData.value.nodes.find(n => n.id === 'main')
  if (mainNode) {
    graphData.value.nodes = [mainNode]
    graphData.value.links = []
  } else {
    graphData.value.nodes = []
    graphData.value.links = []
  }
  
  refreshGraph()
  message.success('已清空所有节点（保留主节点）')
}

// 刷新图表
const refreshGraph = () => {
  if (svgRef.value) {
    // 使用 setTimeout 确保 DOM 更新完成
    setTimeout(() => {
      initGraph(svgRef.value!, graphData.value)
    }, 50)
  }
}

// 重置缩放
const resetZoom = () => {
  resetZoomView()
  message.success('视图已重置')
}

// 窗口大小改变时重新初始化
const handleResize = () => {
  if (svgRef.value) {
    initGraph(svgRef.value, graphData.value)
  }
}

onMounted(() => {
  if (svgRef.value) {
    initGraph(svgRef.value, graphData.value)
  }
  window.addEventListener('resize', handleResize)
})

onUnmounted(() => {
  window.removeEventListener('resize', handleResize)
})
</script>

<style scoped lang="less">
.knowledge-graph-container {
  padding: 16px;
  height: 100vh;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  gap: 16px;

  .toolbar-card {
    flex-shrink: 0;
    
    .toolbar-content {
      display: flex;
      flex-wrap: wrap;
      gap: 16px;
      align-items: center;
      
      .toolbar-section {
        display: flex;
        align-items: center;
        gap: 8px;
        
        .section-title {
          font-weight: 500;
          color: #666;
          white-space: nowrap;
        }
      }
    }
  }

  :deep(.ant-card) {
    display: flex;
    flex-direction: column;
    
    &:not(.toolbar-card) {
      flex: 1;
      min-height: 0;
    }
  }

  :deep(.ant-card-body) {
    flex: 1;
    overflow: hidden;
    display: flex;
    flex-direction: column;
  }
}

.graph-wrapper {
  flex: 1;
  position: relative;
  background: #fafafa;
  border-radius: 4px;
  overflow: hidden;
}

.knowledge-graph-svg {
  width: 100%;
  height: 100%;
  cursor: grab;

  &:active {
    cursor: grabbing;
  }
}

// 节点样式
:deep(.node) {
  cursor: pointer;
  // 移除CSS transform，使用SVG原生transform避免冲突
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
