"""
财报表相关 Pydantic 模型
"""
from datetime import date
from typing import List, Optional
from pydantic import BaseModel, Field


class FinancialReportItem(BaseModel):
    """财报表数据模型"""
    code: str = Field(..., description="股票代码（6位数字）")
    quote_name: str = Field(..., description="股票名称")
    report_date: date = Field(..., description="报告日期")
    report_name: str = Field(..., description="报告名称（如：2025三季报）")
    currency: str = Field(default="CNY", description="货币代码")
    currency_name: str = Field(default="人民币", description="货币名称")
    org_type: int = Field(default=1, description="组织类型")
    
    # 经营活动产生的现金流量 (Operating Activities)
    oa_ncf: Optional[float] = Field(None, description="经营活动产生的现金流量净额")
    oa_cash_received_of_sales_service: Optional[float] = Field(None, description="销售商品、提供劳务收到的现金")
    oa_refund_of_tax_and_levies: Optional[float] = Field(None, description="收到的税费返还")
    oa_cash_received_of_othr: Optional[float] = Field(None, description="收到其他与经营活动有关的现金")
    oa_sub_total_ci: Optional[float] = Field(None, description="经营活动现金流入小计")
    oa_goods_buy_and_service_cash_pay: Optional[float] = Field(None, description="购买商品、接受劳务支付的现金")
    oa_cash_paid_to_employee_etc: Optional[float] = Field(None, description="支付给职工以及为职工支付的现金")
    oa_payments_of_all_taxes: Optional[float] = Field(None, description="支付的各项税费")
    oa_othrcash_paid_relating_to: Optional[float] = Field(None, description="支付其他与经营活动有关的现金")
    oa_sub_total_cos: Optional[float] = Field(None, description="经营活动现金流出小计")
    
    # 投资活动产生的现金流量 (Investing Activities)
    ia_ncf: Optional[float] = Field(None, description="投资活动产生的现金流量净额")
    ia_cash_received_of_dspsl_invest: Optional[float] = Field(None, description="收回投资收到的现金")
    ia_invest_income_cash_received: Optional[float] = Field(None, description="取得投资收益收到的现金")
    ia_net_cash_of_disposal_assets: Optional[float] = Field(None, description="处置固定资产、无形资产和其他长期资产收回的现金净额")
    ia_net_cash_of_disposal_branch: Optional[float] = Field(None, description="处置子公司及其他营业单位收到的现金净额")
    ia_cash_received_of_othr: Optional[float] = Field(None, description="收到其他与投资活动有关的现金")
    ia_sub_total_ci: Optional[float] = Field(None, description="投资活动现金流入小计")
    ia_invest_paid_cash: Optional[float] = Field(None, description="购建固定资产、无形资产和其他长期资产支付的现金")
    ia_cash_paid_for_assets: Optional[float] = Field(None, description="投资支付的现金")
    ia_othrcash_paid_relating_to: Optional[float] = Field(None, description="支付其他与投资活动有关的现金")
    ia_sub_total_cos: Optional[float] = Field(None, description="投资活动现金流出小计")
    
    # 筹资活动产生的现金流量 (Financing Activities)
    fa_ncf: Optional[float] = Field(None, description="筹资活动产生的现金流量净额")
    fa_cash_received_of_absorb_invest: Optional[float] = Field(None, description="吸收投资收到的现金")
    fa_cash_received_from_investor: Optional[float] = Field(None, description="其中：子公司吸收少数股东投资收到的现金")
    fa_cash_received_from_bond_issue: Optional[float] = Field(None, description="发行债券收到的现金")
    fa_cash_received_of_borrowing: Optional[float] = Field(None, description="取得借款收到的现金")
    fa_cash_received_of_othr: Optional[float] = Field(None, description="收到其他与筹资活动有关的现金")
    fa_sub_total_ci: Optional[float] = Field(None, description="筹资活动现金流入小计")
    fa_cash_pay_for_debt: Optional[float] = Field(None, description="偿还债务支付的现金")
    fa_cash_paid_of_distribution: Optional[float] = Field(None, description="分配股利、利润或偿付利息支付的现金")
    fa_branch_paid_to_minority_holder: Optional[float] = Field(None, description="其中：子公司支付给少数股东的股利、利润")
    fa_othrcash_paid_relating_to: Optional[float] = Field(None, description="支付其他与筹资活动有关的现金")
    fa_sub_total_cos: Optional[float] = Field(None, description="筹资活动现金流出小计")
    
    # 现金及现金等价物 (Cash and Cash Equivalents)
    cce_effect_of_exchange_chg: Optional[float] = Field(None, description="汇率变动对现金及现金等价物的影响")
    cce_net_increase: Optional[float] = Field(None, description="现金及现金等价物净增加额")
    cce_initial_balance: Optional[float] = Field(None, description="期初现金及现金等价物余额")
    cce_final_balance: Optional[float] = Field(None, description="期末现金及现金等价物余额")
    
    # 其他
    net_cash_amt_from_branch: Optional[float] = Field(None, description="子公司支付给少数股东的股利、利润")
    
    # 财务指标数据 (Financial Indicators)
    avg_roe: Optional[float] = Field(None, description="平均ROE（净资产收益率）")
    np_per_share: Optional[float] = Field(None, description="每股净利润")
    operate_cash_flow_ps: Optional[float] = Field(None, description="每股经营现金流")
    basic_eps: Optional[float] = Field(None, description="基本每股收益")
    capital_reserve: Optional[float] = Field(None, description="资本公积")
    undistri_profit_ps: Optional[float] = Field(None, description="每股未分配利润")
    net_interest_of_total_assets: Optional[float] = Field(None, description="净利润/总资产")
    net_selling_rate: Optional[float] = Field(None, description="净销售率")
    gross_selling_rate: Optional[float] = Field(None, description="毛利率")
    total_revenue: Optional[float] = Field(None, description="总营收")
    operating_income_yoy: Optional[float] = Field(None, description="营业收入同比增长率（%）")
    net_profit_atsopc: Optional[float] = Field(None, description="归属于母公司股东的净利润")
    net_profit_atsopc_yoy: Optional[float] = Field(None, description="归属于母公司股东的净利润同比增长率（%）")
    net_profit_after_nrgal_atsolc: Optional[float] = Field(None, description="扣除非经常性损益后的净利润")
    np_atsopc_nrgal_yoy: Optional[float] = Field(None, description="扣除非经常性损益后的净利润同比增长率（%）")
    ore_dlt: Optional[float] = Field(None, description="ROE（净资产收益率）")
    rop: Optional[float] = Field(None, description="ROA（总资产收益率）")
    asset_liab_ratio: Optional[float] = Field(None, description="资产负债率（%）")
    current_ratio: Optional[float] = Field(None, description="流动比率")
    quick_ratio: Optional[float] = Field(None, description="速动比率")
    equity_multiplier: Optional[float] = Field(None, description="权益乘数")
    equity_ratio: Optional[float] = Field(None, description="权益比率（%）")
    holder_equity: Optional[float] = Field(None, description="股东权益")
    ncf_from_oa_to_total_liab: Optional[float] = Field(None, description="经营活动现金流/总负债")
    inventory_turnover_days: Optional[float] = Field(None, description="存货周转天数")
    receivable_turnover_days: Optional[float] = Field(None, description="应收账款周转天数")
    accounts_payable_turnover_days: Optional[float] = Field(None, description="应付账款周转天数")
    cash_cycle: Optional[float] = Field(None, description="现金周期（天）")
    operating_cycle: Optional[float] = Field(None, description="经营周期（天）")
    total_capital_turnover: Optional[float] = Field(None, description="总资本周转率")
    inventory_turnover: Optional[float] = Field(None, description="存货周转率")
    account_receivable_turnover: Optional[float] = Field(None, description="应收账款周转率")
    accounts_payable_turnover: Optional[float] = Field(None, description="应付账款周转率")
    current_asset_turnover_rate: Optional[float] = Field(None, description="流动资产周转率")
    fixed_asset_turnover_ratio: Optional[float] = Field(None, description="固定资产周转率")
    
    # 元数据
    version: Optional[str] = Field(None, description="版本时间")


