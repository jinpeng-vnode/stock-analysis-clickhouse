"""
ClickHouse迁移命令行工具
"""
import sys
import argparse
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from loguru import logger
from common.db.clickhouse_client import get_clickhouse_client
from common.db.migrate import run_migrations, show_migration_status


def main():
    parser = argparse.ArgumentParser(description='ClickHouse数据库迁移工具')
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='仅检查迁移状态，不执行'
    )
    parser.add_argument(
        '--status',
        action='store_true',
        help='显示迁移状态'
    )
    
    args = parser.parse_args()
    
    # 配置日志
    logger.remove()
    logger.add(
        sys.stderr,
        level="INFO",
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>"
    )
    
    client = next(get_clickhouse_client())
    
    if args.status:
        show_migration_status(client=client)
    else:
        logger.info("开始执行数据库迁移...")
        stats = run_migrations(client=client, dry_run=args.dry_run)
        
        print("\n" + "="*60)
        print("迁移执行结果")
        print("="*60)
        print(f"总迁移文件数: {stats['total']}")
        print(f"已执行迁移数: {stats['executed']}")
        print(f"待执行迁移数: {stats['pending']}")
        print(f"本次执行数: {stats['executed_now']}")
        print(f"跳过数: {stats['skipped']}")
        print(f"失败数: {stats['failed']}")
        print("="*60)
        
        if stats['failed'] > 0:
            sys.exit(1)
    
    client.close()


if __name__ == "__main__":
    main()

