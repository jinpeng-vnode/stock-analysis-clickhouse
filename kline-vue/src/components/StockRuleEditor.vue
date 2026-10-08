<template>
  <div class="stock-rule-editor">
    <a-row :gutter="16">
      <a-col :span="12">
        <JsonLogicRuleEditor
          :model-value="buyRule"
          :field-options="stockFieldOptions"
          :operator-names="operatorNames"
          :rule-title="buyRuleTitle"
          :default-conditions="defaultBuyConditions"
          :show-preview="false"
          :show-description="false"
          :debounce-delay="debounceDelay"
          @update:modelValue="handleBuyRuleUpdate"
        />
      </a-col>
      <a-col :span="12">
        <JsonLogicRuleEditor
          :model-value="sellRule"
          :field-options="stockFieldOptions"
          :operator-names="operatorNames"
          :rule-title="sellRuleTitle"
          :default-conditions="defaultSellConditions"
          :show-preview="false"
          :show-description="false"
          :debounce-delay="debounceDelay"
          @update:modelValue="handleSellRuleUpdate"
        />
      </a-col>
    </a-row>
    
    <!-- JSON预览 -->
    <a-card title="规则预览" size="small" style="margin-top: 16px" v-if="showPreview">
      <a-row :gutter="16">
        <a-col :span="12">
          <h4>{{ buyRuleTitle }} JSON:</h4>
          <pre class="json-preview">{{ JSON.stringify(buyRule, null, 2) }}</pre>
        </a-col>
        <a-col :span="12">
          <h4>{{ sellRuleTitle }} JSON:</h4>
          <pre class="json-preview">{{ JSON.stringify(sellRule, null, 2) }}</pre>
        </a-col>
      </a-row>
    </a-card>

    <a-alert
      v-if="showDescription"
      message="规则说明"
      :description="ruleDescription"
      type="info"
      show-icon
      style="margin-top: 16px"
    />
  </div>
</template>

<script setup>
import { computed } from 'vue';
import JsonLogicRuleEditor from './JsonLogicRuleEditor.vue';

// 股票相关字段配置
const stockFieldOptions = [
  // 基础价格
  { value: 'close', label: '收盘价', type: 'number', precision: 2 },
  { value: 'high', label: '最高价', type: 'number', precision: 2 },
  { value: 'low', label: '最低价', type: 'number', precision: 2 },
  { value: 'open', label: '开盘价', type: 'number', precision: 2 },
  // 成交量数据
  { value: 'volume', label: '成交量', type: 'number', precision: 0 },
  { value: 'amount', label: '成交额', type: 'number', precision: 2 },
  { value: 'turnover_rate', label: '换手率', type: 'number', precision: 2 },
  // 技术指标
  { value: 'wr6', label: '威廉指标6', type: 'number', precision: 2 },
  { value: 'wr10', label: '威廉指标10', type: 'number', precision: 2 },
  { value: 'ma5', label: '5日均线', type: 'number', precision: 2 },
  { value: 'ma10', label: '10日均线', type: 'number', precision: 2 },
  { value: 'ma20', label: '20日均线', type: 'number', precision: 2 },
  { value: 'slope_180', label: '180日斜率', type: 'number', precision: 2 },
  { value: 'slope_7', label: '7日斜率', type: 'number', precision: 2 },
  { value: 'fit_7', label: '7日拟合值', type: 'number', precision: 2 },
  { value: 'fit_180', label: '180日拟合值', type: 'number', precision: 2 },
  // 涨跌数据
  { value: 'amplitude', label: '振幅', type: 'number', precision: 2 },
  { value: 'change_pct', label: '涨跌幅', type: 'number', precision: 2 },
  { value: 'change_amount', label: '涨跌额', type: 'number', precision: 2 },
  // 交易信号
  { value: 'best_buy', label: '买入信号', type: 'boolean', precision: 0 },
  { value: 'best_sell', label: '卖出信号', type: 'boolean', precision: 0 },
  { value: 'buy_count_7', label: '7日买点数量', type: 'number', precision: 0 },
  { value: 'sell_count_7', label: '7日卖点数量', type: 'number', precision: 0 },
  { value: 'buy_count_14', label: '14日买点数量', type: 'number', precision: 0 },
  { value: 'sell_count_14', label: '14日卖点数量', type: 'number', precision: 0 },
  // 持仓数据
  { value: 'profit_pct', label: '收益率', type: 'number', precision: 2 }
];

// 操作符中文映射
const operatorNames = {
  '==': '等于',
  '!=': '不等于',
  '>': '大于',
  '<': '小于',
  '>=': '大于等于',
  '<=': '小于等于',
  'in': '包含',
  '!in': '不包含'
};

// 默认买入条件
const defaultBuyConditions = [
  { field: 'wr6', operator: '<', value: 20 },
  { field: 'close', operator: '>', value: 3 },
  { field: 'close', operator: '<', value: 100 }
];

// 默认卖出条件
const defaultSellConditions = [
  { field: 'best_sell', operator: '==', value: true },
  { field: 'profit_pct', operator: '<', value: -0.02 },
  { field: 'profit_pct', operator: '>', value: 0.05 }
];

const props = defineProps({
  buyRule: {
    type: Object,
    required: true
  },
  sellRule: {
    type: Object,
    required: true
  },
  buyRuleTitle: {
    type: String,
    default: '买入规则'
  },
  sellRuleTitle: {
    type: String,
    default: '卖出规则'
  },
  showPreview: {
    type: Boolean,
    default: false
  },
  showDescription: {
    type: Boolean,
    default: false
  },
  debounceDelay: {
    type: Number,
    default: 100
  }
});

const emit = defineEmits(['update:buyRule', 'update:sellRule']);

// 规则描述
const ruleDescription = computed(() => {
  const fieldNames = stockFieldOptions.map(f => f.label).join('、');
  return `支持字段：${fieldNames}`;
});

// 处理买入规则更新
const handleBuyRuleUpdate = (rule) => {
  emit('update:buyRule', rule);
};

// 处理卖出规则更新
const handleSellRuleUpdate = (rule) => {
  emit('update:sellRule', rule);
};
</script>

<style scoped>
.stock-rule-editor {
  width: 100%;
}

.json-preview {
  background-color: #f5f5f5;
  padding: 12px;
  border-radius: 4px;
  font-size: 12px;
  max-height: 200px;
  overflow: auto;
  white-space: pre-wrap;
  word-break: break-word;
}

h4 {
  margin: 0 0 8px 0;
  font-size: 14px;
  font-weight: 600;
}
</style>
