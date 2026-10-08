/**
 * 股票数据缓存功能测试
 * 用于验证缓存机制的正确性和性能提升
 */
import { loadStockData, cacheManager } from './dataLoader.js';

// 测试配置
const TEST_CONFIG = {
  stockCodes: ['000001', '000002', '600000'],
  startDate: '2024-01-01',
  endDate: '2024-01-31'
};

/**
 * 执行缓存功能测试
 */
export async function runCacheTest() {
  console.log('🧪 开始股票数据缓存功能测试...');
  
  try {
    // 第一次加载 - 应该从API获取
    console.log('\n📡 第一次加载数据（应该从API获取）...');
    const startTime1 = Date.now();
    const data1 = await loadStockData(
      TEST_CONFIG.startDate, 
      TEST_CONFIG.endDate, 
      TEST_CONFIG.stockCodes,
      (message, type) => console.log(`[${type.toUpperCase()}] ${message}`)
    );
    const time1 = Date.now() - startTime1;
    console.log(`✅ 第一次加载完成，耗时: ${time1}ms，数据量: ${data1.length}条`);
    
    // 显示缓存状态
    const stats1 = cacheManager.getStats();
    console.log(`💾 缓存状态: ${stats1.totalStocks}个缓存条目, ${stats1.totalRecords}条记录`);
    
    // 第二次加载 - 应该从缓存获取
    console.log('\n💾 第二次加载数据（应该从缓存获取）...');
    const startTime2 = Date.now();
    const data2 = await loadStockData(
      TEST_CONFIG.startDate, 
      TEST_CONFIG.endDate, 
      TEST_CONFIG.stockCodes,
      (message, type) => console.log(`[${type.toUpperCase()}] ${message}`)
    );
    const time2 = Date.now() - startTime2;
    console.log(`✅ 第二次加载完成，耗时: ${time2}ms，数据量: ${data2.length}条`);
    
    // 验证数据一致性
    const dataConsistent = data1.length === data2.length && 
      data1.every((item, index) => 
        item.code === data2[index].code && 
        item.date === data2[index].date
      );
    
    console.log(`\n📊 测试结果:`);
    console.log(`- 数据一致性: ${dataConsistent ? '✅ 通过' : '❌ 失败'}`);
    console.log(`- 性能提升: ${time1 > 0 ? Math.round((time1 - time2) / time1 * 100) : 0}%`);
    console.log(`- 第一次耗时: ${time1}ms`);
    console.log(`- 第二次耗时: ${time2}ms`);
    
    // 测试不同时间范围的数据筛选
    console.log('\n🔍 测试不同时间范围的数据筛选...');
    const startTime3 = Date.now();
    const data3 = await loadStockData(
      '2024-01-15', 
      '2024-01-20', 
      TEST_CONFIG.stockCodes,
      (message, type) => console.log(`[${type.toUpperCase()}] ${message}`)
    );
    const time3 = Date.now() - startTime3;
    console.log(`✅ 筛选加载完成，耗时: ${time3}ms，数据量: ${data3.length}条`);
    
    // 显示最终缓存状态
    const finalStats = cacheManager.getStats();
    console.log(`\n💾 最终缓存状态:`);
    console.log(`- 缓存条目数: ${finalStats.totalStocks}`);
    console.log(`- 总记录数: ${finalStats.totalRecords}`);
    console.log(`- 内存使用: ${finalStats.memoryUsage}MB`);
    console.log(`- 过期缓存数: ${finalStats.expiredCount}`);
    
    return {
      success: true,
      dataConsistent,
      performanceImprovement: time1 > 0 ? Math.round((time1 - time2) / time1 * 100) : 0,
      firstLoadTime: time1,
      secondLoadTime: time2,
      filterLoadTime: time3,
      cacheStats: finalStats
    };
    
  } catch (error) {
    console.error('❌ 缓存测试失败:', error);
    return {
      success: false,
      error: error.message
    };
  }
}

/**
 * 清理测试数据
 */
export function cleanupTest() {
  cacheManager.clearAll();
  console.log('🧹 测试数据已清理');
}

// 如果直接运行此文件，执行测试
if (typeof window !== 'undefined' && window.location) {
  // 在浏览器环境中，可以通过控制台调用
  window.runCacheTest = runCacheTest;
  window.cleanupTest = cleanupTest;
  console.log('💡 缓存测试已准备就绪，可通过 runCacheTest() 执行测试');
}
