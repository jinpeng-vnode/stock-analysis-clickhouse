<template>
  <a-card title="AI分析">
    <template #extra>
      <a-button type="text" size="small" @click="showFullscreen = true">
        <template #icon>
          <ExpandOutlined />
        </template>
        放大
      </a-button>
    </template>
    <div class="ai-analysis-content">
      <McLayout class="chat-container">
        <McLayoutContent class="content-container" v-if="messages.length > 0">
          <template v-for="(msg, idx) in messages" :key="idx">
            <McBubble v-if="msg.from === 'user'" :align="'right'"
              :avatarConfig="{ imgSrc: 'https://matechat.gitcode.com/png/demo/userAvatar.svg' }">
              <McMarkdownCard v-if="msg.content" :content="msg.content" :theme="'light'" :typing="false" />
            </McBubble>
            <McBubble v-else :avatarConfig="{ imgSrc: 'https://matechat.gitcode.com/logo.svg' }" :loading="msg.loading">
              <McMarkdownCard v-if="msg.content" :content="msg.content" :theme="'light'" :typing="true"
                :enableThink="true"
                :typingOptions="typingOptions" />
            </McBubble>
          </template>
        </McLayoutContent>
        <McLayoutContent v-else
          style="display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 12px; min-height: 300px;">
          <McIntroduction :logoImg="'https://matechat.gitcode.com/logo2x.svg'" :title="'AI分析助手'"
            :subTitle="'Hi，我可以帮您分析股票相关问题'" :description="description" />
          <McPrompt :list="introPrompt.list" class="intro-prompt" @itemClick="handlePromptClick($event)" />
        </McLayoutContent>

        <McLayoutSender>
          <McInput :value="inputValue" :maxLength="2000" @change="(e) => (inputValue = e)" @submit="onSubmit">
            <template #extra>
              <div class="input-foot-wrapper">
                <div class="input-foot-left">
                  <span class="input-foot-maxlength">{{ inputValue.length }}/2000</span>
                </div>
                <div class="input-foot-right">
                  <a-button type="text" size="small" :disabled="!inputValue" @click="inputValue = ''">
                    清空输入
                  </a-button>
                  <a-button type="text" size="small" @click="handleClear">
                    新建对话
                  </a-button>
                </div>
              </div>
            </template>
          </McInput>
        </McLayoutSender>
      </McLayout>
    </div>

    <!-- 全屏模态框 -->
    <a-modal
      v-model:open="showFullscreen"
      title="AI分析 - 全屏查看"
      :footer="null"
      :width="'95vw'"
      @cancel="showFullscreen = false"
    >
      <div class="ai-analysis-content" style="min-height: 80vh;">
        <McLayout class="chat-container">
          <McLayoutContent class="content-container" v-if="messages.length > 0">
            <template v-for="(msg, idx) in messages" :key="idx">
              <McBubble v-if="msg.from === 'user'" :align="'right'"
                :avatarConfig="{ imgSrc: 'https://matechat.gitcode.com/png/demo/userAvatar.svg' }">
                <McMarkdownCard v-if="msg.content" :content="msg.content" :theme="'light'" :typing="false" />
              </McBubble>
              <McBubble v-else :avatarConfig="{ imgSrc: 'https://matechat.gitcode.com/logo.svg' }" :loading="msg.loading">
                <McMarkdownCard v-if="msg.content" :content="msg.content" :theme="'light'" :typing="true"
                  :enableThink="true"
                  :typingOptions="typingOptions" />
              </McBubble>
            </template>
          </McLayoutContent>
          <McLayoutContent v-else
            style="display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 12px; min-height: 300px;">
            <McIntroduction :logoImg="'https://matechat.gitcode.com/logo2x.svg'" :title="'AI分析助手'"
              :subTitle="'Hi，我可以帮您分析股票相关问题'" :description="description" />
            <McPrompt :list="introPrompt.list" class="intro-prompt" @itemClick="handlePromptClick($event)" />
          </McLayoutContent>

          <McLayoutSender>
            <McInput :value="inputValue" :maxLength="2000" @change="(e) => (inputValue = e)" @submit="onSubmit">
              <template #extra>
                <div class="input-foot-wrapper">
                  <div class="input-foot-left">
                    <span class="input-foot-maxlength">{{ inputValue.length }}/2000</span>
                  </div>
                  <div class="input-foot-right">
                    <a-button type="text" size="small" :disabled="!inputValue" @click="inputValue = ''">
                      清空输入
                    </a-button>
                    <a-button type="text" size="small" @click="handleClear">
                      新建对话
                    </a-button>
                  </div>
                </div>
              </template>
            </McInput>
          </McLayoutSender>
        </McLayout>
      </div>
    </a-modal>
  </a-card>
