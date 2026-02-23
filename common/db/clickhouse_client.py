"""
ClickHouse客户端 - 使用FastAPI依赖注入管理连接
"""
from typing import Generator
from clickhouse_connect import get_client
from clickhouse_connect.driver import Client
from loguru import logger
from config import config


def get_clickhouse_client() -> Generator[Client, None, None]:
    """ClickHouse客户端依赖注入函数"""
    client = None
    try:
        client = get_client(
            host=config.CLICKHOUSE_HOST,
            port=config.CLICKHOUSE_PORT,
            database=config.CLICKHOUSE_DB,
            username=config.CLICKHOUSE_USER,
            password=config.CLICKHOUSE_PASSWORD,
            settings={
                'max_execution_time': config.CLICKHOUSE_TIMEOUT,
                'max_memory_usage': '20000000000',  # 10GB
                'max_threads': 8
            }
        )
        logger.debug("ClickHouse客户端连接已建立")
        yield client
    except Exception as e:
        logger.error(f"ClickHouse连接失败: {e}")
        raise
    finally:
        if client:
            client.close()
            logger.debug("ClickHouse客户端连接已关闭")


def init_clickhouse() -> None:
    """初始化ClickHouse连接（测试连接）"""
    try:
        client = next(get_clickhouse_client())
        client.query("SELECT 1")
        logger.info("ClickHouse连接测试成功")
    except Exception as e:
        logger.error(f"ClickHouse连接测试失败: {e}")
        raise


def close_clickhouse() -> None:
    """关闭ClickHouse连接（依赖注入自动管理，无需手动操作）"""
    logger.info("ClickHouse连接由FastAPI依赖注入自动管理")

