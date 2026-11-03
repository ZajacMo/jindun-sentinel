"""The global financial cycle factor and the country-panel cross-check.

Two different objects live in this module and they must not be confused:

**The global financial cycle factor (layer L3).**  A single common driver
estimated from global credit and currency conditions published by the BIS:
global cross-border credit growth in total, in dollars and in euros, the
credit-to-GDP gap of every monitored economy, and the year-on-year change of
the broad nominal effective exchange rate of the United States.  It is the
first principal component of the standardised input block.  This is the
factor a *global* financial cycle is made of, in the sense of Bruno & Shin
(2014) and Miranda-Agrippino & Rey (2020).

**The country-panel factor (layer L1).**  The first principal component of
the aligned country composites — the aggregate of the monitored stress
indices.  It is the same construction the country layer uses for its
sub-market indices, so the global layer stays consistent with the country
layer by design.

The first implementation published the second object under the name "global
cycle".  The panel factor is still computed — it is the natural cross-check
on the first — but it is reported as the cross-check, and the factor itself
is the one the BIS inputs estimate.

Both factors are reported with their loadings and their explained variance,
because a factor that explains a tenth of the variance is a different
statement from a factor that explains half of it, and the difference matters
for how the global cycle is used as a common driver.

**What a high factor means.**  The factor is a *conditions* factor, not a
stress index.  Its sign is oriented so that a higher value means faster
global credit expansion, a larger credit gap and a stronger dollar — the
configuration that historically precedes global stress — and not that stress
is already present.  A reader who treats a rising factor as a rising stress
index will read it backwards.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any

import numpy as np
import pandas as pd

from .bis_cycle import CycleInputs

__all__ = [
    "CycleFactor",
    "GlobalCycle",
    "build_global_cycle",
    "extract_cycle_factor",
]


@dataclass(slots=True)
class CycleFactor:
    """The extracted country-panel factor and its diagnostics."""

    dates: list[str] = field(default_factory=list)
    factor: list[float] = field(default_factory=list)
    loadings: dict[str, float] = field(default_factory=dict)
    explained_variance_ratio: list[float] = field(default_factory=list)
    cumulative_variance_ratio: list[float] = field(default_factory=list)
    observations: int = 0
    notes: list[str] = field(default_factory=list)

    def to_payload(self) -> dict[str, object]:
        return {
            "dates": list(self.dates),
            "factor": [round(float(value), 8) for value in self.factor],
            "loadings": {key: round(float(value), 8) for key, value in self.loadings.items()},
            "explained_variance_ratio": [
                round(float(value), 8) for value in self.explained_variance_ratio
            ],
            "cumulative_variance_ratio": [
                round(float(value), 8) for value in self.cumulative_variance_ratio
            ],
            "observations": self.observations,
            "notes": list(self.notes),
        }


@dataclass(slots=True)
class GlobalCycle:
    """The global financial cycle factor and its diagnostics."""

    dates: list[str] = field(default_factory=list)
    factor: list[float] = field(default_factory=list)
    loadings: dict[str, float] = field(default_factory=dict)
    explained_variance_ratio: list[float] = field(default_factory=list)
    cumulative_variance_ratio: list[float] = field(default_factory=list)
    observations: int = 0
    frequency: str = "Q"
    orientation: str = ""
    factor_standard_deviation: float = 0.0
    inputs: list[dict[str, Any]] = field(default_factory=list)
    cross_check: dict[str, Any] = field(default_factory=dict)
    notes: list[str] = field(default_factory=list)

    def to_payload(self) -> dict[str, object]:
        return {
            "dates": list(self.dates),
            "factor": [round(float(value), 8) for value in self.factor],
            "loadings": {key: round(float(value), 8) for key, value in self.loadings.items()},
            "explained_variance_ratio": [
                round(float(value), 8) for value in self.explained_variance_ratio
            ],
            "cumulative_variance_ratio": [
                round(float(value), 8) for value in self.cumulative_variance_ratio
            ],
            "observations": self.observations,
            "frequency": self.frequency,
            "orientation": self.orientation,
            "factor_standard_deviation": round(float(self.factor_standard_deviation), 8),
            "inputs": [dict(entry) for entry in self.inputs],
            "cross_check": dict(self.cross_check),
            "notes": list(self.notes),
        }


def extract_cycle_factor(
    composites: Mapping[str, pd.Series],
    *,
    standardize: bool = True,
) -> CycleFactor:
    """Extract the country-panel factor from the country composites.

    The first principal component of the aligned panel is the factor.  The
    sign of the component is arbitrary, so it is oriented so that it
    correlates positively with the mean of the country composites: without
    that, two runs of the same data could report opposite signs and a reader
    would have to guess which direction is "more stress".
    """
    if not composites:
        return CycleFactor(notes=["no country composites were supplied"])

    frame = pd.DataFrame(composites).sort_index().dropna(how="any")
    if frame.shape[1] < 2:
        return CycleFactor(notes=["at least two countries with a common calendar are required"])

    panel = frame
    if standardize:
        panel = (frame - frame.mean()) / frame.std(ddof=0).replace(0.0, np.nan)
    panel = panel.dropna(how="any")
    if panel.empty:
        return CycleFactor(notes=["the country composites share no usable dates"])

    values, vectors = np.linalg.eigh(panel.cov().to_numpy(dtype=float))
    order = np.argsort(values)[::-1]
    values = np.clip(values[order], 0.0, None)
    vectors = vectors[:, order]
    total = float(values.sum())
    ratios = values / total if total > 0 else np.zeros_like(values)
    cumulative = np.cumsum(ratios)

    factor = panel.to_numpy(dtype=float) @ vectors[:, 0]
    loadings = dict(zip(panel.columns, vectors[:, 0].tolist(), strict=True))
    if float(np.corrcoef(factor, panel.mean(axis=1).to_numpy())[0, 1]) < 0:
        factor = -factor
        loadings = {key: -value for key, value in loadings.items()}

    notes: list[str] = []
    if ratios[0] < 0.30:
        notes.append(
            f"the first principal component explains only "
            f"{ratios[0] * 100:.1f} % of the common variance; the country stress "
            "indices are not dominated by a single global driver"
        )

    return CycleFactor(
        dates=[date.isoformat() for date in panel.index],
        factor=[float(value) for value in factor],
        loadings=loadings,
        explained_variance_ratio=[float(value) for value in ratios],
        cumulative_variance_ratio=[float(value) for value in cumulative],
        observations=int(len(panel)),
        notes=notes,
    )


def _panel_factor_series(panel: CycleFactor) -> pd.Series:
    """Return the country-panel factor as a dated series."""
    if not panel.dates:
        return pd.Series(dtype=float)
    return pd.Series(
        [float(value) for value in panel.factor],
        index=pd.DatetimeIndex(pd.to_datetime(panel.dates)),
        name="panel_factor",
    )


def _orientation_anchor(panel: pd.DataFrame) -> tuple[pd.Series | None, str]:
    """Return the series the sign of the factor is oriented on.

    The credit-to-GDP gap is preferred: it is the input whose level carries
    the stress reading, and it is the part of the block the first component
    tracks most closely.  When no credit gap is in the block the mean of all
    inputs is used instead.
    """
    gaps = [name for name in panel.columns if name.startswith("credit_gap_")]
    if gaps:
        return panel[gaps].mean(axis=1), "the mean of the standardised credit gaps"
    return panel.mean(axis=1), "the mean of the standardised inputs"


def _describe_loadings(loadings: Mapping[str, float]) -> str:
    """Describe what a higher factor means, from the loadings themselves.

    The wording is derived from the estimated loadings rather than written by
    hand, so it cannot drift away from what the factor actually is.
    """
    gaps = {name: value for name, value in loadings.items() if name.startswith("credit_gap_")}
    growth = {name: value for name, value in loadings.items() if name.endswith("_credit_yoy")}
    parts: list[str] = []
    if gaps:
        direction = "a wider" if sum(gaps.values()) > 0 else "a narrower"
        parts.append(f"{direction} credit-to-GDP gap")
    if growth:
        direction = "slower" if sum(growth.values()) < 0 else "faster"
        parts.append(f"{direction} global credit growth")
    if not parts:
        return "the sign follows the first principal component"
    return "a higher factor means " + " and ".join(parts)


def build_global_cycle(
    inputs: CycleInputs,
    composites: Mapping[str, pd.Series],
    *,
    standardize: bool = True,
) -> GlobalCycle:
    """Estimate the global financial cycle factor and cross-check it.

    The factor is the first principal component of the standardised BIS input
    block.  The cross-check is the country-panel factor: the quarterly factor
    is carried forward onto the daily calendar of the panel and the two are
    correlated over the overlap.
    """
    notes: list[str] = list(inputs.notes)
    frame = inputs.frame
    if frame.empty or frame.shape[1] < 2:
        notes.append("the global cycle factor could not be estimated")
        return GlobalCycle(inputs=list(inputs.metadata), notes=notes)

    panel = frame
    if standardize:
        panel = (frame - frame.mean()) / frame.std(ddof=0).replace(0.0, np.nan)
    panel = panel.dropna(how="any")
    if panel.empty:
        notes.append("the BIS input block has no complete quarter")
        return GlobalCycle(inputs=list(inputs.metadata), notes=notes)

    values, vectors = np.linalg.eigh(panel.cov().to_numpy(dtype=float))
    order = np.argsort(values)[::-1]
    values = np.clip(values[order], 0.0, None)
    vectors = vectors[:, order]
    total = float(values.sum())
    ratios = values / total if total > 0 else np.zeros_like(values)
    cumulative = np.cumsum(ratios)

    factor = panel.to_numpy(dtype=float) @ vectors[:, 0]
    loadings = dict(zip(panel.columns, vectors[:, 0].tolist(), strict=True))

    # The sign of a principal component is arbitrary.  The factor is oriented
    # on the credit gap: the mean of the standardised credit-to-GDP gaps is
    # the anchor that both correlates strongly with the first component and
    # says something a reader can act on — a higher factor means credit is
    # further above its own trend.
    anchor, anchor_name = _orientation_anchor(panel)
    orientation = ""
    if anchor is not None:
        correlation = float(np.corrcoef(factor, anchor.to_numpy())[0, 1])
        if correlation < 0:
            factor = -factor
            loadings = {key: -value for key, value in loadings.items()}
            correlation = -correlation
        orientation = (
            f"the sign is oriented on {anchor_name}, which correlates "
            f"{correlation:.2f} with the factor: {_describe_loadings(loadings)}"
        )

    if ratios[0] < 0.30:
        notes.append(
            f"the first principal component explains only {ratios[0] * 100:.1f} % of the "
            "variance of the BIS input block; the inputs do not move as one driver"
        )
    else:
        notes.append(
            f"the first principal component explains {ratios[0] * 100:.1f} % of the "
            "variance of the BIS input block"
        )

    weak = sorted(
        (name for name, value in loadings.items() if abs(value) < 0.10),
        key=lambda name: abs(loadings[name]),
    )
    if weak:
        notes.append(
            "these inputs are essentially orthogonal to the first component and "
            f"carry it only weakly: {', '.join(weak)}"
        )

    cycle = GlobalCycle(
        dates=[date.date().isoformat() for date in panel.index],
        factor=[float(value) for value in factor],
        loadings=loadings,
        explained_variance_ratio=[float(value) for value in ratios],
        cumulative_variance_ratio=[float(value) for value in cumulative],
        observations=int(len(panel)),
        frequency="Q",
        orientation=orientation,
        factor_standard_deviation=float(np.std(factor, ddof=0)),
        inputs=list(inputs.metadata),
        notes=notes,
    )
    cycle.cross_check = _cross_check(cycle, composites, notes)
    return cycle


def _cross_check(
    cycle: GlobalCycle,
    composites: Mapping[str, pd.Series],
    notes: list[str],
) -> dict[str, Any]:
    """Correlate the cycle factor with the country-panel factor.

    The BIS factor is quarterly and the panel factor is daily, so the
    quarterly factor is carried forward onto the daily calendar of the panel.
    It does not move between publications, and the artefact says so.
    """
    panel = extract_cycle_factor(composites)
    if not panel.dates or not cycle.dates:
        return {
            "method": "country panel first principal component",
            "available": False,
            "reason": "the country panel or the BIS factor is missing",
        }

    panel_series = _panel_factor_series(panel)
    cycle_series = pd.Series(
        [float(value) for value in cycle.factor],
        index=pd.DatetimeIndex(pd.to_datetime(cycle.dates)),
        name="cycle_factor",
    )
    carried = cycle_series.reindex(panel_series.index.union(cycle_series.index)).ffill()
    carried = carried.reindex(panel_series.index).dropna()
    joined = pd.concat([panel_series.rename("panel"), carried.rename("cycle")], axis=1).dropna()
    if len(joined) < 10:
        return {
            "method": "country panel first principal component",
            "available": False,
            "reason": f"only {len(joined)} overlapping observations",
            "overlap": int(len(joined)),
        }

    correlation = float(np.corrcoef(joined["cycle"], joined["panel"])[0, 1])
    return {
        "method": "country panel first principal component",
        "available": True,
        "correlation": round(correlation, 6),
        "observations": int(len(joined)),
        "panel_factor": panel.to_payload(),
        "notes": [
            "the BIS factor is quarterly and is carried forward onto the daily "
            "calendar of the country panel; it does not move between publications",
            *panel.notes,
        ],
    }
