"""
信号分析控制器
"""
from fastapi import APIRouter, Query, HTTPException, Depends
from typing import List, Optional
from datetime import datetime
from clickhouse_connect.driver import Client
from common.db.clickhouse_client import get_clickhouse_client
from stock.stock_signal.schemas.signal_schemas import (
    StockSignalInfo, 
    SignalAnalysisResponse
)
from loguru import logger
from config import config

# 创建信号分析路由器
router = APIRouter(tags=["股票信号分析"])

def _filter_last_day_signal(
    results: List[dict], 
    start_date: str, 
    end_date: str, 
    last_day_signal: str,
    client: Client
) -> List[dict]:
    """过滤最后一天信号条件"""
    filtered_results = []
    
    for result in results:
        code = result[0]  # code是第一个字段
        
        # 获取该股票最后一天的数据
        last_day_query = """
        SELECT best_buy, best_sell
        FROM stock_daily_k_i_read
        WHERE code = %(code)s 
            AND trade_date >= %(start_date)s 
            AND trade_date <= %(end_date)s
        ORDER BY trade_date DESC
        LIMIT 1
        """
        
        last_day_result = client.query(last_day_query, parameters={
            'code': code,
            'start_date': start_date,
            'end_date': end_date
        }).result_rows
        
        if last_day_result:
            last_day = last_day_result[0]
            if last_day_signal == "buy" and last_day[0] == 1:  # best_buy是第一个字段
                filtered_results.append(result)
            elif last_day_signal == "sell" and last_day[1] == 1:  # best_sell是第二个字段
                filtered_results.append(result)
    
    return filtered_results

def _filter_wr_condition(
    results: List[dict], 
    start_date: str, 
    end_date: str, 
    wr_condition: str, 
    wr_value: float,
    client: Client
) -> List[dict]:
    """过滤威廉指数条件"""
    filtered_results = []
    
    for result in results:
        code = result[0]  # code是第一个字段
        
        # 获取该股票最后一天的威廉指标
        wr_query = """
        SELECT wr6, wr10
        FROM stock_daily_k_i_read
        WHERE code = %(code)s 
            AND trade_date >= %(start_date)s 
            AND trade_date <= %(end_date)s
        ORDER BY trade_date DESC
        LIMIT 1
        """
        
        wr_result = client.query(wr_query, parameters={
            'code': code,
            'start_date': start_date,
            'end_date': end_date
        }).result_rows
        
        if wr_result:
            wr_data = wr_result[0]
            wr6_value = wr_data[0] if wr_data[0] is not None else None  # wr6是第一个字段
            wr10_value = wr_data[1] if wr_data[1] is not None else None  # wr10是第二个字段
            
            # 检查威廉指数条件
            satisfied = False
            if wr6_value is not None:
                if wr_condition == "lt" and wr6_value < wr_value:
                    satisfied = True
                elif wr_condition == "gt" and wr6_value > wr_value:
                    satisfied = True
                elif wr_condition == "lte" and wr6_value <= wr_value:
                    satisfied = True
                elif wr_condition == "gte" and wr6_value >= wr_value:
                    satisfied = True
            
            if wr10_value is not None and not satisfied:
                if wr_condition == "lt" and wr10_value < wr_value:
                    satisfied = True
                elif wr_condition == "gt" and wr10_value > wr_value:
                    satisfied = True
                elif wr_condition == "lte" and wr10_value <= wr_value:
                    satisfied = True
                elif wr_condition == "gte" and wr10_value >= wr_value:
                    satisfied = True
            
            if satisfied:
                filtered_results.append(result)
    
    return filtered_results

def _filter_price_range(
    results: List[dict], 
    start_date: str, 
    end_date: str, 
    price_min: float = None, 
    price_max: float = None,
    client: Client = None
) -> List[dict]:
    """过滤价格范围条件"""
    if client is None:
        client = next(get_clickhouse_client())
    filtered_results = []
    
    for result in results:
        code = result[0]  # code是第一个字段
        
        # 获取该股票在指定时间段内的价格数据
        price_query = """
        SELECT close_price
        FROM stock_daily_k_i_read
        WHERE code = %(code)s 
            AND trade_date >= %(start_date)s 
            AND trade_date <= %(end_date)s
        ORDER BY trade_date DESC
        LIMIT 1
        """
        
        price_result = client.query(price_query, parameters={
            'code': code,
            'start_date': start_date,
            'end_date': end_date
        }).result_rows
        
        if price_result:
            current_price = price_result[0][0]  # close_price是第一个字段
            
            # 检查价格范围条件
            price_satisfied = True
            if price_min is not None and current_price < price_min:
                price_satisfied = False
            if price_max is not None and current_price > price_max:
                price_satisfied = False
            
            if price_satisfied:
                filtered_results.append(result)
    
    return filtered_results

