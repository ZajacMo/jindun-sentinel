"""The global cycle factor.

The global cycle is the component of the country stress indices that moves
together.  It is estimated as the first principal component of the aligned
country composites, which is the same construction the country layer uses for
its sub-market indices — the global layer is therefore consistent with the
country layer by design.

The factor is reported with its loadings and its explained variance, because a
factor that explains a tenth of the variance is a different statement from a
factor that explains half of it, and the difference matters for how the
global cycle is used as a common driver.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

__all__ = ["CycleFactor", "extract_cycle_factor"]


@dataclass(slots=True)
class CycleFactor:
    """The extracted global cycle and its diagnostics."""

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


def extract_cycle_factor(
    composites: dict[str, pd.Series],
    *,
    standardize: bool = True,
) -> CycleFactor:
    """Extract the global cycle factor from the country composites.

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
        return CycleFactor(
            notes=["at least two countries with a common calendar are required"]
        )

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
