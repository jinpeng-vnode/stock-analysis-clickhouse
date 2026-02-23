import * as d3 from 'd3'
import type { Node, GraphData } from './types'
import { buildHierarchy, calculateTreeLayout } from './graphUtils'
import { renderNodes, setNodePortConfig, getNodeRenderer } from './nodes'
import { renderLinks, type LinkData } from './nodes/link'

export interface RendererContext {
  svg: d3.Selection<SVGSVGElement, unknown, null, undefined> | null
  zoom: d3.ZoomBehavior<SVGElement, unknown> | null
  container: d3.Selection<SVGGElement, unknown, null, undefined> | null
  link: d3.Selection<SVGLineElement, LinkData, SVGGElement, unknown> | null
  linkLabels: d3.Selection<SVGTextElement, LinkData, SVGGElement, unknown> | null
  linkLabelBgs: d3.Selection<SVGRectElement, LinkData, SVGGElement, unknown> | null
  node: d3.Selection<SVGGElement, Node, SVGGElement, unknown> | null
}

let context: RendererContext = {
  svg: null,
  zoom: null,
  container: null,
  link: null,
  linkLabels: null,
  linkLabelBgs: null,
  node: null
}

// 保存已渲染的节点位置信息
let renderedNodesMap = new Map<string, Node>()
let renderedLinksMap = new Map<string, LinkData>()

