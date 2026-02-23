// 从后端API加载股票数据
// 将前端规则(JSON Logic)的字段映射为后端列名，并适配操作符
import { getStockDailyData, queryByJsonLogic } from '@/api/stocks'
import stockDataCache from './stockDataCache'
function transformRuleToBackend(rule) {
  if (!rule || typeof rule !== 'object') return {};

  const fieldMap = {
    close: 'close_price',
    open: 'open_price',
    high: 'high_price',
    low: 'low_price',
    // 其余名称保持不变：wr6, wr10, ma5, ma10, ma20, amplitude, change_pct, change_amount, turnover_rate, best_buy, best_sell
  };

  const transformNode = (node) => {
    if (!node || typeof node !== 'object') return node;
    const keys = Object.keys(node);
    if (keys.length !== 1) return node;
    const op = keys[0];
    const val = node[op];

    // 逻辑组合 and/or
    if (op === 'and' || op === 'or') {
      if (!Array.isArray(val)) return node;
      return { [op]: val.map(transformNode) };
    }

    // not/inv
    if (op === '!') {
      return { '!': transformNode(val) };
    }

    // not in -> nin
    if (op === '!in') {
      return { nin: Array.isArray(val) ? val.map(v => (v && v.var ? { var: fieldMap[v.var] || v.var } : v)) : val };
    }

    // 其他二元比较或集合操作
    if (Array.isArray(val) && val.length === 2) {
      const left = val[0];
      const right = val[1];
      const leftTx = (left && typeof left === 'object' && left.var)
        ? { var: fieldMap[left.var] || left.var }
        : left;
      return { [op]: [leftTx, right] };
    }

    return node;
  };

  return transformNode(rule);
}

// 数值安全转换
function num(v) {
  if (v === null || v === undefined || v === '') return null;
  const n = Number(v);
  return isNaN(n) ? null : n;
}

// 将中文字段对象映射为回测引擎所需字段
function mapCnRowToEngine(row, codeFallback = '', stockName = '') {
  return {
    date: row['日期'],
    trade_date: row['日期'],
    open: num(row['开盘']),
    close: num(row['收盘']),
    close_price: num(row['收盘']),
    high: num(row['最高']),
    low: num(row['最低']),
    volume: num(row['成交量']),
    amount: num(row['成交额']),
    amplitude: num(row['振幅']),
    change_pct: num(row['涨跌幅']),
    change_amount: num(row['涨跌额']),
    turnover_rate: num(row['换手率']),
    wr6: num(row['WR6']),
    wr10: num(row['WR10']),
    ma5: num(row['MA5']),
    ma10: num(row['MA10']),
    ma20: num(row['MA20']),
    slope_180: num(row['180日斜率']),
    slope_7: num(row['7日斜率']),
    fit_7: num(row['7日拟合值']),
    fit_180: num(row['180日拟合值']),
    // 将 0/1 映射为布尔，避免 JSON Logic 中 true/false 比较失效
    best_buy: row['最佳买点'] === true || row['最佳买点'] === 1,
    best_sell: row['最佳卖点'] === true || row['最佳卖点'] === 1,
    buy_count_7: row['7日买点数量'],
    sell_count_7: row['7日卖点数量'],
    buy_count_14: row['14日买点数量'],
    sell_count_14: row['14日卖点数量'],
    code: row['代码'] || codeFallback,
    name: stockName || codeFallback // 使用传入的股票名称
  };
}

