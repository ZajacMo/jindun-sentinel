"""The cross-border banking network.

The BIS locational banking statistics are the only public measure of **who
lends to whom across borders**.  They are the plumbing under every story about
global financial contagion: a stress episode is not "the euro area is in
trouble", it is "the German and Japanese banks that fund the US and the UK
are the ones that have to be rescued".

Building the network from the BIS data needs one fact that the SDMX service
does not make obvious, and it was verified against the live service:

* the flow ``WS_LBS_D_PUB`` serves the bilateral matrix only in the **bulk
  flat file**.  Through the API the reporting-country dimension only accepts
  the aggregate ``5A`` ("All reporting economies"), so a request for
  ``L_REP_CTY=US`` answers 404 even though the data exists.  The adapter
  therefore reads the bulk archive once and keeps a filtered snapshot of the
  bilateral matrix in the repository.

The dimensions of the key are fixed by the data structure definition::

    FREQ.L_MEASURE.L_POSITION.L_INSTR.L_DENOM.L_CURR_TYPE.L_PARENT_CTY
        .L_REP_BANK_TYPE.L_REP_CTY.L_CP_SECTOR.L_CP_COUNTRY.L_POS_TYPE

``L_PARENT_CTY=5J`` is "All countries" and is the only value the flow accepts
there; ``L_REP_CTY`` is the reporting economy (the lender) and
``L_CP_COUNTRY`` the residence of the counterparty (the borrower), so the
directed edge *lender -> borrower* is exactly ``L_REP_CTY -> L_CP_COUNTRY``.
"""

from __future__ import annotations

import csv
import datetime as dt
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path

__all__ = [
    "BankingEdge",
    "BankingNetwork",
    "build_banking_network",
    "load_banking_network",
    "BIS_AREA_CODES",
    "EURO_AREA_MEMBERS",
]

#: Mapping from the country codes used by this project to the BIS area codes.
#: The euro area is an aggregate in the BIS data (``XM``); when it is not
#: reported as such the member states are added up instead.
BIS_AREA_CODES: Mapping[str, str] = {
    "CN": "CN",
    "US": "US",
    "GB": "GB",
    "JP": "JP",
    "EU": "XM",
}

#: The member states of the euro area, used when the aggregate is missing.
EURO_AREA_MEMBERS: tuple[str, ...] = (
    "AT",
    "BE",
    "CY",
    "DE",
    "EE",
    "ES",
    "FI",
    "FR",
    "GR",
    "HR",
    "IE",
    "IT",
    "LT",
    "LU",
    "LV",
    "MT",
    "NL",
    "PT",
    "SI",
    "SK",
)

#: The positions of the locational banking statistics.
_POSITION_CLAIMS = "C"
_POSITION_LIABILITIES = "L"

#: Aggregate reference areas.  They are published as rows of their own and
#: would otherwise appear as "countries" with an implausible size.
AGGREGATE_CODES = frozenset({"5A", "5J", "XW", "4T", "G2", "1X", "M1"})


@dataclass(frozen=True, slots=True)
class BankingEdge:
    """One directed cross-border banking exposure."""

    source: str
    target: str
    claims: float
    liabilities: float
    as_of: str
    unit: str = "USD"

    @property
    def net(self) -> float:
        """The reporting economy's net position with the counterparty."""
        return self.claims - self.liabilities

    def to_payload(self) -> dict[str, object]:
        return {
            "source": self.source,
            "target": self.target,
            "claims": round(self.claims, 2),
            "liabilities": round(self.liabilities, 2),
            "net": round(self.net, 2),
            "as_of": self.as_of,
            "unit": self.unit,
        }


