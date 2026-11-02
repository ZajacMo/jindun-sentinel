"""Add or update one key in every locale catalogue.

The catalogues under `locales/` are the single source of truth for every
translatable string in the product — the Python server reads them through
`jindun.i18n` and the front end reads the very same files at build time.
They are therefore written *once*, by hand, in all four languages at the same
time; there is no retrofitting step and no machine translation, because the
financial vocabulary genuinely differs between Simplified and Traditional
Chinese.

This tool is how a key gets added.  It refuses to write a key that is present
in only some of the catalogues, so a half-translated key can never reach the
tree, and it keeps the insertion point stable so that the files stay
diffable.

    python scripts/set_locale_key.py \
        --key spillover.estimator \
        --anchor method.legacy_appendix \
        --en-US "Estimator" --zh-CN "估计量" --zh-TW "估計量" --ja-JP "推定量"

Afterwards, `scripts/audit_locale_keys.py` checks that the four catalogues
still agree.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

LOCALES = ("en-US", "zh-CN", "zh-TW", "ja-JP")

LOCALES_DIR = Path(__file__).resolve().parents[1] / "locales"


def _read(path: Path) -> dict[str, str]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise SystemExit(f"{path} is not a JSON object")
    return {str(key): str(value) for key, value in payload.items()}


def _write(path: Path, catalogue: dict[str, str]) -> None:
    path.write_text(
        json.dumps(catalogue, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def _insert(catalogue: dict[str, str], key: str, value: str, anchor: str | None) -> dict[str, str]:
    """Return the catalogue with ``key`` set, placed after ``anchor``."""
    updated: dict[str, str] = {}
    placed = False
    for existing_key, existing_value in catalogue.items():
        updated[existing_key] = existing_value
        if anchor and existing_key == anchor:
            updated[key] = value
            placed = True
    if not placed:
        updated[key] = value
    return updated


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--key", required=True, help="the dotted key to set")
    parser.add_argument(
        "--anchor",
        default=None,
        help="the key the new entry is placed after; appended when omitted",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="overwrite an existing key instead of refusing",
    )
    for locale in LOCALES:
        # The destination keeps the dash of the locale code, so the argument
        # and the catalogue file always carry the same spelling.
        parser.add_argument(
            f"--{locale}", dest=locale, required=True, help=f"the {locale} text"
        )
    args = parser.parse_args(argv)

    values = {locale: getattr(args, locale) for locale in LOCALES}
    catalogues = {locale: _read(LOCALES_DIR / f"{locale}.json") for locale in LOCALES}

    present = [locale for locale, catalogue in catalogues.items() if args.key in catalogue]
    if present and not args.force:
        raise SystemExit(
            f"{args.key!r} already exists in {', '.join(present)}; pass --force to overwrite"
        )

    missing_anchor = [
        locale for locale, catalogue in catalogues.items() if args.anchor not in catalogue
    ]
    if args.anchor and missing_anchor:
        raise SystemExit(
            f"the anchor {args.anchor!r} does not exist in {', '.join(missing_anchor)}"
        )

    for locale in LOCALES:
        path = LOCALES_DIR / f"{locale}.json"
        _write(path, _insert(catalogues[locale], args.key, values[locale], args.anchor))
        print(f"{locale}: {len(catalogues[locale]) + 1} keys")

    print(f"\n{args.key} set in {len(LOCALES)} catalogues.")
    print("Run scripts/audit_locale_keys.py to confirm that they still agree.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
