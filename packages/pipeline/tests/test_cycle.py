"""Tests for the global financial cycle factor and its BIS inputs."""

from __future__ import annotations

import csv
import datetime as dt
import io
import json
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from jindun.global_layer.bis_cycle import (
    CycleInputs,
    _daily_series,
    _parse_period,
    _quarterly_series,
    _resample_to_quarter_end,
    _year_on_change,
    credit_gap_selection,
    effective_exchange_rate_selection,
    select_rows,
)
from jindun.global_layer.cycle import build_global_cycle


# ----------------------------------------------------------------------
# Period parsing
# ----------------------------------------------------------------------
def test_a_quarter_period_becomes_the_end_of_the_quarter() -> None:
    assert _parse_period("2025-Q4") == ("Q", dt.date(2025, 12, 31))
    assert _parse_period("2025-Q1") == ("Q", dt.date(2025, 3, 31))
    assert _parse_period("2024-Q2") == ("Q", dt.date(2024, 6, 30))


def test_a_month_period_becomes_the_end_of_the_month() -> None:
    assert _parse_period("2025-09") == ("M", dt.date(2025, 9, 30))
    assert _parse_period("2024-02") == ("M", dt.date(2024, 2, 29))


def test_a_day_period_keeps_its_date() -> None:
    assert _parse_period("2026-10-27") == ("D", dt.date(2026, 10, 27))


def test_an_unusable_period_is_rejected() -> None:
    assert _parse_period("") is None
    assert _parse_period("not-a-period") is None
    assert _parse_period("2025-Q9") is None


# ----------------------------------------------------------------------
# Reading the published files
# ----------------------------------------------------------------------
def _write_flat_csv(path: Path, header: list[str], rows: list[list[str]]) -> Path:
    """Write a BIS-style flat CSV into a zip archive and return its path."""
    path.parent.mkdir(parents=True, exist_ok=True)
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(header)
    writer.writerows(rows)
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("flow_csv_flat.csv", buffer.getvalue())
    return path


def test_a_selection_matches_on_the_dimension_code(tmp_path: Path) -> None:
    header = [
        "FREQ:Frequency",
        "CURR_DENOM:Currency of denomination",
        "TIME_PERIOD:Time period or range",
        "OBS_VALUE:Observation Value",
        "TITLE:Title",
    ]
    rows = [
        ["Q: Quarterly", "USD: US dollar", "2025-Q1", "1.5", "a dollar series"],
        ["Q: Quarterly", "EUR: Euro", "2025-Q1", "2.5", "a euro series"],
        ["Q: Quarterly", "USD: US dollar", "2025-Q2", "3.5", "a dollar series"],
    ]
    archive = _write_flat_csv(tmp_path / "WS_GLI_csv_flat.zip", header, rows)

    matched = select_rows(archive, {"CURR_DENOM": "USD"})

    assert [row["TIME_PERIOD"] for row in matched] == ["2025-Q1", "2025-Q2"]
    assert [row["OBS_VALUE"] for row in matched] == ["1.5", "3.5"]


def test_an_unknown_dimension_is_reported(tmp_path: Path) -> None:
    header = ["TIME_PERIOD:Time period or range", "OBS_VALUE:Observation Value"]
    archive = _write_flat_csv(tmp_path / "WS_GLI_csv_flat.zip", header, [["2025-Q1", "1.0"]])

    with pytest.raises(ValueError, match="no dimension"):
        select_rows(archive, {"CURR_DENOM": "USD"})


