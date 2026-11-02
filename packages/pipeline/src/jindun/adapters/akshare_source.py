"""Adapter for Chinese market data through ``akshare``.

``akshare`` is an optional dependency: the pipeline installs without it and
degrades to "this indicator is unavailable" instead of failing.  That matters
because the Chinese tertiary indicators are the only part of the system that
depends on a third-party scraper; every other source is an official API.

Only series whose output shape was **verified against the live service** are
registered here.  A series that is not registered is reported as unavailable
with a warning, and the quality gate turns that into a visible gap rather
than a silent zero.

Two layers are provided:

``base``
    A direct read of one upstream table, for example the ChinaBond yield
    curve or the SHIBOR fixing table.

``derived``
    A deterministic transformation of base series — a spread between two
    tenors, a rolling volatility, a year-on-year deviation.  Deriving them in
    the pipeline rather than in the configuration keeps the calculation
    reproducible and testable.
"""

from __future__ import annotations

import contextlib
import datetime as dt
import io
import sys
from dataclasses import dataclass
from typing import Callable, Mapping

import numpy as np
import pandas as pd

from .base import FetchResult, SnapshotStore

__all__ = ["AkshareAdapter", "AkshareSeries", "BASE_SERIES", "DERIVED_SERIES"]


@contextlib.contextmanager
def _quiet():
    """Silence the progress bars that some upstream tables draw.

    The pipeline's own output is meant to be machine readable, so the
    scraper's progress bar is redirected into a buffer.
    """
    buffer = io.StringIO()
    with contextlib.redirect_stderr(buffer), contextlib.redirect_stdout(buffer):
        yield


@dataclass(frozen=True, slots=True)
class AkshareSeries:
    """Description of one registered series."""

    series_id: str
    description: str
    frequency: str = "D"
    unit: str = ""
    transform: str = "level"


def _require_akshare():
    try:
        import akshare as ak
    except ImportError as exc:  # pragma: no cover - optional dependency
        raise RuntimeError(
            "the akshare extra is not installed; run `uv sync --extra market` "
            "to enable the Chinese market data sources"
        ) from exc
    return ak


_CGB_CACHE: "pd.DataFrame | None" = None


# ----------------------------------------------------------------------
# Base readers.  Each one returns a pandas Series indexed by date.
# ----------------------------------------------------------------------


def _index_close(symbol: str) -> pd.Series:
    ak = _require_akshare()
    with _quiet():
        frame = ak.stock_zh_index_daily(symbol=symbol)
    frame = frame.rename(columns={"date": "date"})
    frame["date"] = pd.to_datetime(frame["date"])
    return frame.set_index("date")["close"].astype(float)


def _index_volume(symbol: str) -> pd.Series:
    ak = _require_akshare()
    with _quiet():
        frame = ak.stock_zh_index_daily(symbol=symbol)
    frame["date"] = pd.to_datetime(frame["date"])
    return frame.set_index("date")["volume"].astype(float)


def _cgb_curve(start_year: int = 2010) -> pd.DataFrame:
    """The ChinaBond government yield curve, one column per tenor.

    The upstream table only answers windows of about one year at a time — a
    multi-year request returns an empty frame — so the curve is assembled
    year by year and cached in memory for the duration of the run.
    """
    global _CGB_CACHE
    if _CGB_CACHE is not None:
        return _CGB_CACHE

    ak = _require_akshare()
    end_year = dt.date.today().year
    frames: list[pd.DataFrame] = []
    for year in range(start_year, end_year + 1):
        with _quiet():
            frame = ak.bond_china_yield(
                start_date=f"{year}0101", end_date=f"{year}1231"
            )
        if frame is None or frame.empty:
            continue
        frame = frame.rename(columns={"日期": "date", "曲线名称": "curve"})
        frame["date"] = pd.to_datetime(frame["date"])
        government = frame[
            frame["curve"].astype(str).str.contains("中债国债收益率曲线")
        ]
        if government.empty:
            government = frame
        frames.append(government)

    if not frames:
        _CGB_CACHE = pd.DataFrame()
        return _CGB_CACHE

    combined = pd.concat(frames, axis=0)
    combined = combined[~combined["date"].duplicated(keep="last")].sort_values("date")
    _CGB_CACHE = combined.set_index("date")
    return _CGB_CACHE


def _cgb_tenor(tenor: str) -> pd.Series:
    """One tenor of the ChinaBond government bond yield curve."""
    curve = _cgb_curve()
    if curve.empty or tenor not in curve.columns:
        return pd.Series(dtype=float)
    return curve[tenor].astype(float)


def _shibor(column: str) -> pd.Series:
    ak = _require_akshare()
    with _quiet():
        frame = ak.macro_china_shibor_all()
    frame = frame.rename(columns={"日期": "date"})
    frame["date"] = pd.to_datetime(frame["date"])
    return frame.set_index("date")[column].astype(float)


