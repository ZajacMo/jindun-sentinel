"""The JinDun Sentinel agent: a question in, a localised answer out.

The agent is a thin layer on top of the published artefacts.  It

1. resolves the country the question is about and selects the read-only tools
   that answer it,
2. assembles a language-neutral context pack from those tools,
3. renders an English system prompt and user prompt around the pack, and
4. either asks an OpenAI-compatible chat-completions endpoint or, when no
   endpoint is configured, renders a deterministic answer straight from the
   locale catalogue and the artefacts.

The offline path is the default and it is deliberately dull: it never reaches
out to the network, it never crashes and it never prints a number that is not
in the artefacts.
"""

from __future__ import annotations

import json
import math
import os
import re
import urllib.error
import urllib.request
from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any

from .context import DEFAULT_TAIL, DEFAULT_TOP, ContextPack, build_context_pack
from .locale import DEFAULT_LOCALE, AgentLocale
from .prompts import build_system_prompt, build_user_prompt
from .tools import ArtifactReader, ToolRegistry, build_registry

__all__ = ["Agent", "AgentAnswer", "AgentConfig", "LLMCallError"]

DEFAULT_MODEL = "gpt-4o-mini"
DEFAULT_TIMEOUT = 60.0

ENV_ENDPOINT = "JINDUN_AGENT_ENDPOINT"
ENV_MODEL = "JINDUN_AGENT_MODEL"
ENV_API_KEY = "JINDUN_AGENT_API_KEY"
ENV_TIMEOUT = "JINDUN_AGENT_TIMEOUT"

#: The keywords that make a tool relevant for a question.  The keywords are
#: English on purpose: the catalogue is the only place where the agent knows
#: another language.
_TOOL_KEYWORDS: dict[str, tuple[str, ...]] = {
    "spillover_network": ("spillover", "contagion", "transmission", "network", "shock"),
    "global_layer": ("global", "worldwide", "cross-country", "international"),
    "alerts": ("alert", "warning", "warned"),
    "data_quality": ("quality", "coverage", "missing", "freshness", "stale"),
    "composite_history": ("history", "trend", "series", "recent", "observations"),
}

_CODE_PATTERN = re.compile(r"\b[A-Za-z]{2}\b")


class LLMCallError(RuntimeError):
    """Raised when the configured chat-completions endpoint cannot be used."""


@dataclass
class AgentConfig:
    """The configuration of the agent.

    The endpoint is optional: without it the agent answers offline, from the
    artefacts and the locale catalogue alone.
    """

    endpoint: str | None = None
    model: str = DEFAULT_MODEL
    api_key: str | None = None
    timeout: float = DEFAULT_TIMEOUT
    history: int = DEFAULT_TAIL
    top: int = DEFAULT_TOP

    @classmethod
    def from_env(cls, env: Mapping[str, str] | None = None) -> AgentConfig:
        """Return the configuration read from the environment."""
        environ: Mapping[str, str] = os.environ if env is None else env
        endpoint = (environ.get(ENV_ENDPOINT) or "").strip() or None
        model = (environ.get(ENV_MODEL) or "").strip() or DEFAULT_MODEL
        api_key = (environ.get(ENV_API_KEY) or "").strip() or None
        timeout = DEFAULT_TIMEOUT
        raw_timeout = (environ.get(ENV_TIMEOUT) or "").strip()
        if raw_timeout:
            try:
                timeout = float(raw_timeout)
            except ValueError:
                timeout = DEFAULT_TIMEOUT
        return cls(endpoint=endpoint, model=model, api_key=api_key, timeout=timeout)


