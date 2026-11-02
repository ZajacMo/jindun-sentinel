"""Adapter for the BIS Statistical API and the BIS bulk downloads.

The BIS publishes its statistics through an SDMX 2.1 service at
``stats.bis.org``.  Two practical details dominate this adapter and both were
verified against the live service:

**The key must be part of the path, not a query parameter.**  A request of the
form ``/api/v1/data/WS_LBS_D_PUB?key=...`` *silently ignores* the key and
returns the whole flow — 25 MB for a single quarter of the locational banking
statistics.  The correct form is::

    /api/v1/data/{flow}/{key}?startPeriod=...&endPeriod=...&format=csvfile

which returns 358 bytes for the same query.  Every request this adapter makes
uses the path form.

**Only the v1 API exists.**  The v2 paths answer 404 or 501, and requesting
``application/vnd.sdmx.structure+json`` returns 406 — the structure endpoint
answers SDMX-ML (XML) and that is what is parsed here.
"""

from __future__ import annotations

import csv
import datetime as dt
import io
from typing import Any, Iterable
from xml.etree import ElementTree as ET

from .base import FetchResult, HttpClient, SnapshotStore

__all__ = ["BisAdapter", "BIS_API_BASE", "BIS_BULK_BASE", "LBS_DSD_KEY_ORDER"]

BIS_API_BASE = "https://stats.bis.org/api/v1"
BIS_BULK_BASE = "https://data.bis.org/static/bulk"

#: The dimension order of the locational banking statistics key.
LBS_DSD_KEY_ORDER = (
    "FREQ",
    "L_MEASURE",
    "L_POSITION",
    "L_INSTR",
    "L_DENOM",
    "L_CURR_TYPE",
    "L_PARENT_CTY",
    "L_REP_BANK_TYPE",
    "L_REP_CTY",
    "L_CP_SECTOR",
    "L_CP_COUNTRY",
    "L_POS_TYPE",
)

#: Flows this project actually uses.  The full list (56 flows) is available
#: from ``/api/v1/dataflow/BIS``.
KNOWN_FLOWS = (
    "WS_LBS_D_PUB",
    "WS_LBS_PUB",
    "WS_CBS_PUB",
    "WS_GLI",
    "WS_CREDIT_GAP",
    "WS_DSR",
    "WS_EER",
    "WS_XRU",
    "WS_OTC_DERIV2",
    "WS_CPP",
)

_SDMX_NS = "{http://www.sdmx.org/resources/sdmxml/schemas/v2_1/structure}"
_COMMON_NS = "{http://www.sdmx.org/resources/sdmxml/schemas/v2_1/common}"
_MESSAGE_NS = "{http://www.sdmx.org/resources/sdmxml/schemas/v2_1/message}"


def _parse_csv(payload: bytes) -> list[dict[str, str]]:
    text = payload.decode("utf-8-sig", errors="replace")
    reader = csv.DictReader(io.StringIO(text))
    return [dict(row) for row in reader]


