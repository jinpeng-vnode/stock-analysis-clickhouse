/**
 * 股票数据缓存管理器
 * 提供内存缓存功能，避免重复请求相同股票的数据
 */
class StockDataCache {
  constructor() {
    // 内存缓存：股票代码 -> 完整数据数组
    this.cache = new Map();
    
    // 缓存元数据：股票代码 -> { lastUpdate, dataCount, stockName }
    this.metadata = new Map();
    
    // 缓存配置
    this.config = {
      maxCacheSize: Infinity,  // 无限制缓存条目数量
      maxMemoryMB: Infinity,   // 无限制内存使用量
      ttl: 24 * 60 * 60 * 1000, // 缓存过期时间(24小时)
    };
  }

  /**
   * 生成缓存键
   * @param {string} code 股票代码
   * @param {string} startDate 开始日期
   * @param {string} endDate 结束日期
   * @returns {string} 缓存键
   */
  getCacheKey(code, startDate, endDate) {
    return `${code.toUpperCase()}_${startDate}_${endDate}`;
  }

  /**
   * 检查缓存是否过期
   * @param {string} code 股票代码
   * @param {string} startDate 开始日期
   * @param {string} endDate 结束日期
   * @returns {boolean} 是否过期
   */
  isExpired(code, startDate, endDate) {
    const key = this.getCacheKey(code, startDate, endDate);
    const meta = this.metadata.get(key);
    if (!meta) return true;
    
    const now = Date.now();
    return (now - meta.lastUpdate) > this.config.ttl;
  }

  /**
   * 从缓存获取股票数据
   * @param {string} code 股票代码
   * @param {string} startDate 开始日期
   * @param {string} endDate 结束日期
   * @returns {Array|null} 股票数据数组，未找到返回null
   */
  get(code, startDate, endDate) {
    const key = this.getCacheKey(code, startDate, endDate);
    
    // 检查缓存是否存在且未过期
    if (!this.cache.has(key) || this.isExpired(code, startDate, endDate)) {
      return null;
    }

    return this.cache.get(key);
  }

  /**
   * 将股票数据存入缓存
   * @param {string} code 股票代码
   * @param {Array} data 股票数据数组
   * @param {string} startDate 开始日期
   * @param {string} endDate 结束日期
   * @param {string} stockName 股票名称
   */
  set(code, data, startDate, endDate, stockName = '') {
    const key = this.getCacheKey(code, startDate, endDate);
    
    // 存储数据（无大小限制）
    this.cache.set(key, data);
    
    // 存储元数据
    this.metadata.set(key, {
      lastUpdate: Date.now(),
      dataCount: data.length,
      stockName: stockName,
      startDate: startDate,
      endDate: endDate,
      firstDate: data.length > 0 ? data[0].date : null,
      lastDate: data.length > 0 ? data[data.length - 1].date : null
    });

    console.log(`💾 已缓存股票 ${code}(${stockName}) 数据: ${data.length} 条 [${startDate} - ${endDate}]`);
  }

  /**
   * 按时间范围筛选数据
   * @param {Array} data 原始数据
   * @param {string} startDate 开始日期
   * @param {string} endDate 结束日期
   * @returns {Array} 筛选后的数据
   */
  filterByDateRange(data, startDate, endDate) {
    if (!data || data.length === 0) return [];
    
    return data.filter(item => {
      const itemDate = item.date || item.trade_date;
      if (!itemDate) return false;
      
      if (startDate && itemDate < startDate) return false;
      if (endDate && itemDate > endDate) return false;
      
      return true;
    });
  }

  /**
   * 检查股票是否已缓存
   * @param {string} code 股票代码
   * @param {string} startDate 开始日期
   * @param {string} endDate 结束日期
   * @returns {boolean} 是否已缓存
   */
  has(code, startDate, endDate) {
    const key = this.getCacheKey(code, startDate, endDate);
    return this.cache.has(key) && !this.isExpired(code, startDate, endDate);
  }

  /**
   * 获取缓存统计信息
   * @returns {Object} 统计信息
   */
  getStats() {
    const stats = {
      totalStocks: this.cache.size,
      totalRecords: 0,
      memoryUsage: 0,
      expiredCount: 0,
      stocks: []
    };

    for (const [key, data] of this.cache.entries()) {
      const meta = this.metadata.get(key);
      const [code, startDate, endDate] = key.split('_');
      const isExpired = this.isExpired(code, startDate, endDate);
      
      stats.totalRecords += data.length;
      stats.memoryUsage += JSON.stringify(data).length;
      
      if (isExpired) {
        stats.expiredCount++;
      }

      stats.stocks.push({
        code: code,
        name: meta?.stockName || '',
        recordCount: data.length,
        dateRange: `${startDate} - ${endDate}`,
        lastUpdate: meta?.lastUpdate ? new Date(meta.lastUpdate).toLocaleString() : '',
        firstDate: meta?.firstDate || '',
        lastDate: meta?.lastDate || '',
        isExpired: isExpired
      });
    }

    // 转换内存使用量为MB
    stats.memoryUsage = Math.round(stats.memoryUsage / 1024 / 1024 * 100) / 100;

    return stats;
  }

  /**
   * 清理过期缓存
   */
  cleanup() {
    const expiredKeys = [];
    
    for (const [key, meta] of this.metadata.entries()) {
      const [code, startDate, endDate] = key.split('_');
      if (this.isExpired(code, startDate, endDate)) {
        expiredKeys.push(key);
      }
    }

    // 删除过期缓存
    expiredKeys.forEach(key => {
      this.cache.delete(key);
      this.metadata.delete(key);
    });

    if (expiredKeys.length > 0) {
      console.log(`🧹 已清理 ${expiredKeys.length} 个过期缓存`);
    }

    // 无大小限制，不需要清理最旧缓存
  }

  /**
   * 清空所有缓存
   */
  clear() {
    this.cache.clear();
    this.metadata.clear();
    console.log('🗑️ 已清空所有股票数据缓存');
  }

  /**
   * 删除指定股票的缓存
   * @param {string} code 股票代码
   * @param {string} startDate 开始日期
   * @param {string} endDate 结束日期
   */
  delete(code, startDate, endDate) {
    const key = this.getCacheKey(code, startDate, endDate);
    const deleted = this.cache.delete(key);
    this.metadata.delete(key);
    
    if (deleted) {
      console.log(`🗑️ 已删除股票 ${code} 的缓存 [${startDate} - ${endDate}]`);
    }
  }

  /**
   * 预热缓存 - 批量预加载股票数据
   * @param {Array} codes 股票代码数组
   * @param {Function} loadFunction 数据加载函数
   * @param {Function} logCallback 日志回调函数
   */
  async warmup(codes, loadFunction, logCallback = null) {
    const log = (message, type = 'info') => {
      console.log(message);
      if (logCallback) {
        logCallback(message, type);
      }
    };

    log(`🔥 开始预热缓存，共 ${codes.length} 只股票...`);
    
    let loaded = 0;
    for (const code of codes) {
      if (!this.has(code)) {
        try {
          const data = await loadFunction(code);
          if (data && data.length > 0) {
            this.set(code, data);
            loaded++;
          }
        } catch (error) {
          log(`❌ 预热失败 ${code}: ${error.message}`, 'warning');
        }
      }
    }

    log(`✅ 缓存预热完成，新增 ${loaded} 只股票缓存`);
  }
}

// 创建全局缓存实例
const stockDataCache = new StockDataCache();

export default stockDataCache;