@dataclass
class AgentAnswer:
    """One answer of the agent."""

    question: str
    country: str | None
    locale: str
    requested_locale: str
    mode: str
    answer: str
    facts: dict[str, Any] = field(default_factory=dict)
    tools_used: list[str] = field(default_factory=list)
    tools_selected: list[str] = field(default_factory=list)
    context: ContextPack | None = None
    llm_error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-safe representation of the answer."""
        return {
            "question": self.question,
            "country": self.country,
            "locale": self.locale,
            "requested_locale": self.requested_locale,
            "mode": self.mode,
            "answer": self.answer,
            "facts": self.facts,
            "tools_used": list(self.tools_used),
            "tools_selected": list(self.tools_selected),
            "context": self.context.to_dict() if self.context is not None else None,
            "llm_error": self.llm_error,
        }


def select_tools(question: str) -> list[str]:
    """Return the tools that are relevant for a question.

    A question that names a subject ("the spillover network", "the alerts")
    selects the tools of that subject; an open question selects the whole
    published snapshot.
    """
    text = (question or "").lower()
    selected = {"latest_state"}
    for name, keywords in _TOOL_KEYWORDS.items():
        if any(keyword in text for keyword in keywords):
            selected.add(name)
    if len(selected) == 1:
        selected.update(_TOOL_KEYWORDS)
    return sorted(selected)


def _format_number(value: Any) -> str:
    """Render a number exactly as the artefact stores it.

    The value is never rounded into a new number: the agent shows the digits
    the pipeline published.
    """
    if value is None or isinstance(value, bool):
        return ""
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        if not math.isfinite(value):
            return ""
        return repr(value)
    return str(value)


def _chat_completions_url(endpoint: str) -> str:
    """Return the chat-completions URL of an OpenAI-compatible endpoint."""
    url = endpoint.strip()
    if url.endswith("/chat/completions"):
        return url
    return f"{url.rstrip('/')}/chat/completions"


def _post_json(
    url: str,
    payload: dict[str, Any],
    *,
    api_key: str | None,
    timeout: float,
) -> dict[str, Any]:
    """POST a JSON payload to an OpenAI-compatible endpoint.

    ``httpx`` is used when it is installed; otherwise the standard library
    does the job, so the agent has no hard network dependency.
    """
    body = json.dumps(payload).encode("utf-8")
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    try:
        import httpx
    except ImportError:
        httpx = None  # type: ignore[assignment]

    if httpx is not None:
        response = httpx.post(url, content=body, headers=headers, timeout=timeout)
        response.raise_for_status()
        return dict(response.json())

    request = urllib.request.Request(url, data=body, headers=headers, method="POST")
    with urllib.request.urlopen(request, timeout=timeout) as handle:
        return dict(json.loads(handle.read().decode("utf-8")))


def _extract_content(response: Any) -> str:
    """Return the assistant message of a chat-completions response."""
    if not isinstance(response, Mapping):
        return ""
    choices = response.get("choices")
    if not isinstance(choices, list) or not choices:
        return ""
    first = choices[0]
    if not isinstance(first, Mapping):
        return ""
    message = first.get("message")
    if isinstance(message, Mapping):
        content = message.get("content")
        if isinstance(content, str):
            return content.strip()
    text = first.get("text")
    return text.strip() if isinstance(text, str) else ""


class Agent:
    """The analyst agent of JinDun Sentinel."""

    def __init__(
        self,
        config: AgentConfig | None = None,
        reader: ArtifactReader | None = None,
        registry: ToolRegistry | None = None,
    ) -> None:
        self.config = config or AgentConfig.from_env()
        self.registry = registry or build_registry(reader)
        self.reader = self.registry.reader

    # ------------------------------------------------------------------
    def ask(
        self,
        question: str,
        country: str | None = None,
        locale: str = DEFAULT_LOCALE,
    ) -> AgentAnswer:
        """Answer a question about the published artefacts.

        The answer is rendered in ``locale``; the prompt that is sent to a
        model is always English.  Without a configured endpoint the answer is
        built from the artefacts and the locale catalogue, deterministically.
        """
        loc = AgentLocale(locale)
        selected = select_tools(question)
        code = self._resolve_country(question, country, loc)

        if code is None:
            return self._no_country_answer(question, loc, selected)

        pack = build_context_pack(
            code,
            registry=self.registry,
            tail=self.config.history,
            top=self.config.top,
            tools=selected,
        )
        if not pack.available:
            return self._no_data_answer(question, code, loc, selected)

        context = pack.to_dict()
        tools_used = [name for name in selected if name in self.registry.names()]

        if self.config.endpoint:
            try:
                text = self._call_llm(question, context, loc)
            except LLMCallError as exc:
                return AgentAnswer(
                    question=question,
                    country=pack.country,
                    locale=loc.resolved,
                    requested_locale=loc.requested,
                    mode="offline",
                    answer=self._render_offline_answer(pack, loc),
                    facts=context,
                    tools_used=tools_used,
                    tools_selected=selected,
                    context=pack,
                    llm_error=str(exc),
                )
            return AgentAnswer(
                question=question,
                country=pack.country,
                locale=loc.resolved,
                requested_locale=loc.requested,
                mode="llm",
                answer=text,
                facts=context,
                tools_used=tools_used,
                tools_selected=selected,
                context=pack,
            )

        return AgentAnswer(
            question=question,
            country=pack.country,
            locale=loc.resolved,
            requested_locale=loc.requested,
            mode="offline",
            answer=self._render_offline_answer(pack, loc),
            facts=context,
            tools_used=tools_used,
            tools_selected=selected,
            context=pack,
        )

    # ------------------------------------------------------------------
    def _resolve_country(
        self,
        question: str,
        explicit: str | None,
        loc: AgentLocale,
    ) -> str | None:
        """Return the country the question is about."""
        if explicit:
            return str(explicit).strip().upper()

        available = self.reader.available_countries()
        if not available:
            return None

        text = question or ""
        lowered = text.lower()
        candidates: list[str] = []
        for token in _CODE_PATTERN.findall(text):
            upper = token.upper()
            if upper in available and upper not in candidates:
                candidates.append(upper)
        for code in available:
            label = loc.country_label(code)
            if not label or label == code:
                continue
            if label.lower() in lowered and code not in candidates:
                candidates.append(code)

        if len(candidates) == 1:
            return candidates[0]
        if not candidates and len(available) == 1:
            return available[0]
        return None

    def _call_llm(self, question: str, context: dict[str, Any], loc: AgentLocale) -> str:
        """Ask the configured endpoint and return the assistant message."""
        endpoint = self.config.endpoint or ""
        payload = {
            "model": self.config.model,
            "messages": [
                {
                    "role": "system",
                    "content": build_system_prompt(loc.resolved),
                },
                {
                    "role": "user",
                    "content": build_user_prompt(question, context, loc.resolved),
                },
            ],
            "temperature": 0.2,
        }
        try:
            response = _post_json(
                _chat_completions_url(endpoint),
                payload,
                api_key=self.config.api_key,
                timeout=self.config.timeout,
            )
        except (urllib.error.URLError, OSError, ValueError) as exc:
            raise LLMCallError(f"the endpoint could not be reached: {exc}") from exc
        except Exception as exc:  # noqa: BLE001 - any client failure falls back offline
            raise LLMCallError(f"the endpoint call failed: {exc}") from exc

        text = _extract_content(response)
        if not text:
            raise LLMCallError("the endpoint returned no message content")
        return text

    # ------------------------------------------------------------------
    def _no_country_answer(
        self,
        question: str,
        loc: AgentLocale,
        selected: list[str],
    ) -> AgentAnswer:
        """Return the answer for a question that names no country."""
        available = self.reader.available_countries()
        lines = [loc.text("app.name")]
        lines.append(f"{loc.text('nav.countries')}: {', '.join(available)}")
        lines.append(f"{loc.text('nav.overview')}: {loc.text('common.empty')}")
        return AgentAnswer(
            question=question,
            country=None,
            locale=loc.resolved,
            requested_locale=loc.requested,
            mode="offline",
            answer="\n".join(lines),
            facts={"available": False, "countries": available},
            tools_used=[],
            tools_selected=selected,
        )

    def _no_data_answer(
        self,
        question: str,
        code: str,
        loc: AgentLocale,
        selected: list[str],
    ) -> AgentAnswer:
        """Return the answer for a country without a published artefact."""
        label = loc.country_label(code)
        title = f"{loc.text('app.name')} · {label}"
        if label != code:
            title = f"{title} ({code})"
        path = str(self.reader.artefact_path(code))
        lines = [title, loc.text("common.empty"), f"{loc.text('common.source')}: {path}"]
        return AgentAnswer(
            question=question,
            country=code,
            locale=loc.resolved,
            requested_locale=loc.requested,
            mode="offline",
            answer="\n".join(lines),
            facts={"country": code, "available": False, "source_path": path},
            tools_used=[],
            tools_selected=selected,
        )

    def _render_offline_answer(self, pack: ContextPack, loc: AgentLocale) -> str:
        """Render the deterministic, fully localised answer of a context pack."""
        lines: list[str] = []
        label = loc.country_label(pack.country)
        title = f"{loc.text('app.name')} · {label}"
        if label != pack.country:
            title = f"{title} ({pack.country})"
        lines.append(title)
        if pack.as_of:
            lines.append(loc.text("index.asOf", date=pack.as_of))
        lines.append("")

        lines.append(loc.text("nav.overview"))
        if pack.composite:
            lines.append(
                f"  {loc.text('index.composite')}: "
                f"{_format_number(pack.composite.get('value'))} {loc.text('unit.index')}"
            )
        if pack.percentile:
            lines.append(
                f"  {loc.text('index.percentile')}: "
                f"{_format_number(pack.percentile.get('value'))}"
            )
        if pack.deviation:
            lines.append(
                f"  {loc.text('index.deviation')}: "
                f"{_format_number(pack.deviation.get('value'))}"
            )
        regime = pack.regime or {}
        if regime.get("label"):
            parts = [loc.regime_label(str(regime["label"]))]
            if regime.get("probability") is not None:
                parts.append(
                    f"{loc.text('regime.probability')} "
                    f"{_format_number(regime.get('probability'))}"
                )
            lines.append("  " + " · ".join(parts))
        if pack.market_indices:
            items = [
                f"{loc.market_label(code)} {_format_number(block.get('value'))}"
                for code, block in pack.market_indices.items()
            ]
            lines.append("  " + " · ".join(items))

        if pack.spillover:
            lines.append("")
            lines.append(loc.text("nav.spillover"))
            lines.append(
                "  "
                + f"{loc.text('metric.spillOut')}: "
                + " · ".join(
                    f"{loc.market_label(str(entry.get('node')))} "
                    f"{_format_number(entry.get('spillout'))}"
                    for entry in pack.spillover
                )
            )
            lines.append(
                "  "
                + f"{loc.text('metric.net')}: "
                + " · ".join(
                    f"{loc.market_label(str(entry.get('node')))} "
                    f"{_format_number(entry.get('net'))}"
                    for entry in pack.spillover
                )
            )

        if "alerts" in pack.tools:
            lines.append("")
            lines.append(loc.text("nav.alerts"))
            if pack.alerts:
                for alert in pack.alerts:
                    lines.append("  " + self._render_alert(alert, loc))
            else:
                lines.append(f"  {loc.text('common.empty')}")

        if "data_quality" in pack.tools:
            lines.append("")
            lines.append(loc.text("nav.dataQuality"))
            counts = (pack.data_quality or {}).get("counts") or {}
            parts = [
                f"{loc.quality_label(state)} {counts[state]}"
                for state in ("ok", "warning", "failure")
                if state in counts
            ]
            if parts:
                lines.append("  " + " · ".join(parts))
            else:
                lines.append(f"  {loc.text('common.empty')}")

        cycle = pack.global_cycle or {}
        if cycle.get("value") is not None or pack.global_spillover:
            lines.append("")
            lines.append(loc.text("scope.global"))
            if cycle.get("value") is not None:
                lines.append(
                    f"  {loc.text('index.composite')}: {_format_number(cycle.get('value'))}"
                )
            if pack.global_spillover:
                lines.append(
                    "  "
                    + f"{loc.text('metric.spillOut')}: "
                    + " · ".join(
                        f"{loc.country_label(str(entry.get('node')))} "
                        f"{_format_number(entry.get('spillout'))}"
                        for entry in pack.global_spillover
                    )
                )

        return "\n".join(lines)

    def _render_alert(self, alert: Mapping[str, Any], loc: AgentLocale) -> str:
        """Render one alert through its catalogue message."""
        key = str(alert.get("message_key") or "")
        params = dict(alert.get("message_params") or {})
        if key and loc.has(key):
            text = loc.text(key, **params)
            if not text.startswith("[i18n-missing]"):
                return text
        severity = loc.severity_label(str(alert.get("severity") or ""))
        rule = str(alert.get("rule_id") or "")
        return " ".join(part for part in (severity, rule) if part)
