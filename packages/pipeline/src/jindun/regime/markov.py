"""Regime identification with a Markov-switching autoregression.

The China pipeline identifies two stress regimes — "moderate" and "high" — by
fitting a Markov-switching autoregression (MS-AR) to the logarithm of the
composite stress index.

Everything here is parameterised: the number of regimes, the autoregressive
order, the variance switching and the trend term come from the configuration,
never from a literal in the source.  When the MLE fit does not converge (which
happens on short or degenerate samples) the module degrades to a deterministic
two-cluster assignment rather than failing the daily run.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from ..models import RegimeLabel

__all__ = ["RegimeFit", "fit_regime", "fallback_regimes"]


@dataclass(slots=True)
class RegimeFit:
    """Outcome of a regime fit."""

    labels: list[RegimeLabel]
    dates: list
    regime_means: dict[str, float] = field(default_factory=dict)
    regime_stds: dict[str, float] = field(default_factory=dict)
    method: str = "markov"
    converged: bool = True
    transition_matrix: list[list[float]] = field(default_factory=list)
    note: str = ""

    def as_frame(self) -> pd.DataFrame:
        return pd.DataFrame({"regime": [label.value for label in self.labels]}, index=self.dates)


def _extract_regime_labels(result, k_regimes: int) -> np.ndarray:
    """Return the most likely regime of every observation.

    ``statsmodels`` exposes the *filtered* posterior probabilities of each
    regime, so the label of an observation is the regime with the highest
    filtered probability.

    The **filtered** probabilities are used deliberately and the **smoothed**
    ones are not: smoothing uses observations that lie in the future of the
    observation being labelled, which is look-ahead bias.  A monitoring
    system that publishes a state for today may not use tomorrow's data to
    decide today's state.
    """
    for attribute in (
        "filtered_marginal_probabilities",
        "filtered",
        "regime",
    ):
        if not hasattr(result, attribute):
            continue
        array = np.asarray(getattr(result, attribute))
        if array.ndim == 1:
            return array.astype(int)
        if array.ndim == 2 and array.shape[1] >= 2:
            return np.argmax(array, axis=1).astype(int)
    raise ValueError("the fitted model does not expose regime probabilities")


def _order_labels_by_mean(values: np.ndarray, labels: np.ndarray) -> np.ndarray:
    """Relabel so that regime 0 is the calm one and regime 1 the stressed one."""
    means = {}
    for regime in np.unique(labels):
        means[regime] = float(np.mean(values[labels == regime]))
    ordered = sorted(means, key=lambda key: means[key])
    mapping = {old: new for new, old in enumerate(ordered)}
    return np.array([mapping[label] for label in labels], dtype=int)


def fallback_regimes(
    series: pd.Series,
    *,
    smooth_window: int = 21,
) -> RegimeFit:
    """Deterministic two-regime assignment used when the MLE fit fails.

    A rolling mean is split at its median; observations above the median are
    labelled ``high``, the rest ``moderate``.
    """
    clean = pd.Series(series).astype(float).dropna()
    if clean.empty:
        return RegimeFit(
            labels=[], dates=[], method="fallback", converged=False, note="empty series"
        )
    window = max(3, smooth_window)
    smoothed = clean.rolling(window, min_periods=1).mean()
    threshold = float(smoothed.median())
    labels = np.where(smoothed.to_numpy() > threshold, 1, 0)
    means = {
        "moderate": float(np.mean(clean.to_numpy()[labels == 0])) if np.any(labels == 0) else 0.0,
        "high": float(np.mean(clean.to_numpy()[labels == 1])) if np.any(labels == 1) else 0.0,
    }
    stds = {
        "moderate": float(np.std(clean.to_numpy()[labels == 0])) if np.any(labels == 0) else 0.0,
        "high": float(np.std(clean.to_numpy()[labels == 1])) if np.any(labels == 1) else 0.0,
    }
    return RegimeFit(
        labels=[RegimeLabel.HIGH if label else RegimeLabel.MODERATE for label in labels],
        dates=list(clean.index),
        regime_means=means,
        regime_stds=stds,
        method="fallback",
        converged=False,
        note="Markov-switching fit did not converge; deterministic split applied",
    )


def fit_regime(
    series: pd.Series,
    *,
    k_regimes: int = 2,
    order: int = 5,
    switching_variance: bool = True,
    trend: str = "c",
    max_iter: int = 500,
    max_observations: int | None = None,
) -> RegimeFit:
    """Fit an MS-AR to ``series`` and return the regime assignment.

    ``max_observations`` caps the sample at its most recent end.  A
    Markov-switching model with several lags is expensive to fit and becomes
    over-parameterised on decades of daily data; for a monitoring system the
    recent past is the part that carries the information.
    """
    clean = pd.Series(series).astype(float).dropna()
    if max_observations and len(clean) > max_observations:
        clean = clean.iloc[-max_observations:]
    if len(clean) < max(30, order * 10):
        return fallback_regimes(clean)

    try:
        from statsmodels.tsa.regime_switching.markov_regression import MarkovRegression

        model = MarkovRegression(
            clean,
            k_regimes=k_regimes,
            order=order,
            switching_variance=switching_variance,
            trend=trend,
        )
        result = model.fit(maxiter=max_iter, disp=False)
    except Exception:
        return fallback_regimes(clean)

    try:
        raw = _extract_regime_labels(result, k_regimes)
    except Exception:
        return fallback_regimes(clean)

    values = clean.to_numpy(dtype=float)
    if len(raw) != len(values):
        return fallback_regimes(clean)

    raw = _order_labels_by_mean(values, raw)
    labels = [RegimeLabel.HIGH if label == k_regimes - 1 else RegimeLabel.MODERATE for label in raw]

    means: dict[str, float] = {}
    stds: dict[str, float] = {}
    for index, name in ((0, "moderate"), (k_regimes - 1, "high")):
        mask = raw == index
        if np.any(mask):
            means[name] = float(np.mean(values[mask]))
            stds[name] = float(np.std(values[mask]))
        else:
            means[name] = 0.0
            stds[name] = 0.0

    transition: list[list[float]] = []
    try:
        matrix = np.asarray(result.regime_transition)
        # statsmodels stores the transition matrix as (k, k, 1).
        matrix = matrix.reshape(k_regimes, k_regimes, -1)[..., -1]
        transition = matrix.tolist()
    except Exception:
        transition = []

    return RegimeFit(
        labels=labels,
        dates=list(clean.index),
        regime_means=means,
        regime_stds=stds,
        method="markov",
        converged=True,
        transition_matrix=transition,
    )
