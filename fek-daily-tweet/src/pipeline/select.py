"""Pick which of the day's publications to read.

Not "the first one": on 2026-08-06 the lowest-numbered Τεύχος Α issue was the
2-page Α 128/2026, while the substantive law that day was the 80-page Α 126/2026.
Page count is a cheap prior for substance; triage makes the real decision.
"""

from __future__ import annotations

import logging

from config import settings
from et_client import ISSUE_FIRST, ISSUE_SECOND, Publication

log = logging.getLogger(__name__)


def candidates(publications: list[Publication]) -> list[Publication]:
    """Rank the day's publications, best first.

    Τεύχος Α (νόμοι, προεδρικά διατάγματα) always outranks Τεύχος Β (υπουργικές
    αποφάσεις), which is only considered on the many days no Α is published.
    """
    first = [p for p in publications if p.issue_group == ISSUE_FIRST]
    second = [p for p in publications if p.issue_group == ISSUE_SECOND]

    ranked = sorted(first, key=lambda p: p.pages, reverse=True)
    if not ranked:
        ranked = sorted(second, key=lambda p: p.pages, reverse=True)
        if ranked:
            log.info("no Τεύχος Α today, falling back to %d Τεύχος Β issues", len(second))

    selected = ranked[: settings.max_candidates]
    log.info(
        "candidates: %s", ", ".join(f"{p.label} ({p.pages}p)" for p in selected) or "none"
    )
    return selected
