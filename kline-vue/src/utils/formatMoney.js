/**
 * 金额格式化工具函数
 * 将金额从分转换为合适的单位（亿、万），并根据数值大小自动切换
 */

/**
 * 格式化金额
 * @param {number|string|null|undefined} value - 金额值（单位：分）
 * @param {object} options - 配置选项
 * @param {number} options.decimals - 小数位数，默认2位
 * @param {boolean} options.showUnit - 是否显示单位，默认true
 * @param {string} options.emptyText - 空值显示文本，默认'-'
 * @returns {string} 格式化后的金额字符串
 * 
 * @example
 * formatMoney(100000000) // "1.00亿"
 * formatMoney(10000000)  // "100.00万"
 * formatMoney(100000)    // "1.00万"
 * formatMoney(1000)      // "10.00元"
 * formatMoney(null)      // "-"
 */
export function formatMoney(value, options = {}) {
  const {
    decimals = 2,
    showUnit = true,
    emptyText = '-'
  } = options

  // 处理空值
  if (value === null || value === undefined || value === '') {
    return emptyText
  }

  // 转换为数字
  const numValue = typeof value === 'string' ? parseFloat(value) : value

  // 检查是否为有效数字
  if (isNaN(numValue) || !isFinite(numValue)) {
    return emptyText
  }

  // 金额为0
  if (numValue === 0) {
    return showUnit ? '0.00元' : '0.00'
  }

  // 绝对值，用于判断单位
  const absValue = Math.abs(numValue)
  const sign = numValue < 0 ? '-' : ''

  // 1亿分 = 100,000,000分 = 1,000,000元
  const YI_FEN = 100000000  // 1亿分
  // 1万分 = 10,000分 = 100元
  const WAN_FEN = 10000     // 1万分

  let formattedValue
  let unit = ''

  if (absValue >= YI_FEN) {
    // 大于等于1亿分，转换为亿
    formattedValue = (absValue / YI_FEN).toFixed(decimals)
    unit = showUnit ? '亿' : ''
  } else if (absValue >= WAN_FEN) {
    // 大于等于1万分，转换为万
    formattedValue = (absValue / WAN_FEN).toFixed(decimals)
    unit = showUnit ? '万' : ''
  } else {
    // 小于1万分，转换为元
    formattedValue = (absValue / 100).toFixed(decimals)  // 分转元
    unit = showUnit ? '元' : ''
  }

  // 移除末尾的0
  if (decimals > 0) {
    formattedValue = parseFloat(formattedValue).toFixed(decimals)
  }

  return `${sign}${formattedValue}${unit}`
}

/**
 * 格式化金额（简版，只显示数值和单位，不显示"元"）
 * @param {number|string|null|undefined} value - 金额值（单位：分）
 * @param {number} decimals - 小数位数，默认2位
 * @returns {string} 格式化后的金额字符串
 * 
 * @example
 * formatMoneySimple(100000000) // "1.00亿"
 * formatMoneySimple(10000000)  // "100.00万"
 * formatMoneySimple(100000)    // "1.00万"
 * formatMoneySimple(1000)      // "10.00"
 */
export function formatMoneySimple(value, decimals = 2) {
  return formatMoney(value, { decimals, showUnit: true, emptyText: '-' })
    .replace('元', '')  // 移除"元"单位
}

/**
 * 格式化金额（带颜色，正数绿色，负数红色）
 * @param {number|string|null|undefined} value - 金额值（单位：分）
 * @param {object} options - 配置选项
 * @returns {object} 包含text和color的对象
 */
export function formatMoneyWithColor(value, options = {}) {
  const text = formatMoney(value, options)
  
  if (value === null || value === undefined || value === '') {
    return { text, color: undefined }
  }

  const numValue = typeof value === 'string' ? parseFloat(value) : value
  if (isNaN(numValue) || !isFinite(numValue)) {
    return { text, color: undefined }
  }

  return {
    text,
    color: numValue >= 0 ? '#52c41a' : '#ff4d4f'  // 绿色和红色
  }
}

export default formatMoney


