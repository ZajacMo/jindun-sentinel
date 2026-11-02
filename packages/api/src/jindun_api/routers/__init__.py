"""Routing of the JinDun Sentinel API."""

from __future__ import annotations

from .countries import router as countries_router
from .global_layer import router as global_router
from .system import router as system_router

__all__ = ["countries_router", "global_router", "system_router"]
