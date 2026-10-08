-- ============================================
-- ClickHouse股票分析系统 - 建表SQL脚本
-- 创建时间: 2025-10-15
-- 说明: 按年分区优化，支持1990年至今35年历史数据
-- 数据量: 约4375万条（5000股 × 35年 × 250交易日）
-- ============================================

-- 创建数据库（如果不存在）
CREATE DATABASE IF NOT EXISTS stock_analysis;

USE stock_analysis;

-- ============================================
-- 表1: stock_info - 股票基础信息表
-- ============================================
-- 表名: stock_info
-- 说明: 存储A股所有股票的基础信息，约5000条记录
-- 引擎: ReplacingMergeTree - 自动去重，保留最新版本
-- 用途: 股票代码查询、股票名称映射
-- 作用: 可读写，供业务查询使用
-- ============================================
CREATE TABLE IF NOT EXISTS stock_info (
    code String COMMENT '股票代码（6位数字）',
    name String COMMENT '股票名称',
    market String DEFAULT '' COMMENT '市场类型：SH/SZ',
    status String DEFAULT '正常' COMMENT '股票状态',
    version DateTime DEFAULT now() COMMENT '版本时间，用于去重',
    
    -- 组织信息
    org_id Nullable(String) COMMENT '组织ID',
    org_name_cn Nullable(String) COMMENT '中文全称',
    org_name_en Nullable(String) COMMENT '英文全称',
    org_short_name_en Nullable(String) COMMENT '英文简称',
    pre_name_cn Nullable(String) COMMENT '曾用名',
    
    -- 业务信息
    main_operation_business Nullable(String) COMMENT '主营业务',
    operating_scope Nullable(String) COMMENT '经营范围',
    industry_code Nullable(String) COMMENT '行业代码',
    industry_name Nullable(String) COMMENT '行业名称',
    
    -- 注册信息
    district_encode Nullable(String) COMMENT '地区编码',
    provincial_name Nullable(String) COMMENT '省份名称',
    established_date Nullable(Date) COMMENT '成立日期',
    reg_asset Nullable(Float64) COMMENT '注册资本',
    reg_address_cn Nullable(String) COMMENT '注册地址（中文）',
    reg_address_en Nullable(String) COMMENT '注册地址（英文）',
    office_address_cn Nullable(String) COMMENT '办公地址（中文）',
    office_address_en Nullable(String) COMMENT '办公地址（英文）',
    
    -- 联系信息
    telephone Nullable(String) COMMENT '电话',
    postcode Nullable(String) COMMENT '邮编',
    fax Nullable(String) COMMENT '传真',
    email Nullable(String) COMMENT '邮箱',
    org_website Nullable(String) COMMENT '网站',
    
    -- 管理信息
    legal_representative Nullable(String) COMMENT '法定代表人',
    chairman Nullable(String) COMMENT '董事长',
    general_manager Nullable(String) COMMENT '总经理',
    secretary Nullable(String) COMMENT '董事会秘书',
    executives_nums Nullable(UInt16) COMMENT '高管人数',
    actual_controller Nullable(String) COMMENT '实际控制人',
    classi_name Nullable(String) COMMENT '企业性质',
    
    -- 上市信息
    listed_date Nullable(Date) COMMENT '上市日期',
    actual_issue_vol Nullable(Float64) COMMENT '实际发行量',
    issue_price Nullable(Float32) COMMENT '发行价格',
    actual_rc_net_amt Nullable(Float64) COMMENT '实际募集净额',
    pe_after_issuing Nullable(Float32) COMMENT '发行后市盈率',
    online_success_rate_of_issue Nullable(Float32) COMMENT '网上中签率',
    
    -- 其他信息
    staff_num Nullable(UInt32) COMMENT '员工数',
    currency_encode Nullable(String) COMMENT '货币编码',
    currency Nullable(String) COMMENT '货币'
) 
ENGINE = ReplacingMergeTree(version)
ORDER BY code
COMMENT '股票基础信息表 - ReplacingMergeTree引擎，可读写，存储股票基础信息';

