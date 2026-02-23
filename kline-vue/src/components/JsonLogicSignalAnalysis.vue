<template>
  <a-card title="JSONLogic 信号分析">
    <a-form :model="form" layout="horizontal" :label-col="{ style: { width: '100px' } }">
      <!-- 基础配置 -->
      <a-form-item name="showDays" label="展示天数">
        <a-input-number v-model:value="form.showDays" :min="5" :max="300" style="width: 100px" />
      </a-form-item>

      <!-- 信号分析规则配置 -->
      <a-form-item>
        <JsonLogicRuleEditor :model-value="signalRule" :field-options="stockFieldOptions"
          :operator-names="operatorNames" rule-title="信号分析规则" :default-conditions="defaultSignalConditions"
          :show-preview="false" :show-description="false" @update:modelValue="handleSignalRuleUpdate">
          <template #title>
            <div style="display: flex; align-items: center; gap: 8px; width: 100%;">
              <a-dropdown placement="bottomLeft">
                <a-button type="text" size="small">
                  <DownOutlined />
                </a-button>
                <template #overlay>
                  <a-menu>
                    <a-menu-item v-for="rule in savedRules" :key="rule.name" @click="handleRuleSwitch(rule.name)">
                      {{ rule.name }}
                    </a-menu-item>
                    <a-menu-divider />
                    <a-menu-item key="new" @click="handleCreateRule">新建规则</a-menu-item>
                    <a-menu-item key="delete" danger :disabled="!currentRuleName" @click="deleteRule">删除当前规则</a-menu-item>
                  </a-menu>
                </template>
              </a-dropdown>
              <div
                ref="editableTitleRef"
                contenteditable="true"
                :textContent="currentRuleName || '未命名规则'"
                @input="onTitleInput"
                @blur="onTitleBlur"
                style="
                  outline: none;
                  min-width: 120px;
                  max-width: 60%;
                  padding: 2px 6px;
                  border-radius: 4px;
                "
              ></div>

        
            </div>
          </template>
        </JsonLogicRuleEditor>
      </a-form-item>

      <!-- 分析按钮 -->
      <a-form-item>
        <a-button type="primary" @click="onAnalysis" :loading="loading" style="width: 100%">
          开始 JSONLogic 分析
        </a-button>
      </a-form-item>

      <!-- 统计区域 -->
      <a-form-item label="" v-if="analysisResults.length > 0">
        <div class="summary">
          <a-statistic title="分析股票数" :value="summary.totalStocks" />
          <a-statistic title="符合条件股票数" :value="analysisResults.length" />
          <a-statistic title="当前选择" :value="`${currentIndex + 1}/${analysisResults.length}`" />
        </div>
      </a-form-item>

      <!-- 股票选择器 -->
      <a-form-item label="" v-if="analysisResults.length > 0">
        <div class="summary">
          <StockSelector
            v-model:value="form.code"
            :stocks="analysisResults"
            placeholder="选择股票"
            width="300px"
            :show-signals="true"
            @change="handleStockChange"
          />
        </div>
      </a-form-item>

      <!-- 选中股票信息区域 -->
      <a-form-item label="" v-if="selectedStock">
        <div class="selected-stock-info">
          <a-card size="small" title="选中股票信息">
            <template #extra>
              <a-button type="primary" @click="addToCandidateList" :disabled="!selectedStock">
                加入候选列表
              </a-button>
            </template>
            <a-descriptions :column="2" size="small">
              <a-descriptions-item label="股票代码">{{ selectedStock.code }}</a-descriptions-item>
              <a-descriptions-item label="股票名称">{{ selectedStock.name }}</a-descriptions-item>
              <a-descriptions-item label="收盘价">{{ selectedStock.close_price || selectedStock['收盘'] }}</a-descriptions-item>
              <a-descriptions-item label="交易日期">{{ selectedStock.trade_date || selectedStock['日期'] }}</a-descriptions-item>
              <a-descriptions-item label="买点数量">
                <a-tag color="green">{{ selectedStock.buy_signals || 0 }}</a-tag>
              </a-descriptions-item>
              <a-descriptions-item label="卖点数量">
                <a-tag color="red">{{ selectedStock.sell_signals || 0 }}</a-tag>
              </a-descriptions-item>
              <a-descriptions-item label="总信号数">
                <a-tag color="blue">{{ selectedStock.total_signals || 0 }}</a-tag>
              </a-descriptions-item>
              <a-descriptions-item label="数据行数">{{ selectedStock.data_rows || 1 }}</a-descriptions-item>
            </a-descriptions>
          </a-card>
        </div>
      </a-form-item>

    </a-form>
  </a-card>
