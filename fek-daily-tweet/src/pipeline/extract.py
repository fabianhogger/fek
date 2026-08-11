"""Stage 2: turn the selected articles into structured facts.

Tweets are composed from this JSON rather than from prose, which is what makes
threading, length enforcement, and auditing tractable.
"""

from __future__ import annotations

import logging
from dataclasses import asdict, dataclass, field

import llm
from config import editorial_policy, prompt, settings
from fek_doc import FekDoc

log = logging.getLogger(__name__)


@dataclass
class Provision:
    what_changes: str
    who_is_affected: str = ""
    amount: str | None = None
    effective_date: str | None = None
    importance: int = 0


@dataclass
class Facts:
    law_name: str
    headline: str
    provisions: list[Provision] = field(default_factory=list)
    contains_personal_names: bool = False
    pdf_url: str = ""

    def as_dict(self) -> dict:
        return {
            "law_name": self.law_name,
            "headline": self.headline,
            "contains_personal_names": self.contains_personal_names,
            "pdf_url": self.pdf_url,
            "provisions": [asdict(p) for p in self.provisions],
        }


def _clean(value) -> str | None:
    """Models return the string "null" about as often as a real null."""
    if value is None:
        return None
    text = str(value).strip()
    if not text or text.lower() in ("null", "none", "n/a", "-"):
        return None
    return text


def extract(doc: FekDoc, article_numbers: list[int]) -> Facts:
    body = doc.section_text(article_numbers, settings.max_extract_chars)

    system = prompt("extract").format(editorial_policy=editorial_policy())
    user = (
        f"Πράξη: {doc.law_name}\n"
        f"Τίτλος: {doc.law_title}\n\n"
        f"Κείμενο επιλεγμένων άρθρων:\n{body}"
    )

    data = llm.complete_json(
        system, user, label=f"extract {doc.label}", max_tokens=3000
    )

    provisions = []
    for raw in data.get("provisions") or []:
        what = _clean(raw.get("what_changes"))
        if not what:
            continue
        try:
            importance = int(raw.get("importance") or 0)
        except (TypeError, ValueError):
            importance = 0
        provisions.append(
            Provision(
                what_changes=what,
                who_is_affected=_clean(raw.get("who_is_affected")) or "",
                amount=_clean(raw.get("amount")),
                effective_date=_clean(raw.get("effective_date")),
                importance=importance,
            )
        )
    provisions.sort(key=lambda p: p.importance, reverse=True)

    facts = Facts(
        law_name=doc.law_name,
        headline=_clean(data.get("headline")) or doc.law_title[:100],
        provisions=provisions,
        contains_personal_names=bool(data.get("contains_personal_names")),
        pdf_url=doc.pdf_url,
    )
    log.info(
        "extract %s → %d provisions, personal_names=%s",
        doc.label,
        len(facts.provisions),
        facts.contains_personal_names,
    )
    return facts
