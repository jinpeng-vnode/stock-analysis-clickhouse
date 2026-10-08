class PositionManager {
  constructor(config) {
    this.method = config.position_config.method;
    this.ratio = config.position_config.ratio || 0.1;
    this.fixedAmount = config.position_config.fixed_amount || 10000;
    this.fixedQuantity = config.position_config.fixed_quantity || 100;
    this.maxPositionPerStock = config.position_config.max_position_per_stock || 0.3;
  }

  calculatePositionSize(price, account) {
    console.log(`💰 PositionManager 计算仓位: 价格=${price}, 现金=${account.cash}, 总价值=${account.total_value}`);
    
    let quantity = 0;
    
    // 根据方法计算股数
    if (this.method === 'fixed_quantity') {
      // 固定股数方法
      quantity = this.fixedQuantity;
      console.log(`📊 固定股数计算: 方法=${this.method}, 固定股数=${quantity}`);
    } else {
      // 原有方法：先计算目标金额，再计算股数
      let targetAmount = 0;
      
      if (this.method === 'fixed_amount') {
        targetAmount = this.fixedAmount;
      } else if (this.method === 'fixed_ratio') {
        targetAmount = account.total_value * this.ratio;
      }
      
      console.log(`📊 目标金额计算: 方法=${this.method}, 比例=${this.ratio}, 目标金额=${targetAmount}`);
      
      // 检查单股最大仓位限制
      const maxAmount = account.total_value * this.maxPositionPerStock;
      targetAmount = Math.min(targetAmount, maxAmount);
      
      console.log(`📈 单股最大仓位限制: 最大金额=${maxAmount}, 限制后目标金额=${targetAmount}`);
      
      // 检查可用资金
      targetAmount = Math.min(targetAmount, account.cash);
      
      console.log(`💵 可用资金限制: 现金=${account.cash}, 最终目标金额=${targetAmount}`);
      
      // 计算股数（100股为1手）
      quantity = Math.floor(targetAmount / price / 100) * 100;
    }
    
    // 对于固定股数方法，需要检查资金是否充足
    if (this.method === 'fixed_quantity') {
      const requiredAmount = price * quantity;
      if (requiredAmount > account.cash) {
        console.log(`⚠️ 资金不足，需要: ${requiredAmount.toFixed(2)}, 可用: ${account.cash.toFixed(2)}`);
        quantity = 0;
      } else {
        console.log(`✅ 固定股数: ${quantity}股, 需要资金: ${requiredAmount.toFixed(2)}`);
      }
    }
    
    console.log(`📦 最终股数: ${quantity}`);
    
    return quantity;
  }
}

export default PositionManager;