-- ============================================
-- 表2: stock_daily_k_read - 日K线数据表（按年分区）
-- ============================================
-- 表名: stock_daily_k_read
-- 说明: 存储所有股票的日K线OHLC数据（1990年至今）
-- 数据量: 约4375万条（5000股 × 35年 × 250交易日）
-- 分区策略: 按年分区，35个分区（1990-2025）
-- 分区优势:
--   - 查询年度数据只扫描1个分区（最常见场景）
--   - 分区数量少，管理简单
--   - 历史数据自然归档
-- 压缩: Gorilla/T64编解码器，5倍压缩率
-- 存储: 压缩后约350-500MB
-- 作用: 读表 - 只读，由物化视图写入
-- ============================================
-- 聚合中间表（K线）
CREATE TABLE IF NOT EXISTS stock_daily_k_agg (
    code String COMMENT '股票代码',
    trade_date Date COMMENT '交易日期（1990-01-01至今）',
    name_state AggregateFunction(argMax, String, DateTime) COMMENT '股票名称聚合状态',
    open_price_state AggregateFunction(argMax, Float32, DateTime) COMMENT '开盘价聚合状态',
    close_price_state AggregateFunction(argMax, Float32, DateTime) COMMENT '收盘价聚合状态',
    high_price_state AggregateFunction(argMax, Float32, DateTime) COMMENT '最高价聚合状态',
    low_price_state AggregateFunction(argMax, Float32, DateTime) COMMENT '最低价聚合状态',
    volume_state AggregateFunction(argMax, UInt64, DateTime) COMMENT '成交量聚合状态',
    amount_state AggregateFunction(argMax, Float64, DateTime) COMMENT '成交额聚合状态',
    amplitude_state AggregateFunction(argMax, Nullable(Float32), DateTime) COMMENT '振幅聚合状态',
    change_pct_state AggregateFunction(argMax, Nullable(Float32), DateTime) COMMENT '涨跌幅聚合状态',
    change_amount_state AggregateFunction(argMax, Nullable(Float32), DateTime) COMMENT '涨跌额聚合状态',
    turnover_rate_state AggregateFunction(argMax, Nullable(Float32), DateTime) COMMENT '换手率聚合状态',
    version_state AggregateFunction(argMax, DateTime, DateTime) COMMENT '版本时间聚合状态'
)
ENGINE = AggregatingMergeTree
PARTITION BY toYear(trade_date)
ORDER BY (trade_date, code)
SETTINGS index_granularity = 8192
COMMENT 'K线聚合中间表 - AggregatingMergeTree，存储 argMaxState 状态';

-- 注意：AggregatingMergeTree 表不支持在聚合函数上创建索引
-- 如需索引，可在查询时使用 argMaxMerge() 表达式

-- 读视图（K线最新快照）
-- 说明:
--   - 从聚合中间表 stock_daily_k_agg 以 argMaxMerge 合并出最新版本
--   - 任意时刻对同一 (code, trade_date) 恒唯一，无需 FINAL
--   - 分区裁剪：继承自中间表按年分区（toYear(trade_date)）
--   - 典型查询：按日期范围+code 过滤，避免 SELECT * 全表扫
--   - 索引：跳数索引建立在中间表上（使用 argMaxMerge(...) 表达式）
-- 注意:
--   - 该对象为 VIEW，不支持表级 COMMENT 子句
--   - 如需物理表 COMMENT，可改为物化落地表，但会牺牲“零 FINAL 即时唯一”的优势
CREATE OR REPLACE VIEW stock_daily_k_read AS
SELECT
    code,
    trade_date,
    argMaxMerge(name_state)          AS name,
    argMaxMerge(open_price_state)    AS open_price,
    argMaxMerge(close_price_state)   AS close_price,
    argMaxMerge(high_price_state)    AS high_price,
    argMaxMerge(low_price_state)     AS low_price,
    argMaxMerge(volume_state)        AS volume,
    argMaxMerge(amount_state)        AS amount,
    argMaxMerge(amplitude_state)     AS amplitude,
    argMaxMerge(change_pct_state)    AS change_pct,
    argMaxMerge(change_amount_state) AS change_amount,
    argMaxMerge(turnover_rate_state) AS turnover_rate,
    argMaxMerge(version_state)       AS version
FROM stock_daily_k_agg
GROUP BY code, trade_date;

