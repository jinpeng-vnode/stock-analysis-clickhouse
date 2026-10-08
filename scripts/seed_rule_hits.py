"""
向 stock_rule_hit 写入分布在近180天的测试数据
"""
from datetime import datetime, date, timedelta
from pathlib import Path
import sys
import random

# 项目根路径加入 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from clickhouse_connect import get_client  # type: ignore
from clickhouse_connect.driver import Client  # type: ignore
from config import config  # type: ignore


def create_clickhouse_client() -> Client:
    return get_client(
        host=config.CLICKHOUSE_HOST,
        port=config.CLICKHOUSE_PORT,
        database=config.CLICKHOUSE_DB,
        username=config.CLICKHOUSE_USER,
        password=config.CLICKHOUSE_PASSWORD,
        settings={
            'max_execution_time': config.CLICKHOUSE_TIMEOUT,
            'max_threads': 8,
        },
    )


def generate_seed_rows() -> list[tuple[str, str, str, date, datetime]]:
    today = date.today()
    now = datetime.now()

    codes = [
        ("000001.SZ", "平安银行"),
        ("000002.SZ", "万 科Ａ"),
        ("600000.SH", "浦发银行"),
        ("600519.SH", "贵州茅台"),
        ("300750.SZ", "宁德时代"),
    ]
    rules = ["测试", "测试2", "低价回撤", "突破均线", "缩量上涨"]

    rows: list[tuple[str, str, str, date, datetime]] = []

    # 近180天，按交易日粗略估计（简单忽略周末过滤，主要用于测试分布）
    for day_delta in range(0, 180):
        td = today - timedelta(days=day_delta)
        ht = now - timedelta(days=day_delta)

        # 每天为每只股票按一定概率写入 0~3 条命中
        for code, name in codes:
            if random.random() < 0.6:  # 60% 概率当天有命中
                k = random.randint(1, 3)
                pick_rules = random.sample(rules, k)
                for rn in pick_rules:
                    rows.append((code, name, rn, td, ht))

    return rows


def main() -> None:
    client = create_clickhouse_client()

    # 生成数据
    rows = generate_seed_rows()

    # 分批写入（防止单次包过大）
    batch_size = 10_000
    for i in range(0, len(rows), batch_size):
        batch = rows[i : i + batch_size]
        if batch:
            client.insert(
                table='stock_rule_hit',
                data=batch,
                column_names=['code', 'name', 'rule_name', 'trade_date', 'hit_time'],
            )

    # 打印简单统计
    q1 = "SELECT count() FROM stock_rule_hit"
    q2 = "SELECT rule_name, count() as c FROM stock_rule_hit WHERE hit_time >= now() - INTERVAL 30 DAY GROUP BY rule_name ORDER BY c DESC LIMIT 5"
    total = client.query(q1).result_rows[0][0]
    top_rules = client.query(q2).result_rows
    print(f"seed rows total: {total}")
    for r in top_rules:
        print("top_rule_30d", r[0], r[1])


if __name__ == "__main__":
    main()


