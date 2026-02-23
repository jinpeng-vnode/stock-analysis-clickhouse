<template>
  <div class="config-page">
    <a-row :gutter="24">
      <!-- 左侧配置区域 -->
      <a-col :span="12" class="config-section">
        <!-- 信号分析配置 -->
        <a-card class="config-card">
          <template #title>
            <span>
              <BarChartOutlined style="color: #fa8c16; margin-right: 8px;" />
              信号分析配置
            </span>
          </template>
          <template #extra>
            <a-space>
              <a-switch v-model:checked="config.use_signal_analysis" @change="handleSignalAnalysisToggle"
                checked-children="开启" un-checked-children="关闭" />
              <a-button type="primary" :loading="running" @click="runBacktest">
                <template #icon>
                  <PlayCircleOutlined />
                </template>
                开始回测
              </a-button>
              <a-button @click="goToResults">
                <template #icon>
                  <BarChartOutlined />
                </template>
                查看回测结果
              </a-button>
            </a-space>
          </template>

          <div v-if="config.use_signal_analysis" class="signal-analysis-container">
            <StockSignalAnalysis ref="signalAnalysisRef" @analysis-complete="handleSignalAnalysisComplete"
              @stock-select="handleStockSelect" />
          </div>
          <div v-else class="signal-analysis-disabled">
            <a-empty description="信号分析已关闭，将使用所有可用股票进行回测" :image="Empty.PRESENTED_IMAGE_SIMPLE" />
          </div>
        </a-card>
        <a-form :model="config" layout="vertical">
          <!-- 基础配置 -->
          <a-card class="config-card">
            <template #title>
              <span>
                <SettingOutlined style="color: #1890ff; margin-right: 8px;" />
                基础配置
              </span>
            </template>
            <!-- 基本信息 -->
            <a-row :gutter="16">
              <a-col :span="8">
                <a-form-item>
                  <template #label>
                    <span>
                      <UserOutlined style="color: #1890ff; margin-right: 4px;" />
                      配置名称
                      <a-tooltip title="为回测配置起一个便于识别的名称，用于区分不同的策略配置">
                        <QuestionCircleOutlined style="color: #999; margin-left: 4px; cursor: help;" />
                      </a-tooltip>
                    </span>
                  </template>
                  <a-input v-model:value="config.name" placeholder="请输入配置名称">
                    <template #suffix>
                      <EditOutlined style="color: #1890ff" />
                    </template>
                  </a-input>
                </a-form-item>
              </a-col>
              <a-col :span="8">
                <a-form-item>
                  <template #label>
                    <span>
                      <WalletOutlined style="color: #52c41a; margin-right: 4px;" />
                      初始资金
                      <a-tooltip title="回测开始时的资金总额，用于计算收益率和风险指标">
                        <QuestionCircleOutlined style="color: #999; margin-left: 4px; cursor: help;" />
                      </a-tooltip>
                    </span>
                  </template>
                  <a-input :value="formattedInitialCapital" @input="handleInitialCapitalInput"
                    @blur="validateInitialCapital" style="width: 100%" placeholder="请输入初始资金">
                    <template #addonAfter>
                      <span style="color: #52c41a; font-weight: 500;">元</span>
                    </template>
                  </a-input>
                </a-form-item>
              </a-col>
            </a-row>
            <a-row :gutter="16">
              <a-col :span="8">
                <a-form-item>
                  <template #label>
                    <span>
                      <CalendarIcon2 style="color: #1890ff; margin-right: 4px;" />
                      开始日期
                      <a-tooltip title="回测开始的时间，系统将从这一天开始执行交易策略">
                        <QuestionCircleOutlined style="color: #999; margin-left: 4px; cursor: help;" />
                      </a-tooltip>
                    </span>
                  </template>
                  <a-date-picker v-model:value="config.start_date" style="width: 100%" format="YYYY-MM-DD"
                    placeholder="选择开始日期">
                    <template #suffixIcon>
                      <CalendarOutlined style="color: #1890ff" />
                    </template>
                  </a-date-picker>
                </a-form-item>
              </a-col>
              <a-col :span="8">
                <a-form-item>
                  <template #label>
                    <span>
                      <CalendarIcon2 style="color: #1890ff; margin-right: 4px;" />
                      结束日期
                      <a-tooltip title="回测结束的时间，系统将在这天停止执行交易策略">
                        <QuestionCircleOutlined style="color: #999; margin-left: 4px; cursor: help;" />
                      </a-tooltip>
                    </span>
                  </template>
                  <a-date-picker v-model:value="config.end_date" style="width: 100%" format="YYYY-MM-DD"
                    placeholder="选择结束日期">
                    <template #suffixIcon>
                      <CalendarOutlined style="color: #1890ff" />
                    </template>
                  </a-date-picker>
                </a-form-item>
              </a-col>
            </a-row>

            <!-- 快捷时间选择 -->
            <a-row :gutter="16">
              <a-col :span="24">
                <a-form-item>
                  <template #label>
                    <span>
                      <ClockCircleOutlined style="color: #52c41a; margin-right: 4px;" />
                      快捷选择
                      <a-tooltip title="快速设置常用的时间范围，或自定义天数">
                        <QuestionCircleOutlined style="color: #999; margin-left: 4px; cursor: help;" />
                      </a-tooltip>
                    </span>
                  </template>
                  <div class="quick-time-selector">
                    <a-space wrap>
                      <a-button size="small" @click="setQuickTimeRange('3months')" type="default">
                        3个月
                      </a-button>
                      <a-button size="small" @click="setQuickTimeRange('6months')" type="default">
                        6个月
                      </a-button>
                      <a-button size="small" @click="setQuickTimeRange('1year')" type="default">
                        1年
                      </a-button>
                      <a-button size="small" @click="setQuickTimeRange('2year')" type="default">
                        2年
                      </a-button>
                      <a-button size="small" @click="setQuickTimeRange('5year')" type="default">
                        5年
                      </a-button>
                      <a-button size="small" @click="setQuickTimeRange('10year')" type="default">
                        10年
                      </a-button>


                      <a-input suffix="天" v-model:value="customDays" :min="1" :max="3650" size="small" style="width: 80px;"
                        placeholder="天数" />
                      <a-button size="small" @click="setCustomDays" type="primary">
                        自定义天数
                      </a-button>
                    </a-space>
                  </div>
                </a-form-item>
              </a-col>
            </a-row>

            <!-- 交易成本配置 -->
            <a-row :gutter="16">
              <a-col :span="6">
                <a-form-item>
                  <template #label>
                    <span>
                      <PercentageIcon style="color: #fa8c16; margin-right: 4px;" />
                      佣金率
                      <a-tooltip title="每笔交易收取的佣金比例，通常为万分之几">
                        <QuestionCircleOutlined style="color: #999; margin-left: 4px; cursor: help;" />
                      </a-tooltip>
                    </span>
                  </template>
                  <a-input-number v-model:value="config.commission_rate" :min="0" :max="0.01" :step="0.0001"
                    :precision="4" style="width: 100%" placeholder="佣金率">
                    <template #addonAfter>
                      <span style="color: #fa8c16; font-weight: 500;">%</span>
                    </template>
                  </a-input-number>
                </a-form-item>
              </a-col>
              <a-col :span="6">
                <a-form-item>
                  <template #label>
                    <span>
                      <MinusCircleOutlined style="color: #722ed1; margin-right: 4px;" />
                      最低佣金
                      <a-tooltip title="每笔交易的最低佣金费用，即使按比例计算低于此金额也按此金额收取">
                        <QuestionCircleOutlined style="color: #999; margin-left: 4px; cursor: help;" />
                      </a-tooltip>
                    </span>
                  </template>
                  <a-input-number v-model:value="config.min_commission" :min="0" :max="10" style="width: 100%"
                    placeholder="最低佣金">
                    <template #addonAfter>
                      <span style="color: #722ed1; font-weight: 500;">元</span>
                    </template>
                  </a-input-number>
                </a-form-item>
              </a-col>
              <a-col :span="6">
                <a-form-item>
                  <template #label>
                    <span>
                      <FileTextIcon style="color: #13c2c2; margin-right: 4px;" />
                      印花税率
                      <a-tooltip title="卖出股票时收取的印花税比例，目前A股为千分之一">
                        <QuestionCircleOutlined style="color: #999; margin-left: 4px; cursor: help;" />
                      </a-tooltip>
                    </span>
                  </template>
                  <a-input-number v-model:value="config.stamp_duty_rate" :min="0" :max="0.01" :step="0.0001"
                    :precision="4" style="width: 100%" placeholder="印花税率">
                    <template #addonAfter>
                      <span style="color: #13c2c2; font-weight: 500;">%</span>
                    </template>
                  </a-input-number>
                </a-form-item>
              </a-col>
              <a-col :span="6">
                <a-form-item>
                  <template #label>
                    <span>
                      <SwapIcon style="color: #eb2f96; margin-right: 4px;" />
                      滑点率
                      <a-tooltip title="实际成交价格与预期价格的偏差比例，模拟市场冲击成本">
                        <QuestionCircleOutlined style="color: #999; margin-left: 4px; cursor: help;" />
                      </a-tooltip>
                    </span>
                  </template>
                  <a-input-number v-model:value="config.slippage_rate" :min="0" :max="0.01" :step="0.0001"
                    :precision="4" style="width: 100%" placeholder="滑点率">
                    <template #addonAfter>
                      <span style="color: #eb2f96; font-weight: 500;">%</span>
                    </template>
                  </a-input-number>
                </a-form-item>
              </a-col>
            </a-row>

            <!-- 仓位配置 -->
            <a-row :gutter="16">
              <a-col :span="8">
                <a-form-item>
                  <template #label>
                    <span>
                      <PieChartIcon2 style="color: #1890ff; margin-right: 4px;" />
                      仓位分配方法
                      <a-tooltip title="选择资金分配方式：固定比例按资金比例分配，固定金额按固定金额分配，固定股数按固定股数买入">
                        <QuestionCircleOutlined style="color: #999; margin-left: 4px; cursor: help;" />
                      </a-tooltip>
                    </span>
                  </template>
                  <a-select v-model:value="config.position_config.method" placeholder="选择分配方法">
                    <template #suffixIcon>
                      <PieChartOutlined style="color: #1890ff" />
                    </template>
                    <a-select-option value="fixed_ratio">固定比例</a-select-option>
                    <a-select-option value="fixed_amount">固定金额</a-select-option>
                    <a-select-option value="fixed_quantity">固定股数</a-select-option>
                  </a-select>
                </a-form-item>
              </a-col>
              <a-col :span="8" v-if="config.position_config.method === 'fixed_ratio'">
                <a-form-item>
                  <template #label>
                    <span>
                      <PercentageIcon style="color: #52c41a; margin-right: 4px;" />
                      固定比例
                      <a-tooltip title="每次买入时使用总资金的比例，如0.1表示每次用10%的资金买入">
                        <QuestionCircleOutlined style="color: #999; margin-left: 4px; cursor: help;" />
                      </a-tooltip>
                    </span>
                  </template>
                  <a-input-number v-model:value="config.position_config.ratio" :min="0.01" :max="1" :step="0.01"
                    :precision="2" style="width: 100%" placeholder="固定比例">
                    <template #addonAfter>
                      <span style="color: #52c41a; font-weight: 500;">%</span>
                    </template>
                  </a-input-number>
                </a-form-item>
              </a-col>
              <a-col :span="8" v-if="config.position_config.method === 'fixed_amount'">
                <a-form-item>
                  <template #label>
                    <span>
                      <WalletOutlined style="color: #52c41a; margin-right: 4px;" />
                      固定金额
                      <a-tooltip title="每次买入时使用的固定金额，不受总资金变化影响">
                        <QuestionCircleOutlined style="color: #999; margin-left: 4px; cursor: help;" />
                      </a-tooltip>
                    </span>
                  </template>
                  <a-input-number v-model:value="config.position_config.fixed_amount" :min="1000" :max="1000000"
                    :step="1000" style="width: 100%" placeholder="固定金额">
                    <template #addonAfter>
                      <span style="color: #52c41a; font-weight: 500;">元</span>
                    </template>
                  </a-input-number>
                </a-form-item>
              </a-col>
              <a-col :span="8" v-if="config.position_config.method === 'fixed_quantity'">
                <a-form-item>
                  <template #label>
                    <span>
                      <NumberIcon style="color: #52c41a; margin-right: 4px;" />
                      固定股数
                      <a-tooltip title="每次买入的固定股数，必须是100的倍数（A股交易规则）">
                        <QuestionCircleOutlined style="color: #999; margin-left: 4px; cursor: help;" />
                      </a-tooltip>
                    </span>
                  </template>
                  <a-input-number v-model:value="config.position_config.fixed_quantity" :min="100" :max="10000"
                    :step="100" style="width: 100%" placeholder="固定股数">
                    <template #addonAfter>
                      <span style="color: #52c41a; font-weight: 500;">股</span>
                    </template>
                  </a-input-number>
                </a-form-item>
              </a-col>
            </a-row>
            <a-row :gutter="16">
              <a-col :span="8">
                <a-form-item>
                  <template #label>
                    <span>
                      <PieChartIcon2 style="color: #fa8c16; margin-right: 4px;" />
                      单股最大仓位
                      <a-tooltip title="单只股票的最大仓位比例，防止过度集中投资">
                        <QuestionCircleOutlined style="color: #999; margin-left: 4px; cursor: help;" />
                      </a-tooltip>
                    </span>
                  </template>
                  <a-input-number v-model:value="config.position_config.max_position_per_stock" :min="0.01" :max="1"
                    :step="0.01" :precision="2" style="width: 100%" placeholder="单股最大仓位">
                    <template #addonAfter>
                      <span style="color: #fa8c16; font-weight: 500;">%</span>
                    </template>
                  </a-input-number>
                </a-form-item>
              </a-col>
              <a-col :span="8">
                <a-form-item>
                  <template #label>
                    <span>
                      <NumberIcon style="color: #13c2c2; margin-right: 4px;" />
                      最大持仓股票数
                      <a-tooltip title="同时持有的最大股票数量，控制投资组合的分散程度">
                        <QuestionCircleOutlined style="color: #999; margin-left: 4px; cursor: help;" />
                      </a-tooltip>
                    </span>
                  </template>
                  <a-input-number v-model:value="config.position_config.max_stocks" :min="1" :max="100"
                    style="width: 100%" placeholder="最大持仓股票数">
                    <template #addonAfter>
                      <span style="color: #13c2c2; font-weight: 500;">只</span>
                    </template>
                  </a-input-number>
                </a-form-item>
              </a-col>
              <a-col :span="8">
                <a-form-item>
                  <template #label>
                    <span>
                      <NumberIcon style="color: #eb2f96; margin-right: 4px;" />
                      每日最大购买数
                      <a-tooltip title="每个交易日最多可以买入的股票数量，用于控制交易频率和风险">
                        <QuestionCircleOutlined style="color: #999; margin-left: 4px; cursor: help;" />
                      </a-tooltip>
                    </span>
                  </template>
                  <a-input-number v-model:value="config.max_daily_buy_count" :min="1" :max="100"
                    style="width: 100%" placeholder="每日最大购买数">
                    <template #addonAfter>
                      <span style="color: #eb2f96; font-weight: 500;">只</span>
                    </template>
                  </a-input-number>
                </a-form-item>
              </a-col>
            </a-row>
          </a-card>

          <!-- 交易规则配置 -->
          <a-card class="config-card">
            <template #title>
              <span>
                <ToolOutlined style="color: #52c41a; margin-right: 8px;" />
                交易规则配置
              </span>
            </template>
            <RuleEditor v-model:buy-rule="config.buy_rule" v-model:sell-rule="config.sell_rule"
              @update:buy-rule="handleRuleChange" @update:sell-rule="handleRuleChange" />
          </a-card>

        </a-form>


      </a-col>

      <!-- 右侧交易过程显示区域 -->
      <a-col :span="12" class="trading-section">
        <a-card class="trading-card">
          <template #title>
            <span>
              <BarChartOutlined style="color: #fa8c16; margin-right: 8px;" />
              交易过程
            </span>
          </template>
          <template #extra>
            <a-space>
              <a-button @click="showDetail" size="small" type="primary" :disabled="!currentResult">
                <template #icon>
                  <BarChartOutlined />
                </template>
                查看详情
              </a-button>
              <a-button @click="clearTradingLog" size="small">
                <template #icon>
                  <ClearOutlined />
                </template>
                清空日志
              </a-button>
              <a-button @click="toggleAutoScroll" size="small" :type="autoScroll ? 'primary' : 'default'">
                <template #icon>
                  <VerticalAlignBottomOutlined />
                </template>
                {{ autoScroll ? '关闭' : '开启' }}自动滚动
              </a-button>
            </a-space>
          </template>

          <div class="trading-log" ref="tradingLogRef">
            <div v-if="tradingLogs.length === 0" class="empty-log">
              <a-empty description="暂无交易日志" />
            </div>
            <div v-else class="log-content">
              <div v-for="(log, index) in tradingLogs" :key="index" :class="['log-item', log.type]">
                <span class="log-time">{{ log.time }}</span>
                <span class="log-message">{{ log.message }}</span>
              </div>
            </div>
          </div>
        </a-card>
      </a-col>
    </a-row>

    <!-- 回测详情弹窗 -->
    <a-modal v-model:open="detailVisible" width="90%" :footer="null" @cancel="closeDetail">
      <template #title>
        <span>
          <BarChartOutlined style="color: #1890ff; margin-right: 8px;" />
          回测详情
        </span>
      </template>
      <ResultDetail v-if="currentResult" :result="currentResult" :show-close="false" />
    </a-modal>

  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, nextTick, watch } from 'vue';
