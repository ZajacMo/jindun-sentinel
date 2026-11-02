"""Country level routes."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query

from jindun_api.schemas import (
    AlertListResponse,
    AlertResponse,
    CountryListResponse,
    CountrySummary,
    IndexResponse,
    QualityResponse,
    RegimeBlock,
    SeriesPoint,
    SpilloverResponse,
)
from jindun_api.store import ArtifactStore, RunStoreError

router = APIRouter(prefix="/countries", tags=["countries"])


def get_store() -> ArtifactStore:
    return ArtifactStore()


def _require_run(store: ArtifactStore, code: str) -> dict[str, Any]:
    try:
        return store.run(code)
    except RunStoreError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("", response_model=CountryListResponse)
def list_countries(store: ArtifactStore = Depends(get_store)) -> CountryListResponse:
    """Every country the store holds a run for."""
    summaries: list[CountrySummary] = []
    for code in store.available_countries():
        try:
            payload = store.run(code)
        except RunStoreError:
            continue
        percentile = payload.get("percentile") or []
        deviation = payload.get("deviation") or []
        regime = payload.get("regime") or {}
        labels = regime.get("labels") or []
        probability_high = regime.get("probability_high") or []
        markets = list((payload.get("market_indices") or {}).get("series", {}).keys())
        summaries.append(
            CountrySummary(
                code=payload.get("country_code", code),
                name_en=code,
                as_of=payload.get("as_of"),
                markets=markets,
                latest_percentile=percentile[-1]["value"] if percentile else None,
                latest_deviation=deviation[-1]["value"] if deviation else None,
                regime=labels[-1] if labels else None,
                probability_high=probability_high[-1] if probability_high else None,
                open_alerts=len(payload.get("alerts") or []),
            )
        )
    return CountryListResponse(countries=summaries)


@router.get("/{code}/index", response_model=IndexResponse)
def country_index(
    code: str,
    lens: str = Query("percentile", pattern="^(percentile|deviation|composite)$"),
    store: ArtifactStore = Depends(get_store),
) -> IndexResponse:
    """The composite series, both lenses and the market indices of one country."""
    payload = _require_run(store, code)
    market_block = payload.get("market_indices") or {}
    dates = market_block.get("dates") or []
    series = market_block.get("series") or {}

    markets: dict[str, list[SeriesPoint]] = {}
    for name, values in series.items():
        markets[name] = [
            SeriesPoint(date=day, value=float(value))
            for day, value in zip(dates, values, strict=False)
        ]

    regime_block = payload.get("regime") or {}
    return IndexResponse(
        country_code=payload.get("country_code", code.upper()),
        as_of=payload.get("as_of", ""),
        lens=lens,
        composite=[
            SeriesPoint(date=item["date"], value=float(item["value"]))
            for item in payload.get("composite") or []
        ],
        percentile=[
            SeriesPoint(date=item["date"], value=float(item["value"]))
            for item in payload.get("percentile") or []
        ],
        deviation=[
            SeriesPoint(date=item["date"], value=float(item["value"]))
            for item in payload.get("deviation") or []
        ],
        market_indices=markets,
        market_dates=dates,
        regime=RegimeBlock(
            dates=regime_block.get("dates") or [],
            labels=regime_block.get("labels") or [],
            probability_moderate=regime_block.get("probability_moderate") or [],
            probability_high=regime_block.get("probability_high") or [],
            params=regime_block.get("params") or {},
        ),
        warnings=payload.get("warnings") or [],
    )


@router.get("/{code}/spillover", response_model=SpilloverResponse)
def country_spillover(
    code: str,
    store: ArtifactStore = Depends(get_store),
) -> SpilloverResponse:
    """The cross-market spillover network of one country."""
    payload = _require_run(store, code)
    block = payload.get("spillover") or {}
    if not block:
        raise HTTPException(
            status_code=404,
            detail=f"the run for {code!r} contains no spillover network",
        )
    return SpilloverResponse(
        scope=block.get("scope", code.upper()),
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


@router.get("/{code}/alerts", response_model=AlertListResponse)
def country_alerts(
    code: str,
    store: ArtifactStore = Depends(get_store),
) -> AlertListResponse:
    """The alerts that the last run raised for one country."""
    payload = _require_run(store, code)
    return AlertListResponse(
        alerts=[AlertResponse(**item) for item in payload.get("alerts") or []]
    )


@router.get("/{code}/data-quality", response_model=QualityResponse)
def country_quality(
    code: str,
    store: ArtifactStore = Depends(get_store),
) -> QualityResponse:
    """The quality-gate verdicts of the last run of one country."""
    try:
        payload = store.quality(code)
    except RunStoreError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return QualityResponse(**payload)
