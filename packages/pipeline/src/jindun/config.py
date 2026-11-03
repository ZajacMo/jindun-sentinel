"""Configuration loading for JinDun Sentinel.

All tunable methodology lives in YAML under ``packages/pipeline/configs``:
market weights, PCA thresholds, regime parameters, indicator definitions and
alerting rules.  Nothing in the compute code may hard-code a parameter that a
researcher would want to vary — that was defect E2 in the legacy implementation
and it is what this module exists to prevent.
"""

from __future__ import annotations

import os
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from .contagion.gvd import METHODS
from .models import Country, Direction, Indicator, Market

__all__ = [
    "LocaleSpec",
    "IndexParams",
    "CompositeParams",
    "RegimeParams",
    "ForecastParams",
    "ContagionParams",
    "AlertRule",
    "Settings",
    "load_settings",
    "default_config_dir",
]


def default_config_dir() -> Path:
    """Return the directory holding the shipped YAML configuration."""
    from . import paths

    return paths.config_dir()


@dataclass(frozen=True, slots=True)
class LocaleSpec:
    code: str
    label: str
    direction: str = "ltr"
    date_format: str = "medium"
    number_locale: str | None = None

    @property
    def resolved_number_locale(self) -> str:
        return self.number_locale or self.code


@dataclass(frozen=True, slots=True)
class IndexParams:
    """Parameters for normalisation and sub-market PCA."""

    pca_variance_threshold: float = 0.80
    normalisation: str = "cdf_rank"
    min_observations: int = 60
    rolling_window: int = 250


@dataclass(frozen=True, slots=True)
class CompositeParams:
    """Parameters for the MBSED composite."""

    market_weights: Mapping[str, float] = field(default_factory=dict)
    scale: float = 2.0
    baseline: str = "percentile"
    weight_mode: str = "configured"


@dataclass(frozen=True, slots=True)
class ContagionParams:
    """Parameters for the VAR / generalised variance decomposition."""

    method: str = "paper_equation"
    horizon: int = 10
    var_order: int | None = None
    criterion: str = "bic"
    max_order: int = 5
    transform: str = "level"
    # The estimators published side by side in every artefact.  They answer
    # different questions and are not interchangeable — the generalised
    # decomposition is signed, the structural one depends on the variable
    # ordering, and the legacy one is not a forecast error variance
    # decomposition at all — so the project publishes all of them instead of
    # quietly presenting one as "the" spillover number.
    publish_methods: tuple[str, ...] = METHODS
    # Rolling windows used to build the spill-out history behind the surge
    # alert.  See contagion/surge.py for why they are deliberately coarse.
    surge_enabled: bool = True
    surge_window: int = 500
    surge_step: int = 250
    surge_max_windows: int = 24
    surge_min_windows: int = 4
    surge_min_relative_change: float = 0.20


@dataclass(frozen=True, slots=True)
class RegimeParams:
    """Parameters for the Markov-switching regime model."""

    k_regimes: int = 2
    order: int = 5
    switching_variance: bool = True
    trend: str = "c"
    probability_bandwidth: float = 0.2
    hp_window: int = 90
    #: The regime model is fitted on the most recent observations only.  A
    #: Markov-switching model with several lags on forty years of daily data is
    #: both slow and over-parameterised, and for a *monitoring* system the
    #: recent past is the informative part.
    max_observations: int = 2500


@dataclass(frozen=True, slots=True)
class ForecastParams:
    """Parameters for the forecast module."""

    horizon: int = 50
    arima_max_order: int = 3
    lstm_epochs: int = 100
    lstm_batch_size: int = 32
    lstm_window: int = 300
    backtest_window: int = 120
    backtest_stride: int = 10
    max_backtest_origins: int = 120
    #: The forecast is fitted on the most recent observations only, for the same
    #: reason as the regime model: the horizon is short and the recent past is
    #: what predicts it.
    max_observations: int = 2500


@dataclass(frozen=True, slots=True)
class CycleParams:
    """Parameters for the global financial cycle factor (layer L3).

    The factor is estimated from BIS data, so these are the choices a
    researcher would want to vary: which economies contribute a credit gap,
    and which currency carries the global-funding leg.
    """

    enabled: bool = True
    #: Every listed economy contributes its credit-to-GDP gap.  The common
    #: window of the factor is the window all of them share, so an economy
    #: whose series starts late sets the start of the factor.
    credit_gap_economies: tuple[str, ...] = ("US", "CN", "JP", "GB", "XM")
    #: The currency whose effective exchange rate carries the funding leg.
    dollar_reference_area: str = "US"
    #: ``B`` is the broad basket (64 economies), ``N`` the narrow one (27).
    eer_basket: str = "B"
    #: Fewer observations than this are not enough to estimate a factor.
    min_observations: int = 40


