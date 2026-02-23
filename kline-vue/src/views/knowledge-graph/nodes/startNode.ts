import type { Node } from '../types'
import type { NodeRenderer, NodeRendererOptions, NodeRenderResult } from './base'
import { ensureShadowFilter, createBaseNodeGroup, renderNodePorts, type PortConfig } from './base'
import { getNodeWidth } from '../graphUtils'

/**
 * 开始节点渲染器
 * 特点：浅灰色背景 + 深灰色边框 + 左上角三个彩色方块 + 右上角蓝色对勾图标 + 大号文字
 */
export const renderStartNode: NodeRenderer = (
  node: Node,
  options: NodeRendererOptions
): NodeRenderResult => {
  const { defs, nodeGroup } = options

  // 确保阴影滤镜存在
  ensureShadowFilter(defs)

  // 创建基础节点组
  const nodeElement = createBaseNodeGroup(node, nodeGroup)

  // 创建节点背景（浅灰色 + 深灰色边框）
  const nodeWidth = getNodeWidth(node.label)
  nodeElement.append('rect')
    .attr('width', nodeWidth)
    .attr('height', 40)
    .attr('x', -nodeWidth / 2)
    .attr('y', -20)
    .attr('rx', 6)
    .attr('ry', 6)
    .attr('fill', '#f5f5f5') // 浅灰色背景
    .attr('stroke', '#666666') // 深灰色边框
    .attr('stroke-width', 1.5)
    .attr('opacity', 0.98)
    .attr('filter', 'url(#node-shadow)')

  // 左上角：三个小方块（水平排列）
  const leftOffset = -nodeWidth / 2 + 6
  const topOffset = -20 + 6
  const squareSize = 8
  const squareSpacing = 4

  // 紫色方块
  nodeElement.append('rect')
    .attr('x', leftOffset)
    .attr('y', topOffset)
    .attr('width', squareSize)
    .attr('height', squareSize)
    .attr('fill', '#9b59b6') // 紫色
    .attr('rx', 1)

  // 红棕色方块
  nodeElement.append('rect')
    .attr('x', leftOffset + squareSize + squareSpacing)
    .attr('y', topOffset)
    .attr('width', squareSize)
    .attr('height', squareSize)
    .attr('fill', '#8b4513') // 红棕色（maroon）
    .attr('rx', 1)

  // 青绿色方块
  nodeElement.append('rect')
    .attr('x', leftOffset + (squareSize + squareSpacing) * 2)
    .attr('y', topOffset)
    .attr('width', squareSize)
    .attr('height', squareSize)
    .attr('fill', '#20b2aa') // 青绿色（teal）
    .attr('rx', 1)

  // 右上角：蓝色圆角方块 + 白色对勾
  const rightOffset = nodeWidth / 2 - 18
  const checkBoxSize = 14
  const checkBoxCenterX = rightOffset + checkBoxSize / 2
  const checkBoxCenterY = topOffset + checkBoxSize / 2
  
  // 蓝色圆角方块
  nodeElement.append('rect')
    .attr('x', rightOffset)
    .attr('y', topOffset)
    .attr('width', checkBoxSize)
    .attr('height', checkBoxSize)
    .attr('fill', '#1890ff') // 蓝色
    .attr('rx', 3)
    .attr('ry', 3)

  // 白色对勾图标（使用 SVG path 绘制，居中显示）
  nodeElement.append('path')
    .attr('d', `M ${checkBoxCenterX - 4} ${checkBoxCenterY} L ${checkBoxCenterX - 1} ${checkBoxCenterY + 3} L ${checkBoxCenterX + 4} ${checkBoxCenterY - 2}`)
    .attr('stroke', '#ffffff')
    .attr('stroke-width', 2)
    .attr('stroke-linecap', 'round')
    .attr('stroke-linejoin', 'round')
    .attr('fill', 'none')

  // 创建节点文本（大号深色文字）
  nodeElement.append('text')
    .attr('x', 0)
    .attr('y', 5)
    .attr('text-anchor', 'middle')
    .attr('font-size', '15px') // 更大的字体
    .attr('font-weight', '500')
    .attr('fill', '#333333')
    .text(() => {
      const maxChars = Math.floor((getNodeWidth(node.label) - 20) / 16)
      return node.label.length > maxChars ? node.label.substring(0, maxChars - 1) + '...' : node.label
    })
    .style('user-select', 'none')

  // 定义端口配置
  // 开始节点：没有输入端口（因为是根节点），只有输出端口
  const portConfig: PortConfig = {
    inputPorts: [], // 开始节点不需要输入
    outputPorts: [
      { x: nodeWidth / 2, y: 0, visible: false } // 右侧中间，不显示圆圈但用于连线
    ]
  }

  // 渲染端口
  renderNodePorts(nodeElement, portConfig)

  return { nodeElement, portConfig }
}

