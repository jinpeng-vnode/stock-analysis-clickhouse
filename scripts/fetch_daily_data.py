"""
日线数据抓取脚本 - ClickHouse版本
"""
import os
import sys
import argparse
import time
import re
import queue
from datetime import datetime, date, timedelta
from typing import List, Dict, Optional, Tuple
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import pandas as pd
import requests
from requests.adapters import HTTPAdapter
from concurrent.futures import ThreadPoolExecutor, as_completed
from loguru import logger
import threading
from collections import deque

# 导入代理池工具类
from common.utils.proxy_pool import ProxyPool, ProxyBalanceExhausted

# 设置日志级别为INFO，隐藏DEBUG日志
logger.remove()  # 移除默认处理器
logger.add(sys.stderr, level="INFO",
           format="<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>")

from clickhouse_connect import get_client
from clickhouse_connect.driver import Client
from config import config

# ========== 常量配置 ==========

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


HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/91.0.4472.124 Safari/537.36"
    ),
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    "Accept-Encoding": "identity",
    "Connection": "keep-alive",
    "Cache-Control": "no-cache",
    "Referer": "https://quote.eastmoney.com/",
    "Origin": "https://quote.eastmoney.com",
}

# EastMoney K线接口
KLINE_BASE_URL = "https://push2his.eastmoney.com/api/qt/stock/kline/get"

# 字段映射
KLINE_FIELDS = {
    "f51": "日期",
    "f52": "开盘",
    "f53": "收盘",
    "f54": "最高",
    "f55": "最低",
    "f56": "成交量",
    "f57": "成交额",
    "f58": "振幅",
    "f59": "涨跌幅",
    "f60": "涨跌额",
    "f61": "换手率",
}

# 异常代码前缀（跳过这些代码）
ABNORMAL_PREFIXES = ("83", "87", "43", "92", "200", "900")


def sanitize_name(name: str) -> str:
    """清理股票名称"""
    return re.sub(r'[\\/:*?"<>|]', "_", str(name)).strip()


def get_stock_codes() -> List[Dict[str, str]]:
    """获取股票代码列表"""
    client = None
    try:
        client = create_clickhouse_client()

        # 从数据库获取股票代码
        query = "SELECT code, name FROM stock_info WHERE status = '正常' ORDER BY code"
        result = client.query(query).result_rows

        if result:
            stocks = [{'code': row[0], 'name': row[1]} for row in result]
            logger.debug(f"从数据库获取股票代码: {len(stocks)}条")
            return stocks

    except Exception as e:
        logger.error(f"获取股票代码失败: {e}")
        return []
    finally:
        if client:
            client.close()


def is_trading_day(check_date: date) -> bool:
    """判断是否为交易日（简单实现：排除周末）"""
    # 0=Monday, 6=Sunday
    return check_date.weekday() < 5


def get_next_trading_day(start_date: date) -> date:
    """获取下一个交易日"""
    next_day = start_date + timedelta(days=1)
    while not is_trading_day(next_day):
        next_day += timedelta(days=1)
    return next_day


def get_last_trade_date(code: str) -> Optional[date]:
    """获取股票最后交易日期（优化版本）"""
    try:
        # 每个线程创建独立的客户端实例
        client = create_clickhouse_client()

        # 使用更精确的查询，按日期倒序取第一条
        query = """
        SELECT trade_date 
        FROM stock_daily_k_read 
        WHERE code = %(code)s 
        ORDER BY trade_date DESC 
        LIMIT 1
        """
        result = client.query(query, parameters={'code': code}).result_rows

        if result and result[0][0]:
            last_date = result[0][0]
            logger.debug(f"股票 {code} 最后交易日期: {last_date}")
            return last_date
        return None

    except Exception as e:
        logger.error(f"获取最后交易日期失败 {code}: {e}")
        return None
    finally:
        # 确保关闭连接
        if 'client' in locals():
            client.close()


