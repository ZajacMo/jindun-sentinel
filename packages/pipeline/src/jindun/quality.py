"""Quality gates for the data the pipeline consumes.

A daily monitoring system is only useful if it refuses to publish a number it
cannot stand behind.  This module turns the raw observations of every series
into an explicit verdict: every check is named, every failure carries the
measured value and the threshold it breached, and the overall verdict is a
single boolean plus a severity.

The checks are deliberately conservative.  A series that is merely *stale* is
a warning, not a failure — a weekend or a holiday will produce one.  A
series that is *broken* (no observations, non-monotonic dates, duplicated
dates, values outside the plausible range) is a failure and blocks the run.
"""

from __future__ import annotations

import datetime as dt
from collections.abc import Iterable
from dataclasses import dataclass, field
from enum import StrEnum

from .adapters.base import FetchResult

__all__ = [
    "Severity",
    "QualityCheck",
    "SeriesQuality",
    "QualityReport",
    "QualityPolicy",
    "evaluate_series",
    "evaluate_all",
]


class Severity(StrEnum):
    OK = "ok"
    WARNING = "warning"
    FAILURE = "failure"


@dataclass(frozen=True, slots=True)
class QualityPolicy:
    """Thresholds the gates are evaluated against."""

    #: A daily series is stale after this many calendar days.
    max_staleness_days: int = 5
    #: A daily series is expected to have at least this share of its
    #: observations on distinct business days.
    min_completeness: float = 0.90
    #: The longest tolerated gap between two observations, in days.  A long
    #: holiday weekend in the Chinese market reaches nine days, so the
    #: default leaves room for two such breaks in a row.
    max_gap_days: int = 15
    #: Minimum number of observations for the series to be usable.
    min_observations: int = 60
    #: Optional hard bounds; ``None`` disables the check.
    lower_bound: float | None = None
    upper_bound: float | None = None


@dataclass(frozen=True, slots=True)
class QualityCheck:
    """The outcome of one named check."""

    name: str
    passed: bool
    severity: Severity
    measured: float | str | None = None
    threshold: float | str | None = None
    message: str = ""

    def to_payload(self) -> dict[str, object]:
        return {
            "name": self.name,
            "passed": self.passed,
            "severity": self.severity.value,
            "measured": self.measured,
            "threshold": self.threshold,
            "message": self.message,
        }


@dataclass(slots=True)
class SeriesQuality:
    """Aggregated verdict for one series."""

    series_id: str
    adapter: str
    country_code: str
    checks: list[QualityCheck] = field(default_factory=list)
    observations: int = 0
    first_date: str | None = None
    last_date: str | None = None

    @property
    def severity(self) -> Severity:
        if any(check.severity is Severity.FAILURE for check in self.checks):
            return Severity.FAILURE
        if any(check.severity is Severity.WARNING for check in self.checks):
            return Severity.WARNING
        return Severity.OK

    @property
    def passed(self) -> bool:
        return self.severity is not Severity.FAILURE

    def to_payload(self) -> dict[str, object]:
        return {
            "series_id": self.series_id,
            "adapter": self.adapter,
            "country_code": self.country_code,
            "severity": self.severity.value,
            "passed": self.passed,
            "observations": self.observations,
            "first_date": self.first_date,
            "last_date": self.last_date,
            "checks": [check.to_payload() for check in self.checks],
        }


@dataclass(slots=True)
class QualityReport:
    """The verdict of a whole run."""

    generated_at: str
    series: list[SeriesQuality] = field(default_factory=list)

    @property
    def failures(self) -> list[SeriesQuality]:
        return [item for item in self.series if item.severity is Severity.FAILURE]

    @property
    def warnings(self) -> list[SeriesQuality]:
        return [item for item in self.series if item.severity is Severity.WARNING]

    @property
    def passed(self) -> bool:
        return not self.failures

    def to_payload(self) -> dict[str, object]:
        return {
            "generated_at": self.generated_at,
            "passed": self.passed,
            "counts": {
                "total": len(self.series),
                "ok": len([i for i in self.series if i.severity is Severity.OK]),
                "warning": len(self.warnings),
                "failure": len(self.failures),
            },
            "series": [item.to_payload() for item in self.series],
        }


def _as_date(value: object) -> dt.date:
    """Coerce a value to a plain date, whatever the adapter produced."""
    if isinstance(value, dt.datetime):
        return value.date()
    if isinstance(value, dt.date):
        return value
    return dt.date.fromisoformat(str(value)[:10])


def _business_days_between(start: dt.date, end: dt.date) -> int:
    if end <= start:
        return 0
    days = 0
    cursor = start
    while cursor < end:
        cursor += dt.timedelta(days=1)
        if cursor.weekday() < 5:
            days += 1
    return days


