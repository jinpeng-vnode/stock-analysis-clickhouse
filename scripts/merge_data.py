"""
数据合并脚本 - ClickHouse版本
用于合并增量更新导致的重复数据
"""
import os
import sys
from pathlib import Path
from datetime import datetime
from typing import List, Dict

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from loguru import logger
from clickhouse_connect import get_client
from clickhouse_connect.driver import Client
from config import config

# 设置日志
logger.remove()
logger.add(sys.stderr, level="INFO",
           format="<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>")
logger.add(
    "logs/merge_data.log",
    rotation="1 day",
    retention="7 days",
    level="INFO",
    format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {name}:{function}:{line} - {message}"
)


def create_clickhouse_client() -> Client:
    """创建ClickHouse客户端连接"""
    return get_client(
        host=config.CLICKHOUSE_HOST,
        port=config.CLICKHOUSE_PORT,
        database=config.CLICKHOUSE_DB,
        username=config.CLICKHOUSE_USER,
        password=config.CLICKHOUSE_PASSWORD,
        settings={
            'max_execution_time': 3600,  # 1小时超时
            'max_memory_usage': '20000000000',  # 20GB
            'max_threads': 16
        }
    )


def get_table_partitions(client: Client, table: str) -> List[str]:
    """获取表的所有分区"""
    query = f"""
    SELECT DISTINCT partition
    FROM system.parts
    WHERE database = '{config.CLICKHOUSE_DB}' 
      AND table = '{table}'
      AND active = 1
    ORDER BY partition
    """
    result = client.query(query).result_rows
    return [row[0] for row in result] if result else []


def get_table_stats(client: Client, table: str) -> Dict:
    """获取表的统计信息"""
    query = f"""
    SELECT 
        count() as total_rows,
        sum(rows) as total_parts_rows,
        count(DISTINCT partition) as partition_count,
        formatReadableSize(sum(bytes_on_disk)) as disk_size
    FROM system.parts
    WHERE database = '{config.CLICKHOUSE_DB}' 
      AND table = '{table}'
      AND active = 1
    """
    result = client.query(query).result_rows
    if result and result[0]:
        row = result[0]
        return {
            'total_rows': row[0] or 0,
            'total_parts_rows': row[1] or 0,
            'partition_count': row[2] or 0,
            'disk_size': row[3] or '0 B'
        }
    return {'total_rows': 0, 'total_parts_rows': 0, 'partition_count': 0, 'disk_size': '0 B'}


def optimize_table_final(client: Client, table: str, partition: str = None) -> bool:
    """
    优化表，强制合并数据
    
    Args:
        client: ClickHouse客户端
        table: 表名
        partition: 分区名（可选，如果指定则只合并该分区）
    
    Returns:
        是否成功
    """
    try:
        if partition:
            # 合并指定分区
            query = f"OPTIMIZE TABLE {table} PARTITION {partition} FINAL"
            logger.info(f"开始合并表 {table} 的分区 {partition}...")
        else:
            # 合并整个表的所有分区
            query = f"OPTIMIZE TABLE {table} FINAL"
            logger.info(f"开始合并表 {table} 的所有分区...")
        
        # 执行优化（异步执行，等待完成）
        client.command(query)
        logger.info(f"✅ 表 {table} 合并完成" + (f"（分区: {partition}）" if partition else ""))
        return True
        
    except Exception as e:
        logger.error(f"❌ 合并表 {table} 失败: {e}")
        return False


def cleanup_inactive_parts(client: Client, tables: List[str]) -> int:
    """
    清理非活跃的parts（合并后留下的旧数据）
    
    Args:
        client: ClickHouse客户端
        tables: 要清理的表列表
    
    Returns:
        清理的parts数量
    """
    cleanup_count = 0
    
    for table in tables:
        try:
            # 获取非活跃parts的数量和大小
            query = f"""
            SELECT count(), formatReadableSize(sum(bytes_on_disk))
            FROM system.parts
            WHERE database = '{config.CLICKHOUSE_DB}' 
              AND table = '{table}'
              AND active = 0
            """
            result = client.query(query).result_rows
            if result and result[0][0] > 0:
                inactive_count = result[0][0]
                inactive_size = result[0][1]
                logger.info(f"  表 {table}: 发现 {inactive_count} 个非活跃parts，占用 {inactive_size}")
                
                # 删除非活跃parts
                drop_query = f"""
                ALTER TABLE {table} DROP DETACHED PARTITION ID 'all'
                """
                # 注意：ClickHouse没有直接删除非活跃parts的命令
                # 需要使用DETACH然后DROP，或者等待自动清理
                # 这里我们使用OPTIMIZE来触发清理
                try:
                    # 再次优化表，这会触发清理非活跃parts
                    client.command(f"OPTIMIZE TABLE {table} FINAL")
                    cleanup_count += inactive_count
                    logger.info(f"  ✅ 表 {table} 清理完成")
                except Exception as e:
                    logger.warning(f"  ⚠️ 表 {table} 清理失败: {e}")
        except Exception as e:
            logger.error(f"检查表 {table} 的非活跃parts失败: {e}")
    
    return cleanup_count


