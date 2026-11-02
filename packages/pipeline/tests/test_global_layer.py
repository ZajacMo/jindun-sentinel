"""Tests for the global layer, the surge test and the path resolution."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from jindun import paths
from jindun.contagion import GVDSpec, rolling_spillout_history, spillout_surge_scores
from jindun.contagion.surge import surging_markets
from jindun.global_layer.banking_network import (
    EURO_AREA_MEMBERS,
    build_banking_network,
    load_banking_network,
)


# ----------------------------------------------------------------------
# Surge test
# ----------------------------------------------------------------------
def test_rolling_history_ends_on_the_last_observation(market_indices: pd.DataFrame) -> None:
    history = rolling_spillout_history(
        market_indices, GVDSpec(horizon=4, max_order=2), window=200, step=100
    )
    assert not history.empty
    assert history.index[-1] == str(market_indices.index[-1])[:10]
    assert set(history.columns) == set(market_indices.columns)


def test_rolling_history_needs_enough_windows(market_indices: pd.DataFrame) -> None:
    history = rolling_spillout_history(
        market_indices, GVDSpec(horizon=4, max_order=2), window=200, step=100, min_windows=99
    )
    assert history.empty


def test_surge_scores_are_standardised_against_the_history(
    market_indices: pd.DataFrame,
) -> None:
    history = rolling_spillout_history(
        market_indices, GVDSpec(horizon=4, max_order=2), window=200, step=100
    )
    scores = spillout_surge_scores(history)
    assert scores
    for market, score in scores.items():
        assert score.market == market
        assert score.windows == len(history)
        assert np.isfinite(score.zscore)
        expected = (score.latest - score.mean) / score.std
        assert score.zscore == pytest.approx(expected, rel=1e-6)


def test_surging_markets_respect_the_threshold() -> None:
    # With ten windows a z-score above two is reachable; with four it is not.
    history = pd.DataFrame(
        {
            "equity": [0.10] * 9 + [0.40],
            "bond": [0.20] * 9 + [0.21],
        },
        index=pd.date_range("2023-01-31", periods=10, freq="QE"),
    )
    scores = spillout_surge_scores(history)
    # Both series show the same z-score, because a single outlier among equal
    # values always produces the same standardised distance.  The relative
    # margin is what separates a real surge from a rounding error.
    assert scores["equity"].zscore == pytest.approx(scores["bond"].zscore)
    assert "equity" in surging_markets(scores, 2.0, min_relative_change=0.20)
    assert "bond" not in surging_markets(scores, 2.0, min_relative_change=0.20)


def test_surge_scores_need_two_windows() -> None:
    history = pd.DataFrame({"equity": [0.1]}, index=pd.Index(["2024-01-01"]))
    assert spillout_surge_scores(history) == {}


# ----------------------------------------------------------------------
# Cross-border banking network
# ----------------------------------------------------------------------
def _records() -> dict[tuple[str, str], dict[str, float]]:
    return {
        ("US", "GB"): {"claims": 100.0, "liabilities": 40.0},
        ("US", "DE"): {"claims": 60.0, "liabilities": 20.0},
        ("GB", "US"): {"claims": 30.0, "liabilities": 90.0},
        ("CN", "US"): {"claims": 20.0, "liabilities": 10.0},
    }


def test_banking_network_edges_are_directed() -> None:
    network = build_banking_network(_records(), as_of="2025-Q4", scale=1.0)
    pairs = {(edge.source, edge.target) for edge in network.edges}
    assert ("US", "GB") in pairs
    assert ("GB", "US") in pairs
    assert ("US", "GB") != ("GB", "US")


def test_banking_network_node_metrics() -> None:
    network = build_banking_network(_records(), as_of="2025-Q4", scale=1.0)
    united_states = network.nodes["US"]
    # US lends 100 to GB and 60 to DE; it is owed 90 by GB and 10 by CN.
    assert united_states["out_claims"] == pytest.approx(160.0)
    assert united_states["in_liabilities"] == pytest.approx(100.0)
    assert united_states["net_exposure"] == pytest.approx(60.0)


def test_banking_network_concentration_is_a_share() -> None:
    network = build_banking_network(_records(), as_of="2025-Q4", scale=1.0)
    concentration = network.concentration
    assert 0.0 <= concentration["hhi_bilateral"] <= 1.0
    assert 0.0 <= concentration["largest_bilateral_share"] <= 1.0
    assert concentration["total_claims"] == pytest.approx(210.0)


def test_euro_area_members_are_folded_and_intra_area_edges_dropped() -> None:
    records = {
        ("DE", "FR"): {"claims": 10.0, "liabilities": 10.0},
        ("DE", "US"): {"claims": 50.0, "liabilities": 5.0},
        ("FR", "US"): {"claims": 30.0, "liabilities": 5.0},
    }
    network = build_banking_network(records, as_of="2025-Q4", scale=1.0)
    pairs = {(edge.source, edge.target) for edge in network.edges}
    assert ("XM", "US") in pairs
    assert ("DE", "FR") not in pairs
    assert "XM" in network.nodes
    assert network.nodes["XM"]["out_claims"] == pytest.approx(80.0)


def test_euro_area_members_are_recognised() -> None:
    assert "DE" in EURO_AREA_MEMBERS
    assert "FR" in EURO_AREA_MEMBERS


def test_load_banking_network_reads_a_snapshot(tmp_path) -> None:
    path = tmp_path / "lbs.csv"
    path.write_text(
        "MEASURE,L_REP_CTY,L_CP_COUNTRY,L_POSITION,TIME_PERIOD,UNIT_MEASURE,OBS_VALUE\n"
        "all_instruments,US,GB,C,2025-Q4,USD,1000\n"
        "all_instruments,US,GB,L,2025-Q4,USD,400\n"
        "all_instruments,GB,US,C,2025-Q4,USD,300\n"
        "all_instruments,GB,US,L,2025-Q4,USD,900\n"
        "loans_and_deposits,US,GB,C,2025-Q4,USD,50\n",
        encoding="utf-8",
    )
    network = load_banking_network(path, scale=1e6)
    assert network.as_of == "2025-Q4"
    assert len(network.edges) == 2
    edge = next(edge for edge in network.edges if edge.source == "US" and edge.target == "GB")
    assert edge.claims == pytest.approx(1e9)
    assert edge.liabilities == pytest.approx(4e8)
    assert edge.net == pytest.approx(6e8)


def test_load_banking_network_skips_the_aggregates(tmp_path) -> None:
    path = tmp_path / "lbs.csv"
    path.write_text(
        "MEASURE,L_REP_CTY,L_CP_COUNTRY,L_POSITION,TIME_PERIOD,UNIT_MEASURE,OBS_VALUE\n"
        "all_instruments,5A,US,C,2025-Q4,USD,9999\n"
        "all_instruments,US,5J,C,2025-Q4,USD,8888\n"
        "all_instruments,US,GB,C,2025-Q4,USD,1000\n",
        encoding="utf-8",
    )
    network = load_banking_network(path, scale=1.0)
    assert [(edge.source, edge.target) for edge in network.edges] == [("US", "GB")]


def test_banking_network_payload_is_json_safe() -> None:
    import json

    network = build_banking_network(_records(), as_of="2025-Q4", scale=1.0)
    payload = network.to_payload()
    json.dumps(payload)  # must not raise
    assert payload["as_of"] == "2025-Q4"
    assert payload["edges"]


# ----------------------------------------------------------------------
# Path resolution
# ----------------------------------------------------------------------
def test_repo_root_carries_the_workspace_manifest() -> None:
    root = paths.repo_root()
    assert (root / "pyproject.toml").is_file()
    assert (root / "locales").is_dir()


def test_locales_are_resolved_to_the_shared_catalogue() -> None:
    root = paths.locales_dir()
    assert root.is_dir()
    assert (root / "en-US.json").is_file()


def test_data_locations_sit_under_the_repository() -> None:
    for location in (paths.snapshot_dir(), paths.runs_dir(), paths.baseline_dir()):
        assert location.is_relative_to(paths.repo_root())
