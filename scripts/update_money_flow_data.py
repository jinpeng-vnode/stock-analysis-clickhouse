"""
资金流向数据更新脚本 - ClickHouse版本
从东方财富API获取股票资金流向数据并存储到ClickHouse
"""
import os
import sys
import time
import threading
from datetime import datetime, date, timedelta
from typing import List, Dict, Optional, Tuple
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from collections import defaultdict

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import requests
import pandas as pd
from loguru import logger

from clickhouse_connect import get_client
from clickhouse_connect.driver import Client
from config import config

# ========== 东方财富API配置 ==========

EASTMONEY_API_BASE = "https://push2his.eastmoney.com/api/qt/stock/fflow/daykline/get"

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

def get_stock_money_flow_eastmoney(code: str, start_date: str = "20200101", end_date: str = None) -> Optional[pd.DataFrame]:
    """
    使用东方财富API获取个股历史资金流向数据
    start_date: 开始日期，格式 YYYYMMDD
    end_date: 结束日期，格式 YYYYMMDD，默认为今天
    """
    try:
        # 判断市场前缀
        if code.startswith(('600', '601', '603', '605', '688')):
            secid = f"1.{code}"  # 沪市
        else:
            secid = f"0.{code}"  # 深市

        # 设置结束日期
        if end_date is None:
            end_date = datetime.now().strftime('%Y%m%d')

        # 构建请求URL
        url = EASTMONEY_API_BASE
        
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Referer": "https://quote.eastmoney.com/"
        }
        
        # 计算需要获取的数据条数
        start_dt = pd.to_datetime(start_date)
        end_dt = pd.to_datetime(end_date)
        days_count = (end_dt - start_dt).days + 1
        
        params = {
            "lmt": str(days_count),  # 指定获取的数据条数
            "klt": "101",  # 日K线
            "secid": secid,
            "fields1": "f1,f2,f3,f7",
            "fields2": "f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61,f62,f63,f64,f65",
            "ut": "b2884a393a59ad64002292a3e90d46a5",
            "_": int(time.time() * 1000),
        }
        
        response = requests.get(url, params=params, headers=headers, timeout=10)
        data = response.json()
        
        if 'data' not in data or data['data'] is None:
            logger.warning(f"未获取到{code}的资金流向数据")
            return None
            
        klines = data['data']['klines']
        if not klines:
            logger.warning(f"{code}没有资金流向数据")
            return None
            
        # 根据实际数据格式解析
        columns = [
            '日期', '主力净流入-净额', '小单净流入-净额', '中单净流入-净额', '大单净流入-净额', '超大单净流入-净额',
            '主力净流入-净占比', '小单净流入-净占比', '中单净流入-净占比', '大单净流入-净占比', '超大单净流入-净占比',
            '收盘价', '涨跌幅', 'col13', 'col14'
        ]
        
        df = pd.DataFrame([kline.split(',') for kline in klines], columns=columns)
        
        # 转换数据类型
        df['日期'] = pd.to_datetime(df['日期'])
        for col in df.columns:
            if col != '日期':
                df[col] = pd.to_numeric(df[col], errors='coerce')
        
        if len(df) == 0:
            logger.warning(f"{code}没有资金流向数据")
            return None
        
        logger.info(f"获取{code}资金流向数据成功，共{len(df)}条数据")
        return df
        
    except Exception as e:
        logger.error(f"获取{code}资金流向数据失败: {e}")
        return None

def get_existing_dates(client: Client, code: str, start_date: date, end_date: date) -> set:
    """获取已存在的资金流向数据日期"""
    try:
        query = """
        SELECT DISTINCT trade_date 
        FROM stock_money_flow_read 
        WHERE code = %(code)s 
            AND trade_date >= %(start_date)s 
            AND trade_date <= %(end_date)s
        ORDER BY trade_date
        """
        
        result = client.query(
            query, 
            parameters={
                'code': code,
                'start_date': start_date,
                'end_date': end_date
            }
        ).result_rows
        
        existing_dates = {row[0] for row in result}
        logger.debug(f"股票{code}已存在{len(existing_dates)}个日期的资金流向数据")
        return existing_dates
        
    except Exception as e:
        logger.error(f"查询股票{code}已存在日期失败: {e}")
        return set()

