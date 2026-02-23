"""
买卖点统计工具函数
"""
from typing import List, Optional, Tuple


def calculate_signal_counts(buy_signals: List[int], sell_signals: List[int], period: int) -> Tuple[List[Optional[int]], List[Optional[int]]]:
    if len(buy_signals) != len(sell_signals):
        raise ValueError("买卖信号列表长度必须相同")
    buy_counts: List[Optional[int]] = []
    sell_counts: List[Optional[int]] = []
    for i in range(len(buy_signals)):
        if i < period - 1:
            buy_counts.append(None)
            sell_counts.append(None)
        else:
            recent_buy = buy_signals[i - period + 1:i + 1]
            recent_sell = sell_signals[i - period + 1:i + 1]
            buy_counts.append(sum(recent_buy))
            sell_counts.append(sum(recent_sell))
    return buy_counts, sell_counts


