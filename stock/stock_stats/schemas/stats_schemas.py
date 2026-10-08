"""
统计信息相关 Pydantic 模型（从 models/stock_models.py 提取）
"""
from typing import Dict, Optional
from pydantic import BaseModel, Field


class StatsResponse(BaseModel):
    """统计信息响应模型"""
    stocks: int = Field(..., description="股票数量")
    daily_records: int = Field(..., description="日K线记录数")
    date_range: Dict[str, Optional[str]] = Field(..., description="数据日期范围")
    signals: Dict[str, int] = Field(..., description="信号统计")
    table_sizes: Dict[str, str] = Field(..., description="表大小信息")

