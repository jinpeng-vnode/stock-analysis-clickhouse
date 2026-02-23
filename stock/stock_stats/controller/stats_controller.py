"""
统计信息控制器
"""
from fastapi import APIRouter, HTTPException, Depends
from typing import Dict, Any
from clickhouse_connect.driver import Client
from common.db.clickhouse_client import get_clickhouse_client
from stock.stock_stats.schemas.stats_schemas import StatsResponse
from loguru import logger

# 创建统计信息路由器
router = APIRouter(tags=["统计信息"])

@router.get("/stats", summary="获取数据库统计信息")
def get_stats(client: Client = Depends(get_clickhouse_client)):
    """获取数据库统计信息"""
    try:
        
        # 股票数量
        stock_count_query = "SELECT count() as total FROM stock_info"
        stock_count_result = client.query(stock_count_query).result_rows
        stock_count = stock_count_result[0][0] if stock_count_result else 0
        
        # 日K线记录数
        daily_count_query = "SELECT count() as total FROM stock_daily_k_read"
        daily_count_result = client.query(daily_count_query).result_rows
        daily_count = daily_count_result[0][0] if daily_count_result else 0
        
        # 数据日期范围
        date_range_query = """
        SELECT 
            min(trade_date) as min_date,
            max(trade_date) as max_date
        FROM stock_daily_k_read
        """
        date_range_result = client.query(date_range_query).result_rows
        if date_range_result:
            date_range = {
                'min_date': str(date_range_result[0][0]) if date_range_result[0][0] else None,
                'max_date': str(date_range_result[0][1]) if date_range_result[0][1] else None
            }
        else:
            date_range = {'min_date': None, 'max_date': None}
        
        # 信号统计
        signal_stats_query = """
        SELECT 
            sum(best_buy) as total_buy,
            sum(best_sell) as total_sell
        FROM stock_daily_k_i_read
        """
        signal_stats_result = client.query(signal_stats_query).result_rows
        if signal_stats_result:
            signal_stats = {
                'total_buy': signal_stats_result[0][0] or 0,
                'total_sell': signal_stats_result[0][1] or 0
            }
        else:
            signal_stats = {'total_buy': 0, 'total_sell': 0}
        
        # 表大小信息
        table_sizes = _get_table_sizes()
        
        result = StatsResponse(
            stocks=stock_count,
            daily_records=daily_count,
            date_range={
                "start": date_range.get('min_date'),
                "end": date_range.get('max_date')
            },
            signals={
                "buy_signals": int(signal_stats.get('total_buy', 0) or 0),
                "sell_signals": int(signal_stats.get('total_sell', 0) or 0)
            },
            table_sizes=table_sizes
        )
        
        return {
            "code": 200,
            "message": "获取成功",
            "data": result.dict()
        }
        
    except Exception as e:
        logger.error(f"获取统计信息失败: {e}")
        raise HTTPException(status_code=500, detail="获取统计信息失败")

@router.get("/stats/partitions", summary="获取分区信息")
def get_partition_info(client: Client = Depends(get_clickhouse_client)):
    """获取分区信息"""
    try:
        
        # 获取所有表的分区信息
        partition_query = """
        SELECT 
            table,
            partition,
            count() as parts,
            sum(rows) as rows,
            formatReadableSize(sum(bytes)) as size
        FROM system.parts 
        WHERE database = 'stock_analysis'
        GROUP BY table, partition
        ORDER BY table, partition
        """
        
        result = client.query(partition_query).result_rows
        
        # 按表分组
        partition_info = {}
        for row in result:
            table = row[0]
            if table not in partition_info:
                partition_info[table] = []
            
            partition_info[table].append({
                'partition': row[1],
                'parts': row[2],
                'rows': row[3],
                'size': row[4]
            })
        
        return {
            "code": 200,
            "message": "获取成功",
            "data": partition_info
        }
        
    except Exception as e:
        logger.error(f"获取分区信息失败: {e}")
        raise HTTPException(status_code=500, detail="获取分区信息失败")