import { message, Empty } from 'ant-design-vue';
import { useRouter } from 'vue-router';
import {
  PlayCircleOutlined,
  ClearOutlined,
  VerticalAlignBottomOutlined,
  BarChartOutlined,
  EditOutlined,
  DollarOutlined,
  CalendarOutlined,
  PercentageOutlined,
  MinusOutlined,
  FileTextOutlined,
  SwapOutlined,
  PieChartOutlined,
  NumberOutlined,
  DatabaseOutlined,
  FunctionOutlined,
  SettingOutlined,
  DollarCircleOutlined,
  CalendarOutlined as CalendarIcon,
  PieChartOutlined as PieChartIcon,
  ToolOutlined,
  QuestionCircleOutlined,
  UserOutlined,
  WalletOutlined,
  CalendarOutlined as CalendarIcon2,
  PercentageOutlined as PercentageIcon,
  MinusCircleOutlined,
  FileTextOutlined as FileTextIcon,
  SwapOutlined as SwapIcon,
  PieChartOutlined as PieChartIcon2,
  NumberOutlined as NumberIcon,
  ClockCircleOutlined
} from '@ant-design/icons-vue';
import dayjs from 'dayjs';
import RuleEditor from './RuleEditor.vue';
import BacktestEngine from '../core/BacktestEngine';
import { loadStockData } from '../utils/dataLoader';
import storage from '../utils/storage';
import ResultDetail from '../result/detail.vue';
import StockSignalAnalysis from '../../kline-analysis/StockSignalAnalysis.vue';

