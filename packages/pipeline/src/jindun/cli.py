"""Command line interface of the JinDun Sentinel pipeline.

The commands are deliberately few and each one does one thing:

``sources``
    List the series the adapters can deliver, and the coverage of every
    external source.

``fetch``
    Download the configured sources into the snapshot directory.  Nothing is
    computed; this is the step that can fail on a bad network day.

``run``
    Execute the full pipeline for one or more countries and write the
    artefacts plus the run manifest.

``verify``
    Re-evaluate the quality gates against the stored snapshots without
    recomputing the indices.

All commands write UTF-8 to stdout even on a Windows console, because their
output is meant to be consumed by another program rather than by a human.
"""

from __future__ import annotations

import argparse
import contextlib
import datetime as dt
import json
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from .adapters import (
    AkshareAdapter,
    BisAdapter,
    BojAdapter,
    EcbCissAdapter,
    SnapshotStore,
)
from .config import Settings, load_settings
from .manifest import RunManifest, git_version, new_run_id
from .models import Country, Message
from .pipeline import run_country, write_run_artifacts
from .quality import QualityPolicy, evaluate_all

__all__ = ["main", "build_parser"]


def _force_utf8() -> None:
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            with contextlib.suppress(AttributeError, ValueError):
                reconfigure(encoding="utf-8")


def _repo_root() -> Path:
    """Return the repository root (see :mod:`jindun.paths`)."""
    from . import paths

    return paths.repo_root()


def _settings(args: argparse.Namespace) -> Settings:
    if args.config:
        return load_settings(args.config)
    return load_settings()


def _adapter_fetcher(settings: Settings, store: SnapshotStore, *, country: Country):
    """Return a callable that fetches one series for ``country``."""
    akshare = AkshareAdapter(store)
    ecb = EcbCissAdapter(store=store)

    def fetch(series_id: str, *, use_cache: bool = True):
        adapter = series_id.split(".", 1)[0]
        if adapter == "akshare":
            return akshare.fetch(series_id, country_code=country.code, use_cache=use_cache)
        if adapter == "ecb_ciss":
            area = country.ciss_area or country.code
            return ecb.fetch_composite(area, country_code=country.code, use_cache=use_cache)
        if adapter == "boj":
            return BojAdapter(store=store).fetch_series(
                series_id, country_code=country.code, use_cache=use_cache
            )
        return akshare.fetch(series_id, country_code=country.code, use_cache=use_cache)

    return fetch


def _countries(settings: Settings, requested: Sequence[str] | None) -> list[Country]:
    if not requested:
        return list(settings.enabled_countries())
    wanted = {code.upper() for code in requested}
    return [country for country in settings.countries if country.code.upper() in wanted]