-- ============================================
-- 表2.1: stock_daily_k_write - K线数据写入表
-- ============================================
-- 表名: stock_daily_k_write
-- 说明: 作为K线数据写入入口，包含 version 列，用于通过MV聚合去重
-- 引擎: ReplacingMergeTree(version) - 以 version 作为去重版本
-- 读表: stock_daily_k_read，由物化视图汇总写入
-- 作用: 写表 - 只写，数据写入入口
-- ============================================
CREATE TABLE IF NOT EXISTS stock_daily_k_write (
    code String COMMENT '股票代码',
    trade_date Date COMMENT '交易日期（1990-01-01至今）',
    name String COMMENT '股票名称',

    -- OHLC数据
    open_price Float32 COMMENT '开盘价（元）',
    close_price Float32 COMMENT '收盘价（元）',
    high_price Float32 COMMENT '最高价（元）',
    low_price Float32 COMMENT '最低价（元）',

    -- 成交数据
    volume UInt64 COMMENT '成交量（手）',
    amount Float64 COMMENT '成交额（元）',

    -- 衍生指标
    amplitude Nullable(Float32) COMMENT '振幅（%）',
    change_pct Nullable(Float32) COMMENT '涨跌幅（%）',
    change_amount Nullable(Float32) COMMENT '涨跌额（元）',
    turnover_rate Nullable(Float32) COMMENT '换手率（%）',

    -- 元数据
    version DateTime DEFAULT now() COMMENT '版本时间（上游去重用，本表不使用）'
)
ENGINE = ReplacingMergeTree(version)
PARTITION BY toYear(trade_date)
ORDER BY (code, trade_date)
SETTINGS index_granularity = 8192
COMMENT 'K线数据写入表 - ReplacingMergeTree(version)引擎，只写，数据写入入口';


-- ============================================
-- 表3: stock_daily_i_write - 技术指标表（按年分区）
-- ============================================
-- 表名: stock_daily_i_write
-- 说明: 存储预计算的技术指标
-- 策略: 预计算+存储，查询5000股<0.5秒
-- 数据量: 约4375万条
-- 扩展: ALTER TABLE ADD COLUMN（<1秒）
-- 作用: 写表 - 只写，存储计算后的指标
-- ============================================
CREATE TABLE IF NOT EXISTS stock_daily_i_write (
    code String COMMENT '股票代码',
    trade_date Date COMMENT '交易日期',
    
    -- 威廉指标
    wr6 Nullable(Float32) COMMENT 'WR6威廉指标',
    wr10 Nullable(Float32) COMMENT 'WR10威廉指标',
    
    -- 移动平均
    ma5 Nullable(Float32) COMMENT 'MA5均线（元）',
    ma10 Nullable(Float32) COMMENT 'MA10均线（元）',
    ma20 Nullable(Float32) COMMENT 'MA20均线（元）',
    
    -- 趋势指标
    slope_180 Nullable(Float32) COMMENT '180个交易日斜率',
    slope_7 Nullable(Float32) COMMENT '7个交易日斜率',
    
    -- 拟合值指标
    fit_7 Nullable(Float32) COMMENT '7日拟合值',
    fit_180 Nullable(Float32) COMMENT '180日拟合值',
    
    -- 买卖信号
    best_buy Nullable(UInt8) COMMENT '最佳买点（0/1）',
    best_sell Nullable(UInt8) COMMENT '最佳卖点（0/1）',
    
    -- 买卖点统计
    buy_count_7 Nullable(UInt8) COMMENT '7个交易日买点数量',
    sell_count_7 Nullable(UInt8) COMMENT '7个交易日卖点数量',
    buy_count_14 Nullable(UInt8) COMMENT '14个交易日买点数量',
    sell_count_14 Nullable(UInt8) COMMENT '14个交易日卖点数量',
    
    version DateTime DEFAULT now() COMMENT '版本时间，用于去重'
) 
ENGINE = ReplacingMergeTree(version)
PARTITION BY toYear(trade_date)
ORDER BY (trade_date, code)
SETTINGS index_granularity = 8192
COMMENT '技术指标表 - ReplacingMergeTree引擎，只写，存储技术指标';

-- 添加买卖信号索引
-- bloom_filter索引：适合布尔值过滤，性能更好
ALTER TABLE stock_daily_i_write
    ADD INDEX IF NOT EXISTS idx_best_buy best_buy TYPE bloom_filter GRANULARITY 4,
    ADD INDEX IF NOT EXISTS idx_best_sell best_sell TYPE bloom_filter GRANULARITY 4;