def test_the_monthly_block_of_a_daily_file_is_not_mixed_in(tmp_path: Path) -> None:
    """The effective exchange rate file carries a daily and a monthly block.

    Only the daily block may enter the factor: the monthly block overlaps it
    in calendar time, so accepting both would put a monthly average and a
    daily observation into the same quarter.
    """
    header = [
        "EER_TYPE:Type",
        "EER_BASKET:Basket",
        "REF_AREA:Reference area",
        "TIME_PERIOD:Time period or range",
        "OBS_VALUE:Observation Value",
    ]
    rows = [
        ["N: Nominal", "B: Broad (64 economies)", "US: United States", "2025-01-02", "100.0"],
        ["N: Nominal", "B: Broad (64 economies)", "US: United States", "2025-01-03", "101.0"],
        ["N: Nominal", "B: Broad (64 economies)", "US: United States", "2025-01", "99.0"],
    ]
    archive = _write_flat_csv(tmp_path / "WS_EER_csv_flat.zip", header, rows)
    selection = effective_exchange_rate_selection("US", "B")

    daily, _ = _daily_series(select_rows(archive, selection.selectors), selection)

    assert len(daily) == 2
    assert daily.index[0] == pd.Timestamp("2025-01-02")


def test_a_quarterly_selection_keeps_only_the_quarterly_rows() -> None:
    selection = credit_gap_selection("US")
    rows = [
        {"TIME_PERIOD": "2025-Q1", "OBS_VALUE": "1.0", "TITLE": "gap"},
        {"TIME_PERIOD": "2025-01", "OBS_VALUE": "2.0", "TITLE": "gap"},
    ]

    series, title = _quarterly_series(rows, selection)

    assert len(series) == 1
    assert series.index[0] == pd.Timestamp("2025-03-31")
    assert title == "gap"


# ----------------------------------------------------------------------
# Resampling
# ----------------------------------------------------------------------
def test_an_unfinished_quarter_is_dropped() -> None:
    """The last BIS release stops in the middle of the current quarter."""
    index = pd.to_datetime(["2025-09-29", "2025-09-30", "2025-10-01", "2025-10-02", "2025-10-03"])
    daily = pd.Series([1.0, 2.0, 3.0, 4.0, 5.0], index=index, name="eer_us_yoy")

    quarterly = _resample_to_quarter_end(daily)

    assert len(quarterly) == 1
    assert quarterly.index[0] == pd.Timestamp("2025-09-30")
    assert quarterly.iloc[0] == 2.0


def test_the_resampled_series_keeps_its_name() -> None:
    index = pd.to_datetime(["2025-09-29", "2025-09-30"])
    daily = pd.Series([1.0, 2.0], index=index, name="eer_us_yoy")

    quarterly = _resample_to_quarter_end(daily)

    assert quarterly.name == "eer_us_yoy"


def test_the_year_on_change_compares_four_quarters() -> None:
    index = pd.date_range("2024-01-31", periods=6, freq="QE")
    quarterly = pd.Series([100.0, 101.0, 102.0, 110.0, 111.0, 121.0], index=index)

    change = _year_on_change(quarterly)

    assert np.isnan(change.iloc[3])
    assert change.iloc[4] == pytest.approx(11.0)
    assert change.iloc[5] == pytest.approx(19.801980198019802)


# ----------------------------------------------------------------------
# The factor
# ----------------------------------------------------------------------
def _input_frame(periods: int = 60) -> pd.DataFrame:
    """A synthetic input block with a known common structure."""
    index = pd.date_range("2015-03-31", periods=periods, freq="QE")
    generator = np.random.default_rng(20261103)
    common = generator.normal(size=periods)
    frame = pd.DataFrame(
        {
            "global_credit_yoy": common * 2.0 + generator.normal(scale=0.2, size=periods),
            "usd_credit_yoy": common * 2.4 + generator.normal(scale=0.2, size=periods),
            "eur_credit_yoy": common * 0.8 + generator.normal(scale=0.4, size=periods),
            "credit_gap_us": common * 1.6 + generator.normal(scale=0.3, size=periods),
            "credit_gap_cn": common * 0.4 + generator.normal(scale=0.5, size=periods),
            "eer_us_yoy": generator.normal(size=periods),
        },
        index=index,
    )
    return frame


