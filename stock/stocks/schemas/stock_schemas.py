"""
股票基础与日线相关 Pydantic 模型（从 models/stock_models.py 拆分）
"""
from datetime import date, datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class StockInfo(BaseModel):
    code: str = Field(..., description="股票代码（6位数字）")
    name: str = Field(..., description="股票名称")
    market: str = Field(default="", description="市场类型：SH/SZ")
    status: str = Field(default="正常", description="股票状态")
    created_at: Optional[datetime] = Field(None, description="创建时间")
    updated_at: Optional[datetime] = Field(None, description="更新时间")


class StockDaily(BaseModel):
    code: str = Field(..., description="股票代码")
    trade_date: date = Field(..., description="交易日期")
    name: str = Field(..., description="股票名称")
    open_price: float = Field(..., description="开盘价（元）")
    close_price: float = Field(..., description="收盘价（元）")
    high_price: float = Field(..., description="最高价（元）")
    low_price: float = Field(..., description="最低价（元）")
    volume: int = Field(..., description="成交量（手）")
    amount: float = Field(..., description="成交额（元）")
    amplitude: Optional[float] = Field(None, description="振幅（%）")
    change_pct: Optional[float] = Field(None, description="涨跌幅（%）")
    change_amount: Optional[float] = Field(None, description="涨跌额（元）")
    turnover_rate: Optional[float] = Field(None, description="换手率（%）")
    created_at: Optional[datetime] = Field(None, description="数据入库时间")


class StockListResponse(BaseModel):
    total: int = Field(..., description="总数量")
    stocks: List[StockInfo] = Field(..., description="股票列表")


class StockDailyResponse(BaseModel):
    code: str = Field(..., description="股票代码")
    name: str = Field(..., description="股票名称")
    total_records: int = Field(..., description="总记录数")
    data: List[StockDaily] = Field(..., description="K线数据列表")


class StockItem(BaseModel):
    code: str = Field(..., description="股票代码")
    name: str = Field(..., description="股票名称")


class DayDataResponse(BaseModel):
    code: str = Field(..., description="股票代码")
    date: str = Field(..., description="日期")
    name: str = Field(..., description="股票名称")
    rows: int = Field(..., description="数据行数")
    data: List[Dict[str, Any]] = Field(..., description="数据列表")