-- ============================================
-- 表4: stock_daily_i_read - 技术指标读表（按年分区）
-- ============================================
-- 表名: stock_daily_i_read
-- 说明: 存储去重后的技术指标数据
-- 策略: 由物化视图从写入表聚合去重后写入
-- 数据量: 约4375万条
-- 作用: 读表 - 只读，供业务查询使用
-- ============================================
-- 聚合中间表（指标）
CREATE TABLE IF NOT EXISTS stock_daily_i_agg (
    code String COMMENT '股票代码',
    trade_date Date COMMENT '交易日期',
    wr6_state AggregateFunction(argMax, Nullable(Float32), DateTime) COMMENT 'WR6威廉指标聚合状态',
    wr10_state AggregateFunction(argMax, Nullable(Float32), DateTime) COMMENT 'WR10威廉指标聚合状态',
    ma5_state AggregateFunction(argMax, Nullable(Float32), DateTime) COMMENT 'MA5均线聚合状态',
    ma10_state AggregateFunction(argMax, Nullable(Float32), DateTime) COMMENT 'MA10均线聚合状态',
    ma20_state AggregateFunction(argMax, Nullable(Float32), DateTime) COMMENT 'MA20均线聚合状态',
    slope_180_state AggregateFunction(argMax, Nullable(Float32), DateTime) COMMENT '180个交易日斜率聚合状态',
    slope_7_state AggregateFunction(argMax, Nullable(Float32), DateTime) COMMENT '7个交易日斜率聚合状态',
    fit_7_state AggregateFunction(argMax, Nullable(Float32), DateTime) COMMENT '7日拟合值聚合状态',
    fit_180_state AggregateFunction(argMax, Nullable(Float32), DateTime) COMMENT '180日拟合值聚合状态',
    best_buy_state AggregateFunction(argMax, Nullable(UInt8), DateTime) COMMENT '最佳买点聚合状态',
    best_sell_state AggregateFunction(argMax, Nullable(UInt8), DateTime) COMMENT '最佳卖点聚合状态',
    buy_count_7_state AggregateFunction(argMax, Nullable(UInt8), DateTime) COMMENT '7个交易日买点数量聚合状态',
    sell_count_7_state AggregateFunction(argMax, Nullable(UInt8), DateTime) COMMENT '7个交易日卖点数量聚合状态',
    buy_count_14_state AggregateFunction(argMax, Nullable(UInt8), DateTime) COMMENT '14个交易日买点数量聚合状态',
    sell_count_14_state AggregateFunction(argMax, Nullable(UInt8), DateTime) COMMENT '14个交易日卖点数量聚合状态',
    version_state AggregateFunction(argMax, DateTime, DateTime) COMMENT '版本时间聚合状态'
)
ENGINE = AggregatingMergeTree
PARTITION BY toYear(trade_date)
ORDER BY (trade_date, code)
SETTINGS index_granularity = 8192
COMMENT '技术指标聚合中间表 - AggregatingMergeTree，存储 argMaxState 状态';

-- 注意：AggregatingMergeTree 表不支持在聚合函数上创建索引
-- 如需索引，可在查询时使用 argMaxMerge() 表达式

