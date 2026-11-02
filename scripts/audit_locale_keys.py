"""Audit the locale catalogue against the keys the front end and the pipeline use.

A missing key renders as the key itself, which is loud but ugly; a key that
nothing uses is dead weight in four catalogues.  This script reports both.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
LOCALES = REPO / "locales"
WEB = REPO / "packages" / "web" / "src"
PIPELINE = REPO / "packages" / "pipeline" / "src"

CALL = re.compile(r"""(?<![\w.])t\(\s*['"]([a-zA-Z0-9_.\-]+)['"]""")
DYNAMIC = re.compile(r"""(?<![\w.])t\(\s*`([^`]+)`""")
PY_KEY = re.compile(r"""message_key\s*=\s*['"]([a-zA-Z0-9_.\-]+)['"]""")


def _is_pattern(text: str) -> bool:
    return "${" in text


def _matches(text: str, reference: set[str]) -> bool:
    """Return whether a literal or a template pattern is covered."""
    if not _is_pattern(text):
        return text in reference
    regex = re.escape(text)
    regex = re.sub(r"\\\$\\\{[^}]*\\\}", "[^.]*", regex)
    return any(re.fullmatch(regex, key) for key in reference)


def catalogue_keys() -> dict[str, set[str]]:
    keys: dict[str, set[str]] = {}
    for path in sorted(LOCALES.glob("*.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        keys[path.stem] = set(payload)
    return keys


def collect(source: Path, patterns: list[re.Pattern[str]]) -> set[str]:
    found: set[str] = set()
    for path in source.rglob("*"):
        if path.suffix not in (".vue", ".ts", ".py"):
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        for pattern in patterns:
            found.update(pattern.findall(text))
    return found


def main() -> int:
    keys = catalogue_keys()
    reference = keys.get("en-US", set())
    print(f"catalogue: {len(reference)} keys in en-US; locales = {sorted(keys)}")
    for name, values in keys.items():
        missing = reference - values
        extra = values - reference
        if missing or extra:
            print(f"  {name}: missing {sorted(missing)} extra {sorted(extra)}")

    used = collect(WEB, [CALL, DYNAMIC])
    used |= collect(PIPELINE, [PY_KEY])
    # The composite/plural messages are assembled with .text() on the server side.
    used |= {
        "alert.composite_p1",
        "alert.composite_p2",
        "alert.regime_change",
        "alert.spillout_surge",
    }

    missing = sorted(key for key in used if not _matches(key, reference))
    unused = sorted(
        key
        for key in reference
        if key not in used and not any(_matches(other, {key}) for other in used)
    )
    print(f"\nused keys: {len(used)}")
    print(f"missing from the catalogue: {missing}")
    print(f"not referenced anywhere: {unused}")
    return 1 if missing else 0


if __name__ == "__main__":
    raise SystemExit(main())
