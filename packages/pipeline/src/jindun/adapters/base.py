"""Shared HTTP plumbing for the external data adapters.

The adapters are read-only clients for public statistical sources.  Three
things matter for them and are handled here once:

* **Timeouts and retries.**  A daily run must not hang because a statistics
  office is slow.  Every request has a bounded timeout and a small retry
  budget with exponential backoff.
* **A user agent.**  Several of the endpoints (notably the ECB SDMX service)
  reject requests without one.
* **On-disk snapshots.**  Every successful response is written to the snapshot
  directory together with its retrieval time and SHA-256, so a run is
  reproducible and a failed run can be replayed from the last good data.
"""

from __future__ import annotations

import datetime as dt
import hashlib
import json
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping

from ..models import Direction, Observation

__all__ = [
    "HttpClient",
    "HttpError",
    "HttpResponse",
    "SnapshotStore",
    "FetchResult",
    "default_snapshot_dir",
    "USER_AGENT",
]

USER_AGENT = "jindun-sentinel/0.1 (+https://github.com/ZajacMo/jindun-sentinel)"


class HttpError(RuntimeError):
    """Raised when a request cannot be completed."""

    def __init__(self, url: str, status: int | None, message: str) -> None:
        super().__init__(f"{url} -> {status if status is not None else 'error'}: {message}")
        self.url = url
        self.status = status
        self.message = message


@dataclass(slots=True)
class HttpResponse:
    url: str
    status: int
    body: bytes
    retrieved_at: dt.datetime

    @property
    def sha256(self) -> str:
        return hashlib.sha256(self.body).hexdigest()

    def text(self, encoding: str = "utf-8") -> str:
        return self.body.decode(encoding, errors="replace")


@dataclass(frozen=True, slots=True)
class _RetryPolicy:
    attempts: int = 3
    backoff_seconds: float = 1.5
    timeout_seconds: float = 30.0


class HttpClient:
    """A tiny, dependency-free HTTP client with retries."""

    def __init__(
        self,
        *,
        timeout: float = 30.0,
        attempts: int = 3,
        backoff: float = 1.5,
        user_agent: str = USER_AGENT,
    ) -> None:
        self._policy = _RetryPolicy(
            attempts=max(1, attempts),
            backoff_seconds=max(0.0, backoff),
            timeout_seconds=timeout,
        )
        self._user_agent = user_agent

    def get(
        self,
        url: str,
        *,
        headers: Mapping[str, str] | None = None,
        timeout: float | None = None,
    ) -> HttpResponse:
        request = urllib.request.Request(url, method="GET")
        request.add_header("User-Agent", self._user_agent)
        request.add_header("Accept-Encoding", "identity")
        for name, value in (headers or {}).items():
            request.add_header(name, value)

        limit = timeout if timeout is not None else self._policy.timeout_seconds
        last_error: Exception | None = None
        for attempt in range(self._policy.attempts):
            try:
                with urllib.request.urlopen(request, timeout=limit) as handle:
                    body = handle.read()
                    return HttpResponse(
                        url=url,
                        status=int(handle.status),
                        body=body,
                        retrieved_at=dt.datetime.now(dt.timezone.utc),
                    )
            except urllib.error.HTTPError as exc:
                last_error = HttpError(url, exc.code, exc.reason or "http error")
                # 4xx other than 429 will not succeed on a retry.
                if exc.code not in (429, 500, 502, 503, 504):
                    raise last_error from exc
            except (urllib.error.URLError, TimeoutError, OSError) as exc:
                last_error = HttpError(url, None, str(exc))
            if attempt + 1 < self._policy.attempts:
                time.sleep(self._policy.backoff_seconds * (2**attempt))
        raise last_error if last_error else HttpError(url, None, "unknown failure")


def default_snapshot_dir() -> Path:
    """Return the directory that stores raw source snapshots.

    Resolution lives in :mod:`jindun.paths` so that the snapshot store, the
    run store and the locale catalogue can never disagree about where the
    repository lives.
    """
    from .. import paths

    return paths.snapshot_dir()


@dataclass(slots=True)
class FetchResult:
    """The outcome of one adapter call.

    The result is language neutral: it carries stable identifiers and raw
    numbers only.  Display names belong to the locale catalogues.
    """

    adapter: str
    series_id: str
    country_code: str
    observations: tuple[Observation, ...] = ()
    source_url: str = ""
    retrieved_at: str = ""
    vintage: str | None = None
    unit: str = ""
    frequency: str = "D"
    warnings: list[str] = field(default_factory=list)
    cached: bool = False
    extra: dict[str, Any] = field(default_factory=dict)

    @property
    def first_date(self) -> dt.date | None:
        return self.observations[0].date if self.observations else None

    @property
    def last_date(self) -> dt.date | None:
        return self.observations[-1].date if self.observations else None

    def to_series(self) -> "Series":
        from ..models import Series

        return Series(
            code=self.series_id,
            country_code=self.country_code,
            market_code=self.country_code,
            unit=self.unit,
            direction=Direction.SAME,
            observations=tuple(self.observations),
            source=self.adapter,
        )

    def to_payload(self) -> dict[str, Any]:
        return {
            "adapter": self.adapter,
            "series_id": self.series_id,
            "country_code": self.country_code,
            "observations": len(self.observations),
            "first_date": self.first_date.isoformat() if self.first_date else None,
            "last_date": self.last_date.isoformat() if self.last_date else None,
            "source_url": self.source_url,
            "retrieved_at": self.retrieved_at,
            "vintage": self.vintage,
            "unit": self.unit,
            "frequency": self.frequency,
            "warnings": list(self.warnings),
            "cached": self.cached,
            "extra": dict(self.extra),
        }


class SnapshotStore:
    """A content-addressed store for raw source payloads.

    Snapshots are keyed by ``adapter/series_id`` and stored together with a
    small sidecar that records the URL, the retrieval timestamp and the
    SHA-256 of the payload.  The store is deliberately append-only: a rerun
    never overwrites an existing snapshot silently, it writes a new one and
    updates the pointer.
    """

    def __init__(self, root: str | Path | None = None) -> None:
        self.root = Path(root) if root is not None else default_snapshot_dir()
        self.root.mkdir(parents=True, exist_ok=True)

    def path_for(self, adapter: str, series_id: str) -> Path:
        safe = series_id.replace("/", "_").replace(":", "_").replace("?", "_")
        return self.root / adapter / f"{safe}.bin"

    def write(
        self,
        adapter: str,
        series_id: str,
        payload: bytes,
        *,
        url: str,
        retrieved_at: dt.datetime | None = None,
        extra: Mapping[str, Any] | None = None,
    ) -> Path:
        moment = retrieved_at or dt.datetime.now(dt.timezone.utc)
        target = self.path_for(adapter, series_id)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(payload)
        meta = {
            "adapter": adapter,
            "series_id": series_id,
            "url": url,
            "retrieved_at": moment.isoformat(),
            "sha256": hashlib.sha256(payload).hexdigest(),
            "bytes": len(payload),
        }
        if extra:
            meta.update(dict(extra))
        target.with_suffix(".meta.json").write_text(
            json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        return target

    def read(self, adapter: str, series_id: str) -> bytes | None:
        target = self.path_for(adapter, series_id)
        if not target.exists():
            return None
        return target.read_bytes()

    def metadata(self, adapter: str, series_id: str) -> dict[str, Any] | None:
        target = self.path_for(adapter, series_id).with_suffix(".meta.json")
        if not target.exists():
            return None
        return json.loads(target.read_text(encoding="utf-8"))