@dataclass(frozen=True, slots=True)
class BankingNetwork:
    """A snapshot of the cross-border banking network."""

    as_of: str
    edges: tuple[BankingEdge, ...] = ()
    nodes: Mapping[str, Mapping[str, float]] = field(default_factory=dict)
    concentration: Mapping[str, float] = field(default_factory=dict)
    notes: tuple[str, ...] = ()

    def top_sources(self, count: int = 5) -> list[tuple[str, float]]:
        """Return the largest net lenders."""
        ranked = sorted(
            self.nodes.items(),
            key=lambda item: -float(item[1].get("net_exposure", 0.0)),
        )
        return [(code, float(values.get("net_exposure", 0.0))) for code, values in ranked[:count]]

    def top_targets(self, count: int = 5) -> list[tuple[str, float]]:
        """Return the largest net borrowers."""
        ranked = sorted(
            self.nodes.items(),
            key=lambda item: float(item[1].get("net_exposure", 0.0)),
        )
        return [(code, float(values.get("net_exposure", 0.0))) for code, values in ranked[:count]]

    def to_payload(self) -> dict[str, object]:
        return {
            "as_of": self.as_of,
            "edges": [edge.to_payload() for edge in self.edges],
            "nodes": {
                code: {key: round(float(value), 2) for key, value in values.items()}
                for code, values in self.nodes.items()
            },
            "concentration": {
                key: (value if isinstance(value, str) else round(float(value), 6))
                for key, value in self.concentration.items()
            },
            "notes": list(self.notes),
        }


def _aggregate_euro_area(
    records: Mapping[tuple[str, str], dict[str, float]],
) -> dict[tuple[str, str], dict[str, float]]:
    """Fold the euro-area member states into a single node.

    The published euro-area aggregate is dropped first: the member states are
    summed instead, so the aggregate is never counted twice.  Intra-area
    positions are dropped as well — a French bank's claim on a German bank is
    not a cross-border exposure of the euro area to the world, and counting it
    would make the aggregate look more internationally connected than it is.
    """
    members = set(EURO_AREA_MEMBERS)
    folded: dict[tuple[str, str], dict[str, float]] = {}
    for (source, target), values in records.items():
        if source == "XM" or target == "XM":
            continue
        new_source = "XM" if source in members else source
        new_target = "XM" if target in members else target
        if new_source == new_target:
            continue
        bucket = folded.setdefault((new_source, new_target), {"claims": 0.0, "liabilities": 0.0})
        bucket["claims"] += values.get("claims", 0.0)
        bucket["liabilities"] += values.get("liabilities", 0.0)
    return folded


def build_banking_network(
    records: Mapping[tuple[str, str], Mapping[str, float]],
    *,
    as_of: str = "",
    scale: float = 1e6,
    unit: str = "USD",
    fold_euro_area: bool = True,
    notes: Sequence[str] = (),
) -> BankingNetwork:
    """Build a network from a mapping of ``(source, target) -> positions``.

    ``records`` maps the pair of BIS area codes to a mapping with the
    ``claims`` and ``liabilities`` values in the units of the source file.
    ``scale`` converts them into the reporting unit (the BIS publishes the
    locational banking statistics in millions of US dollars).
    """
    working = {key: dict(values) for key, values in records.items()}
    if fold_euro_area:
        working = _aggregate_euro_area(working)

    edges: list[BankingEdge] = []
    for (source, target), values in sorted(working.items()):
        if source == target:
            continue
        edges.append(
            BankingEdge(
                source=source,
                target=target,
                claims=float(values.get("claims", 0.0)) * scale,
                liabilities=float(values.get("liabilities", 0.0)) * scale,
                as_of=as_of,
                unit=unit,
            )
        )

    nodes: dict[str, dict[str, float]] = {}
    for edge in edges:
        source = nodes.setdefault(
            edge.source, {"out_claims": 0.0, "in_liabilities": 0.0, "net_exposure": 0.0}
        )
        target = nodes.setdefault(
            edge.target, {"out_claims": 0.0, "in_liabilities": 0.0, "net_exposure": 0.0}
        )
        source["out_claims"] += edge.claims
        target["in_liabilities"] += edge.liabilities
    for values in nodes.values():
        values["net_exposure"] = values["out_claims"] - values["in_liabilities"]

    total_claims = sum(edge.claims for edge in edges)
    for values in nodes.values():
        values["share_of_network_claims"] = (
            values["out_claims"] / total_claims if total_claims else 0.0
        )

    concentration = _concentration(edges, nodes, total_claims)

    return BankingNetwork(
        as_of=as_of,
        edges=tuple(edges),
        nodes=nodes,
        concentration=concentration,
        notes=tuple(notes),
    )


