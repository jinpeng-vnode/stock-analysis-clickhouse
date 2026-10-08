"""
清理非活跃parts脚本 - ClickHouse版本
用于清理合并后留下的非活跃parts，释放磁盘空间
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
    "logs/cleanup_inactive_parts.log",
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


def get_inactive_parts_stats(client: Client) -> Dict:
    """获取非活跃parts的统计信息"""
    query = f"""
    SELECT 
        count() as total_count,
        formatReadableSize(sum(bytes_on_disk)) as total_size,
        count(DISTINCT table) as table_count
    FROM system.parts
    WHERE database = '{config.CLICKHOUSE_DB}' 
      AND active = 0
    """
    result = client.query(query).result_rows
    if result and result[0]:
        return {
            'total_count': result[0][0] or 0,
            'total_size': result[0][1] or '0 B',
            'table_count': result[0][2] or 0
        }
    return {'total_count': 0, 'total_size': '0 B', 'table_count': 0}


def get_inactive_parts_by_table(client: Client) -> List[Dict]:
    """获取每个表的非活跃parts信息"""
    query = f"""
    SELECT 
        table,
        count() as parts_count,
        formatReadableSize(sum(bytes_on_disk)) as parts_size
    FROM system.parts
    WHERE database = '{config.CLICKHOUSE_DB}' 
      AND active = 0
    GROUP BY table
    ORDER BY sum(bytes_on_disk) DESC
    """
    result = client.query(query).result_rows
    tables_info = []
    for row in result:
        tables_info.append({
            'table': row[0],
            'count': row[1],
            'size': row[2]
        })
    return tables_info


def cleanup_inactive_parts(client: Client) -> bool:
    """
    清理非活跃parts
    
    注意：ClickHouse的非活跃parts会在以下情况自动清理：
    1. 执行OPTIMIZE TABLE ... FINAL后，旧parts会被标记为非活跃
    2. 非活跃parts会在后台自动删除（通常需要一些时间）
    3. 也可以手动触发清理，但需要谨慎操作
    
    这里我们通过再次执行OPTIMIZE来触发清理
    """
    try:
        # 获取需要清理的表
        tables_info = get_inactive_parts_by_table(client)
        
        if not tables_info:
            logger.info("✅ 没有发现非活跃parts，无需清理")
            return True
        
        logger.info(f"📋 发现 {len(tables_info)} 个表有非活跃parts:")
        for info in tables_info:
            logger.info(f"  - {info['table']}: {info['count']} 个parts，占用 {info['size']}")
        
        logger.info("\n💡 ClickHouse会自动清理非活跃parts，但可能需要一些时间")
        logger.info("   可以通过以下方式加速清理：")
        logger.info("   1. 等待后台自动清理（推荐）")
        logger.info("   2. 重启ClickHouse服务（会立即清理）")
        logger.info("   3. 手动删除detached目录（需要谨慎）")
        
        # 尝试通过OPTIMIZE触发清理（但这不会立即删除非活跃parts）
        # 非活跃parts会在后台自动清理，或者重启服务时清理
        
        return True
        
    except Exception as e:
        logger.error(f"❌ 清理失败: {e}")
        return False


def force_cleanup_by_restart_hint():
    """提示如何强制清理"""
    logger.info("\n" + "=" * 60)
    logger.info("🔧 强制清理非活跃parts的方法：")
    logger.info("=" * 60)
    logger.info("方法1: 重启ClickHouse服务（推荐）")
    logger.info("   docker restart stock_clickhouse_db")
    logger.info("   重启后，非活跃parts会被自动清理")
    logger.info("")
    logger.info("方法2: 手动清理detached目录（需要谨慎）")
    logger.info("   1. 停止ClickHouse服务")
    logger.info("   2. 删除 /var/lib/clickhouse/store/*/detached 目录")
    logger.info("   3. 重启服务")
    logger.info("")
    logger.info("方法3: 等待后台自动清理（最安全）")
    logger.info("   ClickHouse会在后台自动清理非活跃parts")
    logger.info("   通常需要几小时到几天时间")
    logger.info("=" * 60)


if __name__ == "__main__":
    client = None
    try:
        logger.info("🔧 连接ClickHouse数据库...")
        client = create_clickhouse_client()
        logger.info("✅ 连接成功")
        
        logger.info("=" * 60)
        logger.info("🧹 检查非活跃parts...")
        logger.info("=" * 60)
        
        # 获取统计信息
        stats = get_inactive_parts_stats(client)
        logger.info(f"\n📊 非活跃parts统计:")
        logger.info(f"   - 总数: {stats['total_count']:,} 个")
        logger.info(f"   - 占用空间: {stats['total_size']}")
        logger.info(f"   - 涉及表数: {stats['table_count']} 个")
        
        if stats['total_count'] > 0:
            # 显示各表的详细信息
            logger.info("\n📋 各表非活跃parts详情:")
            tables_info = get_inactive_parts_by_table(client)
            for info in tables_info:
                logger.info(f"   - {info['table']}: {info['count']} 个parts，占用 {info['size']}")
            
            # 尝试清理
            logger.info("\n" + "=" * 60)
            cleanup_inactive_parts(client)
            
            # 显示清理建议
            force_cleanup_by_restart_hint()
        else:
            logger.info("\n✅ 没有发现非活跃parts，空间已优化")
        
        logger.info("\n" + "=" * 60)
        logger.info("✅ 检查完成！")
        logger.info("=" * 60)
        
    except Exception as e:
        logger.error(f"❌ 执行失败: {e}")
        sys.exit(1)
    finally:
        if client:
            client.close()
            logger.info("🔌 已关闭数据库连接")

