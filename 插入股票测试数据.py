import clickhouse_connect
from datetime import datetime

client = clickhouse_connect.get_client(
    host='localhost',
    port=8123,
    database='stock_analysis',
    username='default',
    password=''
)

print('✅ ClickHouse数据库连接成功！')

# 准备5条测试股票数据
print('\n📊 准备插入5条测试股票数据...')
test_stocks = [
    {'code': '000001', 'name': '平安银行', 'market': 'SZ', 'status': '正常'},
    {'code': '000002', 'name': '万科A', 'market': 'SZ', 'status': '正常'},
    {'code': '600000', 'name': '浦发银行', 'market': 'SH', 'status': '正常'},
    {'code': '600036', 'name': '招商银行', 'market': 'SH', 'status': '正常'},
    {'code': '000858', 'name': '五粮液', 'market': 'SZ', 'status': '正常'}
]

# 插入数据
print('\n🔄 开始插入数据...')
insert_sql = '''
INSERT INTO stock_info (code, name, market, status)
VALUES (%(code)s, %(name)s, %(market)s, %(status)s)
'''

success_count = 0
for stock in test_stocks:
    try:
        client.command(insert_sql, stock)
        print(f'✅ {stock["code"]} - {stock["name"]} 插入成功')
        success_count += 1
    except Exception as e:
        print(f'❌ {stock["code"]} - {stock["name"]} 插入失败: {e}')

print(f'\n📈 插入完成！成功: {success_count}/5 条')

# 验证插入结果
print('\n🔍 验证插入结果...')
try:
    result = client.query('SELECT code, name, market, status, created_at FROM stock_info ORDER BY code')
    print(f'✅ 查询成功！共 {len(result.result_rows)} 条记录')
    print('\n📋 股票信息表数据:')
    print('   代码    | 名称     | 市场 | 状态 | 创建时间')
    print('   --------|----------|------|------|-------------------')
    for row in result.result_rows:
        print(f'   {row[0]:<8} | {row[1]:<8} | {row[2]:<4} | {row[3]:<4} | {row[4]}')
except Exception as e:
    print(f'❌ 查询失败: {e}')

client.close()
