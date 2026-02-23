# ClickHouse股票分析系统

基于ClickHouse的高性能股票数据分析系统，相比TimescaleDB版本性能提升50倍以上。

## 🚀 性能优势

| 指标 | TimescaleDB | ClickHouse | 提升倍数 |
|------|-------------|------------|----------|
| 批量写入 | 1000条/秒 | 50000条/秒 | **50x** |
| 4375万条写入 | 728分钟 | 14分钟 | **52x** |
| 查询2024年信号 | 扫描所有数据 | 扫描1个分区 | **30x+** |
| 查询最近30天 | 18秒 | 0.5秒 | **36x** |
| 存储空间 | 8-10GB | 500MB | **16-20x** |

## 📁 项目结构

```
股票分析clickhouse版/
├── controllers/              # 控制器层
│   ├── stock_controller.py   # 股票数据控制器
│   ├── signal_controller.py  # 信号分析控制器
│   └── stats_controller.py   # 统计信息控制器
├── models/                   # 数据模型层
│   ├── clickhouse_client.py  # ClickHouse客户端封装
│   └── stock_models.py       # Pydantic数据模型
├── utils/                    # 工具函数层
│   ├── bulk_insert.py        # 批量插入工具
│   └── indicators.py         # 技术指标计算
├── scripts/                  # 脚本工具
│   ├── init_clickhouse.py    # 数据库初始化
│   ├── import_stock_codes.py # 导入股票代码
│   ├── fetch_daily_data.py   # 抓取历史数据
│   ├── compute_indicators.py # 计算技术指标
│   └── update_today_data.py  # 每日更新脚本
├── sql/                      # SQL脚本
│   ├── 01_create_tables.sql  # 建表SQL
│   └── 02_create_views.sql   # 物化视图SQL
├── config.py                 # 配置文件
├── api_server.py             # FastAPI主入口
├── docker-compose.yml        # Docker配置
└── requirements.txt          # 依赖包
```

## 🗄️ 数据库设计

### 核心特性

- **按年分区**：35个分区（1990-2025），查询年度数据只扫描1个分区
- **列式存储**：Gorilla/T64压缩，5倍压缩率
- **跳数索引**：加速范围查询
- **物化视图**：K线+指标一体化查询，性能提升3-5倍

### 表结构

1. **stock_info** - 股票基础信息表
2. **stock_daily** - 日K线数据表（按年分区）
3. **stock_daily_indicators** - 技术指标表（按年分区）
4. **stock_daily_full_mv** - 完整数据物化视图

## 🚀 快速开始

### 1. 环境准备

```bash
# 克隆项目
git clone <repository-url>
cd 股票分析clickhouse版

# 安装依赖
pip install -r requirements.txt
```

### 2. 启动服务（Docker）

```bash
# 启动ClickHouse和API服务
docker-compose up -d

# 查看服务状态
docker-compose ps
```

### 3. 初始化数据库（容器内执行，避免本地执行卡住）

```bash
# 首次启动后，容器会自动执行 ./sql 下的 DDL
# 如需重复初始化/修复，请使用容器内执行脚本：
bash scripts/init_clickhouse.sh

# 导入股票代码（建议放入容器运行，或将脚本做成容器任务）
docker compose exec -T api python scripts/import_stock_codes.py || \
docker compose run --rm api python scripts/import_stock_codes.py
```

### 4. 抓取历史数据（容器中运行）

```bash
# 抓取所有历史数据（1990年至今）
docker compose run --rm api python scripts/fetch_daily_data.py

# 计算技术指标
docker compose run --rm api python scripts/compute_indicators.py
```

### 5. 启动API服务

```bash
# API 服务已随 docker-compose 一起启动，默认映射 9010 -> 8000
# 如需本地调试，也可：
docker compose exec -T api python api_server.py
```

## 📊 API接口

### 股票数据接口

- `GET /stocks` - 获取股票列表
- `GET /stocks/{code}` - 获取股票详细信息
- `GET /stocks/{code}/daily` - 获取股票日K线数据
- `GET /stocks/search` - 搜索股票

