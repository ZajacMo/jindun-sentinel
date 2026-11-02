"""Generalized forecast error variance decomposition and spillover networks.

Three estimators are provided, and they are *not* interchangeable.  Each one
answers a slightly different question and each one has a documented caveat.

``paper_equation``
    The estimator written in the source paper (equations 6 and 7):

    .. math::

        Y_{ij}^{H} = \\frac{\\sum_{k=0}^{H-1} (e_i' A_k e_j)^2 \\varepsilon_{jj}}
                          {\\sum_{k=0}^{H-1} (e_i' A_k A_k' e_i)}, \\qquad
        \\widetilde{Y}_{ij}^{H} = \\frac{Y_{ij}^{H}}{\\sum_{j=1}^{n} Y_{ij}^{H}}

    with ``A_k`` the VMA(inf) coefficient :math:`\\Psi_k` and
    :math:`\\varepsilon_{jj}` the variance of the ``j``-th equation's
    estimation error.  The row normalisation in the second equation cancels
    the denominator of the first, so only the *shape* of the numerator
    matters; the denominator is nevertheless evaluated and reported so that
    the implementation can be checked against the paper line by line.

``sims_structural``
    Sims (1980) forecast error variance decomposition with Cholesky
    orthogonalisation and unit-variance structural shocks.  This is the
    estimator that most practitioners mean by "spillover".  It is
    non-negative by construction but depends on the ordering of the
    variables, which is why it must not be used to compare systems with
    different node sets.

``dy_generalised``
    The Diebold-Yilmaz (2009, 2012) *generalized* forecast error variance
    decomposition, which does not require contemporaneous independence and
    is therefore free of the ordering artefact:

    .. math::

        \\Theta_{ij}^{H} = \\sigma_{jj}^{-1}
            \\sum_{k=0}^{H-1} (\\Psi_k \\Sigma_u \\Psi_k')_{ij}

    Caveat: the generalized decomposition is a signed quantity — a negative
    entry means the innovation of node ``j`` *reduces* the forecast error
    variance of node ``i``.  That is a real feature of the estimator, not a
    numerical defect, and it is why the absolute-value variant used by the
    legacy implementation is documented separately.

``legacy_appendix``
    A literal transcription of the spillover code that shipped with the
    original competition submission.  It is retained so that numbers
    published in the earlier paper can be regenerated, and it is *not* a
    forecast error variance decomposition: it is a residual-correlation
    weighted index.  See ``docs/methodology/spillover-legacy-vs-paper.md``.

The shared reporting convention follows the source paper: the matrix is
normalised row-wise, so ``matrix[i][j]`` is the share of node ``i``'s own
forecast error variance that is attributable to node ``j``.  Consequently

* ``total_spillout[j]`` (column off-diagonal sum) is how much of the
  *system's* forecast error variance node ``j`` is responsible for, and
* ``total_spillin[i]`` (row off-diagonal sum) is how much of node ``i``'s
  own forecast error variance comes from elsewhere.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass

import numpy as np
import pandas as pd

from ..models import SpilloverResult
from .var import VARFit, fit_var, select_var_order, vma_coefficients

__all__ = [
    "GVDSpec",
    "GVDSpecError",
    "METHODS",
    "compute_spillover",
    "sims_structural_gvd",
    "paper_equation_gvd",
    "diebold_yilmaz_generalised_gvd",
    "legacy_appendix_spillover",
    "total_spillout",
    "total_spillin",
    "net_spillover",
]

METHODS = (
    "paper_equation",
    "sims_structural",
    "dy_generalised",
    "legacy_appendix",
)


class GVDSpecError(ValueError):
    """Raised when a decomposition cannot be computed as requested."""


@dataclass(frozen=True, slots=True)
class GVDSpec:
    """Everything that controls a spillover computation."""

    method: str = "paper_equation"
    horizon: int = 10
    var_order: int | None = None
    criterion: str = "bic"
    max_order: int = 5
    require_stable: bool = True
    transform: str = "level"
    absolute: bool = False
    notes: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if self.method not in METHODS:
            raise GVDSpecError(f"unknown method {self.method!r}; expected one of {METHODS}")
        if self.horizon < 1:
            raise GVDSpecError("horizon must be >= 1")


def _prepare(data: pd.DataFrame, transform: str) -> pd.DataFrame:
    frame = data.replace([np.inf, -np.inf], np.nan).dropna(how="any")
    if transform in ("none", "", "level"):
        return frame
    if transform == "diff":
        return frame.diff().dropna(how="any")
    if transform == "logdiff":
        return np.log(frame).diff().dropna(how="any")
    raise GVDSpecError(f"unknown transform {transform!r}")


def _fit(data: pd.DataFrame, spec: GVDSpec) -> VARFit:
    if spec.var_order is not None:
        fit = fit_var(data, spec.var_order)
    else:
        fit = select_var_order(
            data,
            max_order=spec.max_order,
            criterion=spec.criterion,
            require_stable=spec.require_stable,
        )
    if fit is None:
        raise GVDSpecError(
            "no stable VAR could be fitted to the supplied series; "
            "check the sample length or relax the stability requirement"
        )
    return fit


def _cholesky(sigma: np.ndarray) -> np.ndarray:
    from scipy.linalg import cholesky

    try:
        return cholesky(sigma, lower=True)
    except Exception:  # pragma: no cover - defensive, sigma is PSD in practice
        return np.eye(sigma.shape[0])


def paper_equation_gvd(fit: VARFit, horizon: int) -> tuple[np.ndarray, np.ndarray]:
    """Equations (6) and (7) of the source paper.

    Returns ``(raw, shares)`` where ``raw[i][j]`` is the un-normalised
    :math:`Y_{ij}^{H}` and ``shares`` is the row-normalised matrix.
    """
    size = len(fit.names)
    psi = vma_coefficients(fit, horizon)
    sigma = np.asarray(fit.sigma_u, dtype=float)
    shock_variance = np.diag(sigma)

    numerator = np.zeros((size, size))
    denominator = np.zeros(size)
    for k in range(horizon + 1):
        response = psi[k]
        numerator += (response**2) * shock_variance.reshape(1, -1)
        denominator += np.einsum("ij,ij->i", response, response)

    raw = numerator / denominator.reshape(-1, 1)
    row_sums = raw.sum(axis=1, keepdims=True)
    if np.any(row_sums == 0):
        raise GVDSpecError("degenerate decomposition: a row of Y is identically zero")
    return raw, raw / row_sums


def sims_structural_gvd(fit: VARFit, horizon: int) -> tuple[np.ndarray, np.ndarray]:
    """Sims (1980) FEVD with Cholesky orthogonalisation."""
    size = len(fit.names)
    psi = vma_coefficients(fit, horizon)
    sigma = np.asarray(fit.sigma_u, dtype=float)
    lower = _cholesky(sigma)

    raw = np.zeros((size, size))
    for k in range(horizon + 1):
        response = psi[k] @ lower
        raw += response**2
    row_sums = raw.sum(axis=1, keepdims=True)
    if np.any(row_sums == 0):
        raise GVDSpecError("degenerate decomposition: a row of the FEVD is identically zero")
    return raw, raw / row_sums


def diebold_yilmaz_generalised_gvd(fit: VARFit, horizon: int) -> tuple[np.ndarray, np.ndarray]:
    """Diebold-Yilmaz (2009, 2012) generalized FEVD.

    The result is signed: a negative entry means the innovation of the
    column node reduces the forecast error variance of the row node.
    """
    size = len(fit.names)
    psi = vma_coefficients(fit, horizon)
    sigma = np.asarray(fit.sigma_u, dtype=float)
    shock_variance = np.diag(sigma)
    if np.any(shock_variance <= 0):
        raise GVDSpecError("a degenerate variance was detected in the VAR residual covariance")

    raw = np.zeros((size, size))
    for k in range(horizon + 1):
        raw += psi[k] @ sigma @ psi[k].T
    raw = raw / shock_variance.reshape(1, -1)
    row_sums = raw.sum(axis=1, keepdims=True)
    if np.any(row_sums == 0):
        raise GVDSpecError("degenerate decomposition: a row of the GVD is identically zero")
    return raw, raw / row_sums


def legacy_appendix_spillover(fit: VARFit, horizon: int) -> tuple[np.ndarray, np.ndarray]:
    """Literal transcription of the legacy competition-submission code.

    The original implementation is reproduced verbatim, including its two
    structural quirks, so that published numbers can be regenerated:

    1. the denominator is built from the *row* of the coefficient stack
       selected by the outer loop index while the numerator uses the
       *column* selected by the inner loop index, and
    2. the matrix product ``sigma @ coefs[:H, j]`` is only defined when the
       horizon equals the number of variables.

    The result is a residual-correlation weighted index, **not** a forecast
    error variance decomposition.
    """
    size = len(fit.names)
    coefs = np.asarray(fit.coefficients, dtype=float)
    sigma = np.asarray(fit.sigma_u, dtype=float)
    usable = min(horizon, coefs.shape[0])
    if usable != size:
        raise GVDSpecError(
            "the legacy appendix implementation requires horizon == number of nodes "
            f"(got horizon={horizon}, nodes={size})"
        )

    raw = np.zeros((size, size))
    for j in range(size):
        for k in range(size):
            column_j = coefs[:usable, j]
            column_k = coefs[:usable, k]
            denominator = abs(sigma[k, k]) * float(np.sum(sigma @ column_j @ column_j.T))
            if denominator == 0:
                raise GVDSpecError("the legacy decomposition hit a zero denominator")
            theta = float(np.sum((sigma @ column_k) ** 2)) * abs(sigma[j, k]) / denominator
            raw[j, k] = abs(theta)
    row_sums = raw.sum(axis=1, keepdims=True)
    if np.any(row_sums == 0):
        raise GVDSpecError("degenerate decomposition: a row of the legacy index is zero")
    return raw, raw / row_sums


_DISPATCH = {
    "paper_equation": paper_equation_gvd,
    "sims_structural": sims_structural_gvd,
    "dy_generalised": diebold_yilmaz_generalised_gvd,
    "legacy_appendix": legacy_appendix_spillover,
}


def total_spillout(shares: np.ndarray, nodes: Sequence[str]) -> dict[str, float]:
    """How much of the system's forecast error variance each node causes.

    This is the column off-diagonal sum: the share of *other* nodes'
    forecast error variance that is attributable to the node.
    """
    result: dict[str, float] = {}
    for index, node in enumerate(nodes):
        column = shares[:, index]
        result[str(node)] = float(column.sum() - column[index])
    return result


def total_spillin(shares: np.ndarray, nodes: Sequence[str]) -> dict[str, float]:
    """How much of each node's own forecast error variance comes from elsewhere."""
    result: dict[str, float] = {}
    for index, node in enumerate(nodes):
        row = shares[index]
        result[str(node)] = float(row.sum() - row[index])
    return result


