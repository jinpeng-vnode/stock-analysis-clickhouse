"""
财务报告抓取脚本 - 从雪球API获取现金流量表和财务指标数据
数据插入ClickHouse数据库
使用 playwright 发送请求，支持 cookies
"""
import time
import json
import sys
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from datetime import datetime, date

from playwright.sync_api import sync_playwright, Page, BrowserContext
from loguru import logger

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from clickhouse_connect import get_client
from clickhouse_connect.driver import Client
from config import config

# 配置日志
logger.remove()
logger.add(sys.stderr, level="INFO",
           format="<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>")


def convert_symbol(code: str, market: str = '') -> str:
    """
    转换股票代码为雪球API格式
    
    Args:
        code: 股票代码，如 '000001' 或 '601127'
        market: 市场类型，如 'SH' 或 'SZ'，如果为空则根据代码自动判断
    
    Returns:
        雪球格式代码，如 'SH000001' 或 'SZ000001'
    """
    if not market:
        # 根据代码判断市场
        if code.startswith('6'):
            market = 'SH'
        elif code.startswith('0') or code.startswith('3'):
            market = 'SZ'
        else:
            market = 'SH'  # 默认上海
    
    return f"{market}{code}"


def timestamp_to_date(timestamp: Optional[int]) -> Optional[date]:
    """
    将时间戳转换为日期对象
    
    Args:
        timestamp: 毫秒时间戳
    
    Returns:
        日期对象 (date) 或 None
    """
    if not timestamp:
        return None
    
    try:
        dt = datetime.fromtimestamp(timestamp / 1000)
        return dt.date()
    except Exception as e:
        logger.warning(f"时间戳转换失败: {timestamp}, 错误: {e}")
        return None


def timestamp_to_datetime(timestamp: Optional[int]) -> Optional[datetime]:
    """
    将时间戳转换为日期时间对象
    
    Args:
        timestamp: 毫秒时间戳
    
    Returns:
        日期时间对象 (datetime) 或 None
    """
    if not timestamp:
        return None
    
    try:
        dt = datetime.fromtimestamp(timestamp / 1000)
        return dt
    except Exception as e:
        logger.warning(f"时间戳转换失败: {timestamp}, 错误: {e}")
        return None


def extract_value(data) -> Optional[float]:
    """
    从数组格式 [值, 增长率] 中提取第一个值
    
    Args:
        data: 可能是数组 [值, 增长率] 或单个值或 None
    
    Returns:
        提取的数值或 None
    """
    if data is None:
        return None
    
    if isinstance(data, list) and len(data) > 0:
        return data[0] if data[0] is not None else None
    
    if isinstance(data, (int, float)):
        return float(data)
    
    return None


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


def get_stock_codes_from_db(client: Client) -> List[Dict[str, str]]:
    """
    从数据库获取股票代码列表
    
    Args:
        client: ClickHouse客户端
    
    Returns:
        股票代码列表，格式: [{'code': '000001', 'market': 'SZ'}, ...]
    """
    try:
        # 从数据库获取股票代码，只获取状态为正常的股票
        query = "SELECT code, market FROM stock_info WHERE status = '正常' ORDER BY code"
        result = client.query(query).result_rows
        
        if result:
            stocks = [{'code': row[0], 'market': row[1] or ''} for row in result]
            logger.info(f"从数据库获取股票代码: {len(stocks)}条")
            return stocks
        else:
            logger.warning("数据库中没有找到股票代码")
            return []
            
    except Exception as e:
        logger.error(f"获取股票代码失败: {e}")
        return []


def get_existing_financial_reports(client: Client) -> set:
    """
    批量查询所有已存在的财务报告（code + report_date组合）
    
    Args:
        client: ClickHouse客户端
    
    Returns:
        已有财务报告的 (code, report_date) 元组集合
    """
    try:
        # 一次性查询所有已存在的财务报告
        # 使用FINAL关键字确保获取最新版本的数据（ReplacingMergeTree引擎）
        query = """
            SELECT code, report_date 
            FROM stock_financial_report FINAL
        """
        result = client.query(query).result_rows
        
        if result:
            existing = {(row[0], row[1]) for row in result}
            logger.info(f"已存在财务报告的记录数量: {len(existing)}")
            return existing
        else:
            logger.info("没有找到已有财务报告")
            return set()
            
    except Exception as e:
        logger.warning(f"批量查询已有财务报告失败: {e}")
        # 如果查询失败，返回空集合，继续执行抓取流程
        return set()


