from typing import Any, Dict, List, Optional
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from clickhouse_connect.driver import Client
from common.db.clickhouse_client import get_clickhouse_client
from stock.stock_rule_hit.schemas.rule_hit_schemas import (
    RuleTag,
    RuleHitStock,
    RuleHitDetail
)


router = APIRouter(prefix="/rule-hits", tags=["规则命中查询"])


@router.get("/tags", response_model=List[RuleTag], summary="获取股票规则标签列表")
def list_rule_tags(
    days: int = Query(30, ge=1, le=3650, description="统计最近N天（按hit_time过滤）")
    , client: Client = Depends(get_clickhouse_client)
):
    cutoff = datetime.now() - timedelta(days=days)
    params: Dict[str, Any] = {"cut": cutoff}
    sql = f"""
        SELECT rule_name, count() AS hit_count
        FROM stock_rule_hit
        WHERE hit_time >= %(cut)s
        GROUP BY rule_name
        ORDER BY hit_count DESC
    """
    rs = client.query(sql, parameters=params)
    rows = rs.result_rows
    return [RuleTag(rule_name=r[0], hit_count=r[1]) for r in rows]


@router.get("/stocks", response_model=List[RuleHitStock], summary="获取命中指定规则的股票列表")
def list_hit_stocks(
    rule_name: str = Query(..., description="规则名称"),
    days: int = Query(30, ge=1, le=3650, description="统计最近N天（按hit_time过滤）")
    , client: Client = Depends(get_clickhouse_client)
):
    cutoff = datetime.now() - timedelta(days=days)
    params: Dict[str, Any] = {"rn": rule_name, "cut": cutoff}
    sql = f"""
        SELECT code, anyOrNull(name) AS name, count() AS hit_count
        FROM stock_rule_hit
        WHERE rule_name = %(rn)s AND hit_time >= %(cut)s
        GROUP BY code
        ORDER BY hit_count DESC
    """
    rs = client.query(sql, parameters=params)
    rows = rs.result_rows
    return [RuleHitStock(code=r[0], name=r[1], hit_count=r[2]) for r in rows]


@router.get("/stock/{code}", response_model=List[RuleHitDetail], summary="获取指定股票的规则命中详情列表")
def list_stock_hit_details(
    code: str,
    days: int = Query(30, ge=1, le=3650, description="统计最近N天（按hit_time过滤）")
    , client: Client = Depends(get_clickhouse_client)
):
    cutoff = datetime.now() - timedelta(days=days)
    params: Dict[str, Any] = {"cd": code, "cut": cutoff}
    sql = f"""
        SELECT code, name, rule_name, toString(trade_date) AS trade_date, toString(hit_time) AS hit_time
        FROM stock_rule_hit
        WHERE code = %(cd)s AND hit_time >= %(cut)s
        ORDER BY hit_time DESC
    """
    rs = client.query(sql, parameters=params)
    rows = rs.result_rows
    return [RuleHitDetail(code=r[0], name=r[1], rule_name=r[2], trade_date=r[3], hit_time=r[4]) for r in rows]

