"""Freeze the regression baseline for the China pipeline.

The baseline is the *output* of the legacy research codebase, not raw market
data: the five sub-market stress indices, the composite index and the spillover
matrix that the legacy implementation produced.  It is vendored so that the
rebuilt pipeline can be regression-tested against the published specification.

Sources (read-only, never modified by this script):

* ``output/指数汇总_系统性金融风险维度.xlsx`` — legacy market and composite indices
* ``output/风险概率.xlsx``                  — legacy regime probabilities
* the competition-submission paper          — Table 5-2 / 5-3 / 5-4

Usage::

    python scripts/freeze_baseline.py --legacy-root <path> --out data/baseline
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path

# The matrix published as Table 5-2 of the paper (full sample).
PAPER_TABLE_5_2 = [
    [0.971463, 0.009948, 0.001805, 0.000433, 0.016351],
    [0.080189, 0.880632, 0.010749, 0.024040, 0.004391],
    [0.049396, 0.036482, 0.875167, 0.037995, 0.000961],
    [0.005730, 0.039462, 0.018376, 0.913027, 0.023405],
    [0.395704, 0.013183, 0.000850, 0.042807, 0.547456],
]

# Table 5-3: window ending 2015-05 (before the 2015 crash).
PAPER_TABLE_5_3 = [
    [0.942086, 0.046843, 0.003473, 0.005860, 0.001738],
    [0.366686, 0.541732, 0.038901, 0.050144, 0.002538],
    [0.051861, 0.074208, 0.722477, 0.109683, 0.041771],
    [0.039676, 0.043369, 0.049730, 0.824255, 0.042970],
    [0.073857, 0.013779, 0.118889, 0.269742, 0.523734],
]

# Table 5-4: window ending 2015-09 (after the 2015 crash).
PAPER_TABLE_5_4 = [
    [0.627383, 0.061862, 0.019071, 0.235223, 0.056461],
    [0.333192, 0.441569, 0.021911, 0.199942, 0.003385],
    [0.312528, 0.066667, 0.411953, 0.201035, 0.007817],
    [0.348072, 0.054932, 0.018153, 0.548914, 0.029929],
    [0.567496, 0.006318, 0.004795, 0.203289, 0.218103],
]

MARKETS = ["equity", "bond", "fx", "money", "derivative"]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_market_indices(path: Path):
    import pandas as pd

    raw = pd.read_excel(path, sheet_name="Sheet1", header=None)
    header_idx = next(
        (i for i in range(min(6, len(raw))) if str(raw.iat[i, 0]).strip() in {"时间", "日期"}), 0
    )
    frame = raw.iloc[header_idx + 1 :].copy()
    frame.columns = [str(c).strip() for c in raw.iloc[header_idx].tolist()]
    frame = frame.rename(columns={"时间": "date", "日期": "date"})
    frame["date"] = pd.to_datetime(frame["date"])
    frame = frame.set_index("date")
    markets = [c for c in frame.columns if c != "date"][:6]
    frame = frame[markets]
    frame.columns = [*MARKETS, "composite"]
    return frame.astype(float).sort_index()


def write_csv(frame, target: Path) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["date", *frame.columns])
        for index, row in frame.iterrows():
            writer.writerow([index.date().isoformat(), *[f"{v:.10g}" for v in row.to_numpy()]])


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--legacy-root", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()

    root: Path = args.legacy_root
    out: Path = args.out

    index_workbook = root / "output" / "指数汇总_系统性金融风险维度.xlsx"
    frame = load_market_indices(index_workbook)
    write_csv(frame, out / "cn_legacy_market_indices.csv")

    paper = {
        "source": "competition-submission paper, section 5.2",
        "market_order": MARKETS,
        "note": (
            "Row i / column j is the share of node i's H-step forecast error variance "
            "attributable to node j; each row sums to one."
        ),
        "tables": {
            "full_sample": PAPER_TABLE_5_2,
            "pre_2015_crash": PAPER_TABLE_5_3,
            "post_2015_crash": PAPER_TABLE_5_4,
        },
        "known_gap": (
            "The workbook the legacy VAR was fitted on (Database2.xlsx) was not committed "
            "to the original repository, so these matrices cannot be reproduced bit for bit "
            "from the surviving data vintages. See "
            "docs/methodology/spillover-legacy-vs-paper.md."
        ),
    }
    (out / "paper_spillover_tables.json").write_text(
        json.dumps(paper, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    provenance = {
        "source_workbook": str(index_workbook),
        "source_sha256": sha256(index_workbook),
        "rows": int(len(frame)),
        "first_date": frame.index[0].date().isoformat(),
        "last_date": frame.index[-1].date().isoformat(),
        "generated_files": {
            "cn_legacy_market_indices.csv": sha256(out / "cn_legacy_market_indices.csv"),
            "paper_spillover_tables.json": sha256(out / "paper_spillover_tables.json"),
        },
    }
    (out / "provenance.json").write_text(
        json.dumps(provenance, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(f"baseline written to {out}")
    print(json.dumps(provenance, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
