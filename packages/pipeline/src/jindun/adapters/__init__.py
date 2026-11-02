"""Read-only connectors to the external data sources.

Every adapter in this package follows the same contract: it returns a
:class:`~jindun.adapters.base.FetchResult` that carries stable identifiers
and raw numbers only, and it never raises for a missing series — a gap is
reported as a warning so that the quality gate can turn it into something
visible.

The adapters were all verified against their live services; the notes in each
module record the coverage gaps that matter (Japan has no ECB CISS anchor,
the BIS key has to be part of the path, and so on).
"""

from __future__ import annotations

from .akshare_source import AkshareAdapter, AkshareSeries
from .base import FetchResult, HttpClient, HttpError, SnapshotStore
from .bis import BisAdapter
from .boj import BojAdapter
from .ecb_ciss import EcbCissAdapter
from .fsb import FsbAdapter

__all__ = [
    "AkshareAdapter",
    "AkshareSeries",
    "BisAdapter",
    "BojAdapter",
    "EcbCissAdapter",
    "FsbAdapter",
    "FetchResult",
    "HttpClient",
    "HttpError",
    "SnapshotStore",
]
