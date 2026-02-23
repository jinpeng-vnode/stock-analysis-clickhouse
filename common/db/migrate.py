"""
ClickHouse自动迁移工具
"""
import os
import hashlib
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime
from loguru import logger
from clickhouse_connect.driver import Client
from config import config


def get_migrations_table_sql() -> str:
    """获取创建迁移追踪表的SQL"""
    return """
    CREATE TABLE IF NOT EXISTS migrations (
        filename String COMMENT '迁移文件名',
        executed_at DateTime DEFAULT now() COMMENT '执行时间',
        checksum String COMMENT '文件校验和',
        status String DEFAULT 'success' COMMENT '执行状态'
    )
    ENGINE = ReplacingMergeTree(executed_at)
    ORDER BY filename
    COMMENT '迁移执行记录表';
    """


def ensure_migrations_table(client: Client) -> None:
    """确保迁移追踪表存在"""
    client.command(get_migrations_table_sql())


def get_sql_directory() -> Path:
    """获取SQL文件目录"""
    # 从当前文件定位项目根目录
    current_file = Path(__file__)
    project_root = current_file.parent.parent.parent
    sql_dir = project_root / "sql"
    return sql_dir


def get_migration_files() -> List[Path]:
    """获取所有迁移SQL文件，按文件名排序"""
    sql_dir = get_sql_directory()
    if not sql_dir.exists():
        logger.warning(f"SQL目录不存在: {sql_dir}")
        return []
    
    # 获取所有 .sql 文件并按文件名排序
    sql_files = sorted(sql_dir.glob("*.sql"))
    logger.info(f"找到 {len(sql_files)} 个SQL迁移文件")
    return sql_files


def calculate_checksum(file_path: Path) -> str:
    """计算文件MD5校验和"""
    with open(file_path, 'rb') as f:
        return hashlib.md5(f.read()).hexdigest()


def get_executed_migrations(client: Client) -> Dict[str, Dict]:
    """获取已执行的迁移记录"""
    ensure_migrations_table(client)
    
    query = """
    SELECT 
        filename,
        executed_at,
        checksum,
        status
    FROM migrations
    FINAL
    ORDER BY filename
    """
    
    result = client.query(query)
    executed = {}
    
    for row in result.result_rows:
        filename = row[0]
        executed[filename] = {
            'executed_at': row[1],
            'checksum': row[2],
            'status': row[3]
        }
    
    return executed


def execute_sql_file(client: Client, file_path: Path) -> None:
    """执行SQL文件"""
    logger.info(f"执行迁移文件: {file_path.name}")
    
    with open(file_path, 'r', encoding='utf-8') as f:
        sql_content = f.read()
    
    # 移除BOM标记（如果有）
    if sql_content.startswith('\ufeff'):
        sql_content = sql_content[1:]
    
    # 分割SQL语句：按分号分割，但保留多行语句
    # 先简单处理：如果文件中有多个分号结尾的语句，逐条执行
    # 使用正则表达式或简单分割来提取语句
    statements = []
    current_statement = []
    in_string = False
    string_char = None
    
    lines = sql_content.split('\n')
    for line in lines:
        stripped = line.strip()
        # 跳过空行
        if not stripped:
            current_statement.append('')
            continue
        
        # 处理单行注释
        if stripped.startswith('--'):
            continue
        
        # 检查字符串字面量（简单处理）
        i = 0
        while i < len(line):
            char = line[i]
            if char in ("'", '"') and (i == 0 or line[i-1] != '\\'):
                if not in_string:
                    in_string = True
                    string_char = char
                elif char == string_char:
                    in_string = False
                    string_char = None
            i += 1
        
        current_statement.append(line)
        
        # 如果行以分号结尾且不在字符串中，说明一个语句结束
        if stripped.endswith(';') and not in_string:
            statement = '\n'.join(current_statement).strip()
            if statement:
                statements.append(statement)
            current_statement = []
            in_string = False
            string_char = None
    
    # 如果还有未完成的语句（文件末尾没有分号），也添加进去
    if current_statement:
        statement = '\n'.join(current_statement).strip()
        if statement:
            statements.append(statement)
    
    # 执行所有SQL语句
    for i, statement in enumerate(statements, 1):
        if statement.strip():
            logger.debug(f"执行SQL语句 {i}/{len(statements)}")
            client.command(statement)
    
    logger.info(f"迁移文件执行完成: {file_path.name}")


