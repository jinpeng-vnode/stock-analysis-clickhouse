import pandas as pd
import requests
import time
from datetime import datetime, timedelta

def get_stock_money_flow_eastmoney(code: str, start_date: str = "20200101", end_date: str = None, market: str = None):
    """
    使用东方财富API获取个股历史资金流向数据
    code: 股票代码
    start_date: 开始日期，格式 YYYYMMDD
    end_date: 结束日期，格式 YYYYMMDD，默认为今天
    market: 股票市场; 上海证券交易所: sh, 深证证券交易所: sz, 北京证券交易所: bj; 如果为None则自动判断
    """
    try:
        # 市场代码映射
        market_map = {"sh": 1, "sz": 0, "bj": 0}
        
        # 确定市场类型
        if market is not None:
            if market not in market_map:
                raise ValueError(f"不支持的市场类型: {market}，支持的类型: {list(market_map.keys())}")
            secid = f"{market_map[market]}.{code}"
        else:
            # 自动判断市场类型
            if code.startswith(('600', '601', '603', '605', '688')):
                secid = f"1.{code}"  # 沪市
            elif code.startswith(('000', '001', '002', '003', '300')):
                secid = f"0.{code}"  # 深市
            elif code.startswith(('430', '830', '870', '871', '872', '873', '874', '875', '876', '877', '878', '879')):
                secid = f"0.{code}"  # 北交所
            else:
                # 默认深市
                secid = f"0.{code}"

        # 设置结束日期
        if end_date is None:
            end_date = datetime.now().strftime('%Y%m%d')

        # 构建请求URL
        url = "https://push2his.eastmoney.com/api/qt/stock/fflow/daykline/get"
        
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Referer": "https://quote.eastmoney.com/"
        }
        
        params = {
            "lmt": "0",  # 0表示获取所有数据
            "klt": "101",  # 日K线
            "secid": secid,
            "fields1": "f1,f2,f3,f7",
            "fields2": "f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61,f62,f63,f64,f65",
            "ut": "b2884a393a59ad64002292a3e90d46a5",
            "_": int(time.time() * 1000),
        }
        
        response = requests.get(url, params=params, headers=headers, timeout=10)
        data = response.json()
        
        if 'data' not in data or data['data'] is None:
            print(f"未获取到{code}的资金流向数据")
            return None
            
        klines = data['data']['klines']
        if not klines:
            print(f"{code}没有资金流向数据")
            return None
            
        # 根据实际数据格式解析，与示例代码保持一致
        temp_df = pd.DataFrame([item.split(",") for item in klines])
        temp_df.columns = [
            "日期",
            "主力净流入-净额",
            "小单净流入-净额",
            "中单净流入-净额",
            "大单净流入-净额",
            "超大单净流入-净额",
            "主力净流入-净占比",
            "小单净流入-净占比",
            "中单净流入-净占比",
            "大单净流入-净占比",
            "超大单净流入-净占比",
            "收盘价",
            "涨跌幅",
            "-",
            "-",
        ]
        
        # 选择需要的列，与示例代码保持一致，使用copy()避免SettingWithCopyWarning
        df = temp_df[
            [
                "日期",
                "收盘价",
                "涨跌幅",
                "主力净流入-净额",
                "主力净流入-净占比",
                "超大单净流入-净额",
                "超大单净流入-净占比",
                "大单净流入-净额",
                "大单净流入-净占比",
                "中单净流入-净额",
                "中单净流入-净占比",
                "小单净流入-净额",
                "小单净流入-净占比",
            ]
        ].copy()
        
        # 转换数据类型，与示例代码保持一致
        df["日期"] = pd.to_datetime(df["日期"], errors="coerce").dt.date
        df["主力净流入-净额"] = pd.to_numeric(df["主力净流入-净额"], errors="coerce")
        df["小单净流入-净额"] = pd.to_numeric(df["小单净流入-净额"], errors="coerce")
        df["中单净流入-净额"] = pd.to_numeric(df["中单净流入-净额"], errors="coerce")
        df["大单净流入-净额"] = pd.to_numeric(df["大单净流入-净额"], errors="coerce")
        df["超大单净流入-净额"] = pd.to_numeric(df["超大单净流入-净额"], errors="coerce")
        df["主力净流入-净占比"] = pd.to_numeric(df["主力净流入-净占比"], errors="coerce")
        df["小单净流入-净占比"] = pd.to_numeric(df["小单净流入-净占比"], errors="coerce")
        df["中单净流入-净占比"] = pd.to_numeric(df["中单净流入-净占比"], errors="coerce")
        df["大单净流入-净占比"] = pd.to_numeric(df["大单净流入-净占比"], errors="coerce")
        df["超大单净流入-净占比"] = pd.to_numeric(df["超大单净流入-净占比"], errors="coerce")
        df["收盘价"] = pd.to_numeric(df["收盘价"], errors="coerce")
        df["涨跌幅"] = pd.to_numeric(df["涨跌幅"], errors="coerce")
        
        # 先查看原始数据的时间范围
        print(f"原始数据时间范围: {df['日期'].min().strftime('%Y-%m-%d')} 到 {df['日期'].max().strftime('%Y-%m-%d')}")
        print(f"原始数据条数: {len(df)}")
        
        # 过滤日期范围
        start_dt = pd.to_datetime(start_date).date()
        end_dt = pd.to_datetime(end_date).date()
        df_filtered = df[(df['日期'] >= start_dt) & (df['日期'] <= end_dt)]
        print(f"过滤后数据条数: {len(df_filtered)}")
        
        df = df_filtered
        
        print(f"获取{code}历史资金流向数据成功，共{len(df)}条数据")
        if len(df) > 0:
            print(f"时间范围: {df['日期'].min().strftime('%Y-%m-%d')} 到 {df['日期'].max().strftime('%Y-%m-%d')}")
        return df
        
    except Exception as e:
        print(f"获取{code}历史资金流向数据失败: {e}")
        return None

