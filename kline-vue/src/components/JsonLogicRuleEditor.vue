<template>
  <div class="jsonlogic-rule-editor">
    <a-card size="small">
      <template #title>
        <slot name="title">
          {{ ruleTitle }}
        </slot>
      </template>
      <template #extra>
        <a-space>
          <a-radio-group v-model:value="logicOperator" @change="updateRule" button-style="solid" size="small">
            <a-radio-button value="and">且 (AND)</a-radio-button>
            <a-radio-button value="or">或 (OR)</a-radio-button>
          </a-radio-group>
          <a-space>
            <a-tooltip title="复制规则">
              <CopyOutlined 
                @click="copyRule" 
                :style="{ 
                  color: hasValidRule ? '#52c41a' : '#d9d9d9', 
                  fontSize: '16px', 
                  cursor: hasValidRule ? 'pointer' : 'not-allowed',
                  padding: '4px',
                  borderRadius: '4px',
                  transition: 'all 0.3s ease'
                }"
                class="icon-hover"
              />
            </a-tooltip>
            <a-tooltip title="导入规则">
              <ImportOutlined 
                @click="importRule" 
                style="color: #1890ff; font-size: 16px; cursor: pointer; padding: 4px; border-radius: 4px; transition: all 0.3s ease;"
                class="icon-hover"
              />
            </a-tooltip>
          </a-space>
        </a-space>
      </template>
      
      <div class="rule-builder">
        <div v-for="(condition, index) in conditions" :key="index" class="condition-group">
          <a-space align="middle" size="middle">
            <a-select v-model:value="condition.field" placeholder="选择字段" @change="updateRule" style="width: 150px">
              <template #suffixIcon>
                <DatabaseOutlined style="color: #1890ff" />
              </template>
              <a-select-option v-for="field in fieldOptions" :key="field.value" :value="field.value">
                {{ field.label }}
              </a-select-option>
            </a-select>
            
            <a-select v-model:value="condition.operator" placeholder="操作符" @change="onOperatorChange(index)" style="width: 120px">
              <template #suffixIcon>
                <FunctionOutlined style="color: #52c41a" />
              </template>
              <a-select-option v-for="op in getOperatorOptions(condition.field)" :key="op" :value="op">
                {{ operatorNames[op] || op }}
              </a-select-option>
            </a-select>
            
            <template v-if="isBooleanField(condition.field)">
              <a-switch
                v-model:checked="condition.value"
                checked-children="是"
                un-checked-children="否"
                @change="updateRule"
              />
            </template>
            <template v-else-if="isDateField(condition.field)">
              <a-date-picker 
                v-model:value="condition.value" 
                placeholder="选择日期"
                format="YYYY-MM-DD"
                value-format="YYYY-MM-DD"
                @change="updateRule"
                style="width: 140px"
              />
            </template>
            <template v-else>
              <a-input-number 
                v-if="condition.operator !== 'in' && condition.operator !== '!in'"
                v-model:value="condition.value" 
                placeholder="值"
                :precision="getFieldPrecision(condition.field)"
                @change="updateRule"
                style="width: 120px"
              />
              <a-input 
                v-else
                v-model:value="condition.value" 
                placeholder="值，多个用逗号分隔"
                @change="updateRule"
                style="width: 120px"
              />
            </template>
            
            <a-button 
              type="text" 
              danger 
              @click="removeCondition(index)"
              :disabled="conditions.length <= 1"
              size="small"
            >
              <template #icon><DeleteOutlined /></template>
            </a-button>
          </a-space>
        </div>
        <a-button 
          type="dashed" 
          block 
          @click="addCondition"
          style="margin-top: 8px"
        >
          <template #icon><PlusOutlined /></template>
          添加条件
        </a-button>
      </div>
    </a-card>
    
    <!-- JSON预览 -->
    <a-card title="规则预览" size="small" style="margin-top: 16px" v-if="showPreview">
      <h4>{{ ruleTitle }} JSON:</h4>
      <pre class="json-preview">{{ JSON.stringify(rule, null, 2) }}</pre>
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
import { ref, reactive, watch, onMounted, computed } from 'vue';
import { message } from 'ant-design-vue';
import { 
  PlusOutlined, 
  DeleteOutlined, 
  DatabaseOutlined, 
  FunctionOutlined, 
  NumberOutlined,
  CopyOutlined,
  ImportOutlined
} from '@ant-design/icons-vue';


