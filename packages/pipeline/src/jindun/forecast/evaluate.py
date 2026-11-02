"""Walk-forward evaluation of a forecasting engine.

The evaluation is the part that makes a forecast claim meaningful.  A model
is fitted on a window, forecasts the next block, the window is rolled forward
and the process repeats; every prediction is therefore made with information
that was available at the time.

The metrics are:

``mae`` / ``rmse``
    The error in the units of the series.
``mase``
    The mean absolute scaled error: the MAE divided by the mean absolute
    change of the training window.  It is the only metric here that can be
    compared across series with different levels and volatilities, and a
    value below one means the model beats a naive random walk.
``directional_accuracy``
    The share of steps in which the model and the series moved in the same
    direction.  A stress index is read by people who care about the
    direction more than about the level.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Mapping

import numpy as np
import pandas as pd

__all__ = [
    "ForecastMetrics",
    "mean_absolute_scaled_error",
    "backtest",
    "compare_engines",
    "forecast_series",
]


@dataclass(slots=True)
class ForecastMetrics:
    """Out-of-sample error of a forecasting engine."""

    engine: str
    mae: float = float("nan")
    rmse: float = float("nan")
    mase: float = float("nan")
    directional_accuracy: float = float("nan")
    steps: int = 0
    observations: int = 0
    note: str = ""
    detail: dict[str, float | str | int] = field(default_factory=dict)

    def to_payload(self) -> dict[str, object]:
        return {
            "engine": self.engine,
            "mae": None if np.isnan(self.mae) else round(self.mae, 8),
            "rmse": None if np.isnan(self.rmse) else round(self.rmse, 8),
            "mase": None if np.isnan(self.mase) else round(self.mase, 8),
            "directional_accuracy": None
            if np.isnan(self.directional_accuracy)
            else round(self.directional_accuracy, 8),
            "steps": self.steps,
            "observations": self.observations,
            "detail": dict(self.detail),
        }


def mean_absolute_scaled_error(
    actual: np.ndarray, predicted: np.ndarray, naive_scale: np.ndarray
) -> float:
    """MASE: the MAE of the model divided by the in-sample naive error."""
    denominator = float(np.mean(np.abs(naive_scale))) if len(naive_scale) else 0.0
    if denominator <= 0:
        return float("nan")
    return float(np.mean(np.abs(actual - predicted)) / denominator)


def backtest(
    series: pd.Series,
    forecast_fn: Callable[[pd.Series, int], np.ndarray],
    *,
    horizon: int = 10,
    window: int = 250,
    engine: str = "model",
    stride: int = 1,
    max_origins: int | None = None,
) -> ForecastMetrics:
    """Run a walk-forward backtest of ``forecast_fn``.

    ``forecast_fn`` is called as ``forecast_fn(training_window, horizon)`` and
    must return ``horizon`` predictions.

    ``stride`` and ``max_origins`` bound the cost of the evaluation.  A daily
    composite has thousands of observations, and refitting the model at every
    single origin costs tens of thousands of fits for a number that does not
    change.  The default stride is the forecast horizon, which produces
    non-overlapping forecast blocks, and the most recent origins are the ones
    that describe the behaviour of the model today; both are recorded in the
    metrics so the evaluation stays auditable.
    """
    clean = pd.Series(series).astype(float).dropna()
    values = clean.to_numpy(dtype=float)
    if len(values) < window + horizon + 2:
        return ForecastMetrics(engine=engine, note="not enough data to backtest")

    step = max(1, int(stride))
    origins = list(range(window, len(values) - horizon + 1, step))
    if max_origins is not None and max_origins > 0 and len(origins) > max_origins:
        origins = origins[-max_origins:]

    errors: list[float] = []
    squared: list[float] = []
    actuals: list[float] = []
    predictions: list[float] = []
    direction_hits = 0
    direction_total = 0
    steps = 0

    for end in origins:
        training = pd.Series(values[:end])
        try:
            predicted = np.asarray(forecast_fn(training, horizon), dtype=float)
        except Exception:
            continue
        if predicted.shape[0] != horizon or not np.all(np.isfinite(predicted)):
            continue
        actual = values[end : end + horizon]
        errors.extend((actual - predicted).tolist())
        squared.extend(((actual - predicted) ** 2).tolist())
        actuals.extend(actual.tolist())
        predictions.extend(predicted.tolist())
        steps += 1
        previous = values[end - 1]
        for index in range(horizon):
            actual_move = np.sign(actual[index] - previous)
            predicted_move = np.sign(predicted[index] - previous)
            if actual_move == 0 and predicted_move == 0:
                direction_total += 1
                direction_hits += 1
            elif actual_move == predicted_move:
                direction_total += 1
                direction_hits += 1
            previous = actual[index]

    if not errors:
        return ForecastMetrics(engine=engine, observations=len(values))

    error_array = np.asarray(errors, dtype=float)
    naive = np.diff(values[:window])
    return ForecastMetrics(
        engine=engine,
        mae=float(np.mean(np.abs(error_array))),
        rmse=float(np.sqrt(np.mean(np.asarray(squared, dtype=float)))),
        mase=mean_absolute_scaled_error(
            np.asarray(actuals, dtype=float),
            np.asarray(predictions, dtype=float),
            naive,
        ),
        directional_accuracy=(
            float(direction_hits / direction_total) if direction_total else float("nan")
        ),
        steps=steps,
        observations=len(values),
        detail={
            "window": window,
            "horizon": horizon,
            "stride": step,
            "origins": len(origins),
        },
    )


def compare_engines(
    series: pd.Series,
    engines: Mapping[str, Callable[[pd.Series, int], np.ndarray]],
    *,
    horizon: int = 10,
    window: int = 250,
) -> dict[str, ForecastMetrics]:
    """Backtest several engines on the same series."""
    results: dict[str, ForecastMetrics] = {}
    for name, engine in engines.items():
        results[name] = backtest(
            series, engine, horizon=horizon, window=window, engine=name
        )
    return results


def forecast_series(
    series: pd.Series,
    *,
    engine: str = "arima",
    horizon: int = 50,
    max_p: int = 3,
    max_d: int = 1,
    max_q: int = 2,
) -> dict[str, object]:
    """Forecast ``horizon`` steps ahead with the requested engine.

    The LSTM engine raises a clear error when the optional dependency is
    missing rather than silently falling back, because a silent fallback
    would publish numbers under the wrong name.
    """
    from .arima import forecast_arima
    from .lstm import forecast_lstm

    if engine == "arima":
        fit = forecast_arima(
            series, horizon=horizon, max_p=max_p, max_d=max_d, max_q=max_q
        )
        return {
            "engine": "arima",
            "order": list(fit.order),
            "dates": fit.dates,
            "values": [round(float(value), 8) for value in fit.forecast],
            "lower": [round(float(value), 8) for value in fit.lower],
            "upper": [round(float(value), 8) for value in fit.upper],
            "converged": fit.converged,
            "notes": [fit.note] if fit.note else [],
        }
    if engine == "lstm":
        fit = forecast_lstm(series, horizon=horizon)
        return {
            "engine": "lstm",
            "dates": fit.dates,
            "values": [round(float(value), 8) for value in fit.forecast],
            "lower": [],
            "upper": [],
            "converged": fit.converged,
            "notes": list(fit.notes),
        }
    raise ValueError(f"unknown forecasting engine: {engine!r}")
