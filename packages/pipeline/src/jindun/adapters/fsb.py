"""Adapter for the FSB list of global systemically important banks (G-SIBs).

The FSB publishes the annual G-SIB list as a PDF linked from the news
announcement.  The announcement page itself contains no bank names — the
content lives in the linked document — so the adapter follows the link and
parses the document.

The published list is the input of the global layer's bank-concentration
analysis: G-SIB status is one of the edges in the cross-border banking
network, and the bucket (1 to 10) carries the additional capital surcharge
that the Basel Committee applies.
"""

from __future__ import annotations

import datetime as dt
import re
from dataclasses import dataclass
from typing import Iterable

from .base import FetchResult, HttpClient, SnapshotStore

__all__ = ["FsbAdapter", "GsibBank", "FSB_ANNOUNCEMENT_URL", "FSB_LIST_PAGE_URL"]

FSB_ANNOUNCEMENT_URL = "https://www.fsb.org/2025/11/fsb-publishes-2025-g-sib-list"
FSB_LIST_PAGE_URL = (
    "https://www.fsb.org/2025/11/2025-list-of-global-systemically-important-banks-g-sibs/"
)

_PDF_LINK = re.compile(r"https://www\.fsb\.org/uploads/P\d+\.pdf", re.IGNORECASE)
_BUCKET = re.compile(r"\b([1-9]|10)\b")


@dataclass(frozen=True, slots=True)
class GsibBank:
    """One bank on the G-SIB list."""

    name: str
    bucket: int
    jurisdiction: str = ""
    year: int = 0

    def to_payload(self) -> dict[str, object]:
        return {
            "name": self.name,
            "bucket": self.bucket,
            "jurisdiction": self.jurisdiction,
            "year": self.year,
        }


class FsbAdapter:
    """Read-only client for the FSB G-SIB list."""

    name = "fsb"

    def __init__(
        self,
        client: HttpClient | None = None,
        store: SnapshotStore | None = None,
    ) -> None:
        self.client = client or HttpClient()
        self.store = store or SnapshotStore()

    # ------------------------------------------------------------------
    def document_url(self, *, page_url: str = FSB_LIST_PAGE_URL) -> str:
        """Resolve the URL of the G-SIB list document from its web page."""
        response = self.client.get(page_url)
        html = response.text()
        match = _PDF_LINK.search(html)
        if match:
            return match.group(0)
        raise RuntimeError(f"no G-SIB document link found on {page_url}")

    # ------------------------------------------------------------------
    def fetch_gsib_list(
        self,
        *,
        year: int | None = None,
        country_code: str = "GLOBAL",
        use_cache: bool = True,
    ) -> FetchResult:
        """Download and parse the G-SIB list."""
        warnings: list[str] = []
        try:
            document_url = self.document_url()
        except Exception as exc:  # noqa: BLE001
            return FetchResult(
                adapter=self.name,
                series_id="fsb.gsib",
                country_code=country_code,
                warnings=[f"could not resolve the G-SIB document: {exc}"],
            )

        series_id = f"fsb.gsib.{year}" if year else "fsb.gsib"
        payload = self._read(series_id, document_url, use_cache=use_cache)
        if payload is None:
            return FetchResult(
                adapter=self.name,
                series_id=series_id,
                country_code=country_code,
                source_url=document_url,
                warnings=["the G-SIB document could not be downloaded"],
            )

        banks, parse_warnings = parse_gsib_document(payload, year=year)
        warnings.extend(parse_warnings)
        metadata = self.store.metadata(self.name, series_id) or {}

        return FetchResult(
            adapter=self.name,
            series_id=series_id,
            country_code=country_code,
            source_url=document_url,
            retrieved_at=str(metadata.get("retrieved_at", "")),
            vintage=str(metadata.get("retrieved_at", "")) or None,
            frequency="A",
            warnings=warnings,
            extra={"banks": [bank.to_payload() for bank in banks], "count": len(banks)},
        )

    # ------------------------------------------------------------------
    def _read(self, series_id: str, url: str, *, use_cache: bool) -> bytes | None:
        if use_cache:
            cached = self.store.read(self.name, series_id)
            if cached is not None:
                return cached
        try:
            response = self.client.get(url)
        except Exception:  # noqa: BLE001
            return None
        self.store.write(
            self.name, series_id, response.body, url=url, retrieved_at=response.retrieved_at
        )
        return response.body