const props = defineProps({
  // 规则数据
  modelValue: {
    type: Object,
    default: () => ({})
  },
  // 字段配置
  fieldOptions: {
    type: Array,
    default: () => [
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
    ]
  },
  // 操作符名称映射
  operatorNames: {
    type: Object,
    default: () => ({
      '==': '等于',
      '!=': '不等于',
      '>': '大于',
      '<': '小于',
      '>=': '大于等于',
      '<=': '小于等于',
      'in': '包含',
      '!in': '不包含'
    })
  },
  // 标题配置
  ruleTitle: {
    type: String,
    default: '规则'
  },
  // 默认条件
  defaultConditions: {
    type: Array,
    default: () => []
  },
  // 显示配置
  showPreview: {
    type: Boolean,
    default: true
  },
  showDescription: {
    type: Boolean,
    default: true
  },
  // 防抖延迟
  debounceDelay: {
    type: Number,
    default: 100
  }
});

const emit = defineEmits(['update:modelValue']);

// 规则相关
const conditions = ref([]);
const logicOperator = ref('and');

// 字段映射（用于快速查找）
const fieldMap = computed(() => {
  const map = {};
  props.fieldOptions.forEach(field => {
    map[field.value] = field;
  });
  return map;
});

// 检查是否有有效规则
const hasValidRule = computed(() => {
  const rule = conditionsToRule(conditions.value, logicOperator.value);
  return rule && Object.keys(rule).length > 0;
});

// 判断布尔字段
const isBooleanField = (field) => {
  const fieldConfig = fieldMap.value[field];
  return fieldConfig && fieldConfig.type === 'boolean';
};

// 判断日期字段
const isDateField = (field) => {
  const fieldConfig = fieldMap.value[field];
  return fieldConfig && fieldConfig.type === 'date';
};

// 根据字段返回可选操作符
const getOperatorOptions = (field) => {
  if (isBooleanField(field)) {
    return ['==', '!='];
  }
  if (isDateField(field)) {
    return ['==', '!=', '>', '<', '>=', '<='];
  }
  return ['==', '!=', '>', '<', '>=', '<=', 'in', '!in'];
};

// 当操作符变化时若是布尔字段，规范值为 true/false
const onOperatorChange = (index) => {
  const cond = conditions.value[index];
  if (isBooleanField(cond.field)) {
    if (typeof cond.value !== 'boolean') cond.value = true;
  }
  if (isDateField(cond.field)) {
    if (!cond.value) cond.value = '';
  }
  updateRule();
};

// 获取字段精度
const getFieldPrecision = (field) => {
  const fieldConfig = fieldMap.value[field];
  return fieldConfig ? fieldConfig.precision : 2;
};

// 生成条件的中文描述
const generateConditionDescription = (condition) => {
  if (!condition.field || !condition.operator || condition.value === '' || condition.value === null || condition.value === undefined) {
    return '';
  }
  
  const fieldConfig = fieldMap.value[condition.field];
  const fieldName = fieldConfig ? fieldConfig.label : condition.field;
  const operatorName = props.operatorNames[condition.operator] || condition.operator;
  let valueText = condition.value;
  
  // 处理特殊值
  if (condition.value === true) valueText = '是';
  if (condition.value === false) valueText = '否';
  if (condition.operator === 'in' || condition.operator === '!in') {
    if (Array.isArray(condition.value)) {
      valueText = condition.value.join('、');
    } else if (typeof condition.value === 'string' && condition.value.includes(',')) {
      valueText = condition.value.split(',').map(v => v.trim()).join('、');
    }
  }
  
  return `${fieldName} ${operatorName} ${valueText}`;
};

// 生成规则的中文描述
const ruleDescription = computed(() => {
  const ruleDesc = generateRuleDescription(conditions.value, logicOperator.value, props.ruleTitle);
  const fieldNames = props.fieldOptions.map(f => f.label).join('、');
  return `${ruleDesc}支持字段：${fieldNames}`;
});

// 生成单个规则的中文描述
const generateRuleDescription = (conditions, logicOperator, ruleType) => {
  const validConditions = conditions.filter(c => c.field && c.operator && c.value !== '' && c.value !== null && c.value !== undefined);
  
  if (validConditions.length === 0) {
    return `${ruleType}：暂无有效条件。`;
  }
  
  const conditionDescs = validConditions.map(condition => generateConditionDescription(condition)).filter(desc => desc);
  
  if (conditionDescs.length === 0) {
    return `${ruleType}：暂无有效条件。`;
  }
  
  const logicText = logicOperator === 'and' ? '且' : '或';
  const ruleText = conditionDescs.join(` ${logicText} `);
  
  return `${ruleType}：${ruleText}。`;
};