// 分批加载股票数据，避免并发过多导致浏览器假死
// 默认并发数设置为10，可根据服务器性能调整
async function loadStocksInBatches(stockCodes, startDate, endDate, log, batchSize = 10) {
  const allData = [];
  const total = stockCodes.length;
  let loaded = 0;
  
  log(`📊 开始分批加载 ${total} 只股票数据，每批 ${batchSize} 只...`);
  
  for (let i = 0; i < stockCodes.length; i += batchSize) {
    const batch = stockCodes.slice(i, i + batchSize);
    const batchNum = Math.floor(i / batchSize) + 1;
    const totalBatches = Math.ceil(stockCodes.length / batchSize);
    
    log(`📦 加载第 ${batchNum}/${totalBatches} 批: ${batch.join(', ')}`);
    
    // 当前批次并发加载
    const batchPromises = batch.map(async (code) => {
      try {
        // 首先尝试从缓存获取数据
        let mappedRows = stockDataCache.get(code, startDate, endDate);
        
        if (mappedRows) {
          // 从缓存获取成功
          loaded++;
          log(`💾 ${code}: 从缓存获取 ${mappedRows.length}条数据 (${loaded}/${total})`);
          return mappedRows;
        }
        
        // 缓存未命中，从API获取指定时间范围数据
        const response = await getStockDailyData(code, { start: startDate, end: endDate });
        const rows = response.data || [];
        const stockName = response.name || code; // 从响应外层获取股票名称
        
        // 映射数据格式
        mappedRows = rows.map(r => mapCnRowToEngine(r, code, stockName));
        
        // 存入缓存
        stockDataCache.set(code, mappedRows, startDate, endDate, stockName);
        
        loaded++;
        log(`📡 ${code}: 从API获取 ${mappedRows.length}条数据 (${loaded}/${total})`);
        return mappedRows;
      } catch (e) {
        loaded++;
        log(`❌ ${code}: 加载失败 - ${e.message} (${loaded}/${total})`, 'warning');
        return [];
      }
    });
    
    const batchResults = await Promise.all(batchPromises);
    allData.push(...batchResults.flat());
    
    // 添加小延迟，避免请求过于密集，优化为50ms
    if (i + batchSize < stockCodes.length) {
      await new Promise(resolve => setTimeout(resolve, 50));
    }
  }
  
  return allData;
}

export async function loadStockData(startDate, endDate, stockCodes = null, logCallback = null, buyRule = null) {
  const log = (message, type = 'info') => {
    console.log(message);
    if (logCallback) {
      logCallback(message, type);
    }
  };
  
  log('📡 开始加载股票数据...');
  log('📅 日期范围: ' + startDate + ' 至 ' + endDate);
  
  // 显示缓存状态
  const cacheStats = stockDataCache.getStats();
  log(`💾 缓存状态: ${cacheStats.totalStocks}只股票, ${cacheStats.totalRecords}条记录, ${cacheStats.memoryUsage}MB`);
  
  try {
    let targetCodes = [];
    
    // 如果指定了股票代码：直接使用
    if (stockCodes && stockCodes.length > 0) {
      log('📊 使用指定股票代码: ' + stockCodes.join(', '));
      targetCodes = stockCodes;
    } else {
      // 否则：通过 JSON Logic 在后端筛出候选股票代码
      log('📊 使用买入规则(JSON Logic)筛选候选股票代码...');
      const buyRuleTx = transformRuleToBackend(buyRule);
      const payload = {
        table: 'stock_daily_k_i_read',
        select: ['code', 'name'],
        order_by: ['code asc', 'trade_date asc'],
        limit: 0,
        logic: {
          and: [
            { '>=': [ { var: 'trade_date' }, startDate ] },
            { '<=': [ { var: 'trade_date' }, endDate ] },
            ...(buyRuleTx && Object.keys(buyRuleTx).length ? [buyRuleTx] : [])
          ]
        }
      };

      const json = await queryByJsonLogic(payload);
      const records = json.data || [];
      
      // 统计原始记录信息
      log(`📊 后端返回记录数: ${records.length}`);
      
      // 去重候选代码 - 过滤接口返回的所有符合条件记录，前端自己进行去重
      const allCodes = records.map(r => r['代码']).filter(Boolean);
      const candidateSet = new Set(allCodes);
      targetCodes = Array.from(candidateSet);
      
      // 输出去重统计信息
      log(`📋 去重前股票代码数: ${allCodes.length}`);
      log(`📋 去重后候选股票数: ${targetCodes.length}`);
      
      if (allCodes.length > targetCodes.length) {
        log(`🔄 已去重 ${allCodes.length - targetCodes.length} 个重复股票代码`);
      }
    }
    
    if (targetCodes.length === 0) {
      log('⚠️ 警告: 没有找到任何股票代码', 'warning');
      return [];
    }
    
    // 分批加载所有股票数据
    const allData = await loadStocksInBatches(targetCodes, startDate, endDate, log);
    
    // 数据验证
    if (allData.length === 0) {
      log('⚠️ 警告: 没有加载到任何数据', 'warning');
    } else {
      // 检查必要字段
      const sample = allData[0];
      const requiredFields = ['date', 'close', 'close_price', 'code'];
      const missingFields = requiredFields.filter(field => !(field in sample));
      if (missingFields.length > 0) {
        log('⚠️ 警告: 数据缺少必要字段: ' + missingFields.join(', '), 'warning');
      }
    }
    
    log('✅ 数据加载完成，总计: ' + allData.length + ' 条');
    return allData;
  } catch (error) {
    console.error('❌ 数据加载失败:', error);
    throw error;
  }
}

