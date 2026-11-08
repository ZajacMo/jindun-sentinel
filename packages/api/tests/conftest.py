"""Shared fixtures for the API tests.

The API is a read-only view over the artefacts the pipeline writes, so the
tests build a small artefact tree of their own and point the store at it.  The
fixtures are deliberately hand-written rather than produced by the pipeline:
the point of these tests is to pin the *contract* the API exposes, not to
re-test the computation that produces the numbers.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from jindun_api.app import create_app
from jindun_api.store import ArtifactStore, get_store


def _spillover_block(method: str, *, nodes: list[str], horizon: int) -> dict[str, Any]:
    """A spillover block for one estimator."""
    size = len(nodes)
    matrix = [
        [0.5 if row == column else 0.5 / (size - 1) for column in range(size)]
        for row in range(size)
    ]
    return {
        "scope": "CN",
        "nodes": nodes,
        "matrix": matrix,
        "total_spillout": {node: 0.25 for node in nodes},
        "total_spillin": {node: 0.25 for node in nodes},
        "net": {node: 0.0 for node in nodes},
        "horizon": horizon,
        "window": None,
        "method": method,
        "var_order": 2,
        "notes": [
            {
                "key": "spillover.note.method",
                "params": {
                    "method": method,
                    "order": 2,
                    "criterion": "bic",
                    "horizon": horizon,
                    "start": "2024-01-01",
                    "end": "2024-12-31",
                },
            }
        ],
    }


def _run_payload(
    code: str,
    *,
    profile: str = "mbsed",
    capabilities: dict[str, bool] | None = None,
    spillover: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """A minimal run artefact."""
    return {
        "country_code": code,
        "as_of": "2026-11-03",
        "profile": profile,
        "capabilities": capabilities
        or {
            "composite_synthesis": profile != "official_index",
            "market_decomposition": profile != "official_index",
            "market_attribution": profile != "official_index",
            "spillover_network": profile != "official_index",
            "regime": True,
            "forecast": True,
        },
        "market_indices": {
            "dates": ["2026-11-02", "2026-11-03"],
            "series": {"equity": [0.1, 0.2]},
        },
        "composite": [{"date": "2026-11-03", "value": 0.4}],
        "percentile": [{"date": "2026-11-03", "value": 0.6}],
        "deviation": [{"date": "2026-11-03", "value": -0.2}],
        "regime": {
            "dates": ["2026-11-03"],
            "labels": ["moderate"],
            "probability_moderate": [0.8],
            "probability_high": [0.2],
            "params": {},
        },
        "spillover": spillover or {},
        "alerts": [],
        "attribution": {},
        "forecast": {},
        "warnings": [],
    }


@pytest.fixture
def artefact_root(tmp_path: Path) -> Path:
    """A miniature artefact tree with a decomposed and an undecomposed economy."""
    root = tmp_path / "runs"

    decomposed = _spillover_block("paper_equation", nodes=["equity", "bond"], horizon=10)
    decomposed["default_method"] = "paper_equation"
    decomposed["estimators"] = {
        "paper_equation": _spillover_block("paper_equation", nodes=["equity", "bond"], horizon=10),
        "legacy_appendix": _spillover_block("legacy_appendix", nodes=["equity", "bond"], horizon=2),
    }
    decomposed["failed_estimators"] = {}

    cn = root / "CN"
    cn.mkdir(parents=True)
    (cn / "run.json").write_text(
        json.dumps(_run_payload("CN", spillover=decomposed)),
        encoding="utf-8",
    )
    (cn / "quality.json").write_text(
        json.dumps(
            {
                "generated_at": "2026-11-03T00:00:00+00:00",
                "passed": True,
                "counts": {"total": 1, "ok": 1, "warning": 0, "failure": 0},
                "series": [],
            },
        ),
        encoding="utf-8",
    )

    us = root / "US"
    us.mkdir(parents=True)
    (us / "run.json").write_text(
        json.dumps(_run_payload("US", profile="official_index")),
        encoding="utf-8",
    )

    global_dir = root / "global"
    global_dir.mkdir(parents=True)
    (global_dir / "spillover.json").write_text(json.dumps(decomposed), encoding="utf-8")
    (global_dir / "cycle.json").write_text(
        json.dumps({"dates": [], "countries": ["CN", "US"]}),
        encoding="utf-8",
    )
    (global_dir / "banking_network.json").write_text(
        json.dumps({"as_of": "2026-Q2", "edges": [], "nodes": {}}),
        encoding="utf-8",
    )
    (global_dir / "gsib.json").write_text(json.dumps({"banks": [], "count": 0}), encoding="utf-8")

    return root


@pytest.fixture
def client(artefact_root: Path) -> TestClient:
    """A test client whose store reads the miniature artefact tree."""
    application = create_app()
    application.dependency_overrides[get_store] = lambda: ArtifactStore(artefact_root)
    with TestClient(application) as test_client:
        yield test_client
