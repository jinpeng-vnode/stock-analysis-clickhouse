"""
股票数据控制器
"""
import math
from fastapi import APIRouter, Query, HTTPException, Depends
from typing import List, Optional
from datetime import date, datetime
from clickhouse_connect.driver import Client
from common.db.clickhouse_client import get_clickhouse_client
from stock.stocks.schemas.stock_schemas import (
    StockInfo, 
    StockDaily, 
    StockListResponse, 
    StockDailyResponse,
    DayDataResponse,
    StockItem
)
from loguru import logger
from config import config

# 创建股票数据路由器
router = APIRouter(tags=["股票数据"])

@router.get("/stocks", response_model=list[StockItem], summary="获取可搜索的股票代码列表")
def list_stocks(
    q: str | None = Query(None, description="搜索关键词，按代码或名称包含匹配"),
    client: Client = Depends(get_clickhouse_client)
):
    """
    可搜索的股票代码列表，支持按代码或名称模糊匹配。
    """
    try:
        
        if q and q.strip():
            # 如果有搜索关键词，使用搜索功能
            result = search_stocks(keyword=q.strip(), client=client)
            return [StockItem(code=stock.code, name=stock.name) for stock in result]
        else:
            # 否则返回所有股票列表
            result = get_stock_list(limit=1000, offset=0, client=client)
            return [StockItem(code=stock.code, name=stock.name) for stock in result.stocks]
    except Exception as e:
        logger.error(f"获取股票列表失败: {e}")
        raise HTTPException(status_code=500, detail="获取股票列表失败")

@router.get("/stocks/search", summary="搜索股票")
def search_stocks_api(
    keyword: str = Query(..., description="搜索关键词"),
    limit: int = Query(100, description="返回数量限制", le=config.MAX_QUERY_LIMIT)
):
    """搜索股票"""
    try:
        stocks = search_stocks(keyword=keyword, limit=limit)
        return {
            "code": 200,
            "message": "搜索成功",
            "data": {
                "total": len(stocks),
                "stocks": [stock.dict() for stock in stocks]
            }
        }
    except Exception as e:
        logger.error(f"搜索股票失败: {e}")
        raise HTTPException(status_code=500, detail="搜索股票失败")