def prepare_money_flow_data(df: pd.DataFrame, code: str) -> List[List]:
    """准备资金流向数据用于批量插入"""
    data_list = []
    
    for _, row in df.iterrows():
        try:
            # 确保日期是date对象
            trade_date = row['日期'].date() if hasattr(row['日期'], 'date') else row['日期']
            
            data_list.append([
                code,
                trade_date,
                float(row['收盘价']) if pd.notna(row['收盘价']) else 0.0,
                float(row['涨跌幅']) if pd.notna(row['涨跌幅']) else 0.0,
                float(row['主力净流入-净额']) if pd.notna(row['主力净流入-净额']) else 0.0,
                float(row['主力净流入-净占比']) if pd.notna(row['主力净流入-净占比']) else 0.0,
                float(row['超大单净流入-净额']) if pd.notna(row['超大单净流入-净额']) else 0.0,
                float(row['超大单净流入-净占比']) if pd.notna(row['超大单净流入-净占比']) else 0.0,
                float(row['大单净流入-净额']) if pd.notna(row['大单净流入-净额']) else 0.0,
                float(row['大单净流入-净占比']) if pd.notna(row['大单净流入-净占比']) else 0.0,
                float(row['中单净流入-净额']) if pd.notna(row['中单净流入-净额']) else 0.0,
                float(row['中单净流入-净占比']) if pd.notna(row['中单净流入-净占比']) else 0.0,
                float(row['小单净流入-净额']) if pd.notna(row['小单净流入-净额']) else 0.0,
                float(row['小单净流入-净占比']) if pd.notna(row['小单净流入-净占比']) else 0.0
            ])
        except Exception as e:
            logger.error(f"准备股票{code}数据失败: {e}")
            continue
    
    return data_list

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

def process_stock_money_flow(stock_batch: List[Dict], thread_id: int, 
                           success_counter: ThreadSafeCounter,
                           days_back: int = 30) -> int:
    """处理股票批次的资金流向数据"""
    batch_success_count = 0
    
    try:
        logger.info(f"[线程{thread_id}] 开始处理 {len(stock_batch)} 只股票")
        
        # 为每个线程创建独立的ClickHouse客户端
        client = create_clickhouse_client()
        
        for stock in stock_batch:
            code = stock['code']
            name = stock['name']
            success_count = 0
            
            try:
                logger.info(f"[线程{thread_id}] 开始处理股票 {code} {name}")
                
                # 计算日期范围
                end_date = date.today()
                start_date = end_date - timedelta(days=days_back)
                
                # 获取资金流向数据
                df = get_stock_money_flow_eastmoney(
                    code, 
                    start_date.strftime('%Y%m%d'), 
                    end_date.strftime('%Y%m%d')
                )
                
                if df is None or len(df) == 0:
                    logger.warning(f"[线程{thread_id}] 股票 {code} 没有资金流向数据")
                    continue
                
                # 准备批量插入数据
                data_list = prepare_money_flow_data(df, code)
                
                if not data_list:
                    logger.warning(f"[线程{thread_id}] 股票 {code} 没有有效的数据可插入")
                    continue
                
                # 批量插入数据
                client.insert(
                    table='stock_money_flow_write',
                    data=data_list,
                    column_names=[
                        'code', 'trade_date', 'close_price', 'change_pct',
                        'main_net_inflow_amount', 'main_net_inflow_ratio',
                        'super_large_net_inflow_amount', 'super_large_net_inflow_ratio',
                        'large_net_inflow_amount', 'large_net_inflow_ratio',
                        'medium_net_inflow_amount', 'medium_net_inflow_ratio',
                        'small_net_inflow_amount', 'small_net_inflow_ratio'
                    ]
                )
                
                # 更新统计信息
                success_count = len(data_list)
                success_counter.increment(success_count)
                batch_success_count += success_count
                
                logger.info(f"[线程{thread_id}] 股票 {code} 成功插入 {success_count} 条资金流向数据")
                
                # 输出最新数据预览
                if len(df) > 0:
                    latest_row = df.iloc[-1]
                    logger.info(
                        f"[线程{thread_id}] {code} 最新数据 | 日期={latest_row['日期'].strftime('%Y-%m-%d')} "
                        f"收盘价={latest_row['收盘价']:.2f} 涨跌幅={latest_row['涨跌幅']:.2f}% "
                        f"主力净流入={latest_row['主力净流入-净额']:.0f}万 "
                        f"主力净占比={latest_row['主力净流入-净占比']:.2f}%"
                    )
                
            except Exception as e:
                logger.error(f"[线程{thread_id}] 处理股票 {code} 失败: {e}")
                continue
        
        logger.info(f"[线程{thread_id}] 批次处理完成，成功处理 {batch_success_count} 条数据")
        return batch_success_count
        
    except Exception as e:
        logger.error(f"[线程{thread_id}] 批次处理失败: {e}")
        return 0
    finally:
        if 'client' in locals():
            client.close()

