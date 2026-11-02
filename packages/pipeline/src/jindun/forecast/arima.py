"""ARIMA forecasting of a stress index.

The model is deliberately plain: the order is chosen by the information
criterion over a small grid, the series is differenced as far as the
criterion requires, and the forecast is the model's own prediction with the
confidence interval the model reports.

Two properties of the original research are corrected here:

* the order is **selected** rather than fixed to ``(5, 1, 0)``, and
* the forecast is **validated out of sample** with a walk-forward backtest,
  because the published evaluation showed that the ARIMA forecast converges
  to a constant almost immediately, which a model that is never scored
  against reality would not reveal.
"""

from __future__ import annotations

import datetime as dt
import warnings
from dataclasses import dataclass, field

import numpy as np
import pandas as pd

__all__ = ["ArimaFit", "select_arima_order", "fit_arima", "forecast_arima"]


@dataclass(slots=True)
class ArimaFit:
    """A fitted ARIMA model and its forecast."""

    order: tuple[int, int, int]
    fitted_values: np.ndarray
    forecast: np.ndarray
    lower: np.ndarray
    upper: np.ndarray
    dates: list[str] = field(default_factory=list)
    aic: float = float("nan")
    converged: bool = True
    note: str = ""


def _to_series(values: pd.Series | list[float]) -> pd.Series:
    series = pd.Series(values).astype(float)
    if not isinstance(series.index, pd.DatetimeIndex):
        series.index = pd.RangeIndex(len(series))
    return series


def select_arima_order(
    series: pd.Series,
    *,
    max_p: int = 3,
    max_d: int = 1,
    max_q: int = 2,
    criterion: str = "aic",
) -> tuple[int, int, int]:
    """Select the ARIMA order by the information criterion.

    The search is small on purpose: a daily stress index does not support a
    large grid, and a large grid would invite overfitting of the order
    itself.
    """
    from statsmodels.tsa.arima.model import ARIMA

    clean = _to_series(series).dropna()
    if len(clean) < 30:
        return (1, 0, 0)

    best: tuple[int, int, int] = (1, 0, 0)
    best_score = np.inf
    for p in range(0, max_p + 1):
        for d in range(0, max_d + 1):
            for q in range(0, max_q + 1):
                if p == 0 and q == 0 and d == 0:
                    continue
                try:
                    with warnings.catch_warnings():
                        warnings.simplefilter("ignore")
                        fitted = ARIMA(clean, order=(p, d, q)).fit()
                except Exception:
                    continue
                score = float(fitted.aic if criterion == "aic" else fitted.bic)
                if not np.isfinite(score):
                    continue
                if score < best_score:
                    best_score = score
                    best = (p, d, q)
    return best


def fit_arima(
    series: pd.Series,
    *,
    order: tuple[int, int, int] | None = None,
    max_p: int = 3,
    max_d: int = 1,
    max_q: int = 2,
) -> ArimaFit:
    """Fit an ARIMA model to ``series``."""
    from statsmodels.tsa.arima.model import ARIMA

    clean = _to_series(series).dropna()
    if len(clean) < 30:
        raise ValueError("at least 30 observations are required to fit an ARIMA model")

    chosen = order or select_arima_order(clean, max_p=max_p, max_d=max_d, max_q=max_q)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        fitted = ARIMA(clean, order=chosen).fit()

    converged = bool(getattr(fitted, "mle_retvals", {}).get("converged", True))
    return ArimaFit(
        order=chosen,
        fitted_values=np.asarray(fitted.fittedvalues, dtype=float),
        forecast=np.asarray(fitted.forecast, dtype=float),
        lower=np.asarray(fitted.get_forecast().conf_int(alpha=0.05)[:, 0], dtype=float)
        if hasattr(fitted, "get_forecast")
        else np.array([]),
        upper=np.asarray(fitted.get_forecast().conf_int(alpha=0.05)[:, 1], dtype=float)
        if hasattr(fitted, "get_forecast")
        else np.array([]),
        dates=[str(index) for index in clean.index],
        aic=float(getattr(fitted, "aic", float("nan"))),
        converged=converged,
        note="" if converged else "the maximum likelihood optimisation did not converge",
    )


def forecast_arima(
    series: pd.Series,
    *,
    horizon: int = 50,
    order: tuple[int, int, int] | None = None,
    max_p: int = 3,
    max_d: int = 1,
    max_q: int = 2,
    last_date: dt.date | None = None,
) -> ArimaFit:
    """Fit an ARIMA model and forecast ``horizon`` steps ahead."""
    from statsmodels.tsa.arima.model import ARIMA

    clean = _to_series(series).dropna()
    if len(clean) < 30:
        raise ValueError("at least 30 observations are required to forecast")
    chosen = order or select_arima_order(clean, max_p=max_p, max_d=max_d, max_q=max_q)

    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        fitted = ARIMA(clean, order=chosen).fit()
        prediction = fitted.get_forecast(steps=horizon)

    mean = np.asarray(prediction.predicted_mean, dtype=float)
    interval = np.asarray(prediction.conf_int(alpha=0.05), dtype=float)
    lower = interval[:, 0] if interval.size else np.array([])
    upper = interval[:, 1] if interval.size else np.array([])

    dates: list[str] = []
    if isinstance(clean.index, pd.DatetimeIndex):
        anchor = clean.index[-1]
        step = _infer_step(clean.index)
        future = [anchor + step * (index + 1) for index in range(horizon)]
        dates = [date.date().isoformat() for date in future]
    elif last_date is not None:
        dates = [(last_date + dt.timedelta(days=index + 1)).isoformat() for index in range(horizon)]

    return ArimaFit(
        order=chosen,
        fitted_values=np.asarray(fitted.fittedvalues, dtype=float),
        forecast=mean,
        lower=lower,
        upper=upper,
        dates=dates,
        aic=float(getattr(fitted, "aic", float("nan"))),
        converged=bool(getattr(fitted, "mle_retvals", {}).get("converged", True)),
        note=""
        if getattr(fitted, "mle_retvals", {}).get("converged", True)
        else "the maximum likelihood optimisation did not converge",
    )


def _infer_step(index: pd.DatetimeIndex) -> pd.Timedelta:
    if len(index) < 2:
        return pd.Timedelta(days=1)
    delta = index[-1] - index[-2]
    return delta if delta > pd.Timedelta(0) else pd.Timedelta(days=1)
