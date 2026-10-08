"""
今日数据更新脚本 - ClickHouse版本
"""
import os
import sys
import re
import time
import threading
from datetime import datetime, date, timedelta
from typing import List, Dict, Optional
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from collections import defaultdict

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import requests
from loguru import logger

from clickhouse_connect import get_client
from clickhouse_connect.driver import Client
# 移除 bulk_insert 依赖，直接使用 ClickHouse 列式插入
from scripts.compute_indicators import compute_indicators_for_stock
from config import config

# ========== 腾讯接口配置 ==========

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

TENCENT_API_BASE = "https://qt.gtimg.cn/q="

def is_trading_day(check_date: date) -> bool:
    """判断是否为交易日（简单实现：排除周末）"""
    # 0=Monday, 6=Sunday
    return check_date.weekday() < 5

def get_last_trading_day(start_date: date) -> date:
    """获取上一个交易日"""
    prev_day = start_date - timedelta(days=1)
    while not is_trading_day(prev_day):
        prev_day -= timedelta(days=1)
    return prev_day

def normalize_to_tencent_code(code: str) -> tuple[str, str]:
    """转换为腾讯接口代码格式"""
    if code.startswith(('000', '002', '300')):
        return f"sz{code}", "SZ"
    else:
        return f"sh{code}", "SH"

def parse_tencent_line(line: str) -> Optional[Dict[str, str]]:
    """解析腾讯接口返回的一行数据"""
    try:
        # 提取股票代码和名称
        match = re.search(r'v_[a-zA-Z]{2}(\d{6})="([^"]*)"', line)
        if not match:
            return None
        
        code = match.group(1)
        data_str = match.group(2)
        
        # 分割数据
        arr = data_str.split('~')
        if len(arr) < 38:
            return None
        
        # 查找时间戳字段（格式：YYYYMMDDHHMMSS）
        timestamp_str = ''
        for i, field in enumerate(arr):
            if len(field) == 14 and field.isdigit() and field.startswith('202'):
                timestamp_str = field
                break
        
        return {
            'code': code,
            'name': arr[1] if len(arr) > 1 else '',
            'last': arr[3] if len(arr) > 3 else '',
            'prev_close': arr[4] if len(arr) > 4 else '',
            'open': arr[5] if len(arr) > 5 else '',
            'high': arr[33] if len(arr) > 33 else '',
            'low': arr[34] if len(arr) > 34 else '',
            'volume_hand': arr[36] if len(arr) > 36 else '',
            'amount': arr[37] if len(arr) > 37 else '',
            'timestamp': timestamp_str,
        }
    except Exception as e:
        logger.warning(f"解析腾讯数据失败: {e}")
        return None

def fetch_tencent_batch(batch_codes: List[str]) -> Dict[str, Dict[str, str]]:
    """批量获取腾讯数据"""
    if not batch_codes:
        return {}
    
    # 构建腾讯代码列表
    tencent_codes = []
    for code in batch_codes:
        tc, _ = normalize_to_tencent_code(code)
        tencent_codes.append(tc)
    
    # 构建请求URL
    url = f"{TENCENT_API_BASE}{','.join(tencent_codes)}"
    
    try:
        response = requests.get(url, timeout=10)
        if response.status_code != 200:
            logger.warning(f"腾讯接口返回错误: {response.status_code}")
            return {}
        
        # 解析响应
        result = {}
        for line in response.text.splitlines():
            parsed = parse_tencent_line(line)
            if not parsed:
                continue
            
            code = parsed.get('code', '')
            if len(code) == 6:
                result[code] = parsed
        
        return result
        
    except Exception as e:
        logger.error(f"获取腾讯数据失败: {e}")
        return {}

def build_today_row(code: str, parsed: Dict[str, str], fallback_date: date) -> Dict:
    """构建今日数据行"""
    name = parsed.get('name', '') or ''
    
    # 解析接口返回的时间戳
    timestamp_str = parsed.get('timestamp', '')
    trade_date = fallback_date  # 默认使用传入的日期
    
    if timestamp_str and len(timestamp_str) == 14:
        try:
            # 解析时间戳：YYYYMMDDHHMMSS -> date
            trade_date = datetime.strptime(timestamp_str[:8], '%Y%m%d').date()
        except ValueError:
            logger.warning(f"股票 {code} 时间戳格式错误: {timestamp_str}")
    
    # 数值转换
    def to_float(x: str) -> float:
        try:
            return float(x)
        except:
            return 0.0
    
    last = to_float(parsed.get('last', ''))
    prev_close = to_float(parsed.get('prev_close', ''))
    open_px = to_float(parsed.get('open', '')) or (last or prev_close)
    high = to_float(parsed.get('high', '')) or max(open_px, last)
    low = to_float(parsed.get('low', '')) or min(open_px, last)
    vol_hand = to_float(parsed.get('volume_hand', ''))
    amount = to_float(parsed.get('amount', ''))
    
    # 计算衍生指标
    change_amt = last - prev_close if prev_close > 0 else 0.0
    change_pct = (change_amt / prev_close * 100.0) if prev_close > 0 else 0.0
    amplitude = ((high - low) / prev_close * 100.0) if prev_close > 0 else 0.0
    
    return {
        'code': code,
        'trade_date': trade_date,
        'name': name if name else code,
        'open_price': round(open_px, 4),
        'close_price': round(last, 4),
        'high_price': round(high, 4),
        'low_price': round(low, 4),
        'volume': int(vol_hand),
        'amount': round(amount * 10000.0, 2),  # 腾讯返回万元，转换为元
        'amplitude': round(amplitude, 4),
        'change_pct': round(change_pct, 4),
        'change_amount': round(change_amt, 4),
        'turnover_rate': 0.0,  # 腾讯接口不提供换手率
    }

