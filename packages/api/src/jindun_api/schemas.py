"""Response models of the JinDun Sentinel API.

Every payload is language neutral: numbers stay numbers, dates stay
ISO-8601 strings and enumerations stay stable codes.  The client maps the
codes onto the localised strings in the shared catalogue.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

__all__ = [
    "HealthResponse",
    "CountrySummary",
    "CountryListResponse",
    "SeriesPoint",
    "IndexResponse",
    "RegimeBlock",
    "SpilloverResponse",
    "AlertResponse",
    "AlertListResponse",
    "QualityResponse",
    "RunMetadataResponse",
    "LocaleListResponse",
]


class HealthResponse(BaseModel):
    status: str = "ok"
    version: str
    countries: list[str] = Field(default_factory=list)
    last_run_id: str | None = None


class CountrySummary(BaseModel):
    code: str
    name_en: str
    as_of: str | None = None
    markets: list[str] = Field(default_factory=list)
    latest_percentile: float | None = None
    latest_deviation: float | None = None
    regime: str | None = None
    probability_high: float | None = None
    open_alerts: int = 0


class CountryListResponse(BaseModel):
    countries: list[CountrySummary] = Field(default_factory=list)


class SeriesPoint(BaseModel):
    date: str
    value: float


class RegimeBlock(BaseModel):
    dates: list[str] = Field(default_factory=list)
    labels: list[str] = Field(default_factory=list)
    probability_moderate: list[float] = Field(default_factory=list)
    probability_high: list[float] = Field(default_factory=list)
    params: dict[str, Any] = Field(default_factory=dict)


class IndexResponse(BaseModel):
    country_code: str
    as_of: str
    lens: str = "percentile"
    composite: list[SeriesPoint] = Field(default_factory=list)
    percentile: list[SeriesPoint] = Field(default_factory=list)
    deviation: list[SeriesPoint] = Field(default_factory=list)
    market_indices: dict[str, list[SeriesPoint]] = Field(default_factory=dict)
    market_dates: list[str] = Field(default_factory=list)
    regime: RegimeBlock = Field(default_factory=RegimeBlock)
    warnings: list[str] = Field(default_factory=list)


class SpilloverResponse(BaseModel):
    scope: str
    nodes: list[str] = Field(default_factory=list)
    matrix: list[list[float]] = Field(default_factory=list)
    total_spillout: dict[str, float] = Field(default_factory=dict)
    total_spillin: dict[str, float] = Field(default_factory=dict)
    net: dict[str, float] = Field(default_factory=dict)
    horizon: int = 10
    method: str = "paper_equation"
    var_order: int | None = None
    window: list[str] | None = None
    notes: list[str] = Field(default_factory=list)


class AlertResponse(BaseModel):
    alert_id: str
    country_code: str
    rule_id: str
    severity: str
    state: str
    fired_at: str
    message_key: str
    message_params: dict[str, Any] = Field(default_factory=dict)
    attribution: dict[str, Any] = Field(default_factory=dict)
    detail: dict[str, Any] = Field(default_factory=dict)


class AlertListResponse(BaseModel):
    alerts: list[AlertResponse] = Field(default_factory=list)


class QualityResponse(BaseModel):
    generated_at: str
    passed: bool
    counts: dict[str, int] = Field(default_factory=dict)
    series: list[dict[str, Any]] = Field(default_factory=list)


class RunMetadataResponse(BaseModel):
    root: str
    countries: list[str] = Field(default_factory=list)
    last_run_id: str | None = None
    last_started_at: str | None = None
    generated_at: str


class LocaleListResponse(BaseModel):
    default: str = "en-US"
    locales: list[str] = Field(default_factory=list)
    fallback: str = "en-US"
