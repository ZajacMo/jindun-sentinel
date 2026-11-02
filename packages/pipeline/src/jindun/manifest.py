"""Run manifest — the reproducibility contract.

Every pipeline run emits a manifest that pins the code version, the data
snapshot, the configuration and the hashes of every artefact.  Two runs with
the same manifest inputs must produce byte-identical outputs; the CI
regression job enforces that.

Source *vintages* are recorded separately from the data itself because
official statistics get revised between releases, and a pipeline that silently
mixes two vintages produces numbers nobody can reproduce.
"""

from __future__ import annotations

import datetime as dt
import hashlib
import json
import subprocess
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

__all__ = [
    "SourceVintage",
    "RunManifest",
    "sha256_bytes",
    "sha256_file",
    "sha256_json",
    "git_version",
]


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def sha256_file(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sha256_json(payload: Any) -> str:
    """Hash a JSON-serialisable payload with stable key ordering."""
    encoded = json.dumps(payload, sort_keys=True, ensure_ascii=False, default=str)
    return sha256_bytes(encoded.encode("utf-8"))


def git_version(repo_root: str | Path) -> dict[str, Any]:
    """Return the git commit and dirty flag for ``repo_root``.

    Falls back to a plain marker when git is unavailable or the directory is
    not a repository, so the manifest stays writable everywhere.
    """
    root = Path(repo_root)
    try:
        commit = subprocess.run(
            ["git", "-C", str(root), "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            timeout=20,
            check=False,
        )
        if commit.returncode != 0:
            return {"git_commit": None, "dirty": None}
        sha = commit.stdout.strip()
        status = subprocess.run(
            ["git", "-C", str(root), "status", "--porcelain"],
            capture_output=True,
            text=True,
            timeout=20,
            check=False,
        )
        dirty = bool(status.stdout.strip())
        return {"git_commit": sha, "dirty": dirty}
    except (OSError, subprocess.SubprocessError):
        return {"git_commit": None, "dirty": None}


@dataclass(frozen=True, slots=True)
class SourceVintage:
    """Where a given data source was read from and as of when."""

    name: str
    adapter: str
    as_of: str | None = None
    vintage: str | None = None
    series_count: int = 0
    url: str | None = None


@dataclass(slots=True)
class RunManifest:
    """The reproducibility record emitted by every run."""

    run_id: str
    started_at: str
    code_version: dict[str, Any] = field(default_factory=dict)
    data_snapshot: dict[str, Any] = field(default_factory=dict)
    sources: list[SourceVintage] = field(default_factory=list)
    config: dict[str, Any] = field(default_factory=dict)
    environment: dict[str, Any] = field(default_factory=dict)
    outputs: dict[str, Any] = field(default_factory=dict)
    elapsed_sec: float = 0.0
    warnings: list[str] = field(default_factory=list)

    def to_payload(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "started_at": self.started_at,
            "code_version": self.code_version,
            "data_snapshot": self.data_snapshot,
            "sources": [asdict(source) for source in self.sources],
            "config": self.config,
            "environment": self.environment,
            "outputs": self.outputs,
            "elapsed_sec": round(self.elapsed_sec, 3),
            "warnings": self.warnings,
        }

    def write(self, path: str | Path) -> Path:
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(
            json.dumps(self.to_payload(), ensure_ascii=False, indent=2, default=str),
            encoding="utf-8",
        )
        return target

    @classmethod
    def read(cls, path: str | Path) -> RunManifest:
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
        sources = [SourceVintage(**item) for item in payload.get("sources", [])]
        return cls(
            run_id=payload["run_id"],
            started_at=payload["started_at"],
            code_version=payload.get("code_version", {}),
            data_snapshot=payload.get("data_snapshot", {}),
            sources=sources,
            config=payload.get("config", {}),
            environment=payload.get("environment", {}),
            outputs=payload.get("outputs", {}),
            elapsed_sec=float(payload.get("elapsed_sec", 0.0)),
            warnings=list(payload.get("warnings", [])),
        )


def new_run_id(moment: dt.datetime | None = None) -> str:
    moment = moment or dt.datetime.now(dt.UTC)
    return moment.strftime("%Y-%m-%dT%H-%M-%SZ")
