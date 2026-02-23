-- ============================================
-- ClickHouse股票分析系统 - 规则命中表SQL脚本
-- 创建时间: 2025-10-28
-- 说明: 记录“规则-股票-日期”的命中关系，按最近N条统计
-- ============================================

-- 目标数据库
USE stock_analysis;

-- ============================================
-- 表: stock_rule_hit - 规则命中记录表
-- ============================================
CREATE TABLE IF NOT EXISTS stock_rule_hit
(
    code       String    COMMENT '股票代码',
    name       String    COMMENT '股票名称',
    rule_name  String    COMMENT '规则名称',
    trade_date Date      COMMENT '命中对应的交易日期',
    hit_time   DateTime  DEFAULT now() COMMENT '命中记录写入时间'
)
ENGINE = MergeTree
PARTITION BY toYYYYMM(trade_date)
ORDER BY (rule_name, trade_date, code, hit_time)
COMMENT '规则-股票命中记录表：追加式插入，不去重，基于最近N条进行统计';

-- ============================================
-- 创建完成提示（放在最后）
-- ============================================
SELECT '规则-股票命中记录表创建完成！(stock_rule_hit)' AS message;