const emit = defineEmits(['run-backtest']);
const router = useRouter();

// 格式化初始资金显示
const formattedInitialCapital = computed(() => {
  if (!config.initial_capital && config.initial_capital !== 0) return '';
  const num = Number(config.initial_capital);
  if (isNaN(num)) return '';
  return num.toLocaleString('zh-CN');
});

// 处理初始资金输入
const handleInitialCapitalInput = (event) => {
  const value = event.target.value;
  // 只允许数字和逗号
  const cleanValue = value.replace(/[^\d,]/g, '');
  // 解析数字
  const num = parseFloat(cleanValue.replace(/,/g, ''));
  if (!isNaN(num)) {
    config.initial_capital = num;
  }
};

// 验证初始资金
const validateInitialCapital = () => {
  const value = Number(config.initial_capital);
  if (isNaN(value) || value === 0) {
    config.initial_capital = 100000;
    return;
  }

  if (value < 1000) {
    config.initial_capital = 1000;
    message.warning('初始资金不能少于1000元');
  } else if (value > 10000000) {
    config.initial_capital = 10000000;
    message.warning('初始资金不能超过1000万元');
  }
};

// 跳转到回测结果页面
const goToResults = () => {
  router.push('/backtest/results');
};

// 配置数据
const config = reactive({
  id: `bt_${Date.now()}`,
  name: '默认回测配置',
  initial_capital: 100000,
  start_date: dayjs('2024-04-01'),
  end_date: dayjs('2024-06-30'),
  commission_rate: 0.0003,
  min_commission: 5,
  stamp_duty_rate: 0.001,
  slippage_rate: 0.001,
  use_signal_analysis: false, // 是否使用信号分析
  signal_analysis_result: null, // 信号分析结果
  buy_rule: {
    "and": [
      { "<": [{ "var": "wr6" }, 20] },   // WR6 < 20 表示超卖，买入信号
      { ">": [{ "var": "close" }, 3] },  // 价格 > 3元
      { "<": [{ "var": "close" }, 100] } // 价格 < 100元
    ]
  },
  sell_rule: {
    "or": [
      { "==": [{ "var": "best_sell" }, true] },
      { "<": [{ "var": "profit_pct" }, -0.02] },
      { ">": [{ "var": "profit_pct" }, 0.05] },
      { "<": [{ "var": "wr6" }, -90] }
    ]
  },
  position_config: {
    method: 'fixed_ratio',
    ratio: 0.1,
    fixed_amount: 10000,
    fixed_quantity: 100,
    max_position_per_stock: 0.3,
    max_stocks: 10
  },
  max_daily_buy_count: 5, // 每日最大购买数限制
  created_at: new Date().toISOString()
});

