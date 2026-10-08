import * as d3 from 'd3'
import type { Node } from '../types'
import { getPortWorldPosition, type PortPosition } from './base'
import { getNodePortConfig } from './index'
import { getNodeWidth } from '../graphUtils'

// 节点高度（固定值）
const NODE_HEIGHT = 40

// 贝塞尔曲线控制点偏移量（用于控制曲线的弯曲程度）
const CURVE_OFFSET = 50

// 连线数据接口
export interface LinkData {
  source: Node
  target: Node
  label: string
  sourcePortIndex?: number // 源节点输出端口索引
  targetPortIndex?: number // 目标节点输入端口索引
}

// 连线渲染选项
export interface LinkRendererOptions {
  defs: d3.Selection<SVGDefsElement, unknown, null, undefined>
  linkGroup: d3.Selection<SVGGElement, unknown, null, undefined>
}

/**
 * 计算连线端点（使用端口位置）
 * @param linkData 连线数据
 * @returns 包含起点和终点坐标的对象
 */
const calculateLinkEndpoints = (
  linkData: LinkData
): { x1: number, y1: number, x2: number, y2: number } => {
  const { source, target, sourcePortIndex = 0, targetPortIndex = 0 } = linkData
  
  // 获取源节点的端口配置
  const sourcePortConfig = getNodePortConfig(source.id)
  // 确保有输出端口且索引有效
  let sourcePort: PortPosition | undefined
  if (sourcePortConfig?.outputPorts && sourcePortConfig.outputPorts.length > 0) {
    // 如果指定索引在范围内，使用指定索引的端口；否则使用第一个可用端口
    sourcePort = sourcePortConfig.outputPorts[sourcePortIndex] || sourcePortConfig.outputPorts[0]
  }
  
  // 获取目标节点的端口配置
  const targetPortConfig = getNodePortConfig(target.id)
  // 确保有输入端口且索引有效
  let targetPort: PortPosition | undefined
  if (targetPortConfig?.inputPorts && targetPortConfig.inputPorts.length > 0) {
    // 如果指定索引在范围内，使用指定索引的端口；否则使用第一个可用端口
    targetPort = targetPortConfig.inputPorts[targetPortIndex] || targetPortConfig.inputPorts[0]
  }
  
  // 如果端口存在，使用端口位置
  if (sourcePort && targetPort) {
    const sourcePos = getPortWorldPosition(source, sourcePort)
    const targetPos = getPortWorldPosition(target, targetPort)
    return {
      x1: sourcePos.x,
      y1: sourcePos.y,
      x2: targetPos.x,
      y2: targetPos.y
    }
  }
  
  // 如果只有一个端口存在，尝试使用它
  if (sourcePort) {
    const sourcePos = getPortWorldPosition(source, sourcePort)
    // 计算目标节点边缘的交点
    const targetX = target.x || 0
    const targetY = target.y || 0
    const targetWidth = getNodeWidth(target.label)
    const targetHalfWidth = targetWidth / 2
    return {
      x1: sourcePos.x,
      y1: sourcePos.y,
      x2: targetX - targetHalfWidth,
      y2: targetY
    }
  }
  
  if (targetPort) {
    const targetPos = getPortWorldPosition(target, targetPort)
    // 计算源节点边缘的交点
    const sourceX = source.x || 0
    const sourceY = source.y || 0
    const sourceWidth = getNodeWidth(source.label)
    const sourceHalfWidth = sourceWidth / 2
    return {
      x1: sourceX + sourceHalfWidth,
      y1: sourceY,
      x2: targetPos.x,
      y2: targetPos.y
    }
  }
  
  // 降级方案：计算节点边缘的交点
  const sourceX = source.x || 0
  const sourceY = source.y || 0
  const targetX = target.x || 0
  const targetY = target.y || 0
  
  // 计算两个节点中心之间的角度
  const dx = targetX - sourceX
  const dy = targetY - sourceY
  const angle = Math.atan2(dy, dx)
  
  // 获取节点宽度
  const sourceWidth = getNodeWidth(source.label)
  const targetWidth = getNodeWidth(target.label)
  
  const sourceHalfWidth = sourceWidth / 2
  const sourceHalfHeight = NODE_HEIGHT / 2
  const targetHalfWidth = targetWidth / 2
  const targetHalfHeight = NODE_HEIGHT / 2
  
  // 计算源节点右边缘的交点
  let x1: number, y1: number
  if (Math.abs(angle) < Math.PI / 4 || Math.abs(angle) > 3 * Math.PI / 4) {
    // 主要水平方向，使用右边缘
    x1 = sourceX + sourceHalfWidth
    y1 = sourceY + sourceHalfHeight * Math.tan(angle)
    // 限制在节点高度范围内
    if (y1 > sourceY + sourceHalfHeight) {
      y1 = sourceY + sourceHalfHeight
      x1 = sourceX + sourceHalfWidth
    } else if (y1 < sourceY - sourceHalfHeight) {
      y1 = sourceY - sourceHalfHeight
      x1 = sourceX + sourceHalfWidth
    }
  } else {
    // 主要垂直方向，使用上/下边缘
    y1 = sourceY + (dy > 0 ? sourceHalfHeight : -sourceHalfHeight)
    x1 = sourceX + sourceHalfWidth
  }
  
  // 计算目标节点左边缘的交点
  let x2: number, y2: number
  if (Math.abs(angle) < Math.PI / 4 || Math.abs(angle) > 3 * Math.PI / 4) {
    // 主要水平方向，使用左边缘
    x2 = targetX - targetHalfWidth
    y2 = targetY + targetHalfHeight * Math.tan(angle)
    // 限制在节点高度范围内
    if (y2 > targetY + targetHalfHeight) {
      y2 = targetY + targetHalfHeight
      x2 = targetX - targetHalfWidth
    } else if (y2 < targetY - targetHalfHeight) {
      y2 = targetY - targetHalfHeight
      x2 = targetX - targetHalfWidth
    }
  } else {
    // 主要垂直方向，使用上/下边缘
    y2 = targetY + (dy > 0 ? -targetHalfHeight : targetHalfHeight)
    x2 = targetX - targetHalfWidth
  }
  
  return { x1, y1, x2, y2 }
}

