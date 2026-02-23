"""
信号分析相关 Pydantic 模型（从 models/stock_models.py 提取）
"""
from typing import List
from pydantic import BaseModel, Field


class StockSignalInfo(BaseModel):
    """股票信号信息模型"""
    code: str = Field(..., description="股票代码")
    name: str = Field(..., description="股票名称")
    buy_signals: int = Field(..., description="买入信号数量")
    sell_signals: int = Field(..., description="卖出信号数量")
    total_signals: int = Field(..., description="总信号数量")
    data_rows: int = Field(..., description="数据行数")


class SignalAnalysisResponse(BaseModel):
    """信号分析响应模型"""
    start_date: str = Field(..., description="开始日期")
    end_date: str = Field(..., description="结束日期")
    min_signals: int = Field(..., description="最小信号数量")
    total_stocks_analyzed: int = Field(..., description="分析股票总数")
    matching_stocks: int = Field(..., description="匹配股票数量")
    stocks: List[StockSignalInfo] = Field(..., description="股票信号列表")