// 回测状态
const running = ref(false);

// 交易日志相关
const tradingLogs = ref([]);
const tradingLogRef = ref(null);
const autoScroll = ref(true);

// 回测详情弹窗相关
const detailVisible = ref(false);
const currentResult = ref(null);

// 信号分析相关
const signalAnalysisRef = ref(null);

// 快捷时间选择相关
const customDays = ref(30);

// 监听配置变化，自动保存
watch(() => config, () => {
  // 使用防抖，避免频繁保存
  if (saveConfigTimer) {
    clearTimeout(saveConfigTimer);
  }
  saveConfigTimer = setTimeout(() => {
    saveConfigToLocal();
  }, 1000); // 1秒后保存
}, { deep: true });

let saveConfigTimer = null;

// 运行回测
const runBacktest = async () => {
  try {
    running.value = true;

    // 清空之前的日志
    clearTradingLog();

    console.log('🚀 准备运行回测...');
    addTradingLog('🚀 开始运行回测...', 'info');

    // 转换日期格式
    const startDate = dayjs(config.start_date).format('YYYY-MM-DD');
    const endDate = dayjs(config.end_date).format('YYYY-MM-DD');

    addTradingLog(`📅 回测日期范围: ${startDate} 至 ${endDate}`, 'info');
    addTradingLog(`💰 初始资金: ${config.initial_capital.toLocaleString()}元`, 'info');

    // 加载数据
    message.loading('正在加载股票数据...', 0);
    addTradingLog('📡 开始加载股票数据...', 'info');

    let stockData;
    if (config.use_signal_analysis && config.signal_analysis_result && config.signal_analysis_result.stocks.length > 0) {
      // 使用信号分析的结果
      const stockCodes = config.signal_analysis_result.stocks.map(stock => stock.code);
      addTradingLog(`📊 使用信号分析结果，共 ${stockCodes.length} 只股票`, 'info');
      stockData = await loadStockData(startDate, endDate, stockCodes, addTradingLog, config.buy_rule);
    } else {
      // 使用原有方式加载所有股票
      addTradingLog('📊 使用默认方式加载所有股票', 'info');
      stockData = await loadStockData(startDate, endDate, null, addTradingLog, config.buy_rule);
    }
    message.destroy();

    if (!stockData || stockData.length === 0) {
      message.error('没有可用的股票数据');
      addTradingLog('❌ 没有可用的股票数据', 'error');
      return;
    }

    message.success(`数据加载完成，共 ${stockData.length} 条记录`);
    addTradingLog(`✅ 数据加载完成，共 ${stockData.length} 条记录`, 'success');

    // 创建回测引擎
    const engineConfig = {
      ...config,
      start_date: startDate,
      end_date: endDate
    };
    const engine = new BacktestEngine(engineConfig);

    // 设置日志回调
    engine.setLogCallback(addTradingLog);

    addTradingLog('🔧 回测引擎初始化完成', 'info');

    // 运行回测
    addTradingLog('⚡ 开始执行回测策略...', 'info');
    const result = await engine.run(stockData, (p) => {
      // 添加进度日志
      if (p.progress % 10 === 0) { // 每10%显示一次进度
        addTradingLog(`📊 回测进度: ${Math.floor(p.progress)}% - 当前日期: ${p.date}`, 'info');
      }
    });

    console.log('📊 回测结果:', result);

    // 添加回测结果日志
    addTradingLog(`🎯 回测完成！总收益率: ${(result.total_return * 100).toFixed(2)}%`, 'success');
    addTradingLog(`💰 最终资金: ${result.final_capital.toLocaleString()}元`, 'success');
    addTradingLog(`📈 交易次数: ${result.total_trades}次`, 'info');
    addTradingLog(`🎲 胜率: ${(result.win_rate * 100).toFixed(2)}%`, 'info');

    // 保存结果
    storage.saveResult(result);
    addTradingLog('💾 回测结果已保存', 'success');

    message.success('回测完成！');
    addTradingLog('✅ 回测完成，可以点击"查看详情"查看详细结果', 'success');

    // 保存当前结果供详情弹窗使用
    currentResult.value = result;
  } catch (error) {
    console.error('回测失败:', error);
    addTradingLog(`❌ 回测失败: ${error.message}`, 'error');
    message.error('回测失败: ' + error.message);
  } finally {
    running.value = false;
  }
};


