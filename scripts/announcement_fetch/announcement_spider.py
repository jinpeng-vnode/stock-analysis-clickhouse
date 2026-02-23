#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
股票公告爬虫 - 使用 Playwright 抓取东方财富网公告
"""

import json
import time
import sys
from pathlib import Path
from typing import List, Dict, Optional
from playwright.sync_api import sync_playwright, Page, Browser, BrowserContext
from datetime import datetime, date
import threading

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from clickhouse_connect import get_client
from clickhouse_connect.driver import Client
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


def save_announcements_to_db(client: Client, code: str, announcements: List[Dict]) -> int:
    """
    将公告数据保存到ClickHouse数据库
    
    Args:
        client: ClickHouse客户端
        code: 股票代码
        announcements: 公告列表
    
    Returns:
        成功保存的数量
    """
    if not announcements:
        return 0
    
    # 准备批量数据
    batch_data = []
    for ann in announcements:
        # 解析日期字符串为date对象
        try:
            ann_date = datetime.strptime(ann['date'], '%Y-%m-%d').date()
        except:
            print(f"  ⚠️  日期格式错误: {ann['date']}，跳过该公告")
            continue
        
        # 从attachments列表中取第一个PDF链接URL，如果没有则为空字符串
        attachments_list = ann.get('attachments', [])
        attachment_url = ""
        if attachments_list and len(attachments_list) > 0:
            # 取第一个附件的URL
            attachment_url = attachments_list[0].get('url', '')
        
        batch_data.append([
            code,
            ann_date,
            ann.get('title', ''),
            ann.get('type', ''),
            ann.get('detail_url', ''),
            ann.get('content', ''),
            attachment_url
        ])
    
    if not batch_data:
        return 0
    
    # 批量插入数据库
    try:
        client.insert(
            table='stock_announcement',
            data=batch_data,
            column_names=[
                'code', 'announce_date', 'title', 'type',
                'detail_url', 'content', 'attachments'
            ]
        )
        print(f"  ✅ 成功保存 {len(batch_data)} 条公告到数据库")
        return len(batch_data)
    except Exception as e:
        print(f"  ❌ 保存到数据库失败: {e}")
        return 0


def safe_goto(page: Page, url: str, max_retries: int = 3, timeout: int = 60000) -> bool:
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
            response = page.goto(url, wait_until="domcontentloaded", timeout=timeout)
            if response and response.status >= 400:
                raise Exception(f"HTTP {response.status}")
            # 等待页面基本加载完成
            page.wait_for_load_state("domcontentloaded", timeout=5000)
            return True
        except Exception as e:
            if attempt < max_retries:
                wait_time = attempt * 2  # 递增等待时间
                print(f"  ⚠️  第 {attempt} 次导航失败，{wait_time} 秒后重试... ({e})")
                time.sleep(wait_time)
            else:
                print(f"  ❌ 导航失败，已重试 {max_retries} 次: {e}")
                return False
    return False

def wait_for_dom_or_sleep(page: Page, interval: float, timeout: int = 10000):
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
            page.wait_for_load_state("load", timeout=timeout)
        except Exception as e:
            print(f"  ⚠️  等待load状态超时: {e}")
    else:
        time.sleep(interval)

def get_stock_announcements(context: BrowserContext, code: str, test_mode: bool = False, test_limit: int = 5, interval: float = 0.5, max_workers: int = 10) -> Dict:
    """
    抓取单个股票的所有公告
    
    分为两个阶段：
    1. 第一阶段：遍历所有页面，收集所有公告链接
    2. 第二阶段：使用多个标签页并行访问详情页，抓取内容和PDF
    
    Args:
        context: Playwright 浏览器上下文对象
        code: 股票代码（6位数字）
        test_mode: 是否启用测试模式（只抓取第一页的前N个）
        test_limit: 测试模式下最多抓取的公告数量
        interval: 统一的请求间隔时间（秒），页面加载固定3秒
        max_workers: 并行抓取详情页的标签页数量（默认10个）
    
    Returns:
        包含股票公告信息的字典
    """
    url = f"https://data.eastmoney.com/notices/stock/{code}.html"
    
    print(f"\n{'='*60}")
    print(f"📊 开始抓取股票 {code} 的公告")
    print(f"{'='*60}")
    
    # 创建用于列表页的页面
    page = context.new_page()
    
    try:
        # 访问公告列表页
        print(f"[步骤1] 正在访问列表页: {url}")
        if not safe_goto(page, url, max_retries=3, timeout=60000):
            raise Exception(f"无法访问页面: {url}")
        
        wait_for_dom_or_sleep(page, 3 if interval == 0 else interval)  # 等待页面渲染
        print(f"[步骤1] ✅ 列表页加载完成")
        
        # 获取股票名称
        stock_name = ""
        try:
            name_element = page.locator("h1, .stock-name, .title").first
            if name_element.count() > 0:
                stock_name = name_element.inner_text().strip()
            else:
                # 尝试从页面标题提取
                title = page.title()
                if "公告" in title:
                    stock_name = title.split("公告")[0].strip()
            print(f"[步骤1] 股票名称: {stock_name}")
        except Exception as e:
            print(f"[步骤1] ⚠️  获取股票名称失败: {e}")
        
        # ========== 第一阶段：收集所有公告链接 ==========
        print(f"\n[阶段1] 开始收集所有公告链接...")
        announcement_links = []
        page_num = 1
        
        while True:
            print(f"[阶段1-页面{page_num}] 正在解析第 {page_num} 页...")
            
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
                    page.wait_for_selector(selector, timeout=5000)
                    table_loaded = True
                    break
                except:
                    continue
            
            if not table_loaded:
                print(f"[阶段1-页面{page_num}] ⚠️  等待表格加载超时，尝试继续...")
                wait_for_dom_or_sleep(page, interval)
            
            # 提取当前页的公告列表
            rows = page.locator("table tbody tr")
            row_count = rows.count()
            
            if row_count == 0:
                print(f"[阶段1-页面{page_num}] ⚠️  第 {page_num} 页没有数据")
                break
            
            valid_count = 0
            
            # 遍历每一行
            for i in range(row_count):
                try:
                    row = rows.nth(i)
                    cells = row.locator("td")
                    cell_count = cells.count()
                    
                    # 公告行应该有3列：标题、类型、日期
                    if cell_count < 3:
                        continue
                    
                    # 提取各列数据
                    title_cell = cells.nth(0)  # 公告标题列
                    type_cell = cells.nth(1)   # 公告类型列
                    date_cell = cells.nth(2)   # 公告日期列
                    
                    # 获取标题和链接
                    title_link = title_cell.locator("a").first
                    if title_link.count() == 0:
                        continue
                    
                    title = title_link.inner_text().strip()
                    detail_url = title_link.get_attribute("href")
                    
                    # 验证日期格式
                    ann_date = date_cell.inner_text().strip()
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
                    
                    ann_type = type_cell.inner_text().strip()
                    
                    # 保存链接信息（暂时不访问详情页）
                    announcement_links.append({
                        "title": title,
                        "type": ann_type,
                        "date": ann_date,
                        "detail_url": detail_url
                    })
                    
                    valid_count += 1
                    
                    # 测试模式：只抓取第一页的前N个
                    if test_mode and page_num == 1 and len(announcement_links) >= test_limit:
                        print(f"[阶段1-页面{page_num}] 🧪 测试模式：已收集{test_limit}个公告，停止收集")
                        break
                    
                except Exception as e:
                    print(f"[阶段1-页面{page_num}] ⚠️  处理第 {i+1} 行失败: {e}")
                    continue
            
            print(f"[阶段1-页面{page_num}] ✅ 本页收集到 {valid_count} 条公告链接（累计: {len(announcement_links)} 条）")
            
            # 测试模式：第一页收集完N个后不再翻页
            if test_mode and page_num == 1 and len(announcement_links) >= test_limit:
                print(f"[阶段1] 🧪 测试模式：已收集{test_limit}个公告，跳过后续页面")
                break
            
            # 尝试翻页
            try:
                can_go_next = page.evaluate("""
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
                    clicked = page.evaluate("""
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
                    
                    if clicked:
                        wait_for_dom_or_sleep(page, interval)
                        page_num += 1
                        print(f"[阶段1-页面{page_num-1}] 📄 翻页成功，准备解析第 {page_num} 页...")
                    else:
                        print(f"[阶段1] ✅ 无法点击下一页，链接收集完成")
                        break
                else:
                    print(f"[阶段1] ✅ 已到最后一页，链接收集完成")
                    break
            except Exception as e:
                print(f"[阶段1] ⚠️  翻页处理失败: {e}")
                break
        
        print(f"\n[阶段1] ✅ 链接收集完成！共收集到 {len(announcement_links)} 条公告链接\n")
    
    finally:
        # 关闭列表页
        page.close()
    
    # ========== 第二阶段：使用多标签页并行访问详情页 ==========
    print(f"[阶段2] 开始使用 {max_workers} 个标签页并行抓取详情页...")
    
    # 预先创建多个page
    pages = []
    for i in range(max_workers):
        try:
            page = context.new_page()
            pages.append(page)
        except Exception as e:
            print(f"[阶段2] ⚠️  创建标签页 {i+1} 失败: {e}")
            break
    
    if not pages:
        raise Exception("无法创建任何标签页")
    
    print(f"[阶段2] ✅ 成功创建 {len(pages)} 个标签页")
    
    # 将任务分配给各个page（轮询分配）
    page_tasks = [[] for _ in range(len(pages))]
    for idx, link_info in enumerate(announcement_links):
        page_idx = idx % len(pages)
        page_tasks[page_idx].append((idx, link_info))
    
    # 创建结果列表，用于存储每个链接的抓取结果（保持顺序）
    announcements = [None] * len(announcement_links)
    completed_count = 0
    
    # 在主线程中顺序处理各个page的任务
    # 虽然看起来是串行的，但多个page可以复用，减少创建开销
    for page_idx, tasks in enumerate(page_tasks):
        if not tasks:
            continue
        
        page = pages[page_idx]
        for idx, link_info in tasks:
            detail_url = link_info["detail_url"]
            title = link_info["title"]
            
            try:
                print(f"[阶段2-{idx+1}/{len(announcement_links)}] 标签页[{page_idx+1}] 正在访问: {title[:50]}...")
                
                content = ""
                attachments = []
                
                if detail_url:
                    try:
                        content, attachments = get_announcement_detail(page, detail_url, interval=interval)
                        print(f"[阶段2-{idx+1}/{len(announcement_links)}] ✅ 抓取成功 - 内容长度: {len(content)} 字符, PDF附件: {len(attachments)} 个")
                    except Exception as e:
                        print(f"[阶段2-{idx+1}/{len(announcement_links)}] ⚠️  抓取失败: {e}")
                
                announcement = {
                    "title": link_info["title"],
                    "type": link_info["type"],
                    "date": link_info["date"],
                    "detail_url": detail_url,
                    "content": content,
                    "attachments": attachments
                }
                
                announcements[idx] = announcement
                completed_count += 1
                
                # 更新进度
                if completed_count % 10 == 0 or completed_count == len(announcement_links):
                    print(f"[阶段2] 进度: {completed_count}/{len(announcement_links)} ({completed_count*100//len(announcement_links)}%)")
            
            except Exception as e:
                print(f"[阶段2-{idx+1}/{len(announcement_links)}] ⚠️  处理异常: {e}")
                # 即使失败也创建一个空结果
                announcements[idx] = {
                    "title": link_info["title"],
                    "type": link_info["type"],
                    "date": link_info["date"],
                    "detail_url": detail_url,
                    "content": "",
                    "attachments": []
                }
                completed_count += 1
    
    # 关闭所有page
    for page in pages:
        try:
            page.close()
        except:
            pass
    
    # 过滤掉None值（理论上不应该有，但为了安全）
    announcements = [ann for ann in announcements if ann is not None]
    
    print(f"\n[阶段2] ✅ 详情页抓取完成！共抓取 {len(announcements)} 条公告详情\n")
    
    result = {
        "code": code,
        "name": stock_name,
        "total": len(announcements),
        "announcements": announcements
    }
    
    print(f"{'='*60}")
    print(f"✅ 股票 {code} ({stock_name}) 抓取完成！")
    print(f"   总公告数: {len(announcements)} 条")
    print(f"{'='*60}\n")
    
    return result


def get_announcement_detail(page: Page, detail_url: str, interval: float = 0.5) -> tuple:
    """
    抓取公告详情页内容
    
    Args:
        page: Playwright 页面对象
        detail_url: 公告详情页URL
        interval: 统一的请求间隔时间（秒），页面加载固定3秒
    
    Returns:
        (内容文本, 附件列表)
    """
    # 访问详情页
    if not safe_goto(page, detail_url, max_retries=2, timeout=30000):
        return "", []  # 如果访问失败，返回空内容
    
    wait_for_dom_or_sleep(page, interval)  # 等待内容加载
    
    content = ""
    attachments = []
    
    try:
        # 提取PDF附件链接
        try:
            pdf_links = page.locator("a:has-text('查看PDF原文'), a:has-text('[点击查看PDF原文]')")
            pdf_count = pdf_links.count()
            
            if pdf_count > 0:
                pdf_urls = set()  # 使用set去重
                
                for i in range(pdf_count):
                    link = pdf_links.nth(i)
                    href = link.get_attribute("href")
                    text = link.inner_text().strip()
                    
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
            pass
        
        # 提取公告正文内容
        # 使用JavaScript提取正文区域的内容（更可靠）
        try:
            content = page.evaluate("""
                () => {
                    // 查找包含公告正文的div（通常在标题和分页之间）
                    const divs = Array.from(document.querySelectorAll('div'));
                    let bestDiv = null;
                    let maxTextLength = 0;
                    
                    for (let div of divs) {
                        const text = div.innerText || '';
                        // 正文应该包含较长的文本，且不包含导航、页脚等内容
                        if (text.length > 500 && 
                            !text.includes('登录') && 
                            !text.includes('注册') &&
                            !text.includes('网友评论') &&
                            !text.includes('郑重声明') &&
                            !text.includes('数据来源') &&
                            !text.includes('版权所有')) {
                            if (text.length > maxTextLength) {
                                maxTextLength = text.length;
                                bestDiv = div;
                            }
                        }
                    }
                    
                    return bestDiv ? bestDiv.innerText.trim() : '';
                }
            """)
        except Exception as e:
            pass
        
        # 如果JavaScript方法失败，尝试使用选择器
        if not content or len(content) < 100:
            content_selectors = [
                ".notice-content",
                ".content",
                "#noticeContent",
                ".detail-content",
                "article",
                ".main-content"
            ]
            
            for selector in content_selectors:
                try:
                    content_elements = page.locator(selector)
                    max_length = 0
                    best_content = ""
                    
                    for i in range(min(content_elements.count(), 5)):
                        element = content_elements.nth(i)
                        text = element.inner_text().strip()
                        if len(text) > max_length and len(text) > 100:
                            max_length = len(text)
                            best_content = text
                    
                    if best_content:
                        content = best_content
                        break
                except:
                    continue
        
    except Exception as e:
        pass
    
    return content, attachments


def crawl_announcements(stock_codes: List[str], test_mode: bool = False, test_limit: int = 5, headless: bool = False, interval: float = 0.5, max_workers: int = 10) -> Dict:
    """
    抓取多个股票的公告
    
    Args:
        stock_codes: 股票代码列表
        test_mode: 是否启用测试模式（只抓取第一页的前N个）
        test_limit: 测试模式下最多抓取的公告数量
        headless: 是否使用无头模式（不显示浏览器界面）
        interval: 统一的请求间隔时间（秒），页面加载固定3秒
        max_workers: 并行抓取详情页的标签页数量（默认10个）
    
    Returns:
        包含所有股票公告的字典
    """
    print(f"\n{'#'*60}")
    print(f"🚀 开始批量抓取股票公告")
    print(f"   股票数量: {len(stock_codes)}")
    print(f"   股票代码: {', '.join(stock_codes)}")
    print(f"{'#'*60}\n")
    
    results = {}
    
    with sync_playwright() as p:
        # 启动浏览器
        print(f"[初始化] 正在启动浏览器...")
        browser = p.chromium.launch(headless=headless)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            viewport={"width": 1920, "height": 1080},
            ignore_https_errors=True
        )
        print(f"[初始化] ✅ 浏览器启动成功\n")
        
        try:
            for idx, code in enumerate(stock_codes, 1):
                # 确保代码是6位
                code = str(code).strip().zfill(6)
                
                print(f"\n{'#'*60}")
                print(f"[股票 {idx}/{len(stock_codes)}] 正在处理股票代码: {code}")
                print(f"{'#'*60}")
                
                try:
                    result = get_stock_announcements(context, code, test_mode=test_mode, test_limit=test_limit, interval=interval, max_workers=max_workers)
                    results[code] = result
                    print(f"[股票 {idx}/{len(stock_codes)}] ✅ 股票 {code} 抓取成功")
                except Exception as e:
                    print(f"[股票 {idx}/{len(stock_codes)}] ❌ 股票 {code} 抓取失败: {e}\n")
                    results[code] = {
                        "code": code,
                        "name": "",
                        "total": 0,
                        "announcements": [],
                        "error": str(e)
                    }
                
                # 避免请求过快
                if idx < len(stock_codes):
                    print(f"[等待] 等待{interval}秒后处理下一个股票...\n")
                    if interval > 0:
                        time.sleep(interval)
        
        finally:
            print(f"\n[清理] 正在关闭浏览器...")
            browser.close()
            print(f"[清理] ✅ 浏览器已关闭\n")
    
    return results


def generate_markdown(results: Dict) -> str:
    """
    生成 Markdown 格式的内容
    
    Args:
        results: 抓取结果字典
    
    Returns:
        Markdown 格式的字符串
    """
    md_lines = []
    
    # 标题
    md_lines.append("# 股票公告抓取结果\n")
    md_lines.append(f"**抓取时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    # 统计信息
    total_stocks = len(results)
    total_announcements = sum(r.get("total", 0) for r in results.values())
    md_lines.append("## 📊 统计信息\n")
    md_lines.append(f"- **股票数量**: {total_stocks}")
    md_lines.append(f"- **公告总数**: {total_announcements}")
    md_lines.append(f"- **平均每个股票**: {total_announcements / total_stocks if total_stocks > 0 else 0:.1f} 条\n")
    
    # 遍历每个股票
    for code, data in results.items():
        stock_name = data.get("name", "未知")
        announcements = data.get("announcements", [])
        total = data.get("total", len(announcements))
        
        md_lines.append(f"## {code} - {stock_name}\n")
        md_lines.append(f"**公告总数**: {total}\n")
        
        if not announcements:
            md_lines.append("*暂无公告*\n")
            continue
        
        # 表格头部
        md_lines.append("| 序号 | 公告标题 | 公告类型 | 公告日期 | PDF链接 |")
        md_lines.append("|------|----------|----------|----------|---------|")
        
        # 遍历公告
        for idx, ann in enumerate(announcements, 1):
            title = ann.get("title", "").replace("|", "\\|")  # 转义表格中的管道符
            ann_type = ann.get("type", "").replace("|", "\\|")
            date = ann.get("date", "")
            pdf_urls = ann.get("attachments", [])
            
            # 限制标题长度，避免表格过宽
            if len(title) > 50:
                title = title[:47] + "..."
            
            # PDF链接处理
            pdf_links = ""
            if pdf_urls:
                for pdf_url in pdf_urls[:2]:  # 最多显示2个PDF链接
                    pdf_links += f"[PDF]({pdf_url}) "
                if len(pdf_urls) > 2:
                    pdf_links += f"*+{len(pdf_urls) - 2}个*"
            else:
                pdf_links = "-"
            
            md_lines.append(f"| {idx} | {title} | {ann_type} | {date} | {pdf_links} |")
        
        md_lines.append("")  # 空行分隔
        
        # 公告详情（可选，如果内容不太长的话）
        for idx, ann in enumerate(announcements, 1):
            content = ann.get("content", "").strip()
            if content and len(content) < 500:  # 只显示较短的正文
                md_lines.append(f"### {idx}. {ann.get('title', '')}\n")
                md_lines.append(f"**类型**: {ann.get('type', '')}  |  **日期**: {ann.get('date', '')}\n")
                md_lines.append(f"**详情链接**: [{ann.get('detail_url', '')}]({ann.get('detail_url', '')})\n")
                md_lines.append(f"\n{content}\n")
                md_lines.append("---\n")
    
    return "\n".join(md_lines)


def save_results(results: Dict, output_file: str = "announcements.json"):
    """
    保存结果到JSON和Markdown文件
    
    Args:
        results: 抓取结果字典
        output_file: JSON输出文件路径
    """
    # 保存JSON格式
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    
    print(f"💾 JSON结果已保存到: {output_file}")
    
    # 保存Markdown格式
    md_file = output_file.replace(".json", ".md")
    md_content = generate_markdown(results)
    with open(md_file, "w", encoding="utf-8") as f:
        f.write(md_content)
    
    print(f"💾 Markdown结果已保存到: {md_file}")
    
    # 打印统计信息
    total_stocks = len(results)
    total_announcements = sum(r.get("total", 0) for r in results.values())
    print(f"\n📊 统计信息:")
    print(f"   - 股票数量: {total_stocks}")
    print(f"   - 公告总数: {total_announcements}")
    print(f"   - 平均每个股票: {total_announcements / total_stocks if total_stocks > 0 else 0:.1f} 条")


def main():
    """主函数"""
    # 要抓取的股票代码列表
    stock_codes = [
        "603026",  # 石大胜华
        
    ]
    
    # 测试模式配置
    test_mode = False   # 是否启用测试模式（只抓取第一页的前N个）
    test_limit = 10     # 测试模式下最多抓取的公告数量
    
    # 浏览器配置
    headless = False   # 是否使用无头模式（不显示浏览器界面）
    
    # 延迟配置
    interval = 0     # 统一的请求间隔时间（秒），页面加载固定3秒
    
    # 数据库配置
    save_to_db = True  # 是否保存到数据库
    
    # 输出文件路径
    output_file = "announcements.json"
    
    print("🚀 开始抓取股票公告...")
    print(f"📋 目标股票: {', '.join(stock_codes)}")
    if test_mode:
        print(f"🧪 测试模式: 启用（只抓取第一页的前{test_limit}个公告）")
    if save_to_db:
        print(f"💾 数据库保存: 启用")
    print()
    
    start_time = time.time()
    
    # 创建数据库连接（如果需要保存到数据库）
    client = None
    if save_to_db:
        try:
            print("[数据库] 正在连接ClickHouse数据库...")
            client = create_clickhouse_client()
            print("[数据库] ✅ 数据库连接成功")
        except Exception as e:
            print(f"[数据库] ❌ 数据库连接失败: {e}")
            print("[数据库] ⚠️  将只保存到文件，不保存到数据库")
            save_to_db = False
    
    # 执行抓取
    results = crawl_announcements(stock_codes, test_mode=test_mode, test_limit=test_limit, headless=headless, interval=interval)
    
    # 保存到数据库
    if save_to_db and client:
        print(f"\n[数据库] 开始保存公告数据到数据库...")
        total_saved = 0
        for code, data in results.items():
            announcements = data.get("announcements", [])
            if announcements:
                saved_count = save_announcements_to_db(client, code, announcements)
                total_saved += saved_count
        print(f"[数据库] ✅ 数据库保存完成！共保存 {total_saved} 条公告")
        client.close()
    
    # 保存结果到文件
    save_results(results, output_file)
    
    elapsed_time = time.time() - start_time
    print(f"\n⏱️  总耗时: {elapsed_time:.1f} 秒")


if __name__ == "__main__":
    main()
