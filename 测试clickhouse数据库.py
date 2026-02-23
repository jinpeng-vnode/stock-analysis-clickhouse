import clickhouse_connect
from datetime import datetime, date

# 连接ClickHouse数据库
client = clickhouse_connect.get_client(
    host='localhost',
    port=8123,
    database='stock_analysis',
    username='default',
    password=''
)

print("✅ ClickHouse数据库连接成功！")

# 第一步：向日线写入表插入模拟数据
print("\n📊 第一步：向日线写入表插入模拟数据")

# 模拟K线数据
kline_data = {
    'code': '000001',
    'trade_date': date(2024, 1, 15),
    'name': '平安银行',
    'open_price': 123.50,
    'close_price': 12.80,
    'high_price': 12.95,
    'low_price': 12.45,
    'volume': 1500000,
    'amount': 19200000.0,
    'amplitude': 4.0,
    'change_pct': 2.4,
    'change_amount': 0.30,
    'turnover_rate': 0.8
}

# 插入数据到K线写入表（不包含version字段）
insert_sql = """
INSERT INTO stock_daily_k_write 
(code, trade_date, name, open_price, close_price, high_price, low_price, 
 volume, amount, amplitude, change_pct, change_amount, turnover_rate)
VALUES (%(code)s, %(trade_date)s, %(name)s, %(open_price)s, %(close_price)s, 
        %(high_price)s, %(low_price)s, %(volume)s, %(amount)s, %(amplitude)s, 
        %(change_pct)s, %(change_amount)s, %(turnover_rate)s)
"""

try:
    client.command(insert_sql, kline_data)
    print("✅ K线数据插入成功！")
    print(f"   股票代码: {kline_data['code']}")
    print(f"   交易日期: {kline_data['trade_date']}")
    print(f"   收盘价: {kline_data['close_price']}元")
except Exception as e:
    print(f"❌ K线数据插入失败: {e}")

client.close()
