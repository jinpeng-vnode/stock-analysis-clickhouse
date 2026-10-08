<template>
  <div class="status-page">
    <a-page-header
      title="系统状态"
      sub-title="股票分析系统运行状态监控"
      class="page-header"
    >
      <template #extra>
        <a-space>
          <a-button 
            type="primary" 
            :loading="loading"
            @click="refreshData"
          >
            <template #icon>
              <a-icon type="reload" />
            </template>
            刷新数据
          </a-button>
          <a-button 
            type="default" 
            :loading="optimizing"
            @click="optimizeTables"
          >
            <template #icon>
              <a-icon type="tool" />
            </template>
            优化表
          </a-button>
        </a-space>
      </template>
    </a-page-header>

    <div class="content">
      <!-- 基础统计信息 -->
      <a-row :gutter="[16, 16]" class="stats-cards">
        <a-col :span="6">
          <a-card class="stat-card">
            <a-statistic
              title="股票数量"
              :value="statsData.stocks"
              :loading="loading"
            >
              <template #prefix>
                <a-icon type="stock" style="color: #1890ff" />
              </template>
            </a-statistic>
          </a-card>
        </a-col>
        
        <a-col :span="6">
          <a-card class="stat-card">
            <a-statistic
              title="日K线记录数"
              :value="statsData.daily_records"
              :loading="loading"
            >
              <template #prefix>
                <a-icon type="bar-chart" style="color: #52c41a" />
              </template>
            </a-statistic>
          </a-card>
        </a-col>
        
        <a-col :span="6">
          <a-card class="stat-card">
            <a-statistic
              title="买入信号"
              :value="statsData.signals.buy_signals"
              :loading="loading"
            >
              <template #prefix>
                <a-icon type="rise" style="color: #f5222d" />
              </template>
            </a-statistic>
          </a-card>
        </a-col>
        
        <a-col :span="6">
          <a-card class="stat-card">
            <a-statistic
              title="卖出信号"
              :value="statsData.signals.sell_signals"
              :loading="loading"
            >
              <template #prefix>
                <a-icon type="fall" style="color: #52c41a" />
              </template>
            </a-statistic>
          </a-card>
        </a-col>
      </a-row>

      <!-- 数据范围和表大小信息 -->
      <a-row :gutter="[16, 16]" class="info-cards">
        <a-col :span="12">
          <a-card title="数据日期范围" class="info-card">
            <a-descriptions :column="1" size="small">
              <a-descriptions-item label="开始日期">
                {{ statsData.date_range.start || '暂无数据' }}
              </a-descriptions-item>
              <a-descriptions-item label="结束日期">
                {{ statsData.date_range.end || '暂无数据' }}
              </a-descriptions-item>
            </a-descriptions>
          </a-card>
        </a-col>
        
        <a-col :span="12">
          <a-card title="表大小信息" class="info-card">
            <a-descriptions :column="1" size="small">
              <a-descriptions-item 
                v-for="(size, table) in statsData.table_sizes" 
                :key="table"
                :label="table"
              >
                {{ size }}
              </a-descriptions-item>
            </a-descriptions>
          </a-card>
        </a-col>
      </a-row>

      <!-- 详细信息标签页 -->
      <a-card class="detail-card">
        <a-tabs v-model="activeTab" @change="handleTabChange">
          <a-tab-pane key="partitions" tab="分区信息">
            <a-table
              :columns="partitionColumns"
              :data-source="partitionData"
              :loading="loading"
              :pagination="false"
              size="small"
            />
          </a-tab-pane>
          
          <a-tab-pane key="performance" tab="性能统计">
            <a-row :gutter="[16, 16]">
              <a-col :span="12">
                <a-card title="查询统计" size="small">
                  <a-descriptions :column="1" size="small">
                    <a-descriptions-item label="总查询数">
                      {{ performanceData.query_stats.total_queries || 0 }}
                    </a-descriptions-item>
                    <a-descriptions-item label="平均耗时(ms)">
                      {{ performanceData.query_stats.avg_duration_ms || 0 }}
                    </a-descriptions-item>
                    <a-descriptions-item label="最大耗时(ms)">
                      {{ performanceData.query_stats.max_duration_ms || 0 }}
                    </a-descriptions-item>
                  </a-descriptions>
                </a-card>
              </a-col>
              
              <a-col :span="12">
                <a-card title="表查询统计" size="small">
                  <a-table
                    :columns="tableQueryColumns"
                    :data-source="performanceData.table_query_stats || []"
                    :pagination="false"
                    size="small"
                  />
                </a-card>
              </a-col>
            </a-row>
          </a-tab-pane>
        </a-tabs>
      </a-card>
    </div>
  </div>
</template>

<script>
import { getStats, getPartitions, getPerformance, optimizeTables } from '@/api/stocks'

