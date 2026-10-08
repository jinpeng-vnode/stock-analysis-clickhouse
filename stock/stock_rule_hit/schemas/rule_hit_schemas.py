"""
规则命中查询相关 Pydantic 模型（从 controllers/rule_hit_controller.py 提取）
"""
from typing import Optional, List
from pydantic import BaseModel, Field


class RuleTag(BaseModel):
    rule_name: str = Field(..., description="规则名称")
    hit_count: int = Field(..., description="命中次数")


class RuleHitStock(BaseModel):
    code: str
    name: Optional[str] = None
    hit_count: int


class RuleHitDetail(BaseModel):
    code: str
    name: Optional[str] = None
    rule_name: str
    trade_date: Optional[str] = None
    hit_time: str