// 初始化图表
export const initGraph = (svgElement: SVGSVGElement, graphData: GraphData) => {
  if (!svgElement) return

  // 清空之前的图表
  d3.select(svgElement).selectAll('*').remove()

  // 设置 SVG 尺寸
  const width = svgElement.clientWidth || 1200
  const height = svgElement.clientHeight || 800

  context.svg = d3.select(svgElement)
    .attr('width', width)
    .attr('height', height)

  // 创建容器组（用于缩放和平移）
  context.container = context.svg.append('g').attr('class', 'container')

  // 创建缩放行为
  context.zoom = d3.zoom<SVGElement, unknown>()
    .scaleExtent([0.1, 4])
    .on('zoom', (event) => {
      if (context.container) {
        context.container.attr('transform', event.transform.toString())
      }
    })

  context.svg.call(context.zoom as any)

  // 创建 defs（用于箭头标记等）
  const defs = context.container.append('defs')

  // 构建层次树
  const root = buildHierarchy(graphData)
  if (!root) return

  // 计算布局
  const { allNodes, links: layoutLinks } = calculateTreeLayout(root, width, height)

  // 先渲染节点（这样端口配置会被保存）
  context.node = renderNodes(allNodes, defs, context.container)

  // 为连线添加标签，转换为 LinkData 格式
  const linksWithLabels: LinkData[] = layoutLinks.map(layoutLink => {
    const relation = graphData.links.find(l => {
      const sourceId = typeof l.source === 'string' ? l.source : (l.source as Node).id
      const targetId = typeof l.target === 'string' ? l.target : (l.target as Node).id
      return sourceId === layoutLink.source.id && targetId === layoutLink.target.id
    })
    return {
      source: layoutLink.source,
      target: layoutLink.target,
      label: relation?.label || ''
    }
  })

  // 为连线分配端口索引（根据连线顺序自动分配）
  const sourcePortUsage = new Map<string, number>() // 记录每个源节点已使用的输出端口数
  const targetPortUsage = new Map<string, number>() // 记录每个目标节点已使用的输入端口数
  
  linksWithLabels.forEach(link => {
    // 分配源节点输出端口索引
    const sourceKey = link.source.id
    const sourceIndex = sourcePortUsage.get(sourceKey) || 0
    link.sourcePortIndex = sourceIndex
    sourcePortUsage.set(sourceKey, sourceIndex + 1)
    
    // 分配目标节点输入端口索引
    const targetKey = link.target.id
    const targetIndex = targetPortUsage.get(targetKey) || 0
    link.targetPortIndex = targetIndex
    targetPortUsage.set(targetKey, targetIndex + 1)
  })

  // 创建连线组
  const linkGroup = context.container.append('g').attr('class', 'links')
  
  // 使用连线模块渲染连线（节点已渲染，端口配置已保存）
  const { linkElements, labelElements, labelBgElements } = renderLinks(
    linksWithLabels,
    defs,
    linkGroup
  )
  
  context.link = linkElements
  context.linkLabels = labelElements
  context.linkLabelBgs = labelBgElements

  // 添加鼠标悬停效果（统一处理）
  context.node.on('mouseover', function(_event, d) {
    const nodeElement = d3.select(this)
    const rect = nodeElement.select('rect')
    const currentStrokeWidth = d.id === 'main' ? 2 : 1.5
    rect.attr('opacity', 1).attr('stroke-width', currentStrokeWidth + 1)
    // 轻微放大效果
    nodeElement
      .transition()
      .duration(200)
      .attr('transform', `translate(${d.x || 0},${d.y || 0}) scale(1.02)`)
    // 高亮相关连线
    if (context.link) {
      context.link.attr('stroke-opacity', l => {
        return (l.source.id === d.id || l.target.id === d.id) ? 0.9 : 0.15
      })
    }
    if (context.linkLabels) {
      context.linkLabels.attr('opacity', l => {
        return (l.source.id === d.id || l.target.id === d.id) ? 1 : 0.2
      })
    }
    if (context.linkLabelBgs) {
      context.linkLabelBgs.attr('opacity', (_bg, i) => {
        const linkData = linksWithLabels[i]
        return (linkData.source.id === d.id || linkData.target.id === d.id) ? 1 : 0.2
      })
    }
  })
  .on('mouseout', function(_event, d) {
    const nodeElement = d3.select(this)
    const rect = nodeElement.select('rect')
    const currentStrokeWidth = d.id === 'main' ? 2 : 1.5
    rect.attr('opacity', 0.98).attr('stroke-width', currentStrokeWidth)
    // 恢复原始大小
    nodeElement
      .transition()
      .duration(200)
      .attr('transform', `translate(${d.x || 0},${d.y || 0})`)
    // 恢复所有连线的正常显示（已显示的保持显示）
    if (context.link) {
      context.link.attr('stroke-opacity', (_l, i) => {
        const linkData = linksWithLabels[i]
        // 检查这个连线是否已经通过动画显示过
        return linkData.source.x !== undefined && linkData.target.x !== undefined ? 0.7 : 0
      })
    }
    if (context.linkLabels) {
      context.linkLabels.attr('opacity', (_l, i) => {
        const linkData = linksWithLabels[i]
        return linkData.source.x !== undefined && linkData.target.x !== undefined ? 1 : 0
      })
    }
    if (context.linkLabelBgs) {
      context.linkLabelBgs.attr('opacity', (_bg, i) => {
        const linkData = linksWithLabels[i]
        return linkData.source.x !== undefined && linkData.target.x !== undefined ? 1 : 0
      })
    }
  })

  // 保存已渲染的节点和连线信息
  renderedNodesMap.clear()
  renderedLinksMap.clear()
  allNodes.forEach(node => {
    renderedNodesMap.set(node.id, { ...node })
  })
  linksWithLabels.forEach(link => {
    const key = `${link.source.id}-${link.target.id}`
    renderedLinksMap.set(key, link)
  })

  // 开始动画
  animateNodes(allNodes, linksWithLabels)

  // 初始化完成后，聚焦到第一个节点（主节点或第一个节点）
  // 优先查找主节点，如果没有则使用第一个节点
  // 对于从左到右的布局，使用 alignLeft=true 将节点放在左侧，右侧留出更多空间
  const firstNode = allNodes.find(node => node.id === 'main') || allNodes[0]
  if (firstNode && firstNode.x !== undefined && firstNode.y !== undefined) {
    // 延迟一下，确保节点位置已经计算完成并且节点映射已经保存
    // 延迟 200ms 以确保初始化完成
    setTimeout(() => {
      focusOnNode(firstNode.id, true) // 使用 alignLeft=true 让节点偏左显示
    }, 200)
  }
}