/**
 * 生成贝塞尔曲线路径
 * @param x1 起点x坐标
 * @param y1 起点y坐标
 * @param x2 终点x坐标
 * @param y2 终点y坐标
 * @returns SVG路径字符串
 */
const generateBezierPath = (
  x1: number,
  y1: number,
  x2: number,
  y2: number
): string => {
  // 计算控制点位置（在起点和终点之间的适当偏移）
  // 控制点1：从起点向右偏移
  const cp1x = x1 + CURVE_OFFSET
  const cp1y = y1
  
  // 控制点2：从终点向左偏移
  const cp2x = x2 - CURVE_OFFSET
  const cp2y = y2
  
  // 生成三次贝塞尔曲线路径
  return `M ${x1} ${y1} C ${cp1x} ${cp1y}, ${cp2x} ${cp2y}, ${x2} ${y2}`
}

/**
 * 计算贝塞尔曲线上的点位置（用于标签定位）
 * @param x1 起点x坐标
 * @param y1 起点y坐标
 * @param x2 终点x坐标
 * @param y2 终点y坐标
 * @param t 参数值（0-1之间，0.5表示中点）
 * @returns 曲线上对应点的坐标
 */
const getPointOnBezierCurve = (
  x1: number,
  y1: number,
  x2: number,
  y2: number,
  t: number = 0.5
): { x: number, y: number } => {
  // 计算控制点位置
  const cp1x = x1 + CURVE_OFFSET
  const cp1y = y1
  const cp2x = x2 - CURVE_OFFSET
  const cp2y = y2
  
  // 三次贝塞尔曲线公式：B(t) = (1-t)³P₀ + 3(1-t)²tP₁ + 3(1-t)t²P₂ + t³P₃
  const mt = 1 - t
  const mt2 = mt * mt
  const mt3 = mt2 * mt
  const t2 = t * t
  const t3 = t2 * t
  
  const x = mt3 * x1 + 3 * mt2 * t * cp1x + 3 * mt * t2 * cp2x + t3 * x2
  const y = mt3 * y1 + 3 * mt2 * t * cp1y + 3 * mt * t2 * cp2y + t3 * y2
  
  return { x, y }
}

/**
 * 渲染单个连线
 */
