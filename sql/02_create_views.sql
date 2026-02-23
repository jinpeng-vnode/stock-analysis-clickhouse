-- ============================================
-- ClickHouse股票分析系统 - 物化视图SQL脚本
-- 创建时间: 2025-10-15
-- 修复时间: 2025-10-22
-- 说明: 创建物化视图优化查询性能
-- 修复内容: 修复 stock_daily_full_from_indicators_mv 的版本计算逻辑
--           使用 greatest() 确保技术指标字段在 FINAL 去重时被正确保留
-- ============================================

USE stock_analysis;

-- ============================================
-- 物化视图1: stock_daily_k_dedup_mv - 写时聚合去重（argMax）
-- ============================================
-- 视图名: stock_daily_k_dedup_mv
-- 说明: 对同一 (code, trade_date) 选择 version 最新的一行聚合到读表 stock_daily_k_read
-- 注意: 需在 stock_daily_k_write 与 stock_daily_k_read 均存在后创建
-- ============================================
CREATE MATERIALIZED VIEW IF NOT EXISTS stock_daily_k_dedup_mv
TO stock_daily_k_agg
AS
SELECT
    r.code,
    r.trade_date,
    argMaxState(r.name, r.version)            AS name_state,
    argMaxState(r.open_price, r.version)      AS open_price_state,
    argMaxState(r.close_price, r.version)     AS close_price_state,
    argMaxState(r.high_price, r.version)      AS high_price_state,
    argMaxState(r.low_price, r.version)       AS low_price_state,
    argMaxState(r.volume, r.version)          AS volume_state,
    argMaxState(r.amount, r.version)          AS amount_state,
    argMaxState(r.amplitude, r.version)       AS amplitude_state,
    argMaxState(r.change_pct, r.version)      AS change_pct_state,
    argMaxState(r.change_amount, r.version)   AS change_amount_state,
    argMaxState(r.turnover_rate, r.version)   AS turnover_rate_state,
    argMaxState(r.version, r.version)         AS version_state
FROM stock_daily_k_write AS r
GROUP BY r.code, r.trade_date
COMMENT '去重聚合物化视图 - 写时聚合到 AggregatingMergeTree（argMaxState）';

-- ============================================
-- 物化视图2: stock_daily_i_dedup_mv - 指标写时聚合去重（argMax）
-- ============================================
-- 视图名: stock_daily_i_dedup_mv
-- 说明: 对同一 (code, trade_date) 选择 version 最新的一行聚合到读表 stock_daily_i_read
-- 注意: 需在 stock_daily_i_write 与 stock_daily_i_read 均存在后创建
-- ============================================
CREATE MATERIALIZED VIEW IF NOT EXISTS stock_daily_i_dedup_mv
TO stock_daily_i_agg
AS
SELECT
    r.code,
    r.trade_date,
    argMaxState(r.wr6, r.version)           AS wr6_state,
    argMaxState(r.wr10, r.version)          AS wr10_state,
    argMaxState(r.ma5, r.version)           AS ma5_state,
    argMaxState(r.ma10, r.version)          AS ma10_state,
    argMaxState(r.ma20, r.version)          AS ma20_state,
    argMaxState(r.slope_180, r.version)     AS slope_180_state,
    argMaxState(r.slope_7, r.version)       AS slope_7_state,
    argMaxState(r.fit_7, r.version)         AS fit_7_state,
    argMaxState(r.fit_180, r.version)       AS fit_180_state,
    argMaxState(r.best_buy, r.version)      AS best_buy_state,
    argMaxState(r.best_sell, r.version)     AS best_sell_state,
    argMaxState(r.buy_count_7, r.version)   AS buy_count_7_state,
    argMaxState(r.sell_count_7, r.version)  AS sell_count_7_state,
    argMaxState(r.buy_count_14, r.version)  AS buy_count_14_state,
    argMaxState(r.sell_count_14, r.version) AS sell_count_14_state,
    argMaxState(r.version, r.version)       AS version_state
FROM stock_daily_i_write AS r
GROUP BY r.code, r.trade_date
COMMENT '指标去重聚合物化视图 - 写时聚合到 AggregatingMergeTree（argMaxState）';

-- ============================================
-- 注释: 合并物化视图已移除
-- ============================================
-- 说明: stock_daily_k_i_read 现在是直接从聚合中间表读取的视图
-- 数据流: 写入表 → 聚合中间表 → 合并视图（无需物化视图）
-- 优势: 任意时刻查询都只有一条记录，无需 FINAL，性能更好
-- ============================================

-- ============================================
-- 版本冲突检测视图
-- ============================================
-- 检测聚合中间表中的版本冲突（因为合并视图已经自动去重）
CREATE OR REPLACE VIEW version_conflict_check AS
SELECT 
    code,
    trade_date,
    count(*) as record_count,
    min(version) as min_version,
    max(version) as max_version,
    max(version) - min(version) as version_diff_seconds
FROM (
    SELECT code, trade_date, argMaxMerge(version_state) as version
    FROM stock_daily_k_agg
    GROUP BY code, trade_date
    UNION ALL
    SELECT code, trade_date, argMaxMerge(version_state) as version
    FROM stock_daily_i_agg
    GROUP BY code, trade_date
)
GROUP BY code, trade_date
HAVING count(*) > 1
ORDER BY version_diff_seconds DESC
COMMENT '数据质量监控视图 - 内部使用，检测聚合中间表版本冲突';

-- ============================================
-- 创建完成提示（放在最后）
-- ============================================
SELECT 'ClickHouse物化视图创建完成！' as message;
SELECT '视图数量: 3个' as view_count;
SELECT '视图1: stock_daily_k_dedup_mv - K线写时聚合至聚合中间表' as view1;
SELECT '视图2: stock_daily_i_dedup_mv - 指标写时聚合至聚合中间表' as view2;
SELECT '视图3: version_conflict_check - 版本冲突检测视图' as view3;
SELECT '策略: 读表使用只读视图(从 AggregatingMergeTree 合并)，恒唯一且无需 FINAL' as strategy_note;
SELECT '合并表: stock_daily_k_i_read 现在是直接从聚合中间表读取的视图' as merge_note;
SELECT '优势: 任意时刻查询都只有一条记录，无需 FINAL，性能更好' as advantage;
