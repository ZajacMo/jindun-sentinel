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
    The global financial cycle factor estimated from the BIS global liquidity,
    credit-gap and exchange-rate data, with the country-panel factor kept as
    its cross-check.
``banking_network.json``
    The cross-border banking network from the BIS locational statistics.
``gsib.json``
    The FSB list of global systemically important banks.
"""

from __future__ import annotations

import datetime as dt
import json
from collections.abc import Iterable, Mapping, Sequence
from pathlib import Path
from typing import Any

import pandas as pd

from ..adapters.fsb import FsbAdapter
from ..config import Settings
from ..contagion import GVDSpec
from ..models import Message
from .banking_network import BIS_AREA_CODES, load_banking_network
from .bis_cycle import build_cycle_inputs
from .cross_country import cross_country_spillover_all
from .cycle import build_global_cycle, extract_cycle_factor

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


def _cycle_payload(
    settings: Settings,
    composites: Mapping[str, pd.Series],
    *,
    use_cache: bool = True,
) -> dict[str, Any]:
    """Build the global financial cycle factor and its cross-check.

    The factor comes from the BIS inputs.  When they cannot be read the
    artefact still carries the country-panel factor, but the failure is
    stated rather than hidden: a missing factor must never look like a
    factor that happens to be flat.
    """
    params = settings.cycle
    source = (
        "BIS global liquidity indicators (WS_GLI), credit-to-GDP gaps "
        "(WS_CREDIT_GAP) and effective exchange rates (WS_EER)"
    )
    if not params.enabled:
        return {
            "dates": [],
            "factor": [],
            "status": "disabled",
            "notes": [Message("cycle.note.disabled").to_payload()],
        }

    try:
        inputs = build_cycle_inputs(
            credit_gap_economies=params.credit_gap_economies,
            dollar_reference_area=params.dollar_reference_area,
            eer_basket=params.eer_basket,
            use_cache=use_cache,
        )
    except Exception as exc:  # noqa: BLE001
        panel = extract_cycle_factor(composites)
        payload = panel.to_payload()
        payload["status"] = "unavailable"
        payload["source"] = source
        payload["notes"] = [
            Message("cycle.note.inputsUnreadable", {"reason": str(exc)}).to_payload(),
            Message("cycle.note.panelPublishedInstead").to_payload(),
            *[note.to_payload() for note in panel.notes],
        ]
        return payload

    if inputs.observations < params.min_observations:
        panel = extract_cycle_factor(composites)
        payload = panel.to_payload()
        payload["status"] = "unavailable"
        payload["source"] = source
        payload["notes"] = [
            Message(
                "cycle.note.tooFewQuarters",
                {"have": inputs.observations, "need": params.min_observations},
            ).to_payload(),
            Message("cycle.note.panelPublishedInstead").to_payload(),
            *[note.to_payload() for note in inputs.notes],
            *[note.to_payload() for note in panel.notes],
        ]
        return payload

    cycle = build_global_cycle(inputs, composites)
    payload = cycle.to_payload()
    payload["status"] = "estimated"
    payload["source"] = source
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
            payload = {
                "scope": "global",
                "nodes": [],
                "matrix": [],
                "notes": [Message("spillover.note.failed", {"reason": str(exc)}).to_payload()],
            }
    else:
        payload = {
            "scope": "global",
            "nodes": [],
            "matrix": [],
            "notes": [
                Message("spillover.note.needTwoCountries", {"count": len(composites)}).to_payload()
            ],
        }
    path = root / "spillover.json"
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    written["spillover"] = str(path)

    # 2. Global financial cycle factor ------------------------------------
    cycle_payload = _cycle_payload(settings, composites, use_cache=use_cache)
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
            payload = {
                "edges": [],
                "nodes": {},
                "notes": [Message("banking.note.failed", {"reason": str(exc)}).to_payload()],
            }
    else:
        payload = {
            "edges": [],
            "nodes": {},
            "notes": [Message("banking.note.snapshotMissing").to_payload()],
        }
    path = root / "banking_network.json"
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    written["banking_network"] = str(path)

    # 4. G-SIB list --------------------------------------------------------
    try:
        payload = _gsib_payload(FsbAdapter(), use_cache=use_cache)
    except Exception as exc:  # noqa: BLE001
        payload = {"banks": [], "count": 0, "warnings": [str(exc)]}
    path = root / "gsib.json"
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    written["gsib"] = str(path)

    return written
