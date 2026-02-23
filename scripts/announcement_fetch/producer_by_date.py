#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
生产者2：按日期范围抓取全部股票链接
- 直接调用东方财富API接口获取公告数据
- 按日期范围收集公告链接
- 写入数据库（只写基础信息，content和attachments留空）
"""

import asyncio
import sys
import logging
import json
import re
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime, date, timedelta
import aiohttp

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from clickhouse_connect import get_client
from clickhouse_connect.driver import Client
from config import config

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - [生产者2] - %(levelname)s - %(message)s',
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


def get_max_announce_date(db_client: Client) -> Optional[date]:
    """
    查询数据库中的最大公告日期
    
    Args:
        db_client: ClickHouse客户端
    
    Returns:
        最大日期，如果没有数据则返回None
    """
    try:
        result = db_client.query(
            "SELECT max(announce_date) as max_date FROM stock_announcement FINAL"
        )
        
        if result.result_rows and result.result_rows[0][0]:
            max_date = result.result_rows[0][0]
            if isinstance(max_date, date):
                return max_date
            elif isinstance(max_date, str):
                return datetime.strptime(max_date, '%Y-%m-%d').date()
            else:
                return max_date
        else:
            return None
    except Exception as e:
        logger.error(f"查询最大日期失败: {e}")
        return None


async def fetch_announcements_by_date(
    session: aiohttp.ClientSession,
    target_date: date,
    page_index: int = 1,
    page_size: int = 50
) -> Dict:
    """
    调用API获取指定日期的公告数据
    
    Args:
        session: aiohttp会话
        target_date: 目标日期
        page_index: 页码（从1开始）
        page_size: 每页数量
    
    Returns:
        API返回的JSON数据
    """
    date_str = target_date.strftime('%Y-%m-%d')
    url = "https://np-anotice-stock.eastmoney.com/api/security/ann"
    
    params = {
        'sr': '-1',  # 排序方式，-1表示倒序
        'page_size': str(page_size),
        'page_index': str(page_index),
        'ann_type': 'SHA,CYB,SZA,BJA,INV',  # 沪深京A股等
        'client_source': 'web',
        'f_node': '0',
        's_node': '0',
        'begin_time': date_str,
        'end_time': date_str
    }
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Referer': 'https://data.eastmoney.com/notices/'
    }
    
    try:
        async with session.get(url, params=params, headers=headers, timeout=aiohttp.ClientTimeout(total=30)) as response:
            if response.status != 200:
                logger.error(f"API请求失败: HTTP {response.status}")
                return {}
            
            # API返回的是JSONP格式，需要提取JSON部分
            text = await response.text()
            
            # 调试：打印前500个字符
            logger.debug(f"API响应前500字符: {text[:500]}")
            
            # 尝试解析JSONP响应
            # 格式类似: jQuery1123046548140674112615_1761982263586({...})
            match = re.search(r'jQuery\d+_\d+\((.*)\);?\s*$', text, re.DOTALL)
            if match:
                json_str = match.group(1)
                try:
                    data = json.loads(json_str)
                    logger.debug(f"成功解析JSONP，数据keys: {list(data.keys()) if isinstance(data, dict) else 'not dict'}")
                    return data
                except json.JSONDecodeError as e:
                    logger.error(f"JSONP解析失败: {e}, JSON片段: {json_str[:200]}")
            else:
                # 如果不是JSONP格式，直接解析JSON
                try:
                    data = json.loads(text)
                    logger.debug(f"成功解析JSON，数据keys: {list(data.keys()) if isinstance(data, dict) else 'not dict'}")
                    return data
                except json.JSONDecodeError as e:
                    logger.error(f"无法解析API响应: {e}, 响应前200字符: {text[:200]}")
                    return {}
    
    except Exception as e:
        logger.error(f"API请求异常: {e}")
        return {}


def parse_announcement_data(api_data: Dict) -> List[Dict]:
    """
    解析API返回的公告数据
    
    Args:
        api_data: API返回的JSON数据
    
    Returns:
        公告链接列表 [{code, title, type, date, detail_url}, ...]
    """
    links = []
    
    logger.debug(f"解析数据，api_data keys: {list(api_data.keys()) if isinstance(api_data, dict) else 'not dict'}")
    
    if not api_data:
        logger.warning("api_data为空")
        return links
    
    if 'data' not in api_data:
        logger.warning(f"api_data中没有'data'字段，keys: {list(api_data.keys())}")
        return links
    
    data = api_data['data']
    logger.debug(f"data keys: {list(data.keys()) if isinstance(data, dict) else 'not dict'}")
    
    if not data:
        logger.warning("data为空")
        return links
    
    if 'list' not in data:
        logger.warning(f"data中没有'list'字段，keys: {list(data.keys())}")
        return links
    
    announcement_list = data['list']
    logger.debug(f"公告列表长度: {len(announcement_list)}")
    
    for item in announcement_list:
        try:
            # 提取字段 - API实际返回的数据结构
            art_code = item.get('art_code', '').strip()  # 公告ID
            title = item.get('title', '').strip()  # 公告标题
            notice_date = item.get('notice_date', '').strip()  # 公告日期
            
            # 从codes数组中提取股票代码
            codes = item.get('codes', [])
            if not codes or len(codes) == 0:
                logger.warning(f"公告没有股票代码: {art_code}")
                continue
            
            code_item = codes[0]  # 取第一个股票代码
            code = code_item.get('stock_code', '').strip()
            
            # 从columns数组中提取公告类型
            columns = item.get('columns', [])
            ann_type = ''
            if columns and len(columns) > 0:
                ann_type = columns[0].get('column_name', '').strip()
            
            # 验证必要字段
            if not code or len(code) != 6:
                logger.warning(f"股票代码格式错误: {code}")
                continue
            
            if not title:
                logger.warning(f"公告标题为空: {art_code}")
                continue
            
            if not notice_date:
                logger.warning(f"公告日期为空: {art_code}")
                continue
            
            # 处理日期格式：从 "2025-10-31 00:00:00" 提取日期部分
            if ' ' in notice_date:
                ann_date = notice_date.split(' ')[0]
            else:
                ann_date = notice_date
            
            # 验证日期格式
            if len(ann_date) != 10 or ann_date[4] != '-' or ann_date[7] != '-':
                logger.warning(f"日期格式错误: {ann_date}")
                continue
            
            # 构建详情URL
            # 格式: /notices/detail/{code}/{art_code}.html
            if art_code and code:
                detail_url = f"https://data.eastmoney.com/notices/detail/{code}/{art_code}.html"
            else:
                logger.warning(f"无法构建URL: code={code}, art_code={art_code}")
                continue
            
            links.append({
                "code": code,
                "title": title,
                "type": ann_type,
                "date": ann_date,
                "detail_url": detail_url
            })
        
        except Exception as e:
            logger.warning(f"解析公告数据失败: {e}, item keys: {list(item.keys()) if isinstance(item, dict) else 'not dict'}")
            continue
    
    return links


def _check_existing_links_sync(db_client: Client, links: List[Dict]) -> List[Dict]:
    """
    检查数据库中已存在的链接，返回需要插入的新链接（同步函数）
    
    Args:
        db_client: ClickHouse客户端
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
            code = link['code']
            
            query = f"""
                SELECT detail_url 
                FROM stock_announcement FINAL
                WHERE code = '{code}' 
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


async def _save_links_to_db(db_client: Client, links: List[Dict]) -> int:
    """
    保存链接到数据库（只写基础字段，content和attachments留空）
    
    Args:
        db_client: ClickHouse客户端
        links: 链接列表
    
    Returns:
        成功保存的数量
    """
    if not links:
        return 0
    
    # 检查已存在的链接，只插入新链接（同步调用，使用线程池）
    new_links = await asyncio.to_thread(_check_existing_links_sync, db_client, links)
    
    if not new_links:
        logger.info(f"所有链接已存在，跳过插入")
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
            link['code'],
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
        logger.info(f"成功保存 {len(batch_data)} 条链接到数据库")
        return len(batch_data)
    except Exception as e:
        logger.error(f"保存到数据库失败: {e}")
        return 0


async def produce_single_date(
    session: aiohttp.ClientSession,
    target_date: date,
    db_client: Client,
    interval: float = 0.5,
    max_pages: Optional[int] = None
) -> int:
    """
    单个日期的生产逻辑
    
    Args:
        session: aiohttp会话
        target_date: 目标日期
        db_client: 数据库客户端
        interval: 请求间隔时间（秒）
        max_pages: 最大抓取页数（None表示不限制，用于测试）
    
    Returns:
        成功保存的链接数量
    """
    date_str = target_date.strftime('%Y-%m-%d')
    logger.info(f"开始抓取 {date_str} 的公告链接")
    if max_pages:
        logger.info(f"测试模式：最多抓取 {max_pages} 页")
    
    total_saved = 0
    page_index = 1
    page_size = 50
    all_links = []
    
    # 遍历所有页面
    while True:
        logger.info(f"正在获取第 {page_index} 页数据...")
        
        # 调用API获取数据
        api_data = await fetch_announcements_by_date(
            session, target_date, page_index=page_index, page_size=page_size
        )
        
        if not api_data:
            logger.warning(f"第 {page_index} 页：API返回空数据")
            break
        
        # 解析数据
        page_links = parse_announcement_data(api_data)
        
        if not page_links:
            logger.info(f"第 {page_index} 页：没有更多数据")
            break
        
        all_links.extend(page_links)
        logger.info(f"第 {page_index} 页：获取到 {len(page_links)} 条公告（累计: {len(all_links)} 条）")
        
        # 打印前3条示例数据（用于验证）
        if page_links and page_index == 1:
            logger.info("示例数据（前3条）：")
            for i, link in enumerate(page_links[:3], 1):
                logger.info(f"  {i}. 代码: {link['code']}, 标题: {link['title'][:50]}..., 类型: {link['type']}, 日期: {link['date']}")
                logger.info(f"     URL: {link['detail_url']}")
        
        # 批量保存到数据库（每页保存一次）
        saved_count = await _save_links_to_db(db_client, page_links)
        total_saved += saved_count
        
        # 检查是否还有下一页
        if 'data' in api_data:
            data = api_data['data']
            total_hits = data.get('total_hits', 0)  # API返回的是total_hits
            current_count = page_index * page_size
            
            logger.debug(f"总数据量: {total_hits}, 当前已获取: {current_count}")
            
            if current_count >= total_hits:
                logger.info(f"已获取所有数据（共 {total_hits} 条）")
                break
            
            # 如果当前页数据量小于page_size，说明已经是最后一页
            if len(page_links) < page_size:
                logger.info(f"当前页数据量({len(page_links)})小于页大小({page_size})，已是最后一页")
                break
        
        # 测试模式：限制页数
        if max_pages and page_index >= max_pages:
            logger.info(f"测试模式：已达到最大页数限制({max_pages}页)，停止抓取")
            break
        
        # 移动到下一页
        page_index += 1
        
        # 避免请求过快
        if interval > 0:
            await asyncio.sleep(interval)
    
    logger.info(f"日期 {date_str}：链接收集完成！共收集到 {len(all_links)} 条链接，成功保存 {total_saved} 条新链接")
    return total_saved


async def produce_by_date(start_date: str, end_date: str, interval: float = 0.5, max_pages: Optional[int] = None) -> Dict:
    """
    按日期范围抓取全部股票链接（主函数）
    
    Args:
        start_date: 开始日期（YYYY-MM-DD）
        end_date: 结束日期（YYYY-MM-DD）
        interval: 请求间隔时间（秒）
        max_pages: 最大抓取页数（None表示不限制，用于测试）
    
    Returns:
        包含每个日期抓取结果的字典
    """
    logger.info(f"开始按日期范围抓取公告链接")
    logger.info(f"日期范围: {start_date} 至 {end_date}")
    
    # 解析日期
    try:
        start = datetime.strptime(start_date, '%Y-%m-%d').date()
        end = datetime.strptime(end_date, '%Y-%m-%d').date()
    except ValueError as e:
        logger.error(f"日期格式错误: {e}")
        return {}
    
    if start > end:
        logger.error(f"开始日期不能晚于结束日期")
        return {}
    
    results = {}
    db_client = None
    
    try:
        # 创建数据库连接
        logger.info("正在连接ClickHouse数据库...")
        db_client = create_clickhouse_client()
        logger.info("数据库连接成功")
        
        # 创建HTTP会话
        async with aiohttp.ClientSession() as session:
            # 遍历日期范围
            current_date = start
            date_count = 0
            
            while current_date <= end:
                date_count += 1
                date_str = current_date.strftime('%Y-%m-%d')
                
                logger.info(f"\n{'='*60}")
                logger.info(f"[日期 {date_count}] 正在处理日期: {date_str}")
                logger.info(f"{'='*60}")
                
                try:
                    saved_count = await produce_single_date(
                        session, current_date, db_client, interval=interval, max_pages=max_pages
                    )
                    results[date_str] = {
                        "success": True,
                        "saved_count": saved_count
                    }
                    logger.info(f"[日期 {date_count}] ✅ 日期 {date_str} 抓取成功，保存 {saved_count} 条新链接")
                except Exception as e:
                    logger.error(f"[日期 {date_count}] ❌ 日期 {date_str} 抓取失败: {e}", exc_info=True)
                    results[date_str] = {
                        "success": False,
                        "error": str(e),
                        "saved_count": 0
                    }
                
                # 移动到下一个日期
                current_date += timedelta(days=1)
                
                # 避免请求过快
                if current_date <= end and interval > 0:
                    logger.info(f"等待{interval}秒后处理下一个日期...")
                    await asyncio.sleep(interval)
    
    finally:
        if db_client:
            db_client.close()
            logger.info("数据库连接已关闭")
    
    return results


async def main():
    """主函数：独立运行入口（增量抓取模式）"""
    # 延迟配置
    interval = 0.5  # 请求间隔时间（秒）
    
    # 测试模式配置
    test_mode = True  # 是否启用测试模式（只抓取前N页）
    max_pages = 2      # 测试模式下最多抓取的页数
    
    logger.info("="*60)
    logger.info("生产者2：按日期范围抓取链接（增量抓取模式）")
    logger.info("="*60)
    
    # 连接数据库，查询最大日期
    db_client = None
    try:
        logger.info("正在连接ClickHouse数据库...")
        db_client = create_clickhouse_client()
        logger.info("数据库连接成功")
        
        # 查询数据库中的最大日期
        max_date = get_max_announce_date(db_client)
        current_date = datetime.now().date()
        
        if max_date:
            logger.info(f"数据库中的最大公告日期: {max_date}")
            logger.info(f"当前日期: {current_date}")
            
            # 计算日期差
            days_diff = (current_date - max_date).days
            
            if days_diff <= 0:
                logger.info(f"数据库已是最新，无需抓取（最大日期: {max_date}, 当前日期: {current_date}）")
                return
            
            # 从最大日期的下一天开始抓取
            start_date = max_date + timedelta(days=1)
            end_date = current_date
            
            logger.info(f"需要补齐 {days_diff} 天的数据")
            logger.info(f"抓取日期范围: {start_date} 至 {end_date}")
        else:
            # 如果没有数据，从当前日期往前推7天开始抓取（可配置）
            default_days_back = 7
            logger.warning("数据库中暂无数据，使用默认日期范围")
            end_date = current_date
            start_date = current_date - timedelta(days=default_days_back)
            logger.info(f"默认抓取日期范围: {start_date} 至 {end_date}（最近{default_days_back}天）")
        
        if test_mode:
            logger.info(f"⚠️  测试模式：最多抓取 {max_pages} 页")
        
        start_time = datetime.now()
        
        # 执行抓取
        results = await produce_by_date(
            start_date=start_date.strftime('%Y-%m-%d'),
            end_date=end_date.strftime('%Y-%m-%d'),
            interval=interval,
            max_pages=max_pages if test_mode else None
        )
        
        # 统计结果
        total_dates = len(results)
        total_saved = sum(r.get("saved_count", 0) for r in results.values())
        success_count = sum(1 for r in results.values() if r.get("success", False))
        failed_count = sum(1 for r in results.values() if not r.get("success", False))
        
        elapsed_time = (datetime.now() - start_time).total_seconds()
        
        logger.info("\n" + "="*60)
        logger.info("抓取完成！")
        logger.info(f"日期数量: {total_dates}")
        logger.info(f"成功抓取: {success_count}")
        logger.info(f"失败: {failed_count}")
        logger.info(f"保存的新链接总数: {total_saved}")
        logger.info(f"总耗时: {elapsed_time:.1f} 秒")
        logger.info("="*60)
    
    finally:
        if db_client:
            db_client.close()
            logger.info("数据库连接已关闭")


if __name__ == "__main__":
    asyncio.run(main())
