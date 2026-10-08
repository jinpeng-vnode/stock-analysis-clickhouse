import { createRouter, createWebHistory } from 'vue-router'
import type { RouteRecordRaw } from 'vue-router'

const routes: RouteRecordRaw[] = [
  {
    path: '/',
    redirect: '/day'
  },
  {
    path: '/kline-analysis',
    name: 'KlineAnalysis',
    component: () => import('@/views/kline-analysis/index.vue'),
    meta: {
      title: '股票分析',
      showInMenu: true,
      icon: 'BarChartOutlined'
    }
  },
  //候选管理
  {
    path: '/candidate',
    name: 'Candidate',
    component: () => import('@/views/candidate/index.vue'),
    meta: {
      title: '候选管理',
      showInMenu: true,
      icon: 'UserOutlined'
    }
  },
  {
    path: '/stocke-info',
    name: 'StockInfo',
    component: () => import('@/views/stocke-info/index.vue'),
    meta: {
      title: '股票信息管理',
      showInMenu: true,
      icon: 'TableOutlined'
    }
  },
  
  {
    path: '/signal-analysis',
    name: 'SignalAnalysis',
    component: () => import('@/views/SignalAnalysisWithChart.vue'),
    meta: {
      title: '信号分析',
      showInMenu: true,
      icon: 'BarChartOutlined'
    }
  },
  {
    path: '/status',
    name: 'Status',
    component: () => import('@/views/status/index.vue'),
    meta: {
      title: '系统状态',
      showInMenu: true,
      icon: 'DashboardOutlined'
    }
  },
  {
    path: '/backtest',
    name: 'Backtest',
    component: () => import('@/views/backtest/index.vue'),
    meta: {
      title: '回测配置',
      showInMenu: true,
      icon: 'ExperimentOutlined'
    }
  },
  {
    path: '/backtest/results',
    name: 'BacktestResults',
    component: () => import('@/views/backtest/results.vue'),
    meta: {
      title: '回测结果',
      showInMenu: true,
      icon: 'BarChartOutlined'
    }
  },
  {
    path: '/flow',
    name: 'MoneyFlow',
    component: () => import('@/views/flow/index.vue'),
    meta: {
      title: '资金流向',
      showInMenu: true,
      icon: 'FundOutlined'
    }
  },
  {
    path: '/rule-hits',
    name: 'RuleHits',
    component: () => import('@/views/rule-hits/index.vue'),
    meta: {
      title: '规则命中',
      showInMenu: true,
      icon: 'TagsOutlined'
    }
  },
  {
    path: '/announcement',
    name: 'Announcement',
    component: () => import('@/views/announcement/index.vue'),
    meta: {
      title: '股票公告',
      showInMenu: true,
      icon: 'FileTextOutlined'
    }
  },
  {
    path: '/financial-report',
    name: 'FinancialReport',
    component: () => import('@/views/financial-report/index.vue'),
    meta: {
      title: '财报表',
      showInMenu: true,
      icon: 'AccountBookOutlined'
    }
  },
  {
    path: '/knowledge-graph',
    name: 'KnowledgeGraph',
    component: () => import('@/views/knowledge-graph/index.vue'),
    meta: {
      title: '知识图谱',
      showInMenu: true,
      icon: 'ClusterOutlined'
    }
  },
  {
    path: '/deepseek-api',
    name: 'DeepSeekApi',
    component: () => import('@/views/deepseek-api/index.vue'),
    meta: {
      title: 'DeepSeek API 包装器',
      showInMenu: true,
      icon: 'ApiOutlined'
    }
  },
  {
    path: '/deepseek-chat',
    name: 'DeepSeekChat',
    component: () => import('@/views/deepseek-chat/index.vue'),
    meta: {
      title: 'DeepSeek 股票分析',
      showInMenu: true,
      icon: 'RobotOutlined'
    }
  },
  {
    path: '/multi-stage-agent-debug',
    name: 'MultiStageAgentDebug',
    component: () => import('@/views/multi-stage-agent-debug/index.vue'),
    meta: {
      title: '多阶段Agent调试',
      showInMenu: true,
      icon: 'BugOutlined'
    }
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

// 路由守卫
router.beforeEach((to, _from, next) => {
  // 设置页面标题
  if (to.meta?.title) {
    document.title = `${to.meta.title} - K线图分析系统`
  }
  next()
})

export default router
