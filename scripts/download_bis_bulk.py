"""Download the BIS LBS bulk flat file into the local (git-ignored) cache.

The SDMX API of WS_LBS_D_PUB only serves the world aggregate (L_REP_CTY=5A);
the reporting-country x counterparty-country bilateral matrix has to come from
the bulk flat file.  One 365 MB download, then a filtered snapshot is committed.

The server supports byte ranges, so the download is chunked and resumable: a
truncated transfer is continued instead of restarted, and the result is only
published once its length matches ``Content-Length`` *and* the archive opens.
"""

from __future__ import annotations

import hashlib
import json
import os
import sys
import time
import urllib.error
import urllib.request
import zipfile

URL = "https://data.bis.org/static/bulk/WS_LBS_D_PUB_csv_flat.zip"
CACHE_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "cache", "bis"
)
TARGET = os.path.join(CACHE_DIR, "WS_LBS_D_PUB_csv_flat.zip")
PART = TARGET + ".part"
META = os.path.join(CACHE_DIR, "WS_LBS_D_PUB_csv_flat.meta.json")
CHUNK = 8 << 20


def remote_size() -> int:
    request = urllib.request.Request(
        URL, method="HEAD", headers={"User-Agent": "jindun-sentinel/0.1"}
    )
    with urllib.request.urlopen(request, timeout=60) as response:
        return int(response.headers.get("Content-Length", "0"))


def download(total: int) -> None:
    start = os.path.getsize(PART) if os.path.exists(PART) else 0
    if start >= total:
        return
    print(f"resuming at {start / 1e6:.1f} MB of {total / 1e6:.1f} MB", flush=True)
    with open(PART, "ab") as handle:
        while True:
            end = min(start + CHUNK, total) - 1
            request = urllib.request.Request(
                URL,
                headers={
                    "User-Agent": "jindun-sentinel/0.1",
                    "Range": f"bytes={start}-{end}",
                    "Accept-Encoding": "identity",
                },
            )
            with urllib.request.urlopen(request, timeout=180) as response:
                chunk = response.read()
            if not chunk:
                time.sleep(2.0)
                continue
            handle.write(chunk)
            handle.flush()
            start += len(chunk)
            print(f"  {start / 1e6:.1f} MB ({start / total * 100:.1f}%)", flush=True)
            if start >= total:
                return


def main() -> int:
    os.makedirs(CACHE_DIR, exist_ok=True)
    total = remote_size()
    print(f"remote size: {total} bytes", flush=True)

    if os.path.exists(TARGET) and os.path.getsize(TARGET) == total:
        print(f"already complete: {TARGET}")
        return 0

    download(total)

    size = os.path.getsize(PART)
    if size != total:
        print(f"incomplete: {size} of {total} bytes", file=sys.stderr)
        return 1
    try:
        with zipfile.ZipFile(PART) as archive:
            names = archive.namelist()
            broken = archive.testzip()
    except zipfile.BadZipFile as exc:
        print(f"the download is not a usable archive: {exc}", file=sys.stderr)
        return 1
    if broken is not None:
        print(f"corrupt member in the archive: {broken}", file=sys.stderr)
        return 1

    os.replace(PART, TARGET)
    digest = hashlib.sha256()
    with open(TARGET, "rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    meta = {
        "url": URL,
        "bytes": total,
        "sha256": digest.hexdigest(),
        "members": names,
        "retrieved_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    with open(META, "w", encoding="utf-8") as handle:
        json.dump(meta, handle, indent=2)
        handle.write("\n")
    print(f"done: {total} bytes sha256={digest.hexdigest()[:16]}... members={len(names)}")
    for name in names:
        print(f"   {name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
