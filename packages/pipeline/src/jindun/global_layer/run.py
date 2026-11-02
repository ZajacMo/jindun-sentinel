"""Run the global layer and write its artefacts.

The global layer is produced *after* the country layer, because it is built
from the country composites: the cross-country network uses them as its nodes
and the global cycle factor is their first principal component.  Nothing is
recomputed here that the country runs already produced, and nothing is
invented: a country without a run artefact simply does not enter the network.

The four artefacts are exactly the ones the API serves:

``spillover.json``
    The cross-country contagion network.
``cycle.json``
    The global cycle factor with its loadings and explained variance.
``banking_network.json``
    The cross-border banking network from the BIS locational statistics.
``gsib.json``
    The FSB list of global systemically important banks.
"""

from __future__ import annotations

import datetime as dt
import json
from collections.abc import Iterable, Sequence
from pathlib import Path
from typing import Any

import pandas as pd

from ..adapters.fsb import FsbAdapter
from ..config import Settings
from ..contagion import GVDSpec
from .banking_network import BIS_AREA_CODES, load_banking_network
from .cross_country import cross_country_spillover_all
from .cycle import extract_cycle_factor

__all__ = [
    "load_country_composites",
    "run_global_layer",
    "GLOBAL_ARTEFACTS",
]

GLOBAL_ARTEFACTS = ("spillover", "cycle", "banking_network", "gsib")


def load_country_composites(
    runs_dir: str | Path,
    codes: Iterable[str],
    *,
    lens: str = "percentile",
) -> dict[str, pd.Series]:
    """Load the published composite of every country that has a run artefact.

    The series are read back from ``run.json`` rather than recomputed, so the
    global layer and the country layer can never disagree about a number.
    """
    root = Path(runs_dir)
    composites: dict[str, pd.Series] = {}
    for code in codes:
        path = root / code / "run.json"
        if not path.exists():
            continue
        payload = json.loads(path.read_text(encoding="utf-8"))
        points = payload.get(lens) or []
        if not points:
            continue
        series = pd.Series(
            [float(point["value"]) for point in points],
            index=pd.to_datetime([point["date"] for point in points]),
            name=code,
        )
        series = series[~series.index.duplicated(keep="last")].sort_index()
        if not series.empty:
            composites[code] = series
    return composites


def _banking_network_payload(
    snapshot: str | Path,
    *,
    countries: Sequence[str] | None,
) -> dict[str, Any]:
    """Build the cross-border banking network from the BIS snapshot."""
    wanted: set[str] | None = None
    if countries:
        wanted = {BIS_AREA_CODES.get(code, code) for code in countries}
        wanted |= {BIS_AREA_CODES.get(code, code) for code in countries}
    network = load_banking_network(snapshot, countries=wanted)
    payload = network.to_payload()
    payload["countries"] = list(countries or [])
    payload["source"] = (
        "BIS locational banking statistics (WS_LBS_D_PUB): loans and deposits, "
        "US dollars, all counterparty sectors"
    )
    return payload


def _gsib_payload(adapter: FsbAdapter, *, use_cache: bool) -> dict[str, Any]:
    """Build the G-SIB artefact."""
    result = adapter.fetch_gsib_list(use_cache=use_cache)
    banks = result.extra.get("banks") or []
    histogram: dict[str, int] = {}
    for bank in banks:
        key = str(bank.get("bucket", "?"))
        histogram[key] = histogram.get(key, 0) + 1
    return {
        "banks": banks,
        "count": len(banks),
        "bucket_histogram": dict(sorted(histogram.items())),
        "source_url": result.source_url,
        "retrieved_at": result.retrieved_at,
        "warnings": list(result.warnings),
    }


def run_global_layer(
    settings: Settings,
    out_dir: str | Path,
    *,
    runs_dir: str | Path | None = None,
    countries: Sequence[str] | None = None,
    banking_snapshot: str | Path | None = None,
    use_cache: bool = True,
) -> dict[str, str]:
    """Produce the global artefacts and return the paths that were written."""
    from .. import paths

    root = Path(out_dir)
    root.mkdir(parents=True, exist_ok=True)
    source_runs = Path(runs_dir) if runs_dir else paths.runs_dir()
    written: dict[str, str] = {}
    warnings: list[str] = []

    codes = list(countries) if countries else [c.code for c in settings.enabled_countries()]
    composites = load_country_composites(source_runs, codes)

    # 1. Cross-country contagion ------------------------------------------
    if len(composites) >= 2:
        try:
            spec = GVDSpec(
                method=settings.contagion.method,
                horizon=settings.contagion.horizon,
                var_order=settings.contagion.var_order,
                criterion=settings.contagion.criterion,
                max_order=settings.contagion.max_order,
                transform=settings.contagion.transform,
            )
            networks = cross_country_spillover_all(
                composites,
                spec,
                methods=settings.contagion.publish_methods,
            )
            default = networks.results.get(spec.method)
            if default is None and networks.results:
                default = next(iter(networks.results.values()))
            payload = default.to_payload() if default is not None else {}
            payload["default_method"] = default.method if default is not None else spec.method
            payload.update(networks.to_payload())
        except Exception as exc:  # noqa: BLE001
            payload = {"scope": "global", "nodes": [], "matrix": [], "notes": [str(exc)]}
            warnings.append(f"the cross-country network could not be computed: {exc}")
    else:
        payload = {
            "scope": "global",
            "nodes": [],
            "matrix": [],
            "notes": [
                "at least two country runs are required for a cross-country network; "
                f"found {len(composites)}"
            ],
        }
        warnings.append("the cross-country network needs at least two country runs")
    path = root / "spillover.json"
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    written["spillover"] = str(path)

    # 2. Global cycle factor ---------------------------------------------
    cycle = extract_cycle_factor(composites)
    cycle_payload = cycle.to_payload()
    cycle_payload["countries"] = sorted(composites)
    cycle_payload["generated_at"] = dt.datetime.now(dt.UTC).isoformat()
    path = root / "cycle.json"
    path.write_text(json.dumps(cycle_payload, ensure_ascii=False, indent=2), encoding="utf-8")
    written["cycle"] = str(path)

    # 3. Cross-border banking network ------------------------------------
    snapshot = (
        Path(banking_snapshot)
        if banking_snapshot
        else (paths.snapshot_dir() / "bis" / "lbs_bilateral.csv")
    )
    if snapshot.exists():
        try:
            payload = _banking_network_payload(snapshot, countries=codes)
        except Exception as exc:  # noqa: BLE001
            payload = {"edges": [], "nodes": {}, "notes": [str(exc)]}
            warnings.append(f"the banking network could not be built: {exc}")
    else:
        payload = {
            "edges": [],
            "nodes": {},
            "notes": [
                "the BIS bilateral snapshot is missing; run "
                "scripts/extract_bis_network.py to create it"
            ],
        }
        warnings.append("the BIS bilateral snapshot is missing")
    path = root / "banking_network.json"
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    written["banking_network"] = str(path)

    # 4. G-SIB list --------------------------------------------------------
    try:
        payload = _gsib_payload(FsbAdapter(), use_cache=use_cache)
        extra = payload.get("warnings")
        if isinstance(extra, list):
            warnings.extend(str(item) for item in extra)
    except Exception as exc:  # noqa: BLE001
        payload = {"banks": [], "count": 0, "warnings": [str(exc)]}
        warnings.append(f"the G-SIB list could not be fetched: {exc}")
    path = root / "gsib.json"
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    written["gsib"] = str(path)

    return written
