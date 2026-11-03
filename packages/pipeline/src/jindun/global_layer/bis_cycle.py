"""The BIS inputs of the global financial cycle factor.

Layer L3 of the global layer is a *global financial cycle* factor in the sense
of Bruno & Shin (2014) and Miranda-Agrippino & Rey (2020): a single common
driver built from global credit and currency conditions.  The country-panel
principal component that earlier releases published under this name is a
different object -- it is the aggregate of the monitored indices, which is
layer L1 -- so it is kept as a cross-check instead of being called the cycle.

Three BIS flows are read, all through the bulk flat files:

``WS_GLI``
    Global liquidity indicators.  Supplies the year-on-year growth of global
    cross-border bank claims on non-bank borrowers, in total, in US dollars
    and in euros.
``WS_CREDIT_GAP``
    Credit-to-GDP gaps.  Supplies the credit gap of every monitored economy.
``WS_EER``
    Effective exchange rates.  Supplies the broad nominal effective exchange
    rate of the United States, whose year-on-year change measures how tight
    the global dollar is.

Two properties of the published files were verified against the live service
and both change how the files must be read:

**The flat file of a flow can carry more than one frequency.**  ``WS_EER``
contains a daily block (``YYYY-MM-DD``, 1996-04-11 to 2026-10-27) *and* a
monthly block (``YYYY-MM``, 1994-01 to 2026-09) appended after it.  The two
blocks overlap in calendar time, so a parser that accepts both formats
silently puts a monthly average and a daily observation into the same
quarter.  Only the daily block is read here, and the rule is stated in the
artefact.

**The last quarter of every flow is usually incomplete.**  A statistical
office publishes what it has, so the current quarter arrives half-finished.
A quarter is only accepted when the series was observed up to its end, which
keeps a half-published quarter from entering the factor as if it were whole.

Every selection is made on the publisher's own dimension codes, and the title
the publisher gives the selected series is carried into the artefact, so a
reader can check the selection without reading this module.
"""

from __future__ import annotations

import calendar
import csv
import datetime as dt
import io
import zipfile
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pandas as pd

from ..adapters.base import HttpClient

__all__ = [
    "BIS_BULK_BASE",
    "CycleInputs",
    "SeriesSelection",
    "build_cycle_inputs",
    "credit_gap_selection",
    "download_bulk",
    "select_rows",
]

BIS_BULK_BASE = "https://data.bis.org/static/bulk"

#: A quarter is accepted when the series was observed within this many days of
#: the quarter end.  Ten days covers a normal holiday week and still rejects a
#: quarter that is only half published.
QUARTER_COMPLETENESS_DAYS = 10

#: The dimensions of the flows this module reads, in the order the data
#: structure definition lists them.  The flat files name every dimension as
#: ``CODE: Name``; the code is what a selection is written against.
GLI_DIMENSIONS = (
    "FREQ",
    "CURR_DENOM",
    "BORROWERS_CTY",
    "BORROWERS_SECTOR",
    "LENDERS_SECTOR",
    "L_POS_TYPE",
    "L_INSTR",
    "UNIT_MEASURE",
)
CREDIT_GAP_DIMENSIONS = ("FREQ", "BORROWERS_CTY", "TC_BORROWERS", "TC_LENDERS", "CG_DTYPE")
EER_DIMENSIONS = ("FREQ", "EER_TYPE", "EER_BASKET", "REF_AREA")


@dataclass(frozen=True, slots=True)
class SeriesSelection:
    """One selected series of a BIS flow.

    The selectors are the publisher's dimension codes; the title is the name
    the publisher gives the series, which is what a reader checks.
    """

    name: str
    flow: str
    selectors: Mapping[str, str]
    title: str
    unit: str
    frequency: str = "Q"
    transform: str = "level"


@dataclass(slots=True)
class CycleInputs:
    """The aligned input block of the global cycle factor."""

    frame: pd.DataFrame = field(default_factory=pd.DataFrame)
    metadata: list[dict[str, Any]] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    @property
    def observations(self) -> int:
        return int(len(self.frame))


# ---------------------------------------------------------------------------
# The published selections
# ---------------------------------------------------------------------------

#: Cross-border bank claims on all countries, non-banks, year-on-year change.
GLOBAL_CREDIT_SELECTION = SeriesSelection(
    name="global_credit_yoy",
    flow="WS_GLI",
    selectors={
        "CURR_DENOM": "TO1",
        "BORROWERS_CTY": "5J",
        "BORROWERS_SECTOR": "N",
        "LENDERS_SECTOR": "B",
        "L_POS_TYPE": "N",
        "L_INSTR": "A",
        "UNIT_MEASURE": "771",
    },
    title="Cross-border bank claims on All countries (total), non-banks",
    unit="year-on-year change, per cent",
)