def _calculate_slope(prices: List[float]) -> float:
    """计算价格序列的线性回归斜率"""
    if len(prices) < 2:
        return 0.0
    
    n = len(prices)
    x_sum = sum(range(n))
    y_sum = sum(prices)
    xy_sum = sum(i * price for i, price in enumerate(prices))
    x2_sum = sum(i * i for i in range(n))
    
    # 线性回归斜率公式: slope = (n*xy_sum - x_sum*y_sum) / (n*x2_sum - x_sum*x_sum)
    denominator = n * x2_sum - x_sum * x_sum
    if denominator == 0:
        return 0.0
    
    slope = (n * xy_sum - x_sum * y_sum) / denominator
    return slope

def _filter_slope_direction(
    results: List[dict], 
    start_date: str, 
    end_date: str, 
    slope_direction: str, 
    slope_period: int,
    slope_threshold: float = None,
    client: Client = None
) -> List[dict]:
    """过滤斜率方向条件"""
    if not results:
        return []
    
    if client is None:
        client = next(get_clickhouse_client())
    
    # 提取所有股票代码
    codes = [result[0] for result in results]
    codes_str = "', '".join(codes)
    
    # 批量获取所有股票的价格数据
    price_query = f"""
    SELECT code, close_price, trade_date
    FROM stock_daily_k_i_read
    WHERE code IN ('{codes_str}')
        AND trade_date <= %(end_date)s
    ORDER BY code, trade_date DESC
    """
    
    price_result = client.query(price_query, parameters={
        'end_date': end_date
    }).result_rows
    
    # 按股票代码分组价格数据
    stock_prices = {}
    for row in price_result:
        code, price, date = row
        if code not in stock_prices:
            stock_prices[code] = []
        stock_prices[code].append((price, date))
    
    filtered_results = []
    
    for result in results:
        code = result[0]
        
        if code in stock_prices and len(stock_prices[code]) >= 2:
            # 取最近N天的价格数据
            recent_prices = stock_prices[code][:slope_period]
            
            # 按时间正序排列（从早到晚）
            prices = [row[0] for row in reversed(recent_prices)]
            
            # 计算斜率
            slope = _calculate_slope(prices)
            
            # 检查斜率方向条件
            slope_satisfied = False
            if slope_direction == "up" and slope > 0:
                slope_satisfied = True
            elif slope_direction == "down" and slope < 0:
                slope_satisfied = True
            
            # 如果设置了斜率阈值，检查斜率强度
            if slope_satisfied and slope_threshold is not None:
                if slope_direction == "up" and slope < slope_threshold:
                    slope_satisfied = False
                elif slope_direction == "down" and slope > -slope_threshold:
                    slope_satisfied = False
            
            if slope_satisfied:
                filtered_results.append(result)
    
    return filtered_results

