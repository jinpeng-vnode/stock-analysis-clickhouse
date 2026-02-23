#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
股票信息数据读取器
"""

from typing import Dict, Optional


def get_stock_info(code: str) -> Dict:
    """
    获取股票基本信息
    
    Args:
        code: 股票代码（6位数字）
    
    Returns:
        包含股票信息的字典
    """
    # 常见股票信息（模拟数据）
    stock_info_database = {
        "000001": {"code": "000001", "name": "平安银行", "market": "SZ", "status": "正常"},
        "000002": {"code": "000002", "name": "万科A", "market": "SZ", "status": "正常"},
        "000858": {"code": "000858", "name": "五粮液", "market": "SZ", "status": "正常"},
        "600000": {"code": "600000", "name": "浦发银行", "market": "SH", "status": "正常"},
        "600036": {"code": "600036", "name": "招商银行", "market": "SH", "status": "正常"},
        "600519": {"code": "600519", "name": "贵州茅台", "market": "SH", "status": "正常"},
        "600887": {"code": "600887", "name": "伊利股份", "market": "SH", "status": "正常"},
        "000157": {"code": "000157", "name": "中联重科", "market": "SZ", "status": "正常"},
        "000876": {"code": "000876", "name": "新希望", "market": "SZ", "status": "正常"},
        "600276": {"code": "600276", "name": "恒瑞医药", "market": "SH", "status": "正常"},
        "002415": {"code": "002415", "name": "海康威视", "market": "SZ", "status": "正常"},
        "000725": {"code": "000725", "name": "京东方A", "market": "SZ", "status": "正常"},
        "002594": {"code": "002594", "name": "比亚迪", "market": "SZ", "status": "正常"},
        "002142": {"code": "002142", "name": "宁波银行", "market": "SZ", "status": "正常"},
    }
    
    # 查找股票信息
    if code in stock_info_database:
        stock_info = stock_info_database[code].copy()
        return stock_info
    else:
        # 如果找不到，返回默认信息
        market = "SH" if code.startswith("6") else "SZ"
        return {
            "code": code,
            "name": f"股票{code}",
            "market": market,
            "status": "正常"
        }


# 函数定义（供DeepSeek使用）
function_define = {
    "type": "function",
    "function": {
        "name": "get_stock_info",
        "description": "根据股票代码获取股票基本信息，包括代码、名称、市场类型、状态等",
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