export const renderLink = (
  linkData: LinkData,
  options: LinkRendererOptions
): {
  linkElement: d3.Selection<SVGPathElement, LinkData, null, undefined>
  labelElement: d3.Selection<SVGTextElement, LinkData, null, undefined>
  labelBgElement: d3.Selection<SVGRectElement, LinkData, null, undefined>
} => {
  const { linkGroup } = options

  // 计算连线端点（使用端口位置）
  const { x1, y1, x2, y2 } = calculateLinkEndpoints(linkData)

  // 生成贝塞尔曲线路径
  const pathString = generateBezierPath(x1, y1, x2, y2)

  // 创建连线元素（使用path而不是line）
  const linkElement = linkGroup
    .append('path')
    .datum(linkData)
    .attr('d', pathString)
    .attr('fill', 'none')
    .attr('stroke', '#a8a8a8')
    .attr('stroke-width', 1.5)
    .attr('stroke-dasharray', '5,5')
    .attr('stroke-opacity', 0)

  // 计算标签位置（在贝塞尔曲线的中点）
  const labelPos = getPointOnBezierCurve(x1, y1, x2, y2, 0.5)

  // 创建连线标签背景
  const labelBgElement = linkGroup
    .append('rect')
    .datum(linkData)
    .attr('class', 'link-label-bg')
    .attr('rx', 3)
    .attr('ry', 3)
    .attr('fill', 'rgba(255, 255, 255, 0.95)')
    .attr('stroke', '#e0e0e0')
    .attr('stroke-width', 0.5)
    .attr('opacity', 0)
    .attr('x', labelPos.x - 20)
    .attr('y', labelPos.y - 8)
    .attr('width', 40)
    .attr('height', 16)

  // 创建连线标签文本
  const labelElement = linkGroup
    .append('text')
    .datum(linkData)
    .attr('class', 'link-label')
    .text(d => d.label)
    .attr('font-size', '11px')
    .attr('fill', '#666')
    .attr('text-anchor', 'middle')
    .attr('pointer-events', 'none')
    .style('user-select', 'none')
    .attr('opacity', 0)
    .attr('x', labelPos.x)
    .attr('y', labelPos.y + 4)

  // 根据文本长度调整背景框宽度
  const bbox = (labelElement.node() as SVGTextElement)?.getBBox()
  if (bbox) {
    const labelWidth = Math.max(bbox.width + 8, 30)
    labelBgElement
      .attr('width', labelWidth)
      .attr('x', labelPos.x - labelWidth / 2)
  }

  return { linkElement, labelElement, labelBgElement }
}

/**
 * 批量渲染连线
 */
