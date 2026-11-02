"""Server-side internationalisation.

The message catalogue lives in a single JSON file per locale and is shared with
the web front end: the front end consumes the very same files through
``vue-i18n``, the server consumes them through this module.  That is what
keeps a report, a push notification and an on-screen label from drifting apart.

The formatter supports the subset of the ICU / vue-i18n message syntax that the
project actually uses:

* named interpolation — ``{name}``
* plain interpolation — ``{0}``
* vue-i18n style pluralisation — ``no alerts | one alert | {count} alerts``

If a key is missing the key itself is returned, prefixed with a visible marker,
so a translation gap is loud rather than silent.
"""

from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path
from typing import Any, Mapping

__all__ = ["Translator", "get_translator", "available_locales", "locale_root"]

_PLACEHOLDER = re.compile(r"\{(\w+)\}")
_MISSING_PREFIX = "[i18n-missing]"


def locale_root() -> Path:
    """Return the directory holding the shared locale catalogues.

    The catalogues live at the repository root so that the web front end and
    the server read *the same files*; that is what stops a report, a push
    notification and an on-screen label from drifting apart.  Resolution lives
    in :mod:`jindun.paths` because an empty package-local directory must not
    shadow the real catalogue.
    """
    from . import paths

    return paths.locales_dir()


def available_locales() -> tuple[str, ...]:
    root = locale_root()
    if not root.exists():
        return ()
    return tuple(sorted(path.stem for path in root.glob("*.json")))


class Translator:
    """Render messages for one locale."""

    def __init__(self, locale: str, catalogue: Mapping[str, str]) -> None:
        self.locale = locale
        self._catalogue = dict(catalogue)
        self._fallback: dict[str, str] = {}

    @classmethod
    def load(cls, locale: str, fallback_locale: str = "en-US") -> "Translator":
        catalogue = _load_catalogue(locale)
        fallback = _load_catalogue(fallback_locale) if fallback_locale != locale else {}
        translator = cls(locale, catalogue)
        translator._fallback = fallback
        return translator

    def has(self, key: str) -> bool:
        return key in self._catalogue or key in self._fallback

    def raw(self, key: str) -> str | None:
        if key in self._catalogue:
            return self._catalogue[key]
        return self._fallback.get(key)

    def text(self, key: str, **params: Any) -> str:
        """Render ``key`` with the given parameters."""
        template = self.raw(key)
        if template is None:
            return f"{_MISSING_PREFIX}:{key}"
        return self._render(template, params)

    __call__ = text

    def _render(self, template: str, params: Mapping[str, Any]) -> str:
        count = params.get("count")
        if "|" in template and count is not None:
            template = _select_plural(template, int(count))
        return _PLACEHOLDER.sub(lambda m: _stringify(params.get(m.group(1), m.group(1))), template)

    def choice(self, key: str, options: Mapping[str, str]) -> str:
        """Render ``key`` after substituting whole option blocks.

        Used for messages whose body differs structurally per risk state, e.g.
        ``alert.regime_change`` with ``moderate`` / ``high`` variants.
        """
        template = self.raw(key)
        if template is None:
            return f"{_MISSING_PREFIX}:{key}"
        rendered = template
        for name, value in options.items():
            rendered = rendered.replace(f"{{{name}}}", value)
        return rendered


def _stringify(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, float):
        return f"{value:.4g}"
    return str(value)


def _select_plural(template: str, count: int) -> str:
    """Pick the vue-i18n plural branch for ``count``.

    vue-i18n's default rule is English-like: one / other.
    """
    parts = [part.strip() for part in template.split("|")]
    if len(parts) == 2:
        # zero-or-many | other
        return parts[1] if count != 1 else parts[0]
    if len(parts) == 3:
        zero, one, other = parts
        if count == 0:
            return zero
        if count == 1:
            return one
        return other
    return parts[-1]


@lru_cache(maxsize=32)
def _load_catalogue(locale: str) -> dict[str, str]:
    path = locale_root() / f"{locale}.json"
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    return {str(key): str(value) for key, value in data.items()}


@lru_cache(maxsize=32)
def get_translator(locale: str = "en-US", fallback_locale: str = "en-US") -> Translator:
    """Return a cached translator for ``locale``."""
    return Translator.load(locale, fallback_locale)
