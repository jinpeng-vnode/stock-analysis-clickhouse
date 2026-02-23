<template>
  <div class="page-container">
    <a-card title="股票公告管理" style="margin-bottom: 16px;">
      <template #extra>
        <a-form layout="inline" :colon="false" style="gap:8px;margin: 8px;">
          <a-form-item label="股票代码" name="code">
            <a-input v-model:value="searchParams.code" placeholder="6位数字" style="width: 120px;" />
          </a-form-item>
          <a-form-item label="开始日期" name="start_date">
            <a-date-picker v-model:value="searchParams.start_date" format="YYYY-MM-DD" style="width: 140px;" />
          </a-form-item>
          <a-form-item label="结束日期" name="end_date">
            <a-date-picker v-model:value="searchParams.end_date" format="YYYY-MM-DD" style="width: 140px;" />
          </a-form-item>
          <a-form-item label="公告类型" name="type">
            <a-input v-model:value="searchParams.type" placeholder="如：业绩预告" style="width: 120px;" />
          </a-form-item>
          <a-form-item>
            <a-space>
              <a-button type="primary" ghost :loading="isLoading" @click="searchReset">重置</a-button>
              <a-button type="primary" :loading="isLoading" @click="doSearch">查询</a-button>
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
      rowKey="detail_url"
      size="middle"
      @change="onTableChange"
    >
      <template #bodyCell="{ column, text, record }">
        <template v-if="column.dataIndex === 'title'">
          <a @click="onViewDetail(record)" style="color: #1890ff;">{{ text }}</a>
        </template>
        <template v-if="column.dataIndex === 'attachments'">
          <a v-if="text" :href="text" target="_blank" style="color: #1890ff;">查看附件</a>
          <span v-else>-</span>
        </template>
        <template v-if="column.dataIndex === 'content'">
          <a-typography-paragraph :ellipsis="{ rows: 2, expandable: false }" style="max-width: 400px; margin: 0;">
            {{ text || '-' }}
          </a-typography-paragraph>
        </template>
      </template>
    </a-table>

    <a-modal
      v-model:open="detailModalVisible"
      title="公告详情"
      width="800px"
      :footer="null"
    >
      <a-descriptions :column="1" bordered v-if="currentRecord">
        <a-descriptions-item label="股票代码">{{ currentRecord.code }}</a-descriptions-item>
        <a-descriptions-item label="公告日期">{{ currentRecord.announce_date }}</a-descriptions-item>
        <a-descriptions-item label="公告标题">{{ currentRecord.title }}</a-descriptions-item>
        <a-descriptions-item label="公告类型">{{ currentRecord.type }}</a-descriptions-item>
        <a-descriptions-item label="详情链接">
          <a :href="currentRecord.detail_url" target="_blank">{{ currentRecord.detail_url }}</a>
        </a-descriptions-item>
        <a-descriptions-item label="附件">
          <a v-if="currentRecord.attachments" :href="currentRecord.attachments" target="_blank">查看附件</a>
          <span v-else>-</span>
        </a-descriptions-item>
        <a-descriptions-item label="公告内容">
          <div style="max-height: 400px; overflow-y: auto; white-space: pre-wrap;">{{ currentRecord.content || '-' }}</div>
        </a-descriptions-item>
      </a-descriptions>
    </a-modal>
  </div>
</template>

<script>
import { message } from 'ant-design-vue'
import { getStockAnnouncements, listAnnouncements } from '@/api/announcements'
import dayjs from 'dayjs'

export default {
  name: 'AnnouncementList',
  data() {
    return {
      columns: [
        { title: '序号', dataIndex: 'index', width: 70, customRender: ({ index }) => (this.pagination.current - 1) * this.pagination.pageSize + index + 1 },
        { title: '股票代码', dataIndex: 'code', width: 100 },
        { title: '公告日期', dataIndex: 'announce_date', width: 120 },
        { title: '公告标题', dataIndex: 'title', width: 300 },
        { title: '公告类型', dataIndex: 'type', width: 120 },
        { title: '附件', dataIndex: 'attachments', width: 100 },
        { title: '内容预览', dataIndex: 'content', width: 300 },
      ],
      searchParams: { 
        code: '', 
        start_date: null, 
        end_date: null, 
        type: '' 
      },
      datasource: [],
      isLoading: false,
      pagination: { 
        current: 1, 
        pageSize: 10, 
        total: 0, 
        showSizeChanger: true, 
        showQuickJumper: true, 
        showTotal: (t) => `共 ${t} 条` 
      },
      detailModalVisible: false,
      currentRecord: null,
    }
  },
  created() { 
    this.doSearch() 
  },
  methods: {
    doSearch() {
      this.isLoading = true
      
      const params = {
        page: this.pagination.current,
        size: this.pagination.pageSize,
      }
      
      // 如果有股票代码，使用单个股票接口
      if (this.searchParams.code && this.searchParams.code.trim()) {
        if (this.searchParams.start_date) {
          params.start_date = dayjs(this.searchParams.start_date).format('YYYY-MM-DD')
        }
        if (this.searchParams.end_date) {
          params.end_date = dayjs(this.searchParams.end_date).format('YYYY-MM-DD')
        }
        if (this.searchParams.type) {
          params.type = this.searchParams.type
        }
        
        getStockAnnouncements(this.searchParams.code.trim(), params)
          .then((data) => {
            this.datasource = data.items || []
            this.pagination.total = data.total || 0
          })
          .catch(() => { message.error('获取数据失败') })
          .finally(() => { this.isLoading = false })
      } else {
        // 否则使用列表接口
        if (this.searchParams.code) {
          params.code = this.searchParams.code
        }
        if (this.searchParams.start_date) {
          params.start_date = dayjs(this.searchParams.start_date).format('YYYY-MM-DD')
        }
        if (this.searchParams.end_date) {
          params.end_date = dayjs(this.searchParams.end_date).format('YYYY-MM-DD')
        }
        if (this.searchParams.type) {
          params.type = this.searchParams.type
        }
        
        listAnnouncements(params)
          .then((data) => {
            this.datasource = data || []
            this.pagination.total = data.length || 0
          })
          .catch(() => { message.error('获取数据失败') })
          .finally(() => { this.isLoading = false })
      }
    },
    searchReset() {
      this.searchParams = { 
        code: '', 
        start_date: null, 
        end_date: null, 
        type: '' 
      }
      this.pagination.current = 1
      this.doSearch()
    },
    onTableChange(pagination) {
      this.pagination = pagination
      this.doSearch()
    },
    onViewDetail(record) {
      this.currentRecord = record
      this.detailModalVisible = true
    },
  },
}
</script>

<style scoped>
.page-container { 
  padding: 8px; 
}
</style>