#: US dollar credit to non-bank borrowers outside the United States.
USD_CREDIT_SELECTION = SeriesSelection(
    name="usd_credit_yoy",
    flow="WS_GLI",
    selectors={
        "CURR_DENOM": "USD",
        "BORROWERS_CTY": "3P",
        "BORROWERS_SECTOR": "N",
        "LENDERS_SECTOR": "A",
        "L_POS_TYPE": "I",
        "L_INSTR": "B",
        "UNIT_MEASURE": "771",
    },
    title=(
        "USD denominated credit (bank loans & debt securities) to non-bank "
        "borrowers located outside the US"
    ),
    unit="year-on-year change, per cent",
)

#: Euro credit to non-bank borrowers outside the euro area.
EUR_CREDIT_SELECTION = SeriesSelection(
    name="eur_credit_yoy",
    flow="WS_GLI",
    selectors={
        "CURR_DENOM": "EUR",
        "BORROWERS_CTY": "3P",
        "BORROWERS_SECTOR": "N",
        "LENDERS_SECTOR": "A",
        "L_POS_TYPE": "I",
        "L_INSTR": "B",
        "UNIT_MEASURE": "771",
    },
    title=(
        "EUR denominated credit (bank loans & debt securities) to non-bank "
        "borrowers located outside the euro area"
    ),
    unit="year-on-year change, per cent",
)


def credit_gap_selection(economy: str) -> SeriesSelection:
    """Return the credit-to-GDP gap of one economy.

    ``CG_DTYPE=C`` is the published gap: the ratio of credit to GDP minus its
    own trend.  A positive gap means credit is above trend, which is the
    configuration that precedes financial stress.
    """
    code = economy.strip().upper()
    return SeriesSelection(
        name=f"credit_gap_{code.lower()}",
        flow="WS_CREDIT_GAP",
        selectors={
            "BORROWERS_CTY": code,
            "TC_BORROWERS": "P",
            "TC_LENDERS": "A",
            "CG_DTYPE": "C",
        },
        title=f"Credit-to-GDP gap, {code}",
        unit="percentage points of GDP",
    )


def effective_exchange_rate_selection(reference_area: str, basket: str = "B") -> SeriesSelection:
    """Return the broad nominal effective exchange rate of one economy.

    The broad basket covers 64 economies and the narrow one 27.  A rising
    index means the currency is appreciating, which for the dollar means the
    global dollar is tightening.
    """
    code = reference_area.strip().upper()
    basket_code = basket.strip().upper()
    label = {"B": "Broad (64 economies)", "N": "Narrow (27 economies)"}.get(
        basket_code, basket_code
    )
    return SeriesSelection(
        name=f"eer_{code.lower()}_yoy",
        flow="WS_EER",
        selectors={"EER_TYPE": "N", "EER_BASKET": basket_code, "REF_AREA": code},
        title=f"Nominal effective exchange rate, {code}, {label}",
        unit="index, 2020 = 100",
        frequency="D",
        transform="yoy",
    )


# ---------------------------------------------------------------------------
# Reading the published files
# ---------------------------------------------------------------------------


def bulk_archive_path(flow: str, *, cache_dir: str | Path | None = None) -> Path:
    """Return the local path of a flow's bulk archive."""
    from .. import paths

    root = Path(cache_dir) if cache_dir is not None else paths.cache_dir() / "bis"
    return root / f"{flow}_csv_flat.zip"


def download_bulk(
    flow: str,
    *,
    cache_dir: str | Path | None = None,
    client: HttpClient | None = None,
    force: bool = False,
) -> Path:
    """Download a flow's bulk flat file into the cache and return its path.

    The cache is git-ignored: these files are large enough to matter for a
    clone (the effective exchange rate file alone holds 1.2 million rows) and
    they are reproducible from the publisher's own endpoint.
    """
    target = bulk_archive_path(flow, cache_dir=cache_dir)
    if target.exists() and not force:
        return target
    target.parent.mkdir(parents=True, exist_ok=True)
    http = client or HttpClient(timeout=300.0)
    response = http.get(f"{BIS_BULK_BASE}/{flow}_csv_flat.zip")
    target.write_bytes(response.body)
    return target


