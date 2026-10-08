"""
技术指标计算脚本 - ClickHouse版本
"""
import os
import sys
import time
import threading
from datetime import datetime, timedelta
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from clickhouse_connect import get_client
from clickhouse_connect.driver import Client
from typing import List, Dict, Optional, Tuple
import pandas as pd
import numpy as np
from loguru import logger
from config import config as app_config
from common.utils.signal_stats import calculate_signal_counts
from common.utils.trend import compute_rolling_slope_and_fit_vectorized
from common.utils.williams_r import (
    compute_williams_r,
    compute_threshold_points_with_near,
)
from common.utils.macd import ema
# 移除 StockIndicatorsInserter，改用直接批量插入


def create_clickhouse_client() -> Client:
    """创建ClickHouse客户端连接"""
    return get_client(
        host=app_config.CLICKHOUSE_HOST,
        port=app_config.CLICKHOUSE_PORT,
        database=app_config.CLICKHOUSE_DB,
        username=app_config.CLICKHOUSE_USER,
        password=app_config.CLICKHOUSE_PASSWORD,
        settings={
            'max_execution_time': app_config.CLICKHOUSE_TIMEOUT,
            'max_memory_usage': '10000000000',  # 10GB
            'max_threads': 8
        }
    )




def compute_indicators_for_stock(client, code: str, days: Optional[int] = None) -> List[Dict[str, object]]:
    # days 为 None 表示计算全历史；否则限制最近 N 天
    if days is None:
        query = """
        SELECT 
            trade_date,
            high_price,
            low_price,
            close_price
        FROM stock_daily_k_read
        WHERE code = %(code)s
        ORDER BY trade_date DESC
        """
        params = {'code': code}
    else:
        query = """
        SELECT 
            trade_date,
            high_price,
            low_price,
            close_price
        FROM stock_daily_k_read
        WHERE code = %(code)s
        ORDER BY trade_date DESC
        LIMIT %(days)s
        """
        params = {'code': code, 'days': days}

    result = client.query(query, parameters=params).result_rows
    if not result:
        return []
    
    # 直接构建DataFrame，减少中间步骤
    df = pd.DataFrame(result, columns=['trade_date', 'high_price', 'low_price', 'close_price'])
    df = df.sort_values('trade_date')
    
    # 直接使用numpy数组进行计算，避免list转换
    dates = df['trade_date'].astype(str).values
    high = df['high_price'].values
    low = df['low_price'].values
    close = df['close_price'].values

    # 将所有计算合并到一个向量化操作中，提升性能
    # 计算180日斜率和拟合值（一次性计算，避免重复）
    if len(close) < 180:
        logger.warning(f"股票 {code} 数据量不足，只有 {len(close)} 天数据，无法计算180天斜率和拟合值")
        slope_180 = [None] * len(close)
        fit_180 = [None] * len(close)
    else:
        slope_180, fit_180 = compute_rolling_slope_and_fit_vectorized(close.tolist(), 180)

    # 计算7日斜率和拟合值
    if len(close) < 7:
        slope_7 = [None] * len(close)
        fit_7 = [None] * len(close)
    else:
        slope_7, fit_7 = compute_rolling_slope_and_fit_vectorized(close.tolist(), 7)

    # 使用 pandas 向量化版本计算 WR
    wr6 = compute_williams_r(high.tolist(), low.tolist(), close.tolist(), 6)
    wr10 = compute_williams_r(high.tolist(), low.tolist(), close.tolist(), 10)

    # 使用EMA计算移动平均线（指数移动平均）
    ma5 = ema(close.tolist(), 5)
    ma10 = ema(close.tolist(), 10)
    ma20 = ema(close.tolist(), 20)

    # 使用外部 helpers：在 WR6 与 WR10 接近的前提下，基于阈值提取买卖点
    near_points = compute_threshold_points_with_near(dates, wr6, wr10, 80.0, 20.0, 1.0)
    buy_points = set((d, v) for d, v in near_points.get("buyPoints", []))
    sell_points = set((d, v) for d, v in near_points.get("sellPoints", []))

    # 向量化计算买卖信号，提升性能
    buy_signals = np.zeros(len(dates), dtype=int)
    sell_signals = np.zeros(len(dates), dtype=int)
    
    # 使用numpy向量化操作替代循环
    for i, (d, val) in enumerate(zip(dates, wr6)):
        if val is not None:
            point_key = (d, float(val))
            if point_key in buy_points:
                buy_signals[i] = 1
            if point_key in sell_points:
                sell_signals[i] = 1
    # 计算买卖点统计（7日与14日窗口）
    buy_count_7, sell_count_7 = calculate_signal_counts(buy_signals, sell_signals, 7)
    buy_count_14, sell_count_14 = calculate_signal_counts(buy_signals, sell_signals, 14)

    # 构建字典列表，每条记录一个字典
    indicator_data = []
    for i in range(len(df)):
        record = {
            'code': code,
            'trade_date': df['trade_date'].iloc[i],
            'wr6': wr6[i],
            'wr10': wr10[i],
            'ma5': ma5[i],
            'ma10': ma10[i],
            'ma20': ma20[i],
            'slope_180': slope_180[i],
            'slope_7': slope_7[i],
            'fit_7': fit_7[i],
            'fit_180': fit_180[i],
            'best_buy': buy_signals[i],
            'best_sell': sell_signals[i],
            'buy_count_7': buy_count_7[i],
            'sell_count_7': sell_count_7[i],
            'buy_count_14': buy_count_14[i],
            'sell_count_14': sell_count_14[i],
        }
        indicator_data.append(record)

    return indicator_data


