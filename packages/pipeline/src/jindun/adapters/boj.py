"""Adapter for the Bank of Japan Time-Series Statistics Search Site API.

The BOJ published an official, key-free API in February 2026.  It is a plain
JSON service under ``/api/v1`` with three resources:

``getMetadata``
    The series catalogue of one database (code, name, unit, frequency, layer).
``getDataCode``
    Observations for up to 250 series codes.
``getDataLayer``
    Observations for a whole layer of the hierarchy (up to 1 250 series).

All three were verified against the live service.  The details that matter:

* the response wraps the data in ``RESULTSET``; every element carries
  ``SERIES_CODE``, ``FREQUENCY`` and a ``VALUES`` object with
  ``SURVEY_DATES`` and ``VALUES`` arrays;
* ``SURVEY_DATES`` are ``YYYYMMDD`` integers for daily series, ``YYYYMM`` for
  monthly and ``YYYYQQ`` for quarterly series;
* pagination is driven by ``NEXTPOSITION``, which has to be echoed back as
  ``startPosition``;
* the BOJ asks clients not to hammer the service, so the adapter applies a
  minimum delay between requests.

Japan has no entry in the ECB CISS, so this adapter is what the Japanese
country configuration falls back on — and the methodology pages say so.
"""

from __future__ import annotations

import datetime as dt
import json
import time
from dataclasses import dataclass
from typing import Any, Iterable

from .base import FetchResult, HttpClient, SnapshotStore

__all__ = ["BojAdapter", "BojSeriesMeta", "BOJ_API_BASE"]

BOJ_API_BASE = "https://www.stat-search.boj.or.jp/api/v1"

#: Databases this project uses.  The full catalogue is available from the
#: BOJ data search site.
KNOWN_DATABASES = {
    "IR01": "Official discount rate and basic loan rate",
    "FM01": "Uncollateralised overnight call rate (daily)",
    "FM08": "Foreign exchange market conditions",
    "FM09": "Effective exchange rate",
    "MD01": "Monetary base",
    "MD02": "Money stock",
    "PR01": "Corporate goods price index",
    "CO": "Tankan (Short-term Economic Survey of Enterprises)",
    "BP01": "Balance of payments statistics",
    "BIS": "BIS international banking and credit statistics (Japan)",
}


@dataclass(frozen=True, slots=True)
class BojSeriesMeta:
    """Metadata of one BOJ series."""

    code: str
    name: str
    unit: str = ""
    frequency: str = ""
    category: str = ""
    start: str = ""
    end: str = ""
    last_update: str = ""


