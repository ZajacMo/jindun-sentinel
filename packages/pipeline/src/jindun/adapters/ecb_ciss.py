"""Adapter for the ECB Composite Indicator of Systemic Stress (CISS).

The ECB publishes a daily and a monthly CISS for a fixed set of reference
areas.  The service is an SDMX 2.1 endpoint that answers with CSV.

Coverage is **not** universal and the gaps matter:

* the daily composite ``SS_CIN`` covers AT, BE, CN, DE, ES, FI, FR, GB, IE,
  IT, NL, PT, U2 (euro area) and US;
* the monthly composite ``SS_CI`` exists only for U2 and US;
* the *component* series (the five sub-stresses) exist only for the euro area
  and only as ``.CON`` contributions — the ``.IDX`` variant of a component
  does not exist and answers 404;
* **Japan is not covered at all.**  Every Japanese reference area answers
  404 on both the daily and the monthly frequency.  The Japanese country
  configuration therefore has no CISS anchor and says so explicitly; the
  Bank of Japan adapter is the substitute, and the methodology pages state
  that the Japanese composite has no official cross-check anchor.

Every one of those statements was verified against the live service.
"""

from __future__ import annotations

import csv
import datetime as dt
import io
from collections.abc import Iterable

from .base import FetchResult, HttpClient, SnapshotStore

__all__ = [
    "EcbCissAdapter",
    "CISS_DAILY_AREAS",
    "CISS_MONTHLY_AREAS",
    "CISS_COMPONENT_AREAS",
    "CISS_COMPONENTS",
    "ECB_CISS_BASE",
]

ECB_CISS_BASE = "https://data-api.ecb.europa.eu/service/data/CISS"

CISS_DAILY_AREAS = (
    "AT", "BE", "CN", "DE", "ES", "FI", "FR", "GB", "IE", "IT", "NL", "PT", "U2", "US",
)
CISS_MONTHLY_AREAS = ("U2", "US")
CISS_COMPONENT_AREAS = ("U2",)
CISS_COMPONENTS = (
    "CREDIT", "EQUITY", "INTERBANK", "REAL_ESTATE", "SOVEREIGN",
)


def _parse_csv(payload: bytes) -> list[tuple[str, float]]:
    text = payload.decode("utf-8-sig", errors="replace")
    reader = csv.DictReader(io.StringIO(text))
    rows: list[tuple[str, float]] = []
    for row in reader:
        period = (row.get("TIME_PERIOD") or "").strip()
        value = (row.get("OBS_VALUE") or "").strip()
        if not period or not value:
            continue
        try:
            rows.append((period, float(value)))
        except ValueError:
            continue
    return rows


def _to_date(period: str) -> dt.date | None:
    text = period.strip()
    for fmt in ("%Y-%m-%d", "%Y-%m-%dT%H:%M:%S", "%Y-%m"):
        try:
            return dt.datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    return None