def fetch_cash_flow_data(page: Page, symbol: str) -> Optional[Dict]:
    """
    从雪球API获取现金流量表数据（使用浏览器访问）
    
    Args:
        page: Playwright Page 对象
        symbol: 雪球格式的股票代码，如 'SH601127'
    
    Returns:
        API返回的数据字典或None
    """
    url = f"https://stock.xueqiu.com/v5/stock/finance/cn/cash_flow.json?symbol={symbol}&type=all&is_detail=true&count=99999&timestamp="
    
    try:
        # 导航到 URL
        response = page.goto(url, wait_until="networkidle", timeout=30000)
        
        # 检查响应状态
        if not response or response.status != 200:
            logger.warning(f"API返回错误状态码: {symbol}, 状态码: {response.status if response else 'None'}")
            return None
        
        # 获取页面内容（JSON数据）
        content = page.content()
        
        # 解析JSON响应
        try:
            data = json.loads(content)
        except json.JSONDecodeError:
            # 如果不是纯JSON，尝试从 <pre> 标签或 body 中提取
            json_text = page.evaluate("document.body.textContent")
            data = json.loads(json_text)
        
        if data.get('error_code') != 0:
            logger.warning(f"API返回错误: {symbol}, 错误码: {data.get('error_code')}, 描述: {data.get('error_description')}")
            return None
        
        return data.get('data')
        
    except Exception as e:
        logger.error(f"获取现金流量数据失败: {symbol}, 错误: {e}")
        return None


def fetch_indicator_data(page: Page, symbol: str) -> Optional[Dict]:
    """
    从雪球API获取财务指标数据（使用浏览器访问）
    
    Args:
        page: Playwright Page 对象
        symbol: 雪球格式的股票代码，如 'SH601127'
    
    Returns:
        API返回的数据字典或None
    """
    url = f"https://stock.xueqiu.com/v5/stock/finance/cn/indicator.json?symbol={symbol}&type=all&is_detail=true&count=99999&timestamp="
    
    try:
        # 导航到 URL
        response = page.goto(url, wait_until="networkidle", timeout=30000)
        
        # 检查响应状态
        if not response or response.status != 200:
            logger.warning(f"API返回错误状态码: {symbol}, 状态码: {response.status if response else 'None'}")
            return None
        
        # 获取页面内容（JSON数据）
        content = page.content()
        
        # 解析JSON响应
        try:
            data = json.loads(content)
        except json.JSONDecodeError:
            # 如果不是纯JSON，尝试从 <pre> 标签或 body 中提取
            json_text = page.evaluate("document.body.textContent")
            data = json.loads(json_text)
        
        if data.get('error_code') != 0:
            logger.warning(f"API返回错误: {symbol}, 错误码: {data.get('error_code')}, 描述: {data.get('error_description')}")
            return None
        
        return data.get('data')
        
    except Exception as e:
        logger.error(f"获取财务指标数据失败: {symbol}, 错误: {e}")
        return None


