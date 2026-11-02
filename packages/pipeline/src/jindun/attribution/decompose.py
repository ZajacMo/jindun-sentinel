"""Attribution: why did the stress index move?

An index without an explanation is a number, not a warning.  This module
answers the question a risk officer actually asks — *what drove today's
change?* — in three layers:

1. **Which market moved the composite.**  The MBSED composite is a smooth
   function of the market indices, so the change is decomposed with the
   gradient of that function at the previous observation.  The gradient is
   exact rather than a heuristic: for a symmetric correlation matrix
   :math:`P` and market weights :math:`W`,

   .. math::

       \\frac{\\partial\\,\\mathrm{MBSED}}{\\partial s_j}
           = \\frac{\\mathrm{scale} \\cdot W_j \\cdot (P (W \\odot s))_j}
                  {\\mathrm{MBSED}}

   and the contributions of the markets sum to the change of the composite up
   to the curvature of the square root.

2. **Which indicator moved the market.**  A market index is a weighted sum of
   its normalised indicators, so the decomposition of the market move is
   exact.

3. **Which market's shock the contagion network blames.**  The spillover
   matrix says how much of each market's own forecast error variance comes
   from the others; that is the structural statement about which market is
   the current source of stress.

The three layers are reported separately and never mixed: the first two
explain a *change*, the third explains a *level*.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field

import numpy as np
import pandas as pd

__all__ = ["Attribution", "attribute_composite_move", "attribute_market_move"]


@dataclass(slots=True)
class Attribution:
    """The explanation of one observation's move."""

    as_of: str
    horizon_days: int = 1
    composite_change: float = 0.0
    composite_previous: float = 0.0
    composite_current: float = 0.0
    market_contributions: dict[str, float] = field(default_factory=dict)
    market_shares: dict[str, float] = field(default_factory=dict)
    indicator_contributions: dict[str, dict[str, float]] = field(default_factory=dict)
    indicator_shares: dict[str, dict[str, float]] = field(default_factory=dict)
    spillover_attribution: dict[str, float] = field(default_factory=dict)
    notes: list[str] = field(default_factory=list)

    def to_payload(self) -> dict[str, object]:
        return {
            "as_of": self.as_of,
            "horizon_days": self.horizon_days,
            "composite_change": round(self.composite_change, 8),
            "composite_previous": round(self.composite_previous, 8),
            "composite_current": round(self.composite_current, 8),
            "market_contributions": {
                key: round(float(value), 8) for key, value in self.market_contributions.items()
            },
            "market_shares": {
                key: round(float(value), 8) for key, value in self.market_shares.items()
            },
            "indicator_contributions": {
                market: {key: round(float(value), 8) for key, value in indicators.items()}
                for market, indicators in self.indicator_contributions.items()
            },
            "indicator_shares": {
                market: {key: round(float(value), 8) for key, value in indicators.items()}
                for market, indicators in self.indicator_shares.items()
            },
            "spillover_attribution": {
                key: round(float(value), 8)
                for key, value in self.spillover_attribution.items()
            },
            "notes": list(self.notes),
        }


def _shares(values: Mapping[str, float]) -> dict[str, float]:
    """Turn signed contributions into shares of the absolute total.

    A market can contribute negatively — a fall in stress lowers the index —
    so the shares are computed against the sum of the absolute contributions.
    The signs are preserved in the contribution itself.
    """
    total = sum(abs(value) for value in values.values())
    if total <= 0:
        return {key: 0.0 for key in values}
    return {key: value / total for key, value in values.items()}


