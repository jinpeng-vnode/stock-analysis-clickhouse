class BacktestStorage {
  constructor() {
    this.CONFIG_PREFIX = 'backtest_config_';
    this.RESULT_PREFIX = 'backtest_result_';
  }

  // 保存配置
  saveConfig(config) {
    const key = `${this.CONFIG_PREFIX}${config.id}`;
    localStorage.setItem(key, JSON.stringify(config));
    console.log('💾 配置已保存:', config.name);
  }

  // 获取所有配置
  getAllConfigs() {
    const configs = [];
    for (let i = 0; i < localStorage.length; i++) {
      const key = localStorage.key(i);
      if (key.startsWith(this.CONFIG_PREFIX)) {
        const config = JSON.parse(localStorage.getItem(key));
        configs.push(config);
      }
    }
    return configs.sort((a, b) => new Date(b.created_at) - new Date(a.created_at));
  }

  // 获取单个配置
  getConfig(id) {
    const key = `${this.CONFIG_PREFIX}${id}`;
    const data = localStorage.getItem(key);
    return data ? JSON.parse(data) : null;
  }

  // 删除配置
  deleteConfig(id) {
    const key = `${this.CONFIG_PREFIX}${id}`;
    localStorage.removeItem(key);
    console.log('🗑️ 配置已删除:', id);
  }

  // 保存结果
  saveResult(result) {
    const key = `${this.RESULT_PREFIX}${result.id}`;
    localStorage.setItem(key, JSON.stringify(result));
    console.log('💾 回测结果已保存:', result.config_name);
  }

  // 获取所有结果
  getAllResults() {
    const results = [];
    for (let i = 0; i < localStorage.length; i++) {
      const key = localStorage.key(i);
      if (key.startsWith(this.RESULT_PREFIX)) {
        const result = JSON.parse(localStorage.getItem(key));
        // 只返回摘要信息，不包含详细交易记录
        results.push({
          id: result.id,
          config_id: result.config_id,
          config_name: result.config_name,
          start_date: result.start_date,
          end_date: result.end_date,
          initial_capital: result.initial_capital,
          final_capital: result.final_capital,
          total_return: result.total_return,
          max_drawdown: result.max_drawdown,
          win_rate: result.win_rate,
          total_trades: result.total_trades,
          win_trades: result.win_trades,
          loss_trades: result.loss_trades,
          created_at: result.created_at
        });
      }
    }
    return results.sort((a, b) => new Date(b.created_at) - new Date(a.created_at));
  }

  // 获取结果详情
  getResult(id) {
    const key = `${this.RESULT_PREFIX}${id}`;
    const data = localStorage.getItem(key);
    return data ? JSON.parse(data) : null;
  }

  // 删除结果
  deleteResult(id) {
    const key = `${this.RESULT_PREFIX}${id}`;
    localStorage.removeItem(key);
    console.log('🗑️ 回测结果已删除:', id);
  }

  // 清空所有结果
  clearAllResults() {
    const keys = [];
    for (let i = 0; i < localStorage.length; i++) {
      const key = localStorage.key(i);
      if (key.startsWith(this.RESULT_PREFIX)) {
        keys.push(key);
      }
    }
    keys.forEach(key => localStorage.removeItem(key));
    console.log('🗑️ 所有回测结果已清空');
  }

  // 清空所有数据
  clearAll() {
    const keys = [];
    for (let i = 0; i < localStorage.length; i++) {
      const key = localStorage.key(i);
      if (key.startsWith(this.CONFIG_PREFIX) || key.startsWith(this.RESULT_PREFIX)) {
        keys.push(key);
      }
    }
    keys.forEach(key => localStorage.removeItem(key));
    console.log('🗑️ 所有回测数据已清空');
  }
}

export default new BacktestStorage();

