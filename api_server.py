"""
ClickHouse股票分析系统 - FastAPI主入口
"""
from fastapi import FastAPI, HTTPException, Query, Depends
from typing import Optional
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from loguru import logger
import uvicorn

from stock.stock_signal.controller.signal_controller import router as signal_router
from stock.stocks.controller.stock_controller import router as stock_router
from stock.stock_stats.controller.stats_controller import router as stats_router
from stock.stock_json_logic_filter.controller.json_logic_filter_controller import router as json_logic_router
from stock.stock_money_flow.controller.money_flow_controller import router as money_flow_router
from stock.stock_rule_hit.controller.rule_hit_controller import router as rule_hit_router
from stock.stock_info.controller.stock_info_controller import router as stock_info_router
from stock.stock_announcement.controller.announcement_controller import router as announcement_router
from stock.stock_financial_report.controller.financial_report_controller import router as financial_report_router
from common.db.clickhouse_client import init_clickhouse, close_clickhouse, get_clickhouse_client
from common.db.migrate import run_migrations
from stock.stocks.schemas.stock_schemas import StockItem, DayDataResponse
from stock.stock_signal.schemas.signal_schemas import SignalAnalysisResponse
from config import config

@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时初始化
    logger.info("正在初始化ClickHouse连接...")
    init_clickhouse()
    
    # 执行数据库迁移
    logger.info("正在执行数据库迁移...")
    client = next(get_clickhouse_client())
    stats = run_migrations(client=client)
    client.close()
    logger.info(
        f"迁移完成 - 总计: {stats['total']}, "
        f"已执行: {stats['executed']}, "
        f"本次执行: {stats['executed_now']}, "
        f"跳过: {stats['skipped']}, "
        f"失败: {stats['failed']}"
    )
    
    logger.info("ClickHouse股票分析系统启动完成！")
    
    yield
    
    # 关闭时清理
    logger.info("正在关闭ClickHouse连接...")
    close_clickhouse()
    logger.info("系统已关闭")

# 创建FastAPI应用
app = FastAPI(
    title="ClickHouse股票分析系统",
    description="基于ClickHouse的高性能股票数据分析系统",
    version="1.0.0",
    lifespan=lifespan
)

# 添加CORS中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由器
app.include_router(stock_router)
app.include_router(stock_info_router)
app.include_router(signal_router)
app.include_router(stats_router)
app.include_router(json_logic_router)
app.include_router(money_flow_router)
app.include_router(rule_hit_router)
app.include_router(announcement_router)
app.include_router(financial_report_router)

# ========== 健康检查接口 ==========

@app.get("/health", response_model=dict)
def health_check():
    """健康检查"""
    try:
        # 简单的ClickHouse连接测试
        client = next(get_clickhouse_client())
        client.query("SELECT 1")
        return {
            "code": 200,
            "message": "系统正常",
            "data": {
                "status": "healthy",
                "database": "connected"
            }
        }
    except Exception as e:
        logger.error(f"健康检查失败: {e}")
        return {
            "code": 500,
            "message": "系统异常",
            "data": {
                "status": "unhealthy",
                "database": "disconnected",
                "error": str(e)
            }
        }

# ========== 根路径 ==========

@app.get("/", response_model=dict)
def root():
    """根路径"""
    return {
        "code": 200,
        "message": "ClickHouse股票分析系统",
        "data": {
            "version": "1.0.0",
            "docs": "/docs",
            "health": "/health"
        }
    }

if __name__ == "__main__":
    # 配置日志
    logger.add(
        config.LOG_FILE,
        rotation="1 day",
        retention="30 days",
        level=config.LOG_LEVEL,
        format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {name}:{function}:{line} - {message}"
    )
    
    # 启动服务器
    uvicorn.run(
        "api_server:app",
        host=config.API_HOST,
        port=config.API_PORT,
        reload=config.DEBUG,
        log_level=config.LOG_LEVEL.lower()
    )