// 添加交易日志
const addTradingLog = (message, type = 'info') => {
  const log = {
    time: new Date().toLocaleTimeString(),
    message,
    type
  };
  tradingLogs.value.push(log);

  // 自动滚动到底部
  if (autoScroll.value) {
    nextTick(() => {
      if (tradingLogRef.value) {
        tradingLogRef.value.scrollTop = tradingLogRef.value.scrollHeight;
      }
    });
  }
};

// 清空交易日志
const clearTradingLog = () => {
  tradingLogs.value = [];
};

// 切换自动滚动
const toggleAutoScroll = () => {
  autoScroll.value = !autoScroll.value;
};

// 查看回测详情
const showDetail = () => {
  if (currentResult.value) {
    detailVisible.value = true;
  } else {
    message.warning('暂无回测结果，请先运行回测');
  }
};

// 关闭详情弹窗
const closeDetail = () => {
  detailVisible.value = false;
};

// 信号分析开关切换
const handleSignalAnalysisToggle = (checked) => {
  console.log('信号分析开关:', checked);
  if (checked) {
    addTradingLog('📊 信号分析已开启，请配置筛选条件', 'info');
  } else {
    addTradingLog('📊 信号分析已关闭，将使用所有可用股票', 'info');
    config.signal_analysis_result = null;
  }
};