</template>

<script setup>
import { ref, reactive, computed, watchEffect, onMounted } from 'vue';
import { message } from 'ant-design-vue';
import { DownOutlined } from '@ant-design/icons-vue';
import JsonLogicRuleEditor from './JsonLogicRuleEditor.vue';
import StockSelector from './StockSelector.vue';
import { queryByJsonLogic } from '@/api/stocks';
import { useCandidateListStore } from '@/stores/candidateList';

// 初始化候选列表store
const candidateListStore = useCandidateListStore();

// 本地存储键名
const RULES_STORAGE_KEY = 'jsonlogic_signal_rules';
const RULES_LAST_USED_KEY = 'jsonlogic_last_rule_name';

// 表单数据
const form = reactive({
  showDays: 180,
  today: '2025-10-09',
  code: ''
});

// 信号分析规则数据
const signalRule = ref({});

// 已保存的规则列表
const savedRules = ref([]);

// 当前选中的规则名称
const currentRuleName = ref('');

// 新规则名称
const newRuleName = ref('');
const editableTitleRef = ref(null);

// 加载状态
const loading = ref(false);

// 分析结果
const analysisResults = ref([]);

// 统计信息
const summary = reactive({
  totalStocks: 0,
  matchedStocks: 0,
  analysisTime: 0
});

// 当前选中的股票
const selectedStock = computed(() => {
  if (!form.code || !analysisResults.value.length) return null;
  return analysisResults.value.find(stock => stock.code === form.code) || null;
});

// 当前股票在列表中的索引
const currentIndex = computed(() => {
  if (!form.code || !analysisResults.value.length) return 0;
  const idx = analysisResults.value.findIndex(stock => stock.code === form.code);
  return idx >= 0 ? idx : 0;
});

