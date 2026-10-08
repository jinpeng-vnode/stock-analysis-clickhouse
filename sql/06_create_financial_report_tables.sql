-- ============================================
-- ClickHouse股票分析系统 - 财报表建表SQL脚本
-- 创建时间: 2025-01-XX
-- 说明: 存储上市公司财报表数据
-- 数据量: 约5000股 × 4报告期/年 × 20年 = 40万条
-- 分区策略: 按报告年度分区
-- ============================================

USE stock_analysis;

-- ============================================
-- 表: stock_financial_report - 财报表
-- ============================================
-- 表名: stock_financial_report
-- 说明: 存储上市公司财报表数据
-- 引擎: ReplacingMergeTree - 自动去重，保留最新版本
-- 分区: 按报告年度分区
-- ============================================
CREATE TABLE IF NOT EXISTS stock_financial_report (
    code String COMMENT '股票代码（6位数字）',
    quote_name String COMMENT '股票名称',
    report_date Date COMMENT '报告日期',
    report_name String COMMENT '报告名称（如：2025三季报）',
    currency String DEFAULT 'CNY' COMMENT '货币代码',
    currency_name String DEFAULT '人民币' COMMENT '货币名称',
    org_type UInt8 DEFAULT 1 COMMENT '组织类型',
    
    -- 经营活动产生的现金流量 (Operating Activities)
    oa_ncf Nullable(Float64) COMMENT '经营活动产生的现金流量净额',
    oa_cash_received_of_sales_service Nullable(Float64) COMMENT '销售商品、提供劳务收到的现金',
    oa_refund_of_tax_and_levies Nullable(Float64) COMMENT '收到的税费返还',
    oa_cash_received_of_othr Nullable(Float64) COMMENT '收到其他与经营活动有关的现金',
    oa_sub_total_ci Nullable(Float64) COMMENT '经营活动现金流入小计',
    oa_goods_buy_and_service_cash_pay Nullable(Float64) COMMENT '购买商品、接受劳务支付的现金',
    oa_cash_paid_to_employee_etc Nullable(Float64) COMMENT '支付给职工以及为职工支付的现金',
    oa_payments_of_all_taxes Nullable(Float64) COMMENT '支付的各项税费',
    oa_othrcash_paid_relating_to Nullable(Float64) COMMENT '支付其他与经营活动有关的现金',
    oa_sub_total_cos Nullable(Float64) COMMENT '经营活动现金流出小计',
    
    -- 投资活动产生的现金流量 (Investing Activities)
    ia_ncf Nullable(Float64) COMMENT '投资活动产生的现金流量净额',
    ia_cash_received_of_dspsl_invest Nullable(Float64) COMMENT '收回投资收到的现金',
    ia_invest_income_cash_received Nullable(Float64) COMMENT '取得投资收益收到的现金',
    ia_net_cash_of_disposal_assets Nullable(Float64) COMMENT '处置固定资产、无形资产和其他长期资产收回的现金净额',
    ia_net_cash_of_disposal_branch Nullable(Float64) COMMENT '处置子公司及其他营业单位收到的现金净额',
    ia_cash_received_of_othr Nullable(Float64) COMMENT '收到其他与投资活动有关的现金',
    ia_sub_total_ci Nullable(Float64) COMMENT '投资活动现金流入小计',
    ia_invest_paid_cash Nullable(Float64) COMMENT '购建固定资产、无形资产和其他长期资产支付的现金',
    ia_cash_paid_for_assets Nullable(Float64) COMMENT '投资支付的现金',
    ia_othrcash_paid_relating_to Nullable(Float64) COMMENT '支付其他与投资活动有关的现金',
    ia_sub_total_cos Nullable(Float64) COMMENT '投资活动现金流出小计',
    
    -- 筹资活动产生的现金流量 (Financing Activities)
    fa_ncf Nullable(Float64) COMMENT '筹资活动产生的现金流量净额',
    fa_cash_received_of_absorb_invest Nullable(Float64) COMMENT '吸收投资收到的现金',
    fa_cash_received_from_investor Nullable(Float64) COMMENT '其中：子公司吸收少数股东投资收到的现金',
    fa_cash_received_from_bond_issue Nullable(Float64) COMMENT '发行债券收到的现金',
    fa_cash_received_of_borrowing Nullable(Float64) COMMENT '取得借款收到的现金',
    fa_cash_received_of_othr Nullable(Float64) COMMENT '收到其他与筹资活动有关的现金',
    fa_sub_total_ci Nullable(Float64) COMMENT '筹资活动现金流入小计',
    fa_cash_pay_for_debt Nullable(Float64) COMMENT '偿还债务支付的现金',
    fa_cash_paid_of_distribution Nullable(Float64) COMMENT '分配股利、利润或偿付利息支付的现金',
    fa_branch_paid_to_minority_holder Nullable(Float64) COMMENT '其中：子公司支付给少数股东的股利、利润',
    fa_othrcash_paid_relating_to Nullable(Float64) COMMENT '支付其他与筹资活动有关的现金',
    fa_sub_total_cos Nullable(Float64) COMMENT '筹资活动现金流出小计',
    
    -- 现金及现金等价物 (Cash and Cash Equivalents)
    cce_effect_of_exchange_chg Nullable(Float64) COMMENT '汇率变动对现金及现金等价物的影响',
    cce_net_increase Nullable(Float64) COMMENT '现金及现金等价物净增加额',
    cce_initial_balance Nullable(Float64) COMMENT '期初现金及现金等价物余额',
    cce_final_balance Nullable(Float64) COMMENT '期末现金及现金等价物余额',
    
    -- 其他
    net_cash_amt_from_branch Nullable(Float64) COMMENT '子公司支付给少数股东的股利、利润',
    
    -- 元数据
    version DateTime DEFAULT now() COMMENT '版本时间（用于去重）'
)
ENGINE = ReplacingMergeTree(version)
PARTITION BY toYear(report_date)
ORDER BY (code, report_date)
SETTINGS index_granularity = 8192
COMMENT '财报表 - ReplacingMergeTree(version)引擎，存储财报表数据';