def parse_financial_data(
    cash_flow_item: Dict, 
    indicator_item: Optional[Dict],
    code: str, 
    market: str,
    quote_name: str,
    currency: str,
    currency_name: str,
    org_type: int
) -> Dict:
    """
    解析单个报告期的财务数据并格式化（合并现金流量表和财务指标数据）
    
    Args:
        cash_flow_item: 现金流量表API返回的单个报告期数据
        indicator_item: 财务指标API返回的单个报告期数据（可选）
        code: 股票代码
        market: 市场类型
        quote_name: 股票名称
        currency: 货币代码
        currency_name: 货币名称
        org_type: 组织类型
    
    Returns:
        格式化后的财务报告记录字典
    """
    # 使用现金流量表数据的报告日期和名称（优先使用indicator的数据，如果没有则用cash_flow的）
    report_date = timestamp_to_date(indicator_item.get('report_date') if indicator_item else None) or timestamp_to_date(cash_flow_item.get('report_date'))
    report_name = indicator_item.get('report_name') if indicator_item else cash_flow_item.get('report_name')
    
    # 构建记录
    record = {
        'code': code,
        'quote_name': quote_name,
        'report_date': report_date,
        'report_name': report_name,
        'currency': currency,
        'currency_name': currency_name,
        'org_type': org_type,
        
        # 经营活动产生的现金流量 (Operating Activities)
        'oa_ncf': extract_value(cash_flow_item.get('ncf_from_oa')),
        'oa_cash_received_of_sales_service': extract_value(cash_flow_item.get('cash_received_of_sales_service')),
        'oa_refund_of_tax_and_levies': extract_value(cash_flow_item.get('refund_of_tax_and_levies')),
        'oa_cash_received_of_othr': extract_value(cash_flow_item.get('cash_received_of_othr_oa')),
        'oa_sub_total_ci': extract_value(cash_flow_item.get('sub_total_of_ci_from_oa')),
        'oa_goods_buy_and_service_cash_pay': extract_value(cash_flow_item.get('goods_buy_and_service_cash_pay')),
        'oa_cash_paid_to_employee_etc': extract_value(cash_flow_item.get('cash_paid_to_employee_etc')),
        'oa_payments_of_all_taxes': extract_value(cash_flow_item.get('payments_of_all_taxes')),
        'oa_othrcash_paid_relating_to': extract_value(cash_flow_item.get('othrcash_paid_relating_to_oa')),
        'oa_sub_total_cos': extract_value(cash_flow_item.get('sub_total_of_cos_from_oa')),
        
        # 投资活动产生的现金流量 (Investing Activities)
        'ia_ncf': extract_value(cash_flow_item.get('ncf_from_ia')),
        'ia_cash_received_of_dspsl_invest': extract_value(cash_flow_item.get('cash_received_of_dspsl_invest')),
        'ia_invest_income_cash_received': extract_value(cash_flow_item.get('invest_income_cash_received')),
        'ia_net_cash_of_disposal_assets': extract_value(cash_flow_item.get('net_cash_of_disposal_assets')),
        'ia_net_cash_of_disposal_branch': extract_value(cash_flow_item.get('net_cash_of_disposal_branch')),
        'ia_cash_received_of_othr': extract_value(cash_flow_item.get('cash_received_of_othr_ia')),
        'ia_sub_total_ci': extract_value(cash_flow_item.get('sub_total_of_ci_from_ia')),
        'ia_invest_paid_cash': extract_value(cash_flow_item.get('invest_paid_cash')),
        'ia_cash_paid_for_assets': extract_value(cash_flow_item.get('cash_paid_for_assets')),
        'ia_othrcash_paid_relating_to': extract_value(cash_flow_item.get('othrcash_paid_relating_to_ia')),
        'ia_sub_total_cos': extract_value(cash_flow_item.get('sub_total_of_cos_from_ia')),
        
        # 筹资活动产生的现金流量 (Financing Activities)
        'fa_ncf': extract_value(cash_flow_item.get('ncf_from_fa')),
        'fa_cash_received_of_absorb_invest': extract_value(cash_flow_item.get('cash_received_of_absorb_invest')),
        'fa_cash_received_from_investor': extract_value(cash_flow_item.get('cash_received_from_investor')),
        'fa_cash_received_from_bond_issue': extract_value(cash_flow_item.get('cash_received_from_bond_issue')),
        'fa_cash_received_of_borrowing': extract_value(cash_flow_item.get('cash_received_of_borrowing')),
        'fa_cash_received_of_othr': extract_value(cash_flow_item.get('cash_received_of_othr_fa')),
        'fa_sub_total_ci': extract_value(cash_flow_item.get('sub_total_of_ci_from_fa')),
        'fa_cash_pay_for_debt': extract_value(cash_flow_item.get('cash_pay_for_debt')),
        'fa_cash_paid_of_distribution': extract_value(cash_flow_item.get('cash_paid_of_distribution')),
        'fa_branch_paid_to_minority_holder': extract_value(cash_flow_item.get('branch_paid_to_minority_holder')),
        'fa_othrcash_paid_relating_to': extract_value(cash_flow_item.get('othrcash_paid_relating_to_fa')),
        'fa_sub_total_cos': extract_value(cash_flow_item.get('sub_total_of_cos_from_fa')),
        
        # 现金及现金等价物 (Cash and Cash Equivalents)
        'cce_effect_of_exchange_chg': extract_value(cash_flow_item.get('effect_of_exchange_chg_on_cce')),
        'cce_net_increase': extract_value(cash_flow_item.get('net_increase_in_cce')),
        'cce_initial_balance': extract_value(cash_flow_item.get('initial_balance_of_cce')),
        'cce_final_balance': extract_value(cash_flow_item.get('final_balance_of_cce')),
        
        # 其他
        'net_cash_amt_from_branch': extract_value(cash_flow_item.get('net_cash_amt_from_branch')),
        
        # 财务指标数据 (Financial Indicators) - 从indicator_item中提取
        'avg_roe': extract_value(indicator_item.get('avg_roe') if indicator_item else None),
        'np_per_share': extract_value(indicator_item.get('np_per_share') if indicator_item else None),
        'operate_cash_flow_ps': extract_value(indicator_item.get('operate_cash_flow_ps') if indicator_item else None),
        'basic_eps': extract_value(indicator_item.get('basic_eps') if indicator_item else None),
        'capital_reserve': extract_value(indicator_item.get('capital_reserve') if indicator_item else None),
        'undistri_profit_ps': extract_value(indicator_item.get('undistri_profit_ps') if indicator_item else None),
        'net_interest_of_total_assets': extract_value(indicator_item.get('net_interest_of_total_assets') if indicator_item else None),
        'net_selling_rate': extract_value(indicator_item.get('net_selling_rate') if indicator_item else None),
        'gross_selling_rate': extract_value(indicator_item.get('gross_selling_rate') if indicator_item else None),
        'total_revenue': extract_value(indicator_item.get('total_revenue') if indicator_item else None),
        'operating_income_yoy': extract_value(indicator_item.get('operating_income_yoy') if indicator_item else None),
        'net_profit_atsopc': extract_value(indicator_item.get('net_profit_atsopc') if indicator_item else None),
        'net_profit_atsopc_yoy': extract_value(indicator_item.get('net_profit_atsopc_yoy') if indicator_item else None),
        'net_profit_after_nrgal_atsolc': extract_value(indicator_item.get('net_profit_after_nrgal_atsolc') if indicator_item else None),
        'np_atsopc_nrgal_yoy': extract_value(indicator_item.get('np_atsopc_nrgal_yoy') if indicator_item else None),
        'ore_dlt': extract_value(indicator_item.get('ore_dlt') if indicator_item else None),
        'rop': extract_value(indicator_item.get('rop') if indicator_item else None),
        'asset_liab_ratio': extract_value(indicator_item.get('asset_liab_ratio') if indicator_item else None),
        'current_ratio': extract_value(indicator_item.get('current_ratio') if indicator_item else None),
        'quick_ratio': extract_value(indicator_item.get('quick_ratio') if indicator_item else None),
        'equity_multiplier': extract_value(indicator_item.get('equity_multiplier') if indicator_item else None),
        'equity_ratio': extract_value(indicator_item.get('equity_ratio') if indicator_item else None),
        'holder_equity': extract_value(indicator_item.get('holder_equity') if indicator_item else None),
        'ncf_from_oa_to_total_liab': extract_value(indicator_item.get('ncf_from_oa_to_total_liab') if indicator_item else None),
        'inventory_turnover_days': extract_value(indicator_item.get('inventory_turnover_days') if indicator_item else None),
        'receivable_turnover_days': extract_value(indicator_item.get('receivable_turnover_days') if indicator_item else None),
        'accounts_payable_turnover_days': extract_value(indicator_item.get('accounts_payable_turnover_days') if indicator_item else None),
        'cash_cycle': extract_value(indicator_item.get('cash_cycle') if indicator_item else None),
        'operating_cycle': extract_value(indicator_item.get('operating_cycle') if indicator_item else None),
        'total_capital_turnover': extract_value(indicator_item.get('total_capital_turnover') if indicator_item else None),
        'inventory_turnover': extract_value(indicator_item.get('inventory_turnover') if indicator_item else None),
        'account_receivable_turnover': extract_value(indicator_item.get('account_receivable_turnover') if indicator_item else None),
        'accounts_payable_turnover': extract_value(indicator_item.get('accounts_payable_turnover') if indicator_item else None),
        'current_asset_turnover_rate': extract_value(indicator_item.get('current_asset_turnover_rate') if indicator_item else None),
        'fixed_asset_turnover_ratio': extract_value(indicator_item.get('fixed_asset_turnover_ratio') if indicator_item else None)
    }
    
    return record


