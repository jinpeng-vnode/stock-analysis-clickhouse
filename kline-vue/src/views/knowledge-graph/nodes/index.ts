import * as d3 from 'd3'
import type { Node, NodeType } from '../types'
import type { NodeRenderer, NodeRendererOptions, NodeRenderResult } from './base'
import { inferNodeType } from './base'
import { renderStartNode } from './startNode'
import { renderConclusionNode } from './conclusionNode'
import { renderSearchNode } from './searchNode'
import { renderMissingNode } from './missingNode'
import { renderEndNode } from './endNode'

// 节点类型到渲染器的映射表
const nodeRenderers: Record<NodeType, NodeRenderer> = {
  start: renderStartNode,
  end: renderEndNode,
  conclusion: renderConclusionNode,
  search: renderSearchNode,
  missing: renderMissingNode
}

/**
 * 根据节点类型获取对应的渲染器
 */
export const getNodeRenderer = (nodeType: NodeType): NodeRenderer => {
  return nodeRenderers[nodeType] || renderConclusionNode // 默认使用结论节点渲染器
}

/**
 * 渲染单个节点
 * 根据节点类型自动调用对应的渲染器
 */
export const renderNode = (
  node: Node,
  options: NodeRendererOptions
): NodeRenderResult => {
  const nodeType = inferNodeType(node)
  const renderer = getNodeRenderer(nodeType)
  return renderer(node, options)
}

// 存储每个节点的端口配置（key: 节点ID, value: 端口配置）
const nodePortConfigs = new Map<string, import('./base').PortConfig>()

/**
 * 获取节点的端口配置
 */
export const getNodePortConfig = (nodeId: string): import('./base').PortConfig | undefined => {
  return nodePortConfigs.get(nodeId)
}

/**
 * 保存节点的端口配置（用于 updateLayoutSmoothly 中的新节点）
 */
export const setNodePortConfig = (nodeId: string, portConfig: import('./base').PortConfig) => {
  nodePortConfigs.set(nodeId, portConfig)
}

/**
 * 批量渲染节点
 */
export const renderNodes = (
  nodes: Node[],
  defs: d3.Selection<SVGDefsElement, unknown, null, undefined>,
  container: d3.Selection<SVGGElement, unknown, null, undefined>
): d3.Selection<SVGGElement, Node, SVGGElement, unknown> => {
  // 创建节点组
  const nodeGroup = container.append('g').attr('class', 'nodes')
  
  // 清空之前的端口配置
  nodePortConfigs.clear()
  
  // 为每个节点调用对应的渲染器
  nodes.forEach(node => {
    const result = renderNode(node, {
      defs,
      nodeGroup
    })
    
    // 保存端口配置
    if (result.portConfig) {
      nodePortConfigs.set(node.id, result.portConfig)
    }
  })

  // 返回所有节点元素的选择器
  return nodeGroup.selectAll<SVGGElement, Node>('g.node')
}

// 导出所有节点渲染器（方便外部扩展）
export {
  renderStartNode,
  renderEndNode,
  renderConclusionNode,
  renderSearchNode,
  renderMissingNode
}

// 导出类型推断函数
export { inferNodeType } from './base'

// 导出连线模块
export { renderLink, renderLinks, updateLinkPositions, type LinkData } from './link'