-- ============================================
-- 添加财务指标字段 (Financial Indicators)
-- ============================================
-- 盈利能力指标
ALTER TABLE stock_financial_report 
    ADD COLUMN IF NOT EXISTS avg_roe Nullable(Float64) COMMENT '平均ROE（净资产收益率）',
    ADD COLUMN IF NOT EXISTS np_per_share Nullable(Float64) COMMENT '每股净利润',
    ADD COLUMN IF NOT EXISTS operate_cash_flow_ps Nullable(Float64) COMMENT '每股经营现金流',
    ADD COLUMN IF NOT EXISTS basic_eps Nullable(Float64) COMMENT '基本每股收益',
    ADD COLUMN IF NOT EXISTS capital_reserve Nullable(Float64) COMMENT '资本公积',
    ADD COLUMN IF NOT EXISTS undistri_profit_ps Nullable(Float64) COMMENT '每股未分配利润',
    ADD COLUMN IF NOT EXISTS net_interest_of_total_assets Nullable(Float64) COMMENT '净利润/总资产',
    ADD COLUMN IF NOT EXISTS net_selling_rate Nullable(Float64) COMMENT '净销售率',
    ADD COLUMN IF NOT EXISTS gross_selling_rate Nullable(Float64) COMMENT '毛利率',
    ADD COLUMN IF NOT EXISTS total_revenue Nullable(Float64) COMMENT '总营收',
    ADD COLUMN IF NOT EXISTS operating_income_yoy Nullable(Float64) COMMENT '营业收入同比增长率（%）',
    ADD COLUMN IF NOT EXISTS net_profit_atsopc Nullable(Float64) COMMENT '归属于母公司股东的净利润',
    ADD COLUMN IF NOT EXISTS net_profit_atsopc_yoy Nullable(Float64) COMMENT '归属于母公司股东的净利润同比增长率（%）',
    ADD COLUMN IF NOT EXISTS net_profit_after_nrgal_atsolc Nullable(Float64) COMMENT '扣除非经常性损益后的净利润',
    ADD COLUMN IF NOT EXISTS np_atsopc_nrgal_yoy Nullable(Float64) COMMENT '扣除非经常性损益后的净利润同比增长率（%）',
    ADD COLUMN IF NOT EXISTS ore_dlt Nullable(Float64) COMMENT 'ROE（净资产收益率）',
    ADD COLUMN IF NOT EXISTS rop Nullable(Float64) COMMENT 'ROA（总资产收益率）',
    -- 偿债能力指标
    ADD COLUMN IF NOT EXISTS asset_liab_ratio Nullable(Float64) COMMENT '资产负债率（%）',
    ADD COLUMN IF NOT EXISTS current_ratio Nullable(Float64) COMMENT '流动比率',
    ADD COLUMN IF NOT EXISTS quick_ratio Nullable(Float64) COMMENT '速动比率',
    ADD COLUMN IF NOT EXISTS equity_multiplier Nullable(Float64) COMMENT '权益乘数',
    ADD COLUMN IF NOT EXISTS equity_ratio Nullable(Float64) COMMENT '权益比率（%）',
    ADD COLUMN IF NOT EXISTS holder_equity Nullable(Float64) COMMENT '股东权益',
    ADD COLUMN IF NOT EXISTS ncf_from_oa_to_total_liab Nullable(Float64) COMMENT '经营活动现金流/总负债',
    -- 营运能力指标
    ADD COLUMN IF NOT EXISTS inventory_turnover_days Nullable(Float64) COMMENT '存货周转天数',
    ADD COLUMN IF NOT EXISTS receivable_turnover_days Nullable(Float64) COMMENT '应收账款周转天数',
    ADD COLUMN IF NOT EXISTS accounts_payable_turnover_days Nullable(Float64) COMMENT '应付账款周转天数',
    ADD COLUMN IF NOT EXISTS cash_cycle Nullable(Float64) COMMENT '现金周期（天）',
    ADD COLUMN IF NOT EXISTS operating_cycle Nullable(Float64) COMMENT '经营周期（天）',
    ADD COLUMN IF NOT EXISTS total_capital_turnover Nullable(Float64) COMMENT '总资本周转率',
    ADD COLUMN IF NOT EXISTS inventory_turnover Nullable(Float64) COMMENT '存货周转率',
    ADD COLUMN IF NOT EXISTS account_receivable_turnover Nullable(Float64) COMMENT '应收账款周转率',
    ADD COLUMN IF NOT EXISTS accounts_payable_turnover Nullable(Float64) COMMENT '应付账款周转率',
    ADD COLUMN IF NOT EXISTS current_asset_turnover_rate Nullable(Float64) COMMENT '流动资产周转率',
    ADD COLUMN IF NOT EXISTS fixed_asset_turnover_ratio Nullable(Float64) COMMENT '固定资产周转率';

