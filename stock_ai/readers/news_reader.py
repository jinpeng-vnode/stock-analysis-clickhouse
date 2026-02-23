#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
资讯数据读取器
使用秘塔AI获取真实新闻数据
"""

import os
import requests
from datetime import datetime
from typing import Dict, List, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed

# 导入股票信息读取器以获取股票名称
try:
    from .stock_info_reader import get_stock_info
except ImportError:
    # 如果相对导入失败，尝试绝对导入（用于直接运行测试）
    import sys
    parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    sys.path.insert(0, parent_dir)
    from readers.stock_info_reader import get_stock_info

# 秘塔AI API配置
METASO_API_BASE_URL = os.getenv("METASO_API_BASE_URL", "https://metaso.cn/api/v1")
METASO_API_TOKEN = os.getenv("METASO_API_TOKEN", "mk-1312C5951A4B3EF2130E44B69528FA70")


def _get_stock_name(code: str) -> str:
    """
    获取股票名称
    
    Args:
        code: 股票代码
        
    Returns:
        股票名称
    """
    stock_info = get_stock_info(code)
    return stock_info.get("name", f"股票{code}")


def _search_metaso_news(query: str, size: int = 10) -> Optional[Dict]:
    """
    调用秘塔AI Search API搜索新闻
    
    Args:
        query: 搜索关键词
        size: 返回数量，默认10条
        
    Returns:
        API响应数据，失败返回None
    """
    url = f"{METASO_API_BASE_URL}/search"
    headers = {
        "Authorization": f"Bearer {METASO_API_TOKEN}",
        "Accept": "application/json",
        "Content-Type": "application/json"
    }
    data = {
        "q": query,
        "scope": "webpage",
        "includeSummary": False,
        "size": str(size),
        "includeRawContent": False,
        "conciseSnippet": False
    }
    
    try:
        response = requests.post(url, json=data, headers=headers, timeout=30)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException:
        return None
    except Exception:
        return None


def _read_metaso_content(url: str) -> Optional[str]:
    """
    调用秘塔AI Reader API获取网页详细内容
    
    Args:
        url: 网页URL
        
    Returns:
        网页内容文本，失败返回None
    """
    reader_url = f"{METASO_API_BASE_URL}/reader"
    headers = {
        "Authorization": f"Bearer {METASO_API_TOKEN}",
        "Accept": "text/plain",
        "Content-Type": "application/json"
    }
    data = {
        "url": url
    }
    
    try:
        response = requests.post(reader_url, json=data, headers=headers, timeout=3)
        response.raise_for_status()
        # 返回响应文本内容
        content = response.text
        return content if content else None
    except requests.exceptions.HTTPError:
        # HTTP错误直接返回None，不打印（保持快速响应）
        return None
    except requests.exceptions.RequestException:
        # 请求错误（包括超时）直接返回None，不打印（保持快速响应）
        return None
    except Exception:
        # 其他错误直接返回None，不打印（保持快速响应）
        return None


def _parse_news_data(api_response: Dict, use_reader: bool = False, on_item_parsed=None) -> List[Dict]:
    """
    解析秘塔AI API返回的新闻数据
    
    Args:
        api_response: API返回的JSON数据
        use_reader: 是否使用reader接口获取详细内容，默认False（只使用snippet）
        on_item_parsed: 可选的回调函数，每解析完一条新闻后调用，参数为 (index, total, news_item)
        
    Returns:
        格式化后的新闻列表
    """
    # 秘塔AI API返回的数据在 webpages 字段中
    webpages = api_response.get("webpages", [])
    total = len(webpages)
    
    # 准备数据列表
    items_data = []
    for index, item in enumerate(webpages, 1):
        items_data.append({
            "index": index,
            "title": item.get("title", ""),
            "link": item.get("link", ""),
            "snippet": item.get("snippet", ""),
            "item": item
        })
    
    # 如果启用reader接口，使用并发方式获取详细内容
    content_results = {}
    if use_reader:
        print(f"  🚀 并发获取 {total} 条新闻的详细内容（超时3秒）...")
        
        def fetch_content(item_data):
            """并发获取单条新闻的详细内容"""
            index = item_data["index"]
            link = item_data["link"]
            if link:
                content = _read_metaso_content(link)
                return {
                    "index": index,
                    "content": content,
                    "success": content is not None
                }
            return {
                "index": index,
                "content": None,
                "success": False
            }
        
        # 使用线程池并发请求
        with ThreadPoolExecutor(max_workers=10) as executor:
            future_to_index = {executor.submit(fetch_content, item_data): item_data["index"] 
                              for item_data in items_data if item_data["link"]}
            
            for future in as_completed(future_to_index):
                index = future_to_index[future]
                try:
                    result = future.result()
                    content_results[result["index"]] = result
                except Exception:
                    content_results[index] = {"index": index, "content": None, "success": False}
    
    # 解析并构建新闻列表
    news_list = []
    for item_data in items_data:
        index = item_data["index"]
        title = item_data["title"]
        link = item_data["link"]
        snippet = item_data["snippet"]
        item = item_data["item"]
        
        # 如果启用reader接口，使用并发获取的内容
        content_summary = snippet
        if use_reader and link:
            result = content_results.get(index, {"content": None, "success": False})
            if result.get("content"):
                detailed_content = result["content"]
                content_summary = detailed_content[:500] + "..." if len(detailed_content) > 500 else detailed_content
                print(f"  ✅ [{index}/{total}] 获取成功: {title[:50]}...")
            else:
                content_summary = snippet if snippet else title
                print(f"  ⚡ [{index}/{total}] 快速跳过: {title[:50]}...")
        else:
            # 不使用reader接口，直接使用snippet
            content_summary = snippet if snippet else title
        
        # 尝试从不同字段获取来源
        source = item.get("source", "")
        if not source:
            # 从链接中提取域名作为来源
            try:
                from urllib.parse import urlparse
                parsed_url = urlparse(link)
                source = parsed_url.netloc.replace("www.", "") if parsed_url.netloc else "未知来源"
            except Exception:
                source = "未知来源"
        
        # 尝试获取发布时间
        publish_time = item.get("publish_time", "")
        if not publish_time:
            publish_time = item.get("date", "")
        if not publish_time:
            publish_time = item.get("published_date", "")
        
        # 格式化发布时间
        if publish_time:
            try:
                # 尝试解析不同格式的时间
                if isinstance(publish_time, str):
                    # 如果已经是标准格式，直接使用
                    if len(publish_time) >= 10:
                        if "T" in publish_time:
                            dt = datetime.fromisoformat(publish_time.replace("Z", "+00:00"))
                            publish_time = dt.strftime("%Y-%m-%d %H:%M:%S")
                        else:
                            publish_time = publish_time[:19] if len(publish_time) > 19 else publish_time
                else:
                    publish_time = ""
            except Exception:
                publish_time = ""
        
        news_item = {
            "title": title,
            "publish_time": publish_time or datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "source": source or "未知来源",
            "content_summary": content_summary,
            "url": link  # 保存URL以便后续获取详细内容
        }
        
        news_list.append(news_item)
        
        # 调用回调函数，实时打印
        if on_item_parsed:
            on_item_parsed(index, total, news_item)
    
    return news_list


def read_news(code: str, use_detailed_content: bool = True) -> Dict:
    """
    读取股票相关资讯数据
    使用秘塔AI API获取真实新闻数据
    
    Args:
        code: 股票代码（6位数字）
        use_detailed_content: 是否使用reader接口获取详细内容，默认True（获取详细内容）
                              False时只使用search接口返回的摘要，速度更快但内容较少
    
    Returns:
        包含资讯数据的字典
    """
    news_list = []
    
    # 获取股票名称
    stock_name = _get_stock_name(code)
    
    # 构建搜索关键词（股票名称 + "股票"）
    search_query = f"{stock_name}股票"
    
    # 固定返回10条新闻
    size = 10
    
    # 调用秘塔AI API搜索新闻
    api_response = _search_metaso_news(search_query, size=size)
    
    if api_response:
        # 定义实时打印回调函数
        def print_news_item(index, total, news_item):
            print(f"\n【新闻 {index}/{total}】")
            print(f"  标题: {news_item.get('title', 'N/A')}")
            print(f"  发布时间: {news_item.get('publish_time', 'N/A')}")
            print(f"  来源: {news_item.get('source', 'N/A')}")
            content = news_item.get('content_summary', 'N/A')
            if len(content) > 100:
                print(f"  摘要: {content[:100]}...")
            else:
                print(f"  摘要: {content}")
            if news_item.get('url'):
                print(f"  链接: {news_item.get('url', 'N/A')}")
        
        # 解析API返回的数据，实时打印
        news_list = _parse_news_data(api_response, use_reader=use_detailed_content, on_item_parsed=print_news_item)
        
        # 按时间倒序排列
        news_list.sort(key=lambda x: x.get("publish_time", ""), reverse=True)
    
    return {
        "code": code,
        "total_count": len(news_list),
        "news_list": news_list
    }


# 函数定义（供DeepSeek使用）
function_define = {
    "type": "function",
    "function": {
        "name": "read_news",
        "description": "获取股票相关的资讯数据，包括新闻标题、发布时间、来源、内容摘要，固定返回10条最新新闻",
        "parameters": {
            "type": "object",
            "properties": {
                "code": {
                    "type": "string",
                    "description": "股票代码，6位数字"
                }
            },
            "required": ["code"]
        }
    }
}


def main():
    """测试主函数"""
    import json
    
    print("=" * 80)
    print("📰 秘塔AI新闻数据读取器测试")
    print("=" * 80)
    print()
    
    # 测试股票代码
    test_code = "000001"  # 平安银行
    
    code = test_code
    print(f"\n{'='*80}")
    print(f"🔍 测试股票代码: {code}")
    print(f"{'='*80}")
    
    try:
        # 获取股票名称
        stock_name = _get_stock_name(code)
        print(f"📊 股票名称: {stock_name}")
        print(f"🔎 搜索关键词: {stock_name}股票")
        print()
        
        # 调用read_news函数
        print("⏳ 正在调用秘塔AI API获取新闻数据...")
        print("💡 提示: 已启用详细内容获取（10条都使用reader接口），实时显示进度")
        print()
        result = read_news(code, use_detailed_content=True)
        
        # 打印结果汇总
        print()
        print("=" * 80)
        if result.get('total_count', 0) > 0:
            print(f"✅ 获取成功！")
            print(f"📈 股票代码: {result['code']}")
            print(f"📰 新闻总数: {result['total_count']}")
        else:
            print("⚠️  未获取到新闻数据")
            print("   可能原因:")
            print("   1. API调用失败")
            print("   2. 该股票暂无相关新闻")
            print("   3. API返回格式与预期不符")
        print("=" * 80)
        
    except Exception as e:
        print(f"\n❌ 测试失败: {str(e)}")
        import traceback
        traceback.print_exc()
    
    print()
    print("=" * 80)
    print("✅ 测试完成！")
    print("=" * 80)


if __name__ == "__main__":
    main()