def attribute_composite_move(
    market_indices: pd.DataFrame,
    composite: pd.Series,
    market_weights: Mapping[str, float],
    *,
    horizon_days: int = 1,
    scale: float = 2.0,
    normalised_indicators: Mapping[str, pd.DataFrame] | None = None,
    indicator_weights: Mapping[str, Mapping[str, float]] | None = None,
) -> Attribution:
    """Explain the change of the composite between two observations."""
    notes: list[str] = []
    index = market_indices.dropna(how="any")
    if len(index) < horizon_days + 1:
        return Attribution(as_of="", notes=["not enough observations to attribute a move"])

    current_date = index.index[-1]
    previous_date = index.index[-1 - horizon_days]
    current = index.loc[current_date]
    previous = index.loc[previous_date]

    markets = [column for column in index.columns if column in market_weights]
    if not markets:
        return Attribution(
            as_of=str(current_date),
            notes=["none of the market indices has a configured weight"],
        )

    weights = np.array([float(market_weights[market]) for market in markets])
    previous_vector = previous[markets].to_numpy(dtype=float)
    current_vector = current[markets].to_numpy(dtype=float)

    previous_composite = float(composite.get(previous_date, np.nan))
    current_composite = float(composite.get(current_date, np.nan))
    if not np.isfinite(previous_composite) or not np.isfinite(current_composite):
        return Attribution(
            as_of=str(current_date),
            notes=["the composite is not defined on both ends of the window"],
        )

    # ``to_numpy(copy=True)`` matters: under pandas 3 the conversion of a frame
    # may return a read-only view of its block, and the diagonal has to be
    # written into it.
    correlation = index[markets].corr().fillna(0.0).to_numpy(dtype=float, copy=True)
    np.fill_diagonal(correlation, 1.0)

    previous_scaled = previous_vector * weights
    current_scaled = current_vector * weights

    previous_quadratic = float(previous_scaled @ correlation @ previous_scaled)
    current_quadratic = float(current_scaled @ correlation @ current_scaled)
    previous_composite = scale * np.sqrt(max(previous_quadratic, 0.0))
    current_composite = scale * np.sqrt(max(current_quadratic, 0.0))

    # Gradient of the composite with respect to each market index, evaluated
    # at the midpoint of the window so that the linearisation is centred.
    midpoint = 0.5 * (previous_scaled + current_scaled)
    gradient_vector = scale * (correlation @ midpoint) / max(current_composite, 1e-12)
    gradient = gradient_vector * weights

    changes = current_vector - previous_vector
    contributions = {
        market: float(gradient[position] * changes[position])
        for position, market in enumerate(markets)
    }
    explained = sum(contributions.values())
    actual_change = current_composite - previous_composite
    if abs(actual_change) > 1e-12 and abs(explained) > 1e-12:
        notes.append(
            f"the first-order decomposition explains {explained / actual_change * 100:.1f} % "
            "of the change; the remainder is the curvature of the square root"
        )

    attribution = Attribution(
        as_of=current_date.date().isoformat() if hasattr(current_date, "date") else str(current_date),
        horizon_days=horizon_days,
        composite_change=actual_change,
        composite_previous=previous_composite,
        composite_current=current_composite,
        market_contributions=contributions,
        market_shares=_shares(contributions),
        notes=notes,
    )

    if normalised_indicators and indicator_weights:
        attribution.indicator_contributions, attribution.indicator_shares = (
            attribute_market_move(
                normalised_indicators,
                indicator_weights,
                horizon_days=horizon_days,
            )
        )

    return attribution


def attribute_market_move(
    normalised_indicators: Mapping[str, pd.DataFrame],
    indicator_weights: Mapping[str, Mapping[str, float]],
    *,
    horizon_days: int = 1,
) -> tuple[dict[str, dict[str, float]], dict[str, dict[str, float]]]:
    """Explain the move of each market index by its indicators.

    ``normalised_indicators`` maps a market code to a frame of normalised
    indicator series; ``indicator_weights`` maps a market code to the weight
    of each indicator.
    """
    contributions: dict[str, dict[str, float]] = {}
    shares: dict[str, dict[str, float]] = {}

    for market, panel in normalised_indicators.items():
        weights = indicator_weights.get(market, {})
        if not weights or panel.empty:
            continue
        columns = [column for column in panel.columns if column in weights]
        if not columns:
            continue
        clean = panel[columns].dropna(how="any")
        if len(clean) < horizon_days + 1:
            continue
        previous = clean.iloc[-1 - horizon_days]
        current = clean.iloc[-1]
        market_change = 0.0
        per_indicator: dict[str, float] = {}
        for column in columns:
            weight = float(weights[column])
            delta = float(current[column] - previous[column])
            contribution = weight * delta
            per_indicator[column] = contribution
            market_change += contribution
        contributions[market] = per_indicator
        shares[market] = _shares(per_indicator)

    return contributions, shares