# 线程安全的统计计数器
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

def process_stock_batch(stock_batch: List[Dict], thread_id: int, 
                       success_counter: ThreadSafeCounter,
                       updated_dates: set,
                       dates_lock: threading.Lock) -> int:
    """处理单个股票批次的线程安全函数"""
    batch_success_count = 0
    batch_codes = [stock['code'] for stock in stock_batch]
    
    try:
        logger.info(f"线程 {thread_id} 开始处理 {len(stock_batch)} 只股票")
        
        # 获取腾讯数据
        tencent_data = fetch_tencent_batch(batch_codes)
        
        # 为每个线程创建独立的ClickHouse客户端
        client = create_clickhouse_client()
        
        for stock in stock_batch:
            code = stock['code']
            name = stock['name']
            
            try:
                if code in tencent_data:
                    # 构建今日数据（使用接口返回的实际日期）
                    today_row = build_today_row(code, tencent_data[code], date.today())
                    
                    # 线程安全地更新日期集合
                    with dates_lock:
                        updated_dates.add(today_row['trade_date'])
                    
                    # 使用列式插入日K线数据到 stock_daily_k_write 表
                    kline_data = [[
                        today_row['code'],
                        today_row['trade_date'],  # 保持 date 对象
                        today_row['name'],
                        today_row['open_price'],
                        today_row['close_price'],
                        today_row['high_price'],
                        today_row['low_price'],
                        today_row['volume'],
                        today_row['amount'],
                        today_row['amplitude'],
                        today_row['change_pct'],
                        today_row['change_amount'],
                        today_row['turnover_rate']
                    ]]
                    
                    client.insert(
                        table='stock_daily_k_write',
                        data=kline_data,
                        column_names=[
                            'code', 'trade_date', 'name', 'open_price', 'close_price', 
                            'high_price', 'low_price', 'volume', 'amount', 'amplitude', 
                            'change_pct', 'change_amount', 'turnover_rate'
                        ]
                    )

                    # 明细日志：更新日期与价格，便于核对
                    logger.info(
                        f"[线程{thread_id}] 行情 | {code} {name} | 日期={today_row['trade_date'].strftime('%Y-%m-%d')} "
                        f"O={today_row['open_price']} H={today_row['high_price']} "
                        f"L={today_row['low_price']} C={today_row['close_price']}"
                    )
                    
                    # 统一计算技术指标，仅写入实际数据日期一条
                    indicator_records = compute_indicators_for_stock(client, code, days=180)
                    if indicator_records and len(indicator_records) > 0:
                        actual_date_str = today_row['trade_date'].strftime('%Y-%m-%d')
                        # 查找实际日期记录；若无精确匹配，取最后一条作为近似
                        today_record = None
                        
                        for r in indicator_records[::-1]:
                            trade_date_str = str(r.get('trade_date'))
                            if trade_date_str == actual_date_str:
                                today_record = r
                                break
                        if today_record is None and indicator_records:
                            today_record = indicator_records[-1]
                        
                        if today_record:
                            # 使用列式插入指标数据到 stock_daily_i_write 表
                            indicator_data = [[
                                today_record.get('code'),
                                today_record.get('trade_date'),  # 保持 date 对象
                                today_record.get('wr6'),
                                today_record.get('wr10'),
                                today_record.get('ma5'),
                                today_record.get('ma10'),
                                today_record.get('ma20'),
                                today_record.get('slope_180'),
                                today_record.get('slope_7'),
                                today_record.get('fit_7'),
                                today_record.get('fit_180'),
                                int(today_record.get('best_buy', 0) or 0),
                                int(today_record.get('best_sell', 0) or 0),
                                today_record.get('buy_count_7'),
                                today_record.get('sell_count_7'),
                                today_record.get('buy_count_14'),
                                today_record.get('sell_count_14')
                            ]]
                            
                            client.insert(
                                table='stock_daily_i_write',
                                data=indicator_data,
                                column_names=[
                                    'code', 'trade_date', 'wr6', 'wr10', 'ma5', 'ma10', 'ma20',
                                    'slope_180', 'slope_7', 'fit_7', 'fit_180', 'best_buy', 'best_sell', 'buy_count_7', 
                                    'sell_count_7', 'buy_count_14', 'sell_count_14'
                                ]
                            )

                        # 指标日志不再输出，仅执行写入
                    
                    batch_success_count += 1
                else:
                    logger.warning(f"[线程{thread_id}] 股票 {code} 无今日数据")
                    batch_success_count += 1  # 无数据也算成功
            
            except Exception as e:
                logger.error(f"[线程{thread_id}] 更新股票失败 {code}: {e}")
                continue
        
        # 更新全局成功计数器
        success_counter.increment(batch_success_count)
        logger.info(f"[线程{thread_id}] 完成处理，成功 {batch_success_count}/{len(stock_batch)} 只股票")
        
    except Exception as e:
        logger.error(f"[线程{thread_id}] 批次处理失败: {e}")
    finally:
        if 'client' in locals():
            client.close()
    
    return batch_success_count

