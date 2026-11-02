"""Risk probability model.

For every observation the pipeline reports how much probability mass the
calm regime and the stressed regime each carry.  The legacy implementation
evaluated two normal densities with *hard-coded* means (-0.9017 and -0.6418)
and a fixed bandwidth of 0.2 (defect E2).

The corrected implementation estimates the two regime locations and dispersions
from the fitted Markov model and evaluates the densities at those estimates.
The legacy constants remain available through :func:`legacy_probability` so
that the regression suite can report exactly how much the change moved the
published probabilities.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
from scipy.stats import norm

from .markov import RegimeFit

__all__ = ["ProbabilityModel", "fit_probability_model", "legacy_probability"]

LEGACY_MEANS = (-0.9017, -0.6418)
LEGACY_BANDWIDTH = 0.2


@dataclass(slots=True)
class ProbabilityModel:
    """A two-component normal mixture over the log composite."""

    means: tuple[float, float]
    stds: tuple[float, float]
    bandwidth: float = 0.2
    normalise: bool = True
    source: str = "fitted"

    def predict(self, values: pd.Series) -> tuple[pd.Series, pd.Series]:
        """Return ``(probability_moderate, probability_high)`` for ``values``."""
        clean = pd.Series(values).astype(float).dropna()
        if clean.empty:
            empty = pd.Series(dtype=float, index=values.index)
            return empty, empty.copy()

        calm = norm.pdf((clean.to_numpy() - self.means[0]) / self.stds[0])
        stressed = norm.pdf((clean.to_numpy() - self.means[1]) / self.stds[1])

        if self.normalise:
            total = calm + stressed
            total = np.where(total <= 0, np.nan, total)
            calm = calm / total
            stressed = stressed / total

        return (
            pd.Series(calm, index=clean.index).reindex(values.index),
            pd.Series(stressed, index=clean.index).reindex(values.index),
        )


def fit_probability_model(
    log_composite: pd.Series,
    regime_fit: RegimeFit,
    *,
    bandwidth: float = 0.2,
    normalise: bool = True,
) -> ProbabilityModel:
    """Build the probability model from a fitted regime."""
    means = (
        float(regime_fit.regime_means.get("moderate", 0.0)),
        float(regime_fit.regime_means.get("high", 0.0)),
    )
    stds = (
        max(float(regime_fit.regime_stds.get("moderate", 0.0)), 1e-6),
        max(float(regime_fit.regime_stds.get("high", 0.0)), 1e-6),
    )
    return ProbabilityModel(
        means=means,
        stds=stds,
        bandwidth=bandwidth,
        normalise=normalise,
        source="fitted",
    )


def legacy_probability(log_composite: pd.Series, *, bandwidth: float = LEGACY_BANDWIDTH) -> ProbabilityModel:
    """Reproduce the legacy hard-coded probability model."""
    return ProbabilityModel(
        means=LEGACY_MEANS,
        stds=(bandwidth, bandwidth),
        bandwidth=bandwidth,
        normalise=False,
        source="legacy",
    )
