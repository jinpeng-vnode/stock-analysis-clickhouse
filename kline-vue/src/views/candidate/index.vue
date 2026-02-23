<template>
  <a-config-provider :locale="zhCN">
    <div class="candidate-page">
      <div class="left">
        <!-- 候选股票管理器 -->
        <a-card title="候选股票管理">
          <template #extra>
            <a-space>
              <a-button type="primary" @click="showAddModal = true">添加股票</a-button>
              <a-button danger @click="clearAllCandidates">清空列表</a-button>
            </a-space>
          </template>

          <!-- 搜索和筛选 -->
          <div class="search-section">
            <a-input-search
              v-model:value="searchKeyword"
              placeholder="搜索股票代码或名称"
              @search="handleSearch"
              style="margin-bottom: 16px"
            />
          </div>

          <!-- 候选股票列表 -->
          <a-table
            :dataSource="filteredCandidates"
            :columns="candidateColumns"
            :pagination="{ pageSize: 10 }"
            size="small"
            :row-selection="rowSelection"
            :row-key="record => record.code"
          >
            <template #bodyCell="{ column, record }">
              <template v-if="column.key === 'action'">
                <a-space>
                  <a-button 
                    type="link" 
                    @click="selectStock(record)"
                    :disabled="selectedCode === record.code"
                  >
                    {{ selectedCode === record.code ? '已选中' : '选择' }}
                  </a-button>
                  <a-button 
                    type="link" 
                    danger 
                    @click="removeCandidate(record.code)"
                  >
                    删除
                  </a-button>
                </a-space>
              </template>
            </template>
          </a-table>
        </a-card>

        <!-- 选中股票信息 -->
        <a-card v-if="selectedStock" title="选中股票信息" style="margin-top: 16px;">
          <a-descriptions :column="2" size="small">
            <a-descriptions-item label="股票代码">{{ selectedStock.code }}</a-descriptions-item>
            <a-descriptions-item label="股票名称">{{ selectedStock.name }}</a-descriptions-item>
          </a-descriptions>
        </a-card>
      </div>

      <div class="right">
        <!-- K线图表 -->
        <vue2-kline-chart 
          v-if="selectedCode" 
          :code="selectedCode" 
          :show-days="showDays" 
          :today="today" 
        />
        <div v-else class="no-selection">
          <a-empty description="请从左侧选择一只股票查看K线图" />
        </div>
      </div>

      <!-- 添加股票模态框 -->
      <a-modal
        v-model:open="showAddModal"
        title="添加股票到候选列表"
        @ok="handleAddStock"
        @cancel="resetAddForm"
      >
        <a-form :model="addForm" layout="vertical">
          <a-form-item label="股票代码" required>
            <a-input v-model:value="addForm.code" placeholder="请输入股票代码" />
          </a-form-item>
          <a-form-item label="股票名称" required>
            <a-input v-model:value="addForm.name" placeholder="请输入股票名称" />
          </a-form-item>
        </a-form>
      </a-modal>
    </div>
  </a-config-provider>
</template>

<script>
import Vue2KlineChart from "../kline-analysis/vue2-kline-chart.vue";
import { ConfigProvider } from 'ant-design-vue';
// @ts-ignore
import zhCN from 'ant-design-vue/es/locale/zh_CN';
import { useCandidateListStore } from '@/stores/candidateList';
import dayjs from 'dayjs';

export default {
  name: 'CandidateManagement',
  components: {
    Vue2KlineChart,
    ConfigProvider
  },
  setup() {
    const candidateListStore = useCandidateListStore()
    return { candidateListStore }
  },
  data() {
    return {
      zhCN,
      selectedCode: '',
      showDays: 180,
      today: '2025-10-09',
      searchKeyword: '',
      showAddModal: false,
      addForm: {
        code: '',
        name: ''
      },
      candidateColumns: [
        {
          title: '股票代码',
          dataIndex: 'code',
          key: 'code',
          width: 100
        },
        {
          title: '股票名称',
          dataIndex: 'name',
          key: 'name',
          width: 150
        },
        {
          title: '操作',
          key: 'action',
          width: 120
        }
      ],
      rowSelection: {
        type: 'radio',
        selectedRowKeys: [],
        onChange: (selectedRowKeys, selectedRows) => {
          if (selectedRows.length > 0) {
            this.selectStock(selectedRows[0])
          }
        }
      }
    }
  },
  computed: {
    selectedStock() {
      if (!this.selectedCode) return null
      return this.candidateListStore.stocks.find(stock => stock.code === this.selectedCode) || null
    },
    filteredCandidates() {
      if (!this.searchKeyword) {
        return this.candidateListStore.stocks
      }
      const keyword = this.searchKeyword.toLowerCase()
      return this.candidateListStore.stocks.filter(stock => 
        stock.code.toLowerCase().includes(keyword) || 
        stock.name.toLowerCase().includes(keyword)
      )
    }
  },
  methods: {
    selectStock(stock) {
      this.selectedCode = stock.code
      this.$message.success(`已选择股票: ${stock.name}(${stock.code})`)
    },
    removeCandidate(code) {
      this.candidateListStore.removeStock(code)
      if (this.selectedCode === code) {
        this.selectedCode = ''
      }
      this.$message.success('已从候选列表移除')
    },
    clearAllCandidates() {
      this.$modal.confirm({
        title: '确认清空',
        content: '确定要清空所有候选股票吗？',
        onOk: () => {
          this.candidateListStore.clearAll()
          this.selectedCode = ''
          this.$message.success('已清空候选列表')
        }
      })
    },
    handleSearch() {
      // 搜索逻辑已在computed中处理
    },
    handleAddStock() {
      if (!this.addForm.code || !this.addForm.name) {
        this.$message.error('请填写完整的股票信息')
        return
      }
      
      this.candidateListStore.addStock({
        code: this.addForm.code,
        name: this.addForm.name
      })
      
      this.$message.success(`已添加股票: ${this.addForm.name}(${this.addForm.code})`)
      this.resetAddForm()
      this.showAddModal = false
    },
    resetAddForm() {
      this.addForm = {
        code: '',
        name: ''
      }
    }
  },
  mounted() {
    // 加载候选列表
    this.candidateListStore.loadFromStorage()
    this.today = dayjs().format('YYYY-MM-DD')
  }
}
</script>

<style scoped>
.candidate-page {
  width: 100%;
  height: 100vh;
  display: flex;
  flex-direction: row;
}

.left {
  width: 600px;
  padding: 12px;
  box-sizing: border-box;
}

.right {
  flex: 1;
  height: 100%;
  margin: 12px;
  box-sizing: border-box;
  overflow: auto;
  background: #fff;
}

.search-section {
  margin-bottom: 16px;
}

.no-selection {
  display: flex;
  justify-content: center;
  align-items: center;
  height: 100%;
  background: #fafafa;
}
</style>
