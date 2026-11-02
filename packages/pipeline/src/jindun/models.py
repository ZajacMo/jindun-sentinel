"""Core domain model for JinDun Sentinel.

The model is deliberately hierarchical — Country -> Market -> Indicator — so that
adding a new economy never requires touching the compute code.  Every derived
artefact is either country-scoped or global-scoped; nothing derived is
market-scoped, because a market index only means something relative to the
country that owns it.

All identifiers are stable, language-neutral codes.  Display names live in the
i18n catalogues so the API never has to decide which language to speak.
"""

from __future__ import annotations

import datetime as dt
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

__all__ = [
    "Direction",
    "Severity",
    "AlertState",
    "Indicator",
    "Market",
    "Country",
    "Observation",
    "Series",
    "RegimeLabel",
    "CountryIndexResult",
    "SpilloverResult",
    "Alert",
]


class Direction(StrEnum):
    """How a tertiary indicator relates to systemic risk.

    Mirrors the Chinese sheet vocabulary of the original workbook:
    同向 (same) / 反向 (opposite) / 双向 (bidirectional).
    """

    SAME = "same"
    OPPOSITE = "opposite"
    BIDIRECTIONAL = "bidirectional"

    @classmethod
    def parse(cls, raw: str) -> Direction:
        """Parse a direction label, accepting the Chinese source vocabulary."""
        key = (raw or "").strip()
        mapping = {
            "同向": cls.SAME,
            "same": cls.SAME,
            "反向": cls.OPPOSITE,
            "opposite": cls.OPPOSITE,
            "双向": cls.BIDIRECTIONAL,
            "bidirectional": cls.BIDIRECTIONAL,
        }
        if key not in mapping:
            raise ValueError(f"unknown indicator direction: {raw!r}")
        return mapping[key]


class Severity(StrEnum):
    P1 = "P1"
    P2 = "P2"
    P3 = "P3"


class AlertState(StrEnum):
    ACTIVE = "active"
    ACKNOWLEDGED = "acknowledged"
    RESOLVED = "resolved"


class RegimeLabel(StrEnum):
    """Two-state regime as defined by the Markov-switching model."""

    MODERATE = "moderate"
    HIGH = "high"


@dataclass(frozen=True, slots=True)
class Indicator:
    """A tertiary indicator belonging to one market of one country."""

    code: str
    label_key: str
    market_code: str
    direction: Direction
    unit: str = ""
    frequency: str = "D"
    source_adapter: str = ""
    source_series_id: str = ""
    weight: float | None = None
    transform: str = "level"
    enabled: bool = True


@dataclass(frozen=True, slots=True)
class Market:
    """A financial market segment inside a country (equity, bond, fx, money...)."""

    code: str
    label_key: str
    country_code: str
    indicators: tuple[Indicator, ...] = ()
    weight: float = 0.0

    def indicator(self, code: str) -> Indicator | None:
        for indicator in self.indicators:
            if indicator.code == code:
                return indicator
        return None


@dataclass(frozen=True, slots=True)
class Country:
    """A monitored economy."""

    code: str
    name_en: str
    name_local: str
    currency: str
    timezone: str
    locale: str
    markets: tuple[Market, ...] = ()
    methodology_ref: str = "default"
    official_index_ref: str | None = None
    ciss_area: str | None = None
    #: ``mbsed`` builds the composite from the sub-market indices; ``official_index``
    #: uses a published official stress index as the country index, which is the
    #: only honest option for an economy without a verified tertiary indicator set.
    profile: str = "mbsed"
    enabled: bool = True

    def market(self, code: str) -> Market | None:
        for market in self.markets:
            if market.code == code:
                return market
        return None

    @property
    def indicator_codes(self) -> tuple[str, ...]:
        return tuple(indicator.code for market in self.markets for indicator in market.indicators)


@dataclass(frozen=True, slots=True)
class Observation:
    """One immutable data point for one indicator."""

    date: dt.date
    value: float

    def as_dict(self) -> dict[str, float | str]:
        return {"date": self.date.isoformat(), "value": self.value}


@dataclass(frozen=True, slots=True)
class Series:
    """An ordered, immutable time series for one indicator."""

    code: str
    country_code: str
    market_code: str
    unit: str
    direction: Direction
    observations: tuple[Observation, ...] = ()
    source: str = ""

    def values(self) -> list[float]:
        return [obs.value for obs in self.observations]

    def dates(self) -> list[dt.date]:
        return [obs.date for obs in self.observations]

    def as_frame(self):
        """Return the series as a pandas DataFrame indexed by date."""
        import pandas as pd

        frame = pd.DataFrame(
            [obs.as_dict() for obs in self.observations],
            columns=["date", "value"],
        )
        if frame.empty:
            frame["date"] = pd.to_datetime(frame["date"])
        else:
            frame["date"] = pd.to_datetime(frame["date"])
        frame = frame.set_index("date")
        frame.index = frame.index.date
        frame.index.name = "date"
        return frame

    def to_records(self) -> list[dict[str, float | str]]:
        return [obs.as_dict() for obs in self.observations]