@dataclass(frozen=True, slots=True)
class AlertRule:
    """One declarative alerting rule."""

    id: str
    severity: str
    scope: str
    message_key: str
    params: Mapping[str, Any] = field(default_factory=dict)
    enabled: bool = True
    silence_days: int = 3
    description: str = ""


@dataclass(slots=True)
class Settings:
    """Fully resolved configuration."""

    project_name: str
    default_locale: str
    locales: tuple[LocaleSpec, ...]
    countries: tuple[Country, ...]
    index: IndexParams
    composite: CompositeParams
    regime: RegimeParams
    forecast: ForecastParams
    contagion: ContagionParams
    cycle: CycleParams
    alert_rules: tuple[AlertRule, ...]
    config_dir: Path
    raw: Mapping[str, Any] = field(default_factory=dict)

    @property
    def locale_codes(self) -> tuple[str, ...]:
        return tuple(locale.code for locale in self.locales)

    def country(self, code: str) -> Country | None:
        for country in self.countries:
            if country.code == code:
                return country
        return None

    def enabled_countries(self) -> tuple[Country, ...]:
        return tuple(country for country in self.countries if country.enabled)

    def rules_for(self, country_code: str) -> tuple[AlertRule, ...]:
        scoped: list[AlertRule] = []
        for rule in self.alert_rules:
            if rule.scope in ("all", country_code):
                scoped.append(rule)
        return tuple(scoped)


def _read_yaml(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle) or {}
    if not isinstance(data, dict):
        raise ValueError(f"configuration file must contain a mapping: {path}")
    return data


def _parse_indicator(raw: Mapping[str, Any], market_code: str) -> Indicator:
    return Indicator(
        code=str(raw["code"]),
        label_key=str(raw.get("label_key", f"indicator.{raw['code']}")),
        market_code=market_code,
        direction=Direction.parse(str(raw.get("direction", "same"))),
        unit=str(raw.get("unit", "")),
        frequency=str(raw.get("frequency", "D")),
        source_adapter=str(raw.get("source_adapter", "")),
        source_series_id=str(raw.get("source_series_id", "")),
        weight=raw.get("weight"),
        transform=str(raw.get("transform", "level")),
        enabled=bool(raw.get("enabled", True)),
    )


def _parse_market(raw: Mapping[str, Any], country_code: str) -> Market:
    market_code = str(raw["code"])
    indicators = tuple(
        _parse_indicator(item, market_code)
        for item in raw.get("indicators", [])
        if item.get("enabled", True)
    )
    return Market(
        code=market_code,
        label_key=str(raw.get("label_key", f"market.{market_code}")),
        country_code=country_code,
        indicators=indicators,
        weight=float(raw.get("weight", 0.0)),
    )


def _parse_country(raw: Mapping[str, Any]) -> Country:
    country_code = str(raw["code"])
    markets = tuple(_parse_market(item, country_code) for item in raw.get("markets", []))
    return Country(
        code=country_code,
        name_en=str(raw.get("name_en", country_code)),
        name_local=str(raw.get("name_local", raw.get("name_en", country_code))),
        currency=str(raw.get("currency", "")),
        timezone=str(raw.get("timezone", "UTC")),
        locale=str(raw.get("locale", "en-US")),
        markets=markets,
        methodology_ref=str(raw.get("methodology_ref", "default")),
        official_index_ref=raw.get("official_index_ref"),
        ciss_area=raw.get("ciss_area"),
        profile=str(raw.get("profile", "mbsed")),
        enabled=bool(raw.get("enabled", True)),
    )


def _parse_locales(raw: Sequence[Mapping[str, Any]]) -> tuple[LocaleSpec, ...]:
    specs: list[LocaleSpec] = []
    for item in raw:
        specs.append(
            LocaleSpec(
                code=str(item["code"]),
                label=str(item.get("label", item["code"])),
                direction=str(item.get("direction", "ltr")),
                date_format=str(item.get("date_format", "medium")),
                number_locale=item.get("number_locale"),
            )
        )
    return tuple(specs)


def _parse_rules(raw: Sequence[Mapping[str, Any]]) -> tuple[AlertRule, ...]:
    rules: list[AlertRule] = []
    for item in raw:
        rules.append(
            AlertRule(
                id=str(item["id"]),
                severity=str(item.get("severity", "P3")),
                scope=str(item.get("scope", "all")),
                message_key=str(item.get("message_key", f"alert.{item['id']}")),
                params=dict(item.get("params", {})),
                enabled=bool(item.get("enabled", True)),
                silence_days=int(item.get("silence_days", 3)),
                description=str(item.get("description", "")),
            )
        )
    return tuple(rules)