def net_spillover(
    spillout: Mapping[str, float], spillin: Mapping[str, float]
) -> dict[str, float]:
    """Net transmitter minus net receiver, per node."""
    return {
        node: float(spillout.get(node, 0.0) - spillin.get(node, 0.0)) for node in spillout
    }


def compute_spillover(
    data: pd.DataFrame,
    spec: GVDSpec | None = None,
    *,
    scope: str = "",
    window: tuple[str, str] | None = None,
) -> SpilloverResult:
    """Fit a VAR to ``data`` and return the spillover network.

    ``data`` must be a frame whose columns are the nodes (markets for a
    single country, countries for the global layer) and whose index is the
    observation date.
    """
    spec = spec or GVDSpec()
    frame = _prepare(data, spec.transform)
    if frame.shape[1] < 2:
        raise GVDSpecError("at least two nodes are required for a spillover decomposition")

    fit = _fit(frame, spec)
    estimator = _DISPATCH[spec.method]
    raw, shares = estimator(fit, spec.horizon)
    if spec.absolute:
        shares = np.abs(shares)
        row_sums = shares.sum(axis=1, keepdims=True)
        shares = shares / row_sums

    nodes = [str(column) for column in frame.columns]
    spillout = total_spillout(shares, nodes)
    spillin = total_spillin(shares, nodes)

    notes = list(spec.notes)
    sample = fit.sample or ("", "")
    notes.append(
        f"method={spec.method}; VAR order={fit.order} (selected by {spec.criterion}); "
        f"horizon={spec.horizon}; sample={sample[0]}..{sample[1]}"
    )
    if spec.method == "dy_generalised":
        notes.append(
            "the generalized decomposition is signed: negative entries mean the "
            "column node reduces the row node's forecast error variance"
        )
    if spec.method == "legacy_appendix":
        notes.append(
            "legacy appendix implementation: residual-correlation weighted index, "
            "not a forecast error variance decomposition"
        )
    if not fit.stable:
        notes.append("WARNING: the fitted VAR is not stable; the decomposition is unreliable")

    return SpilloverResult(
        scope=scope or "unspecified",
        nodes=nodes,
        matrix=[[float(value) for value in row] for row in shares],
        total_spillout=spillout,
        total_spillin=spillin,
        horizon=spec.horizon,
        window=window,
        notes=notes,
        var_order=fit.order,
        method=spec.method,
        net=net_spillover(spillout, spillin),
    )
