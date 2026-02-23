#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
财务数据读取器
通过本地API获取财务数据
"""

import os
import requests
from typing import Dict, Optional
from datetime import date, timedelta

# API基础URL
API_BASE_URL = os.getenv("STOCK_API_BASE_URL", "http://localhost:9010")


def read_financial(code: str) -> Dict:
    """
    读取公司财务数据
    通过本地API获取最新的财务报告数据
    
    Args:
        code: 股票代码（6位数字）
    
    Returns:
        包含财务数据的字典
    """
    # 调用API获取最新的财务报告（最近5年）
    end_date = date.today()
    start_date = date(end_date.year - 5, 1, 1)
    
    url = f"{API_BASE_URL}/financial-reports/{code}"
    params = {
        "start_date": start_date.isoformat(),
        "end_date": end_date.isoformat(),
        "page": 1,
        "size": 1  # 只获取最新的一条
    }
    
    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        api_data = response.json()
        
        # 解析API返回的数据
        items = api_data.get("items", [])
        name = api_data.get("name", "")
        
        if not items:
            return {
                "code": code,
                "name": name,
                "error": "暂无财务数据",
                "report_period": None
            }
        
        # 获取最新的财务报告
        latest_report = items[0]
        
        # 提取报告期
        report_date = latest_report.get("report_date", "")
        report_name = latest_report.get("report_name", "")
        
        # 处理report_date格式（可能是字符串或date对象）
        if isinstance(report_date, str):
            report_date_str = report_date
        elif report_date:
            report_date_str = report_date.strftime("%Y-%m-%d")
        else:
            report_date_str = None
        
        report_period = report_name if report_name else (report_date_str[:4] + "年" if report_date_str else "未知")
        
        # 提取盈利能力指标
        profitability = {
            "roe": latest_report.get("ore_dlt"),  # 净资产收益率（%）
            "roa": latest_report.get("rop"),  # 总资产收益率（%）
            "net_profit_margin": latest_report.get("net_selling_rate"),  # 净利润率（%）
            "gross_profit_margin": latest_report.get("gross_selling_rate"),  # 毛利率（%）
        }
        
        # 提取偿债能力指标
        solvency = {
            "asset_liability_ratio": latest_report.get("asset_liab_ratio"),  # 资产负债率（%）
            "current_ratio": latest_report.get("current_ratio"),  # 流动比率
            "quick_ratio": latest_report.get("quick_ratio"),  # 速动比率
        }
        
        # 提取成长性指标
        growth = {
            "revenue_growth_rate": latest_report.get("operating_income_yoy"),  # 营收增长率（%）
            "net_profit_growth_rate": latest_report.get("net_profit_atsopc_yoy"),  # 净利润增长率（%）
            "total_assets_growth_rate": None,  # 总资产增长率（%），需要计算
        }
        
        # 提取经营数据
        operating_data = {
            "total_revenue": latest_report.get("total_revenue"),  # 营业收入（万元或亿元，需要确认单位）
            "net_profit": latest_report.get("net_profit_atsopc"),  # 净利润（万元或亿元）
            "total_assets": None,  # 总资产（需要从其他字段计算或获取）
            "total_liabilities": None,  # 总负债（需要从其他字段计算或获取）
        }
        
        # 清理None值，转换为可用格式
        def clean_dict(d):
            """清理字典中的None值"""
            return {k: round(v, 2) if isinstance(v, (int, float)) else v 
                   for k, v in d.items() if v is not None}
        
        profitability = clean_dict(profitability)
        solvency = clean_dict(solvency)
        growth = clean_dict(growth)
        operating_data = clean_dict(operating_data)
        
        return {
            "code": code,
            "name": name,
            "report_period": report_period,
            "report_date": report_date_str,
            "profitability": profitability if profitability else None,
            "solvency": solvency if solvency else None,
            "growth": growth if growth else None,
            "operating_data": operating_data if operating_data else None,
            "data_source": "api"
        }
        
    except requests.exceptions.RequestException as e:
        return {
            "code": code,
            "error": f"API请求失败: {str(e)}",
            "data_source": "error"
        }
    except Exception as e:
        return {
            "code": code,
            "error": f"数据处理错误: {str(e)}",
            "data_source": "error"
        }


# 函数定义（供DeepSeek使用）
function_define = {
    "type": "function",
    "function": {
        "name": "read_financial",
        "description": "获取公司财务数据，包括盈利能力指标（ROE、ROA、净利润率、毛利率）、偿债能力指标（资产负债率、流动比率、速动比率）、成长性指标（营收增长率、净利润增长率、总资产增长率）等",
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