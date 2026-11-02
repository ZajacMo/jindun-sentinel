"""Rolling spill-out history and the surge test.

A spillover matrix is a statement about **one sample**.  The alerting question
is a different one: *did a market's spill-out rise sharply against its own
history?*  Answering it needs the network to be recomputed over a rolling
window, so that every market has a distribution of its own spill-out to be
compared with — exactly the same logic the composite index uses when it
reports a within-country percentile instead of a raw level.

The rolling history is deliberately coarse: the windows are wide (hundreds of
observations) and the step between them is large, because the quantity being
estimated is a slowly moving structural share, not a daily flow.  A daily
frequency here would produce a noisy series that fires on noise.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass

import numpy as np
import pandas as pd

from .gvd import GVDSpec, compute_spillover

__all__ = [
    "SurgeScore",
    "rolling_spillout_history",
    "spillout_surge_scores",
]


@dataclass(frozen=True, slots=True)
class SurgeScore:
    """How far the latest spill-out of one market sits above its own history."""

    market: str
    latest: float
    mean: float
    std: float
    zscore: float
    window_end: str
    windows: int

    def to_payload(self) -> dict[str, object]:
        return {
            "market": self.market,
            "latest": round(self.latest, 8),
            "mean": round(self.mean, 8),
            "std": round(self.std, 8),
            "zscore": round(self.zscore, 8),
            "window_end": self.window_end,
            "windows": self.windows,
        }


def rolling_spillout_history(
    data: pd.DataFrame,
    spec: GVDSpec | None = None,
    *,
    window: int = 500,
    step: int = 250,
    max_windows: int = 24,
    min_windows: int = 4,
) -> pd.DataFrame:
    """Return the rolling history of the total spill-out per node.

    The frame is indexed by the last observation of each window and holds one
    column per node.  The most recent windows are kept when the sample is
    longer than ``max_windows`` steps, because the recent past is what the
    alerting question is about.
    """
    spec = spec or GVDSpec()
    frame = data.dropna(how="any")
    rows: list[dict[str, object]] = []
    labels: list[str] = []
    if len(frame) < max(60, window // 2):
        return pd.DataFrame()

    # A sample shorter than the configured window cannot support it: the window
    # shrinks to a third of the sample and the step with it.  The effective
    # values are recorded in the frame attributes so that the artefact says
    # which window produced the numbers.
    length = len(frame)
    effective_window = min(int(window), max(60, length // 3))
    effective_step = max(1, min(int(step), effective_window // 2))

    starts = list(range(0, max(1, length - effective_window + 1), effective_step))
    # The last window always ends on the final observation: the surge test is
    # about the present, so the present must be in the history.
    last_start = max(0, length - effective_window)
    if not starts or starts[-1] != last_start:
        starts.append(last_start)
    if len(starts) > max_windows:
        starts = starts[-max_windows:]

    for start in starts:
        chunk = frame.iloc[start : start + effective_window]
        if len(chunk) < max(60, effective_window // 2):
            continue
        try:
            result = compute_spillover(chunk, spec)
        except Exception:  # noqa: BLE001 - a failed window must not stop the history
            continue
        if not result.total_spillout:
            continue
        rows.append(dict(result.total_spillout))
        labels.append(str(chunk.index[-1])[:10])

    if len(rows) < min_windows:
        return pd.DataFrame()

    history = pd.DataFrame(rows, index=pd.Index(labels, name="window_end"))
    history.attrs["window"] = effective_window
    history.attrs["step"] = effective_step
    return history


def spillout_surge_scores(history: pd.DataFrame) -> dict[str, SurgeScore]:
    """Score the latest window of a rolling history against its own history.

    The standard deviation is taken over the *whole* history including the
    latest window; with a handful of windows that is the more stable choice,
    and the z-score is meant to be a screening device rather than a test.

    The score is reported on its own; deciding whether it is a *surge* also
    needs a relative margin, because a z-score over a flat series is large
    for a negligible absolute change.  :func:`surging_markets` applies both
    conditions.
    """
    if history.empty or len(history) < 2:
        return {}

    latest = history.iloc[-1]
    scores: dict[str, SurgeScore] = {}
    window_end = str(history.index[-1])
    for column in history.columns:
        values = history[column].to_numpy(dtype=float)
        values = values[np.isfinite(values)]
        if len(values) < 2:
            continue
        mean = float(np.mean(values))
        std = float(np.std(values, ddof=1))
        value = float(latest[column])
        if not np.isfinite(value):
            continue
        zscore = (value - mean) / std if std > 1e-12 else 0.0
        scores[str(column)] = SurgeScore(
            market=str(column),
            latest=value,
            mean=mean,
            std=std,
            zscore=float(zscore),
            window_end=window_end,
            windows=int(len(values)),
        )
    return scores


def surging_markets(
    scores: Mapping[str, SurgeScore],
    threshold: float,
    *,
    min_relative_change: float = 0.0,
) -> Sequence[str]:
    """Return the markets whose surge score reaches ``threshold``.

    Two conditions have to hold at the same time: the z-score against the
    market's own history reaches ``threshold``, **and** the latest value is at
    least ``min_relative_change`` above its historical mean.  The second
    condition keeps a nearly flat series from producing a large z-score on a
    negligible absolute move.
    """
    selected: list[str] = []
    for market, score in scores.items():
        if score.zscore < threshold:
            continue
        relative = (score.latest - score.mean) / abs(score.mean) if score.mean else 0.0
        if relative < min_relative_change:
            continue
        selected.append(market)
    return tuple(sorted(selected, key=lambda market: -scores[market].zscore))
