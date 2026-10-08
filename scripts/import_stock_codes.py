"""
股票代码导入脚本
"""
import os
import sys
import csv
from pathlib import Path
from typing import List, Dict, Set

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from clickhouse_connect import get_client
from clickhouse_connect.driver import Client
from loguru import logger
from config import config

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

def load_failed_codes_from_csv(csv_file: str) -> Set[str]:
    """从失败记录CSV文件加载失败的股票代码"""
    failed_codes = set()
    
    try:
        with open(csv_file, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            for row in reader:
                code = row.get('代码', '').strip()
                if code and len(code) == 6 and code.isdigit():
                    failed_codes.add(code)
        
        logger.info(f"从失败记录文件加载失败代码: {len(failed_codes)}条")
        return failed_codes
        
    except Exception as e:
        logger.error(f"加载失败记录文件失败: {e}")
        return set()

def load_stock_codes_from_csv(csv_file: str) -> List[Dict[str, str]]:
    """从CSV文件加载股票代码"""
    stocks = []
    
    try:
        # 使用 utf-8-sig 编码处理BOM
        with open(csv_file, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            for row in reader:
                # 兼容带BOM的列名
                code = row.get('code') or row.get('\ufeffcode', '')
                name = row.get('name', '')
                market = row.get('market', '')
                
                stock = {
                    'code': code.strip(),
                    'name': name.strip(),
                    'market': market.strip()
                }
                
                # 验证数据
                if stock['code'] and len(stock['code']) == 6 and stock['code'].isdigit():
                    stocks.append(stock)
                else:
                    logger.warning(f"跳过无效股票代码: {row}")
        
        logger.info(f"从CSV文件加载股票代码: {len(stocks)}条")
        return stocks
        
    except Exception as e:
        logger.error(f"加载CSV文件失败: {e}")
        return []

def filter_successful_codes(stocks: List[Dict[str, str]], failed_codes: Set[str]) -> List[Dict[str, str]]:
    """过滤掉失败的股票代码，只保留成功的"""
    successful_stocks = []
    
    for stock in stocks:
        if stock['code'] not in failed_codes:
            successful_stocks.append(stock)
        else:
            logger.debug(f"跳过失败股票代码: {stock['code']} - {stock['name']}")
    
    logger.info(f"过滤后成功股票代码: {len(successful_stocks)}条 (原{len(stocks)}条，排除{len(stocks) - len(successful_stocks)}条)")
    return successful_stocks

def create_default_stock_codes() -> List[Dict[str, str]]:
    """创建默认股票代码列表（如果CSV文件不存在）"""
    # 一些常见的股票代码示例
    default_stocks = [
        {'code': '000001', 'name': '平安银行', 'market': 'SZ'},
        {'code': '000002', 'name': '万科A', 'market': 'SZ'},
        {'code': '000858', 'name': '五粮液', 'market': 'SZ'},
        {'code': '000876', 'name': '新希望', 'market': 'SZ'},
        {'code': '002415', 'name': '海康威视', 'market': 'SZ'},
        {'code': '300059', 'name': '东方财富', 'market': 'SZ'},
        {'code': '600000', 'name': '浦发银行', 'market': 'SH'},
        {'code': '600036', 'name': '招商银行', 'market': 'SH'},
        {'code': '600519', 'name': '贵州茅台', 'market': 'SH'},
        {'code': '600887', 'name': '伊利股份', 'market': 'SH'},
    ]
    
    logger.info(f"使用默认股票代码: {len(default_stocks)}条")
    return default_stocks

def import_stock_codes():
    """导入股票代码到ClickHouse"""
    try:
        logger.info("开始导入股票代码...")
        
        # 初始化连接
        client = create_clickhouse_client()
        
        # 获取脚本所在目录
        script_dir = Path(__file__).parent
        
        # 加载失败记录
        failed_codes_file = script_dir / "日k线示抓取失败.csv"
        failed_codes = set()
        if failed_codes_file.exists():
            failed_codes = load_failed_codes_from_csv(str(failed_codes_file))
        else:
            logger.warning("未找到失败记录文件，将导入所有股票代码")
        
        # 加载股票代码列表
        csv_file = script_dir / "股票代码列表.csv"
        if csv_file.exists():
            stocks = load_stock_codes_from_csv(str(csv_file))
            # stocks = create_default_stock_codes()
        else:
            logger.error("未找到股票代码列表文件")
            return False
        
        if not stocks:
            logger.error("没有找到有效的股票代码数据")
            return False
        
        # 过滤掉失败的股票代码
        successful_stocks = filter_successful_codes(stocks, failed_codes)
        
        if not successful_stocks:
            logger.error("过滤后没有有效的股票代码数据")
            return False
        
        # 使用批量列式插入
        logger.info(f"准备插入 {len(successful_stocks)} 条成功股票代码...")
        
        # 准备批量数据
        batch_data = []
        for stock in successful_stocks:
            batch_data.append([
                stock['code'],
                stock['name'],
                stock['market'],
                '正常'  # status
            ])
        
        # 使用 insert 方法进行批量插入
        client.insert(
            table='stock_info',
            data=batch_data,
            column_names=['code', 'name', 'market', 'status']
        )
        
        # 验证插入结果
        result = client.query("SELECT COUNT(*) as total FROM stock_info").result_rows
        total_count = result[0][0] if result else 0
        
        logger.info(f"股票代码导入完成！总数量: {total_count}")
        return True
        
    except Exception as e:
        logger.error(f"导入股票代码失败: {e}")
        return False
    finally:
        if 'client' in locals():
            client.close()

if __name__ == "__main__":
 
    success = import_stock_codes()
    if success:
        print("✅ 股票代码导入成功！")
        sys.exit(0)
    else:
        print("❌ 股票代码导入失败！")
        sys.exit(1)
