"""Tests for the regime identification layer."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from jindun.models import RegimeLabel
from jindun.regime.hp_filter import detrend, hp_filter, hp_lambda_for_window
from jindun.regime.markov import fallback_regimes, fit_regime
from jindun.regime.probability import (
    LEGACY_BANDWIDTH,
    LEGACY_MEANS,
    fit_probability_model,
    legacy_probability,
)


def test_hp_filter_decomposition_is_exact() -> None:
    index = pd.date_range("2020-01-01", periods=200, freq="B")
    values = np.linspace(0, 1, 200) + np.sin(np.arange(200) / 7.0) * 0.05
    series = pd.Series(values, index=index)

    cycle, trend = hp_filter(series, lam=1600.0)
    assert np.allclose((trend + cycle).to_numpy(), series.to_numpy(), atol=1e-8)


def test_hp_filter_removes_a_linear_trend() -> None:
    index = pd.date_range("2020-01-01", periods=300, freq="B")
    series = pd.Series(np.linspace(0, 10, 300), index=index)
    cycle, trend = hp_filter(series, lam=1600.0)
    assert float(cycle.abs().max()) < 0.1
    assert trend.iloc[-1] > trend.iloc[0]


def test_hp_lambda_scales_with_the_window() -> None:
    assert hp_lambda_for_window(90) > hp_lambda_for_window(30)
    assert hp_lambda_for_window(1) == pytest.approx(1600.0)


def test_detrend_uses_the_window_mapping() -> None:
    index = pd.date_range("2020-01-01", periods=200, freq="B")
    series = pd.Series(np.random.default_rng(7).normal(size=200), index=index)
    result = detrend(series, window=90)
    assert len(result) == len(series)


def test_fallback_regimes_split_the_sample() -> None:
    index = pd.date_range("2020-01-01", periods=120, freq="B")
    values = np.concatenate([np.zeros(60), np.ones(60) * 5.0])
    series = pd.Series(values, index=index)
    fit = fallback_regimes(series, smooth_window=5)
    assert fit.method == "fallback"
    assert not fit.converged
    assert fit.labels[0] is RegimeLabel.MODERATE
    assert fit.labels[-1] is RegimeLabel.HIGH


def test_short_samples_fall_back_instead_of_failing() -> None:
    series = pd.Series([1.0, 2.0, 3.0], index=pd.date_range("2020-01-01", periods=3))
    fit = fit_regime(series, order=5)
    assert fit.method == "fallback"
    assert len(fit.labels) == 3


def test_fitted_regimes_are_ordered_calm_first(composite_series: pd.Series) -> None:
    fit = fit_regime(composite_series, order=3, max_iter=50)
    assert len(fit.labels) == len(composite_series)
    if fit.converged:
        assert fit.regime_means["moderate"] <= fit.regime_means["high"]


def test_probability_model_sums_to_one(composite_series: pd.Series) -> None:
    fit = fallback_regimes(composite_series, smooth_window=21)
    model = fit_probability_model(np.log(composite_series), fit)
    calm, stressed = model.predict(np.log(composite_series))
    total = calm + stressed
    valid = total.notna()
    assert np.allclose(total[valid].to_numpy(), 1.0, atol=1e-8)


def test_legacy_probability_keeps_the_published_constants() -> None:
    model = legacy_probability(pd.Series([-0.9]))
    assert model.means == LEGACY_MEANS
    assert model.stds == (LEGACY_BANDWIDTH, LEGACY_BANDWIDTH)
    assert model.source == "legacy"
    assert not model.normalise