def fetch_stock_data(code: str, name: str, start_date: str = None, end_date: str = None,
                     proxy_pool: ProxyPool = None, max_attempts: int = 3) -> List[Dict]:
    """抓取单只股票的历史数据"""
    try:
        # 正确映射交易所前缀：深市 -> 0., 沪市 -> 1.
        code = str(code).strip().zfill(6)
        sh_prefixes = (
            '600', '601', '603', '605',  # 沪主板
            '688', '689',  # 科创板
        )
        sz_prefixes = (
            '000', '001', '002', '003',  # 深主板
            '300', '301',  # 创业板
        )

        if code.startswith(sz_prefixes):
            secid = f"0.{code}"
        elif code.startswith(sh_prefixes):
            secid = f"1.{code}"
        else:
            # 非常规前缀（如B股/北交所/退市等），直接返回空
            logger.warning(f"代码前缀非常规，跳过: {code}")
            return []

        # 构建请求参数
        params = {
            'secid': secid,

            'fields1': 'f1,f2,f3,f4,f5,f6',
            'fields2': 'f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61',
            'klt': '101',  # 日K线
            'fqt': '1',  # 前复权
            'beg': start_date or '19900101',
            'end': end_date or datetime.now().strftime('%Y%m%d'),
        }

        query_string = "&".join([f"{k}={v}" for k, v in params.items()])

        full_url = f"{KLINE_BASE_URL}?{query_string}"
        logger.debug(f"请求URL: {full_url}")

        # 发送请求（带代理和重试机制）
        session = requests.Session()
        session.headers.update(HEADERS)

        attempts = 0
        while attempts < max_attempts:
            attempts += 1
            try:
                proxies = proxy_pool.get() if proxy_pool else {}
            except ProxyBalanceExhausted as e:
                # 余额用尽，直接上抛
                raise

            try:
                response = session.get(KLINE_BASE_URL, params=params, timeout=5, proxies=proxies)

                if response.status_code != 200:
                    logger.warning(f"HTTP {response.status_code} for {code} (attempt {attempts})")
                    if proxy_pool:
                        proxy_pool.ban_and_rotate()
                    time.sleep(0.5 * attempts)
                    continue

                data = response.json()
                # 请求成功，标记代理使用成功
                if proxy_pool:
                    proxy_pool.mark_success()
                break

            except ProxyBalanceExhausted:
                # 余额用尽，直接上抛
                raise
            except Exception as e:
                logger.warning(f"请求失败 {code} (attempt {attempts}): {e}")
                if proxy_pool:
                    proxy_pool.ban_and_rotate()
                time.sleep(0.5 * attempts)
        else:
            logger.error(f"股票 {code} 请求失败，已重试 {max_attempts} 次")
            return []

        if data.get('data') is None:
            logger.warning(f"股票 {code} 无数据")
            return []

        klines = data['data'].get('klines', [])
        if not klines:
            logger.warning(f"股票 {code} 无K线数据")
            return []

        # 解析数据
        results = []
        for kline in klines:
            try:
                fields = kline.split(',')
                if len(fields) < 11:
                    continue

                # 解析日期
                trade_date_str = fields[0]
                trade_date = datetime.strptime(trade_date_str, '%Y-%m-%d').date()

                # 解析价格数据
                open_price = float(fields[1]) if fields[1] else 0.0
                close_price = float(fields[2]) if fields[2] else 0.0
                high_price = float(fields[3]) if fields[3] else 0.0
                low_price = float(fields[4]) if fields[4] else 0.0
                volume = int(float(fields[5])) if fields[5] else 0
                amount = float(fields[6]) if fields[6] else 0.0
                amplitude = float(fields[7]) if fields[7] else 0.0
                change_pct = float(fields[8]) if fields[8] else 0.0
                change_amount = float(fields[9]) if fields[9] else 0.0
                turnover_rate = float(fields[10]) if fields[10] else 0.0

                result = {
                    'code': code,
                    'trade_date': trade_date,
                    'name': sanitize_name(name),
                    'open_price': round(open_price, 4),
                    'close_price': round(close_price, 4),
                    'high_price': round(high_price, 4),
                    'low_price': round(low_price, 4),
                    'volume': volume,
                    'amount': round(amount, 2),
                    'amplitude': round(amplitude, 4),
                    'change_pct': round(change_pct, 4),
                    'change_amount': round(change_amount, 4),
                    'turnover_rate': round(turnover_rate, 4),
                }

                results.append(result)

            except Exception as e:
                logger.warning(f"解析K线数据失败 {code}: {e}")
                continue

        logger.debug(f"抓取股票 {code} 数据: {len(results)}条")
        return results

    except ProxyBalanceExhausted:
        # 继续上抛给上层统一处理
        raise
    except Exception as e:
        logger.error(f"抓取股票数据失败 {code}: {e}")
        return []


