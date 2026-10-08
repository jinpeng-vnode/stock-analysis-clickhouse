"""
资金流向数据控制器
"""
from fastapi import APIRouter, Query, HTTPException, Depends
from typing import List, Optional
from datetime import date, datetime, timedelta
from clickhouse_connect.driver import Client
from common.db.clickhouse_client import get_clickhouse_client
from stock.stock_money_flow.schemas.money_flow_schemas import (
    MoneyFlowData,
    MoneyFlowResponse,
    MoneyFlowStatsResponse,
    MoneyFlowTopItem,
    MoneyFlowTopResponse
)
from loguru import logger
from config import config

# 创建资金流向路由器
router = APIRouter(tags=["资金流向"])

@router.get("/money-flow/stats", response_model=MoneyFlowStatsResponse, summary="获取股票资金流向数据统计信息")
def get_money_flow_stats(client: Client = Depends(get_clickhouse_client)):
    """
    获取资金流向数据统计信息
    """
    try:
        # 总记录数
        total_query = "SELECT count() FROM stock_money_flow_read"
        total_result = client.query(total_query).result_rows
        total_records = total_result[0][0] if total_result else 0
        
        # 日期范围
        date_range_query = """
        SELECT 
            min(trade_date) as min_date,
            max(trade_date) as max_date
        FROM stock_money_flow_read
        """
        date_range_result = client.query(date_range_query).result_rows
        if date_range_result and date_range_result[0][0]:
            date_range = {
                'min_date': str(date_range_result[0][0]),
                'max_date': str(date_range_result[0][1])
            }
        else:
            date_range = {'min_date': None, 'max_date': None}
        
        # 有资金流向数据的股票数量
        stocks_query = """
        SELECT count(DISTINCT code) 
        FROM stock_money_flow_read
        """
        stocks_result = client.query(stocks_query).result_rows
        stocks_with_data = stocks_result[0][0] if stocks_result else 0
        
        # 最新数据日期
        latest_query = """
        SELECT max(trade_date) 
        FROM stock_money_flow_read
        """
        latest_result = client.query(latest_query).result_rows
        latest_update = str(latest_result[0][0]) if latest_result and latest_result[0][0] else None
        
        return MoneyFlowStatsResponse(
            total_records=total_records,
            date_range=date_range,
            stocks_with_data=stocks_with_data,
            latest_update=latest_update
        )
        
    except Exception as e:
        logger.error(f"获取资金流向统计信息失败: {e}")
        raise HTTPException(status_code=500, detail="获取统计信息失败")