// 信号分析完成事件
const handleSignalAnalysisComplete = (data) => {
  console.log('信号分析完成:', data);
  config.signal_analysis_result = data.analysisResult;
  addTradingLog(`📊 信号分析完成，找到 ${data.analysisResult.stocks.length} 只符合条件的股票`, 'success');
};

// 股票选择事件
const handleStockSelect = (stock) => {
  console.log('选中股票:', stock);
  if (stock) {
    addTradingLog(`📈 当前选中: ${stock.name}(${stock.code})`, 'info');
  }
};

// 交易规则变化事件
const handleRuleChange = () => {
  console.log('交易规则已更新');
  addTradingLog('📝 交易规则已更新', 'info');
  // 自动保存配置
  saveConfigToLocal();
};

// 自动保存配置到本地存储
const saveConfigToLocal = () => {
  try {
    const configToSave = {
      ...config,
      id: config.id || `config_${Date.now()}`,
      start_date: dayjs(config.start_date).format('YYYY-MM-DD'),
      end_date: dayjs(config.end_date).format('YYYY-MM-DD'),
      created_at: new Date().toISOString()
    };

    console.log('💾 自动保存配置:', configToSave.name);
    storage.saveConfig(configToSave);
  } catch (error) {
    console.error('❌ 自动保存配置失败:', error);
  }
};

