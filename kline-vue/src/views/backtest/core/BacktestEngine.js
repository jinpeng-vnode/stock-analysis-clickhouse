import jsonLogic from 'json-logic-js';
import TradingCost from './TradingCost';
import PositionManager from './PositionManager';

class BacktestEngine {
  constructor(config) {
    console.log('🔧 BacktestEngine 接收到的配置:', JSON.stringify(config, null, 2));
    this.config = config;
    this.tradingCost = new TradingCost(config);
    this.positionManager = new PositionManager(config);
    
    // 初始化账户
    this.account = {
      cash: config.initial_capital,
      positions: {},
      total_value: config.initial_capital
    };
    
    // 记录数组
    this.trades = [];
    this.accountSnapshots = [];
    
    // 日志回调函数
    this.logCallback = null;
    
    // 每日购买数跟踪（用于限制每日最大购买数）
    this.dailyBuyCount = {}; // {日期: 购买数量}
    
    // 股票历史数据缓存（按股票代码组织，用于检查5日内跌停）
    this.stockHistory = {}; // {股票代码: [{date, change_pct, ...}, ...]}
  }
  
  // 设置日志回调
  setLogCallback(callback) {
    this.logCallback = callback;
  }
  
  // 日志方法
  log(message, type = 'info') {
    console.log(message);
    if (this.logCallback) {
      this.logCallback(message, type);
    }
  }

  // 运行回测
  async run(stockData, onProgress, logCallback) {
    try {
      const log = (message, type = 'info') => {
        console.log(message);
        if (logCallback) {
          logCallback(message, type);
        }
      };
      
      log('🚀 开始回测，数据量: ' + stockData.length);
      
      // 检查数据
      if (!stockData || stockData.length === 0) {
        throw new Error('股票数据为空');
      }
      
      // 输出配置信息
      log('⚙️ 回测配置:');
      log('  - 初始资金: ' + this.config.initial_capital);
      log('  - 最大持仓股票数: ' + this.config.position_config.max_stocks);
      log('  - 单股最大仓位: ' + this.config.position_config.max_position_per_stock);
      log('  - 每日最大购买数: ' + (this.config.max_daily_buy_count || '无限制'));
      log('  - 固定规则: 5日内有跌停的股票不可买入');
      log('  - 买入规则: ' + JSON.stringify(this.config.buy_rule, null, 2));
      log('  - 卖出规则: ' + JSON.stringify(this.config.sell_rule, null, 2));
      
      // 按日期分组数据
      const dataByDate = this.groupByDate(stockData);
      const dates = Object.keys(dataByDate).sort();
      
      if (dates.length === 0) {
        throw new Error('没有有效的交易日数据');
      }
      
      log('📅 回测日期范围: ' + dates[0] + ' 至 ' + dates[dates.length - 1]);
      log('📊 总交易日数: ' + dates.length);
      
      // 构建股票历史数据缓存（按股票代码组织，按日期排序）
      this.buildStockHistory(stockData);
      log('📚 已构建股票历史数据缓存，用于检查5日内跌停规则');
    
    for (let i = 0; i < dates.length; i++) {
      const date = dates[i];
      const todayData = dataByDate[date];
      
      // 重置当日购买数
      this.dailyBuyCount[date] = 0;
      
      log(`\n📅 ========== 处理交易日 ${i + 1}/${dates.length}: ${date} ==========`);
      log(`📊 当日数据: ${todayData.length}只股票`);
      log(`💰 当前资金: ${this.account.cash.toFixed(2)}`);
      log(`📈 当前持仓: ${Object.keys(this.account.positions).length}只`);
      
      // 1. 更新持仓市值
      this.updatePositions(todayData);
      
      // 2. 检查卖出条件
      this.checkSellSignals(date, todayData);
      
      // 3. 检查买入条件
      this.checkBuySignals(date, todayData);
      
      // 4. 保存快照
      this.saveSnapshot(date);
      
      // 5. 进度回调
      if (onProgress) {
        onProgress({
          date,
          progress: ((i + 1) / dates.length) * 100,
          current_value: this.account.total_value
        });
      }
    }
    
      // 生成报告
      const report = this.generateReport();
      log('✅ 回测完成！');
      log('📈 总收益率: ' + (report.total_return * 100).toFixed(2) + '%');
      log('📉 最大回撤: ' + (report.max_drawdown * 100).toFixed(2) + '%');
      log('🎯 胜率: ' + (report.win_rate * 100).toFixed(2) + '%');
      log('💰 最终资金: ' + report.final_capital.toFixed(2));
      
      return report;
    } catch (error) {
      console.error('❌ 回测过程中发生错误:', error);
      throw error;
    }
  }

