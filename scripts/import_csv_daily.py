"""
从本地 CSV 批量导入日线数据到 ClickHouse（写入 stock_daily_raw）
数据源示例: 股票分析/数据/efinance_000001_平安银行_daily.csv
要求: 跳过列 WR6, WR10, 最佳买点, 最佳卖点
"""
import sys
import re
from pathlib import Path
from typing import Optional

import pandas as pd
from loguru import logger

# 注意: bulk_insert 模块可能需要重构，如不存在请使用 ClickHouse 客户端直接插入
from common.utils.bulk_insert import StockDailyInserter


def sanitize_name(name: str) -> str:
    """清理股票名称中的非法文件字符（与抓取脚本保持一致）"""
    return re.sub(r'[\\/:*?"<>|]', "_", str(name)).strip()


def parse_code_name_from_filename(file_path: Path) -> Optional[tuple[str, str]]:
    """从文件名中解析 code 与 name，例如: efinance_000001_平安银行_daily.csv"""
    m = re.search(r"efinance_(\d{6})_(.+?)_daily\.csv$", file_path.name)
    if m is None:
        return None
    code = m.group(1)
    name = m.group(2)
    return code, name


def import_csv_file(csv_path: Path) -> int:
    """导入单个 CSV 文件，返回成功写入的行数"""
    parsed = parse_code_name_from_filename(csv_path)
    if parsed is None:
        logger.warning(f"文件名不符合规则，跳过: {csv_path.name}")
        return 0
    code, name = parsed

    # 读取 CSV
    df = pd.read_csv(csv_path)

    # 必要列校验（按中文表头）
    needed = [
        "日期", "开盘", "收盘", "最高", "最低",
        "成交量", "成交额", "振幅", "涨跌幅", "涨跌额", "换手率",
    ]
    for col in needed:
        if col not in df.columns:
            logger.error(f"缺少必要列 {col}: {csv_path}")
            return 0

    inserted = 0
    with StockDailyInserter() as inserter:
        for _, row in df.iterrows():
            trade_date = str(row["日期"])  # 形如 1991-04-03
            open_price = float(row["开盘"]) if pd.notna(row["开盘"]) else 0.0
            close_price = float(row["收盘"]) if pd.notna(row["收盘"]) else 0.0
            high_price = float(row["最高"]) if pd.notna(row["最高"]) else 0.0
            low_price = float(row["最低"]) if pd.notna(row["最低"]) else 0.0
            volume = int(float(row["成交量"])) if pd.notna(row["成交量"]) else 0
            amount = float(row["成交额"]) if pd.notna(row["成交额"]) else 0.0
            amplitude = float(row["振幅"]) if pd.notna(row["振幅"]) else None
            change_pct = float(row["涨跌幅"]) if pd.notna(row["涨跌幅"]) else None
            change_amount = float(row["涨跌额"]) if pd.notna(row["涨跌额"]) else None
            turnover_rate = float(row["换手率"]) if pd.notna(row["换手率"]) else None

            inserter.add_stock_daily(
                code=code,
                trade_date=trade_date,
                name=sanitize_name(name),
                open_price=round(open_price, 4),
                close_price=round(close_price, 4),
                high_price=round(high_price, 4),
                low_price=round(low_price, 4),
                volume=volume,
                amount=round(amount, 2),
                amplitude=None if amplitude is None else round(amplitude, 4),
                change_pct=None if change_pct is None else round(change_pct, 4),
                change_amount=None if change_amount is None else round(change_amount, 4),
                turnover_rate=None if turnover_rate is None else round(turnover_rate, 4),
            )
            inserted += 1

    logger.info(f"文件导入完成: {csv_path.name}, 行数: {inserted}")
    return inserted


def main():
    # 数据目录: 项目根目录/股票分析/数据
    data_dir = Path(__file__).resolve().parents[2] / "股票分析" / "数据"
    if not data_dir.exists():
        logger.error(f"数据目录不存在: {data_dir}")
        return

    csv_files = sorted(data_dir.glob("efinance_*_daily.csv"))
    if not csv_files:
        logger.warning(f"未找到 CSV 文件: {data_dir}")
        return

    logger.info(f"开始导入 CSV，共 {len(csv_files)} 个文件")
    total = 0
    for csv in csv_files:
        total += import_csv_file(csv)

    logger.info(f"全部导入完成，总写入行数: {total}")


if __name__ == "__main__":
    logger.add(
        "logs/import_csv_daily.log",
        rotation="1 day",
        retention="7 days",
        level="INFO",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {name}:{function}:{line} - {message}",
    )
    main()