class EcbCissAdapter:
    """Read-only client for the ECB CISS data service."""

    name = "ecb_ciss"

    def __init__(
        self,
        client: HttpClient | None = None,
        store: SnapshotStore | None = None,
    ) -> None:
        self.client = client or HttpClient()
        self.store = store or SnapshotStore()

    # ------------------------------------------------------------------
    def url_for(
        self,
        area: str,
        *,
        frequency: str = "D",
        series: str = "SS_CIN",
        variant: str = "IDX",
        observations: int | None = None,
    ) -> str:
        parts = [
            ECB_CISS_BASE,
            ".".join(
                [frequency, area, "Z0Z", "4F", "EC", series, variant]
            ),
        ]
        url = "/".join(parts)
        query = "?format=csvdata&detail=dataonly"
        if observations:
            query += f"&lastNObservations={int(observations)}"
        return url + query

    # ------------------------------------------------------------------
    def fetch_composite(
        self,
        area: str,
        *,
        country_code: str | None = None,
        frequency: str = "D",
        observations: int | None = None,
        use_cache: bool = True,
    ) -> FetchResult:
        """Fetch the composite CISS index for one reference area.

        ``frequency`` is ``"D"`` (daily, ``SS_CIN``) or ``"M"`` (monthly,
        ``SS_CI``).
        """
        if frequency.upper() == "D":
            series, areas = "SS_CIN", CISS_DAILY_AREAS
        elif frequency.upper() == "M":
            series, areas = "SS_CI", CISS_MONTHLY_AREAS
        else:
            raise ValueError(f"unsupported CISS frequency: {frequency!r}")

        warnings: list[str] = []
        if area not in areas:
            warnings.append(
                f"the ECB CISS service does not publish a {frequency} composite for "
                f"reference area {area}; the request is expected to fail"
            )

        series_id = f"ecb_ciss.{series.lower()}.{area.lower()}"
        url = self.url_for(
            area, frequency=frequency.upper(), series=series, observations=observations
        )
        payload = self._read(series_id, url, use_cache=use_cache)
        if payload is None:
            return FetchResult(
                adapter=self.name,
                series_id=series_id,
                country_code=country_code or area,
                source_url=url,
                warnings=[*warnings, "the ECB CISS service did not return data for this key"],
            )

        rows = _parse_csv(payload)
        parsed: list[tuple[dt.date, float]] = []
        for period, value in rows:
            moment = _to_date(period)
            if moment is not None:
                parsed.append((moment, value))
        parsed.sort(key=lambda item: item[0])

        from ..models import Observation

        observations = tuple(Observation(date=day, value=value) for day, value in parsed)
        metadata = self.store.metadata(self.name, series_id) or {}
        return FetchResult(
            adapter=self.name,
            series_id=series_id,
            country_code=country_code or area,
            observations=observations,
            source_url=url,
            retrieved_at=str(metadata.get("retrieved_at", "")),
            vintage=str(metadata.get("retrieved_at", "")) or None,
            unit="index",
            frequency="D" if frequency.upper() == "D" else "M",
            warnings=warnings,
            cached=bool(metadata.get("cached", False)),
            extra={"reference_area": area, "ciss_series": series},
        )

    # ------------------------------------------------------------------
    def fetch_components(
        self,
        area: str = "U2",
        *,
        country_code: str | None = None,
        use_cache: bool = True,
    ) -> list[FetchResult]:
        """Fetch the five euro-area sub-stress contributions.

        Components exist only as ``.CON`` contribution series; the ``.IDX``
        variant does not exist and answers 404.
        """
        results: list[FetchResult] = []
        for component in CISS_COMPONENTS:
            series_id = f"ecb_ciss.con.{component.lower()}.{area.lower()}"
            url = self.url_for(
                area, frequency="D", series=f"{component}_CON", variant="CON"
            )
            payload = self._read(series_id, url, use_cache=use_cache)
            warnings: list[str] = []
            if payload is None:
                warnings.append("no contribution series returned by the ECB service")
                results.append(
                    FetchResult(
                        adapter=self.name,
                        series_id=series_id,
                        country_code=country_code or area,
                        source_url=url,
                        warnings=warnings,
                        extra={"reference_area": area, "ciss_component": component},
                    )
                )
                continue

            from ..models import Observation

            parsed: list[tuple[dt.date, float]] = []
            for period, value in _parse_csv(payload):
                moment = _to_date(period)
                if moment is not None:
                    parsed.append((moment, value))
            parsed.sort(key=lambda item: item[0])
            metadata = self.store.metadata(self.name, series_id) or {}
            results.append(
                FetchResult(
                    adapter=self.name,
                    series_id=series_id,
                    country_code=country_code or area,
                    observations=tuple(
                        Observation(date=day, value=value) for day, value in parsed
                    ),
                    source_url=url,
                    retrieved_at=str(metadata.get("retrieved_at", "")),
                    unit="contribution",
                    frequency="D",
                    warnings=warnings,
                    extra={"reference_area": area, "ciss_component": component},
                )
            )
        return results

    # ------------------------------------------------------------------
    def _read(self, series_id: str, url: str, *, use_cache: bool) -> bytes | None:
        if use_cache:
            cached = self.store.read(self.name, series_id)
            if cached is not None:
                return cached
        try:
            response = self.client.get(url)
        except Exception:  # noqa: BLE001 - a missing series must not kill the run
            return None
        self.store.write(self.name, series_id, response.body, url=url, retrieved_at=response.retrieved_at)
        return response.body

    @staticmethod
    def covered_areas() -> Iterable[str]:
        return CISS_DAILY_AREAS