def select_rows(path: Path, selectors: Mapping[str, str]) -> list[dict[str, str]]:
    """Return the rows of a flat file that match every selector.

    A cell carries both the dimension code and its label, for example
    ``CURR_DENOM: US dollar``.  The selection is written against the code.
    """
    matches: list[dict[str, str]] = []
    with zipfile.ZipFile(path) as archive:
        members = [name for name in archive.namelist() if name.lower().endswith(".csv")]
        if not members:
            raise ValueError(f"the archive holds no CSV member: {path}")
        with archive.open(members[0]) as handle:
            reader = csv.reader(io.TextIOWrapper(handle, encoding="utf-8-sig", errors="replace"))
            header = next(reader)
            positions: dict[str, int] = {}
            for position, column in enumerate(header):
                positions.setdefault(column.split(":", 1)[0].strip(), position)
            missing = [code for code in selectors if code not in positions]
            if missing:
                raise ValueError(f"{path.name} has no dimension {missing}")
            time_position = positions["TIME_PERIOD"]
            value_position = positions["OBS_VALUE"]
            title_position = positions.get("TITLE", positions.get("TITLE_TS"))
            for row in reader:
                if len(row) <= max(positions[code] for code in selectors):
                    continue
                if not all(
                    row[positions[code]].split(":", 1)[0].strip() == expected
                    for code, expected in selectors.items()
                ):
                    continue
                period = row[time_position].strip()
                value = row[value_position].strip()
                if not period or not value:
                    continue
                matches.append(
                    {
                        "TIME_PERIOD": period,
                        "OBS_VALUE": value,
                        "TITLE": row[title_position].strip() if title_position is not None else "",
                    }
                )
    return matches


def _parse_period(period: str) -> tuple[str, dt.date] | None:
    """Return the kind and the end date of a published period.

    ``2025-Q4`` is a quarter, ``2026-09`` a month and ``2026-10-27`` a day.
    The kinds are kept apart because the effective exchange rate file carries
    a monthly block and a daily block at the same time.
    """
    text = period.strip()
    if not text:
        return None
    if "-Q" in text:
        year, _, quarter = text.partition("-Q")
        try:
            year_number = int(year)
            quarter_number = int(quarter)
        except ValueError:
            return None
        if not 1 <= quarter_number <= 4:
            return None
        month = quarter_number * 3
        return "Q", dt.date(year_number, month, calendar.monthrange(year_number, month)[1])
    parts = text.split("-")
    try:
        if len(parts) == 2:
            year_number, month_number = int(parts[0]), int(parts[1])
            return "M", dt.date(
                year_number, month_number, calendar.monthrange(year_number, month_number)[1]
            )
        if len(parts) == 3:
            return "D", dt.date(int(parts[0]), int(parts[1]), int(parts[2]))
    except ValueError:
        return None
    return None


def _quarterly_series(
    rows: Sequence[Mapping[str, str]], selection: SeriesSelection
) -> tuple[pd.Series, str]:
    """Turn the selected rows of a quarterly flow into a series."""
    points: list[tuple[dt.date, float]] = []
    titles: set[str] = set()
    for row in rows:
        parsed = _parse_period(row.get("TIME_PERIOD", ""))
        if parsed is None or parsed[0] != "Q":
            continue
        try:
            value = float(row.get("OBS_VALUE", ""))
        except ValueError:
            continue
        points.append((parsed[1], value))
        if row.get("TITLE"):
            titles.add(str(row["TITLE"]))
    index = pd.DatetimeIndex([moment for moment, _ in points])
    series = pd.Series([value for _, value in points], index=index, name=selection.name)
    series = series[~series.index.duplicated(keep="last")].sort_index()
    return series, "; ".join(sorted(titles))


def _daily_series(
    rows: Sequence[Mapping[str, str]], selection: SeriesSelection
) -> tuple[pd.Series, str]:
    """Turn the selected rows of a daily flow into a series.

    Only the daily block of the file is read.  The monthly block that the
    effective exchange rate file also carries would put a monthly average and
    a daily observation into the same quarter.
    """
    points: list[tuple[dt.date, float]] = []
    titles: set[str] = set()
    for row in rows:
        parsed = _parse_period(row.get("TIME_PERIOD", ""))
        if parsed is None or parsed[0] != "D":
            continue
        try:
            value = float(row.get("OBS_VALUE", ""))
        except ValueError:
            continue
        points.append((parsed[1], value))
        if row.get("TITLE"):
            titles.add(str(row["TITLE"]))
    index = pd.DatetimeIndex([moment for moment, _ in points])
    series = pd.Series([value for _, value in points], index=index, name=selection.name)
    series = series[~series.index.duplicated(keep="last")].sort_index()
    return series, "; ".join(sorted(titles))


