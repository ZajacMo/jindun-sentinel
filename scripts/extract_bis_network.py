"""Extract the bilateral BIS locational banking matrix from the bulk archive.

The BIS bulk flat file is one CSV with every dimension of the flow.  Two
details of its layout dominate this script:

* the header carries both the code and the label (``L_REP_CTY:Reporting
  country``) **and so does every cell** (``GB:United Kingdom``), so the code
  has to be taken from the text before the colon;
* the archive expands to roughly 18 GB of text, so the member is streamed and
  the columns are picked by index — nothing is parsed twice and nothing is
  held in memory.

The filter is documented in ``docs/global/banking-network.md``:

* ``FREQ=Q``, ``L_MEASURE=S``   quarterly stock,
* ``L_PARENT_CTY=5J``           all countries (the only value the flow accepts),
* ``L_REP_BANK_TYPE=A``, ``L_CP_SECTOR=A``, ``L_POS_TYPE=N``  totals, all
  sectors, cross-border positions,
* ``L_DENOM=TO1``               all currencies, converted to US dollars,
* ``L_INSTR`` in ``{A, G}``     all instruments, and loans and deposits as the
  narrower interbank channel,
* ``L_POSITION`` in ``{C, L}``  claims and liabilities.
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import hashlib
import io
import json
import sys
import zipfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
CACHE_ZIP = REPO_ROOT / "data" / "cache" / "bis" / "WS_LBS_D_PUB_csv_flat.zip"
SNAPSHOT_DIR = REPO_ROOT / "data" / "snapshots" / "bis"
OUTPUT = SNAPSHOT_DIR / "lbs_bilateral.csv"
META = SNAPSHOT_DIR / "lbs_bilateral.meta.json"

#: Economies that matter for systemic risk analysis.  The euro area is kept
#: both as the BIS aggregate (``XM``) and through its member states.
DEFAULT_COUNTRIES: tuple[str, ...] = (
    # the five economies this project monitors
    "CN",
    "US",
    "GB",
    "JP",
    # euro area members (the aggregate is reported separately)
    "AT",
    "BE",
    "DE",
    "ES",
    "FI",
    "FR",
    "GR",
    "IE",
    "IT",
    "LU",
    "NL",
    "PT",
    # other financial centres and large economies
    "AU",
    "BR",
    "CA",
    "CH",
    "DK",
    "HK",
    "ID",
    "IN",
    "KR",
    "MX",
    "MY",
    "NO",
    "NZ",
    "PL",
    "RU",
    "SA",
    "SE",
    "SG",
    "TH",
    "TR",
    "TW",
    "VN",
    "ZA",
    # aggregates the BIS itself publishes
    "XM",
    "XW",
    "5A",
    "5J",
    "4T",
    "G2",
)

#: Dimension -> allowed codes.
FILTER: dict[str, set[str]] = {
    "FREQ": {"Q"},
    "L_MEASURE": {"S"},
    "L_DENOM": {"TO1"},
    "L_CURR_TYPE": {"A"},
    "L_PARENT_CTY": {"5J"},
    "L_REP_BANK_TYPE": {"A"},
    "L_CP_SECTOR": {"A"},
    "L_POS_TYPE": {"N"},
    "L_POSITION": {"C", "L"},
}

#: The instrument dimension is kept open; the measure label says which one.
INSTRUMENTS: dict[str, str] = {
    "A": "all_instruments",
    "G": "loans_and_deposits",
}

OUTPUT_COLUMNS = (
    "MEASURE",
    "FREQ",
    "L_MEASURE",
    "L_POSITION",
    "L_INSTR",
    "L_DENOM",
    "L_CURR_TYPE",
    "L_PARENT_CTY",
    "L_REP_BANK_TYPE",
    "L_REP_CTY",
    "L_CP_SECTOR",
    "L_CP_COUNTRY",
    "L_POS_TYPE",
    "UNIT_MEASURE",
    "UNIT_MULT",
    "OBS_STATUS",
    "TIME_PERIOD",
    "OBS_VALUE",
)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="extract-bis-network",
        description="Extract the bilateral BIS banking matrix from the bulk archive",
    )
    parser.add_argument(
        "--zip", type=Path, default=CACHE_ZIP, help="path to the downloaded BIS bulk archive"
    )
    parser.add_argument(
        "--quarters",
        type=int,
        default=8,
        help="how many of the most recent quarters to keep (0 keeps all)",
    )
    parser.add_argument(
        "--countries",
        default=",".join(DEFAULT_COUNTRIES),
        help="comma separated list of BIS area codes to keep",
    )
    parser.add_argument("--output", type=Path, default=OUTPUT)
    return parser.parse_args(argv)


def _code_of(header: str) -> str:
    """Return the dimension code of a ``CODE:Label`` header cell."""
    return header.split(":", 1)[0].strip()


def _cell_code(cell: str) -> str:
    """Return the code part of a ``CODE:Label`` data cell."""
    return cell.split(":", 1)[0].strip()


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if not args.zip.exists():
        print(
            f"the bulk archive is missing: {args.zip}\nrun scripts/download_bis_bulk.py first",
            file=sys.stderr,
        )
        return 1

    wanted = {code.strip().upper() for code in args.countries.split(",") if code.strip()}
    args.output.parent.mkdir(parents=True, exist_ok=True)

    with zipfile.ZipFile(args.zip) as archive:
        members = [name for name in archive.namelist() if name.lower().endswith(".csv")]
        if not members:
            print("the archive holds no CSV member", file=sys.stderr)
            return 1
        member = max(members, key=lambda name: archive.getinfo(name).file_size)
        print(f"reading {member} ({archive.getinfo(member).file_size} bytes uncompressed)")
        with archive.open(member) as raw:
            text = io.TextIOWrapper(raw, encoding="utf-8-sig", newline="")
            reader = csv.reader(text)
            header = next(reader)
            index = {_code_of(name): position for position, name in enumerate(header)}

            needed = [
                *FILTER,
                "L_INSTR",
                "L_REP_CTY",
                "L_CP_COUNTRY",
                "TIME_PERIOD",
                "OBS_VALUE",
                "UNIT_MEASURE",
                "UNIT_MULT",
                "OBS_STATUS",
            ]
            missing = [code for code in needed if code not in index]
            if missing:
                print(f"the archive does not carry the dimensions {missing}", file=sys.stderr)
                return 1

            columns = [code for code in OUTPUT_COLUMNS if code in index]
            # The measure label is derived, not read: it says which instrument
            # slice of the flow the row belongs to.
            columns = ["MEASURE", *columns]
            positions = {code: index[code] for code in columns}
            filter_positions = {code: index[code] for code in FILTER}
            instr_position = index["L_INSTR"]
            rep_position = index["L_REP_CTY"]
            cp_position = index["L_CP_COUNTRY"]
            period_position = index["TIME_PERIOD"]
            value_position = index["OBS_VALUE"]

            kept: list[dict[str, str]] = []
            quarters: set[str] = set()
            scanned = 0
            for row in reader:
                scanned += 1
                if len(row) <= max(rep_position, cp_position, value_position):
                    continue
                if _cell_code(row[rep_position]) not in wanted:
                    continue
                if _cell_code(row[cp_position]) not in wanted:
                    continue
                if any(
                    _cell_code(row[position]) not in FILTER[code]
                    for code, position in filter_positions.items()
                ):
                    continue
                instrument = _cell_code(row[instr_position])
                if instrument not in INSTRUMENTS:
                    continue
                value = row[value_position].strip()
                if not value:
                    continue
                record = {code: _cell_code(row[position]) for code, position in positions.items()}
                record["MEASURE"] = INSTRUMENTS[instrument]
                kept.append(record)
                quarters.add(_cell_code(row[period_position]))
                if scanned % 5_000_000 == 0:
                    print(f"  scanned {scanned:,} rows, kept {len(kept):,}", flush=True)

    if args.quarters and len(quarters) > args.quarters:
        allowed = set(sorted(quarters)[-args.quarters :])
        kept = [row for row in kept if row.get("TIME_PERIOD", "") in allowed]
        quarters = allowed

    with args.output.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(kept)

    digest = hashlib.sha256(args.output.read_bytes()).hexdigest()
    meta = {
        "source": "BIS locational banking statistics (WS_LBS_D_PUB), bulk flat file",
        "source_url": "https://data.bis.org/static/bulk/WS_LBS_D_PUB_csv_flat.zip",
        "archive": str(args.zip),
        "filter": {key: sorted(value) for key, value in FILTER.items()},
        "instruments": INSTRUMENTS,
        "countries": sorted(wanted),
        "quarters": sorted(quarters),
        "rows": len(kept),
        "rows_scanned": scanned,
        "sha256": digest,
        "extracted_at": dt.datetime.now(dt.UTC).isoformat(),
    }
    with META.open("w", encoding="utf-8") as handle:
        json.dump(meta, handle, ensure_ascii=False, indent=2)
        handle.write("\n")

    print(
        f"wrote {len(kept)} rows ({scanned:,} scanned) over {len(quarters)} quarters "
        f"to {args.output}\nsha256={digest[:16]}..."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
