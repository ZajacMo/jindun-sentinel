"""Forecasting of the stress indices.

Two engines are provided:

``arima``
    The default.  An ARIMA model whose order is selected by the information
    criterion on the training window, forecast forward and validated with a
    walk-forward backtest.

``lstm``
    A recurrent model, available only when the optional ``torch`` extra is
    installed.  It is never used by default: on a daily-frequency stress
    index of a few thousand observations the ARIMA model is both more stable
    and easier to explain to a risk committee, and the backtest decides
    which engine to trust rather than a preference.

The selection between the engines is made on **out-of-sample** error, never on
in-sample fit, and the backtest window is configurable so that a researcher
can see how much of the performance depends on it.
"""

from __future__ import annotations

from .arima import ArimaFit, forecast_arima, select_arima_order
from .evaluate import (
    ForecastMetrics,
    backtest,
    compare_engines,
    forecast_series,
    mean_absolute_scaled_error,
)
from .lstm import lstm_available, forecast_lstm

__all__ = [
    "ArimaFit",
    "ForecastMetrics",
    "backtest",
    "compare_engines",
    "forecast_arima",
    "forecast_lstm",
    "forecast_series",
    "lstm_available",
    "mean_absolute_scaled_error",
    "select_arima_order",
]
