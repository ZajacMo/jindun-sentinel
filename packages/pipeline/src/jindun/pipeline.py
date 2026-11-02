"""The daily pipeline: from raw sources to published artefacts.

One function, :func:`run_country`, executes the whole chain for one economy
and returns a :class:`CountryRun`.  The chain is:

1. fetch every tertiary indicator through its adapter,
2. evaluate the quality gates on what came back,
3. normalise each market's indicator panel onto its own percentile and
   aggregate it into a market stress index,
4. synthesise the MBSED composite and its two reporting lenses,
5. identify the stress regime and the risk probability,
6. estimate the cross-market spillover network,
7. evaluate the alerting rules.

Every step writes its own artefact and the whole run is described by a
manifest, so a published number can always be traced back to the source
payloads that produced it.
"""

from __future__ import annotations

import datetime as dt
import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from .adapters.base import FetchResult
from .attribution import attribute_composite_move
from .config import Settings
from .contagion import (
    GVDSpec,
    compute_spillover,
    rolling_spillout_history,
    spillout_surge_scores,
    surging_markets,
)
from .contagion.surge import SurgeScore
from .index.composite import deviation_from_trend, synthesise_composite, to_percentile
from .index.critic import resolve_weights
from .index.normalise import normalise_panel
from .models import (
    Alert,
    AlertState,
    Country,
    Direction,
    RegimeLabel,
    Severity,
)
from .quality import QualityPolicy, QualityReport, evaluate_all
from .regime.markov import fit_regime
from .regime.probability import fit_probability_model

__all__ = ["CountryRun", "run_country", "write_run_artifacts", "resolve_indicator_series"]


@dataclass(slots=True)
class CountryRun:
    """Everything one country run produced."""

    country_code: str
    as_of: dt.date
    market_indices: pd.DataFrame = field(default_factory=pd.DataFrame)
    composite: pd.Series = field(default_factory=pd.Series)
    percentile: pd.Series = field(default_factory=pd.Series)
    deviation: pd.Series = field(default_factory=pd.Series)
    regime_labels: list[str] = field(default_factory=list)
    regime_dates: list[str] = field(default_factory=list)
    probability_moderate: list[float] = field(default_factory=list)
    probability_high: list[float] = field(default_factory=list)
    regime_params: dict[str, float] = field(default_factory=dict)
    spillover: dict[str, Any] = field(default_factory=dict)
    alerts: list[Alert] = field(default_factory=list)
    attribution: dict[str, Any] = field(default_factory=dict)
    forecast: dict[str, Any] = field(default_factory=dict)
    quality: QualityReport | None = None
    sources: list[dict[str, Any]] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def to_payload(self) -> dict[str, Any]:
        return {
            "country_code": self.country_code,
            "as_of": self.as_of.isoformat(),
            "market_indices": {
                "dates": [date.isoformat() for date in self.market_indices.index],
                "series": {
                    column: [round(float(value), 8) for value in self.market_indices[column]]
                    for column in self.market_indices.columns
                },
            },
            "composite": [
                {"date": date.isoformat(), "value": round(float(value), 8)}
                for date, value in self.composite.items()
            ],
            "percentile": [
                {"date": date.isoformat(), "value": round(float(value), 8)}
                for date, value in self.percentile.items()
            ],
            "deviation": [
                {"date": date.isoformat(), "value": round(float(value), 8)}
                for date, value in self.deviation.items()
            ],
            "regime": {
                "dates": list(self.regime_dates),
                "labels": list(self.regime_labels),
                "probability_moderate": [round(v, 8) for v in self.probability_moderate],
                "probability_high": [round(v, 8) for v in self.probability_high],
                "params": dict(self.regime_params),
            },
            "spillover": self.spillover,
            "alerts": [alert.to_payload() for alert in self.alerts],
            "attribution": self.attribution,
            "forecast": self.forecast,
            "warnings": list(self.warnings),
        }