</template>

<script>
import { ExpandOutlined } from '@ant-design/icons-vue';
import { getStockDailyData, getStockMoneyFlow } from '@/api/stocks';
import { getStockFinancialReports } from '@/api/financialReports';

export default {
  name: 'AIAnalysis',
  components: {
    ExpandOutlined
  },
  props: {
    stockCode: {
      type: String,
      default: ''
    },
    stockName: {
      type: String,
      default: ''
    }
  },
  data() {
    return {
      inputValue: '',
      messages: [],
      loading: false,
      abortController: null,
      showFullscreen: false, // 全屏显示状态
      description: [
        '我可以帮您分析股票相关问题，提供投资建议和技术分析。',
        '作为AI模型，我提供的答案仅供参考，投资有风险，请谨慎决策。',
      ],
      typingOptions: {
        interval: 50,
        step: 1,
      },
      introPrompt: {
        direction: 'vertical',
        list: []
      },

    }
  },
  computed: {
    stockDisplayText() {
      if (this.stockCode && this.stockName) {
        return `${this.stockName}(${this.stockCode})`
      }
      return ''
    }
  },
  watch: {
    stockCode: {
      immediate: true,
      handler() {
        this.updatePrompts()
      }
    },
    stockName: {
      immediate: true,
      handler() {
        this.updatePrompts()
      }
    }
  },
  methods: {
    /**
     * 获取1年日线数据
     */
    async fetchDailyData(code) {
      const endDate = new Date();
      const startDate = new Date();
      startDate.setFullYear(endDate.getFullYear() - 1);
      
      const start = startDate.toISOString().split('T')[0];
      const end = endDate.toISOString().split('T')[0];
      
      // axios拦截器已经返回了response.data，所以response就是数据对象
      const response = await getStockDailyData(code, { start, end });
      console.log('日线数据响应:', response);
      return response; // 返回整个响应对象，包含data字段
    },
    /**
     * 获取资金流向数据
     */
    async fetchMoneyFlowData(code) {
      const endDate = new Date();
      const startDate = new Date();
      startDate.setFullYear(endDate.getFullYear() - 1);
      
      const start_date = startDate.toISOString().split('T')[0];
      const end_date = endDate.toISOString().split('T')[0];
      
      // axios拦截器已经返回了response.data，所以response就是数据对象
      const response = await getStockMoneyFlow(code, { start_date, end_date, limit: 365 });
      console.log('资金流向数据响应:', response);
      return response; // 返回整个响应对象，包含data字段
    },
    /**
     * 获取财报信息
     */
    async fetchFinancialReports(code) {
      const endDate = new Date();
      const startDate = new Date();
      startDate.setFullYear(endDate.getFullYear() - 5); // 获取5年财报数据
      
      const start_date = startDate.toISOString().split('T')[0];
      const end_date = endDate.toISOString().split('T')[0];
      
      // 获取所有财报数据，不分页
      // axios拦截器已经返回了response.data，所以response就是数据对象
      const response = await getStockFinancialReports(code, { 
        start_date, 
        end_date, 
        page: 1, 
        size: 200 
      });
      console.log('财报数据响应:', response);
      return response; // 返回整个响应对象，包含items字段
    },
    /**
     * 格式化日线数据为文本
     */
    formatDailyData(dailyData) {
      if (!dailyData || !dailyData.data || dailyData.data.length === 0) {
        return '暂无日线数据';
      }
      
      const data = dailyData.data;
      
      let text = `\n## 日线数据（近1年，共${data.length}个交易日）\n\n`;
      
      // 显示所有交易日的数据
      data.forEach((item, index) => {
        text += `### ${item['日期'] || item.trade_date}\n`;
        text += `- 开盘价：${item['开盘'] || item.open_price}元\n`;
        text += `- 收盘价：${item['收盘'] || item.close_price}元\n`;
        text += `- 最高价：${item['最高'] || item.high_price}元\n`;
        text += `- 最低价：${item['最低'] || item.low_price}元\n`;
        text += `- 成交量：${item['成交量'] || item.volume}手\n`;
        text += `- 成交额：${item['成交额'] || item.amount}元\n`;
        if (item['涨跌幅'] !== null && item['涨跌幅'] !== undefined) {
          text += `- 涨跌幅：${item['涨跌幅'] || item.change_pct}%\n`;
        }
        if (item['换手率'] !== null && item['换手率'] !== undefined) {
          text += `- 换手率：${item['换手率'] || item.turnover_rate}%\n`;
        }
        if (item['振幅'] !== null && item['振幅'] !== undefined) {
          text += `- 振幅：${item['振幅'] || item.amplitude}%\n`;
        }
        if (item['涨跌额'] !== null && item['涨跌额'] !== undefined) {
          text += `- 涨跌额：${item['涨跌额'] || item.change_amount}元\n`;
        }
        if (item['MA5'] !== null && item['MA5'] !== undefined) {
          text += `- MA5：${item['MA5'] || item.ma5}元\n`;
        }
        if (item['MA10'] !== null && item['MA10'] !== undefined) {
          text += `- MA10：${item['MA10'] || item.ma10}元\n`;
        }
        if (item['MA20'] !== null && item['MA20'] !== undefined) {
          text += `- MA20：${item['MA20'] || item.ma20}元\n`;
        }
        if (item['WR6'] !== null && item['WR6'] !== undefined) {
          text += `- WR6：${item['WR6'] || item.wr6}\n`;
        }
        if (item['WR10'] !== null && item['WR10'] !== undefined) {
          text += `- WR10：${item['WR10'] || item.wr10}\n`;
        }
        text += '\n';
      });
      
      return text;
    },
    /**
     * 格式化资金流向数据为文本
     */
    formatMoneyFlowData(moneyFlowData) {
      if (!moneyFlowData || !moneyFlowData.data || moneyFlowData.data.length === 0) {
        return '暂无资金流向数据';
      }
      
      const data = moneyFlowData.data;
      
      let text = `\n## 资金流向数据（近1年，共${data.length}个交易日）\n\n`;
      
      // 显示所有交易日的数据
      data.forEach((item, index) => {
        text += `### ${item.trade_date}\n`;
        text += `- 收盘价：${item.close_price}元\n`;
        if (item.change_pct !== null && item.change_pct !== undefined) {
          text += `- 涨跌幅：${item.change_pct}%\n`;
        }
        if (item.main_net_inflow_amount !== null && item.main_net_inflow_amount !== undefined) {
          text += `- 主力净流入：${item.main_net_inflow_amount}元`;
          if (item.main_net_inflow_ratio !== null && item.main_net_inflow_ratio !== undefined) {
            text += `（${item.main_net_inflow_ratio}%）`;
          }
          text += '\n';
        }
        if (item.super_large_net_inflow_amount !== null && item.super_large_net_inflow_amount !== undefined) {
          text += `- 超大单净流入：${item.super_large_net_inflow_amount}元`;
          if (item.super_large_net_inflow_ratio !== null && item.super_large_net_inflow_ratio !== undefined) {
            text += `（${item.super_large_net_inflow_ratio}%）`;
          }
          text += '\n';
        }
        if (item.large_net_inflow_amount !== null && item.large_net_inflow_amount !== undefined) {
          text += `- 大单净流入：${item.large_net_inflow_amount}元`;
          if (item.large_net_inflow_ratio !== null && item.large_net_inflow_ratio !== undefined) {
            text += `（${item.large_net_inflow_ratio}%）`;
          }
          text += '\n';
        }
        if (item.medium_net_inflow_amount !== null && item.medium_net_inflow_amount !== undefined) {
          text += `- 中单净流入：${item.medium_net_inflow_amount}元`;
          if (item.medium_net_inflow_ratio !== null && item.medium_net_inflow_ratio !== undefined) {
            text += `（${item.medium_net_inflow_ratio}%）`;
          }
          text += '\n';
        }
        if (item.small_net_inflow_amount !== null && item.small_net_inflow_amount !== undefined) {
          text += `- 小单净流入：${item.small_net_inflow_amount}元`;
          if (item.small_net_inflow_ratio !== null && item.small_net_inflow_ratio !== undefined) {
            text += `（${item.small_net_inflow_ratio}%）`;
          }
          text += '\n';
        }
        text += '\n';
      });
      
      return text;
    },
    /**
     * 格式化财报数据为文本
     */
    formatFinancialReports(financialReports) {
      // 财报数据字段是items而不是data
      const reports = financialReports?.items || financialReports?.data || [];
      if (!reports || reports.length === 0) {
        return '暂无财报数据';
      }
      
      let text = `\n## 财报数据（共${reports.length}份报告）\n\n`;
      
      // 按报告日期排序，最新的在前
      const sortedReports = [...reports].sort((a, b) => {
        const dateA = new Date(a.report_date);
        const dateB = new Date(b.report_date);
        return dateB - dateA;
      });
      
      // 显示所有财报数据
      sortedReports.forEach((report, index) => {
        text += `### ${report.report_name}（${report.report_date}）\n`;
        
        // 财务指标
        if (report.total_revenue !== null && report.total_revenue !== undefined) {
          text += `- 营业收入：${report.total_revenue}${report.currency_name || '元'}\n`;
        }
        if (report.operating_income_yoy !== null && report.operating_income_yoy !== undefined) {
          text += `- 营业收入同比增长：${report.operating_income_yoy}%\n`;
        }
        if (report.net_profit_atsopc !== null && report.net_profit_atsopc !== undefined) {
          text += `- 净利润：${report.net_profit_atsopc}${report.currency_name || '元'}\n`;
        }
        if (report.net_profit_atsopc_yoy !== null && report.net_profit_atsopc_yoy !== undefined) {
          text += `- 净利润同比增长：${report.net_profit_atsopc_yoy}%\n`;
        }
        if (report.net_profit_after_nrgal_atsolc !== null && report.net_profit_after_nrgal_atsolc !== undefined) {
          text += `- 扣除非经常性损益后的净利润：${report.net_profit_after_nrgal_atsolc}${report.currency_name || '元'}\n`;
        }
        if (report.np_atsopc_nrgal_yoy !== null && report.np_atsopc_nrgal_yoy !== undefined) {
          text += `- 扣除非经常性损益后的净利润同比增长：${report.np_atsopc_nrgal_yoy}%\n`;
        }
        if (report.basic_eps !== null && report.basic_eps !== undefined) {
          text += `- 基本每股收益：${report.basic_eps}元\n`;
        }
        if (report.avg_roe !== null && report.avg_roe !== undefined) {
          text += `- 平均净资产收益率：${report.avg_roe}%\n`;
        }
        if (report.ore_dlt !== null && report.ore_dlt !== undefined) {
          text += `- ROE（净资产收益率）：${report.ore_dlt}%\n`;
        }
        if (report.rop !== null && report.rop !== undefined) {
          text += `- ROA（总资产收益率）：${report.rop}%\n`;
        }
        if (report.net_selling_rate !== null && report.net_selling_rate !== undefined) {
          text += `- 净销售率：${report.net_selling_rate}%\n`;
        }
        if (report.gross_selling_rate !== null && report.gross_selling_rate !== undefined) {
          text += `- 毛利率：${report.gross_selling_rate}%\n`;
        }
        
        // 财务比率
        if (report.asset_liab_ratio !== null && report.asset_liab_ratio !== undefined) {
          text += `- 资产负债率：${report.asset_liab_ratio}%\n`;
        }
        if (report.current_ratio !== null && report.current_ratio !== undefined) {
          text += `- 流动比率：${report.current_ratio}\n`;
        }
        if (report.quick_ratio !== null && report.quick_ratio !== undefined) {
          text += `- 速动比率：${report.quick_ratio}\n`;
        }
        if (report.equity_multiplier !== null && report.equity_multiplier !== undefined) {
          text += `- 权益乘数：${report.equity_multiplier}\n`;
        }
        if (report.equity_ratio !== null && report.equity_ratio !== undefined) {
          text += `- 权益比率：${report.equity_ratio}%\n`;
        }
        
        // 现金流量
        if (report.oa_ncf !== null && report.oa_ncf !== undefined) {
          text += `- 经营活动产生的现金流量净额：${report.oa_ncf}${report.currency_name || '元'}\n`;
        }
        if (report.ia_ncf !== null && report.ia_ncf !== undefined) {
          text += `- 投资活动产生的现金流量净额：${report.ia_ncf}${report.currency_name || '元'}\n`;
        }
        if (report.fa_ncf !== null && report.fa_ncf !== undefined) {
          text += `- 筹资活动产生的现金流量净额：${report.fa_ncf}${report.currency_name || '元'}\n`;
        }
        if (report.operate_cash_flow_ps !== null && report.operate_cash_flow_ps !== undefined) {
          text += `- 每股经营现金流：${report.operate_cash_flow_ps}元\n`;
        }
        
        // 其他指标
        if (report.np_per_share !== null && report.np_per_share !== undefined) {
          text += `- 每股净利润：${report.np_per_share}元\n`;
        }
        if (report.undistri_profit_ps !== null && report.undistri_profit_ps !== undefined) {
          text += `- 每股未分配利润：${report.undistri_profit_ps}元\n`;
        }
        if (report.capital_reserve !== null && report.capital_reserve !== undefined) {
          text += `- 资本公积：${report.capital_reserve}${report.currency_name || '元'}\n`;
        }
        if (report.holder_equity !== null && report.holder_equity !== undefined) {
          text += `- 股东权益：${report.holder_equity}${report.currency_name || '元'}\n`;
        }
        if (report.net_interest_of_total_assets !== null && report.net_interest_of_total_assets !== undefined) {
          text += `- 净利润/总资产：${report.net_interest_of_total_assets}\n`;
        }
        if (report.ncf_from_oa_to_total_liab !== null && report.ncf_from_oa_to_total_liab !== undefined) {
          text += `- 经营活动现金流/总负债：${report.ncf_from_oa_to_total_liab}\n`;
        }
        
        // 周转率
        if (report.inventory_turnover !== null && report.inventory_turnover !== undefined) {
          text += `- 存货周转率：${report.inventory_turnover}\n`;
        }
        if (report.inventory_turnover_days !== null && report.inventory_turnover_days !== undefined) {
          text += `- 存货周转天数：${report.inventory_turnover_days}天\n`;
        }
        if (report.account_receivable_turnover !== null && report.account_receivable_turnover !== undefined) {
          text += `- 应收账款周转率：${report.account_receivable_turnover}\n`;
        }
        if (report.receivable_turnover_days !== null && report.receivable_turnover_days !== undefined) {
          text += `- 应收账款周转天数：${report.receivable_turnover_days}天\n`;
        }
        if (report.accounts_payable_turnover !== null && report.accounts_payable_turnover !== undefined) {
          text += `- 应付账款周转率：${report.accounts_payable_turnover}\n`;
        }
        if (report.accounts_payable_turnover_days !== null && report.accounts_payable_turnover_days !== undefined) {
          text += `- 应付账款周转天数：${report.accounts_payable_turnover_days}天\n`;
        }
        if (report.total_capital_turnover !== null && report.total_capital_turnover !== undefined) {
          text += `- 总资本周转率：${report.total_capital_turnover}\n`;
        }
        if (report.current_asset_turnover_rate !== null && report.current_asset_turnover_rate !== undefined) {
          text += `- 流动资产周转率：${report.current_asset_turnover_rate}\n`;
        }
        if (report.fixed_asset_turnover_ratio !== null && report.fixed_asset_turnover_ratio !== undefined) {
          text += `- 固定资产周转率：${report.fixed_asset_turnover_ratio}\n`;
        }
        if (report.cash_cycle !== null && report.cash_cycle !== undefined) {
          text += `- 现金周期：${report.cash_cycle}天\n`;
        }
        if (report.operating_cycle !== null && report.operating_cycle !== undefined) {
          text += `- 经营周期：${report.operating_cycle}天\n`;
        }
        
        text += '\n';
      });
      
      return text;
    },
    /**
     * 获取股票相关数据（日线、资金流向、财报）
     * 返回数据数组，每个元素是一个独立的数据消息
     */
    async fetchStockData(code) {
      const [dailyData, moneyFlowData, financialReports] = await Promise.all([
        this.fetchDailyData(code).catch(err => {
          console.error('获取日线数据失败:', err);
          this.$message.error('获取日线数据失败: ' + (err.message || '未知错误'));
          return null;
        }),
        this.fetchMoneyFlowData(code).catch(err => {
          console.error('获取资金流向数据失败:', err);
          this.$message.error('获取资金流向数据失败: ' + (err.message || '未知错误'));
          return null;
        }),
        this.fetchFinancialReports(code).catch(err => {
          console.error('获取财报数据失败:', err);
          this.$message.error('获取财报数据失败: ' + (err.message || '未知错误'));
          return null;
        })
      ]);
      
      console.log('获取到的数据:', { dailyData, moneyFlowData, financialReports });
      
      // 返回数据数组，每个元素作为一个独立的消息
      const dataMessages = [];
      
      if (dailyData) {
        dataMessages.push({
          title: '日线数据',
          content: this.formatDailyData(dailyData)
        });
      }
      
      if (moneyFlowData) {
        dataMessages.push({
          title: '资金流向数据',
          content: this.formatMoneyFlowData(moneyFlowData)
        });
      }
      
      if (financialReports) {
        dataMessages.push({
          title: '财报数据',
          content: this.formatFinancialReports(financialReports)
        });
      }
      
      return dataMessages;
    },
    /**
     * 生成完整的股票分析 prompt
     */
    generateFullAnalysisPrompt(stockText) {
      return `请帮我分析${stockText}今天是否可以买入。

**分析要求**：
请从以下多个维度进行综合分析（这些分析过程不需要在回复中详细展示）：
- 技术面：K线形态、技术指标（MACD、KDJ、RSI、均线系统）、成交量、支撑阻力位
- 基本面：财务状况、盈利能力、行业地位、近期公告、估值水平
- 市场环境：大盘走势影响、同行业对比、市场情绪、资金流向
- 风险评估：主要风险因素、潜在下行空间、风险收益比

**回复要求**：
请只返回一个简洁明确的结论，格式如下：

**结论：[买] 或 [不买]**

**简要理由**：（用1-2句话简要说明主要原因）

**风险提示**：投资有风险，决策需谨慎。

**重要**：必须给出明确且唯一的结论，只能是"买"或"不买"其中之一，不要模棱两可。不需要列出每个维度的详细分析过程。`
    },
    updatePrompts() {
      const stockText = this.stockDisplayText

      if (stockText) {
        // 有股票信息时，显示股票相关的 prompt
        this.introPrompt.list = [
          {
            value: 'buyToday',
            label: `${stockText}今天可以买吗`,
            iconConfig: { name: 'icon-info-o', color: '#5e7ce0' },
            fullPrompt: this.generateFullAnalysisPrompt(stockText)
          },
        ]
      }else{
        this.introPrompt.list = []
      }
    },
    /**
     * 处理 prompt 点击事件
     */
    handlePromptClick(item) {
      // 如果存在完整的 prompt 内容，使用完整内容；否则使用 label
      const promptContent = item.fullPrompt || item.label
      this.onSubmit(promptContent)
    },
    async onSubmit(question) {
      if (!question?.trim()) {
        this.$message.warning('请输入问题')
        return
      }

      this.inputValue = ''

      // 如果有股票代码，先获取相关数据，分多个消息发送
      if (this.stockCode) {
        this.$message.loading('正在获取股票数据...', 0)
        const dataMessages = await this.fetchStockData(this.stockCode)
        this.$message.destroy()
        
        // 先添加用户问题消息
        this.messages.push({
          from: 'user',
          content: question
        })
        
        // 分别添加每个数据消息
        if (dataMessages && dataMessages.length > 0) {
          dataMessages.forEach(dataMsg => {
            this.messages.push({
              from: 'user',
              content: `**${dataMsg.title}**\n\n${dataMsg.content}`
            })
          })
        }
      } else {
        // 没有股票代码，直接添加用户消息
        this.messages.push({
          from: 'user',
          content: question
        })
      }

      // 添加 AI 占位消息
      const aiMessageIndex = this.messages.length
      this.messages.push({
        from: 'model',
        content: '',
        loading: true
      })

      // 取消之前的请求
      if (this.abortController) {
        this.abortController.abort()
      }

      this.abortController = new AbortController()

      try {
        // 构建消息历史（排除正在流式输出的消息）
        const historyMessages = this.messages
          .filter(msg => msg.from === 'user' || (msg.from === 'model' && !msg.loading && msg.content))
          .map(msg => ({
            role: msg.from === 'user' ? 'user' : 'assistant',
            content: msg.content
          }))

        const raw = JSON.stringify({
          model: 'ds-r1',
          stream: true,
          conciseSnippet: true,
          messages: historyMessages
        })

        const requestOptions = {
          method: 'POST',
          headers: {
            'Authorization': 'Bearer mk-1312C5951A4B3EF2130E44B69528FA70',
            'Accept': 'application/json',
            'Content-Type': 'application/json'
          },
          body: raw,
          redirect: 'follow',
          signal: this.abortController.signal
        }

        const response = await fetch('https://metaso.cn/api/v1/chat/completions', requestOptions)

        if (!response.ok) {
          throw new Error(`HTTP error! status: ${response.status}`)
        }

        const reader = response.body.getReader()
        const decoder = new TextDecoder()

        // 开始流式接收
        this.messages[aiMessageIndex].loading = false

        while (true) {
          const { done, value } = await reader.read()
          if (done) break

          const chunk = decoder.decode(value)
          const lines = chunk.split('\n')

          for (const line of lines) {
            const trimmedLine = line.trim()
            if (trimmedLine.startsWith('data:')) {
              const jsonStr = trimmedLine.substring(5).trim()
              if (jsonStr === '[DONE]') return

              if (jsonStr) {
                try {
                  const parsed = JSON.parse(jsonStr)
                  if (parsed.choices?.[0]?.delta) {
                    const delta = parsed.choices[0].delta
                    if (delta.reasoning_content) {
                      this.messages[aiMessageIndex].content += delta.reasoning_content
                    }
                    if (delta.content) {
                      this.messages[aiMessageIndex].content += delta.content
                    }
                  }
                } catch (e) {
                  // 忽略解析错误
                }
              }
            }
          }
        }
      } catch (error) {
        if (error.name === 'AbortError') {
          this.$message.info('请求已取消')
        } else {
          console.error('请求错误:', error)
          this.$message.error('请求失败: ' + error.message)
        }
        // 移除失败的 AI 消息
        this.messages.splice(aiMessageIndex, 1)
      } finally {
        this.abortController = null
      }
    },
    handleClear() {
      this.messages = []
      this.inputValue = ''
      if (this.abortController) {
        this.abortController.abort()
        this.abortController = null
      }
      this.loading = false
    }
  },
  beforeUnmount() {
    if (this.abortController) {
      this.abortController.abort()
    }
  }
}
</script>

<style scoped>
.ai-analysis-content {
  min-height: 200px;
}

.chat-container {
  display: flex;
  flex-direction: column;
  height: 800px;
}

.content-container {
  display: flex;
  flex-direction: column;
  gap: 8px;
  overflow-y: auto;
  overflow-x: hidden;
  flex: 1;
  padding: 16px;
}

.input-foot-wrapper {
  display: flex;
  justify-content: space-between;
  align-items: center;
  width: 100%;
  height: 100%;
  margin-right: 8px;
}

.input-foot-left {
  display: flex;
  align-items: center;
  gap: 8px;
}

.input-foot-maxlength {
  font-size: 14px;
  color: #71757f;
}

.input-foot-right {
  display: flex;
  align-items: center;
  gap: 8px;
}

.intro-prompt {
  margin-top: 16px;
  width: 100%;
  max-width: 800px;
}

.shortcut {
  padding: 8px 16px;
  border-top: 1px solid #e8e8e8;
}
</style>