class ThreadSafeCounter:
    """线程安全的计数器"""
    def __init__(self):
        self._value = 0
        self._lock = threading.Lock()
    
    def increment(self, amount=1):
        with self._lock:
            self._value += amount
    
    def get_value(self):
        with self._lock:
            return self._value


def process_stock_batch(codes: List[str], thread_id: int, 
                       success_counter: ThreadSafeCounter, 
                       processed_counter: ThreadSafeCounter,
                       total_codes: int) -> int:
    """处理一批股票的技术指标计算（线程安全）"""
    # 每个线程使用独立的客户端连接和插入器
    client = create_clickhouse_client()
    batch_success_count = 0
    
    try:
        logger.info(f"线程 {thread_id} 开始处理 {len(codes)} 只股票")
        
        # 使用批量插入到 stock_daily_i_write 表
        batch_data = []  # 收集所有数据，最后批量插入
        batch_size_limit = 10000  # 每批最多插入10000条记录
        
        for code in codes:
            try:
                # 计算单只股票的技术指标
                per_stock_data = compute_indicators_for_stock(client, code)
                
                if per_stock_data and len(per_stock_data) > 0:
                    # 准备批量数据
                    for record in per_stock_data:
                        batch_data.append([
                            record['code'],
                            record['trade_date'],  # 保持 date 对象
                            record['wr6'],
                            record['wr10'],
                            record['ma5'],
                            record['ma10'],
                            record['ma20'],
                            record['slope_180'],
                            record['slope_7'],
                            record['fit_7'],
                            record['fit_180'],
                            int(record['best_buy'] or 0),
                            int(record['best_sell'] or 0),
                            record['buy_count_7'],
                            record['sell_count_7'],
                            record['buy_count_14'],
                            record['sell_count_14']
                        ])
                    
                    records_count = len(per_stock_data)
                    success_counter.increment(records_count)
                    processed_counter.increment(1)
                    batch_success_count += 1
                    
                    current_processed = processed_counter.get_value()
                    logger.info(f"股票 {code} 计算完成 | 记录数: {records_count} | "
                               f"进度: {current_processed}/{total_codes}")
                    
                    # 当批量数据达到限制时，执行插入
                    if len(batch_data) >= batch_size_limit:
                        try:
                            client.insert(
                                table='stock_daily_i_write',
                                data=batch_data,
                                column_names=[
                                    'code', 'trade_date', 'wr6', 'wr10', 'ma5', 'ma10', 'ma20',
                                    'slope_180', 'slope_7', 'fit_7', 'fit_180', 'best_buy', 'best_sell', 'buy_count_7', 'sell_count_7',
                                    'buy_count_14', 'sell_count_14'
                                ]
                            )
                            logger.debug(f"线程 {thread_id} 批量插入 {len(batch_data)} 条记录")
                            batch_data = []  # 清空批量数据
                        except Exception as e:
                            logger.error(f"线程 {thread_id} 批量插入失败: {e}")
                            batch_data = []  # 清空批量数据，继续处理
                else:
                    processed_counter.increment(1)
                    batch_success_count += 1
                    current_processed = processed_counter.get_value()
                    logger.warning(f"股票 {code} 无有效数据 | 进度: {current_processed}/{total_codes}")
                    
            except Exception as e:
                processed_counter.increment(1)
                batch_success_count += 1
                current_processed = processed_counter.get_value()
                logger.error(f"计算股票 {code} 失败: {e} | 进度: {current_processed}/{total_codes}")
                continue
        
        # 插入剩余的批量数据
        if batch_data:
            try:
                client.insert(
                    table='stock_daily_i_write',
                    data=batch_data,
                    column_names=[
                        'code', 'trade_date', 'wr6', 'wr10', 'ma5', 'ma10', 'ma20',
                        'slope_180', 'slope_7', 'fit_7', 'fit_180', 'best_buy', 'best_sell', 'buy_count_7', 'sell_count_7',
                        'buy_count_14', 'sell_count_14'
                    ]
                )
                logger.info(f"线程 {thread_id} 完成处理，成功 {batch_success_count}/{len(codes)} 只股票，最后插入 {len(batch_data)} 条记录")
            except Exception as e:
                logger.error(f"线程 {thread_id} 最后批量插入失败: {e}")
                logger.info(f"线程 {thread_id} 完成处理，成功 {batch_success_count}/{len(codes)} 只股票")
            
    except Exception as e:
        logger.error(f"线程 {thread_id} 批次处理失败: {e}")
    finally:
        # 确保关闭客户端连接
        if 'client' in locals():
            client.close()
    
    return batch_success_count










