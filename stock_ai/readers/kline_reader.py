#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
日线图数据读取器
通过本地API获取股票日K线数据
"""

import os
import requests
from datetime import datetime, timedelta, date
from typing import Dict, List, Optional

# API基础URL
API_BASE_URL = os.getenv("STOCK_API_BASE_URL", "http://localhost:9010")


def read_kline(code: str, days: int = 30, start_date: Optional[str] = None, end_date: Optional[str] = None) -> Dict:
    """
    读取股票日K线数据
    通过本地API获取
    
    Args:
        code: 股票代码（6位数字）
        days: 获取最近多少天的数据，默认30天（如果指定了start_date和end_date则忽略此参数）
        start_date: 开始日期，格式YYYY-MM-DD，可选
        end_date: 结束日期，格式YYYY-MM-DD，可选
    
    Returns:
        包含日K线数据的字典
    """
    # 如果没有指定日期范围，使用days参数计算
    if not start_date and not end_date:
        end_date_obj = date.today()
        start_date_obj = end_date_obj - timedelta(days=days - 1)
        start_date = start_date_obj.isoformat()
        end_date = end_date_obj.isoformat()
    elif not end_date:
        end_date = date.today().isoformat()
    elif not start_date:
        # 如果只指定了结束日期，向前推days天
        end_date_obj = datetime.strptime(end_date, "%Y-%m-%d").date()
        start_date_obj = end_date_obj - timedelta(days=days - 1)
        start_date = start_date_obj.isoformat()
    
    # 调用API
    url = f"{API_BASE_URL}/stocks/{code}/daily"
    params = {
        "start": start_date,
        "end": end_date
    }
    
    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        api_data = response.json()
        
        # 解析API返回的数据
        data_list = api_data.get("data", [])
        name = api_data.get("name", "")
        total_records = api_data.get("total_records", len(data_list))
        
        if not data_list:
            return {
                "code": code,
                "name": name,
                "days": days,
                "start_date": start_date,
                "end_date": end_date,
                "total_records": 0,
                "kline_data": [],
                "message": "暂无数据"
            }
        
        # 转换为所需格式
        kline_data = []
        for item in data_list:
            kline_data.append({
                "trade_date": item.get("trade_date", ""),
                "open_price": item.get("open_price", 0),
                "close_price": item.get("close_price", 0),
                "high_price": item.get("high_price", 0),
                "low_price": item.get("low_price", 0),
                "volume": item.get("volume", 0),
                "amount": item.get("amount", 0),
                "change_pct": item.get("change_pct", 0),
                "change_amount": item.get("change_amount", 0),
                "amplitude": item.get("amplitude", 0),
                "turnover_rate": item.get("turnover_rate", 0),
            })
        
        # 计算统计信息
        if kline_data:
            latest = kline_data[-1]
            first = kline_data[0]
            
            # 计算期间涨跌幅
            period_change_pct = ((latest["close_price"] - first["open_price"]) / first["open_price"] * 100) if first["open_price"] > 0 else 0
            
            # 计算最高价和最低价
            max_price = max(item["high_price"] for item in kline_data)
            min_price = min(item["low_price"] for item in kline_data)
            
            # 计算平均成交量
            avg_volume = sum(item["volume"] for item in kline_data) / len(kline_data) if kline_data else 0
            
            summary = {
                "period_change_pct": round(period_change_pct, 2),
                "max_price": round(max_price, 2),
                "min_price": round(min_price, 2),
                "latest_close_price": round(latest["close_price"], 2),
                "avg_volume": round(avg_volume, 0),
            }
        else:
            summary = {}
        
        return {
            "code": code,
            "name": name,
            "days": days,
            "start_date": start_date,
            "end_date": end_date,
            "total_records": total_records,
            "summary": summary,
            "kline_data": kline_data
        }
        
    except requests.exceptions.RequestException as e:
        return {
            "code": code,
            "error": f"API请求失败: {str(e)}",
            "days": days,
            "kline_data": []
        }
    except Exception as e:
        return {
            "code": code,
            "error": f"数据处理错误: {str(e)}",
            "days": days,
            "kline_data": []
        }


# 函数定义（供DeepSeek使用）
function_define = {
    "type": "function",
    "function": {
        "name": "read_kline",
        "description": "获取股票的日K线数据，包括开盘价、收盘价、最高价、最低价、成交量、成交额、涨跌幅等，以及期间统计信息",
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
                },
                "start_date": {
                    "type": "string",
                    "description": "开始日期，格式YYYY-MM-DD，可选"
                },
                "end_date": {
                    "type": "string",
                    "description": "结束日期，格式YYYY-MM-DD，可选"
                }
            },
            "required": ["code"]
        }
    }
}