// 初始化条件
const initConditions = () => {
  // 解析规则
  if (props.modelValue && Object.keys(props.modelValue).length > 0) {
    parseRuleToConditions(props.modelValue);
  } else {
    conditions.value = [...props.defaultConditions];
  }
};

// 解析规则为条件数组
const parseRuleToConditions = (rule) => {
  if (!rule || typeof rule !== 'object') {
    console.warn('规则解析失败：规则为空或格式错误');
    return;
  }

  const parsedConditions = [];
  const ruleKeys = Object.keys(rule);
  
  if (ruleKeys.length === 0) {
    console.warn('规则解析失败：规则对象为空');
    return;
  }

  const logicOp = ruleKeys[0]; // and, or, 或单个条件

  // 验证逻辑操作符
  if (logicOp === 'and' || logicOp === 'or') {
    logicOperator.value = logicOp;

    const conditionsArray = rule[logicOp];
    if (Array.isArray(conditionsArray)) {
      // 限制条件数量，防止死循环
      const maxConditions = 20;
      const limitedArray = conditionsArray.slice(0, maxConditions);
      
      limitedArray.forEach((condition, index) => {
        if (index >= maxConditions) return; // 防止过多条件
        
        if (typeof condition === 'object' && condition !== null) {
          const conditionKeys = Object.keys(condition);
          if (conditionKeys.length === 1) {
            const operator = conditionKeys[0];
            const operands = condition[operator];
            
            if (Array.isArray(operands) && operands.length === 2) {
              const fieldRef = operands[0];
              const value = operands[1];
              
              if (fieldRef && typeof fieldRef === 'object' && fieldRef.var) {
                parsedConditions.push({
                  field: fieldRef.var,
                  operator: operator,
                  value: value
                });
              }
            }
          }
        }
      });
    }
  } else {
    // 单个条件
    const operands = rule[logicOp];
    if (Array.isArray(operands) && operands.length === 2) {
      const fieldRef = operands[0];
      const value = operands[1];
      
      if (fieldRef && typeof fieldRef === 'object' && fieldRef.var) {
        parsedConditions.push({
          field: fieldRef.var,
          operator: logicOp,
          value: value
        });
      }
    }
  }

  // 限制条件数量
  const maxConditions = 10;
  const limitedConditions = parsedConditions.slice(0, maxConditions);

  // 检查是否有用户正在编辑的条件，如果有则保留它们
  const currentConditions = conditions.value || [];
  const hasEmptyConditions = currentConditions.some(condition => 
    !condition.field || !condition.operator || condition.value === '' || condition.value === null || condition.value === undefined
  );
  
  // 如果用户正在编辑，保留当前条件，只更新非空条件
  if (hasEmptyConditions && currentConditions.length > 0) {
    console.log('保留用户正在编辑的条件');
    return;
  }
  
  conditions.value = limitedConditions.length > 0 ? limitedConditions : [{ field: '', operator: '', value: '' }];
};

// 将条件数组转换为JSON Logic规则
const conditionsToRule = (conditions, logicOperator) => {
  if (conditions.length === 0) return {};

  const validConditions = conditions.filter(c => c.field && c.operator && c.value !== '' && c.value !== null && c.value !== undefined);
  
  if (validConditions.length === 0) return {};

  if (validConditions.length === 1) {
    const condition = validConditions[0];
    return {
      [condition.operator]: [
        { var: condition.field },
        parseValue(condition.value, condition.operator)
      ]
    };
  }

  const ruleConditions = validConditions.map(condition => ({
    [condition.operator]: [
      { var: condition.field },
      parseValue(condition.value, condition.operator)
    ]
  }));

  return {
    [logicOperator]: ruleConditions
  };
};

// 解析值
const parseValue = (value, operator) => {
  if (operator === 'in' || operator === '!in') {
    if (typeof value === 'string' && value.includes(',')) {
      return value.split(',').map(v => v.trim());
    }
    return [value];
  }
  // 布尔字段保持布尔
  if (value === true || value === false) return value;
  // 日期字段保持字符串格式
  if (typeof value === 'string' && /^\d{4}-\d{2}-\d{2}$/.test(value)) {
    return value;
  }
  // 数字解析
  if (typeof value === 'string' && !isNaN(value)) {
    return parseFloat(value);
  }
  return value;
};