@router.get("/stocks/{code}", summary="获取股票详细信息")
def get_stock_info(code: str):
    """获取股票详细信息"""
    try:
        stock = get_stock_by_code(code)
        if not stock:
            raise HTTPException(status_code=404, detail="股票不存在")
        
        return {
            "code": 200,
            "message": "获取成功",
            "data": stock.dict()
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取股票信息失败: {e}")
        raise HTTPException(status_code=500, detail="获取股票信息失败")

@router.get("/stocks/{code}/daily", response_model=DayDataResponse, summary="获取指定股票的日线数据")
def get_stock_daily(
    code: str,
    start: str | None = Query(None, description="开始日期 YYYY-MM-DD，可选"),
    end: str | None = Query(None, description="结束日期 YYYY-MM-DD，可选"),
    client: Client = Depends(get_clickhouse_client)
):
    """
    返回指定股票的日线数据。
    可选按开始/结束日期进行过滤。
    """
    try:
        result = get_stock_daily_data(
            code=code,
            start_date=start,
            end_date=end,
            client=client
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"获取股票日K线数据失败: {e}")
        raise HTTPException(status_code=500, detail="获取股票日K线数据失败")

@router.get("/stocks/{code}/day/{date}", response_model=DayDataResponse, summary="根据股票代码与日期返回当日分钟级数据")
def get_stock_day(code: str, date: str):
    """
    根据股票代码与日期(支持 YYYYMMDD 或 YYYY-MM-DD)返回当日分钟级数据。
    数据来源: 股票分析/数据/<code>_<中文名>/<YYYY-MM-DD>.csv
    """
    try:
        # ClickHouse版本暂时返回日K线数据，因为分钟级数据需要额外实现
        result = get_stock_daily_data(
            code=code,
            start_date=date,
            end_date=date
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"获取股票分钟级数据失败: {e}")
        raise HTTPException(status_code=500, detail="获取股票分钟级数据失败")

def get_stock_list(limit: int = 1000, offset: int = 0, client: Client = None) -> StockListResponse:
    """获取股票列表"""
    try:
        if client is None:
            client = next(get_clickhouse_client())
        
        query = """
        SELECT 
            code,
            name,
            market,
            status,
            version
        FROM stock_info
        ORDER BY code
        LIMIT %(limit)s OFFSET %(offset)s
        """
        
        result = client.query(query, parameters={
            'limit': limit,
            'offset': offset
        }).result_rows
        
        # ClickHouse返回的是元组，需要转换为字典
        stocks = []
        for row in result:
            stock_data = {
                'code': row[0],
                'name': row[1], 
                'market': row[2],
                'status': row[3],
                'version': row[4]
            }
            stocks.append(StockInfo(**stock_data))
        
        # 获取总数
        count_query = "SELECT count() as total FROM stock_info"
        total_result = client.query(count_query).result_rows
        total = total_result[0][0] if total_result else 0
        
        return StockListResponse(total=total, stocks=stocks)
        
    except Exception as e:
        logger.error(f"获取股票列表失败: {e}")
        raise

def get_stock_daily_data(
    code: str, 
    start_date: Optional[str] = None, 
    end_date: Optional[str] = None,
    client: Client = None
) -> DayDataResponse:
    """获取股票日K线数据"""
    try:
        if client is None:
            client = next(get_clickhouse_client())
        
        # 构建查询条件
        where_conditions = ["code = %(code)s"]
        params = {'code': code}
        
        if start_date:
            where_conditions.append("trade_date >= %(start_date)s")
            params['start_date'] = start_date
        
        if end_date:
            where_conditions.append("trade_date <= %(end_date)s")
            params['end_date'] = end_date
        
        where_clause = " AND ".join(where_conditions)
        
        query = f"""
        SELECT 
            code,
            trade_date,
            name,
            open_price,
            close_price,
            high_price,
            low_price,
            volume,
            amount,
            amplitude,
            change_pct,
            change_amount,
            turnover_rate,
            wr6,
            wr10,
            ma5,
            ma10,
            ma20,
            slope_180,
            slope_7,
            fit_7,
            fit_180,
            best_buy,
            best_sell,
            buy_count_7,
            sell_count_7,
            buy_count_14,
            sell_count_14,
            version
        FROM stock_daily_k_i_read
        WHERE {where_clause}
        ORDER BY trade_date ASC
        """
        
        result = client.query(query, parameters=params).result_rows
        
        # 获取股票名称（如果结果为空）
        if not result:
            name_query = "SELECT name FROM stock_info WHERE code = %(code)s"
            name_result = client.query(name_query, parameters={'code': code}).result_rows
            stock_name = name_result[0][0] if name_result else code
        else:
            stock_name = result[0][2]  # name是第3个字段
        
        # 小数统一保留两位精度，保持数值类型
        def round2(val):
            if val is None:
                return None
            try:
                float_val = float(val)
                # 检查是否为特殊浮点值
                if math.isnan(float_val) or math.isinf(float_val):
                    return None
                return round(float_val, 2)
            except (ValueError, TypeError):
                return None

        # ClickHouse返回的是元组，需要转换为字典列表（包含所有技术指标）
        data = []
        for row in result:
            daily_data = {
                '日期': str(row[1]),  # 使用中文列名
                '开盘': round2(row[3]),
                '收盘': round2(row[4]),
                '最高': round2(row[5]),
                '最低': round2(row[6]),
                '成交量': row[7],
                '成交额': round2(row[8]),
                '振幅': round2(row[9]),
                '涨跌幅': round2(row[10]),
                '涨跌额': round2(row[11]),
                '换手率': round2(row[12]),
                'WR6': round2(row[13]),
                'WR10': round2(row[14]),
                'MA5': round2(row[15]),
                'MA10': round2(row[16]),
                'MA20': round2(row[17]),
                '180日斜率': round2(row[18]),
                '7日斜率': round2(row[19]),
                '7日拟合值': round2(row[20]),
                '180日拟合值': round2(row[21]),
                '最佳买点': bool(row[22]),
                '最佳卖点': bool(row[23]),
                '7日买点数量': row[24],
                '7日卖点数量': row[25],
                '14日买点数量': row[26],
                '14日卖点数量': row[27]
            }
            data.append(daily_data)
        
        # 生成日期标签
        date_label = f"{start_date or ''}~{end_date or ''}".strip('~')
        if not date_label:
            date_label = "全部"
        
        return DayDataResponse(
            code=code,
            date=date_label,
            name=stock_name,
            rows=len(data),
            data=data
        )
        
    except Exception as e:
        logger.error(f"获取股票日K线数据失败: {e}")
        raise

def get_stock_by_code(code: str) -> Optional[StockInfo]:
    """根据代码获取股票信息"""
    try:
        client = next(get_clickhouse_client())
        
        query = """
        SELECT 
            code,
            name,
            market,
            status,
            version
        FROM stock_info
        WHERE code = %(code)s
        """
        
        result = client.query(query, parameters={'code': code}).result_rows
        
        if result:
            row = result[0]
            stock_data = {
                'code': row[0],
                'name': row[1], 
                'market': row[2],
                'status': row[3],
                'version': row[4]
            }
            return StockInfo(**stock_data)
        return None
        
    except Exception as e:
        logger.error(f"获取股票信息失败: {e}")
        raise

def search_stocks(keyword: str, limit: int = 100, client: Client = None) -> List[StockInfo]:
    """搜索股票"""
    try:
        if client is None:
            client = next(get_clickhouse_client())
        
        query = """
        SELECT 
            code,
            name,
            market,
            status,
            version
        FROM stock_info
        WHERE code LIKE %(keyword)s OR name LIKE %(keyword)s
        ORDER BY code
        LIMIT %(limit)s
        """
        
        result = client.query(query, parameters={
            'keyword': f'%{keyword}%',
            'limit': limit
        }).result_rows
        
        stocks = []
        for row in result:
            stock_data = {
                'code': row[0],
                'name': row[1], 
                'market': row[2],
                'status': row[3],
                'version': row[4]
            }
            stocks.append(StockInfo(**stock_data))
        return stocks
        
    except Exception as e:
        logger.error(f"搜索股票失败: {e}")
        raise

def get_stock_latest_data(code: str) -> Optional[StockDaily]:
    """获取股票最新数据"""
    try:
        client = next(get_clickhouse_client())
        
        query = """
        SELECT 
            code,
            trade_date,
            name,
            open_price,
            close_price,
            high_price,
            low_price,
            volume,
            amount,
            amplitude,
            change_pct,
            change_amount,
            turnover_rate,
            version
        FROM stock_daily_k_i_read
        WHERE code = %(code)s
        ORDER BY trade_date DESC
        LIMIT 1
        """
        
        result = client.query(query, parameters={'code': code}).result_rows
        
        if result:
            return StockDaily(**result[0])
        return None
        
    except Exception as e:
        logger.error(f"获取股票最新数据失败: {e}")
        raise

def get_stock_data_count(code: str) -> int:
    """获取股票数据条数"""
    try:
        client = next(get_clickhouse_client())
        
        query = "SELECT count() as total FROM stock_daily_k_i_read WHERE code = %(code)s"
        result = client.query(query, parameters={'code': code}).result_rows
        return result[0][0] if result else 0
        
    except Exception as e:
        logger.error(f"获取股票数据条数失败: {e}")
        raise

