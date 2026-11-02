"""Locale handling for the user-facing text of the agent.

The agent never invents a catalogue entry.  Every label it shows comes from the
shared locale catalogue in ``locales/*.json`` through
:class:`jindun.i18n.Translator`, so an answer in Chinese reads exactly like the
dashboard in Chinese and a translation gap stays loud instead of silent.

A message that has no catalogue entry is composed from the entries that do
exist plus a locale-neutral label (a country code, a rule identifier); the
catalogue files themselves are never touched by this package.
"""

from __future__ import annotations

from jindun.i18n import Translator, available_locales, get_translator

__all__ = ["AgentLocale", "DEFAULT_LOCALE", "resolve_locale"]

DEFAULT_LOCALE = "en-US"

_COUNTRY_PREFIX = "country."
_MARKET_PREFIX = "market."
_REGIME_PREFIX = "regime."
_SEVERITY_PREFIX = "severity."
_QUALITY_PREFIX = "quality."


def resolve_locale(locale: str | None) -> str:
    """Return the catalogue locale to use.

    An unknown locale falls back to ``en-US`` rather than to an empty
    catalogue, so a typo in a locale tag degrades to English instead of to
    empty labels.
    """
    if not locale:
        return DEFAULT_LOCALE
    candidate = str(locale).replace("_", "-")
    if candidate in available_locales():
        return candidate
    return DEFAULT_LOCALE


class AgentLocale:
    """Render the agent's text for one locale."""

    def __init__(self, locale: str | None = DEFAULT_LOCALE) -> None:
        self.requested = str(locale or DEFAULT_LOCALE)
        self.resolved = resolve_locale(locale)
        self.translator: Translator = get_translator(self.resolved, fallback_locale=DEFAULT_LOCALE)

    # ------------------------------------------------------------------
    def has(self, key: str) -> bool:
        """Return whether the catalogue holds ``key``."""
        return self.translator.has(key)

    def text(self, key: str, **params: object) -> str:
        """Render ``key`` with the given parameters."""
        return self.translator.text(key, **params)

    def choice(self, key: str, options: dict[str, str]) -> str:
        """Render ``key`` after substituting whole option blocks."""
        return self.translator.choice(key, options)

    # ------------------------------------------------------------------
    def country_label(self, code: str | None) -> str:
        """Return the localised name of a country, or its code when unknown."""
        return self._label(_COUNTRY_PREFIX, code)

    def market_label(self, code: str | None) -> str:
        """Return the localised name of a market, or its code when unknown."""
        return self._label(_MARKET_PREFIX, code)

    def regime_label(self, code: str | None) -> str:
        """Return the localised name of a risk regime, or its code when unknown."""
        return self._label(_REGIME_PREFIX, code)

    def severity_label(self, code: str | None) -> str:
        """Return the localised name of an alert severity, or its code."""
        return self._label(_SEVERITY_PREFIX, code)

    def quality_label(self, code: str | None) -> str:
        """Return the localised name of a quality state, or its code."""
        return self._label(_QUALITY_PREFIX, code)

    # ------------------------------------------------------------------
    def _label(self, prefix: str, code: str | None) -> str:
        """Return the catalogue entry ``prefix + code`` or the bare code."""
        if not code:
            return ""
        text = self.translator.raw(f"{prefix}{code}")
        return text if text is not None else str(code)