@router.get("/money-flow/top", response_model=MoneyFlowTopResponse, summary="获取股票资金流向排行榜")
def get_money_flow_top(
    trade_date: Optional[date] = Query(None, description="统计日期，默认为最新日期"),
    limit: int = Query(20, description="排行榜数量", le=100),
    client: Client = Depends(get_clickhouse_client)
):
    """
    获取资金流向排行榜
    """
    try:
        # 如果没有指定日期，使用最新日期
        if not trade_date:
            latest_date_query = "SELECT max(trade_date) FROM stock_money_flow_read"
            latest_date_result = client.query(latest_date_query).result_rows
            if not latest_date_result or not latest_date_result[0][0]:
                raise HTTPException(status_code=404, detail="没有找到资金流向数据")
            trade_date = latest_date_result[0][0]
        
        # 获取净流入排行榜
        inflow_query = """
        SELECT 
            mf.code,
            si.name,
            mf.trade_date,
            mf.close_price,
            mf.change_pct,
            mf.main_net_inflow_amount,
            mf.main_net_inflow_ratio
        FROM stock_money_flow_read mf
        LEFT JOIN stock_info si ON mf.code = si.code
        WHERE mf.trade_date = %(trade_date)s
            AND mf.main_net_inflow_amount > 0
        ORDER BY mf.main_net_inflow_amount DESC
        LIMIT %(limit)s
        """
        
        inflow_result = client.query(
            inflow_query,
            parameters={'trade_date': trade_date, 'limit': limit}
        ).result_rows
        
        top_inflow = []
        for row in inflow_result:
            top_inflow.append(MoneyFlowTopItem(
                code=row[0],
                name=row[1] or row[0],  # 如果没有名称，使用代码
                trade_date=row[2],
                close_price=row[3],
                change_pct=row[4],
                main_net_inflow_amount=row[5],
                main_net_inflow_ratio=row[6]
            ))
        
        # 获取净流出排行榜
        outflow_query = """
        SELECT 
            mf.code,
            si.name,
            mf.trade_date,
            mf.close_price,
            mf.change_pct,
            mf.main_net_inflow_amount,
            mf.main_net_inflow_ratio
        FROM stock_money_flow_read mf
        LEFT JOIN stock_info si ON mf.code = si.code
        WHERE mf.trade_date = %(trade_date)s
            AND mf.main_net_inflow_amount < 0
        ORDER BY mf.main_net_inflow_amount ASC
        LIMIT %(limit)s
        """
        
        outflow_result = client.query(
            outflow_query,
            parameters={'trade_date': trade_date, 'limit': limit}
        ).result_rows
        
        top_outflow = []
        for row in outflow_result:
            top_outflow.append(MoneyFlowTopItem(
                code=row[0],
                name=row[1] or row[0],  # 如果没有名称，使用代码
                trade_date=row[2],
                close_price=row[3],
                change_pct=row[4],
                main_net_inflow_amount=row[5],
                main_net_inflow_ratio=row[6]
            ))
        
        # 获取总股票数量
        total_stocks_query = """
        SELECT count(DISTINCT code) 
        FROM stock_money_flow_read 
        WHERE trade_date = %(trade_date)s
        """
        total_stocks_result = client.query(
            total_stocks_query,
            parameters={'trade_date': trade_date}
        ).result_rows
        total_stocks = total_stocks_result[0][0] if total_stocks_result else 0
        
        return MoneyFlowTopResponse(
            date=str(trade_date),
            total_stocks=total_stocks,
            top_inflow=top_inflow,
            top_outflow=top_outflow
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取资金流向排行榜失败: {e}")
        raise HTTPException(status_code=500, detail="获取排行榜失败")

@router.get("/money-flow/batch", response_model=List[MoneyFlowResponse], summary="批量获取多只股票的资金流向数据")
def get_batch_money_flow_data(
    codes: str = Query(..., description="股票代码列表，用逗号分隔"),
    start_date: Optional[date] = Query(None, description="开始日期"),
    end_date: Optional[date] = Query(None, description="结束日期"),
    limit: int = Query(50, description="每只股票返回数量限制", le=config.MAX_QUERY_LIMIT),
    client: Client = Depends(get_clickhouse_client)
):
    """
    批量获取多只股票的资金流向数据
    """
    try:
        # 解析股票代码列表
        code_list = [code.strip() for code in codes.split(',') if code.strip()]
        if not code_list:
            raise HTTPException(status_code=400, detail="股票代码列表不能为空")
        
        if len(code_list) > 20:  # 限制批量查询数量
            raise HTTPException(status_code=400, detail="批量查询股票数量不能超过20只")
        
        # 验证股票代码格式
        for code in code_list:
            if len(code) != 6 or not code.isdigit():
                raise HTTPException(status_code=400, detail=f"股票代码{code}格式错误")
        
        # 设置默认日期范围
        if not end_date:
            end_date = date.today()
        if not start_date:
            start_date = end_date - timedelta(days=7)
        
        results = []
        
        for code in code_list:
            try:
                # 获取单只股票数据（复用上面的逻辑）
                response = get_money_flow_data(
                    code=code,
                    start_date=start_date,
                    end_date=end_date,
                    limit=limit,
                    client=client
                )
                results.append(response)
            except HTTPException as e:
                if e.status_code == 404:
                    logger.warning(f"股票{code}不存在，跳过")
                    continue
                else:
                    raise
        
        return results
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"批量获取资金流向数据失败: {e}")
        raise HTTPException(status_code=500, detail="批量获取资金流向数据失败")

