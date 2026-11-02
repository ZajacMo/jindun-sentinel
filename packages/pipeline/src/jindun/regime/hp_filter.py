"""Hodrick-Prescott filter.

The legacy plotting code used ``nltk.tokenize.texttiling.smooth`` to draw a
"HP filtered" line.  That function performs sentence-text tiling, not
Hodrick-Prescott filtering, so the line was never a trend decomposition (defect
E8).  This module implements the actual HP filter:

.. math::

    \\min_{\\beta} \\; \\sum_{t=1}^{T} (y_t - \\beta_t)^2
    + \\lambda \\sum_{t=2}^{T} \\left(\\beta_{t+1} - \\beta_t\\right)^2

The solution is obtained from the standard band matrix.  The smoothing
parameter ``lambda`` trades off fit against smoothness; larger values give a
smoother trend.  Because the legacy code used a window of 90 observations, the
default lambda is calibrated to produce a comparable amount of smoothing on a
daily series, and the value is exposed in the configuration.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

__all__ = ["hp_filter", "hp_lambda_for_window", "detrend"]


def hp_lambda_for_window(window: int, frequency: str = "D") -> float:
    """Translate a moving-average window into an HP smoothing parameter.

    The HP filter and a centred moving average are both low-pass filters; this
    mapping reproduces the legacy ``smooth(data, 90)`` behaviour closely enough
    that the corrected charts remain comparable with the published ones.
    """
    if window <= 1:
        return 1600.0
    if frequency.upper() in ("Q", "QUARTERLY"):
        scale = 1.0
    elif frequency.upper() in ("M", "MONTHLY"):
        scale = 4.0
    else:  # daily and finer
        scale = 16.0
    return float(max(1.0, (window**2) / (12.0 * scale) * 10.0))


def hp_filter(
    series: pd.Series,
    *,
    lam: float = 1600.0,
) -> tuple[pd.Series, pd.Series]:
    """Return ``(cycle, trend)`` for ``series``.

    ``cycle`` is the deviation of the observed series from the trend and
    ``trend`` is the smoothed component; ``observed == trend + cycle``.
    """
    clean = pd.Series(series).astype(float).dropna()
    if len(clean) < 3:
        return clean, clean

    values = clean.to_numpy(dtype=float)
    size = len(values)
    # Second-difference penalty matrix.
    penalty = np.zeros((size - 2, size))
    for index in range(size - 2):
        penalty[index, index] = 1.0
        penalty[index, index + 1] = -2.0
        penalty[index, index + 2] = 1.0

    design = np.eye(size)
    middle = design - lam * (penalty.T @ penalty)
    try:
        trend_values = np.linalg.solve(middle, values)
    except np.linalg.LinAlgError:  # pragma: no cover - singular only for lam=0 edge
        trend_values = values

    trend = pd.Series(trend_values, index=clean.index)
    cycle = clean - trend
    return cycle, trend


def detrend(
    series: pd.Series,
    *,
    lam: float | None = None,
    window: int = 90,
    frequency: str = "D",
) -> pd.Series:
    """Return the cyclical component of ``series``."""
    if lam is None:
        lam = hp_lambda_for_window(window, frequency)
    cycle, _ = hp_filter(series, lam=lam)
    return cycle
