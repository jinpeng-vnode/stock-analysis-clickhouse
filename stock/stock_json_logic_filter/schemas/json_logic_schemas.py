"""
JSON Logic 查询相关 Pydantic 模型（从 controllers/json_logic_filter_controller.py 提取）
"""
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class JsonLogicQuery(BaseModel):
    table: str = Field(..., description="查询的表或视图名称，支持：stock_daily_k_i_read（K线+指标）、stock_daily_k_mf_read（K线+资金流向）、stock_money_flow_read（资金流向）、stock_daily_k_read（K线）、stock_daily_i_read（指标）")
    logic: Dict[str, Any] = Field(..., description="JSON Logic 规则对象")
    select: Optional[List[str]] = Field(None, description="要返回的列，默认 ['*']")
    order_by: Optional[List[str]] = Field(None, description="排序字段，例 ['trade_date desc','code asc']")
    limit: Optional[int] = Field(1000, description="最大返回行数，默认1000，0 或 None 表示不限制")
    offset: Optional[int] = Field(0, description="偏移量，默认0")
    rule_name: Optional[str] = Field(None, alias="ruleName", description="规则名称，用于记录命中关系")


class JsonLogicResult(BaseModel):
    rows: int = Field(..., description="返回行数")
    columns: List[str] = Field(..., description="列名")
    data: List[List[Any]] = Field(..., description="二维数组结果")
    sql: str = Field(..., description="转换后的 SQL 语句")
    records: Optional[List[Dict[str, Any]]] = Field(None, description="对象列表结果（可选）")

