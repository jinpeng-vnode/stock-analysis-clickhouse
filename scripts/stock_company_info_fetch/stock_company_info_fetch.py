"""
股票公司信息抓取脚本 - 从雪球API获取公司基本信息
数据插入ClickHouse数据库
使用 playwright 发送请求，支持 cookies
"""
import time
import json
import sys
from pathlib import Path
from typing import List, Dict, Optional
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
logger.add(
    lambda msg: print(msg, end=''),
    level="INFO",
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>\n"
)


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


def fetch_company_info(page: Page, symbol: str) -> Optional[Dict]:
    """
    从雪球API获取公司信息（使用浏览器访问）
    
    Args:
        page: Playwright Page 对象
        symbol: 雪球格式的股票代码，如 'SH601127'
    
    Returns:
        公司信息字典或None
    """
    url = f"https://stock.xueqiu.com/v5/stock/f10/cn/company.json?symbol={symbol}"
    
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
        # 页面内容可能是HTML包装的，需要提取JSON部分
        # 如果直接返回JSON，直接解析
        try:
            data = json.loads(content)
        except json.JSONDecodeError:
            # 如果不是纯JSON，尝试从 <pre> 标签或 body 中提取
            json_text = page.evaluate("document.body.textContent")
            data = json.loads(json_text)
        
        if data.get('error_code') != 0:
            logger.warning(f"API返回错误: {symbol}, 错误码: {data.get('error_code')}, 描述: {data.get('error_description')}")
            return None
        
        company_data = data.get('data', {}).get('company')
        if not company_data:
            logger.warning(f"未找到公司数据: {symbol}")
            return None
        
        return company_data
        
    except Exception as e:
        logger.error(f"获取公司信息失败: {symbol}, 错误: {e}")
        return None


def parse_company_data(company_data: Dict, code: str, market: str) -> Dict:
    """
    解析公司数据并格式化
    
    Args:
        company_data: API返回的公司数据
        code: 股票代码
        market: 市场类型
    
    Returns:
        格式化后的公司信息字典
    """
    # 行业信息
    industry = company_data.get('affiliate_industry', {})
    
    # 构建记录
    record = {
        'code': code,
        'name': company_data.get('org_short_name_cn') or company_data.get('org_name_cn', ''),
        'market': market if market else ('SH' if code.startswith('6') else 'SZ'),
        
        # 组织信息
        'org_id': company_data.get('org_id'),
        'org_name_cn': company_data.get('org_name_cn'),
        'org_name_en': company_data.get('org_name_en'),
        'org_short_name_en': company_data.get('org_short_name_en'),
        'pre_name_cn': company_data.get('pre_name_cn'),
        
        # 业务信息
        'main_operation_business': company_data.get('main_operation_business'),
        'operating_scope': company_data.get('operating_scope'),
        'industry_code': industry.get('ind_code') if industry else None,
        'industry_name': industry.get('ind_name') if industry else None,
        
        # 注册信息
        'district_encode': company_data.get('district_encode'),
        'provincial_name': company_data.get('provincial_name'),
        'established_date': timestamp_to_date(company_data.get('established_date')),
        'reg_asset': company_data.get('reg_asset'),
        'reg_address_cn': company_data.get('reg_address_cn'),
        'reg_address_en': company_data.get('reg_address_en'),
        'office_address_cn': company_data.get('office_address_cn'),
        'office_address_en': company_data.get('office_address_en'),
        
        # 联系信息
        'telephone': company_data.get('telephone'),
        'postcode': company_data.get('postcode'),
        'fax': company_data.get('fax'),
        'email': company_data.get('email'),
        'org_website': company_data.get('org_website'),
        
        # 管理信息
        'legal_representative': company_data.get('legal_representative'),
        'chairman': company_data.get('chairman'),
        'general_manager': company_data.get('general_manager'),
        'secretary': company_data.get('secretary'),
        'executives_nums': company_data.get('executives_nums'),
        'actual_controller': company_data.get('actual_controller'),
        'classi_name': company_data.get('classi_name'),
        
        # 上市信息
        'listed_date': timestamp_to_date(company_data.get('listed_date')),
        'actual_issue_vol': company_data.get('actual_issue_vol'),
        'issue_price': company_data.get('issue_price'),
        'actual_rc_net_amt': company_data.get('actual_rc_net_amt'),
        'pe_after_issuing': company_data.get('pe_after_issuing'),
        'online_success_rate_of_issue': company_data.get('online_success_rate_of_issue'),
        
        # 其他信息
        'staff_num': company_data.get('staff_num'),
        'currency_encode': company_data.get('currency_encode'),
        'currency': company_data.get('currency')
    }
    
    return record


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