def format_progress_info(current: int, total: int, start_time: float) -> str:
    """格式化进度信息"""
    if total == 0:
        return ""

    # 计算百分比
    percentage = (current / total) * 100

    # 计算已耗时
    elapsed_time = time.time() - start_time
    elapsed_str = format_time(elapsed_time)

    # 计算预估剩余时间
    if current > 0:
        avg_time_per_item = elapsed_time / current
        remaining_items = total - current
        estimated_remaining = avg_time_per_item * remaining_items
        remaining_str = format_time(estimated_remaining)
    else:
        remaining_str = "计算中..."

    return f"({percentage:.1f}%) | 已耗时: {elapsed_str} | 预计剩余: {remaining_str}"


def format_time(seconds: float) -> str:
    """格式化时间显示（HH:MM:SS格式）"""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}"


def format_single_time(seconds: float) -> str:
    """格式化单条耗时显示（秒格式）"""
    return f"{seconds:.2f}s"


def process_stock_batch(stock_batch: List[Dict[str, str]], full: bool = False, proxy_pool: ProxyPool = None,
                        batch_index: int = 0, total_batches: int = 0, start_time: float = 0) -> Tuple[int, int]:
    """处理一批股票数据"""
    success_count = 0
    total_count = 0

    # 为当前线程创建独立的ClickHouse客户端
    client = None
    try:
        client = create_clickhouse_client()

        for stock in stock_batch:
            code = stock['code']
            name = stock['name']

            # 记录单条开始时间
            single_start_time = time.time()

            # 跳过异常代码
            if any(code.startswith(prefix) for prefix in ABNORMAL_PREFIXES):
                continue

            total_count += 1

            try:
                # 根据模式决定抓取范围
                if full:
                    start_date = None  # 全量：下游默认 19900101
                    logger.debug(f"股票 {code} 全量抓取")
                else:
                    # 增量：智能计算开始日期
                    last_date = get_last_trade_date(code)
                    start_date = None

                    if last_date:
                        # 计算下一个交易日
                        next_trading_day = get_next_trading_day(last_date)

                        # 验证是否需要抓取新数据
                        today = date.today()
                        if next_trading_day <= today:
                            start_date = next_trading_day.strftime('%Y%m%d')
                            logger.debug(f"股票 {code} 增量抓取，从 {start_date} 开始")
                        else:
                            single_elapsed = time.time() - single_start_time
                            single_time_str = format_single_time(single_elapsed)
                            progress_info = format_progress_info(batch_index + 1, total_batches, start_time)
                            print(
                                f"⏭️  {code} 跳过 | 数据已是最新 | {single_time_str} | {batch_index + 1}/{total_batches} {progress_info}")
                            continue
                    else:
                        logger.debug(f"股票 {code} 首次抓取（全量）")

                # 抓取数据
                data = fetch_stock_data(code, name, start_date, proxy_pool=proxy_pool)

                if data:
                    # 输出最新价（取最后一条K线的收盘价）
                    latest = data[-1]
                    logger.debug(
                        f"股票 {code} {name} 最新: 日期={latest['trade_date']}, 最新价={latest['close_price']}"
                    )

                    # 批量列式插入到 stock_daily_k_write 表
                    # 准备批量数据（保持 date 对象格式）
                    batch_data = []
                    for row in data:
                        batch_data.append([
                            row['code'],
                            row['trade_date'],  # 保持 date 对象，不转换为字符串
                            row['name'],
                            row['open_price'],
                            row['close_price'],
                            row['high_price'],
                            row['low_price'],
                            row['volume'],
                            row['amount'],
                            row['amplitude'],
                            row['change_pct'],
                            row['change_amount'],
                            row['turnover_rate']
                        ])
                    
                    # 使用 insert 方法进行批量插入
                    client.insert(
                        table='stock_daily_k_write',
                        data=batch_data,
                        column_names=[
                            'code', 'trade_date', 'name', 'open_price', 'close_price', 
                            'high_price', 'low_price', 'volume', 'amount', 'amplitude', 
                            'change_pct', 'change_amount', 'turnover_rate'
                        ]
                    )

                    success_count += 1
                    single_elapsed = time.time() - single_start_time
                    single_time_str = format_single_time(single_elapsed)
                    progress_info = format_progress_info(batch_index + 1, total_batches, start_time)
                    print(
                        f"✅ {code} 入库成功 | {len(data)} records | {single_time_str} | {batch_index + 1}/{total_batches} {progress_info}")
                else:
                    # 无数据（可能是无增量或请求失败），不计为成功，输出跳过提示
                    single_elapsed = time.time() - single_start_time
                    single_time_str = format_single_time(single_elapsed)
                    progress_info = format_progress_info(batch_index + 1, total_batches, start_time)
                    print(
                        f"⏭️  {code} 跳过 | 无新数据或请求失败 | {single_time_str} | {batch_index + 1}/{total_batches} {progress_info}")

            except ProxyBalanceExhausted as e:
                # 余额用尽，上抛让上层停止
                raise
            except Exception as e:
                single_elapsed = time.time() - single_start_time
                single_time_str = format_single_time(single_elapsed)
                progress_info = format_progress_info(batch_index + 1, total_batches, start_time)
                print(
                    f"❌ {code} 处理失败 | {str(e)[:50]}... | {single_time_str} | {batch_index + 1}/{total_batches} {progress_info}")
                continue

    except ProxyBalanceExhausted as e:
        # 往上抛
        raise
    except Exception as e:
        logger.error(f"处理股票批次失败: {e}")
    finally:
        # 确保关闭当前线程的ClickHouse连接
        if client:
            client.close()

    return success_count, total_count


