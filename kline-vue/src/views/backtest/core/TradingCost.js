class TradingCost {
  constructor(config) {
    this.commissionRate = config.commission_rate || 0.0003;
    this.minCommission = config.min_commission || 5;
    this.stampDutyRate = config.stamp_duty_rate || 0.001;
    this.slippageRate = config.slippage_rate || 0.001;
  }

  calculate(amount, direction, code) {
    // 佣金
    const commission = Math.max(amount * this.commissionRate, this.minCommission);
    
    // 过户费（仅上海股票）
    const transferFee = (code && code.startsWith('6')) ? amount * 0.00001 : 0;
    
    // 印花税（仅卖出）
    const stampDuty = direction === 'sell' ? amount * this.stampDutyRate : 0;
    
    // 滑点
    const slippage = amount * this.slippageRate;
    
    return {
      commission: parseFloat(commission.toFixed(2)),
      transfer_fee: parseFloat(transferFee.toFixed(2)),
      stamp_duty: parseFloat(stampDuty.toFixed(2)),
      slippage: parseFloat(slippage.toFixed(2)),
      total_cost: parseFloat((commission + transferFee + stampDuty + slippage).toFixed(2))
    };
  }
}

export default TradingCost;

