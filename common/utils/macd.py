"""
MACD 指标工具（迁移至 common/utils）
"""
from typing import List, Optional, Dict
import pandas as pd
import numpy as np


def _to_optional_list(s: pd.Series) -> List[Optional[float]]:
    return [None if pd.isna(v) else float(v) for v in s.tolist()]


def ema(values: List[float], period: int) -> List[Optional[float]]:
    if not isinstance(values, list) or len(values) == 0 or period <= 0:
        return []
    s = pd.Series(values, dtype="float64")
    ema_s = s.ewm(span=period, adjust=False, min_periods=1).mean()
    ema_s = ema_s.where(~ema_s.isna()).ffill()
    return _to_optional_list(ema_s)


def ema_series_allow_null(values: List[Optional[float]], period: int) -> List[Optional[float]]:
    if not isinstance(values, list) or len(values) == 0 or period <= 0:
        return []
    s = pd.Series(values, dtype="float64")
    ema_s = s.ewm(span=period, adjust=False, min_periods=1).mean()
    ema_s = ema_s.where(~ema_s.isna()).ffill()
    return _to_optional_list(ema_s)


def calculate_macd_series(closes: List[float]) -> Dict[str, List[Optional[float]]]:
    if not isinstance(closes, list) or len(closes) == 0:
        return {"dif": [], "dea": [], "bar": []}

    s = pd.Series(closes, dtype="float64")

    ema12 = s.ewm(span=12, adjust=False, min_periods=1).mean().ffill()
    ema26 = s.ewm(span=26, adjust=False, min_periods=1).mean().ffill()
    dif = ema12 - ema26
    dea = dif.ewm(span=9, adjust=False, min_periods=1).mean().ffill()
    bar = 2.0 * (dif - dea)

    return {
        "dif": _to_optional_list(dif),
        "dea": _to_optional_list(dea),
        "bar": _to_optional_list(bar),
    }


__all__ = [
    "ema",
    "ema_series_allow_null",
    "calculate_macd_series",
]

"""
MACD 指标工具（pandas 向量化实现）
"""
from typing import List, Optional, Dict
import pandas as pd
import numpy as np


def _to_optional_list(s: pd.Series) -> List[Optional[float]]:
    return [None if pd.isna(v) else float(v) for v in s.tolist()]


def ema(values: List[float], period: int) -> List[Optional[float]]:
    if not isinstance(values, list) or len(values) == 0 or period <= 0:
        return []
    s = pd.Series(values, dtype="float64")
    ema_s = s.ewm(span=period, adjust=False, min_periods=1).mean()
    ema_s = ema_s.where(~ema_s.isna()).ffill()
    return _to_optional_list(ema_s)


def ema_series_allow_null(values: List[Optional[float]], period: int) -> List[Optional[float]]:
    if not isinstance(values, list) or len(values) == 0 or period <= 0:
        return []
    s = pd.Series(values, dtype="float64")
    ema_s = s.ewm(span=period, adjust=False, min_periods=1).mean()
    ema_s = ema_s.where(~ema_s.isna()).ffill()
    return _to_optional_list(ema_s)


def calculate_macd_series(closes: List[float]) -> Dict[str, List[Optional[float]]]:
    if not isinstance(closes, list) or len(closes) == 0:
        return {"dif": [], "dea": [], "bar": []}

    s = pd.Series(closes, dtype="float64")

    ema12 = s.ewm(span=12, adjust=False, min_periods=1).mean()
    ema12 = ema12.where(~ema12.isna()).ffill()

    ema26 = s.ewm(span=26, adjust=False, min_periods=1).mean()
    ema26 = ema26.where(~ema26.isna()).ffill()

    dif = ema12 - ema26

    dea = dif.ewm(span=9, adjust=False, min_periods=1).mean()
    dea = dea.where(~dea.isna()).ffill()

    bar = 2.0 * (dif - dea)

    return {
        "dif": _to_optional_list(dif),
        "dea": _to_optional_list(dea),
        "bar": _to_optional_list(bar),
    }


__all__ = [
    "ema",
    "ema_series_allow_null",
    "calculate_macd_series",
]