def extract_pdf_text(payload: bytes) -> str:
    """Extract the text of a PDF document."""
    from io import BytesIO

    from pypdf import PdfReader

    reader = PdfReader(BytesIO(payload))
    pages: list[str] = []
    for page in reader.pages:
        pages.append(page.extract_text() or "")
    return "\n".join(pages)


def parse_gsib_document(
    payload: bytes, *, year: int | None = None
) -> tuple[list[GsibBank], list[str]]:
    """Parse the bank table out of the G-SIB list document.

    The annex of the document is laid out as a flat list of lines: a bucket
    number, the capital buffer that the bucket implies, and then one bank
    name per line until the next bucket starts.  The parser walks that
    structure rather than trying to interpret the page as a table, because
    the text layer of the PDF is a flat sequence rather than a grid.

    The document also states the number of banks on the list; the parser
    reports a warning when the number of parsed rows does not match it.
    """
    warnings: list[str] = []
    try:
        text = extract_pdf_text(payload)
    except Exception as exc:  # noqa: BLE001
        return [], [f"the G-SIB document could not be parsed: {exc}"]

    lines = [
        re.sub(r"\s+", " ", line).strip()
        for line in text.splitlines()
    ]
    lines = [line for line in lines if line]

    buckets: list[GsibBank] = []
    current: int | None = None
    expected: dict[int, int] = {}
    in_annex = False

    for line in lines:
        if "alphabetical order" in line.lower():
            in_annex = True
            continue
        if not in_annex:
            continue
        if re.fullmatch(r"\d{1,2}", line):
            value = int(line)
            if 1 <= value <= 10:
                current = value
                continue
        if current is None:
            continue
        if re.fullmatch(r"\(\d+(?:\.\d+)?%\)", line):
            continue
        if line.lower().startswith("(empty"):
            current = None
            continue
        if _looks_like_bank(line):
            buckets.append(GsibBank(name=line, bucket=current, year=year or 0))
            expected[current] = expected.get(current, 0) + 1
            continue

    declared = _declared_count(text)
    if declared is not None and declared != len(buckets):
        warnings.append(
            f"the document states that the list contains {declared} banks but "
            f"{len(buckets)} rows were parsed; the parser needs review"
        )
    if not buckets:
        warnings.append("no bank rows were recognised in the G-SIB document")

    buckets.sort(key=lambda bank: (-bank.bucket, bank.name))
    return buckets, warnings


def _declared_count(text: str) -> int | None:
    match = re.search(r"list for\s+(\d{4})\s+includes\s+(\d+)\s+G-?SIBs", text, re.IGNORECASE)
    if match:
        return int(match.group(2))
    return None


_INSTITUTION_HINT = (
    "bank",
    "group",
    "holdings",
    "financial",
    "savings",
    "trust",
    "insurance",
    "corporation",
    "company",
    "co.",
    "inc.",
    "plc",
    "ag",
    "sa",
    "nv",
    "kk",
)


def _looks_like_bank(line: str) -> bool:
    lowered = line.lower()
    if lowered.startswith("table") or lowered.startswith("figure"):
        return False
    if any(hint in lowered for hint in _INSTITUTION_HINT):
        return True
    # A capitalised multi-word name is also acceptable.
    words = line.split()
    if len(words) < 2:
        return False
    capitalised = sum(1 for word in words if word[:1].isupper())
    return capitalised >= 2


def gsib_surcharge(bucket: int) -> float:
    """Return the additional capital surcharge of a G-SIB bucket, in percent.

    The schedule is the one the Basel Committee applies under the 2023
    framework: 1.0 % in bucket 1 rising by 0.5 % per bucket to 5.0 % in
    bucket 10.
    """
    if not 1 <= bucket <= 10:
        raise ValueError(f"invalid G-SIB bucket: {bucket}")
    return 0.5 * bucket


def bucket_histogram(banks: Iterable[GsibBank]) -> dict[int, int]:
    """Count the banks per bucket."""
    histogram: dict[int, int] = {}
    for bank in banks:
        histogram[bank.bucket] = histogram.get(bank.bucket, 0) + 1
    return dict(sorted(histogram.items()))