export default {
  name: 'StatusPage',
  data() {
    return {
      loading: false,
      optimizing: false,
      activeTab: 'partitions',
      
      // 统计数据
      statsData: {
        stocks: 0,
        daily_records: 0,
        date_range: {
          start: '',
          end: ''
        },
        signals: {
          buy_signals: 0,
          sell_signals: 0
        },
        table_sizes: {}
      },
      
      // 分区数据
      partitionData: [],
      
      // 性能数据
      performanceData: {
        query_stats: {},
        table_query_stats: []
      },
      
      // 表格列配置
      partitionColumns: [
        {
          title: '表名',
          dataIndex: 'table',
          key: 'table',
          width: 150
        },
        {
          title: '分区',
          dataIndex: 'partition',
          key: 'partition',
          width: 120
        },
        {
          title: '分片数',
          dataIndex: 'parts',
          key: 'parts',
          width: 80
        },
        {
          title: '行数',
          dataIndex: 'rows',
          key: 'rows',
          width: 100
        },
        {
          title: '大小',
          dataIndex: 'size',
          key: 'size',
          width: 100
        }
      ],
      
      tableQueryColumns: [
        {
          title: '表名',
          dataIndex: 'tables',
          key: 'tables',
          width: 200
        },
        {
          title: '查询次数',
          dataIndex: 'query_count',
          key: 'query_count',
          width: 100
        },
        {
          title: '平均耗时(ms)',
          dataIndex: 'avg_duration_ms',
          key: 'avg_duration_ms',
          width: 120
        }
      ]
    }
  },
  
  mounted() {
    this.refreshData()
  },
  
  methods: {
    // 获取基础统计信息
    async fetchStats() {
      try {
        const response = await getStats()
        if (response.code === 200) {
          this.statsData = { ...this.statsData, ...response.data }
        } else {
          this.$message.error(response.message || '获取统计信息失败')
        }
      } catch (error) {
        console.error('获取统计信息失败:', error)
        this.$message.error('获取统计信息失败')
      }
    },
    
    // 获取分区信息
    async fetchPartitions() {
      try {
        const response = await getPartitions()
        if (response.code === 200) {
          // 将分区数据转换为表格格式
          const tableData = []
          Object.entries(response.data).forEach(([table, partitions]) => {
            partitions.forEach((partition) => {
              tableData.push({
                key: `${table}-${partition.partition}`,
                table,
                ...partition
              })
            })
          })
          this.partitionData = tableData
        } else {
          this.$message.error(response.message || '获取分区信息失败')
        }
      } catch (error) {
        console.error('获取分区信息失败:', error)
        this.$message.error('获取分区信息失败')
      }
    },
    
    // 获取性能统计
    async fetchPerformance() {
      try {
        const response = await getPerformance()
        if (response.code === 200) {
          this.performanceData = { ...this.performanceData, ...response.data }
        } else {
          this.$message.error(response.message || '获取性能统计失败')
        }
      } catch (error) {
        console.error('获取性能统计失败:', error)
        this.$message.error('获取性能统计失败')
      }
    },
    
    // 刷新数据
    async refreshData() {
      this.loading = true
      try {
        await Promise.all([
          this.fetchStats(),
          this.fetchPartitions(),
          this.fetchPerformance()
        ])
        this.$message.success('数据刷新成功')
      } catch (error) {
        this.$message.error('数据刷新失败')
      } finally {
        this.loading = false
      }
    },
    
    // 优化表
    async optimizeTables() {
      this.optimizing = true
      try {
        const response = await optimizeTables()
        if (response.code === 200) {
          this.$message.success('表优化完成')
          // 优化后刷新数据
          await this.refreshData()
        } else {
          this.$message.error(response.message || '表优化失败')
        }
      } catch (error) {
        console.error('表优化失败:', error)
        this.$message.error('表优化失败')
      } finally {
        this.optimizing = false
      }
    },
    
    // 标签页切换
    handleTabChange(key) {
      if (key === 'partitions' && this.partitionData.length === 0) {
        this.fetchPartitions()
      } else if (key === 'performance' && !this.performanceData.query_stats.total_queries) {
        this.fetchPerformance()
      }
    }
  }
}
</script>

<style scoped>
.status-page {
  padding: 24px;
  background: #f0f2f5;
  min-height: 100vh;
}

.page-header {
  background: white;
  margin-bottom: 16px;
  border-radius: 6px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
}

.content {
  background: transparent;
}

.stats-cards {
  margin-bottom: 16px;
}

.stat-card {
  text-align: center;
  border-radius: 6px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
}

.stat-card:hover {
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
  transition: box-shadow 0.3s;
}

.info-cards {
  margin-bottom: 16px;
}

.info-card {
  border-radius: 6px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
}

.detail-card {
  border-radius: 6px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
}

::v-deep .ant-card-head {
  border-bottom: 1px solid #f0f0f0;
}

::v-deep .ant-statistic-title {
  color: #666;
  font-size: 14px;
  margin-bottom: 4px;
}

::v-deep .ant-statistic-content {
  color: #262626;
  font-size: 24px;
  font-weight: 600;
}

::v-deep .ant-descriptions-item-label {
  font-weight: 500;
  color: #262626;
}

::v-deep .ant-table-thead > tr > th {
  background: #fafafa;
  font-weight: 600;
}

::v-deep .ant-tabs-tab {
  font-weight: 500;
}
</style>