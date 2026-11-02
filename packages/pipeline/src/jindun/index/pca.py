"""Principal component analysis for the tertiary indicator panel.

This module replaces the legacy ``pca()`` implementation, which contained a
defect (E1) that could change the reported numbers:

* the legacy code used :func:`numpy.linalg.eig` on the covariance matrix and
  consumed the returned eigenvalues **in whatever order the solver produced**;
* the loop that was supposed to pick the number of components tested
  ``sum(eig_value[:principal_num]) / sum(eig_value) > 0.8`` starting from
  ``principal_num = 0`` and left the variable at ``index_num - 1`` when no
  break happened, so the retained component count was neither the minimal one
  nor the maximal one.

The corrected implementation uses :func:`numpy.linalg.eigh`, which is the right
routine for a symmetric covariance matrix, sorts the eigenvalues descending,
clips the numerically negative ones to zero, and then selects the *smallest*
number of components whose cumulative explained variance exceeds the
configured threshold.

The legacy behaviour is still available through
:func:`pca_legacy_selection` so the regression suite can quantify exactly how
much the correction moved the published numbers.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

__all__ = ["PCAResult", "pca_analysis", "pca_legacy_selection"]


@dataclass(slots=True)
class PCAResult:
    """Outcome of a principal component analysis."""

    eigenvalues: np.ndarray
    eigenvectors: np.ndarray
    explained_variance_ratio: np.ndarray
    cumulative_variance_ratio: np.ndarray
    n_components: int
    factor_loading: pd.DataFrame
    factor_contribution: pd.Series
    correlation: pd.DataFrame

    @property
    def threshold(self) -> float:
        if self.n_components >= len(self.cumulative_variance_ratio):
            return float(self.cumulative_variance_ratio[-1])
        return float(self.cumulative_variance_ratio[self.n_components - 1])

    def to_payload(self) -> dict[str, object]:
        return {
            "n_components": self.n_components,
            "eigenvalues": [float(value) for value in self.eigenvalues],
            "explained_variance_ratio": [float(value) for value in self.explained_variance_ratio],
            "cumulative_variance_ratio": [float(value) for value in self.cumulative_variance_ratio],
            "factor_loading": self.factor_loading.round(6).to_dict(),
            "factor_contribution": {
                str(key): float(value) for key, value in self.factor_contribution.items()
            },
        }


def _covariance_eigendecomposition(cov: pd.DataFrame) -> tuple[np.ndarray, np.ndarray]:
    """Descending eigendecomposition of a symmetric covariance matrix."""
    values, vectors = np.linalg.eigh(cov.to_numpy(dtype=float))
    order = np.argsort(values)[::-1]
    values = values[order]
    vectors = vectors[:, order]
    # Numerical noise can make a tiny positive eigenvalue negative.
    values = np.clip(values, 0.0, None)
    return values, vectors


def pca_analysis(
    panel: pd.DataFrame,
    *,
    variance_threshold: float = 0.80,
    legacy: bool = False,
) -> PCAResult:
    """Run PCA on the normalised indicator panel.

    Parameters
    ----------
    panel:
        Normalised indicator panel (one column per indicator).
    variance_threshold:
        Cumulative explained variance that must be reached.
    legacy:
        Reproduce the defective legacy component-selection rule. Used only by
        the regression suite to quantify the correction.
    """
    if panel.shape[1] == 0:
        raise ValueError("PCA requires at least one indicator")
    if panel.shape[0] < 3:
        raise ValueError("PCA requires at least three observations")

    correlation = panel.corr()
    covariance = panel.cov()
    values, vectors = _covariance_eigendecomposition(covariance)

    total = float(values.sum())
    ratios = np.zeros_like(values) if total <= 0 else values / total
    cumulative = np.cumsum(ratios)

    if legacy:
        n_components = pca_legacy_selection(values, panel.shape[1])
    else:
        n_components = int(np.searchsorted(cumulative, variance_threshold) + 1)
        n_components = max(1, min(n_components, len(values)))

    loading_values = vectors[:, :n_components] * np.sqrt(values[:n_components])
    factor_loading = pd.DataFrame(
        loading_values,
        index=panel.columns,
        columns=[f"PC{i + 1}" for i in range(n_components)],
    )

    # The legacy contribution metric divides the loading matrix by the
    # standard deviation of the eigenvalues, then sums absolute values.
    eigenvalue_std = float(np.std(values))
    coefficient = factor_loading / eigenvalue_std if eigenvalue_std > 0 else factor_loading
    contribution = coefficient.abs().sum(axis=1)

    return PCAResult(
        eigenvalues=values,
        eigenvectors=vectors,
        explained_variance_ratio=ratios,
        cumulative_variance_ratio=cumulative,
        n_components=n_components,
        factor_loading=factor_loading,
        factor_contribution=contribution,
        correlation=correlation,
    )


def pca_legacy_selection(eigenvalues: np.ndarray, index_num: int) -> int:
    """Reproduce the legacy component-count rule for comparison purposes.

    The legacy code iterated ``principal_num`` from ``0`` upwards and broke
    when the *unsorted* cumulative share first exceeded 80 %.  When it never
    broke, the loop variable was left at ``index_num - 1``.
    """
    principal_num = 6
    for principal_num in range(index_num):
        if float(np.sum(eigenvalues[:principal_num])) / float(np.sum(eigenvalues)) > 0.8:
            break
    return max(1, min(principal_num + 1, len(eigenvalues)))