def evaluate_series(
    result: FetchResult,
    policy: QualityPolicy | None = None,
    *,
    today: dt.date | None = None,
) -> SeriesQuality:
    """Evaluate every gate for one fetched series."""
    policy = policy or QualityPolicy()
    today = today or dt.date.today()

    quality = SeriesQuality(
        series_id=result.series_id,
        adapter=result.adapter,
        country_code=result.country_code,
        observations=len(result.observations),
        first_date=result.first_date.isoformat() if result.first_date else None,
        last_date=result.last_date.isoformat() if result.last_date else None,
    )

    for warning in result.warnings:
        quality.checks.append(
            QualityCheck(
                name="source_warning",
                passed=False,
                severity=Severity.WARNING,
                message=warning,
            )
        )

    if not result.observations:
        quality.checks.append(
            QualityCheck(
                name="has_observations",
                passed=False,
                severity=Severity.FAILURE,
                measured=0,
                threshold=policy.min_observations,
                message="the series contains no observations",
            )
        )
        return quality

    quality.checks.append(
        QualityCheck(
            name="has_observations",
            passed=True,
            severity=Severity.OK,
            measured=len(result.observations),
            threshold=policy.min_observations,
        )
    )

    if len(result.observations) < policy.min_observations:
        quality.checks.append(
            QualityCheck(
                name="enough_observations",
                passed=False,
                severity=Severity.FAILURE,
                measured=len(result.observations),
                threshold=policy.min_observations,
                message="the series is too short to support the configured methodology",
            )
        )

    dates = [observation.date for observation in result.observations]
    unique_dates = set(dates)
    if len(unique_dates) != len(dates):
        quality.checks.append(
            QualityCheck(
                name="unique_dates",
                passed=False,
                severity=Severity.FAILURE,
                measured=len(dates) - len(unique_dates),
                threshold=0,
                message="the series contains duplicated dates",
            )
        )
    else:
        quality.checks.append(
            QualityCheck(name="unique_dates", passed=True, severity=Severity.OK, measured=0)
        )

    if dates != sorted(dates):
        quality.checks.append(
            QualityCheck(
                name="ordered_dates",
                passed=False,
                severity=Severity.FAILURE,
                message="the observations are not in chronological order",
            )
        )
    else:
        quality.checks.append(QualityCheck(name="ordered_dates", passed=True, severity=Severity.OK))

    first, last = dates[0], dates[-1]
    first = _as_date(first)
    last = _as_date(last)
    span = _business_days_between(first, last)
    completeness = (len(unique_dates) / span) if span > 0 else 1.0
    if completeness < policy.min_completeness:
        quality.checks.append(
            QualityCheck(
                name="completeness",
                passed=False,
                severity=Severity.WARNING,
                measured=round(completeness, 4),
                threshold=policy.min_completeness,
                message="the series has gaps relative to its own calendar",
            )
        )
    else:
        quality.checks.append(
            QualityCheck(
                name="completeness",
                passed=True,
                severity=Severity.OK,
                measured=round(completeness, 4),
                threshold=policy.min_completeness,
            )
        )

    ordered_dates = sorted(unique_dates)
    gaps = [
        (later - earlier).days
        for earlier, later in zip(ordered_dates, ordered_dates[1:], strict=False)
        if later > earlier
    ]
    longest_gap = max(gaps) if gaps else 0
    if longest_gap > policy.max_gap_days:
        quality.checks.append(
            QualityCheck(
                name="max_gap",
                passed=False,
                severity=Severity.WARNING,
                measured=longest_gap,
                threshold=policy.max_gap_days,
                message="the series contains a long gap",
            )
        )
    else:
        quality.checks.append(
            QualityCheck(
                name="max_gap",
                passed=True,
                severity=Severity.OK,
                measured=longest_gap,
                threshold=policy.max_gap_days,
            )
        )

    staleness = (today - last).days
    if staleness > policy.max_staleness_days:
        quality.checks.append(
            QualityCheck(
                name="freshness",
                passed=False,
                severity=Severity.WARNING,
                measured=staleness,
                threshold=policy.max_staleness_days,
                message="the latest observation is stale",
            )
        )
    else:
        quality.checks.append(
            QualityCheck(
                name="freshness",
                passed=True,
                severity=Severity.OK,
                measured=staleness,
                threshold=policy.max_staleness_days,
            )
        )

    values = [observation.value for observation in result.observations]
    if policy.lower_bound is not None or policy.upper_bound is not None:
        below = policy.lower_bound is not None and min(values) < policy.lower_bound
        above = policy.upper_bound is not None and max(values) > policy.upper_bound
        if below or above:
            quality.checks.append(
                QualityCheck(
                    name="value_bounds",
                    passed=False,
                    severity=Severity.FAILURE,
                    measured=f"{min(values):.6g}..{max(values):.6g}",
                    threshold=f"{policy.lower_bound}..{policy.upper_bound}",
                    message="the series leaves its plausible range",
                )
            )
        else:
            quality.checks.append(
                QualityCheck(
                    name="value_bounds",
                    passed=True,
                    severity=Severity.OK,
                    measured=f"{min(values):.6g}..{max(values):.6g}",
                )
            )

    return quality


def evaluate_all(
    results: Iterable[FetchResult],
    policy: QualityPolicy | None = None,
    *,
    today: dt.date | None = None,
    generated_at: str | None = None,
) -> QualityReport:
    """Evaluate every fetched series and aggregate the verdict."""
    moment = generated_at or dt.datetime.now(dt.UTC).isoformat()
    series = [evaluate_series(result, policy, today=today) for result in results]
    return QualityReport(generated_at=moment, series=series)