def get_incremental_stats() -> Dict[str, int]:
    """获取增量统计信息"""
    client = None
    try:
        client = create_clickhouse_client()

        # 统计各状态股票数量
        stats = {
            'total_stocks': 0,
            'has_data': 0,
            'no_data': 0,
            'needs_update': 0
        }

        # 获取股票总数
        total_query = "SELECT COUNT(DISTINCT code) FROM stock_info"
        result = client.query(total_query).result_rows
        stats['total_stocks'] = result[0][0] if result else 0

        # 获取有数据的股票数
        has_data_query = "SELECT COUNT(DISTINCT code) FROM stock_daily_k_read"
        result = client.query(has_data_query).result_rows
        stats['has_data'] = result[0][0] if result else 0
        stats['no_data'] = stats['total_stocks'] - stats['has_data']

        # 获取需要更新的股票数（最后交易日期小于今天）
        today = date.today()
        needs_update_query = """
        SELECT COUNT(DISTINCT code) 
        FROM stock_daily_k_read 
        WHERE trade_date < %(today)s
        """
        result = client.query(needs_update_query, parameters={'today': today}).result_rows
        stats['needs_update'] = result[0][0] if result else 0

        return stats

    except Exception as e:
        logger.error(f"获取增量统计失败: {e}")
        return {'total_stocks': 0, 'has_data': 0, 'no_data': 0, 'needs_update': 0}
    finally:
        if client:
            client.close()