def update_money_flow_data(days_back: int = 30, max_workers: int = None):
    """更新资金流向数据 - 多线程并发版本"""
    start_time = time.time()
    
    if max_workers is None:
        max_workers = config.MAX_WORKERS
    
    try:
        logger.info(f"开始更新资金流向数据（多线程并发模式，回溯{days_back}天）...")
        
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
        logger.info(f"准备更新 {len(stocks)} 只股票的资金流向数据")
        
        # 多线程配置
        batch_size = max(1, len(stocks) // max_workers)  # 每线程处理的股票数量
        
        logger.info(f"使用 {max_workers} 个线程并发处理，每线程约 {batch_size} 只股票")
        
        # 线程安全的统计变量
        success_counter = ThreadSafeCounter()
        
        # 分批处理
        stock_batches = []
        for i in range(0, len(stocks), batch_size):
            batch = stocks[i:i + batch_size]
            stock_batches.append(batch)
        
        # 使用线程池并发处理
        with ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="MoneyFlowWorker") as executor:
            # 提交所有任务
            future_to_batch = {}
            for i, batch in enumerate(stock_batches):
                future = executor.submit(
                    process_stock_money_flow, 
                    batch, 
                    i + 1,  # 线程ID
                    success_counter,
                    days_back
                )
                future_to_batch[future] = i + 1
            
            # 等待所有任务完成，设置超时时间
            completed_batches = 0
            total_batches = len(stock_batches)
            timeout_seconds = 600  # 10分钟超时
            
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
            logger.info(f"✅ 资金流向数据更新完成！成功插入 {success_count} 条数据")
            
            # 性能统计
            avg_time_per_stock = total_time / len(stocks) if len(stocks) > 0 else 0
            stocks_per_second = len(stocks) / total_time if total_time > 0 else 0
            logger.info(f"⏱️ 性能统计: 总耗时 {total_time:.2f}秒, 平均每只股票 {avg_time_per_stock:.3f}秒, 处理速度 {stocks_per_second:.1f}只/秒")
        else:
            logger.warning(f"⚠️ 没有成功插入任何资金流向数据")
        return success_count > 0
        
    except Exception as e:
        logger.error(f"更新资金流向数据失败: {e}")
        return False
    finally:
        if 'client' in locals():
            client.close()

def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='更新股票资金流向数据')
    parser.add_argument('--days', type=int, default=120, help='回溯天数，默认120天')
    parser.add_argument('--workers', type=int, default=None, help=f'线程数，默认使用配置文件值 {config.MAX_WORKERS}')
    parser.add_argument('--test', action='store_true', help='测试模式，只处理前10只股票')
    
    args = parser.parse_args()
    
    # 配置日志
    logger.add(
        "logs/update_money_flow_data.log",
        rotation="1 day",
        retention="7 days",
        level="INFO",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {name}:{function}:{line} - {message}"
    )
    
    if args.test:
        logger.info("🧪 测试模式：只处理前10只股票")
        # 这里可以添加测试逻辑
    
    success = update_money_flow_data(days_back=args.days, max_workers=args.workers)
    
    if success:
        print("✅ 资金流向数据更新完成！")
        sys.exit(0)
    else:
        print("❌ 资金流向数据更新失败！")
        sys.exit(1)

if __name__ == "__main__":
    main()