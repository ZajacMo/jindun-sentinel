"""Tests for the forecast error variance decomposition and spillover networks."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from jindun.contagion import (
    GVDSpec,
    GVDSpecError,
    compute_spillover,
    compute_spillover_all,
    legacy_appendix_spillover,
    net_spillover,
    paper_equation_gvd,
    total_spillin,
    total_spillout,
)
from jindun.contagion.var import fit_var, is_stable, vma_coefficients


def _row_sums(matrix: list[list[float]]) -> list[float]:
    return [sum(row) for row in matrix]


@pytest.mark.parametrize("method", ["paper_equation", "sims_structural"])
def test_rows_sum_to_one(method: str, market_indices: pd.DataFrame) -> None:
    result = compute_spillover(
        market_indices, GVDSpec(method=method, horizon=8, var_order=3), scope="test"
    )
    sums = _row_sums(result.matrix)
    assert np.allclose(sums, 1.0, atol=1e-10)


@pytest.mark.parametrize("method", ["paper_equation", "sims_structural"])
def test_shares_are_non_negative(method: str, market_indices: pd.DataFrame) -> None:
    result = compute_spillover(
        market_indices, GVDSpec(method=method, horizon=8, var_order=3), scope="test"
    )
    matrix = np.asarray(result.matrix)
    assert np.all(matrix >= -1e-12)


def test_dy_generalised_is_signed_but_row_sums_hold(market_indices: pd.DataFrame) -> None:
    result = compute_spillover(
        market_indices, GVDSpec(method="dy_generalised", horizon=8, var_order=3), scope="test"
    )
    sums = _row_sums(result.matrix)
    assert np.allclose(sums, 1.0, atol=1e-10)
    assert any("signed" in note for note in result.notes)


def test_unknown_method_is_rejected() -> None:
    with pytest.raises(GVDSpecError):
        GVDSpec(method="does-not-exist")


def test_single_node_is_rejected(market_indices: pd.DataFrame) -> None:
    with pytest.raises(GVDSpecError):
        compute_spillover(market_indices[["equity"]], GVDSpec(method="paper_equation"))


def test_spillout_and_spillin_agree_on_the_total() -> None:
    """Every unit of spill-in must be matched by a unit of spill-out."""
    shares = np.array(
        [
            [0.80, 0.10, 0.10],
            [0.20, 0.60, 0.20],
            [0.05, 0.05, 0.90],
        ]
    )
    nodes = ["a", "b", "c"]
    spillout = total_spillout(shares, nodes)
    spillin = total_spillin(shares, nodes)
    assert sum(spillout.values()) == pytest.approx(sum(spillin.values()))
    net = net_spillover(spillout, spillin)
    assert net["a"] == pytest.approx(spillout["a"] - spillin["a"])


def test_legacy_appendix_requires_horizon_equal_to_node_count(
    market_indices: pd.DataFrame,
) -> None:
    with pytest.raises(GVDSpecError):
        compute_spillover(market_indices, GVDSpec(method="legacy_appendix", horizon=3, var_order=3))


def test_the_legacy_estimator_is_published_with_the_node_count_as_horizon(
    market_indices: pd.DataFrame,
) -> None:
    """The legacy horizon is structural, so the set computes it that way.

    The single-estimator call still refuses a mismatched horizon; the set
    computes the legacy index with the only horizon it is defined for and
    says so in its notes.
    """
    networks = compute_spillover_all(
        market_indices, GVDSpec(method="paper_equation", horizon=8, var_order=3), scope="test"
    )
    legacy = networks.results["legacy_appendix"]
    assert legacy.horizon == len(legacy.nodes)
    assert any("horizon" in note for note in legacy.notes)


def test_a_failing_estimator_does_not_remove_the_others(
    market_indices: pd.DataFrame,
) -> None:
    """One estimator that cannot be computed must not take the set down."""
    networks = compute_spillover_all(
        market_indices,
        GVDSpec(method="paper_equation", horizon=8, var_order=3),
        scope="test",
        methods=["paper_equation", "not_an_estimator"],
    )
    assert "paper_equation" in networks.results
    assert "not_an_estimator" in networks.failures
    assert "paper_equation" not in networks.failures


def test_every_estimator_is_published_by_default(market_indices: pd.DataFrame) -> None:
    networks = compute_spillover_all(
        market_indices, GVDSpec(method="paper_equation", horizon=8, var_order=3), scope="test"
    )
    assert set(networks.results) == {
        "paper_equation",
        "sims_structural",
        "dy_generalised",
        "legacy_appendix",
    }
    assert not networks.failures


def test_legacy_appendix_matches_an_independent_transcription(
    market_indices: pd.DataFrame,
) -> None:
    """The legacy estimator must equal a literal transcription of the source.

    The reference below is the competition-submission code, transcribed
    character for character, with the two index conventions of the original
    kept intact.
    """
    from statsmodels.tsa.api import VAR

    fitted = VAR(market_indices).fit(5)
    coefs = np.asarray(fitted.coefs, dtype=float)
    sigma = np.asarray(fitted.sigma_u, dtype=float)
    markets = list(market_indices.columns)
    horizon = 5

    reference = np.zeros((len(markets), len(markets)))
    for j in range(len(markets)):
        for k in range(len(markets)):
            denominator = abs(sigma[k, k]) * np.sum(
                sigma @ coefs[:horizon, j] @ coefs[:horizon, j].T
            )
            theta = np.sum((sigma @ coefs[:horizon, k]) ** 2) * abs(sigma[j, k]) / denominator
            reference[j, k] = abs(theta)
    reference = reference / reference.sum(axis=1, keepdims=True)

    our_fit = fit_var(market_indices, 5)
    assert our_fit is not None
    _, shares = legacy_appendix_spillover(our_fit, horizon)
    assert np.allclose(shares, reference, atol=1e-12)


def test_paper_equation_matches_its_own_definition(market_indices: pd.DataFrame) -> None:
    """Re-derive equations (6) and (7) independently and compare."""
    from jindun.contagion.var import vma_coefficients

    fit = fit_var(market_indices, 4)
    assert fit is not None
    raw, shares = paper_equation_gvd(fit, 6)

    psi = vma_coefficients(fit, 6)
    sigma = np.asarray(fit.sigma_u, dtype=float)
    size = len(fit.names)
    expected = np.zeros((size, size))
    denominator = np.zeros(size)
    for k in range(7):
        expected += (psi[k] ** 2) * np.diag(sigma).reshape(1, -1)
        denominator += np.einsum("ij,ij->i", psi[k], psi[k])
    expected = expected / denominator.reshape(-1, 1)

    assert np.allclose(raw, expected, atol=1e-12)
    assert np.allclose(shares, expected / expected.sum(axis=1, keepdims=True), atol=1e-12)


def test_vma_coefficients_start_with_the_identity(market_indices: pd.DataFrame) -> None:
    fit = fit_var(market_indices, 2)
    assert fit is not None
    psi = vma_coefficients(fit, 5)
    assert psi.shape == (6, len(fit.names), len(fit.names))
    assert np.allclose(psi[0], np.eye(len(fit.names)))


def test_stability_detection() -> None:
    stable = np.array([[[0.5, 0.0], [0.0, 0.5]]])
    unstable = np.array([[[1.5, 0.0], [0.0, 0.1]]])
    assert is_stable(stable, 1)
    assert not is_stable(unstable, 1)


def test_var_order_is_selected_when_not_pinned(market_indices: pd.DataFrame) -> None:
    result = compute_spillover(market_indices, GVDSpec(method="paper_equation", horizon=5))
    assert result.var_order is not None
    assert 1 <= result.var_order <= 5
    assert result.notes


def test_result_payload_is_language_neutral(market_indices: pd.DataFrame) -> None:
    result = compute_spillover(
        market_indices, GVDSpec(method="paper_equation", horizon=5, var_order=3), scope="CN"
    )
    payload = result.to_payload()
    assert payload["scope"] == "CN"
    assert payload["method"] == "paper_equation"
    assert payload["var_order"] == 3
    assert isinstance(payload["nodes"], list)
    assert all(isinstance(value, float) for value in payload["total_spillout"].values())
