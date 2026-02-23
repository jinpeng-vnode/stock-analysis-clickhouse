<template>
  <div class="page-container">
    <a-card title="财报表管理" style="margin-bottom: 16px;">
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
      rowKey="report_date"
      size="middle"
      @change="onTableChange"
      :scroll="{ x: 2400 }"
    >
      <template #bodyCell="{ column, text, record }">
        <template v-if="column.dataIndex === 'report_name'">
          <a @click="onViewDetail(record)" style="color: #1890ff;">{{ text }}</a>
        </template>
        <template v-if="column.dataIndex === 'oa_ncf' || column.dataIndex === 'ia_ncf' || column.dataIndex === 'fa_ncf' || column.dataIndex === 'cce_net_increase'">
          <span :style="{ color: text >= 0 ? '#52c41a' : '#ff4d4f' }">
            {{ formatMoney(text) }}
          </span>
        </template>
        <template v-else-if="column.dataIndex.startsWith('oa_') || column.dataIndex.startsWith('ia_') || column.dataIndex.startsWith('fa_') || column.dataIndex.startsWith('cce_') || column.dataIndex === 'total_revenue'">
          {{ formatMoney(text) }}
        </template>
        <template v-else-if="column.dataIndex === 'ore_dlt' || column.dataIndex === 'rop' || column.dataIndex === 'asset_liab_ratio' || column.dataIndex === 'operating_income_yoy'">
          {{ text !== null && text !== undefined ? text.toFixed(2) + '%' : '-' }}
        </template>
        <template v-else-if="column.dataIndex === 'basic_eps' || column.dataIndex === 'np_per_share' || column.dataIndex === 'current_ratio' || column.dataIndex === 'quick_ratio'">
          {{ text !== null && text !== undefined ? text.toFixed(2) : '-' }}
        </template>
      </template>
    </a-table>

    <a-modal
      v-model:open="detailModalVisible"
      title="财报表详情"
      :width="'80vw'"
      :footer="null"
    >
      <a-descriptions :column="2" bordered v-if="currentRecord">
        <a-descriptions-item label="股票代码">{{ currentRecord.code }}</a-descriptions-item>
        <a-descriptions-item label="股票名称">{{ currentRecord.quote_name }}</a-descriptions-item>
        <a-descriptions-item label="报告日期">{{ currentRecord.report_date }}</a-descriptions-item>
        <a-descriptions-item label="报告名称">{{ currentRecord.report_name }}</a-descriptions-item>
        <a-descriptions-item label="货币">{{ currentRecord.currency_name }}</a-descriptions-item>
        <a-descriptions-item label="组织类型">{{ currentRecord.org_type }}</a-descriptions-item>
        
        <a-descriptions-item :span="2">
          <template #label>
            <strong>经营活动产生的现金流量</strong>
          </template>
        </a-descriptions-item>
        <a-descriptions-item label="经营活动产生的现金流量净额" :span="2">
          <span :style="{ color: currentRecord.oa_ncf >= 0 ? '#52c41a' : '#ff4d4f' }">
            {{ formatMoney(currentRecord.oa_ncf) }}
          </span>
        </a-descriptions-item>
        <a-descriptions-item label="销售商品、提供劳务收到的现金">{{ formatMoney(currentRecord.oa_cash_received_of_sales_service) }}</a-descriptions-item>
        <a-descriptions-item label="收到的税费返还">{{ formatMoney(currentRecord.oa_refund_of_tax_and_levies) }}</a-descriptions-item>
        <a-descriptions-item label="收到其他与经营活动有关的现金">{{ formatMoney(currentRecord.oa_cash_received_of_othr) }}</a-descriptions-item>
        <a-descriptions-item label="经营活动现金流入小计">{{ formatMoney(currentRecord.oa_sub_total_ci) }}</a-descriptions-item>
        <a-descriptions-item label="购买商品、接受劳务支付的现金">{{ formatMoney(currentRecord.oa_goods_buy_and_service_cash_pay) }}</a-descriptions-item>
        <a-descriptions-item label="支付给职工以及为职工支付的现金">{{ formatMoney(currentRecord.oa_cash_paid_to_employee_etc) }}</a-descriptions-item>
        <a-descriptions-item label="支付的各项税费">{{ formatMoney(currentRecord.oa_payments_of_all_taxes) }}</a-descriptions-item>
        <a-descriptions-item label="支付其他与经营活动有关的现金">{{ formatMoney(currentRecord.oa_othrcash_paid_relating_to) }}</a-descriptions-item>
        <a-descriptions-item label="经营活动现金流出小计" :span="2">{{ formatMoney(currentRecord.oa_sub_total_cos) }}</a-descriptions-item>
        
        <a-descriptions-item :span="2">
          <template #label>
            <strong>投资活动产生的现金流量</strong>
          </template>
        </a-descriptions-item>
        <a-descriptions-item label="投资活动产生的现金流量净额" :span="2">
          <span :style="{ color: currentRecord.ia_ncf >= 0 ? '#52c41a' : '#ff4d4f' }">
            {{ formatMoney(currentRecord.ia_ncf) }}
          </span>
        </a-descriptions-item>
        <a-descriptions-item label="收回投资收到的现金">{{ formatMoney(currentRecord.ia_cash_received_of_dspsl_invest) }}</a-descriptions-item>
        <a-descriptions-item label="取得投资收益收到的现金">{{ formatMoney(currentRecord.ia_invest_income_cash_received) }}</a-descriptions-item>
        <a-descriptions-item label="处置固定资产、无形资产和其他长期资产收回的现金净额">{{ formatMoney(currentRecord.ia_net_cash_of_disposal_assets) }}</a-descriptions-item>
        <a-descriptions-item label="处置子公司及其他营业单位收到的现金净额">{{ formatMoney(currentRecord.ia_net_cash_of_disposal_branch) }}</a-descriptions-item>
        <a-descriptions-item label="收到其他与投资活动有关的现金">{{ formatMoney(currentRecord.ia_cash_received_of_othr) }}</a-descriptions-item>
        <a-descriptions-item label="投资活动现金流入小计">{{ formatMoney(currentRecord.ia_sub_total_ci) }}</a-descriptions-item>
        <a-descriptions-item label="购建固定资产、无形资产和其他长期资产支付的现金">{{ formatMoney(currentRecord.ia_invest_paid_cash) }}</a-descriptions-item>
        <a-descriptions-item label="投资支付的现金">{{ formatMoney(currentRecord.ia_cash_paid_for_assets) }}</a-descriptions-item>
        <a-descriptions-item label="支付其他与投资活动有关的现金">{{ formatMoney(currentRecord.ia_othrcash_paid_relating_to) }}</a-descriptions-item>
        <a-descriptions-item label="投资活动现金流出小计" :span="2">{{ formatMoney(currentRecord.ia_sub_total_cos) }}</a-descriptions-item>
        
        <a-descriptions-item :span="2">
          <template #label>
            <strong>筹资活动产生的现金流量</strong>
          </template>
        </a-descriptions-item>
        <a-descriptions-item label="筹资活动产生的现金流量净额" :span="2">
          <span :style="{ color: currentRecord.fa_ncf >= 0 ? '#52c41a' : '#ff4d4f' }">
            {{ formatMoney(currentRecord.fa_ncf) }}
          </span>
        </a-descriptions-item>
        <a-descriptions-item label="吸收投资收到的现金">{{ formatMoney(currentRecord.fa_cash_received_of_absorb_invest) }}</a-descriptions-item>
        <a-descriptions-item label="其中：子公司吸收少数股东投资收到的现金">{{ formatMoney(currentRecord.fa_cash_received_from_investor) }}</a-descriptions-item>
        <a-descriptions-item label="发行债券收到的现金">{{ formatMoney(currentRecord.fa_cash_received_from_bond_issue) }}</a-descriptions-item>
        <a-descriptions-item label="取得借款收到的现金">{{ formatMoney(currentRecord.fa_cash_received_of_borrowing) }}</a-descriptions-item>
        <a-descriptions-item label="收到其他与筹资活动有关的现金">{{ formatMoney(currentRecord.fa_cash_received_of_othr) }}</a-descriptions-item>
        <a-descriptions-item label="筹资活动现金流入小计">{{ formatMoney(currentRecord.fa_sub_total_ci) }}</a-descriptions-item>
        <a-descriptions-item label="偿还债务支付的现金">{{ formatMoney(currentRecord.fa_cash_pay_for_debt) }}</a-descriptions-item>
        <a-descriptions-item label="分配股利、利润或偿付利息支付的现金">{{ formatMoney(currentRecord.fa_cash_paid_of_distribution) }}</a-descriptions-item>
        <a-descriptions-item label="其中：子公司支付给少数股东的股利、利润">{{ formatMoney(currentRecord.fa_branch_paid_to_minority_holder) }}</a-descriptions-item>
        <a-descriptions-item label="支付其他与筹资活动有关的现金">{{ formatMoney(currentRecord.fa_othrcash_paid_relating_to) }}</a-descriptions-item>
        <a-descriptions-item label="筹资活动现金流出小计" :span="2">{{ formatMoney(currentRecord.fa_sub_total_cos) }}</a-descriptions-item>
        
        <a-descriptions-item :span="2">
          <template #label>
            <strong>现金及现金等价物</strong>
          </template>
        </a-descriptions-item>
        <a-descriptions-item label="汇率变动对现金及现金等价物的影响">{{ formatMoney(currentRecord.cce_effect_of_exchange_chg) }}</a-descriptions-item>
        <a-descriptions-item label="现金及现金等价物净增加额">
          <span :style="{ color: currentRecord.cce_net_increase >= 0 ? '#52c41a' : '#ff4d4f' }">
            {{ formatMoney(currentRecord.cce_net_increase) }}
          </span>
        </a-descriptions-item>
        <a-descriptions-item label="期初现金及现金等价物余额">{{ formatMoney(currentRecord.cce_initial_balance) }}</a-descriptions-item>
        <a-descriptions-item label="期末现金及现金等价物余额">{{ formatMoney(currentRecord.cce_final_balance) }}</a-descriptions-item>
        
        <a-descriptions-item label="子公司支付给少数股东的股利、利润" :span="2">{{ formatMoney(currentRecord.net_cash_amt_from_branch) }}</a-descriptions-item>
        
        <a-descriptions-item :span="2">
          <template #label>
            <strong>财务指标</strong>
          </template>
        </a-descriptions-item>
        
        <a-descriptions-item :span="2">
          <template #label>
            <strong>盈利能力指标</strong>
          </template>
        </a-descriptions-item>
        <a-descriptions-item label="ROE（净资产收益率）(%)">{{ currentRecord.ore_dlt !== null && currentRecord.ore_dlt !== undefined ? currentRecord.ore_dlt.toFixed(2) + '%' : '-' }}</a-descriptions-item>
        <a-descriptions-item label="ROA（总资产收益率）(%)">{{ currentRecord.rop !== null && currentRecord.rop !== undefined ? currentRecord.rop.toFixed(2) + '%' : '-' }}</a-descriptions-item>
        <a-descriptions-item label="基本每股收益">{{ currentRecord.basic_eps !== null && currentRecord.basic_eps !== undefined ? currentRecord.basic_eps.toFixed(2) : '-' }}</a-descriptions-item>
        <a-descriptions-item label="每股净利润">{{ currentRecord.np_per_share !== null && currentRecord.np_per_share !== undefined ? currentRecord.np_per_share.toFixed(2) : '-' }}</a-descriptions-item>
        <a-descriptions-item label="每股经营现金流">{{ currentRecord.operate_cash_flow_ps !== null && currentRecord.operate_cash_flow_ps !== undefined ? currentRecord.operate_cash_flow_ps.toFixed(2) : '-' }}</a-descriptions-item>
        <a-descriptions-item label="毛利率(%)">{{ currentRecord.gross_selling_rate !== null && currentRecord.gross_selling_rate !== undefined ? currentRecord.gross_selling_rate.toFixed(2) + '%' : '-' }}</a-descriptions-item>
        <a-descriptions-item label="净销售率(%)">{{ currentRecord.net_selling_rate !== null && currentRecord.net_selling_rate !== undefined ? currentRecord.net_selling_rate.toFixed(2) + '%' : '-' }}</a-descriptions-item>
        <a-descriptions-item label="总营收" :span="2">{{ formatMoney(currentRecord.total_revenue) }}</a-descriptions-item>
        <a-descriptions-item label="营业收入同比增长(%)">{{ currentRecord.operating_income_yoy !== null && currentRecord.operating_income_yoy !== undefined ? currentRecord.operating_income_yoy.toFixed(2) + '%' : '-' }}</a-descriptions-item>
        <a-descriptions-item label="归属于母公司股东的净利润">{{ formatMoney(currentRecord.net_profit_atsopc) }}</a-descriptions-item>
        <a-descriptions-item label="归属于母公司股东的净利润同比增长(%)">{{ currentRecord.net_profit_atsopc_yoy !== null && currentRecord.net_profit_atsopc_yoy !== undefined ? currentRecord.net_profit_atsopc_yoy.toFixed(2) + '%' : '-' }}</a-descriptions-item>
        <a-descriptions-item label="扣除非经常性损益后的净利润">{{ formatMoney(currentRecord.net_profit_after_nrgal_atsolc) }}</a-descriptions-item>
        <a-descriptions-item label="扣除非经常性损益后的净利润同比增长(%)">{{ currentRecord.np_atsopc_nrgal_yoy !== null && currentRecord.np_atsopc_nrgal_yoy !== undefined ? currentRecord.np_atsopc_nrgal_yoy.toFixed(2) + '%' : '-' }}</a-descriptions-item>
        
        <a-descriptions-item :span="2">
          <template #label>
            <strong>偿债能力指标</strong>
          </template>
        </a-descriptions-item>
        <a-descriptions-item label="资产负债率(%)">{{ currentRecord.asset_liab_ratio !== null && currentRecord.asset_liab_ratio !== undefined ? currentRecord.asset_liab_ratio.toFixed(2) + '%' : '-' }}</a-descriptions-item>
        <a-descriptions-item label="流动比率">{{ currentRecord.current_ratio !== null && currentRecord.current_ratio !== undefined ? currentRecord.current_ratio.toFixed(2) : '-' }}</a-descriptions-item>
        <a-descriptions-item label="速动比率">{{ currentRecord.quick_ratio !== null && currentRecord.quick_ratio !== undefined ? currentRecord.quick_ratio.toFixed(2) : '-' }}</a-descriptions-item>
        <a-descriptions-item label="权益乘数">{{ currentRecord.equity_multiplier !== null && currentRecord.equity_multiplier !== undefined ? currentRecord.equity_multiplier.toFixed(2) : '-' }}</a-descriptions-item>
        <a-descriptions-item label="权益比率(%)">{{ currentRecord.equity_ratio !== null && currentRecord.equity_ratio !== undefined ? currentRecord.equity_ratio.toFixed(2) + '%' : '-' }}</a-descriptions-item>
        <a-descriptions-item label="股东权益">{{ formatMoney(currentRecord.holder_equity) }}</a-descriptions-item>
        <a-descriptions-item label="经营活动现金流/总负债">{{ currentRecord.ncf_from_oa_to_total_liab !== null && currentRecord.ncf_from_oa_to_total_liab !== undefined ? currentRecord.ncf_from_oa_to_total_liab.toFixed(2) : '-' }}</a-descriptions-item>
        
        <a-descriptions-item :span="2">
          <template #label>
            <strong>营运能力指标</strong>
          </template>
        </a-descriptions-item>
        <a-descriptions-item label="存货周转天数">{{ currentRecord.inventory_turnover_days !== null && currentRecord.inventory_turnover_days !== undefined ? currentRecord.inventory_turnover_days.toFixed(2) + '天' : '-' }}</a-descriptions-item>
        <a-descriptions-item label="应收账款周转天数">{{ currentRecord.receivable_turnover_days !== null && currentRecord.receivable_turnover_days !== undefined ? currentRecord.receivable_turnover_days.toFixed(2) + '天' : '-' }}</a-descriptions-item>
        <a-descriptions-item label="应付账款周转天数">{{ currentRecord.accounts_payable_turnover_days !== null && currentRecord.accounts_payable_turnover_days !== undefined ? currentRecord.accounts_payable_turnover_days.toFixed(2) + '天' : '-' }}</a-descriptions-item>
        <a-descriptions-item label="现金周期">{{ currentRecord.cash_cycle !== null && currentRecord.cash_cycle !== undefined ? currentRecord.cash_cycle.toFixed(2) + '天' : '-' }}</a-descriptions-item>
        <a-descriptions-item label="经营周期">{{ currentRecord.operating_cycle !== null && currentRecord.operating_cycle !== undefined ? currentRecord.operating_cycle.toFixed(2) + '天' : '-' }}</a-descriptions-item>
        <a-descriptions-item label="总资本周转率">{{ currentRecord.total_capital_turnover !== null && currentRecord.total_capital_turnover !== undefined ? currentRecord.total_capital_turnover.toFixed(2) : '-' }}</a-descriptions-item>
        <a-descriptions-item label="存货周转率">{{ currentRecord.inventory_turnover !== null && currentRecord.inventory_turnover !== undefined ? currentRecord.inventory_turnover.toFixed(2) : '-' }}</a-descriptions-item>
        <a-descriptions-item label="应收账款周转率">{{ currentRecord.account_receivable_turnover !== null && currentRecord.account_receivable_turnover !== undefined ? currentRecord.account_receivable_turnover.toFixed(2) : '-' }}</a-descriptions-item>
        <a-descriptions-item label="应付账款周转率">{{ currentRecord.accounts_payable_turnover !== null && currentRecord.accounts_payable_turnover !== undefined ? currentRecord.accounts_payable_turnover.toFixed(2) : '-' }}</a-descriptions-item>
        <a-descriptions-item label="流动资产周转率">{{ currentRecord.current_asset_turnover_rate !== null && currentRecord.current_asset_turnover_rate !== undefined ? currentRecord.current_asset_turnover_rate.toFixed(2) : '-' }}</a-descriptions-item>
        <a-descriptions-item label="固定资产周转率" :span="2">{{ currentRecord.fixed_asset_turnover_ratio !== null && currentRecord.fixed_asset_turnover_ratio !== undefined ? currentRecord.fixed_asset_turnover_ratio.toFixed(2) : '-' }}</a-descriptions-item>
      </a-descriptions>
    </a-modal>
  </div>
