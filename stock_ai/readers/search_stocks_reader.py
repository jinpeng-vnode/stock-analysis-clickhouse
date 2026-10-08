#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
股票搜索数据读取器
"""

from typing import Dict, List


def search_stocks(keyword: str, limit: int = 50) -> Dict:
    """
    搜索股票
    
    Args:
        keyword: 搜索关键词（股票代码或名称）
        limit: 返回结果数量限制，默认50
    
    Returns:
        包含股票列表的字典
    """
    # 常见股票列表（模拟数据）
    stock_database = [
        {"code": "000001", "name": "平安银行", "market": "SZ"},
        {"code": "000002", "name": "万科A", "market": "SZ"},
        {"code": "000858", "name": "五粮液", "market": "SZ"},
        {"code": "600000", "name": "浦发银行", "market": "SH"},
        {"code": "600036", "name": "招商银行", "market": "SH"},
        {"code": "600519", "name": "贵州茅台", "market": "SH"},
        {"code": "600887", "name": "伊利股份", "market": "SH"},
        {"code": "000157", "name": "中联重科", "market": "SZ"},
        {"code": "000876", "name": "新希望", "market": "SZ"},
        {"code": "600276", "name": "恒瑞医药", "market": "SH"},
        {"code": "002415", "name": "海康威视", "market": "SZ"},
        {"code": "000725", "name": "京东方A", "market": "SZ"},
        {"code": "002594", "name": "比亚迪", "market": "SZ"},
        {"code": "002142", "name": "宁波银行", "market": "SZ"},
    ]
    
    # 转换为小写进行模糊匹配
    keyword_lower = keyword.lower()
    matched_stocks = []
    
    for stock in stock_database:
        # 匹配代码或名称
        if (keyword_lower in stock["code"].lower() or 
            keyword_lower in stock["name"].lower()):
            matched_stocks.append({
                "code": stock["code"],
                "name": stock["name"],
                "market": stock["market"]
            })
    
    # 限制返回数量
    matched_stocks = matched_stocks[:limit]
    
    return {
        "keyword": keyword,
        "total_count": len(matched_stocks),
        "limit": limit,
        "stocks": matched_stocks
    }


# 函数定义（供DeepSeek使用）
function_define = {
    "type": "function",
    "function": {
        "name": "search_stocks",
        "description": "根据关键词搜索股票，支持按股票代码或名称进行模糊匹配",
        "parameters": {
            "type": "object",
            "properties": {
                "keyword": {
                    "type": "string",
                    "description": "搜索关键词，可以是股票代码或股票名称"
                },
                "limit": {
                    "type": "integer",
                    "description": "返回结果数量限制，默认50",
                    "default": 50
                }
            },
            "required": ["keyword"]
        }
    }
}