  // 检查买入信号
  checkBuySignals(date, stockData) {
    const positionCount = Object.keys(this.account.positions).length;
    const maxDailyBuy = this.config.max_daily_buy_count || Infinity; // 每日最大购买数，默认无限制
    
    // 确保当日购买数已初始化
    if (!this.dailyBuyCount[date]) {
      this.dailyBuyCount[date] = 0;
    }
    
    this.log(`🔍 [${date}] 检查买入信号，当前持仓: ${positionCount}/${this.config.position_config.max_stocks}，候选股票: ${stockData.length}只，今日已购买: ${this.dailyBuyCount[date]}/${maxDailyBuy}`);
    
    let buySignalCount = 0;
    let ruleEvaluationCount = 0;
    let skippedHolding = 0;
    let skippedDailyLimit = 0;
    let skippedLimitDown = 0; // 跳过5日内有跌停的股票数量
    
    for (const stock of stockData) {
      // 跳过已持仓的股票
      if (this.account.positions[stock.code]) {
        skippedHolding++;
        continue;
      }
      
      // 特殊规则：不买入 ST 股票（含 *ST），名称前缀匹配
      const stockName = String(stock.name || '').toUpperCase();
      if (/^\*?ST/.test(stockName)) {
        this.log(`⛔ [${date}] 跳过ST股票: ${stock.code} ${stock.name}`);
        continue;
      }
      
      // 固定规则：5日内有跌停的股票不可买入
      if (this.hasLimitDownInLast5Days(stock.code, date)) {
        skippedLimitDown++;
        continue; // 静默跳过，避免日志过多
      }
      
      // 检查持仓数量限制
      if (positionCount >= this.config.position_config.max_stocks) {
        this.log(`⚠️ [${date}] 已达到最大持仓数量限制: ${this.config.position_config.max_stocks}`);
        break;
      }
      
      // 检查每日最大购买数限制（动态检查）
      if (this.dailyBuyCount[date] >= maxDailyBuy) {
        skippedDailyLimit++;
        if (skippedDailyLimit === 1) {
          this.log(`⚠️ [${date}] 已达到每日最大购买数限制: ${maxDailyBuy}，跳过后续买入信号`);
        }
        continue;
      }
      
      ruleEvaluationCount++;
      
      // 构造规则评估数据，确保字段名一致
      const evalData = {
        ...stock,
        close: stock.close ?? stock.close_price,
        close_price: stock.close ?? stock.close_price,
        wr6: stock.wr6,
        wr10: stock.wr10,
        slope_180: stock.slope_180,
        slope_7: stock.slope_7,
        fit_7: stock.fit_7,
        fit_180: stock.fit_180,
        best_buy: stock.best_buy,
        best_sell: stock.best_sell
      };
      
      // 使用规则引擎评估买入条件
      try {
        const shouldBuy = jsonLogic.apply(this.config.buy_rule, evalData);
        
        if (shouldBuy) {
          buySignalCount++;
          this.log(`✅ [${date}] 买入信号: ${stock.code} ${stock.name}, 价格: ${stock.close || stock.close_price}`);
          this.executeBuy(date, stock);
          
          // 更新当日购买数
          this.dailyBuyCount[date] = (this.dailyBuyCount[date] || 0) + 1;
          
          // 再次检查是否达到每日限制
          if (this.dailyBuyCount[date] >= maxDailyBuy) {
            this.log(`⚠️ [${date}] 已达到每日最大购买数限制: ${maxDailyBuy}，停止买入`);
            break;
          }
        }
      } catch (error) {
        this.log(`❌ [${date}] 规则评估失败: ${stock.code} - ${error.message}`, 'error');
        console.error('规则评估错误:', error, '评估数据:', evalData);
      }
    }
    
    this.log(`📈 [${date}] 买入信号检查完成: 跳过持仓${skippedHolding}只，跳过5日跌停${skippedLimitDown}只，跳过每日限制${skippedDailyLimit}只，评估${ruleEvaluationCount}只股票，触发${buySignalCount}个买入信号`);
  }

