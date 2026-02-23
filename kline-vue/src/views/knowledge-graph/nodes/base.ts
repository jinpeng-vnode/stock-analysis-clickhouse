import * as d3 from 'd3'
import type { Node, NodeType } from '../types'
import { getNodeWidth } from '../graphUtils'

// 节点渲染器接口
export interface NodeRendererOptions {
  defs: d3.Selection<SVGDefsElement, unknown, null, undefined>
  nodeGroup: d3.Selection<SVGGElement, Node, SVGGElement, unknown>
}

export interface NodeRenderResult {
  nodeElement: d3.Selection<SVGGElement, Node, SVGGElement, unknown>
  portConfig?: PortConfig // 端口配置（可选）
}

export type NodeRenderer = (
  node: Node,
  options: NodeRendererOptions
) => NodeRenderResult

// 创建阴影滤镜（如果不存在）
export const ensureShadowFilter = (
  defs: d3.Selection<SVGDefsElement, unknown, null, undefined>
) => {
  const existingFilter = defs.select('filter#node-shadow')
  if (!existingFilter.empty()) {
    return existingFilter
  }

  const shadowFilter = defs.append('filter')
    .attr('id', 'node-shadow')
    .attr('x', '-50%')
    .attr('y', '-50%')
    .attr('width', '200%')
    .attr('height', '200%')
  
  shadowFilter.append('feGaussianBlur')
    .attr('in', 'SourceAlpha')
    .attr('stdDeviation', 2)
  
  shadowFilter.append('feOffset')
    .attr('dx', 0)
    .attr('dy', 2)
    .attr('result', 'offsetblur')
  
  shadowFilter.append('feComponentTransfer')
    .append('feFuncA')
    .attr('type', 'linear')
    .attr('slope', 0.3)
  
  const feMerge = shadowFilter.append('feMerge')
  feMerge.append('feMergeNode')
  feMerge.append('feMergeNode')
    .attr('in', 'SourceGraphic')

  return shadowFilter
}

// 根据节点数据推断节点类型
export const inferNodeType = (node: Node): NodeType => {
  // 如果节点明确指定了类型，使用指定类型
  if (node.type) {
    return node.type
  }

  // 开始节点：id === 'main'
  if (node.id === 'main') {
    return 'start'
  }

  // 根据 status 推断类型
  switch (node.status) {
    case 'clear':
      return 'conclusion'
    case 'pending':
      return 'search'
    case 'missing':
      return 'missing'
    default:
      return 'conclusion' // 默认返回结论节点
  }
}

// 创建基础节点组（位置和透明度）
export const createBaseNodeGroup = (
  node: Node,
  nodeGroup: d3.Selection<SVGGElement, Node, SVGGElement, unknown>
): d3.Selection<SVGGElement, Node, SVGGElement, unknown> => {
  const nodeType = inferNodeType(node)
  const nodeElement = nodeGroup
    .append('g')
    .datum(node)
    .attr('class', `node node-${nodeType}`)
    .attr('transform', `translate(${node.x || 0},${node.y || 0})`)
    .attr('opacity', 0)
  
  return nodeElement as d3.Selection<SVGGElement, Node, SVGGElement, unknown>
}

// 渲染节点文本（通用）
export const renderNodeText = (
  nodeElement: d3.Selection<SVGGElement, Node, SVGGElement, unknown>,
  textColor: string
) => {
  nodeElement.append('text')
    .attr('x', 0)
    .attr('y', 5)
    .attr('text-anchor', 'middle')
    .attr('font-size', '13px')
    .attr('font-weight', '500')
    .attr('fill', textColor)
    .text(d => {
      const maxChars = Math.floor((getNodeWidth(d.label) - 20) / 14)
      return d.label.length > maxChars ? d.label.substring(0, maxChars - 1) + '...' : d.label
    })
    .style('user-select', 'none')
}

// 渲染状态指示器（左上角小方块）
export const renderStatusIndicator = (
  nodeElement: d3.Selection<SVGGElement, Node, SVGGElement, unknown>,
  color: string,
  show: boolean = true
) => {
  if (!show) return

  nodeElement.append('rect')
    .attr('x', d => -getNodeWidth(d.label) / 2 + 4)
    .attr('y', -20 + 4)
    .attr('width', 8)
    .attr('height', 8)
    .attr('fill', color)
    .attr('stroke', '#fff')
    .attr('stroke-width', 1)
    .attr('rx', 1.5)
}

// 端口位置接口（相对于节点中心）
export interface PortPosition {
  x: number // 相对于节点中心的x坐标
  y: number // 相对于节点中心的y坐标
  visible?: boolean // 是否显示端口圆圈（默认 true）
}

// 端口配置接口
export interface PortConfig {
  inputPorts: PortPosition[] // 输入端口位置列表（左侧）
  outputPorts: PortPosition[] // 输出端口位置列表（右侧）
}

// 端口大小
const PORT_RADIUS = 6

/**
 * 渲染单个端口
 */
const renderPort = (
  portGroup: d3.Selection<SVGGElement, unknown, null, undefined>,
  port: PortPosition,
  type: 'input' | 'output'
) => {
  // 外圈（白色背景 + 边框）
  portGroup
    .append('circle')
    .attr('cx', port.x)
    .attr('cy', port.y)
    .attr('r', PORT_RADIUS)
    .attr('fill', '#fff')
    .attr('stroke', type === 'input' ? '#52c41a' : '#1890ff')
    .attr('stroke-width', 2)
    .style('cursor', 'pointer')
    .style('pointer-events', 'all')

  // 内圈（填充色）
  portGroup
    .append('circle')
    .attr('cx', port.x)
    .attr('cy', port.y)
    .attr('r', PORT_RADIUS - 2)
    .attr('fill', type === 'input' ? '#52c41a' : '#1890ff')
    .attr('opacity', 0.3)
    .style('pointer-events', 'none')
}

/**
 * 渲染节点端口
 * @param nodeElement 节点元素
 * @param portConfig 端口配置
 */
export const renderNodePorts = (
  nodeElement: d3.Selection<SVGGElement, Node, SVGGElement, unknown>,
  portConfig: PortConfig
) => {
  const portGroup = nodeElement.append('g').attr('class', 'ports')

  // 渲染输入端口（左侧）- 只渲染 visible 不为 false 的端口
  portConfig.inputPorts.forEach(port => {
    if (port.visible !== false) {
      renderPort(portGroup, port, 'input')
    }
  })

  // 渲染输出端口（右侧）- 只渲染 visible 不为 false 的端口
  portConfig.outputPorts.forEach(port => {
    if (port.visible !== false) {
      renderPort(portGroup, port, 'output')
    }
  })
}

/**
 * 获取端口的世界坐标（相对于画布）
 */
export const getPortWorldPosition = (
  node: Node,
  port: PortPosition
): { x: number, y: number } => {
  return {
    x: (node.x || 0) + port.x,
    y: (node.y || 0) + port.y
  }
}

