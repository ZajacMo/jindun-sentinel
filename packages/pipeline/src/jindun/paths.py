"""Repository layout resolution.

Every module that needs a file on disk resolves it through this module.  The
previous design counted ``Path.parents`` levels, which is wrong as soon as a
module moves one directory deeper: the snapshot store and the locale catalogue
each resolved to a path inside ``packages/`` instead of the repository root,
so fetched data and translations were written to places nobody looks at.

The root is therefore *discovered* rather than assumed: it is the nearest
ancestor that carries both a ``pyproject.toml`` and a populated ``locales``
directory.  Every location also honours an environment override so that a
deployment can point the pipeline at its own data volume.
"""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

__all__ = [
    "repo_root",
    "data_dir",
    "snapshot_dir",
    "runs_dir",
    "baseline_dir",
    "catalog_dir",
    "cache_dir",
    "locales_dir",
    "config_dir",
]


def _looks_like_root(candidate: Path) -> bool:
    """Return whether ``candidate`` is the repository root.

    A root carries the workspace manifest *and* a populated locale catalogue.
    The second condition matters: an empty ``packages/pipeline/locales``
    directory would otherwise shadow the real catalogue.
    """
    if not (candidate / "pyproject.toml").is_file():
        return False
    locales = candidate / "locales"
    return locales.is_dir() and any(locales.glob("*.json"))


@lru_cache(maxsize=1)
def repo_root() -> Path:
    """Return the repository root.

    Resolution order:

    1. ``JINDUN_ROOT`` if it points at a plausible root;
    2. the nearest ancestor of this module that looks like a root;
    3. the nearest ancestor that has a ``pyproject.toml`` (packaged install);
    4. the current working directory.
    """
    override = os.environ.get("JINDUN_ROOT")
    if override:
        path = Path(override)
        if path.is_dir():
            return path

    here = Path(__file__).resolve()
    for candidate in here.parents:
        if _looks_like_root(candidate):
            return candidate
    for candidate in here.parents:
        if (candidate / "pyproject.toml").is_file():
            return candidate
    return Path.cwd()


def data_dir() -> Path:
    """Return the repository ``data`` directory."""
    return repo_root() / "data"


def snapshot_dir() -> Path:
    """Return the directory holding raw source snapshots."""
    override = os.environ.get("JINDUN_SNAPSHOT_DIR")
    if override:
        return Path(override)
    return data_dir() / "snapshots"


def runs_dir() -> Path:
    """Return the directory holding pipeline run artefacts."""
    override = os.environ.get("JINDUN_RUNS_DIR")
    if override:
        return Path(override)
    return data_dir() / "runs"


def baseline_dir() -> Path:
    """Return the directory holding the frozen regression baseline."""
    return data_dir() / "baseline"


def catalog_dir() -> Path:
    """Return the directory holding the source catalogue."""
    return data_dir() / "catalog"


def cache_dir() -> Path:
    """Return the directory holding bulky, reproducible source downloads."""
    override = os.environ.get("JINDUN_CACHE_DIR")
    if override:
        return Path(override)
    return data_dir() / "cache"


def locales_dir() -> Path:
    """Return the directory holding the shared locale catalogues."""
    override = os.environ.get("JINDUN_LOCALE_DIR")
    if override:
        return Path(override)
    root = repo_root() / "locales"
    if root.is_dir():
        return root
    return repo_root() / "packages" / "pipeline" / "locales"


def config_dir() -> Path:
    """Return the directory holding the shipped YAML configuration."""
    override = os.environ.get("JINDUN_CONFIG_DIR")
    if override:
        return Path(override)
    return Path(__file__).resolve().parents[2] / "configs"
