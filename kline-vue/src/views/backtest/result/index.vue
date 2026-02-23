<template>
  <div class="result-page">
    <a-card title="回测结果列表" :bordered="false">
           <template #extra>
        <a-space>
          <a-button @click="clearAllResults" danger>
            <template #icon><ClearOutlined /></template>
            一键清空
          </a-button>
        </a-space>
      </template>
      
      <a-table
        :columns="columns"
        :data-source="results"
        :pagination="{ pageSize: 10 }"
        :row-key="record => record.id"
      >
        <template #bodyCell="{ column, record }">
          <template v-if="column.key === 'total_return'">
            <a-tag :color="record.total_return >= 0 ? 'red' : 'green'">
              {{ (record.total_return * 100).toFixed(2) }}%
            </a-tag>
          </template>
          <template v-else-if="column.key === 'max_drawdown'">
            <a-tag color="orange">
              {{ (record.max_drawdown * 100).toFixed(2) }}%
            </a-tag>
          </template>
          <template v-else-if="column.key === 'win_rate'">
            <a-tag :color="record.win_rate >= 0.5 ? 'red' : 'green'">
              {{ (record.win_rate * 100).toFixed(2) }}%
            </a-tag>
          </template>
          <template v-else-if="column.key === 'action'">
            <a-space>
              <a-button type="link" size="small" @click="viewDetail(record)">
                查看详情
              </a-button>
              <a-button type="link" size="small" danger @click="deleteResult(record)">
                删除
              </a-button>
            </a-space>
          </template>
        </template>
      </a-table>
    </a-card>

    <!-- 详情对话框 -->
    <a-modal
      v-model:open="detailVisible"
      title="回测详情"
      width="90%"
      :footer="null"
    >
      <ResultDetail v-if="currentResult" :result="currentResult" />
    </a-modal>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue';
import { message, Modal } from 'ant-design-vue';
import { ClearOutlined } from '@ant-design/icons-vue';
import storage from '../utils/storage';
import ResultDetail from './detail.vue';

const results = ref([]);
const detailVisible = ref(false);
const currentResult = ref(null);

const columns = [
  {
    title: '配置名称',
    dataIndex: 'config_name',
    key: 'config_name',
    width: 200
  },
  {
    title: '日期范围',
    key: 'date_range',
    width: 200,
    customRender: ({ record }) => `${record.start_date} ~ ${record.end_date}`
  },
  {
    title: '初始资金',
    dataIndex: 'initial_capital',
    key: 'initial_capital',
    width: 120,
    customRender: ({ text }) => text ? text.toFixed(2) : '0.00'
  },
  {
    title: '最终资金',
    dataIndex: 'final_capital',
    key: 'final_capital',
    width: 120,
    customRender: ({ text }) => text ? text.toFixed(2) : '0.00'
  },
  {
    title: '总收益率',
    dataIndex: 'total_return',
    key: 'total_return',
    width: 100,
    customRender: ({ text }) => text ? `${(text * 100).toFixed(2)}%` : '0.00%'
  },
  {
    title: '最大回撤',
    dataIndex: 'max_drawdown',
    key: 'max_drawdown',
    width: 100,
    customRender: ({ text }) => text ? `${(text * 100).toFixed(2)}%` : '0.00%'
  },
  {
    title: '胜率',
    dataIndex: 'win_rate',
    key: 'win_rate',
    width: 100,
    customRender: ({ text }) => text ? `${(text * 100).toFixed(2)}%` : '0.00%'
  },
  {
    title: '交易次数',
    dataIndex: 'total_trades',
    key: 'total_trades',
    width: 100,
    customRender: ({ text }) => text || 0
  },
  {
    title: '创建时间',
    dataIndex: 'created_at',
    key: 'created_at',
    width: 180,
    customRender: ({ text }) => new Date(text).toLocaleString()
  },
  {
    title: '操作',
    key: 'action',
    width: 150,
    fixed: 'right'
  }
];

// 加载结果列表
const loadResults = () => {
  results.value = storage.getAllResults();
  console.log('📊 加载了', results.value.length, '条回测结果');
};

// 查看详情
const viewDetail = (record) => {
  const fullResult = storage.getResult(record.id);
  if (fullResult) {
    currentResult.value = fullResult;
    detailVisible.value = true;
  } else {
    message.error('无法加载详情');
  }
};

// 删除结果
const deleteResult = (record) => {
  Modal.confirm({
    title: '确认删除',
    content: `确定要删除回测结果"${record.config_name}"吗？`,
    onOk: () => {
      storage.deleteResult(record.id);
      loadResults();
      message.success('删除成功');
    }
  });
};

// 清空所有结果
const clearAllResults = () => {
  if (results.value.length === 0) {
    message.info('没有可清空的结果');
    return;
  }
  
  Modal.confirm({
    title: '确认清空结果',
    content: `确定要清空所有回测结果吗？此操作不可恢复！\n\n将清空 ${results.value.length} 条结果记录。\n\n注意：此操作不会删除回测配置。`,
    okText: '确认清空',
    cancelText: '取消',
    okType: 'danger',
    onOk: () => {
      try {
        storage.clearAllResults();
        loadResults();
        message.success(`已清空所有回测结果（${results.value.length} 条）`);
      } catch (error) {
        console.error('清空结果失败:', error);
        message.error('清空失败，请重试');
      }
    }
  });
};

onMounted(() => {
  loadResults();
});
</script>

<style scoped>
.result-page {
  max-width: 1400px;
  margin: 0 auto;
}
</style>

