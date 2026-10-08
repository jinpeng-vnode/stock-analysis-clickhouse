#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
公司资料数据读取器
通过本地API获取公司资料数据
"""

import os
import requests
from typing import Dict, Optional

# API基础URL
API_BASE_URL = os.getenv("STOCK_API_BASE_URL", "http://localhost:9010")


def read_company_info(code: str) -> Dict:
    """
    读取公司资料数据
    通过本地API获取
    
    Args:
        code: 股票代码（6位数字）
    
    Returns:
        包含公司资料数据的字典
    """
    # 调用API
    url = f"{API_BASE_URL}/stock-info/{code}"
    
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        api_data = response.json()
        
        # 解析API返回的数据
        return {
            "code": api_data.get("code", code),
            "name": api_data.get("name", f"股票{code}"),
            "market": api_data.get("market", ""),
            "status": api_data.get("status", "正常"),
            "industry": api_data.get("industry_name", ""),
            "industry_code": api_data.get("industry_code", ""),
            "established_date": api_data.get("established_date", None),
            "registered_capital": api_data.get("reg_asset", None),
            "provincial_name": api_data.get("provincial_name", ""),
            "main_operation_business": api_data.get("main_operation_business", ""),
            "legal_representative": api_data.get("legal_representative", ""),
            "chairman": api_data.get("chairman", ""),
            "listed_date": api_data.get("listed_date", None),
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
        "name": "read_company_info",
        "description": "获取公司资料数据，包括代码、名称、市场、状态、行业、成立时间、注册资本等基本信息",
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