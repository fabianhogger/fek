"""Stage 1: decide what is worth reading, from the table of contents alone.

This is what keeps a 460k-character law affordable. The model sees only the TOC
(~19k characters for the largest law observed) and returns the handful of articles
worth reading in full.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

import llm
from config import editorial_policy, prompt, settings
from fek_doc import FekDoc

log = logging.getLogger(__name__)


@dataclass
class TriageResult:
    newsworthiness: int
    headline_angle: str
    selected: list[int] = field(default_factory=list)
    reasons: dict[int, str] = field(default_factory=dict)

    @property
    def passes(self) -> bool:
        return self.newsworthiness >= settings.min_newsworthiness and bool(self.selected)


def triage(doc: FekDoc) -> TriageResult:
    toc = doc.render_toc()
    if len(toc) > settings.max_toc_chars:
        log.warning(
            "%s TOC is %d chars, truncating to %d",
            doc.label,
            len(toc),
            settings.max_toc_chars,
        )
        toc = toc[: settings.max_toc_chars]

    system = prompt("triage").format(
        editorial_policy=editorial_policy(), top_k=settings.triage_top_k
    )
    user = (
        f"Πράξη: {doc.law_name}\n"
        f"Τίτλος: {doc.law_title}\n"
        f"Σελίδες: {doc.page_count}\n\n"
        f"Πίνακας περιεχομένων:\n{toc}"
    )

    data = llm.complete_json(system, user, label=f"triage {doc.label}")

    selected = data.get("selected") or []
    valid = {section.number for section in doc.sections}
    numbers, reasons = [], {}
    for item in selected[: settings.triage_top_k]:
        try:
            number = int(item["number"])
        except (KeyError, TypeError, ValueError):
            continue
        if number in valid:
            numbers.append(number)
            reasons[number] = str(item.get("reason", ""))
        else:
            log.warning("%s: triage picked unknown article %s", doc.label, number)

    result = TriageResult(
        newsworthiness=int(data.get("overall_newsworthiness") or 0),
        headline_angle=str(data.get("headline_angle") or ""),
        selected=numbers,
        reasons=reasons,
    )
    log.info(
        "triage %s → score %d, articles %s",
        doc.label,
        result.newsworthiness,
        result.selected,
    )
    return result
