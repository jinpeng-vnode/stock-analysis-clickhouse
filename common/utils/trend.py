"""
线性趋势工具（迁移至 common/utils）
"""
from typing import List, Optional, Dict, Tuple
import pandas as pd
import numpy as np


def _series_to_optional_list(s: pd.Series) -> List[Optional[float]]:
    return [None if pd.isna(v) else float(v) for v in s.tolist()]


def compute_linear_trend_on_range(values: List[Optional[float]], range_: Dict[str, int]) -> List[Optional[float]]:
    if not isinstance(values, list) or len(values) == 0:
        return []

    n = len(values)
    s = max(0, min(int(range_.get("startIndex", 0)), n - 1))
    e = max(s, min(int(range_.get("endIndex", n - 1)), n - 1))
    m = e - s + 1

    out = pd.Series([np.nan] * n, dtype="float64")

    if m <= 1:
        base_candidate = values[s] if values[s] is not None else (values[0] if values[0] is not None else 0.0)
        base = float(base_candidate)
        out.iloc[s : e + 1] = base
        return _series_to_optional_list(out)

    seg = pd.Series(values[s : e + 1], dtype="float64")
    x = pd.Series(np.arange(m, dtype="float64"))
    mask = seg.notna()
    x_fit = x[mask]
    y_fit = seg[mask]

    if len(y_fit) == 0:
        return _series_to_optional_list(out)

    n_fit = float(len(y_fit))
    sum_x = float(x_fit.sum())
    sum_y = float(y_fit.sum())
    sum_xy = float((x_fit * y_fit).sum())
    sum_xx = float((x_fit * x_fit).sum())
    denom = n_fit * sum_xx - sum_x * sum_x
    if denom == 0.0:
        slope = 0.0
        intercept = sum_y / (n_fit if n_fit != 0 else 1.0)
    else:
        slope = (n_fit * sum_xy - sum_x * sum_y) / denom
        intercept = (sum_y - slope * sum_x) / n_fit

    y_hat = intercept + slope * x
    out.iloc[s : e + 1] = y_hat.values
    return _series_to_optional_list(out)


def compute_linear_slope_on_range(values: List[Optional[float]], range_: Dict[str, int]) -> Optional[float]:
    if not isinstance(values, list) or len(values) == 0:
        return None

    n = len(values)
    s = max(0, min(int(range_.get("startIndex", 0)), n - 1))
    e = max(s, min(int(range_.get("endIndex", n - 1)), n - 1))
    m = e - s + 1

    if m <= 0:
        return None

    seg = pd.Series(values[s : e + 1], dtype="float64")
    x = pd.Series(np.arange(m, dtype="float64"))
    mask = seg.notna()
    x_fit = x[mask]
    y_fit = seg[mask]

    if len(y_fit) == 0:
        return None

    n_fit = float(len(y_fit))
    sum_x = float(x_fit.sum())
    sum_y = float(y_fit.sum())
    sum_xy = float((x_fit * y_fit).sum())
    sum_xx = float((x_fit * x_fit).sum())
    denom = n_fit * sum_xx - sum_x * sum_x
    if denom == 0.0:
        return 0.0
    slope = (n_fit * sum_xy - sum_x * sum_y) / denom
    return float(slope)


def compute_rolling_slope_vectorized(values: List[float], window: int) -> List[Optional[float]]:
    if len(values) == 0:
        return []
    if window <= 1:
        return [0.0] * len(values)

    values_array = np.array(values, dtype=np.float64)
    n = len(values_array)
    slopes = np.full(n, np.nan, dtype=np.float64)
    x_base = np.arange(window, dtype=np.float64)

    for i in range(window - 1, n):
        y_window = values_array[i - window + 1:i + 1]
        valid_mask = ~np.isnan(y_window)
        if valid_mask.sum() < 2:
            continue
        x_valid = x_base[valid_mask]
        y_valid = y_window[valid_mask]
        n_valid = len(y_valid)
        sum_x = x_valid.sum()
        sum_y = y_valid.sum()
        sum_xy = (x_valid * y_valid).sum()
        sum_xx = (x_valid * x_valid).sum()
        denom = n_valid * sum_xx - sum_x * sum_x
        if denom != 0:
            slope = (n_valid * sum_xy - sum_x * sum_y) / denom
            slopes[i] = round(float(slope), 6)
        else:
            slopes[i] = 0.0
    return [None if np.isnan(slope) else slope for slope in slopes]


