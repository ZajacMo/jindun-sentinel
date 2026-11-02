"""Global layer routes: cross-country contagion, the global cycle factor, the
cross-border banking network and the G-SIB list.

The global layer is one step up from the country layer: the same methods are
applied to a different set of nodes.  The cross-country spillover network
uses exactly the same generalised variance decomposition as the cross-market
network, with the country composites as the nodes — that is what makes the two
layers comparable.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, HTTPException

from jindun_api.schemas import SpilloverResponse
from jindun_api.store import ArtifactStore

router = APIRouter(prefix="/global", tags=["global"])


def get_store() -> ArtifactStore:
    return ArtifactStore()


def _global_root(store: ArtifactStore) -> Path:
    return store.root / "global"


def _load(store: ArtifactStore, name: str) -> dict[str, Any]:
    path = _global_root(store) / name
    if not path.exists():
        raise HTTPException(
            status_code=404,
            detail=(
                f"the global artefact {name!r} has not been produced yet; "
                "run the global layer of the pipeline first"
            ),
        )
    return json.loads(path.read_text(encoding="utf-8"))


@router.get("/spillover", response_model=SpilloverResponse)
def global_spillover(store: ArtifactStore = Depends(get_store)) -> SpilloverResponse:
    """The cross-country spillover network."""
    block = _load(store, "spillover.json")
    return SpilloverResponse(
        scope=block.get("scope", "global"),
        nodes=block.get("nodes") or [],
        matrix=block.get("matrix") or [],
        total_spillout=block.get("total_spillout") or {},
        total_spillin=block.get("total_spillin") or {},
        net=block.get("net") or {},
        horizon=int(block.get("horizon", 10)),
        method=block.get("method", "paper_equation"),
        var_order=block.get("var_order"),
        window=block.get("window"),
        notes=block.get("notes") or [],
    )


@router.get("/gsib")
def gsib_list(store: ArtifactStore = Depends(get_store)) -> dict[str, Any]:
    """The global systemically important banks and their buckets."""
    return _load(store, "gsib.json")


@router.get("/cycle")
def global_cycle(store: ArtifactStore = Depends(get_store)) -> dict[str, Any]:
    """The global cycle factor extracted from the country composites."""
    return _load(store, "cycle.json")


@router.get("/banking-network")
def banking_network(store: ArtifactStore = Depends(get_store)) -> dict[str, Any]:
    """The cross-border banking network built from the BIS locational statistics."""
    return _load(store, "banking_network.json")
