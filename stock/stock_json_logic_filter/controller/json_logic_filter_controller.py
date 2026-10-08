"""
JSON Logic 过滤查询控制器
接收 JSON Logic 规则，转换为 ClickHouse SQL 并返回查询结果
"""
from typing import Any, Dict, List, Optional, Tuple
from datetime import date as _date, datetime as _datetime
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from clickhouse_connect.driver import Client
from loguru import logger
from common.db.clickhouse_client import get_clickhouse_client
from stock.stock_json_logic_filter.schemas.json_logic_schemas import (
    JsonLogicQuery,
    JsonLogicResult
)


# 路由分组
router = APIRouter(tags=["JSON Logic 查询"])


# ====== JSON Logic -> SQL 转换器 ======

class JsonLogicToSQL:
    """将 JSON Logic 规则转换为 ClickHouse SQL 的简易转换器。
    支持的运算符：
    - 逻辑：and, or, !/not
    - 比较：==, !=, >, >=, <, <=
    - 集合：in, nin (not in)
    - 空判断：is_null, not_null
    - like：like（值中可包含 % 通配）
    - between：{"between": ["field", min, max]}
    - 字面量获取：{"var": "field"}
    不处理计算型函数与聚合，保持简单通用。
    """

    def __init__(self, parameters: Optional[Dict[str, Any]] = None) -> None:
        self.parameters = parameters or {}

    def build_where(self, logic: Dict[str, Any]) -> Tuple[str, Dict[str, Any]]:
        params: Dict[str, Any] = {}
        where_sql = self._expr(logic, params)
        return where_sql if where_sql else "1", params

    def _expr(self, node: Any, params: Dict[str, Any]) -> str:
        if node is None:
            return ""
        if isinstance(node, (int, float)):
            key = self._add_param(params, node)
            return f"%({key})s"
        if isinstance(node, str):
            # 纯字符串作为常量
            key = self._add_param(params, node)
            return f"%({key})s"
        if isinstance(node, list):
            # 直接数组不支持，需由操作符包裹
            raise ValueError("JSON Logic 顶层不支持纯数组表达式")

        if not isinstance(node, dict) or len(node) == 0:
            return ""

        # 只取单一操作符
        if len(node) != 1:
            raise ValueError("JSON Logic 节点必须只包含一个操作符")

        op, val = next(iter(node.items()))
        op = op.lower()

        if op == "var":
            if isinstance(val, list):
                field = val[0]
            else:
                field = val
            return self._quote_ident(field)

        if op in ("and", "or"):
            if not isinstance(val, list) or len(val) == 0:
                return ""
            parts = [self._expr(v, params) for v in val if self._expr(v, params)]
            joiner = " AND " if op == "and" else " OR "
            return f"({joiner.join(parts)})" if parts else ""

        if op in ("!", "not"):
            inner = self._expr(val, params)
            return f"(NOT {inner})" if inner else ""

        # 比较运算
        if op in ("==", "=", "!=", ">", ">=", "<", "<="):
            if not isinstance(val, list) or len(val) != 2:
                raise ValueError(f"{op} 需要 [left, right]")
            left_sql = self._expr(val[0], params)
            right_sql = self._expr(val[1], params)
            real_op = "=" if op in ("==", "=") else op
            return f"({left_sql} {real_op} {right_sql})"

        if op == "in" or op == "nin":
            if not isinstance(val, list) or len(val) != 2:
                raise ValueError("in/nin 需要 [item, list]")
            item_sql = self._expr(val[0], params)
            items = val[1]
            if not isinstance(items, list) or len(items) == 0:
                return "(1=0)" if op == "in" else "(1=1)"
            keys: List[str] = []
            for v in items:
                keys.append(self._add_param(params, v))
            placeholder = ", ".join([f"%({k})s" for k in keys])
            operator = "IN" if op == "in" else "NOT IN"
            return f"({item_sql} {operator} ({placeholder}))"

        if op == "is_null":
            field_sql = self._expr(val, params)
            return f"({field_sql} IS NULL)"

        if op == "not_null":
            field_sql = self._expr(val, params)
            return f"({field_sql} IS NOT NULL)"

        if op == "like":
            if not isinstance(val, list) or len(val) != 2:
                raise ValueError("like 需要 [field, pattern]")
            field_sql = self._expr(val[0], params)
            patt_key = self._add_param(params, val[1])
            return f"({field_sql} LIKE %({patt_key})s)"

        if op == "between":
            if not isinstance(val, list) or len(val) != 3:
                raise ValueError("between 需要 [field, min, max]")
            field_sql = self._expr(val[0], params)
            min_key = self._add_param(params, val[1])
            max_key = self._add_param(params, val[2])
            return f"({field_sql} BETWEEN %({min_key})s AND %({max_key})s)"

        raise ValueError(f"不支持的操作符: {op}")

    def _add_param(self, params: Dict[str, Any], value: Any) -> str:
        key = f"p{len(params)}"
        
        # 布尔字段列表
        boolean_fields = {'best_buy', 'best_sell'}
        
        # 如果是布尔值，转换为0/1
        if isinstance(value, bool):
            params[key] = 1 if value else 0
        # 如果是日期字符串，保持原样（ClickHouse会自动转换）
        elif isinstance(value, str) and len(value) == 10 and value.count('-') == 2:
            params[key] = value
        else:
            params[key] = value
            
        return key

    def _quote_ident(self, name: str) -> str:
        if not isinstance(name, str) or not name:
            raise ValueError("字段名无效")
        # 简单列名/函数保护，不加反引号，避免 ClickHouse 标识符引号差异
        # 仅保留常见安全字符
        return name


