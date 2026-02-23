// 回测系统调试工具
import { getStockDailyData } from '@/api/stocks'
console.log('🔧 回测系统调试工具已加载');

// 测试数据
const testData = {
  stocks: [
    {
      code: '000001',
      name: '平安银行',
      trade_date: '2024-01-02',
      close_price: 12.50,
      best_buy: 1,
      best_sell: 0,
      wr6: -85,
      wr10: -80
    },
    {
      code: '000001',
      name: '平安银行',
      trade_date: '2024-01-03',
      close_price: 12.80,
      best_buy: 0,
      best_sell: 1,
      wr6: -75,
      wr10: -70
    }
  ],
  config: {
    id: 'debug_test',
    name: '调试测试',
    initial_capital: 100000,
    start_date: '2024-01-02',
    end_date: '2024-01-03',
    commission_rate: 0.0003,
    min_commission: 5,
    stamp_duty_rate: 0.001,
    slippage_rate: 0.001,
    buy_rule: {
      "and": [
        {"==": [{"var": "best_buy"}, 1]},
        {"<": [{"var": "wr6"}, -80]},
        {">": [{"var": "close_price"}, 5]},
        {"<": [{"var": "close_price"}, 50]}
      ]
    },
    sell_rule: {
      "or": [
        {"==": [{"var": "best_sell"}, 1]},
        {"<": [{"var": "profit_pct"}, -0.05]},
        {">": [{"var": "profit_pct"}, 0.1}]
    },
    position_config: {
      method: 'fixed_ratio',
      ratio: 0.1,
      max_position_per_stock: 0.3,
      max_stocks: 10
    }
  }
};

// 导出测试函数
window.debugBacktest = {
  // 测试规则引擎
  testRules: async () => {
    try {
      const jsonLogic = await import('json-logic-js');
      console.log('✅ json-logic-js 加载成功');
      
      const stock = testData.stocks[0];
      const shouldBuy = jsonLogic.default.apply(testData.config.buy_rule, stock);
      console.log('📊 买入规则测试:', shouldBuy, '股票:', stock.name);
      
      return { success: true, shouldBuy };
    } catch (error) {
      console.error('❌ 规则引擎测试失败:', error);
      return { success: false, error };
    }
  },
  
  // 测试API连接
  testAPI: async () => {
    try {
      const response = await getStockDailyData('000001', { start: '2024-01-01', end: '2024-01-31' });
      console.log('✅ API连接成功，数据量:', response.data?.length || 0);
      return { success: true, dataCount: response.data?.length || 0 };
    } catch (error) {
      console.error('❌ API连接失败:', error);
      return { success: false, error };
    }
  },
  
  // 测试LocalStorage
  testStorage: () => {
    try {
      localStorage.setItem('backtest_debug_test', JSON.stringify(testData.config));
      const saved = JSON.parse(localStorage.getItem('backtest_debug_test'));
      console.log('✅ LocalStorage 测试成功:', saved.name);
      return { success: true, config: saved };
    } catch (error) {
      console.error('❌ LocalStorage 测试失败:', error);
      return { success: false, error };
    }
  },
  
  // 运行完整测试
  runFullTest: async () => {
    console.log('🚀 开始完整测试...');
    
    const results = {
      rules: await window.debugBacktest.testRules(),
      api: await window.debugBacktest.testAPI(),
      storage: window.debugBacktest.testStorage()
    };
    
    console.log('📊 测试结果:', results);
    
    const allPassed = Object.values(results).every(r => r.success);
    console.log(allPassed ? '🎉 所有测试通过！' : '⚠️ 部分测试失败');
    
    return { allPassed, results };
  }
};

console.log('💡 使用方法:');
console.log('  - debugBacktest.testRules() - 测试规则引擎');
console.log('  - debugBacktest.testAPI() - 测试API连接');
console.log('  - debugBacktest.testStorage() - 测试LocalStorage');
console.log('  - debugBacktest.runFullTest() - 运行完整测试');
