<template>
  <div class="rule-editor">
    <StockRuleEditor
      :buy-rule="buyRule"
      :sell-rule="sellRule"
      @update:buy-rule="handleBuyRuleUpdate"
      @update:sell-rule="handleSellRuleUpdate"
    />
  </div>
</template>

<script setup>
import StockRuleEditor from '@/components/StockRuleEditor.vue';

const props = defineProps({
  buyRule: {
    type: Object,
    required: true
  },
  sellRule: {
    type: Object,
    required: true
  }
});

const emit = defineEmits(['update:buyRule', 'update:sellRule']);

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
.rule-editor {
  width: 100%;
}

.rule-builder {
  min-height: 200px;
}

.condition-group {
  margin-bottom: 12px;
  padding: 8px;
  border: 1px solid #f0f0f0;
  border-radius: 6px;
  background: #fafafa;
}

.logic-operator {
  text-align: center;
  padding: 8px 0;
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