# ====== 路由 ======

# 允许查询的安全表名列表
ALLOWED_TABLES = {
    "stock_daily_k_i_read",      # K线+指标合并视图
    "stock_daily_k_mf_read",     # K线+资金流向合并视图
    "stock_money_flow_read",     # 资金流向读视图
    "stock_daily_k_read",        # K线读视图
    "stock_daily_i_read",        # 指标读视图
    "stock_info"                 # 股票基础信息表
}

def validate_table_name(table_name: str) -> bool:
    """验证表名是否在允许的列表中"""
    return table_name in ALLOWED_TABLES

@router.post("/json-logic/query", summary="接收 JSON Logic 规则，转换为 SQL 并执行查询")
def query_by_json_logic(body: JsonLogicQuery, client: Client = Depends(get_clickhouse_client)):
    """接收 JSON Logic，转换为 SQL 并执行查询。"""
    try:
        if not body.table or not isinstance(body.logic, dict):
            raise ValueError("table 与 logic 为必填")
        
        # 验证表名安全性
        if not validate_table_name(body.table):
            raise ValueError(f"不允许查询表 '{body.table}'，允许的表名：{', '.join(ALLOWED_TABLES)}")

        select_cols = body.select or ["*"]
        select_sql = ", ".join(select_cols)

        translator = JsonLogicToSQL()
        where_sql, params = translator.build_where(body.logic)

        sql = f"SELECT {select_sql} FROM {body.table} WHERE {where_sql}"
        if body.order_by:
            sql += " ORDER BY " + ", ".join(body.order_by)
        if body.limit and body.limit > 0:
            sql += " LIMIT %(limit)s"
            params["limit"] = body.limit
            if body.offset and body.offset > 0:
                sql += " OFFSET %(offset)s"
                params["offset"] = body.offset

        logger.info(f"JSON Logic SQL: {sql} | params={params}")

        result = client.query(sql, parameters=params)
        # clickhouse_connect QueryResult: use column_names and result_rows
        columns = list(getattr(result, "column_names", []))
        rows = result.result_rows

        # 永远返回中文字段对象列表，保持与股票详情接口一致
        zh_map = {
            "code": "代码",
            "name": "股票名称",
            "trade_date": "日期",
            "open_price": "开盘",
            "close_price": "收盘",
            "high_price": "最高",
            "low_price": "最低",
            "volume": "成交量",
            "amount": "成交额",
            "amplitude": "振幅",
            "change_pct": "涨跌幅",
            "change_amount": "涨跌额",
            "turnover_rate": "换手率",
            "wr6": "WR6",
            "wr10": "WR10",
            "ma5": "MA5",
            "ma10": "MA10",
            "ma20": "MA20",
            "slope_180": "180日斜率",
            "slope_7": "7日斜率",
            "fit_7": "7日拟合值",
            "fit_180": "180日拟合值",
            "best_buy": "最佳买点",
            "best_sell": "最佳卖点",
            "buy_count_7": "7日买点数量",
            "sell_count_7": "7日卖点数量",
            "buy_count_14": "14日买点数量",
            "sell_count_14": "14日卖点数量",
            # 资金流向字段映射
            "main_net_inflow_amount": "主力净流入金额",
            "main_net_inflow_ratio": "主力净流入占比",
            "super_large_net_inflow_amount": "超大单净流入金额",
            "super_large_net_inflow_ratio": "超大单净流入占比",
            "large_net_inflow_amount": "大单净流入金额",
            "large_net_inflow_ratio": "大单净流入占比",
            "medium_net_inflow_amount": "中单净流入金额",
            "medium_net_inflow_ratio": "中单净流入占比",
            "small_net_inflow_amount": "小单净流入金额",
            "small_net_inflow_ratio": "小单净流入占比",
            # 合并视图中的资金流向字段（带mf_前缀）
            "mf_close_price": "资金流向收盘价",
            "mf_change_pct": "资金流向涨跌幅"
        }

        # 列名到下标
        name_to_idx = {c: i for i, c in enumerate(columns)}
        records: List[Dict[str, Any]] = []
        for row in rows:
            rec: Dict[str, Any] = {}
            for eng_name, zh_name in zh_map.items():
                if eng_name in name_to_idx:
                    rec[zh_name] = row[name_to_idx[eng_name]]
            records.append(rec)

        # 命中记录插入：仅在提供 rule_name 且结果包含 code 列时执行
        if body.rule_name:
            code_idx = name_to_idx.get("code")
            if code_idx is not None:
                # 命中超过500条则视为无效样本，不做命中记录插入
                if len(rows) > 1000:
                    logger.info(f"命中{len(rows)}条，超过阈值1000，跳过 stock_rule_hit 插入")
                    return {
                        "code": 200,
                        "message": "获取成功",
                        "data": records
                    }
                trade_idx = name_to_idx.get("trade_date")
                name_idx = name_to_idx.get("name")
                # 按月份分批插入，避免单次 INSERT 跨越过多分区
                buckets: Dict[str, List[Tuple[Any, Any, Any, Any]]] = {}
                for r in rows:
                    code_val = r[code_idx]
                    name_val = r[name_idx] if name_idx is not None else ""
                    # 规范 trade_date 为 Python date 对象，避免驱动对字符串的 Date 写入报错
                    tv_date = None
                    if trade_idx is not None:
                        tv_raw = r[trade_idx]
                        if isinstance(tv_raw, _date):
                            tv_date = tv_raw
                        elif hasattr(tv_raw, "date"):
                            tv_date = tv_raw.date()
                        elif isinstance(tv_raw, str) and len(tv_raw) == 10 and tv_raw.count('-') == 2:
                            tv_date = _date.fromisoformat(tv_raw)
                    if tv_date is None:
                        tv_date = _date(1970, 1, 1)
                    month_key = tv_date.strftime("%Y-%m")
                    buckets.setdefault(month_key, []).append((str(code_val), str(name_val), body.rule_name, tv_date))
                for _mk, insert_rows in buckets.items():
                    if insert_rows:
                        client.insert(
                            "stock_rule_hit",
                            insert_rows,
                            column_names=["code", "name", "rule_name", "trade_date"],
                        )

        return {
            "code": 200,
            "message": "获取成功",
            "data": records
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"JSON Logic 查询失败: {e}")
        raise HTTPException(status_code=500, detail="查询失败")