def _margin(column: str) -> pd.Series:
    ak = _require_akshare()
    with _quiet():
        frame = ak.macro_china_market_margin_sh()
    frame = frame.rename(columns={"日期": "date"})
    frame["date"] = pd.to_datetime(frame["date"])
    return frame.set_index("date")[column].astype(float)


def _futures_close(symbol: str) -> pd.Series:
    ak = _require_akshare()
    with _quiet():
        frame = ak.futures_zh_daily_sina(symbol=symbol)
    frame["date"] = pd.to_datetime(frame["date"])
    return frame.set_index("date")["close"].astype(float)


def _currency_boc(symbol: str) -> pd.Series:
    """A Bank of China currency series (USD/CNY middle rate)."""
    ak = _require_akshare()
    end = dt.date.today()
    start = end - dt.timedelta(days=365 * 12)
    with _quiet():
        frame = ak.currency_boc_sina(
            symbol=symbol,
            start_date=start.strftime("%Y%m%d"),
            end_date=end.strftime("%Y%m%d"),
        )
    frame = frame.rename(columns={"日期": "date"})
    frame["date"] = pd.to_datetime(frame["date"])
    series = frame.set_index("date")["中行折算价"].astype(float)
    return series[~series.index.duplicated(keep="last")].sort_index()


#: Series that map one-to-one onto an upstream table.
BASE_SERIES: Mapping[str, tuple[AkshareSeries, Callable[[], pd.Series]]] = {    "cn.equity.sse_composite_close": (
        AkshareSeries("cn.equity.sse_composite_close", "SSE Composite Index close", unit="index"),
        lambda: _index_close("sh000001"),
    ),
    "cn.equity.sse_composite_volume": (
        AkshareSeries("cn.equity.sse_composite_volume", "SSE Composite Index turnover", unit="shares"),
        lambda: _index_volume("sh000001"),
    ),
    "cn.equity.szse_component_close": (
        AkshareSeries("cn.equity.szse_component_close", "SZSE Component Index close", unit="index"),
        lambda: _index_close("sz399001"),
    ),
    "cn.equity.csi300_close": (
        AkshareSeries("cn.equity.csi300_close", "CSI 300 Index close", unit="index"),
        lambda: _index_close("sh000300"),
    ),
    "cn.bond.cgb_3m_yield": (
        AkshareSeries("cn.bond.cgb_3m_yield", "ChinaBond government yield, 3 month", unit="percent"),
        lambda: _cgb_tenor("3月"),
    ),
    "cn.bond.cgb_1y_yield": (
        AkshareSeries("cn.bond.cgb_1y_yield", "ChinaBond government yield, 1 year", unit="percent"),
        lambda: _cgb_tenor("1年"),
    ),
    "cn.bond.cgb_10y_yield": (
        AkshareSeries("cn.bond.cgb_10y_yield", "ChinaBond government yield, 10 year", unit="percent"),
        lambda: _cgb_tenor("10年"),
    ),
    "cn.money.shibor_on": (
        AkshareSeries("cn.money.shibor_on", "SHIBOR overnight fixing", unit="percent"),
        lambda: _shibor("O/N-定价"),
    ),
    "cn.money.shibor_1w": (
        AkshareSeries("cn.money.shibor_1w", "SHIBOR 1 week fixing", unit="percent"),
        lambda: _shibor("1W-定价"),
    ),
    "cn.money.shibor_3m": (
        AkshareSeries("cn.money.shibor_3m", "SHIBOR 3 month fixing", unit="percent"),
        lambda: _shibor("3M-定价"),
    ),
    "cn.equity.margin_balance_sh": (
        AkshareSeries("cn.equity.margin_balance_sh", "Shanghai margin financing balance", unit="CNY"),
        lambda: _margin("融资余额"),
    ),
    "cn.equity.margin_short_balance_sh": (
        AkshareSeries("cn.equity.margin_short_balance_sh", "Shanghai margin short balance", unit="CNY"),
        lambda: _margin("融券余额"),
    ),
    "cn.derivative.csi300_futures_close": (
        AkshareSeries(
            "cn.derivative.csi300_futures_close",
            "CSI 300 index futures continuous contract close",
            unit="index",
        ),
        lambda: _futures_close("IF0"),
    ),
    "cn.fx.usd_cny_mid": (
        AkshareSeries("cn.fx.usd_cny_mid", "USD/CNY middle rate (Bank of China)", unit="CNY per USD"),
        lambda: _currency_boc("美元"),
    ),
}


# ----------------------------------------------------------------------
# Derived readers.  Each one consumes the base series.
# ----------------------------------------------------------------------