def main():
    """主函数 - 计算所有股票的技术指标"""
    # 配置日志
    logger.add(
        "logs/compute_indicators.log",
        rotation="1 day",
        retention="7 days",
        level="INFO",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {name}:{function}:{line} - {message}"
    )

    try:
        logger.info("开始计算技术指标...")

        # 初始化连接
        client = create_clickhouse_client()

        # 获取需要计算指标的股票代码
        query = """
        SELECT DISTINCT code
        FROM stock_daily_k_read
        ORDER BY code
        """

        result = client.query(query).result_rows
        codes = [row[0] for row in result]

        if not codes:
            logger.warning("未找到股票数据")
            print("❌ 技术指标计算失败！")
            sys.exit(1)

        logger.info(f"准备计算 {len(codes)} 只股票的技术指标")

        # 使用多线程并行计算（批量处理模式）
        max_workers = 24  # 增加到32个线程，进一步提升计算速度
        batch_size = max(1, len(codes) // max_workers)  # 每线程处理的股票数量
        total_codes = len(codes)
        start_time = time.time()
        
        logger.info(f"使用 {max_workers} 个线程并发处理，每线程约 {batch_size} 只股票")
        
        # 创建线程安全的计数器
        success_counter = ThreadSafeCounter()
        processed_counter = ThreadSafeCounter()
        
        # 分批处理
        stock_batches = []
        for i in range(0, len(codes), batch_size):
            batch = codes[i:i + batch_size]
            stock_batches.append(batch)
        
        logger.info(f"启动 {max_workers} 个线程进行并行计算...")
        
        # 使用线程池并行处理
        with ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="StockWorker") as executor:
            # 提交所有任务
            future_to_batch = {}
            for i, batch in enumerate(stock_batches):
                future = executor.submit(
                    process_stock_batch,
                    batch,
                    i + 1,  # 线程ID
                    success_counter,
                    processed_counter,
                    total_codes
                )
                future_to_batch[future] = i + 1
            
            # 等待所有任务完成
            completed_batches = 0
            total_batches = len(stock_batches)
            
            for future in future_to_batch:
                try:
                    result = future.result()
                    completed_batches += 1
                    batch_id = future_to_batch[future]
                    logger.info(f"批次 {batch_id} 完成 ({completed_batches}/{total_batches})")
                    
                    # 每完成10个批次输出一次进度
                    if completed_batches % 10 == 0:
                        elapsed_time = time.time() - start_time
                        avg_time_per_batch = elapsed_time / completed_batches
                        remaining_batches = total_batches - completed_batches
                        estimated_remaining_time = avg_time_per_batch * remaining_batches
                        
                        logger.info(f"进度更新: {completed_batches}/{total_batches} 批次 | "
                                  f"已用时间: {elapsed_time/60:.1f}分钟 | "
                                  f"剩余预估: {estimated_remaining_time/60:.1f}分钟")
                        
                except Exception as e:
                    batch_id = future_to_batch[future]
                    logger.error(f"批次 {batch_id} 执行失败: {e}")
        
        total_processed = success_counter.get_value()
        successful_codes = processed_counter.get_value()

        total_elapsed_time = time.time() - start_time
        avg_time_per_stock = total_elapsed_time / len(codes) if len(codes) > 0 else 0
        
        logger.info(f"技术指标计算完成！成功处理股票数: {successful_codes}/{len(codes)}, "
                   f"总记录数: {total_processed}, 总耗时: {total_elapsed_time/60:.1f}分钟, "
                   f"平均每股耗时: {avg_time_per_stock:.2f}秒")
        print(f"✅ 技术指标计算完成！总耗时: {total_elapsed_time/60:.1f}分钟")
        sys.exit(0)

    except Exception as e:
        logger.error(f"计算技术指标失败: {e}")
        print("❌ 技术指标计算失败！")
        sys.exit(1)
    finally:
        if 'client' in locals():
            client.close()


if __name__ == "__main__":
    main()
