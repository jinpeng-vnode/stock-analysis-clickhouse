-- ============================================
-- ClickHouse股票分析系统 - 资金流向表SQL脚本
-- 创建时间: 2025-01-18
-- 说明: 创建股票资金流向数据表，支持主力、超大单、大单、中单、小单净流入数据
-- 数据量: 约4375万条（5000股 × 35年 × 250交易日）
-- 架构: 写入表 + 聚合中间表 + 读视图 + 物化视图
-- ============================================

USE stock_analysis;

-- ============================================
-- 表1: stock_money_flow_write - 资金流向写入表
-- ============================================
-- 表名: stock_money_flow_write
-- 说明: 存储股票资金流向数据，作为数据写入入口
-- 引擎: ReplacingMergeTree(version) - 以 version 作为去重版本
-- 分区: 按年分区，与K线表保持一致
-- 作用: 写表 - 只写，数据写入入口
-- ============================================
CREATE TABLE IF NOT EXISTS stock_money_flow_write (
    code String COMMENT '股票代码（6位数字）',
    trade_date Date COMMENT '交易日期',
    
    -- 基础价格数据
    close_price Float32 COMMENT '收盘价（元）',
    change_pct Float32 COMMENT '涨跌幅（%）',
    
    -- 主力资金流向
    main_net_inflow_amount Float64 COMMENT '主力净流入-净额（元）',
    main_net_inflow_ratio Float32 COMMENT '主力净流入-净占比（%）',
    
    -- 超大单资金流向
    super_large_net_inflow_amount Float64 COMMENT '超大单净流入-净额（元）',
    super_large_net_inflow_ratio Float32 COMMENT '超大单净流入-净占比（%）',
    
    -- 大单资金流向
    large_net_inflow_amount Float64 COMMENT '大单净流入-净额（元）',
    large_net_inflow_ratio Float32 COMMENT '大单净流入-净占比（%）',
    
    -- 中单资金流向
    medium_net_inflow_amount Float64 COMMENT '中单净流入-净额（元）',
    medium_net_inflow_ratio Float32 COMMENT '中单净流入-净占比（%）',
    
    -- 小单资金流向
    small_net_inflow_amount Float64 COMMENT '小单净流入-净额（元）',
    small_net_inflow_ratio Float32 COMMENT '小单净流入-净占比（%）',
    
    -- 元数据
    version DateTime DEFAULT now() COMMENT '版本时间，用于去重'
)
ENGINE = ReplacingMergeTree(version)
PARTITION BY toYear(trade_date)
ORDER BY (code, trade_date)
SETTINGS index_granularity = 8192
COMMENT '资金流向写入表 - ReplacingMergeTree(version)引擎，只写，数据写入入口';

-- ============================================
-- 表2: stock_money_flow_agg - 资金流向聚合中间表
-- ============================================
-- 表名: stock_money_flow_agg
-- 说明: 存储资金流向数据的聚合状态，用于去重和版本管理
-- 引擎: AggregatingMergeTree - 存储 argMaxState 聚合状态
-- 分区: 按年分区
-- 作用: 聚合中间表 - 存储聚合状态
-- ============================================
CREATE TABLE IF NOT EXISTS stock_money_flow_agg (
    code String COMMENT '股票代码',
    trade_date Date COMMENT '交易日期',
    
    -- 基础价格数据聚合状态
    close_price_state AggregateFunction(argMax, Float32, DateTime) COMMENT '收盘价聚合状态',
    change_pct_state AggregateFunction(argMax, Float32, DateTime) COMMENT '涨跌幅聚合状态',
    
    -- 主力资金流向聚合状态
    main_net_inflow_amount_state AggregateFunction(argMax, Float64, DateTime) COMMENT '主力净流入-净额聚合状态',
    main_net_inflow_ratio_state AggregateFunction(argMax, Float32, DateTime) COMMENT '主力净流入-净占比聚合状态',
    
    -- 超大单资金流向聚合状态
    super_large_net_inflow_amount_state AggregateFunction(argMax, Float64, DateTime) COMMENT '超大单净流入-净额聚合状态',
    super_large_net_inflow_ratio_state AggregateFunction(argMax, Float32, DateTime) COMMENT '超大单净流入-净占比聚合状态',
    
    -- 大单资金流向聚合状态
    large_net_inflow_amount_state AggregateFunction(argMax, Float64, DateTime) COMMENT '大单净流入-净额聚合状态',
    large_net_inflow_ratio_state AggregateFunction(argMax, Float32, DateTime) COMMENT '大单净流入-净占比聚合状态',
    
    -- 中单资金流向聚合状态
    medium_net_inflow_amount_state AggregateFunction(argMax, Float64, DateTime) COMMENT '中单净流入-净额聚合状态',
    medium_net_inflow_ratio_state AggregateFunction(argMax, Float32, DateTime) COMMENT '中单净流入-净占比聚合状态',
    
    -- 小单资金流向聚合状态
    small_net_inflow_amount_state AggregateFunction(argMax, Float64, DateTime) COMMENT '小单净流入-净额聚合状态',
    small_net_inflow_ratio_state AggregateFunction(argMax, Float32, DateTime) COMMENT '小单净流入-净占比聚合状态',
    
    -- 版本聚合状态
    version_state AggregateFunction(argMax, DateTime, DateTime) COMMENT '版本时间聚合状态'
)
ENGINE = AggregatingMergeTree
PARTITION BY toYear(trade_date)
ORDER BY (trade_date, code)
SETTINGS index_granularity = 8192
COMMENT '资金流向聚合中间表 - AggregatingMergeTree，存储 argMaxState 状态';