def _concentration(
    edges: Sequence[BankingEdge],
    nodes: Mapping[str, Mapping[str, float]],
    total_claims: float,
) -> dict[str, float]:
    """Concentration measures of the network."""
    if not edges:
        return {}

    shares = [edge.claims / total_claims for edge in edges if total_claims > 0]
    hhi = sum(share * share for share in shares)

    largest = max(edges, key=lambda edge: edge.claims)
    node_shares = sorted(
        (float(values.get("share_of_network_claims", 0.0)) for values in nodes.values()),
        reverse=True,
    )
    concentration = {
        "hhi_bilateral": hhi,
        "largest_bilateral_share": (largest.claims / total_claims if total_claims else 0.0),
        "top_node_share": node_shares[0] if node_shares else 0.0,
        "edge_count": float(len(edges)),
        "total_claims": total_claims,
    }
    concentration["largest_bilateral_source"] = largest.source
    concentration["largest_bilateral_target"] = largest.target
    return concentration


def load_banking_network(
    path: str | Path,
    *,
    countries: Iterable[str] | None = None,
    scale: float = 1e6,
    measure: str = "all_instruments",
    period: str | None = None,
) -> BankingNetwork:
    """Load a filtered BIS bilateral snapshot and build the network.

    The snapshot is the CSV written by ``scripts/extract_bis_network.py``; its
    columns are the BIS dimension codes plus ``MEASURE`` and ``OBS_VALUE``.
    ``measure`` selects the instrument slice: ``all_instruments`` is the total
    cross-border exposure, ``loans_and_deposits`` the narrower interbank
    channel.

    The network is a *snapshot of one period*: the snapshot holds several
    quarters and summing them would produce a meaningless stock.  ``period``
    defaults to the most recent quarter in the file.
    """
    import math

    wanted = set(countries) if countries else None
    records: dict[tuple[str, str], dict[str, float]] = {}
    unit = "USD"

    rows: list[dict[str, str]] = []
    with Path(path).open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            if measure and (row.get("MEASURE") or "").strip() != measure:
                continue
            rows.append(row)

    if period is None:
        period = max((row.get("TIME_PERIOD") or "").strip() for row in rows) if rows else ""

    for row in rows:
        if (row.get("TIME_PERIOD") or "").strip() != period:
            continue
        source = (row.get("L_REP_CTY") or "").strip()
        target = (row.get("L_CP_COUNTRY") or "").strip()
        if not source or not target:
            continue
        if source in AGGREGATE_CODES or target in AGGREGATE_CODES:
            continue
        if wanted is not None and source not in wanted and target not in wanted:
            continue
        value = (row.get("OBS_VALUE") or "").strip()
        if not value:
            continue
        try:
            amount = float(value)
        except ValueError:
            continue
        if not math.isfinite(amount):
            continue
        unit = (row.get("UNIT_MEASURE") or unit).strip() or unit
        position = (row.get("L_POSITION") or "").strip()
        bucket = records.setdefault((source, target), {"claims": 0.0, "liabilities": 0.0})
        if position == _POSITION_CLAIMS:
            bucket["claims"] += amount
        elif position == _POSITION_LIABILITIES:
            bucket["liabilities"] += amount

    return build_banking_network(records, as_of=period, scale=scale, unit=unit)


def quarter_end(period: str) -> str:
    """Convert a BIS period such as ``2025-Q4`` into an ISO date."""
    text = period.strip()
    if "-Q" in text:
        year, _, quarter = text.partition("-Q")
        try:
            month = int(quarter) * 3
        except ValueError:
            return ""
        day = 31 if month in (3, 12) else 30
        try:
            return dt.date(int(year), month, day).isoformat()
        except ValueError:
            return ""
    return text