class BojAdapter:
    """Read-only client for the Bank of Japan statistics API."""

    name = "boj"

    def __init__(
        self,
        client: HttpClient | None = None,
        store: SnapshotStore | None = None,
        *,
        min_interval_seconds: float = 1.0,
    ) -> None:
        self.client = client or HttpClient()
        self.store = store or SnapshotStore()
        self._min_interval = max(0.0, min_interval_seconds)
        self._last_request = 0.0

    # ------------------------------------------------------------------
    def metadata(
        self,
        database: str,
        *,
        language: str = "en",
        use_cache: bool = True,
    ) -> list[BojSeriesMeta]:
        """Return the series catalogue of ``database``."""
        url = f"{BOJ_API_BASE}/getMetadata?db={database.upper()}&lang={language}"
        payload = self._read(f"metadata.{database.upper()}", url, use_cache=use_cache)
        if payload is None:
            return []
        try:
            document = json.loads(payload.decode("utf-8"))
        except (ValueError, UnicodeDecodeError):
            return []

        entries: list[BojSeriesMeta] = []
        for item in document.get("RESULTSET", []) or []:
            code = str(item.get("SERIES_CODE") or "").strip()
            if not code:
                continue
            entries.append(
                BojSeriesMeta(
                    code=code,
                    name=str(item.get("NAME_OF_TIME_SERIES") or ""),
                    unit=str(item.get("UNIT") or ""),
                    frequency=str(item.get("FREQUENCY") or ""),
                    category=str(item.get("CATEGORY") or ""),
                    start=str(item.get("START_OF_THE_TIME_SERIES") or ""),
                    end=str(item.get("END_OF_THE_TIME_SERIES") or ""),
                    last_update=str(item.get("LAST_UPDATE") or ""),
                )
            )
        return entries

    # ------------------------------------------------------------------
    def fetch(
        self,
        database: str,
        codes: Iterable[str],
        *,
        country_code: str = "JP",
        start_date: str | None = None,
        end_date: str | None = None,
        language: str = "en",
        use_cache: bool = True,
    ) -> list[FetchResult]:
        """Fetch one or more BOJ series.

        The BOJ accepts at most 250 series codes per request; longer lists are
        split into batches automatically and the pagination cursor is followed
        until the service stops returning a next position.
        """
        wanted = [code.strip() for code in codes if code.strip()]
        if not wanted:
            return []

        results: list[FetchResult] = []
        for batch in _batches(wanted, 250):
            results.extend(
                self._fetch_batch(
                    database,
                    batch,
                    country_code=country_code,
                    start_date=start_date,
                    end_date=end_date,
                    language=language,
                    use_cache=use_cache,
                )
            )
        return results

    # ------------------------------------------------------------------
    def _fetch_batch(
        self,
        database: str,
        codes: list[str],
        *,
        country_code: str,
        start_date: str | None,
        end_date: str | None,
        language: str,
        use_cache: bool,
    ) -> list[FetchResult]:
        from urllib.parse import urlencode

        identifier = f"{database.upper()}.{'-'.join(codes)}"
        collected: dict[str, dict[str, Any]] = {}
        metadata_by_code: dict[str, BojSeriesMeta] = {}
        start_position: str | None = None
        url = ""

        for _ in range(50):  # pagination guard
            params = {
                "db": database.upper(),
                "code": ",".join(codes),
                "lang": language,
            }
            if start_date:
                params["startDate"] = start_date
            if end_date:
                params["endDate"] = end_date
            if start_position:
                params["startPosition"] = start_position
            url = f"{BOJ_API_BASE}/getDataCode?{urlencode(params)}"

            payload = self._read(identifier, url, use_cache=use_cache and start_position is None)
            if payload is None:
                break
            try:
                document = json.loads(payload.decode("utf-8"))
            except (ValueError, UnicodeDecodeError):
                break

            for item in document.get("RESULTSET", []) or []:
                code = str(item.get("SERIES_CODE") or "").strip()
                if not code:
                    continue
                metadata_by_code.setdefault(
                    code,
                    BojSeriesMeta(
                        code=code,
                        name=str(item.get("NAME_OF_TIME_SERIES") or ""),
                        unit=str(item.get("UNIT") or ""),
                        frequency=str(item.get("FREQUENCY") or ""),
                        category=str(item.get("CATEGORY") or ""),
                        last_update=str(item.get("LAST_UPDATE") or ""),
                    ),
                )
                values = item.get("VALUES") or {}
                dates = values.get("SURVEY_DATES") or []
                numbers = values.get("VALUES") or []
                bucket = collected.setdefault(code, {"dates": [], "values": []})
                bucket["dates"].extend(dates)
                bucket["values"].extend(numbers)

            next_position = document.get("NEXTPOSITION")
            if not next_position:
                break
            start_position = str(next_position)

        results: list[FetchResult] = []
        for code, bucket in collected.items():
            meta = metadata_by_code.get(code, BojSeriesMeta(code=code, name=""))
            observations = _to_observations(bucket["dates"], bucket["values"])
            results.append(
                FetchResult(
                    adapter=self.name,
                    series_id=f"boj.{database.lower()}.{code.lower()}",
                    country_code=country_code,
                    observations=observations,
                    source_url=url,
                    unit=meta.unit,
                    frequency=_frequency_code(meta.frequency),
                    vintage=meta.last_update or None,
                    extra={"database": database.upper(), "series_code": code, "name": meta.name},
                )
            )
        results.sort(key=lambda item: item.series_id)
        return results

    # ------------------------------------------------------------------
    def _read(self, series_id: str, url: str, *, use_cache: bool) -> bytes | None:
        if use_cache:
            cached = self.store.read(self.name, series_id)
            if cached is not None:
                return cached
        self._throttle()
        try:
            response = self.client.get(url)
        except Exception:  # noqa: BLE001
            return None
        self.store.write(
            self.name, series_id, response.body, url=url, retrieved_at=response.retrieved_at
        )
        return response.body

    def _throttle(self) -> None:
        elapsed = time.monotonic() - self._last_request
        if elapsed < self._min_interval:
            time.sleep(self._min_interval - elapsed)
        self._last_request = time.monotonic()


def _batches(items: list[str], size: int) -> Iterable[list[str]]:
    for index in range(0, len(items), size):
        yield items[index : index + size]


def _to_observations(dates: Iterable[Any], values: Iterable[Any]) -> tuple:
    from ..models import Observation

    numbers = list(values)
    observations: list[Observation] = []
    for position, raw_date in enumerate(dates):
        if position >= len(numbers):
            break
        moment = _parse_boj_date(raw_date)
        if moment is None:
            continue
        value = numbers[position]
        if value is None or value == "":
            continue
        try:
            observations.append(Observation(date=moment, value=float(value)))
        except (TypeError, ValueError):
            continue
    observations.sort(key=lambda item: item.date)
    return tuple(observations)


def _parse_boj_date(raw: Any) -> dt.date | None:
    if raw is None:
        return None
    text = str(raw).strip()
    if not text:
        return None
    if len(text) == 8 and text.isdigit():
        try:
            return dt.date(int(text[:4]), int(text[4:6]), int(text[6:8]))
        except ValueError:
            return None
    if len(text) == 6 and text.isdigit():
        try:
            return dt.date(int(text[:4]), int(text[4:6]), 1)
        except ValueError:
            return None
    if len(text) == 4 and text.isdigit():
        try:
            return dt.date(int(text), 1, 1)
        except ValueError:
            return None
    return None


def _frequency_code(raw: str) -> str:
    upper = raw.upper()
    if "DAILY" in upper:
        return "D"
    if "WEEKLY" in upper:
        return "W"
    if "MONTHLY" in upper:
        return "M"
    if "QUARTERLY" in upper:
        return "Q"
    if "SEMI" in upper:
        return "H"
    if "ANNUAL" in upper:
        return "Y"
    return ""