-- ============================================
-- 视图3: stock_money_flow_read - 资金流向读视图
-- ============================================
-- 视图名: stock_money_flow_read
-- 说明: 从聚合中间表合并出最新版本的资金流向数据
-- 数据源: stock_money_flow_agg
-- 聚合函数: argMaxMerge() - 合并聚合状态，获取最新版本
-- 作用: 只读视图 - 供业务查询使用，无需 FINAL 即可保证唯一性
-- ============================================
CREATE OR REPLACE VIEW stock_money_flow_read AS
SELECT
    code,
    trade_date,
    argMaxMerge(close_price_state) AS close_price,
    argMaxMerge(change_pct_state) AS change_pct,
    argMaxMerge(main_net_inflow_amount_state) AS main_net_inflow_amount,
    argMaxMerge(main_net_inflow_ratio_state) AS main_net_inflow_ratio,
    argMaxMerge(super_large_net_inflow_amount_state) AS super_large_net_inflow_amount,
    argMaxMerge(super_large_net_inflow_ratio_state) AS super_large_net_inflow_ratio,
    argMaxMerge(large_net_inflow_amount_state) AS large_net_inflow_amount,
    argMaxMerge(large_net_inflow_ratio_state) AS large_net_inflow_ratio,
    argMaxMerge(medium_net_inflow_amount_state) AS medium_net_inflow_amount,
    argMaxMerge(medium_net_inflow_ratio_state) AS medium_net_inflow_ratio,
    argMaxMerge(small_net_inflow_amount_state) AS small_net_inflow_amount,
    argMaxMerge(small_net_inflow_ratio_state) AS small_net_inflow_ratio,
    argMaxMerge(version_state) AS version
FROM stock_money_flow_agg
GROUP BY code, trade_date;

-- ============================================
-- 物化视图4: stock_money_flow_dedup_mv - 资金流向去重物化视图
-- ============================================
-- 视图名: stock_money_flow_dedup_mv
-- 说明: 对同一 (code, trade_date) 选择 version 最新的一行聚合到读表
-- 数据流: stock_money_flow_write → stock_money_flow_agg
-- 作用: 写时聚合去重，确保数据唯一性
-- ============================================
CREATE MATERIALIZED VIEW IF NOT EXISTS stock_money_flow_dedup_mv
TO stock_money_flow_agg
AS
SELECT
    r.code,
    r.trade_date,
    argMaxState(r.close_price, r.version) AS close_price_state,
    argMaxState(r.change_pct, r.version) AS change_pct_state,
    argMaxState(r.main_net_inflow_amount, r.version) AS main_net_inflow_amount_state,
    argMaxState(r.main_net_inflow_ratio, r.version) AS main_net_inflow_ratio_state,
    argMaxState(r.super_large_net_inflow_amount, r.version) AS super_large_net_inflow_amount_state,
    argMaxState(r.super_large_net_inflow_ratio, r.version) AS super_large_net_inflow_ratio_state,
    argMaxState(r.large_net_inflow_amount, r.version) AS large_net_inflow_amount_state,
    argMaxState(r.large_net_inflow_ratio, r.version) AS large_net_inflow_ratio_state,
    argMaxState(r.medium_net_inflow_amount, r.version) AS medium_net_inflow_amount_state,
    argMaxState(r.medium_net_inflow_ratio, r.version) AS medium_net_inflow_ratio_state,
    argMaxState(r.small_net_inflow_amount, r.version) AS small_net_inflow_amount_state,
    argMaxState(r.small_net_inflow_ratio, r.version) AS small_net_inflow_ratio_state,
    argMaxState(r.version, r.version) AS version_state
