"""
资金流向相关 Pydantic 模型（从 models/stock_models.py 提取）
"""
from datetime import date
from typing import List, Optional, Dict
from pydantic import BaseModel, Field


class MoneyFlowData(BaseModel):
    """资金流向数据模型"""
    code: str = Field(..., description="股票代码")
    trade_date: date = Field(..., description="交易日期")
    close_price: float = Field(..., description="收盘价（元）")
    change_pct: float = Field(..., description="涨跌幅（%）")
    
    # 主力资金流向
    main_net_inflow_amount: float = Field(..., description="主力净流入-净额（元）")
    main_net_inflow_ratio: float = Field(..., description="主力净流入-净占比（%）")
    
    # 超大单资金流向
    super_large_net_inflow_amount: float = Field(..., description="超大单净流入-净额（元）")
    super_large_net_inflow_ratio: float = Field(..., description="超大单净流入-净占比（%）")
    
    # 大单资金流向
    large_net_inflow_amount: float = Field(..., description="大单净流入-净额（元）")
    large_net_inflow_ratio: float = Field(..., description="大单净流入-净占比（%）")
    
    # 中单资金流向
    medium_net_inflow_amount: float = Field(..., description="中单净流入-净额（元）")
    medium_net_inflow_ratio: float = Field(..., description="中单净流入-净占比（%）")
    
    # 小单资金流向
    small_net_inflow_amount: float = Field(..., description="小单净流入-净额（元）")
    small_net_inflow_ratio: float = Field(..., description="小单净流入-净占比（%）")


class MoneyFlowResponse(BaseModel):
    """资金流向响应模型"""
    code: str = Field(..., description="股票代码")
    name: str = Field(..., description="股票名称")
    total_records: int = Field(..., description="总记录数")
    data: List[MoneyFlowData] = Field(..., description="资金流向数据列表")


class MoneyFlowStatsResponse(BaseModel):
    """资金流向统计响应模型"""
    total_records: int = Field(..., description="总记录数")
    date_range: Dict[str, Optional[str]] = Field(..., description="数据日期范围")
    stocks_with_data: int = Field(..., description="有资金流向数据的股票数量")
    latest_update: Optional[str] = Field(None, description="最新数据日期")


class MoneyFlowTopItem(BaseModel):
    """资金流向排行榜项目模型"""
    code: str = Field(..., description="股票代码")
    name: str = Field(..., description="股票名称")
    trade_date: date = Field(..., description="交易日期")
    close_price: float = Field(..., description="收盘价（元）")
    change_pct: float = Field(..., description="涨跌幅（%）")
    main_net_inflow_amount: float = Field(..., description="主力净流入-净额（元）")
    main_net_inflow_ratio: float = Field(..., description="主力净流入-净占比（%）")


class MoneyFlowTopResponse(BaseModel):
    """资金流向排行榜响应模型"""
    date: str = Field(..., description="统计日期")
    total_stocks: int = Field(..., description="总股票数量")
    top_inflow: List[MoneyFlowTopItem] = Field(..., description="净流入排行榜")
    top_outflow: List[MoneyFlowTopItem] = Field(..., description="净流出排行榜")

