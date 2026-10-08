<template>
  <div class="page-container">
    <a-card title="股票信息管理" style="margin-bottom: 16px;">
      <template #extra>
        <a-form layout="inline" :colon="false" style="gap:8px;margin: 8px;">
          <a-form-item label="关键词" name="q">
            <a-input v-model:value="searchParams.q" placeholder="代码/名称" @pressEnter="doSearch(true)" />
          </a-form-item>
          <a-form-item label="市场" name="market">
            <a-select v-model:value="searchParams.market" allow-clear style="width: 120px;">
              <a-select-option value="SH">SH</a-select-option>
              <a-select-option value="SZ">SZ</a-select-option>
            </a-select>
          </a-form-item>
          <a-form-item label="状态" name="status">
            <a-input v-model:value="searchParams.status" placeholder="正常/停牌等" @pressEnter="doSearch(true)" />
          </a-form-item>
          <a-form-item>
            <a-space>
              <a-button type="primary" ghost :loading="isLoading" @click="searchReset">重置</a-button>
              <a-button type="primary" :loading="isLoading" @click="doSearch(true)">查询</a-button>
              <a-button type="primary" @click="onCreate">创建</a-button>
              <a-button type="primary" danger :disabled="!selectedRowKeys.length" :loading="isBatchDeleting" @click="onBatchDelete">
                批量删除
              </a-button>
            </a-space>
          </a-form-item>
        </a-form>
      </template>
    </a-card>

    <a-table
      :columns="columns"
      :dataSource="datasource"
      :loading="isLoading"
      :pagination="pagination"
      rowKey="code"
      size="middle"
      @change="onTableChange"
      :rowSelection="{ selectedRowKeys: selectedRowKeys, onChange: onSelectChange }"
    >
      <template #bodyCell="{ column, text, record }">
        <template v-if="column.dataIndex === 'code'">
          <a @click="onEdit(record)">{{ text }}</a>
        </template>
        <template v-if="column.dataIndex === 'action'">
          <a-space>
            <a @click="onEdit(record)" type="link">编辑</a>
            <a-popconfirm title="确定删除该股票？" @confirm="onDelete(record)">
              <a type="link">删除</a>
            </a-popconfirm>
          </a-space>
        </template>
      </template>
    </a-table>

    <stock-info-edit-modal ref="editModal" @change="doSearch" />
  </div>
  
</template>

<script>
import StockInfoEditModal from './stock-info-edit-modal.vue'
import { message } from 'ant-design-vue'
import { getStockInfoList, deleteStockInfo, batchDeleteStockInfo } from '@/api/stocks'

export default {
  name: 'StockInfoList',
  components: { StockInfoEditModal },
  data() {
    return {
      columns: [
        { title: '序号', dataIndex: 'index', width: 70, customRender: ({ index }) => (this.pagination.current - 1) * this.pagination.pageSize + index + 1 },
        { title: '代码', dataIndex: 'code', width: 100 },
        { title: '名称', dataIndex: 'name', width: 150 },
  
        { title: '状态', dataIndex: 'status', width: 100 },
 
        { title: '版本时间', dataIndex: 'version', width: 180 },
        { title: '操作', dataIndex: 'action', width: 150, fixed: 'right' },
      ],

      searchParams: { q: '', market: undefined, status: '' },
      datasource: [],
      isLoading: false,
      pagination: { current: 1, pageSize: 10, total: 0, showSizeChanger: true, showQuickJumper: true, showTotal: (t) => `共 ${t} 条` },
      selectedRowKeys: [],
      isBatchDeleting: false,
    }
  },
  created() { this.doSearch() },
  methods: {
    doSearch(resetPage = false) {
      // 如果重置分页，则回到第一页
      if (resetPage) {
        this.pagination.current = 1
      }
      
      // 构建查询参数，过滤掉空值
      const params = {
        page: this.pagination.current,
        size: this.pagination.pageSize
      }
      
      // 只添加有效的搜索参数
      if (this.searchParams.q && this.searchParams.q.trim()) {
        params.q = this.searchParams.q.trim()
      }
      if (this.searchParams.market) {
        params.market = this.searchParams.market
      }
      if (this.searchParams.status && this.searchParams.status.trim()) {
        params.status = this.searchParams.status.trim()
      }
      
      this.isLoading = true
      getStockInfoList(params)
        .then((data) => {
          this.datasource = data.items || []
          this.pagination.total = data.total || 0
        })
        .catch(() => { message.error('获取数据失败') })
        .finally(() => { this.isLoading = false })
    },
    searchReset() {
      this.searchParams = { q: '', market: undefined, status: '' }
      this.pagination.current = 1
      this.doSearch()
    },
    onTableChange(pagination) {
      // 处理分页变化，可能是分页对象或包含分页信息的对象
      if (pagination.current !== undefined) {
        this.pagination.current = pagination.current
      }
      if (pagination.pageSize !== undefined) {
        this.pagination.pageSize = pagination.pageSize
      }
      this.doSearch()
    },
    onEdit(record) {
      this.$refs.editModal.id = record.code
      this.$refs.editModal.visible = true
    },
    onDelete(record) {
      return deleteStockInfo(record.code)
        .then(() => { message.success('删除已提交'); this.doSearch() })
        .catch(() => { message.error('删除失败') })
    },
    onSelectChange(keys) { this.selectedRowKeys = keys },
    onBatchDelete() {
      if (!this.selectedRowKeys.length) { message.warning('请选择要删除的数据'); return }
      this.isBatchDeleting = true
      batchDeleteStockInfo(this.selectedRowKeys)
        .then(() => { message.success('批量删除已提交'); this.selectedRowKeys = []; this.doSearch() })
        .catch(() => { message.error('批量删除失败') })
        .finally(() => { this.isBatchDeleting = false })
    },
    onCreate() {
      this.$refs.editModal.id = null
      this.$refs.editModal.visible = true
    },
  },
}
</script>

<style scoped>
.page-container { padding: 8px; }
</style>


