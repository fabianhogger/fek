"""Client for the Εθνικό Τυπογραφείο (search.et.gr) backend.

The public site at https://search.et.gr/el/daily-publications/ is a React SPA; the
HTML contains nothing but a mount point. These are the endpoints its bundle calls.
Neither requires authentication, a nonce, or cookies.
"""

from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass
from typing import Any

import requests

log = logging.getLogger(__name__)

API_BASE = "https://searchetv99.azurewebsites.net/api"
BLOB_BASE = "https://ia37rg02wpsa01.blob.core.windows.net/fek"

# From the bundle's issueTypeToNameMap.
ISSUE_NAMES = {
    1: "Α",
    2: "Β",
    3: "Γ",
    4: "Δ",
    5: "Ν.Π.Δ.Δ.",
    6: "Α.Π.Σ.",
    10: "Α.Σ.Ε.Π.",
    11: "ΠΡΑ.Δ.Ι.Τ.",
    12: "Δ.Δ.Σ.",
    14: "Υ.Ο.Δ.Δ.",
}

ISSUE_FIRST = 1  # Τεύχος Α — νόμοι, προεδρικά διατάγματα
ISSUE_SECOND = 2  # Τεύχος Β — υπουργικές αποφάσεις

_TIMEOUT = (10, 60)  # (connect, read)
_RETRIES = 3


@dataclass(frozen=True)
class Publication:
    """One row of the daily-publications listing."""

    search_id: str
    number: int
    issue_group: int
    year: int
    pages: int
    label: str  # e.g. "Α 121/2026"

    @property
    def fek_id(self) -> str:
        """The gazette id used in blob paths: YYYY + 2-digit issue + 5-digit number."""
        return f"{self.year}{self.issue_group:02d}{self.number:05d}"

    @property
    def pdf_url(self) -> str:
        return f"{BLOB_BASE}/{self.issue_group:02d}/{self.year}/{self.fek_id}.pdf"

    @property
    def issue_name(self) -> str:
        return ISSUE_NAMES.get(self.issue_group, str(self.issue_group))


class EtError(RuntimeError):
    pass


def _request(method: str, url: str, **kwargs: Any) -> requests.Response:
    """Issue a request with bounded retries on transient failures."""
    last: Exception | None = None
    for attempt in range(_RETRIES):
        try:
            res = requests.request(method, url, timeout=_TIMEOUT, **kwargs)
            if res.status_code >= 500:
                raise EtError(f"{url} → HTTP {res.status_code}")
            return res
        except (requests.RequestException, EtError) as exc:
            last = exc
            if attempt < _RETRIES - 1:
                backoff = 2**attempt
                log.warning("%s failed (%s), retrying in %ss", url, exc, backoff)
                time.sleep(backoff)
    raise EtError(f"{method} {url} failed after {_RETRIES} attempts: {last}")


def list_publications(date_iso: str) -> list[Publication]:
    """Return everything published on ``date_iso`` (YYYY-MM-DD).

    Weekends and holidays legitimately return an empty list.
    """
    res = _request(
        "POST",
        f"{API_BASE}/searchbydate",
        headers={"Content-Type": "application/json"},
        data=json.dumps({"datePublished": date_iso}),
    )
    if res.status_code == 400:
        # The API rejects anything that is not YYYY-MM-DD with a generic 400.
        raise EtError(f"searchbydate rejected date {date_iso!r} (HTTP 400)")
    res.raise_for_status()

    payload = res.json()
    if payload.get("status") != "ok":
        raise EtError(f"searchbydate returned status={payload.get('status')!r}")

    # `data` is a JSON-encoded string inside the JSON body, so it needs decoding twice.
    raw = payload.get("data") or ""
    rows = json.loads(raw) if raw else []

    publications = []
    for row in rows:
        try:
            publications.append(
                Publication(
                    search_id=row["search_ID"],
                    number=int(row["search_DocumentNumber"]),
                    issue_group=int(row["search_IssueGroupID"]),
                    year=int(row["search_PrimaryLabel"].rsplit("/", 1)[1]),
                    pages=int(row["search_Pages"]),
                    label=row["search_PrimaryLabel"],
                )
            )
        except (KeyError, ValueError, IndexError) as exc:
            log.warning("skipping unparseable listing row %r: %s", row, exc)
    return publications


def download_pdf(publication: Publication, dest_path: str, max_bytes: int) -> str:
    """Stream a gazette PDF to ``dest_path``.

    Streams rather than buffering because a single Τεύχος Β issue can run to 888 pages.
    """
    res = _request("GET", publication.pdf_url, stream=True)
    res.raise_for_status()

    declared = int(res.headers.get("Content-Length") or 0)
    if declared > max_bytes:
        raise EtError(
            f"{publication.label} is {declared} bytes, over the {max_bytes} byte limit"
        )

    written = 0
    with open(dest_path, "wb") as fh:
        for chunk in res.iter_content(chunk_size=1 << 16):
            written += len(chunk)
            if written > max_bytes:
                raise EtError(
                    f"{publication.label} exceeded the {max_bytes} byte limit mid-download"
                )
            fh.write(chunk)

    log.info("downloaded %s (%d bytes) → %s", publication.label, written, dest_path)
    return dest_path
