import * as d3 from 'd3'
import type { Node } from '../types'
import type { NodeRenderer, NodeRendererOptions, NodeRenderResult } from './base'
import { ensureShadowFilter, createBaseNodeGroup, renderNodeText, renderNodePorts, type PortConfig } from './base'
import { getNodeWidth } from '../graphUtils'

/**
 * 结束节点渲染器
 * 特点：灰色背景 + 深色文字 + 可自定义样式
 */
export const renderEndNode: NodeRenderer = (
  node: Node,
  options: NodeRendererOptions
): NodeRenderResult => {
  const { defs, nodeGroup } = options

  // 确保阴影滤镜存在
  ensureShadowFilter(defs)

  // 创建基础节点组
  const nodeElement = createBaseNodeGroup(node, nodeGroup)

  // 创建节点背景（灰色）
  const nodeWidth = getNodeWidth(node.label)
  nodeElement.append('rect')
    .attr('width', nodeWidth)
    .attr('height', 40)
    .attr('x', -nodeWidth / 2)
    .attr('y', -20)
    .attr('rx', 6)
    .attr('ry', 6)
    .attr('fill', '#d9d9d9') // 灰色背景
    .attr('stroke', '#999')
    .attr('stroke-width', 1.5)
    .attr('opacity', 0.98)
    .attr('filter', 'url(#node-shadow)')

  // 结束节点不显示状态指示器

  // 创建节点文本（深色文字）
  nodeElement.append('text')
    .attr('x', 0)
    .attr('y', 5)
    .attr('text-anchor', 'middle')
    .attr('font-size', '13px')
    .attr('font-weight', '500')
    .attr('fill', '#333')
    .text(() => {
      const maxChars = Math.floor((getNodeWidth(node.label) - 20) / 14)
      return node.label.length > maxChars ? node.label.substring(0, maxChars - 1) + '...' : node.label
    })
    .style('user-select', 'none')

  // 定义端口配置
  // 结束节点：只有输入端口，没有输出端口
  const portConfig: PortConfig = {
    inputPorts: [
      { x: -nodeWidth / 2, y: 0, visible: false } // 左侧中间，不显示圆圈但用于连线
    ],
    outputPorts: [] // 结束节点不需要输出
  }

  // 渲染端口
  renderNodePorts(nodeElement, portConfig)

  return { nodeElement, portConfig }
}