@dataclass(slots=True)
class RegimeSeries:
    """Regime labels and risk probabilities for one country."""

    country_code: str
    labels: list[RegimeLabel] = field(default_factory=list)
    dates: list[dt.date] = field(default_factory=list)
    probability_moderate: list[float] = field(default_factory=list)
    probability_high: list[float] = field(default_factory=list)
    regime_params: dict[str, Any] = field(default_factory=dict)

    def to_records(self) -> list[dict[str, object]]:
        return [
            {
                "date": date.isoformat(),
                "regime": label.value,
                "probability_moderate": p_mod,
                "probability_high": p_high,
            }
            for date, label, p_mod, p_high in zip(
                self.dates,
                self.labels,
                self.probability_moderate,
                self.probability_high,
                strict=False,
            )
        ]


@dataclass(slots=True)
class CountryIndexResult:
    """Everything the pipeline produced for one country."""

    country_code: str
    as_of: dt.date
    market_indices: dict[str, list[float]] = field(default_factory=dict)
    market_dates: list[dt.date] = field(default_factory=list)
    composite: list[float] = field(default_factory=list)
    percentile: list[float] = field(default_factory=list)
    deviation: list[float] = field(default_factory=list)
    correlation: list[list[float]] = field(default_factory=list)
    regime: RegimeSeries | None = None
    indicators: dict[str, Series] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)


@dataclass(slots=True)
class SpilloverResult:
    """A directional spillover matrix (Diebold-Yilmaz generalized FEVD).

    ``matrix[i][j]`` is the share of node ``i``'s own forecast error
    variance that is attributable to node ``j``; rows therefore sum to one.
    ``total_spillout`` is the column off-diagonal sum (how much of the
    system a node causes) and ``total_spillin`` is the row off-diagonal sum
    (how much of a node's own variance comes from elsewhere).
    """

    scope: str
    nodes: list[str]
    matrix: list[list[float]]
    total_spillout: dict[str, float] = field(default_factory=dict)
    total_spillin: dict[str, float] = field(default_factory=dict)
    horizon: int = 10
    window: tuple[str, str] | None = None
    notes: list[str] = field(default_factory=list)
    net: dict[str, float] = field(default_factory=dict)
    var_order: int | None = None
    method: str = "paper_equation"

    def to_payload(self) -> dict[str, object]:
        return {
            "scope": self.scope,
            "nodes": self.nodes,
            "matrix": self.matrix,
            "total_spillout": self.total_spillout,
            "total_spillin": self.total_spillin,
            "net": self.net,
            "horizon": self.horizon,
            "window": list(self.window) if self.window else None,
            "method": self.method,
            "var_order": self.var_order,
            "notes": self.notes,
        }


@dataclass(slots=True)
class SpilloverSet:
    """The networks of every estimator, computed from one VAR fit.

    The estimators are not interchangeable, so they are published side by side.
    One estimator that cannot be computed — the legacy implementation, for
    instance, needs a horizon that equals the number of nodes — must not take
    the others down with it: the failure is recorded per estimator instead.
    """

    results: dict[str, SpilloverResult] = field(default_factory=dict)
    failures: dict[str, str] = field(default_factory=dict)

    def to_payload(self) -> dict[str, object]:
        return {
            "estimators": {method: result.to_payload() for method, result in self.results.items()},
            "failed_estimators": dict(self.failures),
        }


@dataclass(slots=True)
class Alert:
    """A fired alerting rule."""

    alert_id: str
    country_code: str
    rule_id: str
    severity: Severity
    state: AlertState
    fired_at: dt.datetime
    message_key: str
    message_params: dict[str, object] = field(default_factory=dict)
    attribution: dict[str, object] = field(default_factory=dict)
    detail: dict[str, object] = field(default_factory=dict)

    def to_payload(self) -> dict[str, object]:
        return {
            "alert_id": self.alert_id,
            "country_code": self.country_code,
            "rule_id": self.rule_id,
            "severity": self.severity.value,
            "state": self.state.value,
            "fired_at": self.fired_at.isoformat(),
            "message_key": self.message_key,
            "message_params": self.message_params,
            "attribution": self.attribution,
            "detail": self.detail,
        }


def series_from_mapping(
    code: str,
    country_code: str,
    market_code: str,
    rows: Iterable[Mapping[str, object]],
    *,
    unit: str = "",
    direction: Direction = Direction.SAME,
    source: str = "",
    date_key: str = "date",
    value_key: str = "value",
) -> Series:
    """Build a :class:`Series` from an iterable of row mappings.

    Rows whose value cannot be parsed as a float are dropped rather than
    coerced to zero — silently turning a missing observation into a real one
    is exactly the failure mode the pipeline is designed to avoid.
    """
    observations: list[Observation] = []
    for row in rows:
        raw_date = row.get(date_key)
        raw_value = row.get(value_key)
        if raw_date is None or raw_value is None:
            continue
        if isinstance(raw_date, str):
            date = dt.date.fromisoformat(raw_date[:10])
        elif isinstance(raw_date, dt.datetime):
            date = raw_date.date()
        elif isinstance(raw_date, dt.date):
            date = raw_date
        else:
            raise ValueError(f"unsupported date value: {raw_date!r}")
        try:
            value = float(raw_value)
        except (TypeError, ValueError):
            continue
        observations.append(Observation(date=date, value=value))
    observations.sort(key=lambda obs: obs.date)
    return Series(
        code=code,
        country_code=country_code,
        market_code=market_code,
        unit=unit,
        direction=direction,
        observations=tuple(observations),
        source=source,
    )


def countries_by_code(countries: Sequence[Country]) -> dict[str, Country]:
    return {country.code: country for country in countries}