export const renderLinks = (
  links: LinkData[],
  _defs: d3.Selection<SVGDefsElement, unknown, null, undefined>,
  linkGroup: d3.Selection<SVGGElement, unknown, null, undefined>
): {
  linkElements: d3.Selection<SVGPathElement, LinkData, SVGGElement, unknown>
  labelElements: d3.Selection<SVGTextElement, LinkData, SVGGElement, unknown>
  labelBgElements: d3.Selection<SVGRectElement, LinkData, SVGGElement, unknown>
} => {
  // 创建连线选择器（使用path而不是line）
  const linkSelection = linkGroup
    .selectAll<SVGPathElement, LinkData>('path.link-path')
    .data(links, d => `${d.source.id}-${d.target.id}`)

  // 创建标签背景选择器
  const labelBgSelection = linkGroup
    .selectAll<SVGRectElement, LinkData>('rect.link-label-bg')
    .data(links, d => `${d.source.id}-${d.target.id}`)

  // 创建标签文本选择器
  const labelSelection = linkGroup
    .selectAll<SVGTextElement, LinkData>('text.link-label')
    .data(links, d => `${d.source.id}-${d.target.id}`)

  // 处理进入的连线
  const linkEnter = linkSelection.enter()
    .append('path')
    .attr('class', 'link-path')
    .attr('fill', 'none')
    .attr('stroke', '#a8a8a8')
    .attr('stroke-width', 1.5)
    .attr('stroke-dasharray', '5,5')
    .attr('stroke-opacity', 0)

  // 处理进入的标签背景
  const labelBgEnter = labelBgSelection.enter()
    .append('rect')
    .attr('class', 'link-label-bg')
    .attr('rx', 3)
    .attr('ry', 3)
    .attr('fill', 'rgba(255, 255, 255, 0.95)')
    .attr('stroke', '#e0e0e0')
    .attr('stroke-width', 0.5)
    .attr('opacity', 0)

  // 处理进入的标签文本
  const labelEnter = labelSelection.enter()
    .append('text')
    .attr('class', 'link-label')
    .attr('font-size', '11px')
    .attr('fill', '#666')
    .attr('text-anchor', 'middle')
    .attr('pointer-events', 'none')
    .style('user-select', 'none')
    .attr('opacity', 0)
    .text(d => d.label)

  // 合并并更新所有连线路径
  const allLinks = linkSelection.merge(linkEnter)
  allLinks.each(function(d) {
    const { x1, y1, x2, y2 } = calculateLinkEndpoints(d)
    const pathString = generateBezierPath(x1, y1, x2, y2)
    d3.select(this).attr('d', pathString)
  })

  // 合并并更新所有标签背景坐标（使用贝塞尔曲线中点）
  const allLabelBgs = labelBgSelection.merge(labelBgEnter)
  allLabelBgs.each(function(d) {
    const { x1, y1, x2, y2 } = calculateLinkEndpoints(d)
    const labelPos = getPointOnBezierCurve(x1, y1, x2, y2, 0.5)
    d3.select(this)
      .attr('x', labelPos.x - 20)
      .attr('y', labelPos.y - 8)
      .attr('width', 40)
      .attr('height', 16)
  })

  // 合并并更新所有标签文本坐标（使用贝塞尔曲线中点）
  const allLabels = labelSelection.merge(labelEnter)
  allLabels.each(function(d) {
    const { x1, y1, x2, y2 } = calculateLinkEndpoints(d)
    const labelPos = getPointOnBezierCurve(x1, y1, x2, y2, 0.5)
    d3.select(this)
      .attr('x', labelPos.x)
      .attr('y', labelPos.y + 4)
  })

  // 根据文本长度调整背景框宽度
  allLabels.each(function(d) {
    const bbox = (this as SVGTextElement).getBBox()
    const bgElement = allLabelBgs.filter((_bg, i) => links[i] === d)
    if (!bgElement.empty()) {
      const { x1, y1, x2, y2 } = calculateLinkEndpoints(d)
      const labelPos = getPointOnBezierCurve(x1, y1, x2, y2, 0.5)
      const labelWidth = Math.max(bbox.width + 8, 30)
      bgElement
        .attr('width', labelWidth)
        .attr('x', labelPos.x - labelWidth / 2)
    }
  })

  // 移除退出的元素
  linkSelection.exit().remove()
  labelBgSelection.exit().remove()
  labelSelection.exit().remove()

  return {
    linkElements: allLinks,
    labelElements: allLabels,
    labelBgElements: allLabelBgs
  }
}

/**
 * 更新连线的位置（用于平滑过渡）
 */
export const updateLinkPositions = (
  linkElements: d3.Selection<SVGPathElement, LinkData, SVGGElement, unknown>,
  labelElements: d3.Selection<SVGTextElement, LinkData, SVGGElement, unknown>,
  labelBgElements: d3.Selection<SVGRectElement, LinkData, SVGGElement, unknown>,
  duration: number = 600
) => {
  // 更新连线路径（使用贝塞尔曲线）
  linkElements.each(function(d) {
    const { x1, y1, x2, y2 } = calculateLinkEndpoints(d)
    const pathString = generateBezierPath(x1, y1, x2, y2)
    d3.select(this)
      .transition()
      .duration(duration)
      .ease(d3.easeCubicOut)
      .attr('d', pathString)
  })

  // 更新标签位置（使用贝塞尔曲线中点）
  labelElements.each(function(d) {
    const { x1, y1, x2, y2 } = calculateLinkEndpoints(d)
    const labelPos = getPointOnBezierCurve(x1, y1, x2, y2, 0.5)
    d3.select(this)
      .transition()
      .duration(duration)
      .ease(d3.easeCubicOut)
      .attr('x', labelPos.x)
      .attr('y', labelPos.y + 4)
  })

  // 更新标签背景位置（使用贝塞尔曲线中点）
  labelBgElements.each(function(d) {
    const { x1, y1, x2, y2 } = calculateLinkEndpoints(d)
    const labelPos = getPointOnBezierCurve(x1, y1, x2, y2, 0.5)
    const bbox = (labelElements.filter((_l, i) => linkElements.data()[i] === d).node() as SVGTextElement)?.getBBox()
    const labelWidth = bbox ? Math.max(bbox.width + 8, 30) : 40
    
    d3.select(this)
      .transition()
      .duration(duration)
      .ease(d3.easeCubicOut)
      .attr('x', labelPos.x - labelWidth / 2)
      .attr('y', labelPos.y - 8)
      .attr('width', labelWidth)
  })
}

