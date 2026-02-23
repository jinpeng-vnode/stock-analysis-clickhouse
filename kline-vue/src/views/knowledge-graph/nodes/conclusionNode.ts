import * as d3 from 'd3'
import type { Node } from '../types'
import type { NodeRenderer, NodeRendererOptions, NodeRenderResult } from './base'
import { ensureShadowFilter, createBaseNodeGroup, renderNodeText, renderStatusIndicator, renderNodePorts, type PortConfig } from './base'
import { getNodeWidth } from '../graphUtils'

/**
 * 结论节点渲染器
 * 特点：绿色背景 + 白色文字 + 左上角绿色状态指示器
 */
export const renderConclusionNode: NodeRenderer = (
  node: Node,
  options: NodeRendererOptions
): NodeRenderResult => {
  const { defs, nodeGroup } = options

  // 确保阴影滤镜存在
  ensureShadowFilter(defs)

  // 创建基础节点组
  const nodeElement = createBaseNodeGroup(node, nodeGroup)

  // 创建节点背景（绿色）
  const nodeWidth = getNodeWidth(node.label)
  nodeElement.append('rect')
    .attr('width', nodeWidth)
    .attr('height', 40)
    .attr('x', -nodeWidth / 2)
    .attr('y', -20)
    .attr('rx', 6)
    .attr('ry', 6)
    .attr('fill', '#52c41a') // 绿色背景
    .attr('stroke', '#fff')
    .attr('stroke-width', 1.5)
    .attr('opacity', 0.98)
    .attr('filter', 'url(#node-shadow)')

  // 创建状态指示器（左上角绿色小方块）
  nodeElement.append('rect')
    .attr('x', -nodeWidth / 2 + 4)
    .attr('y', -20 + 4)
    .attr('width', 8)
    .attr('height', 8)
    .attr('fill', '#52c41a')
    .attr('stroke', '#fff')
    .attr('stroke-width', 1)
    .attr('rx', 1.5)

  // 创建节点文本（白色文字）
  nodeElement.append('text')
    .attr('x', 0)
    .attr('y', 5)
    .attr('text-anchor', 'middle')
    .attr('font-size', '13px')
    .attr('font-weight', '500')
    .attr('fill', '#fff')
    .text(() => {
      const maxChars = Math.floor((getNodeWidth(node.label) - 20) / 14)
      return node.label.length > maxChars ? node.label.substring(0, maxChars - 1) + '...' : node.label
    })
    .style('user-select', 'none')

  // 定义端口配置
  // 输入端口：左侧，一个在中间
  // 输出端口：右侧，一个在中间
  const portConfig: PortConfig = {
    inputPorts: [
      { x: -nodeWidth / 2, y: 0, visible: false } // 左侧中间，不显示圆圈但用于连线
    ],
    outputPorts: [
      { x: nodeWidth / 2, y: 0, visible: false } // 右侧中间，不显示圆圈但用于连线
    ]
  }

  // 渲染端口
  renderNodePorts(nodeElement, portConfig)

  return { nodeElement, portConfig }
}

