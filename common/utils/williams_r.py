"""
Williams %R 指标工具（迁移至 common/utils）
"""
from typing import List, Optional, Tuple, Dict
import pandas as pd
import numpy as np


def _series_to_opt_list(s: pd.Series) -> List[Optional[float]]:
    return [None if pd.isna(v) else float(v) for v in s.tolist()]


def compute_williams_r(highs: List[float], lows: List[float], closes: List[float], n: int = 14) -> List[Optional[float]]:
    length = len(closes)
    if length == 0 or n <= 1:
        return [None] * length

    h = pd.Series(highs, dtype="float64")
    l = pd.Series(lows, dtype="float64")
    c = pd.Series(closes, dtype="float64")

    rolling_high = h.rolling(window=n, min_periods=n).max()
    rolling_low = l.rolling(window=n, min_periods=n).min()
    denom = rolling_high - rolling_low
    wr = (rolling_high - c) / denom * 100.0
    wr = wr.mask((denom == 0) | denom.isna())
    return _series_to_opt_list(wr)


def compute_threshold_points(category: List[str], wr: List[Optional[float]], buy_threshold: float = 80.0, sell_threshold: float = 20.0) -> Dict[str, List[Tuple[str, float]]]:
    s = pd.Series(wr, dtype="float64")
    idx = pd.Index(range(min(len(category), len(wr))))
    buy_mask = s.ge(buy_threshold)
    sell_mask = s.le(sell_threshold)
    buy_points = [(category[i], float(s.iloc[i])) for i in idx[buy_mask.fillna(False)]]
    sell_points = [(category[i], float(s.iloc[i])) for i in idx[sell_mask.fillna(False)]]
    return {"buyPoints": buy_points, "sellPoints": sell_points}


def compute_threshold_points_with_near(category: List[str], wr6: List[Optional[float]], wr10: List[Optional[float]], buy_threshold: float = 80.0, sell_threshold: float = 20.0, near: float = 1.0) -> Dict[str, List[Tuple[str, float]]]:
    a = pd.Series(wr6, dtype="float64")
    b = pd.Series(wr10, dtype="float64")
    length = min(len(category), len(a), len(b))
    a = a.iloc[:length]
    b = b.iloc[:length]
    diff = (a - b).abs()
    near_mask = diff.lt(near)
    buy_mask = a.ge(buy_threshold)
    sell_mask = a.le(sell_threshold)
    idx = pd.Index(range(length))
    buy_points = [(category[i], float(a.iloc[i])) for i in idx[(near_mask & buy_mask).fillna(False)]]
    sell_points = [(category[i], float(a.iloc[i])) for i in idx[(near_mask & sell_mask).fillna(False)]]
    return {"buyPoints": buy_points, "sellPoints": sell_points}


def compute_close_points(category: List[str], wr6: List[Optional[float]], wr10: List[Optional[float]], threshold: float = 1.0) -> List[Tuple[str, float]]:
    a = pd.Series(wr6, dtype="float64")
    b = pd.Series(wr10, dtype="float64")
    length = min(len(category), len(a), len(b))
    a = a.iloc[:length]
    b = b.iloc[:length]
    diff = (a - b).abs()
    mask = diff.lt(threshold)
    idx = pd.Index(range(length))
    points = [(category[i], float(a.iloc[i])) for i in idx[mask.fillna(False)]]
    return points


__all__ = [
    "compute_williams_r",
    "compute_threshold_points",
    "compute_threshold_points_with_near",
    "compute_close_points",
]

"""
Williams %R 指标工具（pandas 向量化实现）
"""
from typing import List, Optional, Tuple, Dict
import pandas as pd
import numpy as np


def _series_to_opt_list(s: pd.Series) -> List[Optional[float]]:
    return [None if pd.isna(v) else float(v) for v in s.tolist()]


def compute_williams_r(highs: List[float], lows: List[float], closes: List[float], n: int = 14) -> List[Optional[float]]:
    length = len(closes)
    if length == 0 or n <= 1:
        return [None] * length
    h = pd.Series(highs, dtype="float64")
    l = pd.Series(lows, dtype="float64")
    c = pd.Series(closes, dtype="float64")
    rolling_high = h.rolling(window=n, min_periods=n).max()
    rolling_low = l.rolling(window=n, min_periods=n).min()
    denom = rolling_high - rolling_low
    wr = (rolling_high - c) / denom * 100.0
    wr = wr.mask((denom == 0) | denom.isna())
    return _series_to_opt_list(wr)


def compute_threshold_points(category: List[str], wr: List[Optional[float]], buy_threshold: float = 80.0, sell_threshold: float = 20.0) -> Dict[str, List[Tuple[str, float]]]:
    s = pd.Series(wr, dtype="float64")
    idx = pd.Index(range(min(len(category), len(wr))))
    buy_mask = s.ge(buy_threshold)
    sell_mask = s.le(sell_threshold)
    buy_points = [(category[i], float(s.iloc[i])) for i in idx[buy_mask.fillna(False)]]
    sell_points = [(category[i], float(s.iloc[i])) for i in idx[sell_mask.fillna(False)]]
    return {"buyPoints": buy_points, "sellPoints": sell_points}


def compute_threshold_points_with_near(category: List[str], wr6: List[Optional[float]], wr10: List[Optional[float]], buy_threshold: float = 80.0, sell_threshold: float = 20.0, near: float = 1.0) -> Dict[str, List[Tuple[str, float]]]:
    a = pd.Series(wr6, dtype="float64")
    b = pd.Series(wr10, dtype="float64")
    length = min(len(category), len(a), len(b))
    a = a.iloc[:length]
    b = b.iloc[:length]
    diff = (a - b).abs()
    near_mask = diff.lt(near)
    buy_mask = a.ge(buy_threshold)
    sell_mask = a.le(sell_threshold)
    idx = pd.Index(range(length))
    buy_points = [(category[i], float(a.iloc[i])) for i in idx[(near_mask & buy_mask).fillna(False)]]
    sell_points = [(category[i], float(a.iloc[i])) for i in idx[(near_mask & sell_mask).fillna(False)]]
    return {"buyPoints": buy_points, "sellPoints": sell_points}


def compute_close_points(category: List[str], wr6: List[Optional[float]], wr10: List[Optional[float]], threshold: float = 1.0) -> List[Tuple[str, float]]:
    a = pd.Series(wr6, dtype="float64")
    b = pd.Series(wr10, dtype="float64")
    length = min(len(category), len(a), len(b))
    a = a.iloc[:length]
    b = b.iloc[:length]
    diff = (a - b).abs()
    mask = diff.lt(threshold)
    idx = pd.Index(range(length))
    points = [(category[i], float(a.iloc[i])) for i in idx[mask.fillna(False)]]
    return points


__all__ = [
    "compute_williams_r",
    "compute_threshold_points",
    "compute_threshold_points_with_near",
    "compute_close_points",
]


