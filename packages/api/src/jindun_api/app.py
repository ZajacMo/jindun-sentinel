"""FastAPI application factory of JinDun Sentinel.

The API is a read-only view over the artefacts the pipeline produces.  It
never recomputes an index, which is what guarantees that the number on the
screen is the number in the run manifest.
"""

from __future__ import annotations

import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from jindun_api import __version__
from jindun_api.routers import countries_router, global_router, system_router

__all__ = ["create_app", "app"]

DESCRIPTION = """
JinDun Sentinel — an open-source, multi-country systemic financial risk
monitoring, early warning and contagion analytics system.

Every response is language neutral: numbers are numbers, dates are ISO-8601
strings and enumerations are stable codes.  The client renders the codes with
the shared locale catalogue, so the API never decides which language to speak.
"""


def create_app() -> FastAPI:
    """Build the application."""
    application = FastAPI(
        title="JinDun Sentinel API",
        version=__version__,
        description=DESCRIPTION,
        license_info={"name": "Apache-2.0"},
        docs_url="/api/docs",
        openapi_url="/api/openapi.json",
    )

    origins = os.environ.get("JINDUN_CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173")
    application.add_middleware(
        CORSMiddleware,
        allow_origins=[item.strip() for item in origins.split(",") if item.strip()],
        allow_credentials=False,
        allow_methods=["GET", "OPTIONS"],
        allow_headers=["*"],
    )

    application.include_router(system_router, prefix="/api/v1")
    application.include_router(countries_router, prefix="/api/v1")
    application.include_router(global_router, prefix="/api/v1")

    @application.get("/api/v1", include_in_schema=False)
    def api_root() -> dict[str, str]:
        return {"service": "jindun-sentinel", "version": __version__, "docs": "/api/docs"}

    return application


app = create_app()