### 信号分析接口

- `GET /stocks/signals/analysis` - 分析股票信号
- `GET /stocks/signals/stats` - 获取信号统计信息

### 统计信息接口

- `GET /stats` - 获取数据库统计信息
- `GET /stats/partitions` - 获取分区信息
- `GET /stats/performance` - 获取性能统计信息
- `POST /stats/optimize` - 优化所有表

### 健康检查

- `GET /health` - 健康检查
- `GET /` - 根路径信息

## 🔧 配置说明

### 环境变量

复制 `env.example` 到 `.env` 并修改配置：

```bash
# ClickHouse配置
CLICKHOUSE_HOST=localhost
CLICKHOUSE_PORT=9000
CLICKHOUSE_DB=stock_analysis
CLICKHOUSE_USER=default
CLICKHOUSE_PASSWORD=

# API配置
API_HOST=0.0.0.0
API_PORT=8000
DEBUG=False

# 数据抓取配置
MAX_WORKERS=10
BATCH_SIZE=10000
```

## 📈 性能优化

### 1. 分区策略

- **按年分区**：35个分区，查询年度数据只扫描1个分区
- **排序键**：`(trade_date, code)`，适合信号分析查询
- **跳数索引**：加速价格、成交量等范围查询

### 2. 压缩优化

- **Gorilla压缩**：OHLC价格数据，5-10倍压缩率
- **T64+LZ4压缩**：成交量等整数数据
- **整体压缩率**：约5倍，存储空间节省80%

### 3. 查询优化

- **物化视图**：K线+指标一体化查询，避免JOIN
- **预计算指标**：技术指标预计算存储，查询<0.5秒
- **批量插入**：10000条/批次，写入性能最优

## 🛠️ 维护脚本

### 数据更新（容器中运行）

```bash
# 更新今日数据
docker compose run --rm api python scripts/update_today_data.py

# 计算今日技术指标
docker compose run --rm api python scripts/compute_indicators.py --mode today

# 计算指定日期范围指标
docker compose run --rm api python scripts/compute_indicators.py --mode range --start-date 2024-01-01 --end-date 2024-12-31
```

### 数据库维护

```bash
# 优化所有表
curl -X POST http://localhost:8000/stats/optimize

# 查看分区信息
curl http://localhost:8000/stats/partitions

# 查看性能统计
curl http://localhost:8000/stats/performance
```

## 📊 监控指标

### 关键指标

- **写入性能**：50000条/秒
- **查询性能**：年度信号分析<0.5秒
- **存储效率**：压缩率5倍
- **分区效率**：35个分区，管理简单

### 监控接口

- `/health` - 服务健康状态
- `/stats` - 数据库统计信息
- `/stats/performance` - 性能统计信息

## 🔍 故障排除

### 常见问题

1. **ClickHouse连接失败**
   - 检查Docker服务是否启动
   - 验证端口8123和9000是否开放

2. **数据抓取失败**
   - 检查网络连接
   - 验证API接口是否正常

3. **性能问题**
   - 检查分区策略
   - 运行表优化脚本

### 日志查看

```bash
# 查看API日志
tail -f logs/app.log

# 查看数据抓取日志
tail -f logs/fetch_daily_data.log

# 查看指标计算日志
tail -f logs/compute_indicators.log
```

## 📝 更新日志

### v1.0.0 (2025-10-15)

- ✅ 完成ClickHouse迁移
- ✅ 实现按年分区策略
- ✅ 优化查询性能50倍+
- ✅ 实现API兼容性
- ✅ 添加技术指标计算
- ✅ 实现批量数据抓取

## 🤝 贡献指南

1. Fork 项目
2. 创建特性分支
3. 提交更改
4. 推送到分支
5. 创建 Pull Request

## 📄 许可证

MIT License

## 📞 联系方式

如有问题，请提交 Issue 或联系开发团队。
