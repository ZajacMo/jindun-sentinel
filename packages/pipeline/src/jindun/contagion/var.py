"""Vector autoregression and its VMA(∞) representation.

The contagion module needs three things from a VAR:

1. a stable VAR of the right order,
2. the moving-average coefficients :math:`\\Psi_k` so that the impulse
   responses can be accumulated into a forecast-error variance decomposition,
3. the residual covariance :math:`\\Sigma_u`.

The VAR order is selected by information criterion among the orders whose fit
is stable (roots of the companion characteristic polynomial inside the unit
circle).  The paper's specification is "choose p such that VAR(p) is stable",
which this module makes explicit and reproducible.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

__all__ = ["VARFit", "select_var_order", "fit_var", "vma_coefficients", "is_stable"]


@dataclass(slots=True)
class VARFit:
    """A fitted VAR model."""

    order: int
    coefficients: np.ndarray
    intercept: np.ndarray
    sigma_u: np.ndarray
    names: list[str]
    aic: float
    bic: float
    stable: bool
    sample: tuple[str, str] | None = None
    diagnostics: dict[str, float] = field(default_factory=dict)

    @property
    def horizon_limit(self) -> int:
        """Largest horizon the VMA representation should be truncated at."""
        return max(100, self.order * 40)


def is_stable(coefficients: np.ndarray, order: int) -> bool:
    """Check that the VAR companion roots lie inside the unit circle.

    ``coefficients`` has shape ``(order, n, n)`` — one coefficient matrix per
    lag, in the same layout as ``statsmodels`` returns.
    """
    if order <= 0:
        return True
    size = coefficients.shape[1]
    companion = np.zeros((size * order, size * order))
    for index in range(order):
        companion[:size, index * size : (index + 1) * size] = coefficients[index]
    if order > 1:
        companion[size:, :-size] = np.eye(size * (order - 1))
    eigenvalues = np.abs(np.linalg.eigvals(companion))
    return bool(np.all(eigenvalues < 1.0 - 1e-8))


def _fit_single(data: pd.DataFrame, order: int) -> VARFit | None:
    from statsmodels.tsa.api import VAR

    try:
        model = VAR(data)
        fitted = model.fit(maxlags=order, trend="c")
    except Exception:
        return None

    coefficients = np.asarray(fitted.coefs, dtype=float)
    if coefficients.ndim == 3 and coefficients.shape[0] != order:
        coefficients = coefficients[-order:]
    intercept = np.asarray(fitted.intercept, dtype=float).reshape(-1)
    sigma_u = np.asarray(fitted.sigma_u, dtype=float)

    try:
        aic = float(fitted.aic)
        bic = float(fitted.bic)
    except Exception:
        aic = float("nan")
        bic = float("nan")

    stable = is_stable(coefficients, order)
    dates = [str(index) for index in data.index]
    return VARFit(
        order=order,
        coefficients=coefficients,
        intercept=intercept,
        sigma_u=sigma_u,
        names=[str(column) for column in data.columns],
        aic=aic,
        bic=bic,
        stable=stable,
        sample=(dates[0], dates[-1]) if dates else None,
    )


def select_var_order(
    data: pd.DataFrame,
    *,
    max_order: int = 5,
    criterion: str = "bic",
    require_stable: bool = True,
) -> VARFit | None:
    """Select and fit a VAR of ``data``."""
    clean = data.replace([np.inf, -np.inf], np.nan).dropna(how="any")
    if clean.shape[0] < 30 or clean.shape[1] < 2:
        return None

    upper = max(1, min(max_order, (len(clean) - 1) // (10 * clean.shape[1])))
    best: VARFit | None = None
    best_score = np.inf

    for order in range(1, upper + 1):
        fit = _fit_single(clean, order)
        if fit is None:
            continue
        if require_stable and not fit.stable:
            continue
        score = fit.bic if criterion == "bic" else fit.aic
        if np.isnan(score):
            continue
        if score < best_score:
            best_score = score
            best = fit
    return best


def fit_var(data: pd.DataFrame, order: int) -> VARFit | None:
    """Fit a VAR of a fixed order."""
    clean = data.replace([np.inf, -np.inf], np.nan).dropna(how="any")
    if clean.shape[0] < max(10, order * 3):
        return None
    return _fit_single(clean, order)


def vma_coefficients(fit: VARFit, horizon: int) -> np.ndarray:
    """Return the VMA(∞) coefficients ``Psi_k`` for ``k = 0 .. horizon``.

    ``Psi_k`` has shape ``(horizon + 1, n, n)``.
    """
    size = len(fit.names)
    coefficients = fit.coefficients
    psi = np.zeros((horizon + 1, size, size))
    psi[0] = np.eye(size)
    for k in range(1, horizon + 1):
        accumulated = np.zeros((size, size))
        for lag in range(1, min(k, fit.order) + 1):
            accumulated += coefficients[lag - 1] @ psi[k - lag]
        psi[k] = accumulated
    return psi


def impulse_response(fit: VARFit, horizon: int) -> np.ndarray:
    """Orthogonalised impulse responses of shape ``(horizon + 1, n, n)``."""
    from scipy.linalg import cholesky

    psi = vma_coefficients(fit, horizon)
    try:
        lower = cholesky(fit.sigma_u, lower=True)
    except Exception:
        lower = np.eye(len(fit.names))
    responses = np.zeros_like(psi)
    for k in range(psi.shape[0]):
        responses[k] = psi[k] @ lower
    return responses