def _spread(left: str, right: str) -> pd.Series:
    """Difference of two base series on their common calendar."""
    first = BASE_SERIES[left][1]().dropna()
    second = BASE_SERIES[right][1]().dropna()
    index = first.index.intersection(second.index)
    if index.empty:
        return pd.Series(dtype=float)
    return (first.reindex(index) - second.reindex(index)).dropna()


def _ratio(numerator: str, denominator: str) -> pd.Series:
    top = BASE_SERIES[numerator][1]().dropna()
    bottom = BASE_SERIES[denominator][1]().dropna()
    index = top.index.intersection(bottom.index)
    if index.empty:
        return pd.Series(dtype=float)
    return (top.reindex(index) / bottom.reindex(index)).replace([np.inf, -np.inf], np.nan).dropna()


def _volatility(series_id: str, window: int = 20) -> pd.Series:
    frame = BASE_SERIES[series_id][1]()
    returns = np_log_returns(frame)
    return returns.rolling(window, min_periods=max(5, window // 2)).std() * (252**0.5) * 100.0


def np_log_returns(series: pd.Series) -> pd.Series:
    """Log returns of a strictly positive series, in percent."""
    clean = series.dropna()
    positive = clean[clean > 0]
    if len(positive) < 2:
        return pd.Series(dtype=float)
    return (np.log(positive / positive.shift(1)) * 100.0).replace([np.inf, -np.inf], np.nan).dropna()


def _relative_to_ma(series_id: str, window: int = 250) -> pd.Series:
    frame = BASE_SERIES[series_id][1]().dropna()
    moving = frame.rolling(window, min_periods=max(20, window // 4)).mean()
    return (frame / moving - 1.0) * 100.0


#: Series that are computed from the base series.
DERIVED_SERIES: Mapping[str, tuple[AkshareSeries, Callable[[], pd.Series]]] = {
    "cn.bond.cgb_yield_slope_10y_1y": (
        AkshareSeries(
            "cn.bond.cgb_yield_slope_10y_1y",
            "ChinaBond government curve slope, 10 year minus 1 year",
            unit="percent",
        ),
        lambda: _spread("cn.bond.cgb_10y_yield", "cn.bond.cgb_1y_yield"),
    ),
    "cn.bond.cgb_yield_slope_10y_3m": (
        AkshareSeries(
            "cn.bond.cgb_yield_slope_10y_3m",
            "ChinaBond government curve slope, 10 year minus 3 month",
            unit="percent",
        ),
        lambda: _spread("cn.bond.cgb_10y_yield", "cn.bond.cgb_3m_yield"),
    ),
    "cn.equity.return_volatility": (
        AkshareSeries(
            "cn.equity.return_volatility",
            "Annualised volatility of the SSE Composite Index",
            unit="percent",
        ),
        lambda: _volatility("cn.equity.sse_composite_close"),
    ),
    "cn.fx.usd_cny_volatility": (
        AkshareSeries(
            "cn.fx.usd_cny_volatility",
            "Annualised volatility of the USD/CNY middle rate",
            unit="percent",
        ),
        lambda: _volatility("cn.fx.usd_cny_mid"),
    ),
    "cn.money.shibor_3m_volatility": (
        AkshareSeries(
            "cn.money.shibor_3m_volatility",
            "Annualised volatility of the 3 month SHIBOR fixing",
            unit="percent",
        ),
        lambda: _volatility("cn.money.shibor_3m"),
    ),
    "cn.money.shibor_1w_volatility": (
        AkshareSeries(
            "cn.money.shibor_1w_volatility",
            "Annualised volatility of the 1 week SHIBOR fixing",
            unit="percent",
        ),
        lambda: _volatility("cn.money.shibor_1w"),
    ),
    "cn.money.shibor_term_premium": (
        AkshareSeries(
            "cn.money.shibor_term_premium",
            "Money market term premium, 3 month SHIBOR minus the overnight fixing",
            unit="percent",
        ),
        lambda: _spread("cn.money.shibor_3m", "cn.money.shibor_on"),
    ),
    "cn.money.shibor_on_volatility": (
        AkshareSeries(
            "cn.money.shibor_on_volatility",
            "Annualised volatility of the overnight SHIBOR fixing",
            unit="percent",
        ),
        lambda: _volatility("cn.money.shibor_on"),
    ),
    "cn.derivative.csi300_futures_volatility": (
        AkshareSeries(
            "cn.derivative.csi300_futures_volatility",
            "Annualised volatility of the CSI 300 index futures contract",
            unit="percent",
        ),
        lambda: _volatility("cn.derivative.csi300_futures_close"),
    ),
    "cn.derivative.csi300_futures_deviation": (
        AkshareSeries(
            "cn.derivative.csi300_futures_deviation",
            "Deviation of the CSI 300 index futures contract from the spot index",
            unit="percent",
        ),
        lambda: _ratio("cn.derivative.csi300_futures_close", "cn.equity.csi300_close") * 100.0
        - 100.0,
    ),
    "cn.equity.margin_to_market_cap": (
        AkshareSeries(
            "cn.equity.margin_to_market_cap",
            "Margin financing balance relative to the index level",
            unit="ratio",
        ),
        lambda: _ratio("cn.equity.margin_balance_sh", "cn.equity.sse_composite_close"),
    ),
    "cn.equity.sse_deviation_from_trend": (
        AkshareSeries(
            "cn.equity.sse_deviation_from_trend",
            "SSE Composite Index deviation from its one year moving average",
            unit="percent",
        ),
        lambda: _relative_to_ma("cn.equity.sse_composite_close"),
    ),
}


class AkshareAdapter:
    """Read-only client for the akshare-backed Chinese market series."""

    name = "akshare"

    def __init__(self, store: SnapshotStore | None = None) -> None:
        self.store = store or SnapshotStore()

    # ------------------------------------------------------------------
    @staticmethod
    def supported() -> tuple[str, ...]:
        return tuple(sorted({*BASE_SERIES.keys(), *DERIVED_SERIES.keys()}))

    @staticmethod
    def describe(series_id: str) -> AkshareSeries | None:
        if series_id in BASE_SERIES:
            return BASE_SERIES[series_id][0]
        if series_id in DERIVED_SERIES:
            return DERIVED_SERIES[series_id][0]
        return None

    # ------------------------------------------------------------------
    def fetch(
        self,
        series_id: str,
        *,
        country_code: str = "CN",
        use_cache: bool = True,
    ) -> FetchResult:
        """Fetch one series.

        When the series is unknown or the upstream call fails the result
        carries a warning and no observations — it never raises, so a single
        broken source cannot stop a daily run.
        """
        if series_id in BASE_SERIES:
            meta, reader = BASE_SERIES[series_id]
        elif series_id in DERIVED_SERIES:
            meta, reader = DERIVED_SERIES[series_id]
        else:
            return FetchResult(
                adapter=self.name,
                series_id=series_id,
                country_code=country_code,
                warnings=[
                    f"series {series_id!r} is not registered in the akshare adapter; "
                    "the indicator is reported as unavailable"
                ],
            )

        cache_key = f"{series_id}"
        cache_path = self.store.path_for(self.name, cache_key).with_suffix(".csv")
        if use_cache and cache_path.exists():
            try:
                frame = pd.read_csv(cache_path, parse_dates=["date"], index_col="date")
                series = frame["value"].astype(float)
                return FetchResult(
                    adapter=self.name,
                    series_id=series_id,
                    country_code=country_code,
                    observations=_observations(series),
                    source_url="akshare (cached)",
                    unit=meta.unit,
                    frequency=meta.frequency,
                    cached=True,
                    extra={"description": meta.description},
                )
            except Exception:  # noqa: BLE001 - fall through to a live read
                pass

        try:
            series = reader()
        except Exception as exc:  # noqa: BLE001
            return FetchResult(
                adapter=self.name,
                series_id=series_id,
                country_code=country_code,
                warnings=[f"the upstream akshare call failed: {exc}"],
                extra={"description": meta.description},
            )

        series = pd.Series(series).dropna().sort_index()
        self._write_cache(series_id, series)
        return FetchResult(
            adapter=self.name,
            series_id=series_id,
            country_code=country_code,
            observations=_observations(series),
            source_url="akshare",
            unit=meta.unit,
            frequency=meta.frequency,
            extra={"description": meta.description},
        )

    # ------------------------------------------------------------------
    def _write_cache(self, series_id: str, series: pd.Series) -> None:
        target = self.store.path_for(self.name, series_id).with_suffix(".csv")
        target.parent.mkdir(parents=True, exist_ok=True)
        frame = pd.DataFrame({"date": series.index, "value": series.to_numpy()})
        frame.to_csv(target, index=False, encoding="utf-8")


def _observations(series: pd.Series) -> tuple:
    from ..models import Observation

    observations: list[Observation] = []
    for index, value in series.items():
        moment = index
        if isinstance(moment, str):
            try:
                moment = pd.to_datetime(moment).date()
            except ValueError:
                continue
        elif isinstance(moment, dt.datetime):
            # pandas.Timestamp subclasses datetime, so this must be checked
            # before the plain date branch below.
            moment = moment.date()
        elif isinstance(moment, dt.date):
            pass
        else:
            try:
                moment = pd.Timestamp(moment).date()
            except (TypeError, ValueError):
                continue
        try:
            observations.append(Observation(date=moment, value=float(value)))
        except (TypeError, ValueError):
            continue
    observations.sort(key=lambda item: item.date)
    return tuple(observations)
