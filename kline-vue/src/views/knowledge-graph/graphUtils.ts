import * as d3 from 'd3'
import type { Node, GraphData } from './types'

// 节点颜色映射
export const nodeColorMap: Record<string, string> = {
  missing: '#ff4d4f', // 红色 - 信息缺失
  clear: '#52c41a',   // 绿色 - 结论明确
  pending: '#1890ff'  // 蓝色 - 结论待完善
}

// 判断是否为根节点（主节点）
export const isRootNode = (d: Node) => d.id === 'main'

// 构建层次树结构
export const buildHierarchy = (graphData: GraphData): Node | null => {
  const nodeMap = new Map<string, Node>()
  graphData.nodes.forEach(node => {
    nodeMap.set(node.id, { ...node, children: [] })
  })

  // 找到根节点
  const rootNode = nodeMap.get('main')
  if (!rootNode) return null

  // 构建父子关系
  graphData.links.forEach(link => {
    const sourceId = typeof link.source === 'string' ? link.source : (link.source as Node).id
    const targetId = typeof link.target === 'string' ? link.target : (link.target as Node).id
    
    const sourceNode = nodeMap.get(sourceId)
    const targetNode = nodeMap.get(targetId)
    
    if (sourceNode && targetNode) {
      if (!sourceNode.children) {
        sourceNode.children = []
      }
      if (!sourceNode.children.find((n: Node) => n.id === targetNode.id)) {
        sourceNode.children.push(targetNode)
        targetNode.parent = sourceNode
      }
    }
  })

  return rootNode
}

// 简单的哈希函数，用于根据节点ID生成稳定的随机数
const hashString = (str: string): number => {
  let hash = 0
  for (let i = 0; i < str.length; i++) {
    const char = str.charCodeAt(i)
    hash = ((hash << 5) - hash) + char
    hash = hash & hash // 转换为32位整数
  }
  return Math.abs(hash)
}

// 计算树布局
export const calculateTreeLayout = (
  root: Node,
  _width: number, // 不使用画布宽度
  _height: number // 不使用画布高度
): { allNodes: Node[], links: Array<{ source: Node, target: Node, label: string }> } => {
  // 使用 D3 层次布局
  const hierarchy = d3.hierarchy(root)
  
  // 基础间距配置（像素），实际间距会有随机变化
  const baseHorizontalSpacing = 250 // 水平方向（左右）节点基础间距
  const baseVerticalSpacing = 120  // 垂直方向（上下）节点基础间距
  
  // 使用 nodeSize 设置基础节点间距（不限制整体大小，让它自然扩展）
  // nodeSize 的参数顺序是 [height, width]，对应垂直间距和水平间距
  // 因为树布局是垂直方向的，所以第一个参数是垂直间距，第二个是水平间距
  const treeLayout = d3.tree<Node>()
    .nodeSize([baseVerticalSpacing, baseHorizontalSpacing]) // [垂直间距, 水平间距]
    .separation((a: any, b: any) => {
      // 兄弟节点之间的间距比例，添加一些随机性
      // 基础间距是 1.0，随机变化范围在 0.85 到 1.15 之间
      const hashA = hashString(a.data.id || '')
      const hashB = hashString(b.data.id || '')
      const combinedHash = (hashA + hashB) % 1000
      const ratio = 0.85 + (combinedHash / 1000) * 0.3 // 0.85 到 1.15
      return ratio
    })

  const treeData = treeLayout(hierarchy)

  // 根据节点ID生成随机偏移量
  // vertical: true 表示垂直方向，可以双向移动；false 表示水平方向，只能向右移动
  const getRandomOffset = (nodeId: string, maxOffset: number, vertical: boolean = true): number => {
    const hash = hashString(nodeId)
    // 使用哈希值生成 0 到 1 之间的值
    const normalized = (hash % 1000) / 1000
    
    if (vertical) {
      // 垂直方向：可以上下移动，范围在 -maxOffset 到 +maxOffset 之间
      return (normalized * 2 - 1) * maxOffset
    } else {
      // 水平方向：只能向右移动，范围在 0 到 +maxOffset 之间
      // 避免向左移动导致与左侧节点重合
      return normalized * maxOffset
    }
  }

  // 将所有节点收集到一个数组中，并设置坐标
  const allNodes: Node[] = []
  treeData.each((d: any) => {
    const node = d.data as Node
    const baseX = d.y // 树布局中 x 和 y 是交换的
    const baseY = d.x
    
    // 根据深度设置不同的随机偏移范围
    // 根节点偏移小一些，子节点偏移大一些
    const depth = d.depth || 0
    const horizontalOffsetRange = depth === 0 ? 30 : 60  // 水平方向偏移范围（只向右）
    const verticalOffsetRange = depth === 0 ? 20 : 40   // 垂直方向偏移范围（可以上下）
    
    // 添加随机偏移量
    // 水平方向只向右移动，避免与左侧节点重合
    const randomOffsetX = getRandomOffset(node.id, horizontalOffsetRange, false)
    // 垂直方向可以上下移动
    const randomOffsetY = getRandomOffset(node.id + '_y', verticalOffsetRange, true)
    
    node.x = baseX + randomOffsetX
    node.y = baseY + randomOffsetY
    node.depth = depth
    allNodes.push(node)
  })

  // 生成连线数据
  const links: Array<{ source: Node, target: Node, label: string }> = []
  
  treeData.links().forEach((link: any) => {
    const source = link.source.data as Node
    const target = link.target.data as Node
    links.push({
      source,
      target,
      label: '' // 标签将在 renderer 中设置
    })
  })

  return { allNodes, links }
}

// 计算节点宽度（根据文本长度）
export const getNodeWidth = (text: string): number => {
  const chineseChars = (text.match(/[\u4e00-\u9fa5]/g) || []).length
  const otherChars = text.length - chineseChars
  const width = chineseChars * 14 + otherChars * 8 + 20
  return Math.max(120, Math.min(width, 300))
}