def merge_all_tables(client: Client, by_partition: bool = False):
    """
    合并所有需要合并的表
    
    Args:
        client: ClickHouse客户端
        by_partition: 是否按分区逐个合并（更节省内存，但更慢）
    """
    # 需要合并的表列表
    tables = [
        'stock_daily_k_write',  # ReplacingMergeTree - K线写入表
        'stock_daily_i_write',  # ReplacingMergeTree - 指标写入表
        'stock_daily_k_agg',    # AggregatingMergeTree - K线聚合表
        'stock_daily_i_agg',    # AggregatingMergeTree - 指标聚合表
        'stock_info',           # ReplacingMergeTree - 股票信息表
    ]
    
    logger.info("=" * 60)
    logger.info("🚀 开始数据合并任务")
    logger.info("=" * 60)
    
    # 显示合并前的统计信息
    logger.info("\n📊 合并前的表统计信息:")
    for table in tables:
        stats = get_table_stats(client, table)
        logger.info(f"  {table}:")
        logger.info(f"    - 总行数: {stats['total_rows']:,}")
        logger.info(f"    - 分区数: {stats['partition_count']}")
        logger.info(f"    - 磁盘大小: {stats['disk_size']}")
    
    logger.info("\n" + "=" * 60)
    
    # 开始合并
    start_time = datetime.now()
    success_count = 0
    fail_count = 0
    
    for table in tables:
        logger.info(f"\n📋 处理表: {table}")
        
        if by_partition:
            # 按分区逐个合并（更节省内存）
            partitions = get_table_partitions(client, table)
            logger.info(f"  找到 {len(partitions)} 个分区")
            
            for partition in partitions:
                if optimize_table_final(client, table, partition):
                    success_count += 1
                else:
                    fail_count += 1
        else:
            # 合并整个表（更快，但需要更多内存）
            if optimize_table_final(client, table):
                success_count += 1
            else:
                fail_count += 1
    
    # 显示合并后的统计信息
    elapsed_time = (datetime.now() - start_time).total_seconds()
    logger.info("\n" + "=" * 60)
    logger.info("📊 合并后的表统计信息:")
    for table in tables:
        stats = get_table_stats(client, table)
        logger.info(f"  {table}:")
        logger.info(f"    - 总行数: {stats['total_rows']:,}")
        logger.info(f"    - 分区数: {stats['partition_count']}")
        logger.info(f"    - 磁盘大小: {stats['disk_size']}")
    
    logger.info("\n" + "=" * 60)
    logger.info(f"✅ 合并任务完成！")
    logger.info(f"   - 成功: {success_count}")
    logger.info(f"   - 失败: {fail_count}")
    logger.info(f"   - 耗时: {elapsed_time:.2f} 秒")
    logger.info("=" * 60)
    
    # 检查非活跃parts（合并后留下的旧数据）
    logger.info("\n" + "=" * 60)
    logger.info("📊 检查非活跃parts...")
    logger.info("=" * 60)
    
    cleanup_count = cleanup_inactive_parts(client, tables)
    
    if cleanup_count > 0:
        logger.info(f"\n💡 发现 {cleanup_count} 个非活跃parts")
        logger.info("   提示: 非活跃parts会在后台自动清理，或重启服务后清理")
        logger.info("   如需立即清理，请运行: python scripts/cleanup_inactive_parts.py")
    else:
        logger.info("✅ 没有发现非活跃parts")
    
    logger.info("=" * 60)


if __name__ == "__main__":
    client = None
    try:
        logger.info("🔧 连接ClickHouse数据库...")
        client = create_clickhouse_client()
        logger.info("✅ 连接成功")
        
        # 合并所有表（按分区合并，更节省内存）
        # 如果内存充足，可以改为 by_partition=False 来加快速度
        merge_all_tables(client, by_partition=True)
        
        # 显示清理后的空间统计
        logger.info("\n" + "=" * 60)
        logger.info("📊 最终空间统计:")
        logger.info("=" * 60)
        
        # 检查非活跃parts
        inactive_query = f"""
        SELECT 
            formatReadableSize(sum(bytes_on_disk)) as inactive_size,
            count() as inactive_count
        FROM system.parts
        WHERE database = '{config.CLICKHOUSE_DB}' 
          AND active = 0
        """
        result = client.query(inactive_query).result_rows
        if result and result[0][0]:
            logger.info(f"  非活跃parts: {result[0][1]} 个，占用 {result[0][0]}")
            logger.info(f"  💡 提示: 非活跃parts会在下次OPTIMIZE时自动清理")
        else:
            logger.info("  ✅ 没有非活跃parts，空间已优化")
        
        logger.info("=" * 60)
        
    except Exception as e:
        logger.error(f"❌ 执行失败: {e}")
        sys.exit(1)
    finally:
        if client:
            client.close()
            logger.info("🔌 已关闭数据库连接")