@router.get("/stats/performance", summary="获取性能统计信息")
def get_performance_stats(client: Client = Depends(get_clickhouse_client)):
    """获取性能统计信息"""
    try:
        
        # 查询执行统计
        query_stats_query = """
        SELECT 
            count() as total_queries,
            avg(query_duration_ms) as avg_duration_ms,
            max(query_duration_ms) as max_duration_ms
        FROM system.query_log 
        WHERE event_date >= today() - 1
            AND type = 'QueryFinish'
        """
        
        query_stats_result = client.query(query_stats_query).result_rows
        if query_stats_result and len(query_stats_result) > 0:
            query_stats = {
                'total_queries': query_stats_result[0][0] or 0,
                'avg_duration_ms': query_stats_result[0][1] or 0,
                'max_duration_ms': query_stats_result[0][2] or 0
            }
        else:
            query_stats = {'total_queries': 0, 'avg_duration_ms': 0, 'max_duration_ms': 0}
        
        # 表查询统计
        table_query_stats_query = """
        SELECT 
            tables,
            count() as query_count,
            avg(query_duration_ms) as avg_duration_ms
        FROM system.query_log 
        WHERE event_date >= today() - 1
            AND type = 'QueryFinish'
            AND length(tables) > 0
        GROUP BY tables
        ORDER BY query_count DESC
        LIMIT 10
        """
        
        table_query_result = client.query(table_query_stats_query).result_rows
        
        # 将表查询统计转换为对象格式
        formatted_table_stats = []
        for row in table_query_result:
            formatted_table_stats.append({
                'tables': ', '.join(row[0]) if isinstance(row[0], list) else str(row[0]),
                'query_count': row[1],
                'avg_duration_ms': round(row[2], 2)
            })
        
        result = {
            'query_stats': {
                'total_queries': query_stats.get('total_queries', 0),
                'avg_duration_ms': round(query_stats.get('avg_duration_ms', 0), 2),
                'max_duration_ms': query_stats.get('max_duration_ms', 0)
            },
            'table_query_stats': formatted_table_stats
        }
        
        return {
            "code": 200,
            "message": "获取成功",
            "data": result
        }
        
    except Exception as e:
        logger.error(f"获取性能统计失败: {e}")
        raise HTTPException(status_code=500, detail="获取性能统计失败")

@router.post("/stats/optimize", summary="优化所有表")
def optimize_tables():
    """优化所有表"""
    try:
        client = next(get_clickhouse_client())
        
        tables = ['stock_daily_k_write', 'stock_daily_i_write', 'stock_daily_k_agg', 'stock_daily_i_agg']
        results = {}
        
        for table in tables:
            try:
                client.optimize_table(table)
                results[table] = "优化成功"
            except Exception as e:
                results[table] = f"优化失败: {str(e)}"
        
        return {
            "code": 200,
            "message": "优化完成",
            "data": results
        }
        
    except Exception as e:
        logger.error(f"优化表失败: {e}")
        raise HTTPException(status_code=500, detail="优化表失败")

def _get_table_sizes() -> Dict[str, str]:
    """获取表大小信息"""
    try:
        client = next(get_clickhouse_client())
        
        # 使用SQL查询获取表大小信息
        size_query = """
        SELECT 
            table,
            formatReadableSize(sum(bytes)) as size
        FROM system.parts 
        WHERE database = 'stock_analysis'
            AND table IN ('stock_info', 'stock_daily_k_write', 'stock_daily_i_write', 'stock_daily_k_agg', 'stock_daily_i_agg')
        GROUP BY table
        ORDER BY table
        """
        
        result = client.query(size_query).result_rows
        table_sizes = {}
        
        # 初始化所有表的大小为0
        tables = ['stock_info', 'stock_daily_k_write', 'stock_daily_i_write', 'stock_daily_k_agg', 'stock_daily_i_agg']
        for table in tables:
            table_sizes[table] = '0 B'
        
        # 更新实际查询到的表大小
        for row in result:
            table_name = row[0]
            size = row[1]
            table_sizes[table_name] = size
        
        return table_sizes
        
    except Exception as e:
        logger.error(f"获取表大小信息失败: {e}")
        return {}