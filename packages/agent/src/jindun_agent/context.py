"""The language-neutral context pack.

The pack is the agent's memory of the published artefacts: a small, structured
snapshot that is handed to a model and that is rendered offline.  It contains no
sentences at all — numbers stay numbers, dates stay ISO-8601 strings and
enumerations stay the stable codes the pipeline writes — so the very same pack
can be rendered in any locale and cannot smuggle an English label into a
translated answer.

The pack is assembled from the tool registry, so the agent and the tools can
never drift apart: there is exactly one read path into the artefacts.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from .tools import ToolRegistry, default_registry

__all__ = [
    "ContextPack",
    "DEFAULT_TAIL",
    "DEFAULT_TOP",
    "build_context_pack",
]

DEFAULT_TAIL = 12
DEFAULT_TOP = 5


class ContextPack(BaseModel):
    """A structured, language-neutral snapshot of the published artefacts."""

    model_config = ConfigDict(frozen=True)

    country: str
    available: bool = False
    as_of: str | None = None
    composite: dict[str, Any] | None = None
    percentile: dict[str, Any] | None = None
    deviation: dict[str, Any] | None = None
    composite_series: list[dict[str, Any]] = Field(default_factory=list)
    market_indices: dict[str, Any] = Field(default_factory=dict)
    regime: dict[str, Any] | None = None
    spillover: list[dict[str, Any]] = Field(default_factory=list)
    alerts: list[dict[str, Any]] = Field(default_factory=list)
    data_quality: dict[str, Any] | None = None
    global_cycle: dict[str, Any] | None = None
    global_spillover: list[dict[str, Any]] = Field(default_factory=list)
    warning_count: int = 0
    source_path: str | None = None
    tools: list[str] = Field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-safe representation of the pack."""
        return self.model_dump(mode="json")


def build_context_pack(
    country: str,
    *,
    registry: ToolRegistry | None = None,
    tail: int = DEFAULT_TAIL,
    top: int = DEFAULT_TOP,
    tools: Sequence[str] | None = None,
) -> ContextPack:
    """Build the context pack of one country from the published artefacts.

    The country is resolved case-insensitively.  ``tools`` restricts the pack
    to the tools that are relevant for the question; ``latest_state`` is always
    read because it carries the state every answer needs.  When the country has
    no published artefact the returned pack is marked as unavailable and
    carries no numbers at all.
    """
    registry = registry or default_registry()
    code = str(country or "").upper()
    selected = set(tools) if tools is not None else set(registry.names())
    selected.add("latest_state")

    state = registry.call("latest_state", country=code)
    if not state.get("available"):
        return ContextPack(
            country=code,
            available=False,
            source_path=str(registry.reader.artefact_path(code)),
        )

    history = (
        registry.call("composite_history", country=code, last=tail)
        if "composite_history" in selected
        else {}
    )
    spillover = (
        registry.call("spillover_network", country=code, top=top)
        if "spillover_network" in selected
        else {}
    )
    alerts = registry.call("alerts", country=code) if "alerts" in selected else {}
    quality = registry.call("data_quality", country=code) if "data_quality" in selected else {}
    global_layer = registry.call("global_layer", top=top) if "global_layer" in selected else {}

    return ContextPack(
        country=str(state.get("country") or code),
        available=True,
        as_of=state.get("as_of"),
        composite=state.get("composite"),
        percentile=state.get("percentile"),
        deviation=state.get("deviation"),
        composite_series=list(history.get("observations") or []),
        market_indices=dict(state.get("market_indices") or {}),
        regime=state.get("regime"),
        spillover=list(spillover.get("contributors") or []),
        alerts=list(alerts.get("alerts") or []),
        data_quality=quality.get("quality"),
        global_cycle=global_layer.get("global_cycle"),
        global_spillover=list(global_layer.get("spillover_leaders") or []),
        warning_count=int(state.get("warning_count") or 0),
        source_path=str(registry.reader.artefact_path(code)),
        tools=sorted(selected & set(registry.names())),
    )