-- 读视图（指标最新快照）
-- 说明:
--   - 从聚合中间表 stock_daily_i_agg 以 argMaxMerge 合并出最新版本
--   - 任意时刻对同一 (code, trade_date) 恒唯一，无需 FINAL
--   - 分区裁剪：继承自中间表按年分区（toYear(trade_date)）
--   - 典型查询：按日期范围+code 过滤，避免 SELECT * 全表扫
--   - 索引：布隆/跳数索引建立在中间表上（使用 argMaxMerge(...) 表达式）
-- 注意:
--   - 该对象为 VIEW，不支持表级 COMMENT 子句
--   - 如需物理表 COMMENT，可改为物化落地表，但会牺牲“零 FINAL 即时唯一”的优势
CREATE OR REPLACE VIEW stock_daily_i_read AS
SELECT
    code,
    trade_date,
    argMaxMerge(wr6_state)           AS wr6,
    argMaxMerge(wr10_state)          AS wr10,
    argMaxMerge(ma5_state)           AS ma5,
    argMaxMerge(ma10_state)          AS ma10,
    argMaxMerge(ma20_state)          AS ma20,
    argMaxMerge(slope_180_state)     AS slope_180,
    argMaxMerge(slope_7_state)       AS slope_7,
    argMaxMerge(fit_7_state)         AS fit_7,
    argMaxMerge(fit_180_state)       AS fit_180,
    argMaxMerge(best_buy_state)      AS best_buy,
    argMaxMerge(best_sell_state)     AS best_sell,
    argMaxMerge(buy_count_7_state)   AS buy_count_7,
    argMaxMerge(sell_count_7_state)  AS sell_count_7,
    argMaxMerge(buy_count_14_state)  AS buy_count_14,
    argMaxMerge(sell_count_14_state) AS sell_count_14,
    argMaxMerge(version_state)       AS version
FROM stock_daily_i_agg
GROUP BY code, trade_date;

-- ============================================
-- 视图5: stock_daily_k_i_read - K线+指标合并视图
-- ============================================
-- 视图名: stock_daily_k_i_read
-- 说明: 从聚合中间表合并K线和指标数据，确保任意时刻查询都只有一条记录
-- 数据源: stock_daily_k_agg + stock_daily_i_agg（LEFT JOIN）
-- 聚合函数: argMaxMerge() - 合并聚合状态，获取最新版本
-- 作用: 只读视图 - 供业务查询使用，无需 FINAL 即可保证唯一性
-- ============================================
-- 注意:
--   - 该对象为 VIEW，不支持表级 COMMENT 子句
--   - 任意时刻对同一 (code, trade_date) 恒唯一，无需 FINAL
--   - 典型查询：按日期范围+code 过滤，避免 SELECT * 全表扫
--   - 索引：跳数索引建立在中间表上（使用 argMaxMerge(...) 表达式）
CREATE OR REPLACE VIEW stock_daily_k_i_read AS
SELECT
    k.code,
    k.trade_date,
    argMaxMerge(k.name_state) as name,
    argMaxMerge(k.open_price_state) as open_price,
    argMaxMerge(k.close_price_state) as close_price,
    argMaxMerge(k.high_price_state) as high_price,
    argMaxMerge(k.low_price_state) as low_price,
    argMaxMerge(k.volume_state) as volume,
    argMaxMerge(k.amount_state) as amount,
    argMaxMerge(k.amplitude_state) as amplitude,
    argMaxMerge(k.change_pct_state) as change_pct,
    argMaxMerge(k.change_amount_state) as change_amount,
    argMaxMerge(k.turnover_rate_state) as turnover_rate,
    argMaxMerge(i.wr6_state) as wr6,
    argMaxMerge(i.wr10_state) as wr10,
    argMaxMerge(i.ma5_state) as ma5,
    argMaxMerge(i.ma10_state) as ma10,
    argMaxMerge(i.ma20_state) as ma20,
    argMaxMerge(i.slope_180_state) as slope_180,
    argMaxMerge(i.slope_7_state) as slope_7,
    argMaxMerge(i.fit_7_state) as fit_7,
    argMaxMerge(i.fit_180_state) as fit_180,
    argMaxMerge(i.best_buy_state) as best_buy,
    argMaxMerge(i.best_sell_state) as best_sell,
    argMaxMerge(i.buy_count_7_state) as buy_count_7,
    argMaxMerge(i.sell_count_7_state) as sell_count_7,
    argMaxMerge(i.buy_count_14_state) as buy_count_14,
    argMaxMerge(i.sell_count_14_state) as sell_count_14,
    argMaxMerge(k.version_state) as version
FROM stock_daily_k_agg k
LEFT JOIN stock_daily_i_agg i
    ON k.code = i.code AND k.trade_date = i.trade_date
GROUP BY k.code, k.trade_date;

-- ============================================
-- 创建完成提示
-- ============================================
SELECT 'ClickHouse股票分析系统表结构创建完成！' as message;
SELECT '表数量: 6个' as table_count;
SELECT '分区策略: 按年分区（1990-2025）' as partition_strategy;
SELECT '预期数据量: 4375万条' as expected_records;