def resolve_indicator_series(
    country: Country,
    fetcher,
    *,
    use_cache: bool = True,
) -> tuple[dict[str, pd.Series], list[FetchResult]]:
    """Fetch every indicator of ``country`` and return the raw panel.

    ``fetcher`` is called as ``fetcher(series_id, use_cache=...)`` and returns
    a :class:`FetchResult`.
    """
    results: list[FetchResult] = []
    panel: dict[str, pd.Series] = {}
    for market in country.markets:
        for indicator in market.indicators:
            result = fetcher(indicator.source_series_id, use_cache=use_cache)
            result.country_code = country.code
            results.append(result)
            if not result.observations:
                continue
            frame = result.to_series().as_frame()
            panel[f"{market.code}.{indicator.code}"] = frame["value"]
    if not panel:
        return pd.DataFrame(), results
    combined = pd.concat(panel, axis=1).sort_index()
    return combined, results


def _market_index(
    panel: pd.DataFrame,
    market_code: str,
    indicator_codes: Sequence[str],
    directions: Mapping[str, Direction],
    weights: Mapping[str, float],
) -> tuple[pd.Series | None, dict[str, Any], pd.DataFrame]:
    """Build one market stress index from its normalised indicators.

    Returns the index, a report and the normalised indicator panel, which
    the attribution stage needs in order to explain the move.
    """
    columns = [f"{market_code}.{code}" for code in indicator_codes]
    available = [column for column in columns if column in panel.columns]
    if not available:
        return None, {"market": market_code, "status": "no_data"}, pd.DataFrame()
    subset = panel[available].dropna(how="any")
    if subset.empty:
        return None, {"market": market_code, "status": "no_common_observations"}, pd.DataFrame()

    direction_map = {
        f"{market_code}.{code}": directions.get(f"{market_code}.{code}", Direction.SAME)
        for code in indicator_codes
    }
    normalised = normalise_panel(subset, direction_map)
    indicator_weights = resolve_weights(
        normalised,
        {column: float(weights.get(column.split(".", 1)[1], 0.0)) for column in available},
        mode="configured",
    )
    series = normalised.mul(indicator_weights, axis=1).sum(axis=1)
    return (
        series,
        {
            "market": market_code,
            "status": "ok",
            "indicators": available,
            "weights": {key: round(float(value), 8) for key, value in indicator_weights.items()},
            "observations": int(len(series)),
        },
        normalised,
    )


