#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
公告数据读取器
通过本地API获取公告数据
"""

import os
import requests
from datetime import datetime, timedelta, date
from typing import Dict, List, Optional

# API基础URL
API_BASE_URL = os.getenv("STOCK_API_BASE_URL", "http://localhost:9010")


def read_announcement(code: str, days: int = 30) -> Dict:
    """
    读取股票相关公告数据
    通过本地API获取
    
    Args:
        code: 股票代码（6位数字）
        days: 获取最近多少天的数据，默认30天
    
    Returns:
        包含公告数据的字典
    """
    # 计算日期范围
    end_date = date.today()
    start_date = end_date - timedelta(days=days - 1)
    
    # 调用API
    url = f"{API_BASE_URL}/announcements/{code}"
    params = {
        "start_date": start_date.isoformat(),
        "end_date": end_date.isoformat(),
        "page": 1,
        "size": 200  # 获取足够多的数据
    }
    
    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        api_data = response.json()
        
        # 解析API返回的数据
        items = api_data.get("items", [])
        name = api_data.get("name", "")
        total = api_data.get("total", 0)
        
        if not items:
            return {
                "code": code,
                "name": name,
                "days": days,
                "total_count": 0,
                "announcement_list": []
            }
        
        # 转换为所需格式
        announcement_list = []
        for item in items:
            # 格式化发布时间
            announce_date = item.get("announce_date", "")
            if isinstance(announce_date, str):
                publish_time = announce_date
            else:
                publish_time = announce_date.strftime("%Y-%m-%d %H:%M:%S") if announce_date else ""
            
            # 获取内容摘要（如果有content则截取前500字符，否则使用标题）
            content = item.get("content", "")
            if content and len(content) > 0:
                content_summary = content[:500] + "..." if len(content) > 500 else content
            else:
                content_summary = item.get("title", "")
            
            announcement_list.append({
                "type": item.get("type", "其他"),
                "title": item.get("title", ""),
                "publish_time": publish_time,
                "content_summary": content_summary
            })
        
        # 按时间倒序排列
        announcement_list.sort(key=lambda x: x["publish_time"], reverse=True)
        
        return {
            "code": code,
            "name": name,
            "days": days,
            "total_count": len(announcement_list),
            "announcement_list": announcement_list
        }
        
    except requests.exceptions.RequestException as e:
        return {
            "code": code,
            "error": f"API请求失败: {str(e)}",
            "days": days,
            "total_count": 0,
            "announcement_list": []
        }
    except Exception as e:
        return {
            "code": code,
            "error": f"数据处理错误: {str(e)}",
            "days": days,
            "total_count": 0,
            "announcement_list": []
        }


# 函数定义（供DeepSeek使用）
function_define = {
    "type": "function",
    "function": {
        "name": "read_announcement",
        "description": "获取股票相关的公告数据，包括公告类型、标题、发布时间、内容摘要",
        "parameters": {
            "type": "object",
            "properties": {
                "code": {
                    "type": "string",
                    "description": "股票代码，6位数字"
                },
                "days": {
                    "type": "integer",
                    "description": "获取最近多少天的数据，默认30天",
                    "default": 30
                }
            },
            "required": ["code"]
        }
    }
}