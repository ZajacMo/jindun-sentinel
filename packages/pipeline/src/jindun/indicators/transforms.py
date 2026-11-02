"""Indicator-level transforms.

These are the small, well-defined operations that turn raw market series into
the tertiary indicator panel: conditional volatility from a GARCH fit, simple
returns, first differences and cross-sectional de-meaning.
"""

from __future__ import annotations

from typing import Sequence

import numpy as np
import pandas as pd

__all__ = [
    "garch_volatility",
    "log_returns",
    "first_difference",
    "zscore",
    "ewma_volatility",
]


def garch_volatility(
    series: pd.Series,
    *,
    scale: float = 100.0,
    mean: str = "Zero",
    vol: str = "GARCH",
    dist: str = "normal",
    max_iter: int = 500,
) -> pd.Series:
    """Conditional volatility of ``series`` via a GARCH fit.

    The legacy pipeline multiplied by 100 before fitting so that the optimiser
    works on a human-scaled series; the scale is preserved here so that
    downstream numbers stay comparable with the published ones.

    Falls back to a rolling standard deviation when ``arch`` cannot fit the
    series (too few observations, constant values, or non-finite data) rather
    than propagating an exception into a daily run.
    """
    clean = pd.Series(series).astype(float).replace([np.inf, -np.inf], np.nan).dropna()
    if len(clean) < 30:
        return pd.Series(index=clean.index, dtype=float, name=series.name)

    try:
        from arch import arch_model

        model = arch_model(
            clean * scale,
            mean=mean,
            vol=vol,
            dist=dist,
            rescale=False,
        )
        fitted = model.fit(disp="off", maxiter=max_iter)
        volatility = fitted.conditional_volatility
    except Exception:
        window = max(5, min(30, len(clean) // 10))
        volatility = clean.rolling(window, min_periods=window).std()

    volatility = pd.Series(np.asarray(volatility, dtype=float), index=clean.index)
    volatility = volatility.replace([np.inf, -np.inf], np.nan)
    return volatility.dropna()


def ewma_volatility(series: pd.Series, *, halflife: int = 20, scale: float = 100.0) -> pd.Series:
    """Exponentially weighted moving-average volatility.

    Offered as a swappable alternative to GARCH so that a researcher can
    rebuild the index with a different volatility estimator without touching
    the rest of the pipeline.
    """
    clean = pd.Series(series).astype(float).replace([np.inf, -np.inf], np.nan).dropna()
    if len(clean) < 3:
        return pd.Series(index=clean.index, dtype=float, name=series.name)
    returns = clean.diff().dropna()
    variance = returns.ewm(halflife=halflife, min_periods=3).var()
    volatility = (np.sqrt(variance) * scale).reindex(clean.index)
    return volatility.dropna()


def log_returns(series: pd.Series) -> pd.Series:
    """Log returns of a strictly positive series."""
    clean = pd.Series(series).astype(float)
    clean = clean.replace([np.inf, -np.inf], np.nan).dropna()
    if (clean <= 0).any():
        clean = clean[clean > 0]
    if len(clean) < 2:
        return pd.Series(index=clean.index, dtype=float, name=series.name)
    return np.log(clean).diff().dropna()


def first_difference(series: pd.Series) -> pd.Series:
    """First difference of a series."""
    clean = pd.Series(series).astype(float).replace([np.inf, -np.inf], np.nan)
    return clean.diff().dropna()


def zscore(series: pd.Series, window: int | None = None) -> pd.Series:
    """Standardise a series, optionally over a trailing window."""
    clean = pd.Series(series).astype(float)
    if window:
        mean = clean.rolling(window, min_periods=max(3, window // 3)).mean()
        std = clean.rolling(window, min_periods=max(3, window // 3)).std()
    else:
        mean = clean.mean()
        std = pd.Series(clean.std(), index=clean.index)
    std = std.replace(0.0, np.nan)
    return ((clean - mean) / std).dropna()


def apply_transform(
    series: pd.Series,
    transform: str,
    *,
    params: dict[str, float] | None = None,
) -> pd.Series:
    """Apply a named transform, used by the configuration-driven pipeline."""
    params = params or {}
    if transform in ("level", "none", ""):
        return series
    if transform == "garch":
        return garch_volatility(series, scale=float(params.get("scale", 100.0)))
    if transform == "ewma":
        return ewma_volatility(
            series, halflife=int(params.get("halflife", 20)), scale=float(params.get("scale", 100.0))
        )
    if transform == "log_return":
        return log_returns(series)
    if transform == "diff":
        return first_difference(series)
    if transform == "zscore":
        return zscore(series, window=params.get("window"))
    raise ValueError(f"unknown transform: {transform!r}")


def align_frames(
    frames: Sequence[pd.DataFrame],
) -> pd.DataFrame:
    """Align a list of frames on their common index, keeping the union."""
    if not frames:
        return pd.DataFrame()
    combined = pd.concat(frames, axis=1, join="outer")
    return combined.sort_index()
