#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
资金流向数据读取器
通过本地API获取资金流向数据
"""

import os
import requests
from datetime import datetime, timedelta, date
from typing import Dict, List, Optional

# API基础URL
API_BASE_URL = os.getenv("STOCK_API_BASE_URL", "http://localhost:9010")


def read_money_flow(code: str, days: int = 30) -> Dict:
    """
    读取股票资金流向数据
    通过本地API获取
    
    Args:
        code: 股票代码（6位数字）
        days: 获取最近多少天的数据，默认30天
    
    Returns:
        包含资金流向数据的字典
    """
    # 计算日期范围
    end_date = date.today()
    start_date = end_date - timedelta(days=days - 1)
    
    # 调用API
    url = f"{API_BASE_URL}/money-flow/{code}"
    params = {
        "start_date": start_date.isoformat(),
        "end_date": end_date.isoformat(),
        "limit": days
    }
    
    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        api_data = response.json()
        
        # FastAPI直接返回响应模型（MoneyFlowResponse）
        # 解析响应数据
        data_list = api_data.get("data", [])
        name = api_data.get("name", "")
        
        if not data_list:
            return {
                "code": code,
                "name": name,
                "days": days,
                "daily_data": [],
                "message": "暂无数据"
            }
        
        # 转换为所需格式
        daily_data = []
        for item in data_list:
            daily_data.append({
                "date": item.get("trade_date", ""),
                "main_net_inflow_amount": item.get("main_net_inflow_amount", 0),
                "main_net_inflow_ratio": item.get("main_net_inflow_ratio", 0),
                "super_large_net_inflow_amount": item.get("super_large_net_inflow_amount", 0),
                "large_net_inflow_amount": item.get("large_net_inflow_amount", 0),
                "medium_net_inflow_amount": item.get("medium_net_inflow_amount", 0),
                "small_net_inflow_amount": item.get("small_net_inflow_amount", 0),
            })
        
        # 计算多日累计净流入
        net_inflow_3d = sum(d["main_net_inflow_amount"] for d in daily_data[-3:])
        net_inflow_5d = sum(d["main_net_inflow_amount"] for d in daily_data[-5:])
        net_inflow_10d = sum(d["main_net_inflow_amount"] for d in daily_data[-10:])
        net_inflow_20d = sum(d["main_net_inflow_amount"] for d in daily_data[-20:])
        
        # 获取最新数据
        latest = daily_data[-1] if daily_data else {}
        
        return {
            "code": code,
            "name": name,
            "days": days,
            "latest_date": latest.get("date", ""),
            "main_net_inflow_amount": round(latest.get("main_net_inflow_amount", 0), 2),
            "main_net_inflow_ratio": round(latest.get("main_net_inflow_ratio", 0), 2),
            "super_large_net_inflow_amount": round(latest.get("super_large_net_inflow_amount", 0), 2),
            "large_net_inflow_amount": round(latest.get("large_net_inflow_amount", 0), 2),
            "medium_net_inflow_amount": round(latest.get("medium_net_inflow_amount", 0), 2),
            "small_net_inflow_amount": round(latest.get("small_net_inflow_amount", 0), 2),
            "net_inflow_3d": round(net_inflow_3d, 2),
            "net_inflow_5d": round(net_inflow_5d, 2),
            "net_inflow_10d": round(net_inflow_10d, 2),
            "net_inflow_20d": round(net_inflow_20d, 2),
            "daily_data": daily_data
        }
        
    except requests.exceptions.RequestException as e:
        return {
            "code": code,
            "error": f"API请求失败: {str(e)}",
            "days": days,
            "daily_data": []
        }
    except Exception as e:
        return {
            "code": code,
            "error": f"数据处理错误: {str(e)}",
            "days": days,
            "daily_data": []
        }


# 函数定义（供DeepSeek使用）
function_define = {
    "type": "function",
    "function": {
        "name": "read_money_flow",
        "description": "获取股票的资金流向数据，包括主力净流入、超大单、大单、中单、小单净流入，以及多日累计净流入统计",
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