@router.get("/money-flow/{code}", response_model=MoneyFlowResponse, summary="获取指定股票的资金流向数据")
def get_money_flow_data(
    code: str,
    start_date: Optional[date] = Query(None, description="开始日期"),
    end_date: Optional[date] = Query(None, description="结束日期"),
    limit: int = Query(100, description="返回数量限制", le=config.MAX_QUERY_LIMIT),
    client: Client = Depends(get_clickhouse_client)
):
    """
    获取指定股票的资金流向数据
    """
    try:
        # 验证股票代码
        if not code or len(code) != 6 or not code.isdigit():
            raise HTTPException(status_code=400, detail="股票代码格式错误")
        
        # 设置默认日期范围（最近30天）
        if not end_date:
            end_date = date.today()
        if not start_date:
            start_date = end_date - timedelta(days=30)
        
        # 获取股票名称
        stock_name_query = "SELECT name FROM stock_info WHERE code = %(code)s"
        stock_name_result = client.query(stock_name_query, parameters={'code': code}).result_rows
        if not stock_name_result:
            raise HTTPException(status_code=404, detail="股票不存在")
        stock_name = stock_name_result[0][0]
        
        # 构建查询SQL
        query = """
        SELECT 
            code,
            trade_date,
            close_price,
            change_pct,
            main_net_inflow_amount,
            main_net_inflow_ratio,
            super_large_net_inflow_amount,
            super_large_net_inflow_ratio,
            large_net_inflow_amount,
            large_net_inflow_ratio,
            medium_net_inflow_amount,
            medium_net_inflow_ratio,
            small_net_inflow_amount,
            small_net_inflow_ratio
        FROM stock_money_flow_read
        WHERE code = %(code)s
            AND trade_date >= %(start_date)s
            AND trade_date <= %(end_date)s
        ORDER BY trade_date DESC
        LIMIT %(limit)s
        """
        
        # 执行查询
        result = client.query(
            query,
            parameters={
                'code': code,
                'start_date': start_date,
                'end_date': end_date,
                'limit': limit
            }
        ).result_rows
        
        # 转换数据
        money_flow_data = []
        for row in result:
            money_flow_data.append(MoneyFlowData(
                code=row[0],
                trade_date=row[1],
                close_price=row[2],
                change_pct=row[3],
                main_net_inflow_amount=row[4],
                main_net_inflow_ratio=row[5],
                super_large_net_inflow_amount=row[6],
                super_large_net_inflow_ratio=row[7],
                large_net_inflow_amount=row[8],
                large_net_inflow_ratio=row[9],
                medium_net_inflow_amount=row[10],
                medium_net_inflow_ratio=row[11],
                small_net_inflow_amount=row[12],
                small_net_inflow_ratio=row[13]
            ))
        
        # 获取总记录数
        count_query = """
        SELECT count()
        FROM stock_money_flow_read
        WHERE code = %(code)s
            AND trade_date >= %(start_date)s
            AND trade_date <= %(end_date)s
        """
        count_result = client.query(
            count_query,
            parameters={
                'code': code,
                'start_date': start_date,
                'end_date': end_date
            }
        ).result_rows
        total_records = count_result[0][0] if count_result else 0
        
        return MoneyFlowResponse(
            code=code,
            name=stock_name,
            total_records=total_records,
            data=money_flow_data
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取股票{code}资金流向数据失败: {e}")
        raise HTTPException(status_code=500, detail="获取资金流向数据失败")

@router.get("/money-flow/analysis/{code}", summary="获取股票资金流向分析数据（包含多日净流入统计）")
def get_money_flow_analysis(
    code: str,
    days: int = Query(30, description="分析天数", le=365),
    client: Client = Depends(get_clickhouse_client)
):
    """
    获取股票资金流向分析数据（包含多日净流入统计）
    """
    try:
        # 验证股票代码
        if not code or len(code) != 6 or not code.isdigit():
            raise HTTPException(status_code=400, detail="股票代码格式错误")
        
        # 获取股票名称
        stock_name_query = "SELECT name FROM stock_info WHERE code = %(code)s"
        stock_name_result = client.query(stock_name_query, parameters={'code': code}).result_rows
        if not stock_name_result:
            raise HTTPException(status_code=404, detail="股票不存在")
        stock_name = stock_name_result[0][0]
        
        # 获取最近N天的资金流向数据
        query = """
        SELECT 
            trade_date,
            close_price,
            change_pct,
            main_net_inflow_amount,
            main_net_inflow_ratio,
            super_large_net_inflow_amount,
            large_net_inflow_amount,
            medium_net_inflow_amount,
            small_net_inflow_amount
        FROM stock_money_flow_read
        WHERE code = %(code)s
        ORDER BY trade_date DESC
        LIMIT %(days)s
        """
        
        result = client.query(
            query,
            parameters={'code': code, 'days': days}
        ).result_rows
        
        if not result:
            raise HTTPException(status_code=404, detail="没有找到资金流向数据")
        
        # 计算多日净流入统计
        data = []
        for i, row in enumerate(result):
            trade_date = row[0]
            close_price = row[1]
            change_pct = row[2]
            main_net_inflow = row[3]
            main_net_ratio = row[4]
            super_large_net = row[5]
            large_net = row[6]
            medium_net = row[7]
            small_net = row[8]
            
            # 计算3日、5日、10日、20日净流入
            net_3d = sum(r[3] for r in result[i:i+3] if i+3 <= len(result))
            net_5d = sum(r[3] for r in result[i:i+5] if i+5 <= len(result))
            net_10d = sum(r[3] for r in result[i:i+10] if i+10 <= len(result))
            net_20d = sum(r[3] for r in result[i:i+20] if i+20 <= len(result))
            
            data.append({
                'trade_date': str(trade_date),
                'close_price': close_price,
                'change_pct': change_pct,
                'main_net_inflow_amount': main_net_inflow,
                'main_net_inflow_ratio': main_net_ratio,
                'super_large_net_inflow_amount': super_large_net,
                'large_net_inflow_amount': large_net,
                'medium_net_inflow_amount': medium_net,
                'small_net_inflow_amount': small_net,
                'net_inflow_3d': net_3d,
                'net_inflow_5d': net_5d,
                'net_inflow_10d': net_10d,
                'net_inflow_20d': net_20d
            })
        
        return {
            'code': code,
            'name': stock_name,
            'analysis_days': days,
            'total_records': len(data),
            'data': data
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取股票{code}资金流向分析失败: {e}")
        raise HTTPException(status_code=500, detail="获取资金流向分析失败")
