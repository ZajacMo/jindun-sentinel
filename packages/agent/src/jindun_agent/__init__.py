"""The JinDun Sentinel agent layer.

The agent answers questions about the systemic risk state that the pipeline
has already published.  It reads the run artefacts and never recomputes
anything, exactly like the API server: the artefacts are the single source of
truth for every number the agent reports.

The public surface is small:

``Agent``
    The orchestrator: question, optional country, locale.
``build_context_pack``
    The language-neutral snapshot of the published artefacts.
``build_registry``
    The registry of the read-only tools the agent may call.
``AgentLocale``
    The thin wrapper over the shared locale catalogue.
"""

from __future__ import annotations

from .agent import Agent, AgentAnswer, AgentConfig, LLMCallError, select_tools
from .context import ContextPack, build_context_pack
from .locale import AgentLocale, resolve_locale
from .tools import ArtifactReader, Tool, ToolRegistry, build_registry, default_registry

__all__ = [
    "Agent",
    "AgentAnswer",
    "AgentConfig",
    "AgentLocale",
    "ArtifactReader",
    "ContextPack",
    "LLMCallError",
    "Tool",
    "ToolRegistry",
    "build_context_pack",
    "build_registry",
    "default_registry",
    "resolve_locale",
    "select_tools",
    "__version__",
]

__version__ = "0.1.0"