def test_the_factor_is_oriented_on_the_credit_gap() -> None:
    frame = _input_frame()
    inputs = CycleInputs(frame=frame, metadata=[], notes=[])

    cycle = build_global_cycle(inputs, {})

    assert cycle.observations == len(frame)
    anchor = frame[[name for name in frame.columns if name.startswith("credit_gap_")]].mean(axis=1)
    correlation = float(np.corrcoef(cycle.factor, anchor.to_numpy())[0, 1])
    assert correlation > 0
    # The orientation is a set of facts, not a sentence: the wording belongs to
    # the catalogue, the direction is read off the estimated loadings.  The
    # anchor the factor is oriented on is the mean of the *standardised* gaps,
    # which is not the same series as the mean of the raw ones.
    standardised = (frame - frame.mean()) / frame.std(ddof=0).replace(0.0, np.nan)
    standardised_anchor = standardised[
        [name for name in standardised.columns if name.startswith("credit_gap_")]
    ].mean(axis=1)
    expected = float(np.corrcoef(cycle.factor, standardised_anchor.to_numpy())[0, 1])
    assert cycle.orientation["anchor"] == "credit_gap_mean"
    assert cycle.orientation["correlation"] == pytest.approx(expected, abs=1e-6)
    assert cycle.orientation["gap_direction"] in {"wider", "narrower"}


def test_the_loadings_are_reported_for_every_input() -> None:
    frame = _input_frame()
    inputs = CycleInputs(frame=frame, metadata=[], notes=[])

    cycle = build_global_cycle(inputs, {})

    assert set(cycle.loadings) == set(frame.columns)
    assert cycle.explained_variance_ratio[0] > 0
    assert cycle.cumulative_variance_ratio[0] == pytest.approx(cycle.explained_variance_ratio[0])


def test_an_orthogonal_input_is_reported_as_such() -> None:
    frame = _input_frame()
    inputs = CycleInputs(frame=frame, metadata=[], notes=[])

    cycle = build_global_cycle(inputs, {})

    assert any(note.key == "cycle.note.weakInputs" for note in cycle.notes)


def test_an_empty_input_block_is_reported_not_raised() -> None:
    inputs = CycleInputs(frame=pd.DataFrame(), metadata=[], notes=[])

    cycle = build_global_cycle(inputs, {})

    assert cycle.factor == []
    assert cycle.observations == 0
    assert any(note.key == "cycle.note.notEstimated" for note in cycle.notes)


def test_the_cross_check_correlates_with_the_country_panel() -> None:
    frame = _input_frame()
    inputs = CycleInputs(frame=frame, metadata=[], notes=[])
    index = pd.date_range("2015-01-01", periods=800, freq="B")
    composites = {
        "CN": pd.Series(np.linspace(0, 1, 800), index=index),
        "US": pd.Series(np.linspace(1, 0, 800), index=index),
    }

    cycle = build_global_cycle(inputs, composites)

    cross = cycle.cross_check
    assert cross["available"] is True
    assert cross["observations"] > 0
    assert -1.0 <= cross["correlation"] <= 1.0
    assert cross["panel_factor"]["observations"] > 0


def test_the_cross_check_states_its_absence() -> None:
    frame = _input_frame()
    inputs = CycleInputs(frame=frame, metadata=[], notes=[])

    cycle = build_global_cycle(inputs, {})

    assert cycle.cross_check["available"] is False
    assert cycle.cross_check["reason"]


def test_the_artefact_is_writable_as_json() -> None:
    """Every note of the payload must already be a payload, not an object.

    The global layer writes the cycle artefact with ``json.dumps``.  A note
    that stayed a ``Message`` object would take the whole layer down, so the
    payload is written once here, with the cross-check included — that is
    where a note was missed.
    """
    frame = _input_frame()
    inputs = CycleInputs(frame=frame, metadata=[], notes=[])
    index = pd.date_range("2015-01-01", periods=800, freq="B")
    composites = {
        "CN": pd.Series(np.linspace(0, 1, 800), index=index),
        "US": pd.Series(np.linspace(1, 0, 800), index=index),
    }

    cycle = build_global_cycle(inputs, composites)
    payload = cycle.to_payload()

    json.dumps(payload)
    for note in payload["notes"]:
        assert set(note) == {"key", "params"}
    for note in payload["cross_check"]["notes"]:
        assert set(note) == {"key", "params"}