def compute_rolling_slope_and_fit_vectorized(values: List[float], window: int) -> Tuple[List[Optional[float]], List[Optional[float]]]:
    if len(values) == 0:
        return [], []
    if window <= 1:
        return [0.0] * len(values), values

    values_array = np.array(values, dtype=np.float64)
    n = len(values_array)
    slopes = np.full(n, np.nan, dtype=np.float64)
    fit_values = np.full(n, np.nan, dtype=np.float64)
    x_base = np.arange(window, dtype=np.float64)

    for i in range(window - 1, n):
        y_window = values_array[i - window + 1:i + 1]
        valid_mask = ~np.isnan(y_window)
        if valid_mask.sum() < 2:
            continue
        x_valid = x_base[valid_mask]
        y_valid = y_window[valid_mask]
        n_valid = len(y_valid)
        sum_x = x_valid.sum()
        sum_y = y_valid.sum()
        sum_xy = (x_valid * y_valid).sum()
        sum_xx = (x_valid * x_valid).sum()
        denom = n_valid * sum_xx - sum_x * sum_x
        if denom != 0:
            slope = (n_valid * sum_xy - sum_x * sum_y) / denom
            intercept = (sum_y - slope * sum_x) / n_valid
            slopes[i] = round(float(slope), 6)
            fit_last = intercept + slope * (window - 1)
            fit_values[i] = round(float(fit_last), 6)
        else:
            slopes[i] = 0.0
            fit_values[i] = float(y_valid.mean())
    return (
        [None if np.isnan(s) else s for s in slopes],
        [None if np.isnan(f) else f for f in fit_values],
    )


__all__ = [
    "compute_linear_trend_on_range",
    "compute_linear_slope_on_range",
    "compute_rolling_slope_vectorized",
    "compute_rolling_slope_and_fit_vectorized",
]

"""
线性趋势工具（pandas 向量化实现）
"""
from typing import List, Optional, Dict, Tuple
import pandas as pd
import numpy as np


def _series_to_optional_list(s: pd.Series) -> List[Optional[float]]:
    return [None if pd.isna(v) else float(v) for v in s.tolist()]


def compute_linear_trend_on_range(values: List[Optional[float]], range_: Dict[str, int]) -> List[Optional[float]]:
    if not isinstance(values, list) or len(values) == 0:
        return []

    n = len(values)
    s = max(0, min(int(range_.get("startIndex", 0)), n - 1))
    e = max(s, min(int(range_.get("endIndex", n - 1)), n - 1))
    m = e - s + 1

    out = pd.Series([np.nan] * n, dtype="float64")

    if m <= 1:
        base_candidate = values[s] if values[s] is not None else (values[0] if values[0] is not None else 0.0)
        base = float(base_candidate)
        out.iloc[s : e + 1] = base
        return _series_to_optional_list(out)

    seg = pd.Series(values[s : e + 1], dtype="float64")
    x = pd.Series(np.arange(m, dtype="float64"))
    mask = seg.notna()
    x_fit = x[mask]
    y_fit = seg[mask]

    if len(y_fit) == 0:
        return _series_to_optional_list(out)

    n_fit = float(len(y_fit))
    sum_x = float(x_fit.sum())
    sum_y = float(y_fit.sum())
    sum_xy = float((x_fit * y_fit).sum())
    sum_xx = float((x_fit * x_fit).sum())
    denom = n_fit * sum_xx - sum_x * sum_x
    if denom == 0.0:
        slope = 0.0
        intercept = sum_y / (n_fit if n_fit != 0 else 1.0)
    else:
        slope = (n_fit * sum_xy - sum_x * sum_y) / denom
        intercept = (sum_y - slope * sum_x) / n_fit

    y_hat = intercept + slope * x
    out.iloc[s : e + 1] = y_hat.values
    return _series_to_optional_list(out)