def update_today_data():
    """更新今日数据 - 多线程并发版本"""
    start_time = time.time()
    try:
        logger.info("开始更新今日数据（多线程并发模式）...")
        
        # 初始化连接
        client = create_clickhouse_client()
        
        # 获取股票列表
        query = "SELECT code, name FROM stock_info WHERE status = '正常' ORDER BY code"
        result = client.query(query).result_rows
        
        if not result:
            logger.error("未找到股票数据")
            return False
        
        # ClickHouse 返回元组行，按列顺序访问
        stocks = [{'code': row[0], 'name': row[1]} for row in result]
        logger.info(f"准备更新 {len(stocks)} 只股票的数据（将使用接口返回的实际日期）")
        
        # 多线程配置
        max_workers = config.MAX_WORKERS
        batch_size = max(1, len(stocks) // max_workers)  # 每线程处理的股票数量
        
        logger.info(f"使用 {max_workers} 个线程并发处理，每线程约 {batch_size} 只股票")
        
        # 线程安全的统计变量
        success_counter = ThreadSafeCounter()
        updated_dates = set()
        dates_lock = threading.Lock()
        
        # 分批处理
        stock_batches = []
        for i in range(0, len(stocks), batch_size):
            batch = stocks[i:i + batch_size]
            stock_batches.append(batch)
        
        # 使用线程池并发处理
        with ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="StockWorker") as executor:
            # 提交所有任务
            future_to_batch = {}
            for i, batch in enumerate(stock_batches):
                future = executor.submit(
                    process_stock_batch, 
                    batch, 
                    i + 1,  # 线程ID
                    success_counter,
                    updated_dates,
                    dates_lock
                )
                future_to_batch[future] = i + 1
            
            # 等待所有任务完成，设置超时时间
            completed_batches = 0
            total_batches = len(stock_batches)
            timeout_seconds = 300  # 5分钟超时
            
            logger.info(f"开始等待 {total_batches} 个批次完成，超时时间: {timeout_seconds}秒")
            
            try:
                for future in as_completed(future_to_batch, timeout=timeout_seconds):
                    batch_id = future_to_batch[future]
                    try:
                        result = future.result()
                        completed_batches += 1
                        logger.info(f"批次 {batch_id} 完成 ({completed_batches}/{total_batches})")
                    except Exception as e:
                        logger.error(f"批次 {batch_id} 执行失败: {e}")
                        completed_batches += 1  # 即使失败也计入完成数
                        
            except TimeoutError:
                logger.error(f"线程池执行超时 ({timeout_seconds}秒)，已完成 {completed_batches}/{total_batches} 个批次")
                # 取消未完成的任务
                for future in future_to_batch:
                    if not future.done():
                        future.cancel()
                        logger.warning(f"取消未完成的批次 {future_to_batch[future]}")
            
            logger.info(f"线程池执行完成，成功处理 {completed_batches}/{total_batches} 个批次")
        
        # 输出更新结果
        end_time = time.time()
        total_time = end_time - start_time
        success_count = success_counter.get_value()
        
        if success_count > 0:
            if updated_dates:
                dates_str = ', '.join(sorted([d.strftime('%Y-%m-%d') for d in updated_dates]))
                logger.info(f"✅ 数据更新完成！成功更新 {success_count}/{len(stocks)} 只股票的数据")
                logger.info(f"📅 实际更新日期: {dates_str}")
            else:
                logger.info(f"✅ 数据更新完成！成功更新 {success_count}/{len(stocks)} 只股票的数据")
            
            # 性能统计
            avg_time_per_stock = total_time / len(stocks) if len(stocks) > 0 else 0
            stocks_per_second = len(stocks) / total_time if total_time > 0 else 0
            logger.info(f"⏱️ 性能统计: 总耗时 {total_time:.2f}秒, 平均每只股票 {avg_time_per_stock:.3f}秒, 处理速度 {stocks_per_second:.1f}只/秒")
        else:
            logger.warning(f"⚠️ 没有成功更新任何股票数据")
        return success_count > 0
        
    except Exception as e:
        logger.error(f"更新今日数据失败: {e}")
        return False
    finally:
        if 'client' in locals():
            client.close()

if __name__ == "__main__":
    # 配置日志
    logger.add(
        "logs/update_today_data.log",
        rotation="1 day",
        retention="7 days",
        level="INFO",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {name}:{function}:{line} - {message}"
    )
    
    success = update_today_data()
    if success:
        print("✅ 数据更新完成！")
        sys.exit(0)
    else:
        print("❌ 数据更新失败！")
        sys.exit(1)
