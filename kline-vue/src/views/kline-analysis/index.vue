<template>
  <a-config-provider :locale="zhCN">
    <div class="test-page">
      <div class="left">

        <a-card title="信号分析" style="margin-bottom: 16px;">
          <template #extra>
            <a-radio-group v-model:value="selectedAnalyzer" button-style="solid" size="small">
              <a-radio-button value="signal">信号分析</a-radio-button>
              <a-radio-button value="jsonlogic">JSONLogic分析</a-radio-button>
            </a-radio-group>
          </template>
        </a-card>

        <!-- 信号分析组件 -->
        <stock-signal-analysis 
          v-if="selectedAnalyzer === 'signal'"
          ref="signalAnalysisRef" 
          @stock-select="handleStockSelect"
          style="margin-bottom: 16px;"
          @analysis-complete="handleAnalysisComplete" />

        <!-- JSONLogic 信号分析组件 -->
        <JsonLogicSignalAnalysis 
          v-if="selectedAnalyzer === 'jsonlogic'"
          ref="jsonLogicAnalysisRef" 
          @stock-select="handleJsonLogicStockSelect"
          @analysis-complete="handleJsonLogicAnalysisComplete" />











        <!-- 模拟交易组件 -->
        <SimulatedTrading :selected-code="selectedCode" :today="today" />







      </div>
      <div class="right">
        <vue2-kline-chart :code="selectedCode" :show-days="Number(showDays)" :today="today" />
      </div>
      <div class="ai-right">
        <FlowCard :code="selectedCode" display-mode="charts" style="margin-bottom: 16px;" />
        <AIAnalysis :stockCode="selectedCode" :stockName="selectedStockName" />
      </div>
    </div>
  </a-config-provider>
</template>

<script>
import Vue2KlineChart from "./vue2-kline-chart.vue";
import StockSignalAnalysis from "./StockSignalAnalysis.vue";
import JsonLogicSignalAnalysis from "@/components/JsonLogicSignalAnalysis.vue";
import AnalysisComparison from "@/components/AnalysisComparison.vue";
import SimulatedTrading from "./SimulatedTrading.vue";
import AIAnalysis from "./AIAnalysis.vue";
import FlowCard from "@/views/flow/FlowCard.vue";
import { ConfigProvider } from 'ant-design-vue';
// @ts-ignore
import zhCN from 'ant-design-vue/es/locale/zh_CN';

export default {
  name: 'NewPage',
  components: {
    Vue2KlineChart,
    StockSignalAnalysis,
    JsonLogicSignalAnalysis,
    AnalysisComparison,
    SimulatedTrading,
    AIAnalysis,
    FlowCard,
    ConfigProvider
  },
  data() {
    return {
      zhCN,
      selectedCode: '000001',
      selectedStockName: '',
      showDays: 180,
      today: '2025-10-09',
      selectedAnalyzer: 'signal', // 默认使用信号分析器
      // JSONLogic 分析结果
      jsonLogicResults: {
        results: [],
        summary: {},
        rules: {
          signal: {}
        }
      },
    }
  },
  methods: {
    handleStockSelect(stock) {
      console.log('收到股票选择事件:', stock)
      if (stock) {
        this.selectedCode = stock.code
        this.selectedStockName = stock.name || ''
        console.log('更新 selectedCode:', this.selectedCode, 'selectedStockName:', this.selectedStockName)
      }
    },
    handleAnalysisComplete(data) {
      // 从信号分析组件获取表单数据
      const formData = this.$refs.signalAnalysisRef.getFormData()
      this.showDays = formData.showDays
      this.today = formData.today
    },
    // 处理 JSONLogic 股票选择
    handleJsonLogicStockSelect(stock) {
      console.log('收到 JSONLogic 股票选择事件:', stock)
      if (stock) {
        this.selectedCode = stock.code
        this.selectedStockName = stock.name || ''
        console.log('更新 selectedCode:', this.selectedCode, 'selectedStockName:', this.selectedStockName)
      }
    },
    // 处理 JSONLogic 分析完成
    handleJsonLogicAnalysisComplete(data) {
      console.log('收到 JSONLogic 分析完成事件:', data)
      this.jsonLogicResults = data

      // 从 JSONLogic 分析组件获取表单数据
      const formData = this.$refs.jsonLogicAnalysisRef.getFormData()
      this.showDays = formData.showDays
      this.today = formData.today
    }
  }
}
</script>

<style scoped>
.test-page {
  width: 100%;
 
  display: flex;
  flex-direction: row;

}

.left {
  width: 600px;
  padding: 16px;
  box-sizing: border-box;


}

.right {
  flex: 1;
  height: 100%;
  margin: 16px;
  margin-left: 0px;
  box-sizing: border-box;
  overflow: auto;
  background: #fff;
}

.ai-right {
  width: 400px;
  padding: 16px;
  padding-left: 0px;
  box-sizing: border-box;
  height: 100%;
  overflow: auto;
  display: flex;
  flex-direction: column;
}

/* 减小表单项的底部间距 */
:deep(.ant-form-item) {
  margin-bottom: 12px;
}
</style>
