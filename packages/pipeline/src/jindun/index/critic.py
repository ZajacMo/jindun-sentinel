"""CRITIC objective weighting.

CRITIC (Criteria Relevance Importance Criterion, Diakoulaki et al.) weights
indicators by how much *contrast* they carry: an indicator that varies a lot
and is not explained by the other indicators carries more information about
the underlying state.

The legacy pipeline read pre-computed weights out of the second worksheet of
the input workbooks.  This module recomputes them from the data so the weights
are reproducible, and the configuration can still pin explicit weights when a
researcher wants to reproduce a published specification exactly.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

__all__ = ["critic_weights", "resolve_weights"]


def critic_weights(panel: pd.DataFrame) -> pd.Series:
    """Return CRITIC weights for the columns of ``panel``.

    The weights sum to one.  Indicators with zero information content (a
    constant column, or one perfectly collinear with another) receive a zero
    weight rather than a division by zero.
    """
    if panel.shape[1] == 0:
        return pd.Series(dtype=float)
    if panel.shape[1] == 1:
        return pd.Series([1.0], index=panel.columns)

    standardised = (panel - panel.mean()) / panel.std(ddof=0).replace(0.0, np.nan)
    standardised = standardised.replace([np.inf, -np.inf], np.nan).fillna(0.0)

    sigma = standardised.std(ddof=0).fillna(0.0)
    correlation = standardised.corr().fillna(0.0)
    # Perfectly collinear pairs contribute zero contrast.
    contrast = correlation.where(~np.eye(len(correlation), dtype=bool), 0.0)
    information = sigma * (1.0 - contrast).sum(axis=1)
    information = information.clip(lower=0.0)

    total = float(information.sum())
    if total <= 0:
        return pd.Series([1.0 / len(panel.columns)] * len(panel.columns), index=panel.columns)
    return (information / total).astype(float)


def resolve_weights(
    panel: pd.DataFrame,
    configured: dict[str, float] | None = None,
    *,
    mode: str = "configured",
) -> pd.Series:
    """Return the indicator weights to use.

    ``mode`` may be:

    ``configured``
        Use the weights supplied in configuration. Indicators without an
        explicit weight fall back to the CRITIC weight, renormalised.
    ``critic``
        Always recompute CRITIC weights from the data.
    ``equal``
        Equal weights.
    """
    columns = list(panel.columns)
    if mode == "equal":
        return pd.Series([1.0 / len(columns)] * len(columns), index=columns)
    if mode == "critic" or not configured:
        return critic_weights(panel)

    weights = critic_weights(panel)
    final = pd.Series(0.0, index=columns)
    specified = {code: float(value) for code, value in configured.items() if code in columns}
    remainder = [code for code in columns if code not in specified]
    specified_total = sum(specified.values())
    if remainder and specified_total < 1.0:
        residual = 1.0 - specified_total
        residual_weights = weights.loc[remainder]
        residual_total = float(residual_weights.sum())
        if residual_total > 0:
            for code, value in residual_weights.items():
                final[code] = residual * (value / residual_total)
        else:
            for code in remainder:
                final[code] = residual / len(remainder)
    for code, value in specified.items():
        final[code] = value
    total = float(final.sum())
    if total <= 0:
        return critic_weights(panel)
    return (final / total).astype(float)