FROM stock_money_flow_write AS r
GROUP BY r.code, r.trade_date
COMMENT '资金流向去重物化视图 - 写时聚合到 AggregatingMergeTree（argMaxState）';

-- ============================================
-- 视图5: stock_daily_k_mf_read - K线+资金流向合并视图
-- ============================================
-- 视图名: stock_daily_k_mf_read
-- 说明: 合并K线数据和资金流向数据，提供完整的股票分析视图
-- 数据源: stock_daily_k_agg + stock_money_flow_agg（LEFT JOIN）
-- 作用: 只读视图 - 供业务查询使用，包含K线和资金流向数据
-- ============================================
CREATE OR REPLACE VIEW stock_daily_k_mf_read AS
SELECT
    k.code,
    k.trade_date,
    -- K线数据
    argMaxMerge(k.name_state) AS name,
    argMaxMerge(k.open_price_state) AS open_price,
    argMaxMerge(k.close_price_state) AS close_price,
    argMaxMerge(k.high_price_state) AS high_price,
    argMaxMerge(k.low_price_state) AS low_price,
    argMaxMerge(k.volume_state) AS volume,
    argMaxMerge(k.amount_state) AS amount,
    argMaxMerge(k.amplitude_state) AS amplitude,
    argMaxMerge(k.change_pct_state) AS change_pct,
    argMaxMerge(k.change_amount_state) AS change_amount,
    argMaxMerge(k.turnover_rate_state) AS turnover_rate,
    -- 资金流向数据
    argMaxMerge(mf.close_price_state) AS mf_close_price,
    argMaxMerge(mf.change_pct_state) AS mf_change_pct,
    argMaxMerge(mf.main_net_inflow_amount_state) AS main_net_inflow_amount,
    argMaxMerge(mf.main_net_inflow_ratio_state) AS main_net_inflow_ratio,
    argMaxMerge(mf.super_large_net_inflow_amount_state) AS super_large_net_inflow_amount,
    argMaxMerge(mf.super_large_net_inflow_ratio_state) AS super_large_net_inflow_ratio,
    argMaxMerge(mf.large_net_inflow_amount_state) AS large_net_inflow_amount,
    argMaxMerge(mf.large_net_inflow_ratio_state) AS large_net_inflow_ratio,
    argMaxMerge(mf.medium_net_inflow_amount_state) AS medium_net_inflow_amount,
    argMaxMerge(mf.medium_net_inflow_ratio_state) AS medium_net_inflow_ratio,
    argMaxMerge(mf.small_net_inflow_amount_state) AS small_net_inflow_amount,
    argMaxMerge(mf.small_net_inflow_ratio_state) AS small_net_inflow_ratio,
    argMaxMerge(k.version_state) AS version
FROM stock_daily_k_agg k
LEFT JOIN stock_money_flow_agg mf
    ON k.code = mf.code AND k.trade_date = mf.trade_date
GROUP BY k.code, k.trade_date;

-- ============================================
-- 索引优化
-- ============================================
-- 为资金流向表添加必要的索引，提升查询性能

-- 为主力净流入金额添加跳数索引（用于排序和筛选）
ALTER TABLE stock_money_flow_write
    ADD INDEX IF NOT EXISTS idx_main_net_inflow_amount main_net_inflow_amount TYPE minmax GRANULARITY 4;

-- 为主力净流入占比添加跳数索引（用于排序和筛选）
ALTER TABLE stock_money_flow_write
    ADD INDEX IF NOT EXISTS idx_main_net_inflow_ratio main_net_inflow_ratio TYPE minmax GRANULARITY 4;

-- 为涨跌幅添加跳数索引（用于排序和筛选）
ALTER TABLE stock_money_flow_write
    ADD INDEX IF NOT EXISTS idx_change_pct change_pct TYPE minmax GRANULARITY 4;

-- ============================================
-- 创建完成提示
-- ============================================
SELECT 'ClickHouse股票资金流向表结构创建完成！' as message;
SELECT '表数量: 2个（写入表+聚合中间表）' as table_count;
SELECT '视图数量: 3个（读视图+合并视图）' as view_count;
SELECT '物化视图数量: 1个（去重物化视图）' as mv_count;
SELECT '分区策略: 按年分区（1990-2025）' as partition_strategy;
SELECT '预期数据量: 4375万条' as expected_records;
SELECT '支持字段: 主力、超大单、大单、中单、小单净流入金额和占比' as supported_fields;