# 测试获取资金流向数据
print("=== 测试东方财富资金流向数据 ===")

# 测试平安银行 - 使用自动判断
print("\n1. 测试平安银行(000001) - 自动判断市场:")
df_000001 = get_stock_money_flow_eastmoney("000001")
if df_000001 is not None and len(df_000001) > 0:
    # 获取最新一天数据
    latest_data = df_000001.tail(1).iloc[0]
    
    print(f"数据条数: {len(df_000001)}")
    print(f"最新数据日期: {latest_data['日期']}")
    print(f"收盘价: {latest_data['收盘价']:.2f}元")
    print(f"涨跌幅: {latest_data['涨跌幅']:.2f}%")
    print("\n=== 今日净流入 ===")
    print(f"主力净流入: {latest_data['主力净流入-净额']/100000000:,.2f}亿 (净比: {latest_data['主力净流入-净占比']:.2f}%)")
    print(f"超大单净流入: {latest_data['超大单净流入-净额']/100000000:,.2f}亿 (净比: {latest_data['超大单净流入-净占比']:.2f}%)")
    print(f"大单净流入: {latest_data['大单净流入-净额']/100000000:,.2f}亿 (净比: {latest_data['大单净流入-净占比']:.2f}%)")
    print(f"中单净流入: {latest_data['中单净流入-净额']/100000000:,.2f}亿 (净比: {latest_data['中单净流入-净占比']:.2f}%)")
    print(f"小单净流入: {latest_data['小单净流入-净额']/100000000:,.2f}亿 (净比: {latest_data['小单净流入-净占比']:.2f}%)")

# 测试平安银行 - 使用明确指定市场
print("\n1.1 测试平安银行(000001) - 明确指定深市:")
df_000001_sz = get_stock_money_flow_eastmoney("000001", market="sz")
if df_000001_sz is not None and len(df_000001_sz) > 0:
    latest_data_sz = df_000001_sz.tail(1).iloc[0]
    print(f"数据条数: {len(df_000001_sz)}")
    print(f"最新数据日期: {latest_data_sz['日期']}")
    print(f"收盘价: {latest_data_sz['收盘价']:.2f}元")
    print(f"涨跌幅: {latest_data_sz['涨跌幅']:.2f}%")
    print("\n=== 今日净流入 ===")
    print(f"主力净流入: {latest_data_sz['主力净流入-净额']/100000000:,.2f}亿 (净比: {latest_data_sz['主力净流入-净占比']:.2f}%)")
    print(f"超大单净流入: {latest_data_sz['超大单净流入-净额']/100000000:,.2f}亿 (净比: {latest_data_sz['超大单净流入-净占比']:.2f}%)")
    print(f"大单净流入: {latest_data_sz['大单净流入-净额']/100000000:,.2f}亿 (净比: {latest_data_sz['大单净流入-净占比']:.2f}%)")
    print(f"中单净流入: {latest_data_sz['中单净流入-净额']/100000000:,.2f}亿 (净比: {latest_data_sz['中单净流入-净占比']:.2f}%)")
    print(f"小单净流入: {latest_data_sz['小单净流入-净额']/100000000:,.2f}亿 (净比: {latest_data_sz['小单净流入-净占比']:.2f}%)")