def _resample_to_quarter_end(daily: pd.Series) -> pd.Series:
    """Keep the last observation of every fully observed quarter.

    A quarter is kept only when the series reached its end: the last BIS
    release stops in the middle of the current quarter, and that half
    quarter must not enter a factor as if it were complete.
    """
    clean = daily.dropna().sort_index()
    if clean.empty:
        return clean
    frame = clean.to_frame("value")
    frame["quarter"] = frame.index.to_period("Q")
    values = frame.groupby("quarter")["value"].last()
    last_dates = frame.groupby("quarter")["value"].apply(lambda column: column.index[-1])
    ends = last_dates.index.to_timestamp(how="end").normalize()
    distance = (ends - last_dates.to_numpy()).days
    complete = pd.Series(distance, index=values.index) <= QUARTER_COMPLETENESS_DAYS
    result = values[complete]
    # The quarterly flows are indexed by the end of the quarter, so the
    # resampled daily series has to carry the same index type.
    result.index = pd.DatetimeIndex(result.index.to_timestamp(how="end").normalize())
    # The resampling works on an internal frame, so the name of the series is
    # lost on the way; the input block is built from those names.
    result.name = daily.name
    return result


def _year_on_change(quarterly: pd.Series, periods: int = 4) -> pd.Series:
    """Return the year-on-year change of a quarterly series, in per cent."""
    if quarterly.empty:
        return quarterly
    return (quarterly / quarterly.shift(periods) - 1.0) * 100.0


# ---------------------------------------------------------------------------
# The input block
# ---------------------------------------------------------------------------


def build_cycle_inputs(
    *,
    credit_gap_economies: Sequence[str],
    dollar_reference_area: str = "US",
    eer_basket: str = "B",
    cache_dir: str | Path | None = None,
    use_cache: bool = True,
    client: HttpClient | None = None,
) -> CycleInputs:
    """Build the aligned input block of the global cycle factor.

    The block is the intersection of every selected series, so its window is
    the window all of them share.  When one economy's credit gap starts
    later than the others, that economy — not the data quality of any other
    series — sets the start of the factor, and the artefact says so.
    """
    selections: list[SeriesSelection] = [
        GLOBAL_CREDIT_SELECTION,
        USD_CREDIT_SELECTION,
        EUR_CREDIT_SELECTION,
    ]
    selections.extend(credit_gap_selection(code) for code in credit_gap_economies)
    selections.append(effective_exchange_rate_selection(dollar_reference_area, eer_basket))

    archives: dict[str, Path] = {}
    for flow in sorted({selection.flow for selection in selections}):
        archives[flow] = download_bulk(
            flow,
            cache_dir=cache_dir,
            client=client,
            force=not use_cache,
        )

    series: list[pd.Series] = []
    metadata: list[dict[str, Any]] = []
    notes: list[str] = []

    for selection in selections:
        rows = select_rows(archives[selection.flow], selection.selectors)
        if not rows:
            notes.append(f"the {selection.flow} series {selection.name!r} matched no published row")
            continue
        if selection.frequency == "D":
            daily, title = _daily_series(rows, selection)
            quarterly = _resample_to_quarter_end(daily)
            values = _year_on_change(quarterly) if selection.transform == "yoy" else quarterly
            raw_first = daily.index[0].date().isoformat() if not daily.empty else ""
            raw_last = daily.index[-1].date().isoformat() if not daily.empty else ""
        else:
            values, title = _quarterly_series(rows, selection)
            raw_first = values.index[0].date().isoformat() if not values.empty else ""
            raw_last = values.index[-1].date().isoformat() if not values.empty else ""
        if values.dropna().empty:
            notes.append(f"the {selection.flow} series {selection.name!r} carries no usable value")
            continue
        series.append(values)
        metadata.append(
            {
                "name": selection.name,
                "flow": selection.flow,
                "title": title or selection.title,
                "unit": selection.unit,
                "transform": selection.transform,
                "selectors": dict(selection.selectors),
                "source_url": f"{BIS_BULK_BASE}/{selection.flow}_csv_flat.zip",
                "first": raw_first,
                "last": raw_last,
                "observations": int(values.notna().sum()),
            }
        )

    if not series:
        return CycleInputs(metadata=metadata, notes=notes + ["no BIS input could be read"])

    frame = pd.concat(series, axis=1).sort_index()
    complete = frame.dropna(how="any")
    if complete.empty:
        notes.append(
            "the selected BIS series share no common quarter; the factor cannot be estimated"
        )
        return CycleInputs(frame=frame, metadata=metadata, notes=notes)

    dropped = len(frame) - len(complete)
    if dropped:
        notes.append(f"{dropped} quarter(s) were dropped because at least one input was missing")
    notes.append(
        f"the common window is {complete.index[0].date().isoformat()} to "
        f"{complete.index[-1].date().isoformat()} ({len(complete)} quarters)"
    )

    return CycleInputs(frame=complete, metadata=metadata, notes=notes)