// 平滑更新布局 - 重新计算所有节点位置并平滑移动
export const updateLayoutSmoothly = (svgElement: SVGSVGElement, graphData: GraphData): boolean => {
  if (!svgElement || !context.container || !context.svg) {
    return false
  }

  const width = svgElement.clientWidth || 1200
  const height = svgElement.clientHeight || 800

  // 重新构建层次树并计算布局
  const root = buildHierarchy(graphData)
  if (!root) return false

  const { allNodes, links: layoutLinks } = calculateTreeLayout(root, width, height)

  // 为连线添加标签，转换为 LinkData 格式
  const linksWithLabels: LinkData[] = layoutLinks.map(layoutLink => {
    const relation = graphData.links.find(l => {
      const sourceId = typeof l.source === 'string' ? l.source : (l.source as Node).id
      const targetId = typeof l.target === 'string' ? l.target : (l.target as Node).id
      return sourceId === layoutLink.source.id && targetId === layoutLink.target.id
    })
    return {
      source: layoutLink.source,
      target: layoutLink.target,
      label: relation?.label || ''
    }
  })

  // 为连线分配端口索引（根据连线顺序自动分配）
  const sourcePortUsage = new Map<string, number>()
  const targetPortUsage = new Map<string, number>()
  
  linksWithLabels.forEach(link => {
    const sourceKey = link.source.id
    const sourceIndex = sourcePortUsage.get(sourceKey) || 0
    link.sourcePortIndex = sourceIndex
    sourcePortUsage.set(sourceKey, sourceIndex + 1)
    
    const targetKey = link.target.id
    const targetIndex = targetPortUsage.get(targetKey) || 0
    link.targetPortIndex = targetIndex
    targetPortUsage.set(targetKey, targetIndex + 1)
  })

  // 获取节点组和连线组
  let nodeGroup = context.container.select('g.nodes')
  if (nodeGroup.empty()) {
    nodeGroup = context.container.append('g').attr('class', 'nodes')
  }

  let linkGroup = context.container.select('g.links')
  if (linkGroup.empty()) {
    linkGroup = context.container.append('g').attr('class', 'links')
  }

  // 获取 defs
  let defs = context.container.select('defs')
  if (defs.empty()) {
    defs = context.container.append('defs')
  }

  // 更新节点选择器 - 使用数据绑定
  const nodeSelection = nodeGroup.selectAll<SVGGElement, Node>('g.node')
    .data(allNodes, (d: Node) => d.id)

  // 处理新节点 - 创建节点元素
  const newNodeSelection = nodeSelection.enter()
    .append('g')
    .datum((d: Node) => d)
    .attr('class', d => {
      const nodeType = d.id === 'main' ? 'start' : 
                       d.status === 'clear' ? 'conclusion' :
                       d.status === 'pending' ? 'search' : 'missing'
      return `node node-${nodeType}`
    })
    .attr('transform', (d: Node) => `translate(${d.x || 0},${d.y || 0})`)
    .attr('opacity', 0)

  // 为新节点渲染内容（包括端口）
  // 创建一个临时节点组用于渲染
  const tempNodeGroup = nodeGroup.append('g').attr('class', 'temp-nodes')
  newNodeSelection.each(function(d) {
    const targetElement = d3.select(this)
    
    // 使用节点渲染器渲染到临时组
    const nodeType = d.id === 'main' ? 'start' : 
                     d.status === 'clear' ? 'conclusion' :
                     d.status === 'pending' ? 'search' : 'missing'
    const renderer = getNodeRenderer(nodeType)
    const result = renderer(d, {
      defs,
      nodeGroup: tempNodeGroup
    })
    
    // 将渲染的内容复制到目标元素
    const renderedElement = result.nodeElement.node()
    if (renderedElement) {
      Array.from(renderedElement.children).forEach(child => {
        targetElement.node()?.appendChild(child.cloneNode(true))
      })
      // 移除临时渲染的元素
      d3.select(renderedElement).remove()
    }
    
    // 保存端口配置
    if (result.portConfig) {
      setNodePortConfig(d.id, result.portConfig)
    }
  })
  // 移除临时节点组
  tempNodeGroup.remove()

  // 合并已有节点和新节点，更新所有节点位置
  const allNodeElements = nodeSelection.merge(newNodeSelection)

  // 平滑移动所有节点到新位置
  allNodeElements
    .transition()
    .duration(600)
    .ease(d3.easeCubicOut)
    .attr('transform', (d: Node) => `translate(${d.x || 0},${d.y || 0})`)
    .attr('opacity', 1)

  // 使用连线模块更新连线
  const { linkElements, labelElements, labelBgElements } = renderLinks(
    linksWithLabels,
    defs,
    linkGroup
  )

  // 平滑更新连线位置
  linkElements
    .transition()
    .duration(600)
    .ease(d3.easeCubicOut)
    .attr('stroke-opacity', 0.7)

  labelElements
    .transition()
    .duration(600)
    .ease(d3.easeCubicOut)
    .attr('opacity', 1)

  labelBgElements
    .transition()
    .duration(600)
    .ease(d3.easeCubicOut)
    .attr('opacity', 1)

  // 更新选择器引用
  context.node = nodeGroup.selectAll<SVGGElement, Node>('g.node')
  context.link = linkElements
  context.linkLabels = labelElements
  context.linkLabelBgs = labelBgElements

  // 重新绑定交互事件（为新节点）
  context.node.on('mouseover', function(_event, d) {
    const nodeElement = d3.select(this)
    const rect = nodeElement.select('rect')
    const currentStrokeWidth = d.id === 'main' ? 2 : 1.5
    rect.attr('opacity', 1).attr('stroke-width', currentStrokeWidth + 1)
    nodeElement
      .transition()
      .duration(200)
      .attr('transform', `translate(${d.x || 0},${d.y || 0}) scale(1.02)`)
    
    if (context.link) {
      context.link.attr('stroke-opacity', l => {
        return (l.source.id === d.id || l.target.id === d.id) ? 0.9 : 0.15
      })
    }
    if (context.linkLabels) {
      context.linkLabels.attr('opacity', l => {
        return (l.source.id === d.id || l.target.id === d.id) ? 1 : 0.2
      })
    }
    if (context.linkLabelBgs) {
      context.linkLabelBgs.attr('opacity', (_bg, i) => {
        const linkData = linksWithLabels[i]
        return linkData && (linkData.source.id === d.id || linkData.target.id === d.id) ? 1 : 0.2
      })
    }
  })
  .on('mouseout', function(_event, d) {
    const nodeElement = d3.select(this)
    const rect = nodeElement.select('rect')
    const currentStrokeWidth = d.id === 'main' ? 2 : 1.5
    rect.attr('opacity', 0.98).attr('stroke-width', currentStrokeWidth)
    nodeElement
      .transition()
      .duration(200)
      .attr('transform', `translate(${d.x || 0},${d.y || 0})`)
    
    if (context.link) {
      context.link.attr('stroke-opacity', 0.7)
    }
    if (context.linkLabels) {
      context.linkLabels.attr('opacity', 1)
    }
    if (context.linkLabelBgs) {
      context.linkLabelBgs.attr('opacity', 1)
    }
  })

  // 更新已渲染节点映射
  renderedNodesMap.clear()
  renderedLinksMap.clear()
  allNodes.forEach(node => {
    renderedNodesMap.set(node.id, { ...node })
  })
  linksWithLabels.forEach(link => {
    const key = `${link.source.id}-${link.target.id}`
    renderedLinksMap.set(key, link)
  })

  return true
}

