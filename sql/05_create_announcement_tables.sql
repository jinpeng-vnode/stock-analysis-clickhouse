-- ============================================
-- ClickHouse股票分析系统 - 公告表SQL脚本
-- 创建时间: 2025-01-31
-- 说明: 创建股票公告数据表，支持公告标题、类型、内容、附件等数据
-- 架构: ReplacingMergeTree表，按年分区，自动去重
-- ============================================

USE stock_analysis;

-- ============================================
-- 表: stock_announcement - 股票公告表
-- ============================================
-- 表名: stock_announcement
-- 说明: 存储股票公告数据，按年分区优化
-- 引擎: ReplacingMergeTree(version) - 自动去重，保留最新版本
-- 分区策略: 按年分区（toYear(announce_date)），每年一个分区
-- 分区优势:
--   - 查询年度数据只扫描1个分区（最常见场景）
--   - 分区数量少，管理简单
--   - 历史数据自然归档
--   - 删除旧数据只需删除对应分区
-- 排序: (code, announce_date, detail_url) - 保证唯一性并优化查询
-- 作用: 可读写，直接存储公告数据
-- ============================================
CREATE TABLE IF NOT EXISTS stock_announcement (
    code String COMMENT '股票代码（6位数字）',
    announce_date Date COMMENT '公告日期',
    title String COMMENT '公告标题',
    type String COMMENT '公告类型（如：业绩预告、重大合同、股权变动等）',
    detail_url String COMMENT '详情页URL（唯一标识）',
    content String COMMENT '公告正文内容（可能很长）',
    attachments String COMMENT '附件PDF链接URL（一般只有一个）',
    version DateTime DEFAULT now() COMMENT '版本时间，用于去重和保留最新版本'
)
ENGINE = ReplacingMergeTree(version)
PARTITION BY toYear(announce_date)
ORDER BY (code, announce_date, detail_url)
SETTINGS index_granularity = 8192
COMMENT '股票公告表 - ReplacingMergeTree引擎，按年分区，自动去重，保留最新版本';

-- ============================================
-- 创建完成提示
-- ============================================
SELECT 'ClickHouse股票公告表结构创建完成！' as message;
SELECT '表名: stock_announcement' as table_name;
SELECT '引擎: ReplacingMergeTree(version) - 自动去重，保留最新版本' as engine_type;
SELECT '分区策略: 按年分区（toYear(announce_date)）' as partition_strategy;
SELECT '排序键: (code, announce_date, detail_url)' as order_by;
SELECT '支持字段: 标题、类型、内容、附件、详情URL' as supported_fields;

