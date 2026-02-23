#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
生产者1：按股票代码列表抓取链接
- 遍历指定股票的所有页面
- 收集公告链接
- 写入数据库（只写基础信息，content和attachments留空）
"""

import asyncio
import sys
import logging
from pathlib import Path
from typing import List, Dict, Optional
from playwright.async_api import async_playwright, Page, BrowserContext
from datetime import datetime, date

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from clickhouse_connect import get_client
from clickhouse_connect.driver import Client
from config import config

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - [生产者] - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)


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


def check_stock_needs_crawl(db_client: Client, stock_code: str, hours_threshold: int = 24) -> bool:
    """
    检查股票是否需要抓取（根据数据库中的最新版本时间）
    
    Args:
        db_client: ClickHouse客户端
        stock_code: 股票代码
        hours_threshold: 时间阈值（小时），如果最新版本时间在阈值内，则不需要抓取
    
    Returns:
        True: 需要抓取, False: 不需要抓取（已抓取过）
    """
    try:
        # 先检查是否有记录，避免max()返回默认值
        count_query = f"""
            SELECT count() as cnt
            FROM stock_announcement FINAL
            WHERE code = '{stock_code}'
        """
        
        count_result = db_client.query(count_query)
        count = count_result.result_rows[0][0] if count_result.result_rows else 0
        
        if count == 0:
            # 没有记录，需要抓取
            logger.debug(f"股票 {stock_code}：数据库中没有记录，需要抓取")
            return True
        
        # 有记录，查询最新版本时间
        query = f"""
            SELECT max(version) as last_version
            FROM stock_announcement FINAL
            WHERE code = '{stock_code}'
        """
        
        result = db_client.query(query)
        
        if not result.result_rows or not result.result_rows[0][0]:
            # 虽然count>0但max()返回空，需要抓取
            logger.debug(f"股票 {stock_code}：无法获取版本时间，需要抓取")
            return True
        
        last_version = result.result_rows[0][0]
        
        # 处理时间类型（ClickHouse可能返回datetime对象或字符串）
        if isinstance(last_version, str):
            # 字符串格式：尝试解析
            try:
                last_version_dt = datetime.fromisoformat(last_version.replace('Z', '+00:00'))
                if last_version_dt.tzinfo:
                    last_version_dt = last_version_dt.replace(tzinfo=None)
            except:
                logger.warning(f"无法解析版本时间字符串: {last_version}")
                return True  # 解析失败，默认需要抓取
        else:
            # 已经是datetime对象
            last_version_dt = last_version
            if hasattr(last_version_dt, 'tzinfo') and last_version_dt.tzinfo:
                last_version_dt = last_version_dt.replace(tzinfo=None)
        
        # 检查是否是无效的默认时间（Unix时间戳0，即1970-01-01）
        # 如果时间早于2000年，视为无效值
        if last_version_dt.year < 2000:
            logger.debug(f"股票 {stock_code}：版本时间为无效默认值 ({last_version_dt})，视为无记录，需要抓取")
            return True
        
        # 计算时间差（小时）
        now = datetime.now()
        time_diff = (now - last_version_dt).total_seconds() / 3600
        
        if time_diff < hours_threshold:
            logger.info(f"股票 {stock_code}：最新版本时间 {last_version_dt.strftime('%Y-%m-%d %H:%M:%S')}，距离现在 {time_diff:.1f} 小时，跳过抓取")
            return False
        else:
            logger.info(f"股票 {stock_code}：最新版本时间 {last_version_dt.strftime('%Y-%m-%d %H:%M:%S')}，距离现在 {time_diff:.1f} 小时，需要重新抓取")
            return True
    
    except Exception as e:
        logger.warning(f"检查股票 {stock_code} 是否需要抓取失败: {e}，默认需要抓取")
        return True


def get_stock_codes_from_db(
    db_client: Client,
    status: Optional[str] = "正常",
    market: Optional[str] = None,
    limit: Optional[int] = None,
    filter_crawled: bool = True,
    hours_threshold: int = 24
) -> List[str]:
    """
    从数据库读取股票代码列表
    
    Args:
        db_client: ClickHouse客户端
        status: 股票状态过滤（默认："正常"），None表示不过滤
        market: 市场类型过滤（"SH"/"SZ"），None表示不过滤
        limit: 限制返回数量，None表示不限制
        filter_crawled: 是否过滤已抓取的股票（根据版本时间）
        hours_threshold: 时间阈值（小时），如果最新版本时间在阈值内，则跳过
    
    Returns:
        股票代码列表
    """
    try:
        # 构建查询条件
        conditions = []
        if status:
            conditions.append(f"status = '{status}'")
        if market:
            conditions.append(f"market = '{market}'")
        
        where_clause = ""
        if conditions:
            where_clause = "WHERE " + " AND ".join(conditions)
        
        limit_clause = ""
        if limit:
            limit_clause = f"LIMIT {limit}"
        
        # 使用 FINAL 确保去重（ReplacingMergeTree引擎）
        query = f"""
            SELECT DISTINCT code
            FROM stock_info FINAL
            {where_clause}
            ORDER BY code
            {limit_clause}
        """
        
        result = db_client.query(query)
        all_stock_codes = [row[0] for row in result.result_rows]
        
        logger.info(f"从数据库读取到 {len(all_stock_codes)} 个股票代码")
        if status:
            logger.info(f"状态过滤: {status}")
        if market:
            logger.info(f"市场过滤: {market}")
        if limit:
            logger.info(f"数量限制: {limit}")
        
        # 如果需要过滤已抓取的股票
        if filter_crawled:
            logger.info(f"正在批量检查 {len(all_stock_codes)} 个股票的抓取状态...")
            
            # 批量查询所有股票的最新版本时间和记录数
            # 使用 IN 子句批量查询，避免逐个查询
            codes_str = "', '".join(all_stock_codes)
            batch_query = f"""
                SELECT 
                    code,
                    max(version) as last_version,
                    count() as record_count
                FROM stock_announcement FINAL
                WHERE code IN ('{codes_str}')
                GROUP BY code
            """
            
            batch_result = db_client.query(batch_query)
            
            # 构建已抓取股票的字典 {code: last_version}
            crawled_stocks = {}
            for row in batch_result.result_rows:
                code = row[0]
                last_version = row[1]
                record_count = row[2]
                
                # 如果记录数为0或版本时间为空，跳过
                if record_count == 0 or not last_version:
                    continue
                
                # 处理时间类型
                if isinstance(last_version, str):
                    try:
                        last_version_dt = datetime.fromisoformat(last_version.replace('Z', '+00:00'))
                        if last_version_dt.tzinfo:
                            last_version_dt = last_version_dt.replace(tzinfo=None)
                    except:
                        continue
                else:
                    last_version_dt = last_version
                    if hasattr(last_version_dt, 'tzinfo') and last_version_dt.tzinfo:
                        last_version_dt = last_version_dt.replace(tzinfo=None)
                
                # 检查是否是无效的默认时间
                if last_version_dt.year < 2000:
                    continue
                
                crawled_stocks[code] = last_version_dt
            
            # 过滤股票列表
            filtered_codes = []
            skipped_count = 0
            now = datetime.now()
            
            for code in all_stock_codes:
                if code in crawled_stocks:
                    # 有记录，检查时间差
                    last_version_dt = crawled_stocks[code]
                    time_diff = (now - last_version_dt).total_seconds() / 3600
                    
                    if time_diff < hours_threshold:
                        # 时间在阈值内，跳过
                        skipped_count += 1
                        logger.debug(f"股票 {code}：最新版本时间 {last_version_dt.strftime('%Y-%m-%d %H:%M:%S')}，距离现在 {time_diff:.1f} 小时，跳过抓取")
                    else:
                        # 时间超过阈值，需要重新抓取
                        filtered_codes.append(code)
                        logger.debug(f"股票 {code}：最新版本时间 {last_version_dt.strftime('%Y-%m-%d %H:%M:%S')}，距离现在 {time_diff:.1f} 小时，需要重新抓取")
                else:
                    # 没有记录，需要抓取
                    filtered_codes.append(code)
            
            logger.info(f"过滤完成：剩余 {len(filtered_codes)} 个股票需要抓取，跳过 {skipped_count} 个已抓取的股票")
            return filtered_codes
        else:
            return all_stock_codes
    
    except Exception as e:
        logger.error(f"从数据库读取股票代码失败: {e}")
        return []


async def safe_goto(page: Page, url: str, max_retries: int = 3, timeout: int = 60000) -> bool:
    """
    安全地导航到指定URL，带重试机制
    
    Args:
        page: Playwright 页面对象
        url: 目标URL
        max_retries: 最大重试次数
        timeout: 超时时间（毫秒）
    
    Returns:
        是否成功导航
    """
    for attempt in range(1, max_retries + 1):
        try:
            response = await page.goto(url, wait_until="domcontentloaded", timeout=timeout)
            if response and response.status >= 400:
                raise Exception(f"HTTP {response.status}")
            # 等待页面基本加载完成
            await page.wait_for_load_state("domcontentloaded", timeout=5000)
            return True
        except Exception as e:
            if attempt < max_retries:
                wait_time = attempt * 2  # 递增等待时间
                logger.warning(f"第 {attempt} 次导航失败，{wait_time} 秒后重试... ({e})")
                await asyncio.sleep(wait_time)
            else:
                logger.error(f"导航失败，已重试 {max_retries} 次: {e}")
                return False
    return False


async def wait_for_dom_or_sleep(page: Page, interval: float, timeout: int = 10000):
    """
    等待DOM加载完成或延迟指定时间
    
    Args:
        page: Playwright 页面对象
        interval: 延迟时间（秒），如果为0则等待页面load状态
        timeout: DOM等待超时时间（毫秒）
    """
    if interval == 0:
        # 等待页面load状态（所有资源加载完成）
        try:
            await page.wait_for_load_state("load", timeout=timeout)
        except Exception as e:
            logger.warning(f"等待load状态超时: {e}")
    else:
        await asyncio.sleep(interval)


async def _navigate_to_next_page(page: Page) -> bool:
    """
    翻页逻辑
    
    Args:
        page: Playwright 页面对象
    
    Returns:
        是否成功翻页
    """
    try:
        can_go_next = await page.evaluate("""
            () => {
                const links = Array.from(document.querySelectorAll('a'));
                const nextLink = links.find(link => {
                    const text = link.textContent.trim();
                    return text === '下一页' || text.includes('下一页');
                });
                
                if (!nextLink) return false;
                if (nextLink.offsetParent === null) return false;
                
                const parent = nextLink.parentElement;
                if (parent && parent.classList.contains('disabled')) return false;
                if (nextLink.classList.contains('disabled')) return false;
                
                return true;
            }
        """)
        
        if can_go_next:
            clicked = await page.evaluate("""
                () => {
                    const links = Array.from(document.querySelectorAll('a'));
                    const nextLink = links.find(link => {
                        const text = link.textContent.trim();
                        return text === '下一页' || text.includes('下一页');
                    });
                    
                    if (nextLink) {
                        nextLink.click();
                        return true;
                    }
                    return false;
                }
            """)
            return clicked
        return False
    except Exception as e:
        logger.error(f"翻页处理失败: {e}")
        return False


async def _collect_links_from_page(page: Page, stock_code: str, page_num: int) -> List[Dict]:
    """
    从页面收集链接
    
    Args:
        page: Playwright 页面对象
        stock_code: 股票代码
        page_num: 页码
    
    Returns:
        链接列表 [{title, type, date, detail_url}, ...]
    """
    links = []
    
    # 等待表格加载
    table_loaded = False
    selectors = [
        "table tbody tr",
        "table tr",
        "[data-toggle='dataview'] tbody tr",
        ".dataview tbody tr"
    ]
    
    for selector in selectors:
        try:
            await page.wait_for_selector(selector, timeout=5000)
            table_loaded = True
            break
        except:
            continue
    
    if not table_loaded:
        logger.warning(f"股票 {stock_code} 第 {page_num} 页：等待表格加载超时，尝试继续...")
    
    # 提取当前页的公告列表
    rows = page.locator("table tbody tr")
    row_count = await rows.count()
    
    if row_count == 0:
        logger.warning(f"股票 {stock_code} 第 {page_num} 页：没有数据")
        return links
    
    # 遍历每一行
    for i in range(row_count):
        try:
            row = rows.nth(i)
            cells = row.locator("td")
            cell_count = await cells.count()
            
            # 公告行应该有3列：标题、类型、日期
            if cell_count < 3:
                continue
            
            # 提取各列数据
            title_cell = cells.nth(0)  # 公告标题列
            type_cell = cells.nth(1)   # 公告类型列
            date_cell = cells.nth(2)   # 公告日期列
            
            # 获取标题和链接
            title_link = title_cell.locator("a").first
            if await title_link.count() == 0:
                continue
            
            title = await title_link.inner_text()
            title = title.strip() if title else ""
            detail_url = await title_link.get_attribute("href")
            
            # 验证日期格式
            ann_date = await date_cell.inner_text()
            ann_date = ann_date.strip() if ann_date else ""
            if not ann_date or len(ann_date) != 10 or ann_date[4] != '-' or ann_date[7] != '-':
                continue
            
            # 处理URL
            if detail_url:
                if detail_url.startswith("javascript:"):
                    continue
                if not detail_url.startswith("http"):
                    if detail_url.startswith("/"):
                        detail_url = f"https://data.eastmoney.com{detail_url}"
                    else:
                        detail_url = f"https://data.eastmoney.com/{detail_url}"
            
            ann_type = await type_cell.inner_text()
            ann_type = ann_type.strip() if ann_type else ""
            
            # 保存链接信息
            links.append({
                "title": title,
                "type": ann_type,
                "date": ann_date,
                "detail_url": detail_url
            })
            
        except Exception as e:
            logger.warning(f"股票 {stock_code} 第 {page_num} 页：处理第 {i+1} 行失败: {e}")
            continue
    
    return links


def _check_existing_links_sync(db_client: Client, stock_code: str, links: List[Dict]) -> List[Dict]:
    """
    检查数据库中已存在的链接，返回需要插入的新链接（同步函数）
    
    Args:
        db_client: ClickHouse客户端
        stock_code: 股票代码
        links: 链接列表
    
    Returns:
        需要插入的新链接列表
    """
    if not links:
        return []
    
    # 构建查询条件：检查 (code, announce_date, detail_url) 组合
    existing_urls = set()
    
    try:
        # 批量查询已存在的记录
        for link in links:
            ann_date = datetime.strptime(link['date'], '%Y-%m-%d').date()
            detail_url = link['detail_url']
            
            query = f"""
                SELECT detail_url 
                FROM stock_announcement FINAL
                WHERE code = '{stock_code}' 
                  AND announce_date = '{ann_date}' 
                  AND detail_url = '{detail_url.replace("'", "''")}'
                LIMIT 1
            """
            
            result = db_client.query(query)
            if result.result_rows:
                existing_urls.add(detail_url)
    except Exception as e:
        logger.error(f"查询已存在链接失败: {e}")
        # 如果查询失败，返回所有链接（让数据库处理去重）
        return links
    
    # 过滤掉已存在的链接
    new_links = [link for link in links if link['detail_url'] not in existing_urls]
    return new_links


async def _save_links_to_db(db_client: Client, stock_code: str, links: List[Dict]) -> int:
    """
    保存链接到数据库（只写基础字段，content和attachments留空）
    
    Args:
        db_client: ClickHouse客户端
        stock_code: 股票代码
        links: 链接列表
    
    Returns:
        成功保存的数量
    """
    if not links:
        return 0
    
    # 检查已存在的链接，只插入新链接（同步调用，使用线程池）
    new_links = await asyncio.to_thread(_check_existing_links_sync, db_client, stock_code, links)
    
    if not new_links:
        logger.info(f"股票 {stock_code}：所有链接已存在，跳过插入")
        return 0
    
    # 准备批量数据（只写基础字段）
    batch_data = []
    for link in new_links:
        try:
            ann_date = datetime.strptime(link['date'], '%Y-%m-%d').date()
        except:
            logger.warning(f"日期格式错误: {link['date']}，跳过该链接")
            continue
        
        batch_data.append([
            stock_code,
            ann_date,
            link.get('title', ''),
            link.get('type', ''),
            link.get('detail_url', ''),
            '',  # content 留空
            ''   # attachments 留空
        ])
    
    if not batch_data:
        return 0
    
    # 批量插入数据库（同步操作，使用线程池）
    try:
        def insert_to_db():
            db_client.insert(
                table='stock_announcement',
                data=batch_data,
                column_names=[
                    'code', 'announce_date', 'title', 'type',
                    'detail_url', 'content', 'attachments'
                ]
            )
        
        await asyncio.to_thread(insert_to_db)
        logger.info(f"股票 {stock_code}：成功保存 {len(batch_data)} 条链接到数据库")
        return len(batch_data)
    except Exception as e:
        logger.error(f"股票 {stock_code}：保存到数据库失败: {e}")
        return 0


async def produce_single_stock(stock_code: str, context: BrowserContext, db_client: Client, 
                               test_mode: bool = False, test_limit: int = 5, interval: float = 0.5) -> int:
    """
    单个股票的生产逻辑
    
    Args:
        stock_code: 股票代码（6位数字）
        context: 浏览器上下文
        db_client: 数据库客户端
        test_mode: 是否启用测试模式
        test_limit: 测试模式下最多抓取的链接数量
        interval: 请求间隔时间（秒）
    
    Returns:
        成功保存的链接数量
    """
    url = f"https://data.eastmoney.com/notices/stock/{stock_code}.html"
    
    logger.info(f"开始抓取股票 {stock_code} 的公告链接")
    
    # 创建用于列表页的页面
    page = await context.new_page()
    
    try:
        # 访问公告列表页
        logger.info(f"股票 {stock_code}：正在访问列表页")
        if not await safe_goto(page, url, max_retries=3, timeout=60000):
            raise Exception(f"无法访问页面: {url}")
        
        await wait_for_dom_or_sleep(page, 3 if interval == 0 else interval)
        logger.info(f"股票 {stock_code}：列表页加载完成")
        
        total_saved = 0
        page_num = 1
        all_links = []
        
        # 遍历所有页面
        while True:
            logger.info(f"股票 {stock_code}：正在解析第 {page_num} 页...")
            
            # 收集当前页的链接
            page_links = await _collect_links_from_page(page, stock_code, page_num)
            
            if page_links:
                all_links.extend(page_links)
                logger.info(f"股票 {stock_code} 第 {page_num} 页：收集到 {len(page_links)} 条链接（累计: {len(all_links)} 条）")
                
                # 批量保存到数据库（每页保存一次）
                saved_count = await _save_links_to_db(db_client, stock_code, page_links)
                total_saved += saved_count
            
            # 测试模式：只抓取第一页的前N个
            if test_mode and page_num == 1 and len(all_links) >= test_limit:
                logger.info(f"股票 {stock_code}：测试模式，已收集{test_limit}个链接，停止收集")
                break
            
            # 尝试翻页
            if await _navigate_to_next_page(page):
                await wait_for_dom_or_sleep(page, interval)
                page_num += 1
                logger.info(f"股票 {stock_code}：翻页成功，准备解析第 {page_num} 页...")
            else:
                logger.info(f"股票 {stock_code}：已到最后一页，链接收集完成")
                break
        
        logger.info(f"股票 {stock_code}：链接收集完成！共收集到 {len(all_links)} 条链接，成功保存 {total_saved} 条新链接")
        return total_saved
    
    finally:
        await page.close()


async def produce_by_stock(stock_codes: List[str], headless: bool = False, 
                           interval: float = 0.5, test_mode: bool = False, 
                           test_limit: int = 5, filter_crawled: bool = True,
                           hours_threshold: int = 24) -> Dict:
    """
    按股票代码列表抓取链接（主函数）
    
    Args:
        stock_codes: 股票代码列表
        headless: 是否使用无头模式
        interval: 请求间隔时间（秒）
        test_mode: 是否启用测试模式
        test_limit: 测试模式下最多抓取的链接数量
        filter_crawled: 是否过滤已抓取的股票（根据版本时间）
        hours_threshold: 时间阈值（小时），如果最新版本时间在阈值内，则跳过抓取
    
    Returns:
        包含每个股票抓取结果的字典
    """
    logger.info(f"开始批量抓取股票公告链接")
    logger.info(f"股票数量: {len(stock_codes)}")
    logger.info(f"股票代码: {', '.join(stock_codes)}")
    
    results = {}
    db_client = None
    
    try:
        # 创建数据库连接
        logger.info("正在连接ClickHouse数据库...")
        db_client = create_clickhouse_client()
        logger.info("数据库连接成功")
        
        # 启动浏览器
        async with async_playwright() as p:
            logger.info("正在启动浏览器...")
            browser = await p.chromium.launch(headless=headless)
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                viewport={"width": 1920, "height": 1080},
                ignore_https_errors=True
            )
            logger.info("浏览器启动成功")
            
            try:
                skipped_count = 0
                for idx, code in enumerate(stock_codes, 1):
                    # 确保代码是6位
                    code = str(code).strip().zfill(6)
                    
                    logger.info(f"\n{'='*60}")
                    logger.info(f"[股票 {idx}/{len(stock_codes)}] 正在处理股票代码: {code}")
                    logger.info(f"{'='*60}")
                    
                    # 检查是否需要抓取（根据数据库版本时间）
                    if filter_crawled:
                        needs_crawl = await asyncio.to_thread(
                            check_stock_needs_crawl, 
                            db_client, 
                            code, 
                            hours_threshold
                        )
                        if not needs_crawl:
                            logger.info(f"[股票 {idx}/{len(stock_codes)}] ⏭️  股票 {code} 已抓取过，跳过")
                            results[code] = {
                                "success": True,
                                "saved_count": 0,
                                "skipped": True
                            }
                            skipped_count += 1
                            continue
                    
                    try:
                        saved_count = await produce_single_stock(
                            code, context, db_client, 
                            test_mode=test_mode, 
                            test_limit=test_limit, 
                            interval=interval
                        )
                        results[code] = {
                            "success": True,
                            "saved_count": saved_count
                        }
                        logger.info(f"[股票 {idx}/{len(stock_codes)}] ✅ 股票 {code} 抓取成功，保存 {saved_count} 条新链接")
                    except Exception as e:
                        logger.error(f"[股票 {idx}/{len(stock_codes)}] ❌ 股票 {code} 抓取失败: {e}")
                        results[code] = {
                            "success": False,
                            "error": str(e),
                            "saved_count": 0
                        }
                    
                    # 避免请求过快
                    if idx < len(stock_codes):
                        logger.info(f"等待{interval}秒后处理下一个股票...")
                        if interval > 0:
                            await asyncio.sleep(interval)
            
            finally:
                logger.info("正在关闭浏览器...")
                await browser.close()
                logger.info("浏览器已关闭")
    
    finally:
        if db_client:
            db_client.close()
            logger.info("数据库连接已关闭")
    
    return results


async def main():
    """主函数：独立运行入口"""
    # 数据库配置
    use_db = True        # 是否从数据库读取股票代码
    status_filter = None  # 股票状态过滤（"正常"/None表示不过滤）
    market_filter = None    # 市场类型过滤（"SH"/"SZ"/None表示不过滤）
    limit_stocks = None     # 限制股票数量（None表示不限制，用于测试）
    filter_crawled = True   # 是否过滤已抓取的股票（根据版本时间）
    hours_threshold = 24    # 时间阈值（小时），如果最新版本时间在阈值内，则跳过抓取
    
    # 如果不用数据库，手动指定股票代码列表
    manual_stock_codes = [
        "603026",  # 石大胜华
    ]
    
    # 测试模式配置
    test_mode = False   # 是否启用测试模式（只抓取第一页的前N个）
    test_limit = 10     # 测试模式下最多抓取的链接数量
    
    # 浏览器配置
    headless = True   # 是否使用无头模式（不显示浏览器界面）
    
    # 延迟配置
    interval = 0     # 统一的请求间隔时间（秒），页面加载固定3秒
    
    logger.info("="*60)
    logger.info("生产者1：按股票代码抓取链接")
    logger.info("="*60)
    
    # 获取股票代码列表
    stock_codes = []
    db_client = None
    
    if use_db:
        logger.info("正在从数据库读取股票代码...")
        db_client = create_clickhouse_client()
        try:
            stock_codes = get_stock_codes_from_db(
                db_client,
                status=status_filter,
                market=market_filter,
                limit=limit_stocks,
                filter_crawled=filter_crawled,
                hours_threshold=hours_threshold
            )
            if not stock_codes:
                logger.warning("未从数据库读取到股票代码，使用手动配置的股票代码")
                stock_codes = manual_stock_codes
        except Exception as e:
            logger.error(f"从数据库读取股票代码失败: {e}，使用手动配置的股票代码")
            stock_codes = manual_stock_codes
        finally:
            if db_client:
                db_client.close()
    else:
        logger.info("使用手动配置的股票代码列表")
        stock_codes = manual_stock_codes
    
    if not stock_codes:
        logger.error("没有可用的股票代码，退出")
        return
    
    logger.info(f"准备抓取 {len(stock_codes)} 个股票的公告链接")
    
    start_time = datetime.now()
    
    # 执行抓取
    results = await produce_by_stock(
        stock_codes=stock_codes,
        headless=headless,
        interval=interval,
        test_mode=test_mode,
        test_limit=test_limit,
        filter_crawled=filter_crawled,
        hours_threshold=hours_threshold
    )
    
    # 统计结果
    total_stocks = len(results)
    total_saved = sum(r.get("saved_count", 0) for r in results.values())
    success_count = sum(1 for r in results.values() if r.get("success", False) and not r.get("skipped", False))
    skipped_count = sum(1 for r in results.values() if r.get("skipped", False))
    failed_count = sum(1 for r in results.values() if not r.get("success", False))
    
    elapsed_time = (datetime.now() - start_time).total_seconds()
    
    logger.info("\n" + "="*60)
    logger.info("抓取完成！")
    logger.info(f"股票数量: {total_stocks}")
    logger.info(f"成功抓取: {success_count}")
    logger.info(f"跳过（已抓取）: {skipped_count}")
    logger.info(f"失败: {failed_count}")
    logger.info(f"保存的新链接总数: {total_saved}")
    logger.info(f"总耗时: {elapsed_time:.1f} 秒")
    logger.info("="*60)


if __name__ == "__main__":
    asyncio.run(main())