// 增量添加节点 - 重新计算布局并平滑移动所有节点
export const addNode = (svgElement: SVGSVGElement, graphData: GraphData): boolean => {
  return updateLayoutSmoothly(svgElement, graphData)
}

// 动画：按照深度逐步显示节点和连线
const animateNodes = (
  allNodes: Node[],
  links: LinkData[]
) => {
  // 按深度分组节点
  const nodesByDepth = new Map<number, Node[]>()
  allNodes.forEach(node => {
    const depth = node.depth || 0
    if (!nodesByDepth.has(depth)) {
      nodesByDepth.set(depth, [])
    }
    nodesByDepth.get(depth)!.push(node)
  })

  // 按深度顺序逐步显示
  const depths = Array.from(nodesByDepth.keys()).sort((a, b) => a - b)
  
  depths.forEach((depth, depthIndex) => {
    setTimeout(() => {
      const nodesAtDepth = nodesByDepth.get(depth) || []
      
      // 显示这一层的节点
      nodesAtDepth.forEach((nodeData, nodeIndex) => {
        if (!context.node) return
        const nodeElement = context.node.filter((d: Node) => d.id === nodeData.id)
        
        nodeElement
          .transition()
          .duration(400)
          .delay(nodeIndex * 150)
          .attr('opacity', 1)
          .attr('transform', (d: Node) => {
            const scale = 1
            return `translate(${d.x || 0},${d.y || 0}) scale(${scale})`
          })
          .on('end', function() {
            // 节点显示后，显示连接到它的连线
            const connectedLinks = links.filter(l => 
              l.target.id === nodeData.id || (depth === 0 && l.source.id === nodeData.id)
            )
            
            connectedLinks.forEach((linkData, linkIndex) => {
              if (!context.link || !context.linkLabels || !context.linkLabelBgs) return
              
              const linkElement = context.link.filter((_l, i) => links[i] === linkData)
              const labelElement = context.linkLabels.filter((_l, i) => links[i] === linkData)
              const labelBgElement = context.linkLabelBgs.filter((_bg, i) => links[i] === linkData)
              
              setTimeout(() => {
                linkElement
                  .transition()
                  .duration(300)
                  .attr('stroke-opacity', 0.7)
                
                labelElement
                  .transition()
                  .duration(300)
                  .attr('opacity', 1)
                
                labelBgElement
                  .transition()
                  .duration(300)
                  .attr('opacity', 1)
              }, linkIndex * 100)
            })
          })
      })
    }, depthIndex * 800)
  })
}