def record_migration(client: Client, filename: str, checksum: str, status: str = 'success') -> None:
    """记录迁移执行历史"""
    query = """
    INSERT INTO migrations (filename, executed_at, checksum, status)
    VALUES ('{filename}', now(), '{checksum}', '{status}')
    """.format(
        filename=filename.replace("'", "''"),  # SQL注入防护
        checksum=checksum,
        status=status
    )
    client.command(query)


def run_migrations(client: Optional[Client] = None, dry_run: bool = False) -> Dict:
    """
    执行所有未执行的迁移
    
    Args:
        client: ClickHouse客户端，如果为None则创建新连接
        dry_run: 如果为True，只检查不执行
    
    Returns:
        执行结果统计
    """
    from common.db.clickhouse_client import get_clickhouse_client
    
    # 如果没有提供客户端，创建新连接
    if client is None:
        client_gen = get_clickhouse_client()
        client = next(client_gen)
        should_close = True
    else:
        should_close = False
    
    # 确保迁移表存在
    ensure_migrations_table(client)
    
    # 获取已执行的迁移
    executed_migrations = get_executed_migrations(client)
    logger.info(f"已执行迁移数量: {len(executed_migrations)}")
    
    # 获取所有迁移文件
    migration_files = get_migration_files()
    
    # 统计信息
    stats = {
        'total': len(migration_files),
        'executed': len(executed_migrations),
        'pending': 0,
        'skipped': 0,
        'executed_now': 0,
        'failed': 0
    }
    
    # 执行未执行的迁移
    for file_path in migration_files:
        filename = file_path.name
        
        # 检查是否已执行
        if filename in executed_migrations:
            executed_info = executed_migrations[filename]
            current_checksum = calculate_checksum(file_path)
            
            # 检查文件是否被修改
            if executed_info['checksum'] == current_checksum:
                logger.debug(f"跳过已执行的迁移: {filename}")
                stats['skipped'] += 1
                continue
            else:
                logger.warning(
                    f"迁移文件已被修改: {filename} "
                    f"(原校验和: {executed_info['checksum'][:8]}..., "
                    f"新校验和: {current_checksum[:8]}...)"
                )
                # 文件被修改，可以选择重新执行或跳过
                # 这里选择跳过，避免重复执行
                stats['skipped'] += 1
                continue
        
        # 未执行的迁移
        stats['pending'] += 1
        
        if dry_run:
            logger.info(f"[DRY RUN] 将执行迁移: {filename}")
            stats['executed_now'] += 1
            continue
        
        # 执行迁移
        checksum = calculate_checksum(file_path)
        execute_sql_file(client, file_path)
        record_migration(client, filename, checksum, 'success')
        stats['executed_now'] += 1
        logger.success(f"迁移执行成功: {filename}")
    
    if should_close and client:
        client.close()
    
    return stats


def show_migration_status(client: Optional[Client] = None) -> None:
    """显示迁移状态"""
    from common.db.clickhouse_client import get_clickhouse_client
    
    if client is None:
        client_gen = get_clickhouse_client()
        client = next(client_gen)
        should_close = True
    else:
        should_close = False
    
    executed_migrations = get_executed_migrations(client)
    migration_files = get_migration_files()
    
    print("\n" + "="*60)
    print("ClickHouse 迁移状态")
    print("="*60)
    print(f"\n总迁移文件数: {len(migration_files)}")
    print(f"已执行迁移数: {len(executed_migrations)}")
    print(f"待执行迁移数: {len(migration_files) - len(executed_migrations)}")
    
    print("\n迁移文件列表:")
    print("-"*60)
    
    for file_path in migration_files:
        filename = file_path.name
        if filename in executed_migrations:
            info = executed_migrations[filename]
            status_icon = "✓" if info['status'] == 'success' else "✗"
            print(f"{status_icon} {filename:40s} [{info['status']:7s}] {info['executed_at']}")
        else:
            print(f"○ {filename:40s} [pending ]")
    
    print("="*60 + "\n")
    
    if should_close and client:
        client.close()