def run_country(
    country: Country,
    settings: Settings,
    *,
    fetcher,
    quality_policy: QualityPolicy | None = None,
    use_cache: bool = True,
    today: dt.date | None = None,
) -> CountryRun:
    """Execute the full chain for one country."""
    warnings: list[str] = []
    directions = {
        f"{market.code}.{indicator.code}": indicator.direction
        for market in country.markets
        for indicator in market.indicators
    }
    weights = {
        f"{market.code}.{indicator.code}": float(indicator.weight or 0.0)
        for market in country.markets
        for indicator in market.indicators
    }

    panel, results = resolve_indicator_series(
        country, fetcher, use_cache=use_cache
    )
    quality = evaluate_all(results, quality_policy, today=today)
    for failure in quality.failures:
        warnings.append(
            f"quality gate failed for {failure.series_id}: "
            + "; ".join(
                check.message for check in failure.checks if not check.passed
            )
        )

    market_series: dict[str, pd.Series] = {}
    market_reports: list[dict[str, Any]] = []
    normalised_panels: dict[str, pd.DataFrame] = {}
    indicator_weight_map: dict[str, dict[str, float]] = {}
    for market in country.markets:
        codes = [indicator.code for indicator in market.indicators]
        series, report, normalised = _market_index(
            panel, market.code, codes, directions, weights
        )
        market_reports.append(report)
        if series is not None:
            market_series[market.code] = series
            normalised_panels[market.code] = normalised
            indicator_weight_map[market.code] = report.get("weights", {})

    if not market_series:
        return CountryRun(
            country_code=country.code,
            as_of=today or dt.date.today(),
            quality=quality,
            sources=[result.to_payload() for result in results],
            warnings=[*warnings, "no market index could be built"],
        )

    market_frame = pd.DataFrame(market_series).sort_index()
    market_weights = {
        market.code: market.weight
        for market in country.markets
        if market.code in market_frame.columns
    }
    if not market_weights or sum(market_weights.values()) <= 0:
        market_weights = {column: 1.0 for column in market_frame.columns}

    # Two profiles are supported and they are *not* interchangeable:
    #
    # ``mbsed``
    #     The composite is synthesised from the sub-market indices, the way the
    #     original research did it.  This needs a verified tertiary indicator
    #     set for every market.
    # ``official_index``
    #     The country index is a published official stress index.  There is no
    #     sub-market decomposition behind it, and pretending otherwise would
    #     mean publishing an attribution that was never computed.
    official_profile = country.profile == "official_index"
    if official_profile:
        composite = market_frame.iloc[:, 0].copy()
        warnings.append(
            "the country index is an official published stress index; this economy "
            "has no sub-market decomposition, so the market attribution and the "
            "cross-market spillover network are not available for it"
        )
    else:
        composite, _ = synthesise_composite(
            market_frame, market_weights, scale=settings.composite.scale
        )
    percentile = to_percentile(composite)
    deviation = deviation_from_trend(composite)

    regime_fit = fit_regime(
        np.log(composite),
        k_regimes=settings.regime.k_regimes,
        order=settings.regime.order,
        switching_variance=settings.regime.switching_variance,
        trend=settings.regime.trend,
        max_observations=settings.regime.max_observations,
    )
    probability = fit_probability_model(
        np.log(composite),
        regime_fit,
        bandwidth=settings.regime.probability_bandwidth,
        normalise=True,
    )
    calm, stressed = probability.predict(np.log(composite))

    spillover_payload: dict[str, Any] = {}
    surge_scores: dict[str, SurgeScore] = {}
    if official_profile or market_frame.shape[1] < 2:
        if not official_profile:
            warnings.append(
                "the cross-market spillover network needs at least two markets"
            )
    else:
        try:
            spec = GVDSpec(
                method=settings.contagion.method,
                horizon=settings.contagion.horizon,
                var_order=settings.contagion.var_order,
                criterion=settings.contagion.criterion,
                max_order=settings.contagion.max_order,
                transform=settings.contagion.transform,
            )
            spillover = compute_spillover(
                market_frame, spec, scope=country.code
            )
            spillover_payload = spillover.to_payload()
            if spillover.notes != []:
                warnings.extend(spillover.notes)

            # The surge alert compares a market's spill-out with its own
            # history, which needs the network recomputed over rolling windows.
            if settings.contagion.surge_enabled:
                history = rolling_spillout_history(
                    market_frame,
                    spec,
                    window=settings.contagion.surge_window,
                    step=settings.contagion.surge_step,
                    max_windows=settings.contagion.surge_max_windows,
                    min_windows=settings.contagion.surge_min_windows,
                )
                if not history.empty:
                    scores = spillout_surge_scores(history)
                    surge_scores = dict(scores)
                    spillover_payload["spillout_history"] = {
                        "window_end": [str(index) for index in history.index],
                        "markets": [str(column) for column in history.columns],
                        "window": history.attrs.get("window"),
                        "step": history.attrs.get("step"),
                        "values": [
                            [float(value) for value in row] for row in history.to_numpy()
                        ],
                        "scores": {
                            market: score.to_payload() for market, score in scores.items()
                        },
                    }
                else:
                    warnings.append(
                        "the rolling spill-out history could not be built; "
                        "the surge alert stays silent for this run"
                    )
        except Exception as exc:  # noqa: BLE001 - contagion is optional per run
            warnings.append(f"the spillover network could not be computed: {exc}")

    alerts = _evaluate_alerts(
        country, settings, percentile, regime_fit, market_frame, surge_scores
    )

    attribution_payload: dict[str, Any] = {}
    if not official_profile:
        try:
            attribution = attribute_composite_move(
                market_frame,
                composite,
                market_weights,
                scale=settings.composite.scale,
                normalised_indicators=normalised_panels,
                indicator_weights=indicator_weight_map,
            )
            attribution_payload = attribution.to_payload()
            if spillover_payload:
                attribution_payload["spillover_attribution"] = {
                    node: float(value)
                    for node, value in (spillover_payload.get("total_spillin") or {}).items()
                }
        except Exception as exc:  # noqa: BLE001
            warnings.append(f"the move could not be attributed: {exc}")

    forecast_payload: dict[str, Any] = {}
    try:
        forecast_payload = _forecast_payload(composite, settings)
    except Exception as exc:  # noqa: BLE001
        warnings.append(f"the forecast could not be computed: {exc}")

    return CountryRun(
        country_code=country.code,
        as_of=today or dt.date.today(),
        market_indices=market_frame,
        composite=composite,
        percentile=percentile,
        deviation=deviation,
        regime_labels=[label.value for label in regime_fit.labels],
        regime_dates=[date.isoformat() for date in regime_fit.dates],
        probability_moderate=[float(value) for value in calm.fillna(0.0)],
        probability_high=[float(value) for value in stressed.fillna(0.0)],
        regime_params={
            "moderate_mean": float(regime_fit.regime_means.get("moderate", 0.0)),
            "high_mean": float(regime_fit.regime_means.get("high", 0.0)),
            "moderate_std": float(regime_fit.regime_stds.get("moderate", 0.0)),
            "high_std": float(regime_fit.regime_stds.get("high", 0.0)),
            "method": regime_fit.method,
            "converged": bool(regime_fit.converged),
        },
        spillover=spillover_payload,
        alerts=alerts,
        attribution=attribution_payload,
        forecast=forecast_payload,
        quality=quality,
        sources=[result.to_payload() for result in results],
        warnings=warnings,
    )