class BisAdapter:
    """Read-only client for the BIS statistical service."""

    name = "bis"

    def __init__(
        self,
        client: HttpClient | None = None,
        store: SnapshotStore | None = None,
    ) -> None:
        self.client = client or HttpClient()
        self.store = store or SnapshotStore()

    # ------------------------------------------------------------------
    def data_url(
        self,
        flow: str,
        key: str | None = None,
        *,
        start_period: str | None = None,
        end_period: str | None = None,
        format: str = "csvfile",
    ) -> str:
        """Build a BIS data URL using the path-style key."""
        url = f"{BIS_API_BASE}/data/{flow}"
        if key:
            url += f"/{key}"
        query: list[str] = []
        if start_period:
            query.append(f"startPeriod={start_period}")
        if end_period:
            query.append(f"endPeriod={end_period}")
        query.append(f"format={format}")
        return url + "?" + "&".join(query)

    def bulk_url(self, flow: str) -> str:
        """Return the bulk-download URL for a flow."""
        return f"{BIS_BULK_BASE}/{flow}_csv_flat.zip"

    # ------------------------------------------------------------------
    def fetch(
        self,
        flow: str,
        key: str | None = None,
        *,
        series_id: str | None = None,
        country_code: str = "",
        start_period: str | None = None,
        end_period: str | None = None,
        use_cache: bool = True,
    ) -> FetchResult:
        """Fetch a BIS series.

        The response is a CSV whose ``TIME_PERIOD`` column holds the period
        (``2025-Q4`` for quarterly flows, ``2026-10`` for monthly ones) and
        ``OBS_VALUE`` the observation.
        """
        url = self.data_url(
            flow, key, start_period=start_period, end_period=end_period
        )
        identifier = series_id or f"bis.{flow.lower()}.{(key or 'all').lower().replace('.', '_')}"

        payload = self._read(identifier, url, use_cache=use_cache)
        if payload is None:
            return FetchResult(
                adapter=self.name,
                series_id=identifier,
                country_code=country_code,
                source_url=url,
                warnings=["the BIS service did not return data for this key"],
            )

        rows = _parse_csv(payload)
        observations: list[tuple[dt.date, float]] = []
        for row in rows:
            period = (row.get("TIME_PERIOD") or "").strip()
            value = (row.get("OBS_VALUE") or "").strip()
            moment = _parse_period(period)
            if moment is None or not value:
                continue
            try:
                observations.append((moment, float(value)))
            except ValueError:
                continue
        observations.sort(key=lambda item: item[0])

        from ..models import Observation

        metadata = self.store.metadata(self.name, identifier) or {}
        return FetchResult(
            adapter=self.name,
            series_id=identifier,
            country_code=country_code,
            observations=tuple(
                Observation(date=day, value=value) for day, value in observations
            ),
            source_url=url,
            retrieved_at=str(metadata.get("retrieved_at", "")),
            vintage=str(metadata.get("retrieved_at", "")) or None,
            unit=str(rows[0].get("UNIT_MEASURE", "")) if rows else "",
            frequency="Q" if rows and "Q" in str(rows[0].get("FREQ", "")) else "M",
            warnings=[],
            extra={"flow": flow, "key": key or "", "rows": len(rows)},
        )

    # ------------------------------------------------------------------
    def flows(self, *, use_cache: bool = True) -> list[str]:
        """List the data flows published by the service.

        The structure endpoint answers SDMX-ML; requesting the JSON
        representation returns 406, so the XML is parsed instead.
        """
        url = f"{BIS_API_BASE}/dataflow/BIS"
        payload = self._read("__dataflow__", url, use_cache=use_cache)
        if payload is None:
            return list(KNOWN_FLOWS)
        try:
            root = ET.fromstring(payload)
        except ET.ParseError:
            return list(KNOWN_FLOWS)

        found: list[str] = []
        for element in root.iter(f"{_SDMX_NS}Dataflow"):
            identifier = element.get("id")
            if identifier:
                found.append(identifier)
        if not found:
            for element in root.iter(f"{_COMMON_NS}StructureUsage"):
                ref = element.get("ref")
                if ref:
                    found.append(ref)
        return sorted(set(found)) or list(KNOWN_FLOWS)

    # ------------------------------------------------------------------
    def lbs_key(
        self,
        *,
        parent_country: str,
        counterparty_country: str,
        instrument: str = "G",
        measure: str = "S",
        position: str = "C",
        denominator: str = "A",
        currency: str = "GBP",
        rep_bank_type: str = "A",
        rep_country: str = "5A",
        cp_sector: str = "A",
        cp_country: str = "5J",
        pos_type: str = "N",
        frequency: str = "Q",
    ) -> str:
        """Assemble a locational banking statistics key.

        The dimension order is fixed by the data structure definition and is
        exported as :data:`LBS_DSD_KEY_ORDER`.
        """
        values = {
            "FREQ": frequency,
            "L_MEASURE": measure,
            "L_POSITION": position,
            "L_INSTR": instrument,
            "L_DENOM": denominator,
            "L_CURR_TYPE": currency,
            "L_PARENT_CTY": parent_country,
            "L_REP_BANK_TYPE": rep_bank_type,
            "L_REP_CTY": rep_country,
            "L_CP_SECTOR": cp_sector,
            "L_CP_COUNTRY": cp_country,
            "L_POS_TYPE": pos_type,
        }
        return ".".join(values[dimension] for dimension in LBS_DSD_KEY_ORDER)

    # ------------------------------------------------------------------
    def _read(self, series_id: str, url: str, *, use_cache: bool) -> bytes | None:
        if use_cache:
            cached = self.store.read(self.name, series_id)
            if cached is not None:
                return cached
        try:
            response = self.client.get(url)
        except Exception:  # noqa: BLE001
            return None
        self.store.write(
            self.name, series_id, response.body, url=url, retrieved_at=response.retrieved_at
        )
        return response.body

    @staticmethod
    def known_flows() -> Iterable[str]:
        return KNOWN_FLOWS


def _parse_period(period: str) -> dt.date | None:
    text = period.strip()
    if not text:
        return None
    if "Q" in text:
        year, _, quarter = text.partition("-Q")
        try:
            month = (int(quarter) - 1) * 3 + 1
            return dt.date(int(year), month, 1)
        except (TypeError, ValueError):
            return None
    if "-" in text:
        year, _, month = text.partition("-")
        try:
            return dt.date(int(year), int(month), 1)
        except (TypeError, ValueError):
            return None
    try:
        return dt.date(int(text), 1, 1)
    except ValueError:
        return None