  // 分析卖出原因
  analyzeSellReason(sellRule, evalData) {
    if (!sellRule || typeof sellRule !== 'object') {
      return '未知原因';
    }
    
    const reasons = [];
    
    // 分析规则结构
    const analyzeNode = (node, path = '') => {
      if (!node || typeof node !== 'object') return;
      
      const keys = Object.keys(node);
      if (keys.length !== 1) return;
      
      const op = keys[0];
      const val = node[op];
      
      if (op === 'and' && Array.isArray(val)) {
        // AND 条件：所有子条件都必须满足
        val.forEach((child, index) => {
          const childPath = path ? `${path}.and[${index}]` : `and[${index}]`;
          analyzeNode(child, childPath);
        });
      } else if (op === 'or' && Array.isArray(val)) {
        // OR 条件：找出具体满足的子条件
        const satisfiedConditions = [];
        val.forEach((child, index) => {
          const childPath = path ? `${path}.or[${index}]` : `or[${index}]`;
          if (this.evaluateCondition(child, evalData)) {
            // 递归分析满足的子条件
            const childReasons = [];
            this.analyzeNodeReasons(child, evalData, childReasons, childPath);
            if (childReasons.length > 0) {
              satisfiedConditions.push(...childReasons);
            } else {
              satisfiedConditions.push(`条件${index + 1}满足`);
            }
          }
        });
        if (satisfiedConditions.length > 0) {
          reasons.push(...satisfiedConditions);
        }
      } else if (op === '!') {
        // NOT 条件
        const notSatisfied = !this.evaluateCondition(val, evalData);
        if (notSatisfied) {
          reasons.push(`NOT条件满足 (${path || 'root'})`);
        }
      } else if (Array.isArray(val) && val.length === 2) {
        // 二元比较操作
        const left = val[0];
        const right = val[1];
        
        if (left && typeof left === 'object' && left.var) {
          const fieldName = left.var;
          const fieldValue = evalData[fieldName];
          const operator = op;
          const targetValue = right;
          
          const conditionMet = this.evaluateBinaryCondition(fieldValue, operator, targetValue);
          if (conditionMet) {
            reasons.push(`${fieldName} ${this.getOperatorText(operator)} ${targetValue} (当前值: ${fieldValue})`);
          }
        }
      }
    };
    
    // 专门用于分析节点原因的方法
    this.analyzeNodeReasons = (node, evalData, reasons, path = '') => {
      if (!node || typeof node !== 'object') return;
      
      const keys = Object.keys(node);
      if (keys.length !== 1) return;
      
      const op = keys[0];
      const val = node[op];
      
      if (op === 'and' && Array.isArray(val)) {
        val.forEach((child, index) => {
          const childPath = path ? `${path}.and[${index}]` : `and[${index}]`;
          this.analyzeNodeReasons(child, evalData, reasons, childPath);
        });
      } else if (op === 'or' && Array.isArray(val)) {
        val.forEach((child, index) => {
          const childPath = path ? `${path}.or[${index}]` : `or[${index}]`;
          if (this.evaluateCondition(child, evalData)) {
            this.analyzeNodeReasons(child, evalData, reasons, childPath);
          }
        });
      } else if (op === '!') {
        const notSatisfied = !this.evaluateCondition(val, evalData);
        if (notSatisfied) {
          reasons.push(`NOT条件满足`);
        }
      } else if (Array.isArray(val) && val.length === 2) {
        const left = val[0];
        const right = val[1];
        
        if (left && typeof left === 'object' && left.var) {
          const fieldName = left.var;
          const fieldValue = evalData[fieldName];
          const operator = op;
          const targetValue = right;
          
          const conditionMet = this.evaluateBinaryCondition(fieldValue, operator, targetValue);
          if (conditionMet) {
            reasons.push(`${fieldName} ${this.getOperatorText(operator)} ${targetValue} (当前值: ${fieldValue})`);
          }
        }
      }
    };
    
    analyzeNode(sellRule);
    
    return reasons.length > 0 ? reasons.join('; ') : '规则条件满足';
  }
  