def compute_linear_slope_on_range(values: List[Optional[float]], range_: Dict[str, int]) -> Optional[float]:
    if not isinstance(values, list) or len(values) == 0:
        return None

    n = len(values)
    s = max(0, min(int(range_.get("startIndex", 0)), n - 1))
    e = max(s, min(int(range_.get("endIndex", n - 1)), n - 1))
    m = e - s + 1

    if m <= 0:
        return None

    seg = pd.Series(values[s : e + 1], dtype="float64")
    x = pd.Series(np.arange(m, dtype="float64"))
    mask = seg.notna()
    x_fit = x[mask]
    y_fit = seg[mask]

    if len(y_fit) == 0:
        return None

    n_fit = float(len(y_fit))
    sum_x = float(x_fit.sum())
    sum_y = float(y_fit.sum())
    sum_xy = float((x_fit * y_fit).sum())
    sum_xx = float((x_fit * x_fit).sum())
    denom = n_fit * sum_xx - sum_x * sum_x
    if denom == 0.0:
        return 0.0
    slope = (n_fit * sum_xy - sum_x * sum_y) / denom
    return float(slope)


def compute_rolling_slope_vectorized(values: List[float], window: int) -> List[Optional[float]]:
    if len(values) == 0:
        return []
    if window <= 1:
        return [0.0] * len(values)

    values_array = np.array(values, dtype=np.float64)
    n = len(values_array)
    slopes = np.full(n, np.nan, dtype=np.float64)
    x_base = np.arange(window, dtype=np.float64)
    for i in range(window - 1, n):
        y_window = values_array[i - window + 1:i + 1]
        valid_mask = ~np.isnan(y_window)
        if valid_mask.sum() < 2:
            continue
        x_valid = x_base[valid_mask]
        y_valid = y_window[valid_mask]
        n_valid = len(y_valid)
        sum_x = x_valid.sum()
        sum_y = y_valid.sum()
        sum_xy = (x_valid * y_valid).sum()
        sum_xx = (x_valid * x_valid).sum()
        denom = n_valid * sum_xx - sum_x * sum_x
        if denom != 0:
            slope = (n_valid * sum_xy - sum_x * sum_y) / denom
            slopes[i] = round(float(slope), 6)
        else:
            slopes[i] = 0.0
    return [None if np.isnan(slope) else slope for slope in slopes]


def compute_rolling_slope_and_fit_vectorized(values: List[float], window: int) -> Tuple[List[Optional[float]], List[Optional[float]]]:
    if len(values) == 0:
        return [], []
    if window <= 1:
        return [0.0] * len(values), values

    values_array = np.array(values, dtype=np.float64)
    n = len(values_array)
    slopes = np.full(n, np.nan, dtype=np.float64)
    fit_values = np.full(n, np.nan, dtype=np.float64)
    x_base = np.arange(window, dtype=np.float64)
    for i in range(window - 1, n):
        y_window = values_array[i - window + 1:i + 1]
        valid_mask = ~np.isnan(y_window)
        if valid_mask.sum() < 2:
            continue
        x_valid = x_base[valid_mask]
        y_valid = y_window[valid_mask]
        n_valid = len(y_valid)
        sum_x = x_valid.sum()
        sum_y = y_valid.sum()
        sum_xy = (x_valid * y_valid).sum()
        sum_xx = (x_valid * x_valid).sum()
        denom = n_valid * sum_xx - sum_x * sum_x
        if denom != 0:
            slope = (n_valid * sum_xy - sum_x * sum_y) / denom
            intercept = (sum_y - slope * sum_x) / n_valid
            slopes[i] = round(float(slope), 6)
            fit_last = intercept + slope * (window - 1)
            fit_values[i] = round(float(fit_last), 6)
        else:
            slopes[i] = 0.0
            fit_values[i] = float(y_valid.mean())
    return ([None if np.isnan(s) else s for s in slopes], [None if np.isnan(f) else f for f in fit_values])


__all__ = [
    "compute_linear_trend_on_range",
    "compute_linear_slope_on_range",
    "compute_rolling_slope_vectorized",
    "compute_rolling_slope_and_fit_vectorized",
]


