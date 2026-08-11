#!/usr/bin/env python3
"""Download the test fixture PDFs.

They are public gazette issues, so they are fetched on demand rather than
committed — the largest is 9.4 MB. Run once after cloning:

    python scripts/fetch_fixtures.py
"""

from __future__ import annotations

import os
import urllib.request

FIXTURES = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tests", "fixtures"
)

BLOB = "https://ia37rg02wpsa01.blob.core.windows.net/fek"

# Each covers a document shape that broke an earlier version of the parser.
WANTED = {
    # Ν. 5324/2026 — 112 pages, 141 articles, full ΠΙΝΑΚΑΣ ΠΕΡΙΕΧΟΜΕΝΩΝ.
    # Also the "NOMOΣ" spelling with Latin N and O.
    "20260100121": "01/2026",
    # Π.Υ.Σ. 22/2026 — cabinet act, no articles, 76-page annex in an
    # undecodable font encoding.
    "20260100126": "01/2026",
    # Π.Δ. 47/2026 — 2 pages, no table of contents.
    "20260100127": "01/2026",
    # ΦΕΚ Β 5013/2026 — acts delimited by bare "(n)" markers; names private
    # individuals, so it is the privacy regression fixture.
    "20260205013": "02/2026",
}


def main() -> int:
    os.makedirs(FIXTURES, exist_ok=True)
    for fek_id, path in WANTED.items():
        dest = os.path.join(FIXTURES, f"{fek_id}.pdf")
        if os.path.exists(dest):
            print(f"  have {fek_id}.pdf")
            continue
        url = f"{BLOB}/{path}/{fek_id}.pdf"
        print(f"  fetching {fek_id}.pdf …", end=" ", flush=True)
        urllib.request.urlretrieve(url, dest)
        print(f"{os.path.getsize(dest):,} bytes")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
