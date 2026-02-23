"""
测试资金流向API接口
"""
import requests
import json
from datetime import date, timedelta

# API基础URL
BASE_URL = "http://localhost:9010"

def test_money_flow_stats():
    """测试资金流向统计接口"""
    print("=== 测试资金流向统计接口 ===")
    try:
        response = requests.get(f"{BASE_URL}/money-flow/stats")
        if response.status_code == 200:
            data = response.json()
            print("✅ 统计接口测试成功")
            print(f"总记录数: {data['total_records']}")
            print(f"有数据的股票数: {data['stocks_with_data']}")
            print(f"日期范围: {data['date_range']}")
            print(f"最新更新: {data['latest_update']}")
        else:
            print(f"❌ 统计接口测试失败: {response.status_code}")
            print(response.text)
    except Exception as e:
        print(f"❌ 统计接口测试异常: {e}")

def test_money_flow_single_stock():
    """测试单股票资金流向接口"""
    print("\n=== 测试单股票资金流向接口 ===")
    try:
        # 测试平安银行
        response = requests.get(f"{BASE_URL}/money-flow/000001")
        if response.status_code == 200:
            data = response.json()
            print("✅ 单股票接口测试成功")
            print(f"股票代码: {data['code']}")
            print(f"股票名称: {data['name']}")
            print(f"总记录数: {data['total_records']}")
            print(f"数据条数: {len(data['data'])}")
            
            if data['data']:
                latest = data['data'][0]  # 最新数据
                print(f"最新数据: {latest['trade_date']}")
                print(f"收盘价: {latest['close_price']}")
                print(f"涨跌幅: {latest['change_pct']}%")
                print(f"主力净流入: {latest['main_net_inflow_amount']}元")
                print(f"主力净占比: {latest['main_net_inflow_ratio']}%")
        else:
            print(f"❌ 单股票接口测试失败: {response.status_code}")
            print(response.text)
    except Exception as e:
        print(f"❌ 单股票接口测试异常: {e}")

def test_money_flow_batch():
    """测试批量资金流向接口"""
    print("\n=== 测试批量资金流向接口 ===")
    try:
        # 测试多只股票
        codes = "000001,600519,002594"  # 平安银行、贵州茅台、比亚迪
        response = requests.get(f"{BASE_URL}/money-flow/batch?codes={codes}")
        if response.status_code == 200:
            data = response.json()
            print("✅ 批量接口测试成功")
            print(f"返回股票数量: {len(data)}")
            
            for stock_data in data:
                print(f"  {stock_data['code']} {stock_data['name']}: {len(stock_data['data'])}条数据")
        else:
            print(f"❌ 批量接口测试失败: {response.status_code}")
            print(response.text)
    except Exception as e:
        print(f"❌ 批量接口测试异常: {e}")

def test_money_flow_top():
    """测试资金流向排行榜接口"""
    print("\n=== 测试资金流向排行榜接口 ===")
    try:
        response = requests.get(f"{BASE_URL}/money-flow/top?limit=5")
        if response.status_code == 200:
            data = response.json()
            print("✅ 排行榜接口测试成功")
            print(f"统计日期: {data['date']}")
            print(f"总股票数: {data['total_stocks']}")
            print(f"净流入前5名: {len(data['top_inflow'])}")
            print(f"净流出前5名: {len(data['top_outflow'])}")
            
            if data['top_inflow']:
                print("净流入前3名:")
                for i, item in enumerate(data['top_inflow'][:3]):
                    print(f"  {i+1}. {item['code']} {item['name']}: {item['main_net_inflow_amount']}元")
        else:
            print(f"❌ 排行榜接口测试失败: {response.status_code}")
            print(response.text)
    except Exception as e:
        print(f"❌ 排行榜接口测试异常: {e}")

def test_money_flow_analysis():
    """测试资金流向分析接口"""
    print("\n=== 测试资金流向分析接口 ===")
    try:
        # 测试平安银行的分析数据
        response = requests.get(f"{BASE_URL}/money-flow/analysis/000001?days=10")
        if response.status_code == 200:
            data = response.json()
            print("✅ 分析接口测试成功")
            print(f"股票代码: {data['code']}")
            print(f"股票名称: {data['name']}")
            print(f"分析天数: {data['analysis_days']}")
            print(f"数据条数: {data['total_records']}")
            
            if data['data']:
                latest = data['data'][0]  # 最新数据
                print(f"最新数据: {latest['trade_date']}")
                print(f"3日净流入: {latest['net_inflow_3d']}元")
                print(f"5日净流入: {latest['net_inflow_5d']}元")
                print(f"10日净流入: {latest['net_inflow_10d']}元")
        else:
            print(f"❌ 分析接口测试失败: {response.status_code}")
            print(response.text)
    except Exception as e:
        print(f"❌ 分析接口测试异常: {e}")

def main():
    """主测试函数"""
    print("开始测试资金流向API接口...")
    print("=" * 50)
    
    # 测试所有接口
    test_money_flow_stats()
    test_money_flow_single_stock()
    test_money_flow_batch()
    test_money_flow_top()
    test_money_flow_analysis()
    
    print("\n" + "=" * 50)
    print("资金流向API接口测试完成！")
    print("可以访问 http://localhost:8000/docs 查看完整的API文档")

if __name__ == "__main__":
    main()