  // 评估单个条件
  evaluateCondition(condition, evalData) {
    if (!condition || typeof condition !== 'object') return false;
    
    const keys = Object.keys(condition);
    if (keys.length !== 1) return false;
    
    const op = keys[0];
    const val = condition[op];
    
    if (op === 'and' && Array.isArray(val)) {
      return val.every(child => this.evaluateCondition(child, evalData));
    } else if (op === 'or' && Array.isArray(val)) {
      return val.some(child => this.evaluateCondition(child, evalData));
    } else if (op === '!') {
      return !this.evaluateCondition(val, evalData);
    } else if (Array.isArray(val) && val.length === 2) {
      const left = val[0];
      const right = val[1];
      
      if (left && typeof left === 'object' && left.var) {
        const fieldValue = evalData[left.var];
        return this.evaluateBinaryCondition(fieldValue, op, right);
      }
    }
    
    return false;
  }
  
  // 评估二元条件
  evaluateBinaryCondition(left, operator, right) {
    switch (operator) {
      case '==': return left == right;
      case '!=': return left != right;
      case '>': return left > right;
      case '>=': return left >= right;
      case '<': return left < right;
      case '<=': return left <= right;
      case 'in': return Array.isArray(right) && right.includes(left);
      case 'nin': return Array.isArray(right) && !right.includes(left);
      default: return false;
    }
  }
  
  // 获取操作符文本
  getOperatorText(operator) {
    const opMap = {
      '==': '等于',
      '!=': '不等于',
      '>': '大于',
      '>=': '大于等于',
      '<': '小于',
      '<=': '小于等于',
      'in': '在列表中',
      'nin': '不在列表中'
    };
    return opMap[operator] || operator;
  }

  // 检查卖出信号
  checkSellSignals(date, stockData) {
    const stockMap = {};
    stockData.forEach(s => stockMap[s.code] = s);
    
    for (const code in this.account.positions) {
      const position = this.account.positions[code];
      const stock = stockMap[code];
      
      if (!stock) continue;
      
      // 计算持仓盈亏
      const profit_pct = (stock.close - position.cost_price) / position.cost_price;
      
      // 构造评估数据
      const evalData = {
        ...stock,
        profit_pct,
        holding_days: this.calculateHoldingDays(date, position.buy_date),
        wr6: stock.wr6,
        wr10: stock.wr10,
        slope_180: stock.slope_180,
        slope_7: stock.slope_7,
        fit_7: stock.fit_7,
        fit_180: stock.fit_180,
        best_buy: stock.best_buy,
        best_sell: stock.best_sell
      };
      
      // 使用规则引擎评估卖出条件
      try {
        const shouldSell = jsonLogic.apply(this.config.sell_rule, evalData);
        
        if (shouldSell) {
          // 分析卖出原因
          const sellReason = this.analyzeSellReason(this.config.sell_rule, evalData);
          
          this.log(`🔴 [${date}] 卖出信号: ${stock.code} ${stock.name}, 价格: ${stock.close_price}, 盈亏: ${(profit_pct * 100).toFixed(2)}%`);
          this.log(`📋 卖出原因: ${sellReason}`);
          
          this.executeSell(date, stock, position, sellReason);
        }
      } catch (error) {
        this.log(`❌ [${date}] 卖出规则评估失败: ${stock.code} - ${error.message}`, 'error');
        console.error('卖出规则评估错误:', error, '评估数据:', evalData);
      }
    }
  }

