import sys
sys.path.append('scripts')

from fetch_daily_data import create_clickhouse_client, fetch_stock_data
import time

print('✅ 测试批量列式插入...')

# 创建客户端
client = create_clickhouse_client()

# 测试抓取单只股票数据
print('\n📊 测试抓取平安银行数据...')
try:
    data = fetch_stock_data('000001', '平安银行', '20240101', '20240115')
    print(f'✅ 抓取成功！获得 {len(data)} 条数据')
    
    if data:
        # 测试批量插入
        print('\n🔄 测试批量列式插入...')
        batch_data = []
        for row in data:
            batch_data.append([
                row['code'],
                row['trade_date'],  # 保持 date 对象
                row['name'],
                row['open_price'],
                row['close_price'],
                row['high_price'],
                row['low_price'],
                row['volume'],
                row['amount'],
                row['amplitude'],
                row['change_pct'],
                row['change_amount'],
                row['turnover_rate']
            ])
        
        start_time = time.time()
        client.insert(
            table='stock_daily_k_write',
            data=batch_data,
            column_names=[
                'code', 'trade_date', 'name', 'open_price', 'close_price', 
                'high_price', 'low_price', 'volume', 'amount', 'amplitude', 
                'change_pct', 'change_amount', 'turnover_rate'
            ]
        )
        elapsed = time.time() - start_time
        
        print(f'✅ 批量插入成功！耗时: {elapsed:.3f}秒')
        print(f'📊 插入 {len(batch_data)} 条记录')
        
        # 验证插入结果
        result = client.query("SELECT COUNT(*) FROM stock_daily_k_write WHERE code = '000001'")
        print(f'✅ 验证成功！000001 总记录数: {result.result_rows[0][0]}')
        
except Exception as e:
    print(f'❌ 测试失败: {e}')

client.close()
