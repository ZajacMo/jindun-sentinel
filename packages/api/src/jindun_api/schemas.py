"""Response models of the JinDun Sentinel API.

Every payload is language neutral: numbers stay numbers, dates stay
ISO-8601 strings and enumerations stay stable codes.  The client maps the
codes onto the localised strings in the shared catalogue.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field, model_validator

__all__ = [
    "HealthResponse",
    "CountrySummary",
    "CountryListResponse",
    "SeriesPoint",
    "IndexResponse",
    "MessageRef",
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
    profile: str = "mbsed"
    capabilities: dict[str, bool] = Field(default_factory=dict)
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


class MessageRef(BaseModel):
    """A sentence the reader sees: a catalogue key and the facts that fill it.

    The wording lives in the shared locale catalogue and the computation owns
    the facts, so the payload stays language neutral while every reader still
    gets a sentence in their own language.  This is the shape the alerting
    rules already use for their ``message_key`` and ``message_params``.
    """

    key: str
    params: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="before")
    @classmethod
    def accept_a_legacy_sentence(cls, value: Any) -> Any:
        """Read an artefact written before the notes became structured.

        An older artefact carries the note as a finished English sentence.  It
        cannot be translated, because there is no key behind it, but it must
        not take the endpoint down either: the text is passed through and the
        catalogue says that it is a verbatim note.
        """
        if isinstance(value, str):
            return {"key": "common.legacyNote", "params": {"text": value}}
        return value


class IndexResponse(BaseModel):
    country_code: str
    as_of: str
    profile: str = "mbsed"
    capabilities: dict[str, bool] = Field(default_factory=dict)
    lens: str = "percentile"
    composite: list[SeriesPoint] = Field(default_factory=list)
    percentile: list[SeriesPoint] = Field(default_factory=list)
    deviation: list[SeriesPoint] = Field(default_factory=list)
    market_indices: dict[str, list[SeriesPoint]] = Field(default_factory=dict)
    market_dates: list[str] = Field(default_factory=list)
    regime: RegimeBlock = Field(default_factory=RegimeBlock)
    warnings: list[MessageRef] = Field(default_factory=list)


class SpilloverResponse(BaseModel):
    scope: str
    nodes: list[str] = Field(default_factory=list)
    matrix: list[list[float]] = Field(default_factory=list)
    total_spillout: dict[str, float] = Field(default_factory=dict)
    total_spillin: dict[str, float] = Field(default_factory=dict)
    net: dict[str, float] = Field(default_factory=dict)
    horizon: int = 10
    method: str = "paper_equation"
    #: The estimator the artefact publishes as its default.
    default_method: str = "paper_equation"
    #: Every estimator the artefact publishes, so a client can offer a choice.
    available_methods: list[str] = Field(default_factory=list)
    var_order: int | None = None
    window: list[str] | None = None
    notes: list[MessageRef] = Field(default_factory=list)


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
