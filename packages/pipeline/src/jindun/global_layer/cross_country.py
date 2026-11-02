"""Cross-country contagion.

The cross-country network is the same generalised variance decomposition that
the country layer uses across its markets, applied one level up: the nodes
are the country composites and the edges are the share of one country's
forecast error variance that is attributable to another.

Two properties are worth stating because they decide how the network may be
read:

* **The node set changes between runs.**  A network is therefore only
  comparable with another network that was computed over the same nodes.
  This is why the ordering-sensitive Cholesky estimator is not the default
  here — it would make the comparison meaningless.
* **The countries are compared on their percentile lens.**  A percentile is
  the only quantity that is comparable across jurisdictions with different
  indicator mixes and different market structures; the deviation lens is
  reported alongside it as the absolute anchor.
"""

from __future__ import annotations

import pandas as pd

from ..contagion import GVDSpec, compute_spillover
from ..models import SpilloverResult

__all__ = ["cross_country_spillover", "align_country_composites"]


def align_country_composites(composites: dict[str, pd.Series]) -> pd.DataFrame:
    """Align the country composites onto their common calendar.

    Only the dates on which *every* country has an observation are kept: a
    variance decomposition over a ragged panel would silently attribute the
    missing days to whatever country happens to be present.
    """
    if not composites:
        return pd.DataFrame()
    frame = pd.DataFrame(composites).sort_index()
    frame = frame.dropna(how="any")
    return frame


def cross_country_spillover(
    composites: dict[str, pd.Series],
    spec: GVDSpec | None = None,
    *,
    scope: str = "global",
) -> SpilloverResult:
    """Compute the cross-country spillover network.

    ``composites`` maps a country code to its composite series.
    """
    spec = spec or GVDSpec()
    frame = align_country_composites(composites)
    if frame.shape[1] < 2:
        raise ValueError(
            "at least two countries with a common calendar are required for a "
            "cross-country decomposition"
        )
    result = compute_spillover(frame, spec, scope=scope)
    result.notes.append(
        "the cross-country network is computed over the country composites on the "
        "percentile lens; only dates present in every country are used"
    )
    return result
