"""Read access to the artefacts produced by the pipeline.

The pipeline is the single source of truth: it writes the artefacts, the API
reads them and never recomputes an index.  That keeps the numbers on screen
identical to the numbers in the run manifest, and it keeps the API cheap
enough to serve a public dashboard.

The store resolves a country to the most recent run that contains it, and
keeps a small in-process cache so a dashboard that polls does not re-read the
same file on every request.
"""

from __future__ import annotations

import datetime as dt
import json
import threading
from pathlib import Path
from typing import Any

__all__ = ["ArtifactStore", "RunStoreError"]


class RunStoreError(RuntimeError):
    """Raised when a requested run artefact is missing."""


def _default_root() -> Path:
    """Return the directory holding the pipeline run artefacts."""
    from jindun import paths

    return paths.runs_dir()


class ArtifactStore:
    """A read-only view over the run artefacts."""

    def __init__(self, root: str | Path | None = None) -> None:
        self.root = Path(root) if root is not None else _default_root()
        self._lock = threading.Lock()
        self._cache: dict[str, Any] = {}

    # ------------------------------------------------------------------
    def available_countries(self) -> list[str]:
        if not self.root.exists():
            return []
        codes = {
            path.name
            for path in self.root.iterdir()
            if path.is_dir() and (path / "run.json").exists()
        }
        return sorted(codes)

    def has_country(self, code: str) -> bool:
        return code.upper() in set(self.available_countries())

    # ------------------------------------------------------------------
    def run(self, code: str) -> dict[str, Any]:
        """Return the most recent run payload of one country."""
        key = f"run:{code.upper()}"
        with self._lock:
            cached = self._cache.get(key)
        if cached is not None:
            return cached
        path = self.root / code.upper() / "run.json"
        if not path.exists():
            raise RunStoreError(f"no run artefact for country {code!r} in {self.root}")
        payload = json.loads(path.read_text(encoding="utf-8"))
        with self._lock:
            self._cache[key] = payload
        return payload

    def quality(self, code: str) -> dict[str, Any]:
        key = f"quality:{code.upper()}"
        with self._lock:
            cached = self._cache.get(key)
        if cached is not None:
            return cached
        path = self.root / code.upper() / "quality.json"
        if not path.exists():
            raise RunStoreError(f"no quality artefact for country {code!r} in {self.root}")
        payload = json.loads(path.read_text(encoding="utf-8"))
        with self._lock:
            self._cache[key] = payload
        return payload

    def market_indices(self, code: str) -> dict[str, Any]:
        payload = self.run(code)
        return payload.get("market_indices", {"dates": [], "series": {}})

    def spillover(self, code: str) -> dict[str, Any]:
        payload = self.run(code)
        return payload.get("spillover", {})

    def alerts(self, code: str) -> list[dict[str, Any]]:
        payload = self.run(code)
        return list(payload.get("alerts", []))

    # ------------------------------------------------------------------
    def latest_manifest(self) -> dict[str, Any] | None:
        if not self.root.exists():
            return None
        manifests = sorted(self.root.glob("manifest-*.json"))
        if not manifests:
            return None
        return json.loads(manifests[-1].read_text(encoding="utf-8"))

    def run_metadata(self) -> dict[str, Any]:
        """Summary information about what the store currently holds."""
        countries = self.available_countries()
        manifest = self.latest_manifest()
        return {
            "root": str(self.root),
            "countries": countries,
            "last_run_id": (manifest or {}).get("run_id"),
            "last_started_at": (manifest or {}).get("started_at"),
            "generated_at": dt.datetime.now(dt.UTC).isoformat(),
        }