# 测试贵州茅台 - 使用明确指定市场
print("\n2. 测试贵州茅台(600519) - 明确指定沪市:")
df_600519 = get_stock_money_flow_eastmoney("600519", market="sh")
if df_600519 is not None and len(df_600519) > 0:
    latest_data_600519 = df_600519.tail(1).iloc[0]
    print(f"数据条数: {len(df_600519)}")
    print(f"最新数据日期: {latest_data_600519['日期']}")
    print(f"收盘价: {latest_data_600519['收盘价']:.2f}元")
    print(f"涨跌幅: {latest_data_600519['涨跌幅']:.2f}%")
    print("\n=== 今日净流入 ===")
    print(f"主力净流入: {latest_data_600519['主力净流入-净额']/100000000:,.2f}亿 (净比: {latest_data_600519['主力净流入-净占比']:.2f}%)")
    print(f"超大单净流入: {latest_data_600519['超大单净流入-净额']/100000000:,.2f}亿 (净比: {latest_data_600519['超大单净流入-净占比']:.2f}%)")
    print(f"大单净流入: {latest_data_600519['大单净流入-净额']/100000000:,.2f}亿 (净比: {latest_data_600519['大单净流入-净占比']:.2f}%)")
    print(f"中单净流入: {latest_data_600519['中单净流入-净额']/100000000:,.2f}亿 (净比: {latest_data_600519['中单净流入-净占比']:.2f}%)")
    print(f"小单净流入: {latest_data_600519['小单净流入-净额']/100000000:,.2f}亿 (净比: {latest_data_600519['小单净流入-净占比']:.2f}%)")

# 测试比亚迪
print("\n3. 测试比亚迪(002594) - 自动判断:")
df_002594 = get_stock_money_flow_eastmoney("002594")
if df_002594 is not None and len(df_002594) > 0:
    latest_data_002594 = df_002594.tail(1).iloc[0]
    print(f"数据条数: {len(df_002594)}")
    print(f"最新数据日期: {latest_data_002594['日期']}")
    print(f"收盘价: {latest_data_002594['收盘价']:.2f}元")
    print(f"涨跌幅: {latest_data_002594['涨跌幅']:.2f}%")
    print("\n=== 今日净流入 ===")
    print(f"主力净流入: {latest_data_002594['主力净流入-净额']/100000000:,.2f}亿 (净比: {latest_data_002594['主力净流入-净占比']:.2f}%)")
    print(f"超大单净流入: {latest_data_002594['超大单净流入-净额']/100000000:,.2f}亿 (净比: {latest_data_002594['超大单净流入-净占比']:.2f}%)")
    print(f"大单净流入: {latest_data_002594['大单净流入-净额']/100000000:,.2f}亿 (净比: {latest_data_002594['大单净流入-净占比']:.2f}%)")
    print(f"中单净流入: {latest_data_002594['中单净流入-净额']/100000000:,.2f}亿 (净比: {latest_data_002594['中单净流入-净占比']:.2f}%)")
    print(f"小单净流入: {latest_data_002594['小单净流入-净额']/100000000:,.2f}亿 (净比: {latest_data_002594['小单净流入-净占比']:.2f}%)")

# 测试北交所股票（如果有的话）
print("\n4. 测试北交所股票(430047) - 明确指定北交所:")
try:
    df_430047 = get_stock_money_flow_eastmoney("430047", market="bj")
    if df_430047 is not None and len(df_430047) > 0:
        latest_data_430047 = df_430047.tail(1).iloc[0]
        print(f"数据条数: {len(df_430047)}")
        print(f"最新数据日期: {latest_data_430047['日期']}")
        print(f"收盘价: {latest_data_430047['收盘价']:.2f}元")
        print(f"涨跌幅: {latest_data_430047['涨跌幅']:.2f}%")
        print("\n=== 今日净流入 ===")
        print(f"主力净流入: {latest_data_430047['主力净流入-净额']/100000000:,.2f}亿 (净比: {latest_data_430047['主力净流入-净占比']:.2f}%)")
        print(f"超大单净流入: {latest_data_430047['超大单净流入-净额']/100000000:,.2f}亿 (净比: {latest_data_430047['超大单净流入-净占比']:.2f}%)")
        print(f"大单净流入: {latest_data_430047['大单净流入-净额']/100000000:,.2f}亿 (净比: {latest_data_430047['大单净流入-净占比']:.2f}%)")
        print(f"中单净流入: {latest_data_430047['中单净流入-净额']/100000000:,.2f}亿 (净比: {latest_data_430047['中单净流入-净占比']:.2f}%)")
        print(f"小单净流入: {latest_data_430047['小单净流入-净额']/100000000:,.2f}亿 (净比: {latest_data_430047['小单净流入-净占比']:.2f}%)")
    else:
        print("北交所股票可能没有资金流向数据或股票代码不存在")
except Exception as e:
    print(f"北交所股票测试失败: {e}")

print("\n=== 总结 ===")
print("使用东方财富API获取资金流向数据:")
print("1. 支持获取最近120天的历史数据")
print("2. 包含主力、超大单、大单、中单、小单的净流入金额和占比")
print("3. 可以计算20日、10日、5日、3日净流入")
print("4. 数据格式统一，便于后续分析")
print("5. 支持自动判断市场类型或明确指定市场类型")
print("6. 支持沪市(sh)、深市(sz)、北交所(bj)三个市场")
print("7. 与示例代码保持完全一致的数据处理方式")