@router.get("/stocks/signals/analysis", response_model=SignalAnalysisResponse, summary="分析股票信号（查找在指定时间段内买点卖点超过指定数量的股票）")
def analyze_stock_signals(
    start_date: str = Query(..., description="开始日期 YYYY-MM-DD"),
    end_date: str = Query(..., description="结束日期 YYYY-MM-DD"),
    min_signals: int = Query(1, description="最小信号数量，默认1"),
    signal_type: str = Query("all", description="信号类型: all(买卖合计)/buy(买点)/sell(卖点)"),
    last_day_signal: str = Query("any", description="最后一天信号: any(不限)/buy(买点)/sell(卖点)"),
    wr_condition: str = Query("none", description="威廉指数比较条件: none(不限)/lt(小于)/gt(大于)/lte(小于等于)/gte(大于等于)"),
    wr_value: float = Query(0.0, description="威廉指数阈值，默认0.0"),
    price_min: Optional[str] = Query(None, description="最低价格过滤，可选"),
    price_max: Optional[str] = Query(None, description="最高价格过滤，可选"),
    slope_direction: str = Query("any", description="斜率方向: any(不限)/up(上升)/down(下降)"),
    slope_period: int = Query(10, description="斜率计算周期（天数），默认10天"),
    slope_threshold: Optional[str] = Query(None, description="斜率阈值，可选，用于判断趋势强度"),
    limit: int = Query(10000, description="最大返回数量，默认10000，设为0表示不限制"),
    client: Client = Depends(get_clickhouse_client)
):
    """
    查找在指定时间段内买点卖点超过指定数量的所有股票。
    返回符合条件的股票列表及其信号统计信息。
    """
    try:
        
        # 处理价格参数：将空字符串转换为None，非空字符串转换为浮点数
        price_min_float = None
        if price_min is not None and price_min.strip():
            try:
                price_min_float = float(price_min)
            except ValueError:
                raise ValueError("price_min 必须是有效的数字")
        
        price_max_float = None
        if price_max is not None and price_max.strip():
            try:
                price_max_float = float(price_max)
            except ValueError:
                raise ValueError("price_max 必须是有效的数字")
        
        # 验证参数
        if signal_type not in ["all", "buy", "sell"]:
            raise ValueError("signal_type 仅支持 all/buy/sell")
        
        if last_day_signal not in ["any", "buy", "sell"]:
            raise ValueError("last_day_signal 仅支持 any/buy/sell")
        
        if wr_condition not in ["none", "lt", "gt", "lte", "gte"]:
            raise ValueError("wr_condition 仅支持 none/lt/gt/lte/gte")
        
        if slope_direction not in ["any", "up", "down"]:
            raise ValueError("slope_direction 仅支持 any/up/down")
        
        if slope_period < 2:
            raise ValueError("slope_period 必须大于等于2")
        
        if price_min_float is not None and price_max_float is not None and price_min_float > price_max_float:
            raise ValueError("price_min 不能大于 price_max")
        
        # 构建基础查询 - 使用合并视图提升性能
        base_query = """
        SELECT 
            code,
            name,
            sum(best_buy) as buy_signals,
            sum(best_sell) as sell_signals,
            count() as data_rows
        FROM stock_daily_k_i_read
        WHERE trade_date >= %(start_date)s AND trade_date <= %(end_date)s
        GROUP BY code, name
        """
        
        # 信号类型过滤
        if signal_type == "buy":
            base_query += " HAVING buy_signals >= %(min_signals)s"
        elif signal_type == "sell":
            base_query += " HAVING sell_signals >= %(min_signals)s"
        else:  # all
            base_query += " HAVING (buy_signals + sell_signals) >= %(min_signals)s"
        
        base_query += " ORDER BY (buy_signals + sell_signals) DESC"
        if limit > 0:
            base_query += " LIMIT %(limit)s"
        
        # 执行基础查询
        params = {
            'start_date': start_date,
            'end_date': end_date,
            'min_signals': min_signals
        }
        if limit > 0:
            params['limit'] = limit
        
        results = client.query(base_query, parameters=params).result_rows
        
        # 过滤最后一天信号条件
        if last_day_signal in ["buy", "sell"]:
            results = _filter_last_day_signal(results, start_date, end_date, last_day_signal, client)
        
        # 过滤威廉指数条件
        if wr_condition != "none":
            results = _filter_wr_condition(results, start_date, end_date, wr_condition, wr_value, client)
        
        # 后置过滤：价格范围过滤
        if price_min_float is not None or price_max_float is not None:
            results = _filter_price_range(results, start_date, end_date, price_min_float, price_max_float, client)
        
        # 后置过滤：斜率方向过滤
        if slope_direction != "any":
            # 处理斜率阈值参数
            slope_threshold_float = None
            if slope_threshold and slope_threshold.strip():
                try:
                    slope_threshold_float = float(slope_threshold)
                except ValueError:
                    raise ValueError("slope_threshold 必须是有效的数字")
            
            results = _filter_slope_direction(results, start_date, end_date, slope_direction, slope_period, slope_threshold_float, client)
        
        # 转换为响应格式
        stocks = []
        for result in results:
            # ClickHouse返回的是元组，需要按索引访问
            stocks.append(StockSignalInfo(
                code=result[0],  # code
                name=result[1],  # name
                buy_signals=int(result[2]),  # buy_signals
                sell_signals=int(result[3]),  # sell_signals
                total_signals=int(result[2]) + int(result[3]),  # buy_signals + sell_signals
                data_rows=int(result[4])  # data_rows
            ))
        
        # 获取总股票数
        total_stocks_query = "SELECT count(DISTINCT code) as total FROM stock_daily_k_i_read WHERE trade_date >= %(start_date)s AND trade_date <= %(end_date)s"
        total_result = client.query(total_stocks_query, parameters={
            'start_date': start_date,
            'end_date': end_date
        }).result_rows
        total_stocks = total_result[0][0] if total_result else 0
        
        return SignalAnalysisResponse(
            start_date=start_date,
            end_date=end_date,
            min_signals=min_signals,
            total_stocks_analyzed=total_stocks,
            matching_stocks=len(stocks),
            stocks=stocks
        )
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"分析股票信号失败: {e}")
        raise HTTPException(status_code=500, detail="分析股票信号失败")

@router.get("/stocks/signals/stats", summary="获取股票信号统计信息")
def get_signal_stats(
    start_date: str = Query(..., description="开始日期 YYYY-MM-DD"),
    end_date: str = Query(..., description="结束日期 YYYY-MM-DD"),
    client: Client = Depends(get_clickhouse_client)
):
    """获取信号统计信息"""
    try:
        
        query = """
        SELECT 
            sum(best_buy) as total_buy,
            sum(best_sell) as total_sell,
            count(DISTINCT code) as stock_count,
            count() as total_records
        FROM stock_daily_k_i_read
        WHERE trade_date >= %(start_date)s AND trade_date <= %(end_date)s
        """
        
        result = client.query(query, parameters={
            'start_date': start_date,
            'end_date': end_date
        }).result_rows
        
        if result:
            return {
                "code": 200,
                "message": "获取成功",
                "data": {
                    'total_buy': int(result[0][0] or 0),
                    'total_sell': int(result[0][1] or 0),
                    'stock_count': int(result[0][2] or 0),
                    'total_records': int(result[0][3] or 0)
                }
            }
        
        return {
            "code": 200,
            "message": "获取成功",
            "data": {
                'total_buy': 0,
                'total_sell': 0,
                'stock_count': 0,
                'total_records': 0
            }
        }
        
    except Exception as e:
        logger.error(f"获取信号统计失败: {e}")
        raise HTTPException(status_code=500, detail="获取信号统计失败")