// 加载单只股票的数据
export async function loadSingleStock(code, startDate, endDate) {
  const log = (message, type = 'info') => {
    console.log(message);
  };
  
  log(`📡 加载股票 ${code} 数据...`);
  
  try {
    // 首先尝试从缓存获取数据
    let stockData = stockDataCache.get(code, startDate, endDate);
    
    if (stockData) {
      // 从缓存获取成功
      log(`💾 ${code}: 从缓存获取 ${stockData.length}条数据`);
      return stockData;
    }
    
    // 缓存未命中，从API获取指定时间范围数据
    const response = await getStockDailyData(code, { start: startDate, end: endDate });
    stockData = response.data || [];
    const stockName = response.name || code;
    
    // 存入缓存
    stockDataCache.set(code, stockData, startDate, endDate, stockName);
    
    log(`📡 ${code}: 从API获取 ${stockData.length}条数据`);
    return stockData;
  } catch (error) {
    log(`❌ ${code} 加载失败:`, error);
    throw error;
  }
}

// 缓存管理工具函数
export const cacheManager = {
  /**
   * 获取缓存统计信息
   */
  getStats() {
    return stockDataCache.getStats();
  },

  /**
   * 清空所有缓存
   */
  clearAll() {
    stockDataCache.clear();
    console.log('🗑️ 已清空所有股票数据缓存');
  },

  /**
   * 清理过期缓存
   */
  cleanup() {
    stockDataCache.cleanup();
    console.log('🧹 已清理过期缓存');
  },

  /**
   * 删除指定股票缓存
   * @param {string} code 股票代码
   * @param {string} startDate 开始日期
   * @param {string} endDate 结束日期
   */
  deleteStock(code, startDate, endDate) {
    stockDataCache.delete(code, startDate, endDate);
  },

  /**
   * 预热缓存 - 批量预加载股票数据
   * @param {Array} codes 股票代码数组
   * @param {string} startDate 开始日期
   * @param {string} endDate 结束日期
   * @param {Function} logCallback 日志回调函数
   */
  async warmup(codes, startDate, endDate, logCallback = null) {
    const loadFunction = async (code) => {
      const response = await getStockDailyData(code, { start: startDate, end: endDate });
      const rows = response.data || [];
      const stockName = response.name || code;
      return rows.map(r => mapCnRowToEngine(r, code, stockName));
    };
    
    await stockDataCache.warmup(codes, loadFunction, logCallback);
  },

  /**
   * 检查股票是否已缓存
   * @param {string} code 股票代码
   * @param {string} startDate 开始日期
   * @param {string} endDate 结束日期
   */
  hasStock(code, startDate, endDate) {
    return stockDataCache.has(code, startDate, endDate);
  }
};

