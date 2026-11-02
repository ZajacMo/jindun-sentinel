"""Normalisation of tertiary indicators onto a common [0, 1] scale.

The project inherits the "cumulative distribution ranking" normalisation from
the original research: every indicator is mapped onto its own empirical
cumulative distribution, optionally inverted for indicators that move against
risk, and for two-sided indicators mapped onto the rank of the absolute
deviation from its mean.

Two properties matter and are preserved here:

* the result is bounded in [0, 1], so a unit change in one indicator cannot
  dominate the composite;
* the result is a *within-history percentile*, which is what makes countries
  comparable to each other (see the comparability note in the methodology).
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from ..models import Direction

__all__ = ["normalise_panel", "cdf_rank"]


def cdf_rank(values: pd.Series, *, ascending: bool = True) -> pd.Series:
    """Rank ``values`` onto an empirical cumulative distribution in [0, 1].

    Ties are broken by order of appearance (``method="first"``) to match the
    original implementation exactly.
    """
    clean = pd.Series(values).astype(float)
    ranks = clean.rank(method="first", ascending=ascending) / clean.count()
    return ranks


def normalise_panel(
    panel: pd.DataFrame,
    directions: dict[str, Direction],
) -> pd.DataFrame:
    """Normalise every column of ``panel`` according to its direction.

    Parameters
    ----------
    panel:
        Wide frame whose columns are indicator codes.
    directions:
        Mapping of indicator code to :class:`~jindun.models.Direction`.
    """
    normalised = pd.DataFrame(index=panel.index)
    for column in panel.columns:
        series = panel[column]
        direction = directions.get(column, Direction.SAME)
        if direction is Direction.SAME:
            normalised[column] = cdf_rank(series, ascending=True)
        elif direction is Direction.OPPOSITE:
            normalised[column] = cdf_rank(series, ascending=False)
        elif direction is Direction.BIDIRECTIONAL:
            deviation = (series - np.nanmean(series.values)) .abs()
            normalised[column] = cdf_rank(deviation, ascending=True)
        else:  # pragma: no cover - Direction is exhaustive
            raise ValueError(f"unsupported direction: {direction!r}")
    return normalised
