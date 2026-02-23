#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
清空 stock_announcement 表的数据
"""
import sys
import logging
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from clickhouse_connect import get_client
from clickhouse_connect.driver import Client
from config import config

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - [清空数据库] - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)


def create_clickhouse_client() -> Client:
    """创建ClickHouse客户端连接"""
    return get_client(
        host=config.CLICKHOUSE_HOST,
        port=config.CLICKHOUSE_PORT,
        database=config.CLICKHOUSE_DB,
        username=config.CLICKHOUSE_USER,
        password=config.CLICKHOUSE_PASSWORD,
        settings={
            'max_execution_time': config.CLICKHOUSE_TIMEOUT,
            'max_memory_usage': '10000000000',  # 10GB
            'max_threads': 8
        }
    )


def clear_stock_announcement_table():
    """清空 stock_announcement 表"""
    db_client = None
    
    try:
        logger.info("正在连接ClickHouse数据库...")
        db_client = create_clickhouse_client()
        logger.info("数据库连接成功")
        
        # 先查询记录数
        count_result = db_client.query("SELECT count() FROM stock_announcement FINAL")
        total_count = count_result.result_rows[0][0]
        logger.info(f"当前 stock_announcement 表有 {total_count} 条记录")
        
        if total_count == 0:
            logger.info("表已经是空的，无需清空")
            return
        
        # 确认操作
        logger.warning("="*60)
        logger.warning(f"即将清空 stock_announcement 表的所有数据（共 {total_count} 条记录）")
        logger.warning("="*60)
        
        # 使用 TRUNCATE TABLE 清空表（更高效）
        try:
            db_client.command("TRUNCATE TABLE stock_announcement")
            logger.info("✅ 表已清空")
        except Exception as e:
            # 如果 TRUNCATE 不支持，使用 DELETE
            logger.warning(f"TRUNCATE 失败，尝试使用 DELETE: {e}")
            db_client.command("ALTER TABLE stock_announcement DELETE WHERE 1=1")
            logger.info("✅ 表已清空")
        
        # 验证清空结果
        count_result = db_client.query("SELECT count() FROM stock_announcement FINAL")
        remaining_count = count_result.result_rows[0][0]
        
        if remaining_count == 0:
            logger.info("✅ 验证成功：表已完全清空")
        else:
            logger.warning(f"⚠️ 警告：表中仍有 {remaining_count} 条记录")
        
    except Exception as e:
        logger.error(f"清空表失败: {e}")
        raise
    finally:
        if db_client:
            db_client.close()
            logger.info("数据库连接已关闭")


if __name__ == "__main__":
    logger.info("="*60)
    logger.info("开始清空 stock_announcement 表")
    logger.info("="*60)
    
    clear_stock_announcement_table()
    
    logger.info("="*60)
    logger.info("操作完成")
    logger.info("="*60)

