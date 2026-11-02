"""The read-only tools the agent may call.

Every tool reads a *published* artefact and returns a JSON-safe payload.  A
tool never writes, never recomputes an index and never touches the network:
the run artefacts produced by the pipeline are the single source of truth,
exactly as they are for the API server.  The agent layer therefore can only
ever report a number that the pipeline has already published.

The reader caches the parsed artefacts by path, modification time and size, so
that a session that asks several questions does not re-read the multi-megabyte
run payload every time while a rewritten artefact is still picked up.
"""

from __future__ import annotations

import json
import math
from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

__all__ = [
    "ArtifactReader",
    "Tool",
    "ToolRegistry",
    "UnknownToolError",
    "build_registry",
    "default_registry",
]


class UnknownToolError(KeyError):
    """Raised when a tool that is not in the registry is called."""


def _default_runs_dir() -> Path:
    """Return the directory holding the pipeline run artefacts."""
    from jindun import paths

    return paths.runs_dir()


def _finite(value: Any) -> float | None:
    """Return ``value`` as a finite float, or ``None`` when it is not a number."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    number = float(value)
    if not math.isfinite(number):
        return None
    return number


def _jsonable(value: Any) -> Any:
    """Return a JSON-safe copy of ``value``.

    Non-finite floats become ``None`` rather than the ``NaN`` token, which is
    not valid JSON and would break every consumer of a tool payload.
    """
    if value is None or isinstance(value, (bool, str, int)):
        return value
    if isinstance(value, float):
        return value if math.isfinite(value) else None
    if isinstance(value, Mapping):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(item) for item in value]
    return str(value)


def _last_point(series: Any) -> dict[str, Any] | None:
    """Return the last ``{"date", "value"}`` point of a published series."""
    if not isinstance(series, list):
        return None
    for item in reversed(series):
        if not isinstance(item, Mapping):
            continue
        value = _finite(item.get("value"))
        if value is None:
            continue
        return {"date": item.get("date"), "value": value}
    return None


def _last_value(series: Any) -> float | None:
    """Return the last finite number of a published series."""
    if not isinstance(series, list):
        return None
    for item in reversed(series):
        value = _finite(item)
        if value is not None:
            return value
    return None


def _number_map(block: Any) -> dict[str, float | None]:
    """Return a ``{key: number}`` map with non-numeric entries dropped."""
    if not isinstance(block, Mapping):
        return {}
    return {str(key): _finite(value) for key, value in block.items()}


def _latest_market_indices(block: Any) -> dict[str, dict[str, Any]]:
    """Return the last published value of every market stress index."""
    if not isinstance(block, Mapping):
        return {}
    dates = block.get("dates") if isinstance(block.get("dates"), list) else []
    series = block.get("series") if isinstance(block.get("series"), Mapping) else {}
    latest: dict[str, dict[str, Any]] = {}
    for code, values in series.items():
        if not isinstance(values, list):
            continue
        for index in range(len(values) - 1, -1, -1):
            number = _finite(values[index])
            if number is None:
                continue
            date = dates[index] if index < len(dates) else None
            latest[str(code)] = {"date": date, "value": number}
            break
    return dict(sorted(latest.items()))


def _contributors(nodes: list[str], block: Mapping, limit: int) -> list[dict[str, Any]]:
    """Return the nodes of a spillover network, largest spill-out first."""
    spillout = _number_map(block.get("total_spillout"))
    spillin = _number_map(block.get("total_spillin"))
    net = _number_map(block.get("net"))
    rows = [
        {
            "node": node,
            "spillout": spillout.get(node),
            "spillin": spillin.get(node),
            "net": net.get(node),
        }
        for node in nodes
    ]
    rows.sort(key=lambda row: (row["spillout"] is None, -(row["spillout"] or 0.0)))
    return rows[: max(1, int(limit))]


class ArtifactReader:
    """A read-only view over the published run artefacts."""

    def __init__(self, root: str | Path | None = None) -> None:
        self.root = Path(root) if root is not None else _default_runs_dir()
        self._cache: dict[tuple[str, int, int], Any] = {}

    # ------------------------------------------------------------------
    def available_countries(self) -> list[str]:
        """Return the country codes that have a published run artefact."""
        if not self.root.exists():
            return []
        return sorted(
            path.name
            for path in self.root.iterdir()
            if path.is_dir() and (path / "run.json").is_file()
        )

    def has_country(self, code: str) -> bool:
        """Return whether a country has a published run artefact."""
        return code.upper() in set(self.available_countries())

    def artefact_path(self, code: str) -> Path:
        """Return the path the run artefact of a country would live at."""
        return self.root / code.upper() / "run.json"

    def global_path(self, name: str) -> Path:
        """Return the path of a global layer artefact."""
        return self.root / "global" / name

    # ------------------------------------------------------------------
    def _load(self, path: Path) -> Any | None:
        """Return the parsed content of a JSON artefact, or ``None``."""
        if not path.is_file():
            return None
        stat = path.stat()
        key = (str(path), stat.st_mtime_ns, stat.st_size)
        cached = self._cache.get(key)
        if cached is not None:
            return cached
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return None
        self._cache[key] = payload
        return payload

    def run(self, code: str) -> dict[str, Any] | None:
        """Return the run payload of one country, or ``None`` when it is absent."""
        payload = self._load(self.artefact_path(code))
        return payload if isinstance(payload, dict) else None

    def quality(self, code: str) -> dict[str, Any] | None:
        """Return the quality report of one country, or ``None`` when it is absent."""
        payload = self._load(self.root / code.upper() / "quality.json")
        return payload if isinstance(payload, dict) else None

    def global_payload(self, name: str) -> dict[str, Any] | None:
        """Return a global layer artefact, or ``None`` when it is absent."""
        payload = self._load(self.global_path(name))
        return payload if isinstance(payload, dict) else None


@dataclass(frozen=True)
class Tool:
    """One read-only tool of the registry."""

    name: str
    description: str
    parameters: Mapping[str, str]
    handler: Callable[..., dict[str, Any]]

    def describe(self) -> dict[str, Any]:
        """Return a JSON-safe description of the tool."""
        return {
            "name": self.name,
            "description": self.description,
            "parameters": dict(self.parameters),
        }


class ToolRegistry:
    """The registry of the read-only tools the agent may invoke."""

    def __init__(
        self,
        reader: ArtifactReader | None = None,
        tools: Iterable[Tool] = (),
    ) -> None:
        self.reader = reader or ArtifactReader()
        self._tools: dict[str, Tool] = {}
        for tool in tools:
            self.register(tool)

    def register(self, tool: Tool) -> Tool:
        """Add a tool to the registry and return it."""
        self._tools[tool.name] = tool
        return tool

    def names(self) -> list[str]:
        """Return the names of the registered tools."""
        return sorted(self._tools)

    def describe(self) -> list[dict[str, Any]]:
        """Return a JSON-safe description of every registered tool."""
        return [self._tools[name].describe() for name in self.names()]

    def call(self, name: str, **kwargs: Any) -> dict[str, Any]:
        """Invoke a tool and return its JSON-safe payload."""
        tool = self._tools.get(name)
        if tool is None:
            known = ", ".join(self.names()) or "none"
            raise UnknownToolError(f"unknown tool {name!r}; registered tools: {known}")
        return _jsonable(tool.handler(self.reader, **kwargs))


# ----------------------------------------------------------------------
# The tools themselves.
# ----------------------------------------------------------------------


def _tool_latest_state(reader: ArtifactReader, country: str = "CN") -> dict[str, Any]:
    """Return the latest published state of one country."""
    code = str(country or "").upper()
    run = reader.run(code)
    if run is None:
        return {"country": code, "available": False}

    regime = run.get("regime") if isinstance(run.get("regime"), Mapping) else {}
    labels = regime.get("labels") if isinstance(regime.get("labels"), list) else []
    label = str(labels[-1]) if labels else None
    moderate = _last_value(regime.get("probability_moderate"))
    high = _last_value(regime.get("probability_high"))
    probability = {"moderate": moderate, "high": high}.get(label or "")

    return {
        "country": str(run.get("country_code") or code),
        "available": True,
        "as_of": run.get("as_of"),
        "composite": _last_point(run.get("composite")),
        "percentile": _last_point(run.get("percentile")),
        "deviation": _last_point(run.get("deviation")),
        "regime": {
            "label": label,
            "probability": probability,
            "probabilities": {"moderate": moderate, "high": high},
        },
        "market_indices": _latest_market_indices(run.get("market_indices")),
        "warning_count": len(run.get("warnings") or []),
    }


def _tool_composite_history(
    reader: ArtifactReader, country: str = "CN", last: int = 12
) -> dict[str, Any]:
    """Return the tail of the published composite index series."""
    code = str(country or "").upper()
    run = reader.run(code)
    if run is None:
        return {"country": code, "available": False, "observations": []}

    points = run.get("composite") if isinstance(run.get("composite"), list) else []
    tail = points[-max(1, int(last)) :] if last else list(points)
    observations = [
        {"date": item.get("date"), "value": _finite(item.get("value"))}
        for item in tail
        if isinstance(item, Mapping)
    ]
    return {"country": code, "available": True, "observations": observations}


def _tool_spillover_network(
    reader: ArtifactReader, country: str = "CN", top: int = 5
) -> dict[str, Any]:
    """Return the published spillover network of one country."""
    code = str(country or "").upper()
    run = reader.run(code)
    if run is None:
        return {"country": code, "available": False, "nodes": [], "contributors": []}

    block = run.get("spillover") if isinstance(run.get("spillover"), Mapping) else {}
    nodes = [str(node) for node in (block.get("nodes") or [])]
    return {
        "country": code,
        "available": True,
        "scope": block.get("scope"),
        "nodes": nodes,
        "horizon": block.get("horizon"),
        "method": block.get("method"),
        "matrix": _jsonable(block.get("matrix") or []),
        "total_spillout": _number_map(block.get("total_spillout")),
        "total_spillin": _number_map(block.get("total_spillin")),
        "net": _number_map(block.get("net")),
        "contributors": _contributors(nodes, block, top),
    }


def _tool_alerts(reader: ArtifactReader, country: str = "CN") -> dict[str, Any]:
    """Return the active alerts of one country."""
    code = str(country or "").upper()
    run = reader.run(code)
    if run is None:
        return {"country": code, "available": False, "alerts": []}

    alerts: list[dict[str, Any]] = []
    for item in run.get("alerts") or []:
        if not isinstance(item, Mapping):
            continue
        if str(item.get("state")) != "active":
            continue
        alerts.append(
            {
                "alert_id": item.get("alert_id"),
                "rule_id": item.get("rule_id"),
                "severity": item.get("severity"),
                "state": item.get("state"),
                "fired_at": item.get("fired_at"),
                "message_key": item.get("message_key"),
                "message_params": _jsonable(item.get("message_params") or {}),
                "attribution": _jsonable(item.get("attribution") or {}),
            }
        )
    return {"country": code, "available": True, "alerts": alerts}


def _tool_data_quality(reader: ArtifactReader, country: str = "CN") -> dict[str, Any]:
    """Return the data quality summary of one country."""
    code = str(country or "").upper()
    run = reader.run(code)
    if run is None:
        return {"country": code, "available": False, "quality": None}

    payload = reader.quality(code)
    if payload is None:
        return {"country": code, "available": True, "quality": None}

    counts = payload.get("counts") if isinstance(payload.get("counts"), Mapping) else {}
    issues: list[dict[str, Any]] = []
    for series in payload.get("series") or []:
        if not isinstance(series, Mapping):
            continue
        severity = str(series.get("severity") or "")
        if severity == "ok" and series.get("passed", True):
            continue
        issues.append(
            {
                "series_id": series.get("series_id"),
                "severity": severity,
                "passed": bool(series.get("passed", False)),
                "observations": series.get("observations"),
                "last_date": series.get("last_date"),
            }
        )
    return {
        "country": code,
        "available": True,
        "quality": {
            "generated_at": payload.get("generated_at"),
            "passed": bool(payload.get("passed")),
            "counts": {str(key): value for key, value in counts.items()},
            "issues": issues,
        },
    }


def _tool_global_layer(reader: ArtifactReader, top: int = 5) -> dict[str, Any]:
    """Return the global cycle and the cross-country spillover leaders."""
    cycle = reader.global_payload("cycle.json")
    spillover = reader.global_payload("spillover.json")

    cycle_block: dict[str, Any] | None = None
    if isinstance(cycle, Mapping):
        dates = cycle.get("dates") if isinstance(cycle.get("dates"), list) else []
        factor = cycle.get("factor") if isinstance(cycle.get("factor"), list) else []
        value = None
        date = None
        for index in range(len(factor) - 1, -1, -1):
            number = _finite(factor[index])
            if number is None:
                continue
            value = number
            date = dates[index] if index < len(dates) else None
            break
        ratios = cycle.get("explained_variance_ratio")
        ratio = _finite(ratios[0]) if isinstance(ratios, list) and ratios else None
        cycle_block = {
            "value": value,
            "date": date,
            "explained_variance_ratio": ratio,
            "loadings": _number_map(cycle.get("loadings")),
            "observations": cycle.get("observations"),
        }

    leaders: list[dict[str, Any]] = []
    if isinstance(spillover, Mapping):
        nodes = [str(node) for node in (spillover.get("nodes") or [])]
        leaders = _contributors(nodes, spillover, top)

    return {
        "available": cycle_block is not None or bool(leaders),
        "global_cycle": cycle_block,
        "spillover_leaders": leaders,
    }


def build_registry(reader: ArtifactReader | None = None) -> ToolRegistry:
    """Return the registry with every read-only tool of the agent."""
    registry = ToolRegistry(reader)
    registry.register(
        Tool(
            name="latest_state",
            description="Latest published state of one country: composite index, "
            "percentile, deviation, regime and the market stress indices.",
            parameters={"country": "ISO country code, for example CN"},
            handler=_tool_latest_state,
        )
    )
    registry.register(
        Tool(
            name="composite_history",
            description="Tail of the published composite stress index series.",
            parameters={
                "country": "ISO country code, for example CN",
                "last": "number of observations to return",
            },
            handler=_tool_composite_history,
        )
    )
    registry.register(
        Tool(
            name="spillover_network",
            description="Published cross-market spillover network of one country, "
            "with the largest contributors first.",
            parameters={
                "country": "ISO country code, for example CN",
                "top": "number of contributors to return",
            },
            handler=_tool_spillover_network,
        )
    )
    registry.register(
        Tool(
            name="alerts",
            description="Active alerts of one country.",
            parameters={"country": "ISO country code, for example CN"},
            handler=_tool_alerts,
        )
    )
    registry.register(
        Tool(
            name="data_quality",
            description="Data quality summary of one country.",
            parameters={"country": "ISO country code, for example CN"},
            handler=_tool_data_quality,
        )
    )
    registry.register(
        Tool(
            name="global_layer",
            description="Global cycle factor and the cross-country spillover leaders.",
            parameters={"top": "number of cross-country leaders to return"},
            handler=_tool_global_layer,
        )
    )
    return registry


def default_registry() -> ToolRegistry:
    """Return a registry bound to the default artefact directory."""
    return build_registry()
