#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
消费者：从数据库读取未完成的记录，抓取详情并更新
- 查询数据库（content为空或attachments为空）
- 并发抓取详情（10个worker）
- 更新数据库（填充content和attachments）
"""

import asyncio
import sys
import logging
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from datetime import datetime, date
from playwright.async_api import async_playwright, Page, BrowserContext

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from clickhouse_connect import get_client
from clickhouse_connect.driver import Client
from config import config

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - [消费者] - %(levelname)s - %(message)s',
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


async def fetch_single_detail(page: Page, detail_url: str, interval: float = 0.5) -> Tuple[str, List[Dict]]:
    """
    抓取公告详情页内容
    
    Args:
        page: Playwright 页面对象
        detail_url: 公告详情页URL
        interval: 请求间隔时间（秒）
    
    Returns:
        (内容文本, 附件列表)
    """
    # 访问详情页
    if not await safe_goto(page, detail_url, max_retries=2, timeout=30000):
        return "", []  # 如果访问失败，返回空内容
    
    await wait_for_dom_or_sleep(page, interval)  # 等待内容加载
    
    content = ""
    attachments = []
    
    try:
        # 提取PDF附件链接
        try:
            pdf_links = page.locator("a:has-text('查看PDF原文'), a:has-text('[点击查看PDF原文]')")
            pdf_count = await pdf_links.count()
            
            if pdf_count > 0:
                pdf_urls = set()  # 使用set去重
                
                for i in range(pdf_count):
                    link = pdf_links.nth(i)
                    href = await link.get_attribute("href")
                    text = await link.inner_text()
                    text = text.strip() if text else ""
                    
                    if href and "pdf.dfcfw.com" in href:
                        # 如果URL不完整，补全
                        if not href.startswith("http"):
                            href = f"https:{href}" if href.startswith("//") else f"https://{href}"
                        
                        if href not in pdf_urls:
                            pdf_urls.add(href)
                            attachments.append({
                                "name": text or "查看PDF原文",
                                "url": href
                            })
        except Exception as e:
            logger.debug(f"提取PDF附件失败: {e}")
        
        # 提取公告正文内容
        # 使用 div#notice_content 选择器
        try:
            notice_content_element = page.locator("#notice_content")
            count = await notice_content_element.count()
            
            if count > 0:
                content = await notice_content_element.first.inner_text()
                content = content.strip() if content else ""
        except Exception as e:
            logger.debug(f"提取正文内容失败: {e}")
        
    except Exception as e:
        logger.debug(f"提取内容失败: {e}")
    
    return content, attachments


def _get_unfinished_records(db_client: Client, batch_size: int) -> List[Dict]:
    """
    查询未完成记录（同步函数，用于数据库查询）
    
    Args:
        db_client: ClickHouse客户端
        batch_size: 批量大小
    
    Returns:
        记录列表
    """
    try:
        query = f"""
            SELECT code, announce_date, title, type, detail_url
            FROM stock_announcement FINAL
            WHERE empty(content) OR empty(attachments)
            LIMIT {batch_size}
        """
        
        result = db_client.query(query)
        records = []
        
        for row in result.result_rows:
            records.append({
                'code': row[0],
                'announce_date': row[1],
                'title': row[2],
                'type': row[3],
                'detail_url': row[4]
            })
        
        return records
    except Exception as e:
        logger.error(f"查询未完成记录失败: {e}")
        return []


def _update_record_detail(db_client: Client, code: str, announce_date: str, 
                          detail_url: str, content: str, attachments: str) -> bool:
    """
    更新记录的详情（同步函数，用于数据库更新）
    
    注意：使用ReplacingMergeTree后，更新策略改为插入新记录（带新的version）
    ReplacingMergeTree会自动保留version最大的记录，实现去重
    
    Args:
        db_client: ClickHouse客户端
        code: 股票代码
        announce_date: 公告日期
        detail_url: 详情页URL
        content: 公告内容
        attachments: 附件URL（JSON字符串或第一个URL）
    
    Returns:
        bool: 更新是否成功
    """
    try:
        # 转义单引号
        content_escaped = content.replace("'", "''")
        attachments_escaped = attachments.replace("'", "''")
        detail_url_escaped = detail_url.replace("'", "''")
        
        # 先查询原记录的基础信息
        query_select = f"""
            SELECT code, announce_date, title, type, detail_url
            FROM stock_announcement FINAL
            WHERE code = '{code}'
              AND announce_date = '{announce_date}'
              AND detail_url = '{detail_url_escaped}'
            LIMIT 1
        """
        
        result = db_client.query(query_select)
        if not result.result_rows:
            logger.warning(f"未找到原记录，无法更新: {code} - {announce_date}")
            return False
        
        # 获取原记录的基础信息
        row = result.result_rows[0]
        # 从查询结果中获取date对象（确保类型正确）
        announce_date_obj = row[1]  # 已经是date对象
        title = str(row[2])
        ann_type = str(row[3])
        
        # 如果announce_date_obj是字符串，转换为date对象
        if isinstance(announce_date_obj, str):
            announce_date_obj = datetime.strptime(announce_date_obj, '%Y-%m-%d').date()
        elif not isinstance(announce_date_obj, date):
            # 如果是其他类型，尝试转换
            announce_date_obj = datetime.strptime(str(announce_date), '%Y-%m-%d').date()
        
        # 插入新记录（带更新的content和attachments）
        # 使用列式插入（批量插入），性能更好
        # version字段使用数据库默认值now()，确保ReplacingMergeTree去重时使用正确的版本时间
        batch_data = [[
            code,
            announce_date_obj,  # 使用date对象而不是字符串
            title,
            ann_type,
            detail_url,
            content,
            attachments
        ]]
        
        db_client.insert(
            table='stock_announcement',
            data=batch_data,
            column_names=[
                'code', 'announce_date', 'title', 'type',
                'detail_url', 'content', 'attachments'
            ]
        )
        logger.debug(f"更新成功: {code} - {announce_date}")
        return True
    except Exception as e:
        logger.error(f"更新记录失败 {code} - {announce_date}: {e}")
        return False


async def _fetch_and_update_single(page: Page, record: Dict, db_client: Client, interval: float = 0.5):
    """
    抓取并更新单条记录
    
    Args:
        page: Playwright 页面对象
        record: 数据库记录
        db_client: 数据库客户端
        interval: 请求间隔时间（秒）
    
    注意：只有抓取成功时才会更新数据库，失败时不更新（保持未完成状态，避免覆盖版本）
    """
    code = record['code']
    announce_date = str(record['announce_date'])
    detail_url = record['detail_url']
    title = record.get('title', '')[:50]
    
    try:
        logger.info(f"正在抓取: {code} - {title}...")
        
        # 抓取详情
        content, attachments_list = await fetch_single_detail(page, detail_url, interval=interval)
        
        # 检查是否至少抓取到内容（有些公告没有PDF，只有正文）
        if not content or len(content.strip()) == 0:
            logger.warning(f"⚠️ 未抓取到内容，视为失败: {code} - {title}，不更新数据库")
            return  # 没有内容，不更新数据库，保持未完成状态
        
        # 处理附件：取第一个附件的URL，如果没有则为空字符串
        attachment_url = ""
        if attachments_list and len(attachments_list) > 0:
            attachment_url = attachments_list[0].get('url', '')
        
        # 只有抓取成功时才更新数据库（至少要有内容）
        # 使用 asyncio.to_thread 在线程池中执行同步数据库操作
        try:
            update_success = await asyncio.to_thread(
                _update_record_detail, 
                db_client, code, announce_date, detail_url, content, attachment_url
            )
            
            if update_success:
                logger.info(f"✅ 抓取成功并已更新数据库: {code} - 内容长度: {len(content)} 字符, PDF附件: {len(attachments_list)} 个")
            else:
                logger.error(f"抓取成功但数据库更新失败: {code} - {announce_date}")
        except Exception as e:
            logger.error(f"数据库更新异常 {code} - {announce_date}: {e}")
            # 数据库更新失败不影响抓取成功的日志记录
        
    except Exception as e:
        # 抓取失败时，不更新数据库（保持未完成状态，可以重新抓取）
        # 这样不会覆盖数据库中的版本信息
        logger.error(f"❌ 抓取失败 {code} - {title}: {e}，不更新数据库")


async def _consume_worker(worker_id: int, queue: asyncio.Queue, 
                          page: Page, interval: float):
    """
    单个消费者worker
    
    Args:
        worker_id: Worker ID
        queue: 记录队列
        page: 页面对象
        interval: 请求间隔时间（秒）
    
    注意：每个worker会创建独立的ClickHouse客户端实例，避免并发查询冲突
    """
    processed_count = 0
    db_client = None
    
    try:
        # 为每个worker创建独立的ClickHouse客户端实例
        logger.debug(f"Worker {worker_id}: 正在创建ClickHouse客户端...")
        db_client = create_clickhouse_client()
        logger.debug(f"Worker {worker_id}: ClickHouse客户端创建成功")
        
        while True:
            record = None
            try:
                # 从队列取记录
                record = await queue.get()
                
                # 检查结束标记
                if record is None:
                    logger.info(f"Worker {worker_id}: 收到结束标记，退出")
                    break
                
                # 处理记录（内部已有异常处理，确保不会影响其他记录）
                await _fetch_and_update_single(page, record, db_client, interval=interval)
                processed_count += 1
                
            except Exception as e:
                # 处理单条记录时的异常，不影响继续处理其他记录
                logger.error(f"Worker {worker_id} 处理单条记录异常: {e}")
            finally:
                # 确保任务标记为完成，避免队列阻塞
                if record is not None:
                    queue.task_done()
        
        logger.info(f"Worker {worker_id}: 处理完成，共处理 {processed_count} 条记录")
    except Exception as e:
        # 捕获worker级别的异常（比如队列操作异常等）
        logger.error(f"Worker {worker_id} 发生严重异常: {e}", exc_info=True)
        raise  # 重新抛出，让 asyncio.gather 的 return_exceptions=True 处理
    finally:
        # 确保关闭worker的数据库客户端
        if db_client:
            try:
                db_client.close()
                logger.debug(f"Worker {worker_id}: ClickHouse客户端已关闭")
            except Exception as e:
                logger.warning(f"Worker {worker_id}: 关闭ClickHouse客户端时出错: {e}")


async def _process_batch(records: List[Dict], context: BrowserContext, 
                         max_workers: int, interval: float):
    """
    处理一批记录
    
    Args:
        records: 记录列表
        context: 浏览器上下文
        max_workers: Worker数量
        interval: 请求间隔时间（秒）
    
    注意：每个worker会创建独立的ClickHouse客户端实例，避免并发查询冲突
    """
    if not records:
        return
    
    # 创建队列
    queue = asyncio.Queue()
    
    # 将所有记录放入队列
    for record in records:
        await queue.put(record)
    
    # 添加结束标记
    for _ in range(max_workers):
        await queue.put(None)
    
    # 创建多个page和worker
    pages = []
    tasks = []
    
    for i in range(max_workers):
        page = await context.new_page()
        pages.append(page)
        task = asyncio.create_task(
            _consume_worker(i + 1, queue, page, interval)
        )
        tasks.append(task)
    
    # 等待所有worker完成
    # 使用 return_exceptions=True 确保某个worker失败时不影响其他worker
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    # 检查是否有worker异常
    for i, result in enumerate(results):
        if isinstance(result, Exception):
            logger.error(f"Worker {i + 1} 执行异常: {result}")
    
    # 关闭所有page
    for page in pages:
        await page.close()


async def consume_from_db(max_workers: int = 10, batch_size: int = 100, 
                          headless: bool = False, interval: float = 0.5):
    """
    从数据库读取未完成的记录，抓取详情并更新（主函数）
    
    Args:
        max_workers: Worker数量
        batch_size: 批量大小
        headless: 是否使用无头模式
        interval: 请求间隔时间（秒）
    
    注意：使用独立的数据库客户端进行查询，每个worker会创建自己的客户端实例
    """
    logger.info("="*60)
    logger.info("消费者：开始从数据库读取未完成记录并抓取详情")
    logger.info(f"Worker数量: {max_workers}")
    logger.info(f"批量大小: {batch_size}")
    logger.info("="*60)
    
    query_client = None
    
    try:
        # 创建用于查询的数据库连接（仅用于查询未完成记录）
        logger.info("正在连接ClickHouse数据库（查询用）...")
        query_client = create_clickhouse_client()
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
                total_processed = 0
                batch_num = 0
                
                # 循环查询并处理
                while True:
                    batch_num += 1
                    logger.info(f"\n处理第 {batch_num} 批记录...")
                    
                    # 查询未完成记录（同步调用，使用线程池）
                    records = await asyncio.to_thread(_get_unfinished_records, query_client, batch_size)
                    
                    if not records:
                        logger.info("没有更多未完成的记录，退出")
                        break
                    
                    logger.info(f"查询到 {len(records)} 条未完成记录")
                    
                    # 处理这批记录（每个worker会创建独立的数据库客户端）
                    await _process_batch(records, context, max_workers, interval)
                    
                    total_processed += len(records)
                    logger.info(f"第 {batch_num} 批处理完成，累计处理 {total_processed} 条记录")
                    
                    # 短暂延迟，避免查询过快
                    await asyncio.sleep(1)
            
            finally:
                logger.info("正在关闭浏览器...")
                await browser.close()
                logger.info("浏览器已关闭")
    
    finally:
        if query_client:
            query_client.close()
            logger.info("查询用数据库连接已关闭")
    
    logger.info("\n" + "="*60)
    logger.info(f"消费者处理完成！共处理 {total_processed} 条记录")
    logger.info("="*60)


async def main():
    """主函数：独立运行入口"""
    # 配置参数
    max_workers = 10      # Worker数量
    batch_size = 100      # 批量大小
    headless = True      # 是否使用无头模式
    interval = 1          # 请求间隔时间（秒）
    
    logger.info("="*60)
    logger.info("消费者：开始运行")
    logger.info("="*60)
    
    # 执行消费
    await consume_from_db(
        max_workers=max_workers,
        batch_size=batch_size,
        headless=headless,
        interval=interval
    )


if __name__ == "__main__":
    asyncio.run(main())

