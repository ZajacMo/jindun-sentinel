"""Tests for the index construction layer."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from jindun.index.composite import (
    deviation_from_trend,
    synthesise_composite,
    to_percentile,
)
from jindun.index.critic import critic_weights, resolve_weights
from jindun.index.normalise import cdf_rank, normalise_panel
from jindun.index.pca import pca_analysis, pca_legacy_selection
from jindun.models import Direction


def test_cdf_rank_is_bounded_and_monotone() -> None:
    series = pd.Series([3.0, 1.0, 2.0])
    ranks = cdf_rank(series)
    assert ranks.min() > 0.0
    assert ranks.max() <= 1.0
    assert ranks.loc[1] < ranks.loc[2] < ranks.loc[0]


def test_normalise_panel_respects_direction() -> None:
    panel = pd.DataFrame(
        {
            "up": [1.0, 2.0, 3.0, 4.0],
            "down": [1.0, 2.0, 3.0, 4.0],
            "both": [1.0, 2.0, 3.0, 4.0],
        }
    )
    result = normalise_panel(
        panel,
        {
            "up": Direction.SAME,
            "down": Direction.OPPOSITE,
            "both": Direction.BIDIRECTIONAL,
        },
    )
    assert result.loc[3, "up"] > result.loc[0, "up"]
    assert result.loc[3, "down"] < result.loc[0, "down"]
    # The bidirectional indicator is ranked on the absolute deviation from the
    # mean, so the two extreme observations receive the highest ranks.
    assert result.loc[3, "both"] > result.loc[1, "both"]
    assert result.loc[0, "both"] > result.loc[1, "both"]


def test_pca_uses_symmetric_eigendecomposition(indicator_panel: pd.DataFrame) -> None:
    result = pca_analysis(indicator_panel, variance_threshold=0.8)
    assert np.all(np.diff(result.eigenvalues) <= 1e-12)
    assert np.all(result.eigenvalues >= 0.0)
    assert result.cumulative_variance_ratio[-1] == pytest.approx(1.0, abs=1e-8)
    assert 1 <= result.n_components <= indicator_panel.shape[1]
    assert result.threshold >= 0.8


def test_pca_component_count_is_the_smallest_one_reaching_the_threshold(
    indicator_panel: pd.DataFrame,
) -> None:
    result = pca_analysis(indicator_panel, variance_threshold=0.8)
    below = result.cumulative_variance_ratio[result.n_components - 2]
    assert below < 0.8
    assert result.cumulative_variance_ratio[result.n_components - 1] >= 0.8


def test_legacy_selection_is_available_for_regression(indicator_panel: pd.DataFrame) -> None:
    corrected = pca_analysis(indicator_panel, variance_threshold=0.8)
    legacy = pca_analysis(indicator_panel, variance_threshold=0.8, legacy=True)
    assert legacy.n_components >= 1
    assert legacy.n_components <= indicator_panel.shape[1]
    assert corrected.n_components >= 1


def test_pca_legacy_selection_helper() -> None:
    eigenvalues = np.array([5.0, 3.0, 1.0, 1.0])
    assert pca_legacy_selection(eigenvalues, 4) >= 1


def test_critic_weights_sum_to_one(indicator_panel: pd.DataFrame) -> None:
    weights = critic_weights(indicator_panel)
    assert weights.sum() == pytest.approx(1.0)
    assert (weights >= 0).all()


def test_critic_gives_zero_to_a_constant_column() -> None:
    panel = pd.DataFrame({"a": [1.0, 2.0, 3.0, 4.0], "b": [2.0, 2.0, 2.0, 2.0]})
    weights = critic_weights(panel)
    assert weights["b"] == pytest.approx(0.0)
    assert weights["a"] == pytest.approx(1.0)


def test_resolve_weights_prefers_configured_values(indicator_panel: pd.DataFrame) -> None:
    weights = resolve_weights(indicator_panel, {"alpha": 0.6}, mode="configured")
    assert weights["alpha"] == pytest.approx(0.6)
    assert weights.sum() == pytest.approx(1.0)


def test_resolve_weights_equal_mode(indicator_panel: pd.DataFrame) -> None:
    weights = resolve_weights(indicator_panel, mode="equal")
    assert weights.sum() == pytest.approx(1.0)
    for value in weights:
        assert value == pytest.approx(0.25)


def test_composite_is_reproducible_and_bounded(market_indices: pd.DataFrame) -> None:
    weights = {"equity": 0.3, "bond": 0.3, "fx": 0.1, "money": 0.2, "derivative": 0.1}
    series, correlation = synthesise_composite(market_indices, weights)
    again, _ = synthesise_composite(market_indices, weights)
    pd.testing.assert_series_equal(series, again)
    assert (series >= 0).all()
    assert np.allclose(np.diag(correlation.to_numpy()), 1.0)


def test_composite_rejects_a_panel_without_weights(market_indices: pd.DataFrame) -> None:
    with pytest.raises(ValueError):
        synthesise_composite(market_indices, {"unknown": 1.0})


def test_percentile_lens_is_a_share(composite_series: pd.Series) -> None:
    percentile = to_percentile(composite_series)
    assert percentile.max() <= 1.0
    assert percentile.min() > 0.0
    assert percentile.max() == pytest.approx(1.0)
    # The percentile lens is a monotone relabelling of the composite.
    assert percentile.rank(method="first").equals(composite_series.rank(method="first"))


def test_deviation_from_trend_is_centred(composite_series: pd.Series) -> None:
    deviation = deviation_from_trend(composite_series)
    assert len(deviation) > 0
    assert abs(float(deviation.mean())) < 0.5 * float(composite_series.std())