</template>

<script>
import { message } from 'ant-design-vue'
import { getStockFinancialReports, listFinancialReports } from '@/api/financialReports'
import dayjs from 'dayjs'
import { formatMoney as formatMoneyUtil } from '@/utils/formatMoney'

export default {
  name: 'FinancialReportList',
  data() {
    return {
      columns: [
        { title: '序号', dataIndex: 'index', width: 70, fixed: 'left', customRender: ({ index }) => (this.pagination.current - 1) * this.pagination.pageSize + index + 1 },
        { title: '股票代码', dataIndex: 'code', width: 100, fixed: 'left' },
        { title: '股票名称', dataIndex: 'quote_name', width: 120, fixed: 'left' },
        { title: '报告日期', dataIndex: 'report_date', width: 120 },
        { title: '报告名称', dataIndex: 'report_name', width: 150 },
        { title: '经营活动现金流量净额', dataIndex: 'oa_ncf', width: 160 },
        { title: '投资活动现金流量净额', dataIndex: 'ia_ncf', width: 160 },
        { title: '筹资活动现金流量净额', dataIndex: 'fa_ncf', width: 160 },
        { title: '现金及现金等价物净增加额', dataIndex: 'cce_net_increase', width: 180 },
        { title: '期末现金及现金等价物余额', dataIndex: 'cce_final_balance', width: 180 },
        { title: 'ROE(%)', dataIndex: 'ore_dlt', width: 100 },
        { title: 'ROA(%)', dataIndex: 'rop', width: 100 },
        { title: '基本每股收益', dataIndex: 'basic_eps', width: 120 },
        { title: '每股净利润', dataIndex: 'np_per_share', width: 120 },
        { title: '总营收', dataIndex: 'total_revenue', width: 150 },
        { title: '营业收入同比增长(%)', dataIndex: 'operating_income_yoy', width: 160 },
        { title: '资产负债率(%)', dataIndex: 'asset_liab_ratio', width: 120 },
        { title: '流动比率', dataIndex: 'current_ratio', width: 100 },
        { title: '速动比率', dataIndex: 'quick_ratio', width: 100 },
      ],
      searchParams: { 
        code: '', 
        start_date: null, 
        end_date: null
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
    formatMoney(value) {
      // 使用公共的金额格式化函数
      // 注意：后端返回的数据单位是"分"，直接传给formatMoney函数
      if (value === null || value === undefined) return '-'
      const numValue = typeof value === 'number' ? value : parseFloat(value)
      if (isNaN(numValue)) return '-'
      // 数据已经是"分"为单位，直接格式化
      return formatMoneyUtil(numValue)
    },
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
        
        getStockFinancialReports(this.searchParams.code.trim(), params)
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
        
        listFinancialReports(params)
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
        end_date: null
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

