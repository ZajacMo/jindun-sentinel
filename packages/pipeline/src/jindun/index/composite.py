"""Synthesis of the market indices into the systemic stress composite.

The composite follows the specification of the original research: with market
weight vector ``W``, market stress vector ``s`` and the correlation matrix
``P`` of the market indices, the composite (MBSED) is

.. math::  \\mathrm{MBSED}_t = \\sqrt{(W \\odot s_t)\\, P\\,(W \\odot s_t)^\\top} \\times 2

Two comparability lenses are produced alongside it, because a single number
cannot honestly describe "how stressed is this market" across jurisdictions:

``percentile``
    The composite expressed as a within-country percentile.  This is the
    default lens and the one used for cross-country aggregation: it is robust
    to differences in the level and the volatility of the underlying
    indicators in each jurisdiction.
``deviation``
    The distance between the current composite and the country's own
    long-run trend, expressed in the composite's own units.  This lens tells
    you *how unusual* the current reading is in absolute terms.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

__all__ = ["MarketIndexPanel", "synthesise_composite", "to_percentile", "deviation_from_trend"]


class MarketIndexPanel:
    """Container for the per-market stress indices of one country."""

    def __init__(self, frame: pd.DataFrame) -> None:
        self.frame = frame

    @property
    def markets(self) -> list[str]:
        return list(self.frame.columns)

    def correlation(self) -> pd.DataFrame:
        return self.frame.corr()


def synthesise_composite(
    market_indices: pd.DataFrame,
    weights: dict[str, float],
    *,
    scale: float = 2.0,
) -> tuple[pd.Series, pd.DataFrame]:
    """Compute the MBSED composite from the market index panel.

    Returns the composite series and the correlation matrix that was used.
    """
    if market_indices.empty:
        raise ValueError("cannot synthesise a composite from an empty panel")

    markets = [market for market in market_indices.columns if market in weights]
    if not markets:
        raise ValueError("no market in the panel has a configured weight")

    panel = market_indices[markets].dropna(how="any")
    if panel.empty:
        raise ValueError("market indices have no common observations")

    correlation = panel.corr().fillna(0.0)
    # Guard against a degenerate correlation matrix (identical series).
    # ``DataFrame.values`` is read-only under pandas 3, so copy before writing.
    correlation_values = np.array(correlation.to_numpy(dtype=float), copy=True)
    np.fill_diagonal(correlation_values, 1.0)
    correlation = pd.DataFrame(
        correlation_values, index=correlation.index, columns=correlation.columns
    )

    weight_vector = np.array([float(weights[market]) for market in markets])
    values = panel.to_numpy(dtype=float)
    scaled = values * weight_vector
    quadratic = np.einsum("ij,jk,ik->i", scaled, correlation.to_numpy(), scaled)
    composite = np.sqrt(np.clip(quadratic, 0.0, None)) * scale

    series = pd.Series(composite, index=panel.index, name="composite")
    return series, correlation


def to_percentile(series: pd.Series) -> pd.Series:
    """Map a series onto its own empirical cumulative distribution."""
    clean = pd.Series(series).astype(float).dropna()
    if clean.empty:
        return pd.Series(dtype=float, index=series.index)
    ranks = clean.rank(method="first") / clean.count()
    return ranks.reindex(series.index)


def deviation_from_trend(series: pd.Series, trend: pd.Series | None = None) -> pd.Series:
    """Distance from the long-run trend of ``series``.

    When no explicit trend is supplied the centred moving average is used.
    """
    clean = pd.Series(series).astype(float)
    if trend is None:
        window = max(5, min(250, len(clean) // 10))
        trend = clean.rolling(window, min_periods=max(3, window // 3)).mean()
    return (clean - trend).dropna()