def get_existing_company_codes(client: Client) -> set:
    """
    批量查询所有已有公司介绍的股票代码
    
    Args:
        client: ClickHouse客户端
    
    Returns:
        已有公司介绍的股票代码集合
    """
    try:
        # 一次性查询所有已有公司介绍的股票代码
        # 使用FINAL关键字确保获取最新版本的数据（ReplacingMergeTree引擎）
        query = """
            SELECT code 
            FROM stock_info FINAL 
            WHERE main_operation_business IS NOT NULL 
              AND main_operation_business != ''
              AND length(trim(main_operation_business)) > 0
        """
        result = client.query(query).result_rows
        
        if result:
            codes = {row[0] for row in result}
            logger.info(f"已存在公司介绍的股票数量: {len(codes)}")
            return codes
        else:
            logger.info("没有找到已有公司介绍的股票")
            return set()
            
    except Exception as e:
        logger.warning(f"批量查询已有公司介绍失败: {e}")
        # 如果查询失败，返回空集合，继续执行抓取流程
        return set()


def insert_to_database(client: Client, record: Dict) -> bool:
    """
    将单条公司信息列式插入数据库
    
    Args:
        client: ClickHouse客户端
        record: 公司信息记录
    
    Returns:
        是否插入成功
    """
    try:
        # 将记录转换为列表格式，按列顺序排列
        data = [[
            record['code'],
            record['name'],
            record['market'],
            record.get('org_id'),
            record.get('org_name_cn'),
            record.get('org_name_en'),
            record.get('org_short_name_en'),
            record.get('pre_name_cn'),
            record.get('main_operation_business'),
            record.get('operating_scope'),
            record.get('industry_code'),
            record.get('industry_name'),
            record.get('district_encode'),
            record.get('provincial_name'),
            record.get('established_date'),
            record.get('reg_asset'),
            record.get('reg_address_cn'),
            record.get('reg_address_en'),
            record.get('office_address_cn'),
            record.get('office_address_en'),
            record.get('telephone'),
            record.get('postcode'),
            record.get('fax'),
            record.get('email'),
            record.get('org_website'),
            record.get('legal_representative'),
            record.get('chairman'),
            record.get('general_manager'),
            record.get('secretary'),
            record.get('executives_nums'),
            record.get('actual_controller'),
            record.get('classi_name'),
            record.get('listed_date'),
            record.get('actual_issue_vol'),
            record.get('issue_price'),
            record.get('actual_rc_net_amt'),
            record.get('pe_after_issuing'),
            record.get('online_success_rate_of_issue'),
            record.get('staff_num'),
            record.get('currency_encode'),
            record.get('currency')
        ]]
        
        # 使用列式插入
        client.insert(
            table='stock_info',
            data=data,
            column_names=[
                'code', 'name', 'market',
                'org_id', 'org_name_cn', 'org_name_en', 'org_short_name_en', 'pre_name_cn',
                'main_operation_business', 'operating_scope', 'industry_code', 'industry_name',
                'district_encode', 'provincial_name', 'established_date', 'reg_asset',
                'reg_address_cn', 'reg_address_en', 'office_address_cn', 'office_address_en',
                'telephone', 'postcode', 'fax', 'email', 'org_website',
                'legal_representative', 'chairman', 'general_manager', 'secretary', 'executives_nums',
                'actual_controller', 'classi_name',
                'listed_date', 'actual_issue_vol', 'issue_price', 'actual_rc_net_amt',
                'pe_after_issuing', 'online_success_rate_of_issue',
                'staff_num', 'currency_encode', 'currency'
            ]
        )
        return True
    except Exception as e:
        logger.error(f"插入数据库失败: {record.get('code')}, 错误: {e}")
        return False