def format_single_time(seconds: float) -> str:
    """格式化单条耗时显示（秒格式）"""
    return f"{seconds:.2f}s"


def format_progress_info(current: int, total: int, start_time: float) -> str:
    """格式化进度信息"""
    if total == 0:
        return ""
    
    # 计算百分比
    percentage = (current / total) * 100
    
    # 计算已耗时
    elapsed_time = time.time() - start_time
    hours = int(elapsed_time // 3600)
    minutes = int((elapsed_time % 3600) // 60)
    secs = int(elapsed_time % 60)
    elapsed_str = f"{hours:02d}:{minutes:02d}:{secs:02d}"
    
    # 计算预估剩余时间
    if current > 0:
        avg_time_per_item = elapsed_time / current
        remaining_items = total - current
        estimated_remaining = avg_time_per_item * remaining_items
        remaining_hours = int(estimated_remaining // 3600)
        remaining_minutes = int((estimated_remaining % 3600) // 60)
        remaining_secs = int(estimated_remaining % 60)
        remaining_str = f"{remaining_hours:02d}:{remaining_minutes:02d}:{remaining_secs:02d}"
    else:
        remaining_str = "计算中..."
    
    return f"({percentage:.1f}%) | 已耗时: {elapsed_str} | 预计剩余: {remaining_str}"


def insert_to_database(client: Client, records: List[Dict]) -> Tuple[int, int]:
    """
    批量插入财务报告数据到数据库
    
    Args:
        client: ClickHouse客户端
        records: 财务报告记录列表
    
    Returns:
        (成功数量, 失败数量) 元组
    """
    if not records:
        return 0, 0
    
    success_count = 0
    failed_count = 0
    
    try:
        # 将记录转换为列表格式，按列顺序排列
        data = []
        for record in records:
            data.append([
                record['code'],
                record['quote_name'],
                record['report_date'],
                record['report_name'],
                record['currency'],
                record['currency_name'],
                record['org_type'],
                record.get('oa_ncf'),
                record.get('oa_cash_received_of_sales_service'),
                record.get('oa_refund_of_tax_and_levies'),
                record.get('oa_cash_received_of_othr'),
                record.get('oa_sub_total_ci'),
                record.get('oa_goods_buy_and_service_cash_pay'),
                record.get('oa_cash_paid_to_employee_etc'),
                record.get('oa_payments_of_all_taxes'),
                record.get('oa_othrcash_paid_relating_to'),
                record.get('oa_sub_total_cos'),
                record.get('ia_ncf'),
                record.get('ia_cash_received_of_dspsl_invest'),
                record.get('ia_invest_income_cash_received'),
                record.get('ia_net_cash_of_disposal_assets'),
                record.get('ia_net_cash_of_disposal_branch'),
                record.get('ia_cash_received_of_othr'),
                record.get('ia_sub_total_ci'),
                record.get('ia_invest_paid_cash'),
                record.get('ia_cash_paid_for_assets'),
                record.get('ia_othrcash_paid_relating_to'),
                record.get('ia_sub_total_cos'),
                record.get('fa_ncf'),
                record.get('fa_cash_received_of_absorb_invest'),
                record.get('fa_cash_received_from_investor'),
                record.get('fa_cash_received_from_bond_issue'),
                record.get('fa_cash_received_of_borrowing'),
                record.get('fa_cash_received_of_othr'),
                record.get('fa_sub_total_ci'),
                record.get('fa_cash_pay_for_debt'),
                record.get('fa_cash_paid_of_distribution'),
                record.get('fa_branch_paid_to_minority_holder'),
                record.get('fa_othrcash_paid_relating_to'),
                record.get('fa_sub_total_cos'),
                record.get('cce_effect_of_exchange_chg'),
                record.get('cce_net_increase'),
                record.get('cce_initial_balance'),
                record.get('cce_final_balance'),
                record.get('net_cash_amt_from_branch'),
                # 财务指标字段
                record.get('avg_roe'),
                record.get('np_per_share'),
                record.get('operate_cash_flow_ps'),
                record.get('basic_eps'),
                record.get('capital_reserve'),
                record.get('undistri_profit_ps'),
                record.get('net_interest_of_total_assets'),
                record.get('net_selling_rate'),
                record.get('gross_selling_rate'),
                record.get('total_revenue'),
                record.get('operating_income_yoy'),
                record.get('net_profit_atsopc'),
                record.get('net_profit_atsopc_yoy'),
                record.get('net_profit_after_nrgal_atsolc'),
                record.get('np_atsopc_nrgal_yoy'),
                record.get('ore_dlt'),
                record.get('rop'),
                record.get('asset_liab_ratio'),
                record.get('current_ratio'),
                record.get('quick_ratio'),
                record.get('equity_multiplier'),
                record.get('equity_ratio'),
                record.get('holder_equity'),
                record.get('ncf_from_oa_to_total_liab'),
                record.get('inventory_turnover_days'),
                record.get('receivable_turnover_days'),
                record.get('accounts_payable_turnover_days'),
                record.get('cash_cycle'),
                record.get('operating_cycle'),
                record.get('total_capital_turnover'),
                record.get('inventory_turnover'),
                record.get('account_receivable_turnover'),
                record.get('accounts_payable_turnover'),
                record.get('current_asset_turnover_rate'),
                record.get('fixed_asset_turnover_ratio')
            ])
        
        # 使用列式插入
        client.insert(
            table='stock_financial_report',
            data=data,
            column_names=[
                'code', 'quote_name', 'report_date', 'report_name', 'currency', 'currency_name', 'org_type',
                'oa_ncf', 'oa_cash_received_of_sales_service', 'oa_refund_of_tax_and_levies', 'oa_cash_received_of_othr',
                'oa_sub_total_ci', 'oa_goods_buy_and_service_cash_pay', 'oa_cash_paid_to_employee_etc',
                'oa_payments_of_all_taxes', 'oa_othrcash_paid_relating_to', 'oa_sub_total_cos',
                'ia_ncf', 'ia_cash_received_of_dspsl_invest', 'ia_invest_income_cash_received',
                'ia_net_cash_of_disposal_assets', 'ia_net_cash_of_disposal_branch', 'ia_cash_received_of_othr',
                'ia_sub_total_ci', 'ia_invest_paid_cash', 'ia_cash_paid_for_assets', 'ia_othrcash_paid_relating_to',
                'ia_sub_total_cos',
                'fa_ncf', 'fa_cash_received_of_absorb_invest', 'fa_cash_received_from_investor',
                'fa_cash_received_from_bond_issue', 'fa_cash_received_of_borrowing', 'fa_cash_received_of_othr',
                'fa_sub_total_ci', 'fa_cash_pay_for_debt', 'fa_cash_paid_of_distribution',
                'fa_branch_paid_to_minority_holder', 'fa_othrcash_paid_relating_to', 'fa_sub_total_cos',
                'cce_effect_of_exchange_chg', 'cce_net_increase', 'cce_initial_balance', 'cce_final_balance',
                'net_cash_amt_from_branch',
                # 财务指标字段
                'avg_roe', 'np_per_share', 'operate_cash_flow_ps', 'basic_eps', 'capital_reserve',
                'undistri_profit_ps', 'net_interest_of_total_assets', 'net_selling_rate', 'gross_selling_rate',
                'total_revenue', 'operating_income_yoy', 'net_profit_atsopc', 'net_profit_atsopc_yoy',
                'net_profit_after_nrgal_atsolc', 'np_atsopc_nrgal_yoy', 'ore_dlt', 'rop',
                'asset_liab_ratio', 'current_ratio', 'quick_ratio', 'equity_multiplier', 'equity_ratio',
                'holder_equity', 'ncf_from_oa_to_total_liab',
                'inventory_turnover_days', 'receivable_turnover_days', 'accounts_payable_turnover_days',
                'cash_cycle', 'operating_cycle', 'total_capital_turnover', 'inventory_turnover',
                'account_receivable_turnover', 'accounts_payable_turnover', 'current_asset_turnover_rate',
                'fixed_asset_turnover_ratio'
            ]
        )
        success_count = len(records)
        
    except Exception as e:
        logger.error(f"批量插入数据库失败: {records[0].get('code') if records else 'unknown'}, 错误: {e}")
        failed_count = len(records)
    
    return success_count, failed_count


if __name__ == "__main__":
    # 请求延迟（秒），避免请求过快
    delay = 0.5
    
    logger.info("🚀 开始抓取财务报告数据...")
    
    # 创建数据库客户端
    client = create_clickhouse_client()
    
    # 从数据库获取股票代码列表
    stock_codes = get_stock_codes_from_db(client)
    
    if not stock_codes:
        logger.error("❌ 未获取到股票代码，程序退出")
        client.close()
        exit(1)
    
    logger.info(f"📋 准备处理 {len(stock_codes)} 只股票的财务报告数据")
    
    # 一次性批量查询所有已存在的财务报告
    existing_reports = get_existing_financial_reports(client)
    
    total_success = 0
    total_failed = 0
    total_insert_success = 0
    total_insert_failed = 0
    total_skipped = 0  # 跳过数量（已存在所有报告期）
    total_records_skipped = 0  # 跳过的报告期记录数量
    
    # 记录开始时间
    start_time = time.time()
    
    # 使用 playwright 打开浏览器
    with sync_playwright() as p:
        # 启动浏览器（headless模式，可以设置为False查看浏览器）
        browser = p.chromium.launch(headless=False)
        
        # 创建浏览器上下文
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        
        # 创建页面
        page = context.new_page()
        
        try:
            # 先访问一次雪球页面，确保 cookies 生效并加载页面
            logger.info("正在访问雪球页面，初始化浏览器状态...")
            if stock_codes:
                first_stock = stock_codes[0]
                first_code = str(first_stock.get('code', '601127')).zfill(6)
                first_market = first_stock.get('market', '') or ('SH' if first_code.startswith('6') else 'SZ')
            else:
                first_code = '601127'
                first_market = 'SH'
            
            first_symbol = f"{first_market}{first_code}"
            init_url = f"https://xueqiu.com/snowman/S/{first_symbol}/detail#/GSJJ"
            
            page.goto(init_url, wait_until="networkidle", timeout=30000)
            logger.info(f"已访问初始化页面: {init_url}")
            time.sleep(2)  # 等待页面完全加载
            
            for i, stock in enumerate(stock_codes, 1):
                # 记录单条开始时间
                single_start_time = time.time()
                
                # 从数据库获取的是字典格式: {'code': '000001', 'market': 'SZ'}
                if isinstance(stock, dict):
                    code = str(stock.get('code', '')).zfill(6)
                    market = stock.get('market', '') or ''
                else:
                    single_elapsed = time.time() - single_start_time
                    single_time_str = format_single_time(single_elapsed)
                    progress_info = format_progress_info(i, len(stock_codes), start_time)
                    print(f"❌ {stock} 跳过 | 无效的股票代码格式 | {single_time_str} | {i}/{len(stock_codes)} {progress_info}")
                    total_failed += 1
                    continue
                
                symbol = convert_symbol(code, market)
                
                # 获取现金流量数据和财务指标数据
                cash_flow_data = fetch_cash_flow_data(page, symbol)
                indicator_data = fetch_indicator_data(page, symbol)
                
                # 至少需要现金流量数据，如果没有则跳过
                if not cash_flow_data:
                    total_failed += 1
                    single_elapsed = time.time() - single_start_time
                    single_time_str = format_single_time(single_elapsed)
                    progress_info = format_progress_info(i, len(stock_codes), start_time)
                    print(f"❌ {symbol} ({code}) 现金流量数据抓取失败 | {single_time_str} | {i}/{len(stock_codes)} {progress_info}")
                    continue
                
                # 提取基本信息（优先使用indicator数据，如果没有则使用cash_flow数据）
                quote_name = (indicator_data.get('quote_name') if indicator_data else None) or cash_flow_data.get('quote_name', '')
                currency = (indicator_data.get('currency') if indicator_data else None) or cash_flow_data.get('currency', 'CNY')
                currency_name = (indicator_data.get('currency_name') if indicator_data else None) or cash_flow_data.get('currency_name', '人民币')
                org_type = (indicator_data.get('org_type') if indicator_data else None) or cash_flow_data.get('org_type', 1)
                
                cash_flow_list = cash_flow_data.get('list', [])
                indicator_list = indicator_data.get('list', []) if indicator_data else []
                
                if not cash_flow_list:
                    total_failed += 1
                    single_elapsed = time.time() - single_start_time
                    single_time_str = format_single_time(single_elapsed)
                    progress_info = format_progress_info(i, len(stock_codes), start_time)
                    print(f"❌ {symbol} ({code}) 未找到现金流量报告期数据 | {single_time_str} | {i}/{len(stock_codes)} {progress_info}")
                    continue
                
                # 构建indicator数据字典，以report_date为key
                indicator_dict = {}
                for indicator_item in indicator_list:
                    report_date = timestamp_to_date(indicator_item.get('report_date'))
                    if report_date:
                        indicator_dict[report_date] = indicator_item
                
                # 解析所有报告期数据，合并现金流量和指标数据
                records = []
                for cash_flow_item in cash_flow_list:
                    # 获取对应的indicator数据
                    cash_flow_report_date = timestamp_to_date(cash_flow_item.get('report_date'))
                    indicator_item = indicator_dict.get(cash_flow_report_date) if cash_flow_report_date else None
                    
                    record = parse_financial_data(
                        cash_flow_item, indicator_item, code, market, quote_name, currency, currency_name, org_type
                    )
                    
                    # 检查是否已存在该报告期
                    record_key = (code, record['report_date'])
                    if record_key in existing_reports:
                        total_records_skipped += 1
                        continue
                    
                    records.append(record)
                
                if not records:
                    total_skipped += 1
                    single_elapsed = time.time() - single_start_time
                    single_time_str = format_single_time(single_elapsed)
                    progress_info = format_progress_info(i, len(stock_codes), start_time)
                    print(f"⏭️  {symbol} ({code}) 跳过 | 所有报告期已存在 | {single_time_str} | {i}/{len(stock_codes)} {progress_info}")
                    continue
                
                total_success += 1
                
                # 批量插入数据库
                insert_success, insert_failed = insert_to_database(client, records)
                total_insert_success += insert_success
                total_insert_failed += insert_failed
                
                single_elapsed = time.time() - single_start_time
                single_time_str = format_single_time(single_elapsed)
                progress_info = format_progress_info(i, len(stock_codes), start_time)
                
                if insert_failed > 0:
                    print(f"⚠️  {symbol} ({code}) 部分成功 | {len(cash_flow_list)} 个报告期，新增 {insert_success} 条，失败 {insert_failed} 条 | {single_time_str} | {i}/{len(stock_codes)} {progress_info}")
                else:
                    print(f"✅ {symbol} ({code}) 入库成功 | {len(cash_flow_list)} 个报告期，新增 {insert_success} 条记录 | {single_time_str} | {i}/{len(stock_codes)} {progress_info}")
                
                # 延迟，避免请求过快
                if i < len(stock_codes):
                    time.sleep(delay)
        
        finally:
            # 关闭浏览器
            # page.close()
            # context.close()
            # browser.close()
            pass
    
    # 关闭数据库连接
    client.close()
    
    logger.info(f"🎉 抓取完成！成功: {total_success}, 失败: {total_failed}, 跳过: {total_skipped}, 总计: {len(stock_codes)}")
    logger.info(f"📊 报告期记录统计：新增: {total_insert_success}, 失败: {total_insert_failed}, 跳过: {total_records_skipped}")
    logger.info(f"💾 数据库插入完成！成功: {total_insert_success}, 失败: {total_insert_failed}")