  // 执行买入
  executeBuy(date, stock) {
    const price = stock.close || stock.close_price;
    
    // 计算仓位
    const quantity = this.positionManager.calculatePositionSize(
      price,
      this.account
    );
    
    if (quantity === 0) {
      this.log(`⚠️ 资金不足，无法买入 ${stock.code}`);
      return;
    }
    
    // 计算成本
    const amount = price * quantity;
    const cost = this.tradingCost.calculate(amount, 'buy', stock.code);
    const totalCost = amount + cost.total_cost;
    
    // 检查资金
    if (this.account.cash < totalCost) {
      this.log(`⚠️ 资金不足，需要: ${totalCost.toFixed(2)}, 可用: ${this.account.cash.toFixed(2)}`);
      return;
    }
    
    // 更新账户
    this.account.cash -= totalCost;
    this.account.positions[stock.code] = {
      code: stock.code,
      name: stock.name,
      quantity,
      cost_price: price,
      buy_date: date
    };
    
    // 记录交易
    this.trades.push({
      date,
      code: stock.code,
      name: stock.name,
      direction: 'buy',
      price: price,
      quantity,
      amount,
      ...cost,
      signal_type: 'best_buy'
    });
    
    this.log(`💵 买入成功: ${quantity}股, 成本: ${totalCost.toFixed(2)}, 剩余资金: ${this.account.cash.toFixed(2)}`);
  }

  // 执行卖出
  executeSell(date, stock, position, sellReason = '规则条件满足') {
    const price = stock.close || stock.close_price;
    const amount = price * position.quantity;
    const cost = this.tradingCost.calculate(amount, 'sell', stock.code);
    const totalAmount = amount - cost.total_cost;
    
    // 计算盈亏
    const profit = totalAmount - (position.cost_price * position.quantity);
    const profitPct = profit / (position.cost_price * position.quantity);
    
    // 更新账户
    this.account.cash += totalAmount;
    delete this.account.positions[stock.code];
    
    // 记录交易
    this.trades.push({
      date,
      code: stock.code,
      name: stock.name,
      direction: 'sell',
      price: price,
      quantity: position.quantity,
      amount,
      ...cost,
      profit,
      profit_pct: profitPct,
      signal_type: 'best_sell',
      sell_reason: sellReason
    });
    
    this.log(`💰 卖出成功: ${position.quantity}股, 收入: ${totalAmount.toFixed(2)}, 盈亏: ${profit.toFixed(2)} (${(profitPct * 100).toFixed(2)}%)`);
    this.log(`📋 卖出原因: ${sellReason}`);
  }

  // 更新持仓市值
  updatePositions(stockData) {
    const stockMap = {};
    stockData.forEach(s => stockMap[s.code] = s);
    
    let positionValue = 0;
    for (const code in this.account.positions) {
      const position = this.account.positions[code];
      const stock = stockMap[code];
      if (stock) {
        const price = stock.close || stock.close_price;
        positionValue += price * position.quantity;
      }
    }
    
    this.account.total_value = this.account.cash + positionValue;
  }

  // 保存快照
  saveSnapshot(date) {
    // 统计当日买入和卖出股票数量
    const todayBuyTrades = this.trades.filter(trade => 
      trade.direction === 'buy' && trade.date === date
    );
    const todaySellTrades = this.trades.filter(trade => 
      trade.direction === 'sell' && trade.date === date
    );
    const dailyBuyCount = todayBuyTrades.length;
    const dailySellCount = todaySellTrades.length;
    
    this.accountSnapshots.push({
      date,
      cash: this.account.cash,
      position_value: this.account.total_value - this.account.cash,
      total_value: this.account.total_value,
      total_return: (this.account.total_value - this.config.initial_capital) / this.config.initial_capital,
      daily_buy_count: dailyBuyCount,
      daily_sell_count: dailySellCount
    });
  }