def _forecast_payload(composite: pd.Series, settings: Settings) -> dict[str, Any]:
    """Forecast the composite and score the model out of sample."""
    from .forecast import backtest, forecast_arima, select_arima_order

    clean = composite.dropna()
    if len(clean) < 120:
        return {"engine": "arima", "notes": ["not enough data to forecast the composite"]}

    if settings.forecast.max_observations and len(clean) > settings.forecast.max_observations:
        clean = clean.iloc[-settings.forecast.max_observations :]

    window = min(settings.forecast.backtest_window, max(60, len(clean) // 3))
    horizon = min(10, settings.forecast.horizon)

    # The order is chosen once, on the first training window only, and then held
    # fixed for the whole walk-forward.  Re-running the grid at every origin
    # costs tens of thousands of fits for a number that does not change, and
    # choosing the order on data that includes the evaluation period would leak
    # the future into the score.
    order = select_arima_order(clean.iloc[:window], max_p=settings.forecast.arima_max_order)

    def _predict(training: pd.Series, horizon: int) -> np.ndarray:
        return forecast_arima(training, horizon=horizon, order=order).forecast

    metrics = backtest(
        clean,
        _predict,
        horizon=horizon,
        window=window,
        engine="arima",
        stride=settings.forecast.backtest_stride,
        max_origins=settings.forecast.max_backtest_origins,
    )
    fit = forecast_arima(clean, horizon=settings.forecast.horizon)
    return {
        "engine": "arima",
        "order": list(fit.order),
        "dates": fit.dates,
        "values": [round(float(value), 8) for value in fit.forecast],
        "lower": [round(float(value), 8) for value in fit.lower],
        "upper": [round(float(value), 8) for value in fit.upper],
        "converged": fit.converged,
        "backtest": metrics.to_payload(),
        "notes": [fit.note] if fit.note else [],
    }


def _evaluate_alerts(
    country: Country,
    settings: Settings,
    percentile: pd.Series,
    regime_fit,
    market_frame: pd.DataFrame,
    surge_scores: Mapping[str, SurgeScore] | None = None,
) -> list[Alert]:
    """Evaluate the configured alerting rules against the latest reading."""
    alerts: list[Alert] = []
    if percentile.empty:
        return alerts

    latest = percentile.dropna()
    if latest.empty:
        return alerts
    latest_date = latest.index[-1]
    latest_value = float(latest.iloc[-1])

    for rule in settings.rules_for(country.code):
        if not rule.enabled:
            continue
        severity = Severity(rule.severity) if rule.severity in Severity._value2member_map_ else Severity.P3
        threshold = rule.params.get("threshold")
        fired = False
        surge_detail: dict[str, Any] = {}
        message_params: dict[str, Any] = {
            "country": country.code,
            "value": round(latest_value, 6),
            "threshold": threshold,
            "date": latest_date.isoformat(),
        }
        if rule.id.startswith("composite") and threshold is not None:
            fired = latest_value >= float(threshold)
        elif rule.id == "regime.change":
            labels = regime_fit.labels
            fired = bool(len(labels) >= 2 and labels[-1] is RegimeLabel.HIGH and labels[-2] is not RegimeLabel.HIGH)
        elif rule.id == "spillout.surge":
            # A market's total spill-out has risen far above its own rolling
            # history.  The score is a z-score over the rolling windows, so the
            # threshold is dimensionless and comparable across markets.
            zscore_threshold = float(rule.params.get("zscore", 2.0))
            scores = surge_scores or {}
            surging = {
                market: score
                for market, score in scores.items()
                if market
                in surging_markets(
                    scores,
                    zscore_threshold,
                    min_relative_change=settings.contagion.surge_min_relative_change,
                )
            }
            if surging:
                fired = True
                top_market, top_score = max(
                    surging.items(), key=lambda item: item[1].zscore
                )
                surge_detail = {
                    "market": top_market,
                    "zscore": round(top_score.zscore, 6),
                    "latest": round(top_score.latest, 8),
                    "mean": round(top_score.mean, 8),
                    "std": round(top_score.std, 8),
                    "window_end": top_score.window_end,
                    "windows": top_score.windows,
                    "markets": {
                        market: round(score.zscore, 6)
                        for market, score in sorted(surging.items())
                    },
                }
                message_params["value"] = (
                    f"{top_score.latest:.4f} (z={top_score.zscore:.2f}, {top_market})"
                )
                message_params["market"] = top_market
                message_params["zscore"] = surge_detail["zscore"]

        if not fired:
            continue
        alerts.append(
            Alert(
                alert_id=f"{country.code}.{rule.id}.{latest_date.isoformat()}",
                country_code=country.code,
                rule_id=rule.id,
                severity=severity,
                state=AlertState.ACTIVE,
                fired_at=dt.datetime.now(dt.UTC),
                message_key=rule.message_key,
                message_params=message_params,
                attribution={"latest_percentile": round(latest_value, 6), **surge_detail},
                detail={"rule_description": rule.description},
            )
        )
    return alerts


def write_run_artifacts(run: CountryRun, out_dir: str | Path) -> dict[str, str]:
    """Write the artefacts of one country run and return their paths."""
    root = Path(out_dir) / run.country_code
    root.mkdir(parents=True, exist_ok=True)

    paths: dict[str, str] = {}

    market_path = root / "market_indices.csv"
    market_frame = run.market_indices.copy()
    market_frame.index = [date.isoformat() for date in market_frame.index]
    market_frame.to_csv(market_path, encoding="utf-8")
    paths["market_indices"] = str(market_path)

    payload_path = root / "run.json"
    payload_path.write_text(
        json.dumps(run.to_payload(), ensure_ascii=False, indent=2), encoding="utf-8"
    )
    paths["run"] = str(payload_path)

    if run.quality is not None:
        quality_path = root / "quality.json"
        quality_path.write_text(
            json.dumps(run.quality.to_payload(), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        paths["quality"] = str(quality_path)

    return paths