def _cmd_sources(args: argparse.Namespace) -> int:
    settings = _settings(args)
    payload: dict[str, Any] = {
        "countries": [
            {
                "code": country.code,
                "name": country.name_en,
                "enabled": country.enabled,
                "ciss_area": country.ciss_area,
                "markets": len(country.markets),
                "indicators": len(country.indicator_codes),
            }
            for country in settings.countries
        ],
        "akshare_series": list(AkshareAdapter.supported()),
        "ecb_ciss_daily_areas": list(EcbCissAdapter.covered_areas()),
        "bis_flows": list(BisAdapter.known_flows()),
        "boj_databases": sorted(
            {
                "IR01",
                "FM01",
                "FM08",
                "FM09",
                "MD01",
                "MD02",
                "PR01",
                "CO",
                "BP01",
            }
        ),
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


def _cmd_fetch(args: argparse.Namespace) -> int:
    settings = _settings(args)
    store = SnapshotStore(args.snapshot_dir)
    fetched = 0
    failed = 0
    for country in _countries(settings, args.country):
        fetcher = _adapter_fetcher(settings, store, country=country)
        for market in country.markets:
            for indicator in market.indicators:
                result = fetcher(indicator.source_series_id, use_cache=not args.refresh)
                if result.observations:
                    fetched += 1
                    print(
                        f"[ok]   {country.code} {indicator.source_series_id}: "
                        f"{len(result.observations)} observations, "
                        f"last {result.last_date}"
                    )
                else:
                    failed += 1
                    reason = "; ".join(result.warnings) or "no data"
                    print(f"[miss] {country.code} {indicator.source_series_id}: {reason}")
    print(f"\nfetched {fetched} series, {failed} unavailable")
    return 0 if failed == 0 else 1


def _render(message: Message) -> str:
    """Render one structured warning as an English sentence.

    The artefacts stay language neutral: a warning is a catalogue key and the
    facts that fill it.  The command line is the operator's surface and has
    always spoken English, so the sentence is assembled from the English
    catalogue here — the same files the screen reads in the reader's language.
    """
    from .i18n import get_translator

    return get_translator("en-US").text(message.key, **message.params)


def _cmd_run(args: argparse.Namespace) -> int:
    settings = _settings(args)
    store = SnapshotStore(args.snapshot_dir)
    started = dt.datetime.now(dt.UTC)
    run_id = new_run_id(started)
    out_dir = Path(args.out or (_repo_root() / "data" / "runs"))

    manifest = RunManifest(
        run_id=run_id,
        started_at=started.isoformat(),
        code_version=git_version(_repo_root()),
        config={"project": settings.project_name},
    )

    exit_code = 0
    for country in _countries(settings, args.country):
        fetcher = _adapter_fetcher(settings, store, country=country)
        result = run_country(
            country,
            settings,
            fetcher=fetcher,
            quality_policy=QualityPolicy(),
            use_cache=not args.refresh,
        )
        paths = write_run_artifacts(result, out_dir)
        manifest.outputs[country.code] = paths
        manifest.warnings.extend(_render(warning) for warning in result.warnings)
        if result.quality is not None:
            manifest.warnings.extend(
                f"{country.code}: {item.series_id} -> {item.severity.value}"
                for item in result.quality.warnings
            )
        print(
            f"[run] {country.code}: as of {result.as_of}, "
            f"{len(result.market_indices)} market observations, "
            f"{len(result.alerts)} alerts"
        )
        for warning in result.warnings[:10]:
            print(f"       warning: {_render(warning)}")
        if result.quality is not None and not result.quality.passed:
            exit_code = 1

    manifest.elapsed_sec = (dt.datetime.now(dt.UTC) - started).total_seconds()
    manifest_path = manifest.write(out_dir / f"manifest-{run_id}.json")
    print(f"\nmanifest: {manifest_path}")
    return exit_code


def _cmd_verify(args: argparse.Namespace) -> int:
    settings = _settings(args)
    store = SnapshotStore(args.snapshot_dir)
    results = []
    for country in _countries(settings, args.country):
        fetcher = _adapter_fetcher(settings, store, country=country)
        for market in country.markets:
            for indicator in market.indicators:
                results.append(fetcher(indicator.source_series_id, use_cache=True))
    report = evaluate_all(results, QualityPolicy())
    print(json.dumps(report.to_payload(), ensure_ascii=False, indent=2))
    return 0 if report.passed else 1


def _cmd_global(args: argparse.Namespace) -> int:
    """Produce the global layer artefacts from the country runs."""
    from .global_layer import run_global_layer

    settings = _settings(args)
    out_dir = Path(args.out or (_repo_root() / "data" / "runs" / "global"))
    written = run_global_layer(
        settings,
        out_dir,
        countries=args.country,
        banking_snapshot=args.banking_snapshot,
        use_cache=not args.refresh,
    )
    for name, path in written.items():
        print(f"[global] {name}: {path}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="jindun-pipeline", description="JinDun Sentinel computation pipeline"
    )
    parser.add_argument("--config", type=Path, default=None, help="configuration directory")
    parser.add_argument(
        "--snapshot-dir", type=Path, default=None, help="directory for raw source snapshots"
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    sources = subparsers.add_parser("sources", help="list the available data sources")
    sources.set_defaults(func=_cmd_sources)

    fetch = subparsers.add_parser("fetch", help="download the configured sources")
    fetch.add_argument("--country", action="append", default=None)
    fetch.add_argument("--refresh", action="store_true", help="ignore the snapshot cache")
    fetch.set_defaults(func=_cmd_fetch)

    run = subparsers.add_parser("run", help="run the full pipeline")
    run.add_argument("--country", action="append", default=None)
    run.add_argument("--out", type=Path, default=None)
    run.add_argument("--refresh", action="store_true", help="ignore the snapshot cache")
    run.set_defaults(func=_cmd_run)

    verify = subparsers.add_parser("verify", help="re-evaluate the quality gates")
    verify.add_argument("--country", action="append", default=None)
    verify.set_defaults(func=_cmd_verify)

    global_parser = subparsers.add_parser(
        "global", help="build the global layer from the country runs"
    )
    global_parser.add_argument("--country", action="append", default=None)
    global_parser.add_argument("--out", type=Path, default=None)
    global_parser.add_argument(
        "--banking-snapshot",
        type=Path,
        default=None,
        help="the filtered BIS bilateral snapshot used for the banking network",
    )
    global_parser.add_argument("--refresh", action="store_true", help="ignore the snapshot cache")
    global_parser.set_defaults(func=_cmd_global)

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    _force_utf8()
    parser = build_parser()
    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