if __name__ == "__main__":
    # 请求延迟（秒），避免请求过快
    delay = 0.5
    
    logger.info("开始抓取股票公司信息...")
    
    # Cookies配置，格式: [{"name": "cookie_name", "value": "cookie_value", "domain": ".xueqiu.com"}, ...]
    # 可以从浏览器开发者工具中复制 cookies，然后转换为这种格式
    cookies = [
        # 示例格式，需要替换为实际的 cookies
        # {"name": "xq_a_token", "value": "your_token_here", "domain": ".xueqiu.com"},
        # {"name": "xq_r_token", "value": "your_token_here", "domain": ".xueqiu.com"},
    ]
    
    # 创建数据库客户端
    client = create_clickhouse_client()
    
    # 从数据库获取股票代码列表
    stock_codes = get_stock_codes_from_db(client)
    
    if not stock_codes:
        logger.error("未获取到股票代码，程序退出")
        client.close()
        exit(1)
    
    logger.info(f"准备处理 {len(stock_codes)} 只股票的公司信息")
    
    # 一次性批量查询所有已有公司介绍的股票代码
    existing_company_codes = get_existing_company_codes(client)
    
    total_success = 0
    total_failed = 0
    total_insert_success = 0
    total_insert_failed = 0
    total_skipped = 0  # 跳过数量（已存在公司介绍）
    
    # 使用 playwright 打开浏览器
    with sync_playwright() as p:
        # 启动浏览器（headless模式，可以设置为False查看浏览器）
        browser = p.chromium.launch(headless=False)
        
        # 创建浏览器上下文
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        
        # 如果有 cookies，添加到上下文中
        if cookies:
            context.add_cookies(cookies)
        
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
                # 从数据库获取的是字典格式: {'code': '000001', 'market': 'SZ'}
                if isinstance(stock, dict):
                    code = str(stock.get('code', '')).zfill(6)
                    market = stock.get('market', '') or ''
                else:
                    logger.warning(f"跳过无效的股票代码格式: {stock}")
                    total_failed += 1
                    continue
                
                symbol = convert_symbol(code, market)
                
                # 检查是否已存在公司介绍信息（使用集合快速判断）
                if code in existing_company_codes:
                    total_skipped += 1
                    logger.info(f"[{i}/{len(stock_codes)}] {symbol} ({code}) 已存在公司介绍，跳过...")
                    continue
                
                logger.info(f"[{i}/{len(stock_codes)}] 抓取 {symbol} ({code}) 的公司信息...")
                
                # 获取公司信息
                company_data = fetch_company_info(page, symbol)
                
                if company_data:
                    # 解析数据
                    record = parse_company_data(company_data, code, market)
                    total_success += 1
                    logger.info(f"✓ {symbol} 抓取成功")
                    
                    # 立即插入数据库
                    if insert_to_database(client, record):
                        total_insert_success += 1
                        logger.info(f"✓ {symbol} 插入数据库成功")
                    else:
                        total_insert_failed += 1
                        logger.warning(f"✗ {symbol} 插入数据库失败")
                else:
                    total_failed += 1
                    logger.warning(f"✗ {symbol} 抓取失败")
                
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
    
    logger.info(f"抓取完成！成功: {total_success}, 失败: {total_failed}, 跳过: {total_skipped}, 总计: {len(stock_codes)}")
    logger.info(f"数据库插入完成！成功: {total_insert_success}, 失败: {total_insert_failed}")