// 重置缩放
export const resetZoom = () => {
  if (context.svg && context.zoom) {
    context.svg.transition()
      .duration(750)
      .call(context.zoom.transform as any, d3.zoomIdentity)
  }
}

// 聚焦到指定节点
export const focusOnNode = (nodeId: string, alignLeft: boolean = false) => {
  if (!context.svg || !context.zoom || !context.container) {
    return
  }

  // 从已渲染的节点映射中查找节点数据
  let nodeData = renderedNodesMap.get(nodeId)
  
  // 如果映射中没有，尝试从节点选择器中查找
  if (!nodeData && context.node) {
    const nodeArray = context.node.data() as Node[]
    nodeData = nodeArray.find((d: Node) => d.id === nodeId)
  }
  
  if (!nodeData || nodeData.x === undefined || nodeData.y === undefined) {
    return
  }

  // 获取 SVG 尺寸
  const svgElement = context.svg.node()
  if (!svgElement) return
  
  const width = svgElement.clientWidth || 1200
  const height = svgElement.clientHeight || 800

  // 计算节点在画布上的位置
  const nodeX = nodeData.x
  const nodeY = nodeData.y

  // 考虑当前的缩放级别
  const currentTransform = d3.zoomTransform(svgElement)
  
  // 如果 alignLeft 为 true，将节点放在视图左侧约 1/4 位置（适合从左到右的布局）
  // 否则居中显示
  const targetX = alignLeft 
    ? width * 0.25 - nodeX * currentTransform.k  // 左侧 1/4 位置
    : width / 2 - nodeX * currentTransform.k     // 居中
  const targetY = height / 2 - nodeY * currentTransform.k

  // 创建新的变换，保持当前缩放级别，只改变平移
  const newTransform = d3.zoomIdentity
    .translate(targetX, targetY)
    .scale(currentTransform.k)

  // 平滑动画到新位置
  context.svg.transition()
    .duration(750)
    .ease(d3.easeCubicOut)
    .call(context.zoom.transform as any, newTransform)
}