class FinancialReportListResponse(BaseModel):
    """财报表列表响应模型"""
    code: str = Field(..., description="股票代码")
    name: str = Field(..., description="股票名称")
    total: int = Field(..., description="总记录数")
    items: List[FinancialReportItem] = Field(..., description="财报表列表")


class FinancialReportCreate(BaseModel):
    """创建财报表请求模型"""
    code: str = Field(..., description="股票代码（6位数字）")
    quote_name: str = Field(..., description="股票名称")
    report_date: date = Field(..., description="报告日期")
    report_name: str = Field(..., description="报告名称（如：2025三季报）")
    currency: str = Field(default="CNY", description="货币代码")
    currency_name: str = Field(default="人民币", description="货币名称")
    org_type: int = Field(default=1, description="组织类型")
    
    # 经营活动产生的现金流量
    oa_ncf: Optional[float] = None
    oa_cash_received_of_sales_service: Optional[float] = None
    oa_refund_of_tax_and_levies: Optional[float] = None
    oa_cash_received_of_othr: Optional[float] = None
    oa_sub_total_ci: Optional[float] = None
    oa_goods_buy_and_service_cash_pay: Optional[float] = None
    oa_cash_paid_to_employee_etc: Optional[float] = None
    oa_payments_of_all_taxes: Optional[float] = None
    oa_othrcash_paid_relating_to: Optional[float] = None
    oa_sub_total_cos: Optional[float] = None
    
    # 投资活动产生的现金流量
    ia_ncf: Optional[float] = None
    ia_cash_received_of_dspsl_invest: Optional[float] = None
    ia_invest_income_cash_received: Optional[float] = None
    ia_net_cash_of_disposal_assets: Optional[float] = None
    ia_net_cash_of_disposal_branch: Optional[float] = None
    ia_cash_received_of_othr: Optional[float] = None
    ia_sub_total_ci: Optional[float] = None
    ia_invest_paid_cash: Optional[float] = None
    ia_cash_paid_for_assets: Optional[float] = None
    ia_othrcash_paid_relating_to: Optional[float] = None
    ia_sub_total_cos: Optional[float] = None
    
    # 筹资活动产生的现金流量
    fa_ncf: Optional[float] = None
    fa_cash_received_of_absorb_invest: Optional[float] = None
    fa_cash_received_from_investor: Optional[float] = None
    fa_cash_received_from_bond_issue: Optional[float] = None
    fa_cash_received_of_borrowing: Optional[float] = None
    fa_cash_received_of_othr: Optional[float] = None
    fa_sub_total_ci: Optional[float] = None
    fa_cash_pay_for_debt: Optional[float] = None
    fa_cash_paid_of_distribution: Optional[float] = None
    fa_branch_paid_to_minority_holder: Optional[float] = None
    fa_othrcash_paid_relating_to: Optional[float] = None
    fa_sub_total_cos: Optional[float] = None
    
    # 现金及现金等价物
    cce_effect_of_exchange_chg: Optional[float] = None
    cce_net_increase: Optional[float] = None
    cce_initial_balance: Optional[float] = None
    cce_final_balance: Optional[float] = None
    
    # 其他
    net_cash_amt_from_branch: Optional[float] = None
    
    # 财务指标数据 (Financial Indicators)
    avg_roe: Optional[float] = None
    np_per_share: Optional[float] = None
    operate_cash_flow_ps: Optional[float] = None
    basic_eps: Optional[float] = None
    capital_reserve: Optional[float] = None
    undistri_profit_ps: Optional[float] = None
    net_interest_of_total_assets: Optional[float] = None
    net_selling_rate: Optional[float] = None
    gross_selling_rate: Optional[float] = None
    total_revenue: Optional[float] = None
    operating_income_yoy: Optional[float] = None
    net_profit_atsopc: Optional[float] = None
    net_profit_atsopc_yoy: Optional[float] = None
    net_profit_after_nrgal_atsolc: Optional[float] = None
    np_atsopc_nrgal_yoy: Optional[float] = None
    ore_dlt: Optional[float] = None
    rop: Optional[float] = None
    asset_liab_ratio: Optional[float] = None
    current_ratio: Optional[float] = None
    quick_ratio: Optional[float] = None
    equity_multiplier: Optional[float] = None
    equity_ratio: Optional[float] = None
    holder_equity: Optional[float] = None
    ncf_from_oa_to_total_liab: Optional[float] = None
    inventory_turnover_days: Optional[float] = None
    receivable_turnover_days: Optional[float] = None
    accounts_payable_turnover_days: Optional[float] = None
    cash_cycle: Optional[float] = None
    operating_cycle: Optional[float] = None
    total_capital_turnover: Optional[float] = None
    inventory_turnover: Optional[float] = None
    account_receivable_turnover: Optional[float] = None
    accounts_payable_turnover: Optional[float] = None
    current_asset_turnover_rate: Optional[float] = None
    fixed_asset_turnover_ratio: Optional[float] = None


class FinancialReportBatchCreate(BaseModel):
    """批量创建财报表请求模型"""
    financial_reports: List[FinancialReportCreate] = Field(..., description="财报表列表")