// 添加条件
const addCondition = () => {
  conditions.value.push({ field: '', operator: '', value: '' });
};

// 删除条件
const removeCondition = (index) => {
  if (conditions.value.length > 1) {
    conditions.value.splice(index, 1);
    updateRule();
  }
};

// 防抖定时器
let ruleUpdateTimer = null;

// 更新规则
const updateRule = () => {
  // 清除之前的定时器
  if (ruleUpdateTimer) {
    clearTimeout(ruleUpdateTimer);
  }
  
  // 设置防抖延迟
  ruleUpdateTimer = setTimeout(() => {
    const rule = conditionsToRule(conditions.value, logicOperator.value);
    emit('update:modelValue', rule);
  }, props.debounceDelay);
};

// 防止循环更新的标志
let isUpdatingFromProps = false;
let lastRuleString = '';

// 监听props变化
watch(() => props.modelValue, (newRule) => {
  if (isUpdatingFromProps) return; // 防止循环更新
  
  // 将规则转换为字符串进行比较，避免深度比较的性能问题
  const newRuleString = JSON.stringify(newRule);
  if (newRuleString === lastRuleString) return; // 规则没有变化
  
  if (newRule && Object.keys(newRule).length > 0) {
    // 检查当前是否有用户正在编辑的条件（有空字段的条件）
    const hasEmptyConditions = conditions.value.some(condition => 
      !condition.field || !condition.operator || condition.value === '' || condition.value === null || condition.value === undefined
    );
    
    // 如果用户正在编辑，不重新解析规则
    if (hasEmptyConditions) {
      console.log('用户正在编辑条件，跳过规则重新解析');
      return;
    }
    
    isUpdatingFromProps = true;
    lastRuleString = newRuleString;
    parseRuleToConditions(newRule);
    isUpdatingFromProps = false;
  }
}, { deep: true });

// 复制规则到剪贴板
const copyRule = async () => {
  if (!hasValidRule.value) {
    message.warning('没有有效的规则可以复制');
    return;
  }
  
  try {
    const rule = conditionsToRule(conditions.value, logicOperator.value);
    const ruleText = JSON.stringify(rule, null, 2);
    await navigator.clipboard.writeText(ruleText);
    message.success('规则已复制到剪贴板');
  } catch (error) {
    console.error('复制规则失败:', error);
    message.error('复制规则失败，请重试');
  }
};

// 导入规则
const importRule = async () => {
  try {
    // 首先尝试从剪贴板读取
    const clipboardText = await navigator.clipboard.readText();
    if (clipboardText) {
      try {
        const rule = JSON.parse(clipboardText);
        if (validateRule(rule)) {
          parseRuleToConditions(rule);
          message.success('规则已从剪贴板导入');
          return;
        }
      } catch (parseError) {
        console.warn('剪贴板内容不是有效的JSON规则:', parseError);
      }
    }
    
    // 如果剪贴板没有有效规则，提示用户手动输入
    const inputRule = prompt('请输入要导入的规则JSON:');
    if (inputRule) {
      try {
        const rule = JSON.parse(inputRule);
        if (validateRule(rule)) {
          parseRuleToConditions(rule);
          message.success('规则已导入');
        } else {
          message.error('规则格式不正确');
        }
      } catch (parseError) {
        message.error('JSON格式错误，请检查输入内容');
      }
    }
  } catch (error) {
    console.error('导入规则失败:', error);
    message.error('导入规则失败，请重试');
  }
};

// 验证规则格式
const validateRule = (rule) => {
  if (!rule || typeof rule !== 'object') {
    return false;
  }
  
  const keys = Object.keys(rule);
  if (keys.length === 0) {
    return false;
  }
  
  // 检查是否是有效的JSON Logic规则格式
  const validOperators = ['and', 'or', '==', '!=', '>', '<', '>=', '<=', 'in', '!in'];
  const firstKey = keys[0];
  
  if (validOperators.includes(firstKey)) {
    return true;
  }
  
  return false;
};

onMounted(() => {
  initConditions();
});
</script>

<style scoped>
.jsonlogic-rule-editor {
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

/* 图标悬停效果 */
.icon-hover {
  transition: all 0.3s ease;
  border-radius: 4px;
}

.icon-hover:hover {
  background-color: rgba(0, 0, 0, 0.06);
  transform: scale(1.1);
}
</style>
