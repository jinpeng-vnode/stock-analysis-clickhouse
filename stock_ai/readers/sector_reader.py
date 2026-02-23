#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
板块数据读取器
"""

import random
from typing import Dict, List


def read_sector(code: str, days: int = 30) -> Dict:
    """
    读取板块数据
    
    Args:
        code: 股票代码（6位数字）
        days: 获取最近多少天的数据，默认30天
    
    Returns:
        包含板块数据的字典
    """
    # 常见板块列表
    sectors = [
        "银行", "房地产", "白酒", "科技", "医药", "能源", "制造业", 
        "消费", "金融", "互联网", "新能源", "化工", "钢铁", "有色",
        "食品饮料", "家电", "汽车", "电子", "通信", "计算机"
    ]
    
    # 根据股票代码模拟板块（简单映射）
    sector_mapping = {
        "000001": "银行",
        "000002": "房地产",
        "600000": "银行",
        "600519": "白酒",
        "000858": "白酒",
    }
    
    # 获取股票所属板块
    sector_name = sector_mapping.get(code, random.choice(sectors))
    
    # 模拟板块涨跌幅（-5% 到 +5%）
    sector_change_pct = round(random.uniform(-5.0, 5.0), 2)
    
    # 模拟板块内股票列表（5-15只股票）
    stock_count = random.randint(5, 15)
    sector_stocks = []
    
    # 常见股票代码和名称（用于模拟）
    stock_samples = [
        {"code": "000001", "name": "平安银行"},
        {"code": "000002", "name": "万科A"},
        {"code": "600000", "name": "浦发银行"},
        {"code": "600519", "name": "贵州茅台"},
        {"code": "000858", "name": "五粮液"},
        {"code": "600036", "name": "招商银行"},
        {"code": "000157", "name": "中联重科"},
        {"code": "600887", "name": "伊利股份"},
        {"code": "000876", "name": "新希望"},
        {"code": "600276", "name": "恒瑞医药"},
    ]
    
    # 确保当前股票在列表中
    current_stock_in_list = False
    current_stock_rank = random.randint(1, stock_count)
    
    for i in range(stock_count):
        if i == current_stock_rank - 1:
            # 插入当前股票
            sector_stocks.append({
                "code": code,
                "name": f"股票{code}",
                "change_pct": round(random.uniform(-8.0, 8.0), 2),
                "is_current": True
            })
            current_stock_in_list = True
        else:
            # 随机选择其他股票
            if i < len(stock_samples):
                stock = stock_samples[i]
            else:
                stock = {"code": f"{random.randint(100000, 999999)}", "name": f"股票{random.randint(100000, 999999)}"}
            
            sector_stocks.append({
                "code": stock["code"],
                "name": stock["name"],
                "change_pct": round(random.uniform(-10.0, 10.0), 2),
                "is_current": False
            })
    
    # 如果没有插入当前股票，在随机位置插入
    if not current_stock_in_list:
        insert_pos = random.randint(0, len(sector_stocks))
        sector_stocks.insert(insert_pos, {
            "code": code,
            "name": f"股票{code}",
            "change_pct": round(random.uniform(-8.0, 8.0), 2),
            "is_current": True
        })
        current_stock_rank = insert_pos + 1
    
    # 按涨跌幅排序（降序）
    sector_stocks.sort(key=lambda x: x["change_pct"], reverse=True)
    
    # 重新计算排名
    for i, stock in enumerate(sector_stocks):
        if stock["is_current"]:
            current_stock_rank = i + 1
            break
    
    return {
        "code": code,
        "days": days,
        "sector_name": sector_name,
        "sector_change_pct": sector_change_pct,
        "current_stock_rank": current_stock_rank,
        "total_stocks_in_sector": len(sector_stocks),
        "sector_stocks": sector_stocks
    }


# 函数定义（供DeepSeek使用）
function_define = {
    "type": "function",
    "function": {
        "name": "read_sector",
        "description": "获取板块数据，包括所属板块名称、板块涨跌幅、板块内股票列表及涨跌幅、当前股票在板块内的排名等",
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