// 股票字段配置 - 使用数据库字段名
const stockFieldOptions = [
  // 交易日期
  { value: 'trade_date', label: '交易日期', type: 'date', precision: 0 },
  // 基础价格
  { value: 'close_price', label: '收盘价', type: 'number', precision: 2 },
  { value: 'high_price', label: '最高价', type: 'number', precision: 2 },
  { value: 'low_price', label: '最低价', type: 'number', precision: 2 },
  { value: 'open_price', label: '开盘价', type: 'number', precision: 2 },
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

  { value: 'slope_7', label: '7日斜率', type: 'number', precision: 2 },
  { value: 'fit_7', label: '7日拟合值', type: 'number', precision: 2 },
  { value: 'slope_180', label: '180日斜率', type: 'number', precision: 2 },
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

// 操作符配置
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

// 默认信号分析条件
const defaultSignalConditions = [

  { field: 'trade_date', operator: '>', value: '2025-10-01' },
  { field: 'trade_date', operator: '<', value: '2025-10-24' },
  { field: 'close_price', operator: '<', value: 20 },

];


// 事件定义
const emit = defineEmits(['stock-select', 'analysis-complete']);

// 处理股票选择变化
const handleStockChange = (selectedStock) => {
  if (selectedStock) {
    emit('stock-select', selectedStock);
  }
};

// 加入候选列表功能
const addToCandidateList = () => {
  if (!selectedStock.value) return;
  
  candidateListStore.addStock({
    code: selectedStock.value.code,
    name: selectedStock.value.name
  });
  
  message.success(`已将 ${selectedStock.value.name}(${selectedStock.value.code}) 加入候选列表`);
};



// 加载所有保存的规则（优先加载上次使用规则）
const loadRules = () => {
  try {
    const savedRulesData = localStorage.getItem(RULES_STORAGE_KEY);
    if (savedRulesData) {
      const parsedRules = JSON.parse(savedRulesData);
      if (parsedRules && Array.isArray(parsedRules) && parsedRules.length > 0) {
        savedRules.value = parsedRules;
        console.log('已加载保存的规则列表:', parsedRules);
        // 优先加载上次使用的规则，其次回退到第一个
        const lastUsed = localStorage.getItem(RULES_LAST_USED_KEY);
        let target = null;
        if (lastUsed) {
          target = parsedRules.find(r => r.name === lastUsed) || null;
        }
        if (!target) {
          target = parsedRules[0];
        }
        currentRuleName.value = target.name;
        newRuleName.value = target.name;
        signalRule.value = target.rule;
      }
    }
  } catch (error) {
    console.warn('加载规则列表失败:', error);
    localStorage.removeItem(RULES_STORAGE_KEY);
  }
};

// 保存所有规则到本地存储
const saveRules = () => {
  try {
    localStorage.setItem(RULES_STORAGE_KEY, JSON.stringify(savedRules.value));
    console.log('已保存规则列表到本地存储:', savedRules.value);
  } catch (error) {
    console.warn('保存规则列表失败:', error);
  }
};

// 处理信号规则更新
const handleSignalRuleUpdate = (rule) => {
  signalRule.value = rule;
  // 更新当前规则
  if (currentRuleName.value) {
    const currentRule = savedRules.value.find(r => r.name === currentRuleName.value);
    if (currentRule) {
      currentRule.rule = rule;
      saveRules();
      // 更新上次使用规则
      localStorage.setItem(RULES_LAST_USED_KEY, currentRuleName.value);
    }
  }
};

// 标题编辑相关
const onTitleInput = (e) => {
  newRuleName.value = (e.target?.textContent || '').trim();
};

const onTitleBlur = () => {
  autoSaveRule();
};

// 新建规则
const handleCreateRule = () => {
  console.log('handleCreateRule called');
  const baseName = '新建规则';
  let candidate = baseName;
  let idx = 1;
  while (savedRules.value.some(r => r.name === candidate)) {
    candidate = `${baseName} ${idx++}`;
  }
  newRuleName.value = candidate;
  // 没有配置时也允许创建空规则壳
  if (!signalRule.value || Object.keys(signalRule.value).length === 0) {
    signalRule.value = {};
  }
  autoSaveRule();
  // 聚焦编辑标题
  requestAnimationFrame(() => {
    if (editableTitleRef.value) {
      const el = editableTitleRef.value;
      // 将光标移到末尾
      const range = document.createRange();
      range.selectNodeContents(el);
      range.collapse(false);
      const sel = window.getSelection();
      sel.removeAllRanges();
      sel.addRange(range);
      el.focus();
    }
  });
};

// 切换规则
const handleRuleSwitch = (ruleName) => {
  console.log('handleRuleSwitch called with:', ruleName);
  const rule = savedRules.value.find(r => r.name === ruleName);
  if (rule) {
    signalRule.value = rule.rule;
    currentRuleName.value = ruleName;
    newRuleName.value = ruleName;
    console.log('切换到规则:', ruleName);
    // 记录上次使用规则
    localStorage.setItem(RULES_LAST_USED_KEY, ruleName);
  } else {
    console.warn('规则未找到:', ruleName);
  }
};

// 自动保存/更新规则（名称变更或输入变更时触发）
const autoSaveRule = () => {
  if (!newRuleName.value.trim()) {
    // 没有名称则不保存
    return;
  }
  
  if (!signalRule.value || Object.keys(signalRule.value).length === 0) {
    // 没有规则则不保存
    return;
  }
  
  // 检查规则名称是否已存在
  const existingIndex = savedRules.value.findIndex(r => r.name === newRuleName.value);
  if (existingIndex >= 0) {
    // 更新已存在的规则
    savedRules.value[existingIndex].rule = signalRule.value;
  } else {
    // 添加新规则
    savedRules.value.push({
      name: newRuleName.value,
      rule: signalRule.value
    });
  }
  
  // 切换到新保存的规则
  currentRuleName.value = newRuleName.value;
  
  // 保存到本地存储
  saveRules();
  localStorage.setItem(RULES_LAST_USED_KEY, currentRuleName.value);
};

// 删除规则
const deleteRule = () => {
  console.log('deleteRule called');
  if (!currentRuleName.value) {
    message.warning('请先选择要删除的规则');
    return;
  }
  
  const index = savedRules.value.findIndex(r => r.name === currentRuleName.value);
  if (index >= 0) {
    savedRules.value.splice(index, 1);
    saveRules();
    
    // 切换到第一个规则（如果有）
    if (savedRules.value.length > 0) {
      currentRuleName.value = savedRules.value[0].name;
      newRuleName.value = savedRules.value[0].name;
      signalRule.value = savedRules.value[0].rule;
      localStorage.setItem(RULES_LAST_USED_KEY, currentRuleName.value);
    } else {
      currentRuleName.value = '';
      newRuleName.value = '';
      signalRule.value = {};
      localStorage.removeItem(RULES_LAST_USED_KEY);
    }
    
    message.success('规则已删除');
  }
};

// 将JsonLogic返回的数据转换为StockSelector组件期望的格式
const convertJsonLogicDataToStockFormat = (jsonLogicData) => {
  return jsonLogicData.map(item => {
    // 计算信号数据
    const buySignals = item['7日买点数量'] || item['14日买点数量'] || 0;
    const sellSignals = item['7日卖点数量'] || item['14日卖点数量'] || 0;
    const totalSignals = buySignals + sellSignals;
    
    return {
      code: item['代码'] || item.code,
      name: item['股票名称'] || item.name,
      buy_signals: buySignals,
      sell_signals: sellSignals,
      total_signals: totalSignals,
      data_rows: 1, // JsonLogic返回的是单条记录，所以数据行数为1
      // 保留原始数据用于显示
      close_price: item['收盘'] || item.close_price,
      trade_date: item['日期'] || item.trade_date,
      // 保留所有原始字段
      ...item
    };
  });
};

// 根据股票代码去重，保留最新日期的记录
const deduplicateByCode = (data) => {
  // 使用 Map 来存储每个股票代码的信息
  // key: 股票代码, value: { record: 最新记录, count: 满足条件的记录数 }
  const stockMap = new Map();
  
  data.forEach(item => {
    const code = item.code;
    const currentDate = item.trade_date || item['日期'];
    
    if (!stockMap.has(code)) {
      // 首次遇到该股票代码
      stockMap.set(code, { 
        record: { ...item }, 
        count: 1 
      });
    } else {
      const existing = stockMap.get(code);
      const existingDate = existing.record.trade_date || existing.record['日期'];
      
      // 如果当前日期更新，则更新记录
      if (currentDate > existingDate) {
        existing.record = { ...item };
      }
      // 增加满足条件的记录计数
      existing.count++;
    }
  });
  
  // 将 Map 转换回数组，并更新每个股票的 data_rows
  return Array.from(stockMap.values()).map(({ record, count }) => ({
    ...record,
    data_rows: count
  }));
};




// 执行分析
const onAnalysis = async () => {
  if (!signalRule.value || Object.keys(signalRule.value).length === 0) {
    message.warning('请配置信号分析规则');
    return;
  }

  loading.value = true;
  const startTime = Date.now();

  try {
    // 构建查询参数 - 使用正确的格式
    const payload = {
      table: "stock_daily_k_i_read",
      limit: 0,
      logic: signalRule.value,
      ruleName: currentRuleName.value


    };

    console.log('发送 JSONLogic 查询请求:', JSON.stringify(payload, null, 2));

    // 调用 API
    const response = await queryByJsonLogic(payload);
    console.log('JSONLogic 查询响应:', response);

    // 处理响应数据
    if (response && response.data) {
      // 转换数据格式以适配StockSelector组件
      const convertedData = convertJsonLogicDataToStockFormat(response.data);
      
      // 根据股票代码去重，保留最新日期的记录
      const deduplicatedData = deduplicateByCode(convertedData);
      
      analysisResults.value = deduplicatedData;
      summary.totalStocks = response.total || 0;
      summary.matchedStocks = deduplicatedData.length;
      summary.analysisTime = Date.now() - startTime;

      message.success(`分析完成！找到 ${deduplicatedData.length} 只符合条件的股票（已去重）`);

      // 如果有股票数据，自动选择第一个股票
      if (deduplicatedData && deduplicatedData.length > 0) {
        form.code = deduplicatedData[0].code;
        // 发送股票选择事件
        emit('stock-select', deduplicatedData[0]);
      }

      // 触发分析完成事件
      emit('analysis-complete', {
        results: response.data,
        summary: summary,
        rules: {
          signal: signalRule.value
        }
      });
    } else {
      message.error('分析失败：未获取到有效数据');
    }

  } catch (error) {
    console.error('JSONLogic 分析错误:', error);
    message.error('分析失败：' + (error.message || '未知错误'));
  } finally {
    loading.value = false;
  }
};

// 获取表单数据（供父组件调用）
const getFormData = () => {
  return {
    showDays: form.showDays,
    today: form.today,
    signalRule: signalRule.value
  };
};

// 暴露方法给父组件
defineExpose({
  getFormData,
  onAnalysis
});

// 组件挂载时设置默认值
onMounted(() => {
  // 设置默认的today值
  form.today = new Date().toISOString().split('T')[0];
  // 加载保存的规则列表
  loadRules();
});
</script>

<style scoped>
/* 减小表单项的底部间距 */
:deep(.ant-form-item) {
  margin-bottom: 12px;
}

.summary {
  display: flex;
  justify-content: space-around;
  gap: 24px;
  padding: 16px;
  background: #fafafa;
  border-radius: 6px;
}

.selected-stock-info {
  margin-top: 16px;
}
</style>
