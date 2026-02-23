// 知识图谱类型定义

// 节点类型枚举
export type NodeType = 'start' | 'end' | 'conclusion' | 'search' | 'missing'

export interface Node {
  id: string
  label: string
  status: 'missing' | 'clear' | 'pending' // 信息缺失、结论明确、结论待完善
  type?: NodeType // 节点类型（可选，用于覆盖默认类型推断）
  x?: number
  y?: number
  depth?: number
  parent?: Node | null
  children?: Node[]
}

export interface Link {
  source: string | Node
  target: string | Node
  label: string
}

export interface GraphData {
  nodes: Node[]
  links: Link[]
}

