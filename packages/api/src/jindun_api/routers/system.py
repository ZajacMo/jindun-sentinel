"""System routes: health, run metadata and the locale catalogue."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from jindun_api.schemas import (
    HealthResponse,
    LocaleListResponse,
    RunMetadataResponse,
)
from jindun_api.store import ArtifactStore

router = APIRouter(tags=["system"])


def get_store() -> ArtifactStore:
    """Dependency that yields the artefact store."""
    return ArtifactStore()


@router.get("/health", response_model=HealthResponse)
def health(store: ArtifactStore = Depends(get_store)) -> HealthResponse:
    """Liveness and a summary of what the store currently holds."""
    from jindun_api import __version__

    metadata = store.run_metadata()
    return HealthResponse(
        status="ok",
        version=__version__,
        countries=metadata["countries"],
        last_run_id=metadata.get("last_run_id"),
    )


@router.get("/run-metadata", response_model=RunMetadataResponse)
def run_metadata(store: ArtifactStore = Depends(get_store)) -> RunMetadataResponse:
    """Information about the most recent pipeline run."""
    return RunMetadataResponse(**store.run_metadata())


@router.get("/locales", response_model=LocaleListResponse)
def locales() -> LocaleListResponse:
    """The locales the server can render messages in.

    The catalogue files are shared with the web front end, so this list is
    always exactly the list of catalogues on disk.
    """
    from jindun.i18n import available_locales

    codes = list(available_locales())
    return LocaleListResponse(default="en-US", locales=codes, fallback="en-US")


@router.get("/messages")
def messages(locale: str = "en-US", key: str | None = None) -> dict:
    """Render one message or a whole catalogue for the given locale.

    This is what the AI agent layer and the report generator call so that a
    sentence in a push notification is the same sentence the screen shows.
    """
    from jindun.i18n import get_translator

    translator = get_translator(locale)
    if key:
        return {
            "locale": locale,
            "key": key,
            "text": translator.text(key),
            "found": translator.has(key),
        }
    catalogue = translator._catalogue  # noqa: SLF001 - intentional read-only view
    return {"locale": locale, "messages": catalogue}
