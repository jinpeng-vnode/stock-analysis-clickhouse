"""
ClickHouse股票分析系统 - 配置文件
"""
import os
from typing import Optional
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

class Config:
    """应用配置类"""
    
    # ========== ClickHouse配置 ==========
    CLICKHOUSE_HOST: str = os.getenv("CLICKHOUSE_HOST", "localhost")
    CLICKHOUSE_PORT: int = int(os.getenv("CLICKHOUSE_PORT", "8123"))
    CLICKHOUSE_DB: str = os.getenv("CLICKHOUSE_DB", "stock_analysis")
    CLICKHOUSE_USER: str = os.getenv("CLICKHOUSE_USER", "default")
    CLICKHOUSE_PASSWORD: str = os.getenv("CLICKHOUSE_PASSWORD", "")
    
    # ========== API配置 ==========
    API_HOST: str = os.getenv("API_HOST", "0.0.0.0")
    API_PORT: int = int(os.getenv("API_PORT", "9010"))
    DEBUG: bool = os.getenv("DEBUG", "False").lower() == "true"
    
    # ========== 日志配置 ==========
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    LOG_FILE: str = os.getenv("LOG_FILE", "logs/app.log")
    
    # ========== 数据抓取配置 ==========
    MAX_WORKERS: int = int(os.getenv("MAX_WORKERS", "16"))
    BATCH_SIZE: int = int(os.getenv("BATCH_SIZE", "10000"))
    FETCH_INTERVAL: int = int(os.getenv("FETCH_INTERVAL", "3600"))
    
    # ========== 技术指标配置 ==========
    WR_PERIODS: list = [6, 10]
    MA_PERIODS: list = [5, 10, 20]
    
    # ========== 数据源配置 ==========
    # 东方财富API配置
    EASTMONEY_API_BASE: str = "http://push2his.eastmoney.com/api/qt/stock/kline/get"
    
    # 腾讯API配置（用于实时数据）
    TENCENT_API_BASE: str = "http://qt.gtimg.cn/q="
    
    # ========== 性能配置 ==========
    # 查询限制
    MAX_QUERY_LIMIT: int = 10000
    
    # 连接池配置
    CLICKHOUSE_POOL_SIZE: int = 20
    CLICKHOUSE_MAX_CONNECTIONS: int = 100
    
    # 超时配置
    CLICKHOUSE_TIMEOUT: int = 30
    HTTP_TIMEOUT: int = 30

# 全局配置实例
config = Config()