// 快捷时间选择功能
const setQuickTimeRange = (range) => {
  const today = dayjs();
  let startDate, endDate;

  switch (range) {
    case '3months':
      startDate = today.subtract(3, 'month');
      endDate = today;
      break;
    case '6months':
      startDate = today.subtract(6, 'month');
      endDate = today;
      break;
    case '1year':
      startDate = today.subtract(1, 'year');
      endDate = today;
      break;
    case '2years':
      startDate = today.subtract(2, 'year');
      endDate = today;
      break;
    case '3years':
      startDate = today.subtract(3, 'year');
      endDate = today;
      break;
    default:
      return;
  }

  config.start_date = startDate;
  config.end_date = endDate;

  // 添加日志
  const rangeText = {
    '3months': '3个月',
    '6months': '6个月',
    '1year': '1年',
    '2years': '2年',
    '3years': '3年'
  }[range];

  addTradingLog(`📅 已设置时间范围: ${rangeText} (${startDate.format('YYYY-MM-DD')} 至 ${endDate.format('YYYY-MM-DD')})`, 'info');
};

// 自定义天数设置
const setCustomDays = () => {
  if (!customDays.value || customDays.value < 1) {
    message.warning('请输入有效的天数');
    return;
  }

  const today = dayjs();
  const startDate = today.subtract(customDays.value, 'day');
  const endDate = today;

  config.start_date = startDate;
  config.end_date = endDate;

  addTradingLog(`📅 已设置自定义时间范围: ${customDays.value}天 (${startDate.format('YYYY-MM-DD')} 至 ${endDate.format('YYYY-MM-DD')})`, 'info');
};