def load_settings(config_dir: str | os.PathLike[str] | None = None) -> Settings:
    """Load the whole configuration tree.

    ``config_dir`` may point at a single YAML file or at a directory containing
    ``global.yaml`` and a ``countries/`` sub-directory.
    """
    path = Path(config_dir) if config_dir is not None else default_config_dir()
    if path.is_file():
        raw = _read_yaml(path)
        base = path.parent
        global_raw = raw
        countries_raw: list[Mapping[str, Any]] = list(raw.get("countries", []))
    else:
        base = path
        global_raw = _read_yaml(path / "global.yaml")
        countries_raw = []
        country_dir = path / "countries"
        if country_dir.exists():
            for file in sorted(country_dir.glob("*.yaml")):
                data = _read_yaml(file)
                if data:
                    countries_raw.append(data)

    project = global_raw.get("project", {})
    locales = _parse_locales(global_raw.get("locales", []))
    default_locale = str(project.get("default_locale", "en-US"))

    index_raw = global_raw.get("index", {})
    index_params = IndexParams(
        pca_variance_threshold=float(index_raw.get("pca_variance_threshold", 0.80)),
        normalisation=str(index_raw.get("normalisation", "cdf_rank")),
        min_observations=int(index_raw.get("min_observations", 60)),
        rolling_window=int(index_raw.get("rolling_window", 250)),
    )

    composite_raw = global_raw.get("composite", {})
    composite_params = CompositeParams(
        market_weights=dict(composite_raw.get("market_weights", {})),
        scale=float(composite_raw.get("scale", 2.0)),
        baseline=str(composite_raw.get("baseline", "percentile")),
        weight_mode=str(composite_raw.get("weight_mode", "configured")),
    )

    contagion_raw = global_raw.get("contagion", {})
    order_value = contagion_raw.get("var_order")
    publish_raw = contagion_raw.get("publish_methods")
    publish_methods = tuple(str(item) for item in publish_raw) if publish_raw else METHODS
    unknown = [item for item in publish_methods if item not in METHODS]
    if unknown:
        raise ValueError(
            f"unknown contagion estimators {unknown}; expected a subset of {list(METHODS)}"
        )
    contagion_params = ContagionParams(
        method=str(contagion_raw.get("method", "paper_equation")),
        horizon=int(contagion_raw.get("horizon", 10)),
        var_order=None if order_value is None else int(order_value),
        criterion=str(contagion_raw.get("criterion", "bic")),
        max_order=int(contagion_raw.get("max_order", 5)),
        transform=str(contagion_raw.get("transform", "level")),
        publish_methods=publish_methods,
    )

    regime_raw = global_raw.get("regime", {})
    regime_params = RegimeParams(
        k_regimes=int(regime_raw.get("k_regimes", 2)),
        order=int(regime_raw.get("order", 5)),
        switching_variance=bool(regime_raw.get("switching_variance", True)),
        trend=str(regime_raw.get("trend", "c")),
        probability_bandwidth=float(regime_raw.get("probability_bandwidth", 0.2)),
        hp_window=int(regime_raw.get("hp_window", 90)),
    )

    forecast_raw = global_raw.get("forecast", {})
    forecast_params = ForecastParams(
        horizon=int(forecast_raw.get("horizon", 50)),
        arima_max_order=int(forecast_raw.get("arima_max_order", 3)),
        lstm_epochs=int(forecast_raw.get("lstm_epochs", 100)),
        lstm_batch_size=int(forecast_raw.get("lstm_batch_size", 32)),
        lstm_window=int(forecast_raw.get("lstm_window", 300)),
        backtest_window=int(forecast_raw.get("backtest_window", 120)),
    )

    cycle_raw = global_raw.get("cycle", {})
    cycle_params = CycleParams(
        enabled=bool(cycle_raw.get("enabled", True)),
        credit_gap_economies=tuple(
            str(item).upper() for item in cycle_raw.get("credit_gap_economies", ())
        )
        or ("US", "CN", "JP", "GB", "XM"),
        dollar_reference_area=str(cycle_raw.get("dollar_reference_area", "US")).upper(),
        eer_basket=str(cycle_raw.get("eer_basket", "B")).upper(),
        min_observations=int(cycle_raw.get("min_observations", 40)),
    )

    countries = tuple(_parse_country(item) for item in countries_raw)
    rules = _parse_rules(global_raw.get("alert_rules", []))

    return Settings(
        project_name=str(project.get("name", "jindun-sentinel")),
        default_locale=default_locale,
        locales=locales,
        countries=countries,
        index=index_params,
        composite=composite_params,
        regime=regime_params,
        forecast=forecast_params,
        contagion=contagion_params,
        cycle=cycle_params,
        alert_rules=rules,
        config_dir=base,
        raw=global_raw,
    )