def fetch_all_data(full: bool = False, proxy_pool: ProxyPool = None):
    """抓取所有股票数据"""
    try:
        logger.info(f"🚀 开始抓取股票历史数据... 模式={'全量' if full else '增量'}")

        # 显示增量统计信息
        if not full:
            stats = get_incremental_stats()
            logger.debug(f"增量统计: 总股票={stats['total_stocks']}, 有数据={stats['has_data']}, "
                         f"无数据={stats['no_data']}, 需更新={stats['needs_update']}")

        # 获取股票代码列表
        stocks = get_stock_codes()
        if not stocks:
            logger.error("未找到股票代码，退出")
            return False

        logger.info(f"📋 准备抓取 {len(stocks)} 只股票的数据")

        # 创建股票队列
        stock_queue = queue.Queue()
        for stock in stocks:
            stock_queue.put(stock)

        total_success = 0
        total_count = 0
        completed = 0

        # 记录开始时间
        start_time = time.time()

        # 多线程处理：每个线程绑定一个代理，避免冲突
        # 设置合理的线程数量，确保每个线程都有代理可用
        max_workers = min(16, len(stocks))  # 固定使用8个线程，可根据需要调整
        logger.info(f"🚀 启动 {max_workers} 个线程（股票: {len(stocks)}个）")
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # 先提交max_workers个任务（多线程处理）
            futures = []
            for i in range(min(max_workers, len(stocks))):
                if not stock_queue.empty():
                    stock = stock_queue.get()
                    future = executor.submit(process_stock_batch, [stock], full, proxy_pool, i, len(stocks), start_time)
                    futures.append(future)

            # 动态管理任务：完成一个，提交一个
            while futures:
                for future in as_completed(futures):
                    try:
                        success, count = future.result()
                        total_success += success
                        total_count += count
                        completed += 1
                        logger.debug(f"已完成 {completed}/{len(stocks)} 只股票")

                        # 每处理50只股票显示一次代理统计
                        if completed % 50 == 0:
                            proxy_pool.print_stats()
                    except ProxyBalanceExhausted as e:
                        # 余额用尽：立即停止调度并提示
                        logger.error(f"❌ 代理余额已用尽，停止抓取。原因: {e}")
                        # 取消剩余任务
                        for f in futures:
                            f.cancel()
                        futures.clear()
                        raise
                    except Exception as e:
                        logger.error(f"任务处理失败: {e}")

                    # 移除已完成的任务
                    if future in futures:
                        futures.remove(future)

                    # 如果还有待处理的股票，立即提交新任务
                    if not stock_queue.empty():
                        stock = stock_queue.get()
                        new_future = executor.submit(process_stock_batch, [stock], full, proxy_pool, completed,
                                                     len(stocks), start_time)
                        futures.append(new_future)

                    break  # 只处理一个完成的任务，然后重新循环

        logger.info(f"🎉 数据抓取完成！成功: {total_success}/{total_count}")

        # 显示最终代理统计
        if proxy_pool:
            logger.info("=" * 50)
            logger.info("📊 最终代理使用统计:")
            proxy_pool.print_stats()
            logger.info("=" * 50)

        return total_success > 0

    except ProxyBalanceExhausted as e:
        logger.error("⚠️ 检测到代理余额已用尽，已中止所有抓取任务。")
        return False
    except Exception as e:
        logger.error(f"抓取数据失败: {e}")
        return False


if __name__ == "__main__":
    # 配置日志
    logger.add(
        "logs/fetch_daily_data.log",
        rotation="1 day",
        retention="7 days",
        level="INFO",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {name}:{function}:{line} - {message}"
    )
    # 解析命令行参数
    parser = argparse.ArgumentParser(description="Fetch daily stock data to ClickHouse")
    parser.add_argument("--full", action="store_true", help="全量抓取（默认增量）")
    args = parser.parse_args()

    # 初始化代理池（支持多线程，每个线程绑定一个代理，直到失效才轮换）
    proxy_pool = ProxyPool(username="d2086889256", password="8x56dyrr", batch_size=20)
    logger.info(f"🔧 代理池初始化完成（支持多线程，代理失效才轮换，最大化利用率）")

    success = fetch_all_data(full=False, proxy_pool=proxy_pool)
    if success:
        print("✅ 数据抓取完成！")
        sys.exit(0)
    else:
        print("❌ 数据抓取失败！")
        sys.exit(1)