// 页面初始化时自动加载最新配置
onMounted(() => {
  console.log('🔄 开始初始化回测系统...');

  // 添加初始日志
  addTradingLog('回测系统已初始化', 'success');

  // 尝试加载最新保存的配置
  const configs = storage.getAllConfigs();
  console.log('📋 找到的配置数量:', configs.length);

  if (configs.length > 0) {
    const latestConfig = configs[0];
    console.log('🔄 准备加载最新配置:', latestConfig);
    try {
      Object.assign(config, {
        ...latestConfig,
        start_date: dayjs(latestConfig.start_date),
        end_date: dayjs(latestConfig.end_date)
      });
      console.log('✅ 自动加载最新配置成功:', latestConfig.name);
      addTradingLog(`📁 已加载配置: ${latestConfig.name}`, 'success');
    } catch (error) {
      console.error('❌ 加载配置失败:', error);
      addTradingLog('❌ 加载配置失败，使用默认配置', 'warning');
    }
  } else {
    console.log('📝 未找到保存的配置，使用默认配置');
    addTradingLog('📝 使用默认配置', 'info');
  }
});
</script>

<style scoped>
.config-page {
  height: 100%;
}

.config-section {
  padding-right: 12px;
}

.trading-section {
  padding-left: 12px;
}

.config-card {
  margin-bottom: 16px;
}

.trading-card {
  height: 100%;
  display: flex;
  flex-direction: column;
}

.trading-log {
  flex: 1;
  overflow-y: auto;
  max-height: calc(100vh - 300px);
  border: 1px solid #f0f0f0;
  border-radius: 6px;
  background: #fafafa;
}

.empty-log {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 200px;
}

.log-content {
  padding: 8px;
}

.log-item {
  display: flex;
  align-items: flex-start;
  margin-bottom: 4px;
  padding: 4px 8px;
  border-radius: 4px;
  font-size: 12px;
  line-height: 1.4;
}

.log-item.info {
  background: #e6f7ff;
  border-left: 3px solid #1890ff;
}

.log-item.success {
  background: #f6ffed;
  border-left: 3px solid #52c41a;
}

.log-item.error {
  background: #fff2f0;
  border-left: 3px solid #ff4d4f;
}

.log-item.warning {
  background: #fffbe6;
  border-left: 3px solid #faad14;
}

.log-time {
  color: #666;
  margin-right: 8px;
  min-width: 60px;
  font-family: monospace;
}

.log-message {
  flex: 1;
  word-break: break-word;
}

.signal-analysis-container {
  /* 移除StockSignalAnalysis组件的外层card样式 */
  position: relative;
}

.signal-analysis-container :deep(.ant-card) {
  margin: 0;
  box-shadow: none;
  border: none;
}

.signal-analysis-container :deep(.ant-card-head) {
  display: none;
  /* 隐藏StockSignalAnalysis的标题，因为外层已经有标题了 */
}

.signal-analysis-container :deep(.ant-card-body) {
  padding: 0;
}

.signal-analysis-disabled {
  padding: 20px;
  text-align: center;
}

.quick-time-selector {
  padding: 8px 0;
}

.quick-time-selector .ant-space {
  width: 100%;
}

.quick-time-selector .ant-btn {
  margin-right: 8px;
  margin-bottom: 4px;
}

.quick-time-selector .ant-input-number {
  margin-right: 8px;
}
</style>