  // 生成报告
  generateReport() {
    const finalValue = this.account.total_value;
    const totalReturn = (finalValue - this.config.initial_capital) / this.config.initial_capital;
    
    // 计算胜率
    const sellTrades = this.trades.filter(t => t.direction === 'sell');
    const winTrades = sellTrades.filter(t => {
      const buyTrade = this.trades.find(bt => 
        bt.code === t.code && bt.direction === 'buy' && bt.date < t.date
      );
      return buyTrade && t.price > buyTrade.price;
    });
    
    const winRate = sellTrades.length > 0 ? winTrades.length / sellTrades.length : 0;
    
    // 计算最大回撤
    let maxDrawdown = 0;
    let peak = this.config.initial_capital;
    for (const snapshot of this.accountSnapshots) {
      if (snapshot.total_value > peak) {
        peak = snapshot.total_value;
      }
      const drawdown = (snapshot.total_value - peak) / peak;
      if (drawdown < maxDrawdown) {
        maxDrawdown = drawdown;
      }
    }
    
    // 计算平均盈亏
    const avgProfit = winTrades.length > 0 
      ? winTrades.reduce((sum, t) => sum + (t.profit_pct || 0), 0) / winTrades.length 
      : 0;
    const lossTrades = sellTrades.filter(t => !winTrades.includes(t));
    const avgLoss = lossTrades.length > 0 
      ? lossTrades.reduce((sum, t) => sum + (t.profit_pct || 0), 0) / lossTrades.length 
      : 0;
    
    return {
      id: `result_${Date.now()}`,
      config_id: this.config.id,
      config_name: this.config.name,
      start_date: this.config.start_date,
      end_date: this.config.end_date,
      initial_capital: this.config.initial_capital,
      final_capital: finalValue,
      total_return: totalReturn,
      max_drawdown: maxDrawdown,
      win_rate: winRate,
      total_trades: this.trades.length,
      win_trades: winTrades.length,
      loss_trades: lossTrades.length,
      avg_profit: avgProfit,
      avg_loss: avgLoss,
      trades: this.trades,
      account_snapshots: this.accountSnapshots,
      // 添加规则信息
      buy_rule: this.config.buy_rule,
      sell_rule: this.config.sell_rule,
      position_config: this.config.position_config,
      created_at: new Date().toISOString()
    };
  }

  // 辅助方法
  groupByDate(stockData) {
    const grouped = {};
    for (const item of stockData) {
      const date = item.date || item.trade_date || item.日期;
      if (!date) {
        console.warn('⚠️ 股票数据缺少日期字段:', item);
        continue;
      }
      if (!grouped[date]) {
        grouped[date] = [];
      }
      grouped[date].push(item);
    }
    return grouped;
  }

  

  calculateHoldingDays(currentDate, buyDate) {
    const diff = new Date(currentDate) - new Date(buyDate);
    return Math.floor(diff / (1000 * 60 * 60 * 24));
  }

  // 构建股票历史数据缓存（按股票代码组织，按日期排序）
  buildStockHistory(stockData) {
    this.stockHistory = {};
    
    // 按股票代码分组
    for (const item of stockData) {
      const code = item.code;
      if (!code) continue;
      
      if (!this.stockHistory[code]) {
        this.stockHistory[code] = [];
      }
      
      // 保存日期和涨跌幅
      this.stockHistory[code].push({
        date: item.date || item.trade_date,
        change_pct: item.change_pct || null
      });
    }
    
    // 对每个股票的数据按日期排序
    for (const code in this.stockHistory) {
      this.stockHistory[code].sort((a, b) => {
        return a.date.localeCompare(b.date);
      });
    }
  }

  // 检查股票最近5个交易日是否有跌停
  // 跌停判断：A股普通股票跌停为-9.9%或-10%，ST股票为-5%
  hasLimitDownInLast5Days(code, currentDate) {
    const history = this.stockHistory[code];
    if (!history || history.length === 0) {
      return false; // 没有历史数据，不阻止买入
    }
    
    // 找到当前日期在历史数据中的位置
    const currentIndex = history.findIndex(item => item.date === currentDate);
    if (currentIndex === -1) {
      return false; // 找不到当前日期数据，不阻止买入
    }
    
    // 检查最近5个交易日（不包括当前日期）
    const startIndex = Math.max(0, currentIndex - 5);
    const endIndex = currentIndex; // 不包括当前日期
    
    for (let i = startIndex; i < endIndex; i++) {
      const item = history[i];
      const changePct = item.change_pct;
      
      // 判断跌停：涨跌幅 <= -9.9%（A股普通股票跌停）
      // 注意：这里使用-9.9而不是-10，因为实际数据可能有精度问题
      if (changePct !== null && changePct !== undefined && changePct <= -7) {
        return true; // 发现跌停
      }
    }
    
    return false; // 最近5个交易日没有跌停
  }
}

export default BacktestEngine;

