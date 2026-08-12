"""Stage 3: turn structured facts into one tweet or a thread.

Length is enforced here, in code. The prompt asks for brevity but never decides it:
a 281-character string must not reach the X API.

X applies a weighted character count, but every range up to U+10FF counts as 1 —
Greek lives at U+0370-U+03FF, so for this bot the budget is a straight 280
characters. A t.co link always occupies 23 characters regardless of real length.
"""

from __future__ import annotations

import json
import logging
import re
import unicodedata

import llm
from config import editorial_policy, render, settings
from fek_doc import FekDoc
from pipeline.extract import Facts, Provision

log = logging.getLogger(__name__)

COMPOSE_SCHEMA = {
    "type": "object",
    "properties": {"tweets": {"type": "array", "items": {"type": "string"}}},
    "required": ["tweets"],
    "additionalProperties": False,
}

SHORTEN_SCHEMA = {
    "type": "object",
    "properties": {"text": {"type": "string"}},
    "required": ["text"],
    "additionalProperties": False,
}

TWEET_LIMIT = 280
LINK_COST = 24  # 23 for the t.co link + 1 separating space

# The gazette marks surnames and given names of private individuals explicitly.
_NAME_MARKER = re.compile(r"\((?:επ|ον)\)\s*([Α-ΩA-ZΆΈΉΊΌΎΏ][\w\-]{2,})")
_ID_NUMBER = re.compile(r"\b(?:ΑΦΜ|Α\.Φ\.Μ|ΑΜΚΑ|Α\.Μ\.Κ\.Α)\b", re.IGNORECASE)


class ComposeRejected(RuntimeError):
    """Raised when the composed text violates a hard publication rule."""


def _fold(text: str) -> str:
    """Uppercase and strip accents, so name matching survives διαφορές τονισμού."""
    decomposed = unicodedata.normalize("NFD", text.upper())
    return "".join(c for c in decomposed if unicodedata.category(c) != "Mn")


def private_names(doc: FekDoc) -> set[str]:
    """Names of private individuals appearing as subjects of individual acts.

    Taken from the source document's own ``(επ)`` / ``(ον)`` markers rather than
    guessed from capitalisation, which would flag ministry names.
    """
    found = {m.group(1) for m in _NAME_MARKER.finditer(doc.full_text)}
    return {_fold(name) for name in found if len(name) > 2}


def _visible_length(text: str, *, with_link: bool) -> int:
    return len(text) + (LINK_COST if with_link else 0)


def _truncate(text: str, limit: int) -> str:
    """Hard-truncate at a word boundary. Last line of defence, not the first."""
    if len(text) <= limit:
        return text
    cut = text[: limit - 1]
    if " " in cut:
        cut = cut[: cut.rindex(" ")]
    return cut.rstrip(" ,·-—") + "…"


def _render_provision(provision: Provision) -> str:
    parts = [provision.what_changes.rstrip(".")]
    if provision.who_is_affected:
        parts.append(f"Αφορά: {provision.who_is_affected.rstrip('.')}")
    if provision.amount:
        parts.append(f"Ποσό: {provision.amount}")
    if provision.effective_date:
        parts.append(f"Ισχύς: {provision.effective_date}")
    return ". ".join(parts) + "."


def _tweet_count(facts: Facts) -> int:
    mode = settings.thread_mode
    if mode == "single" or not facts.provisions:
        return 1
    if mode == "always":
        return min(1 + len(facts.provisions), settings.thread_max_tweets)

    significant = [
        p for p in facts.provisions if p.importance >= settings.thread_min_importance
    ]
    if len(significant) >= 2:
        return min(1 + len(significant), settings.thread_max_tweets)
    return 1


def _compose_template(facts: Facts, count: int) -> list[str]:
    head = f"{facts.law_name}: {facts.headline.rstrip('.')}."
    if count == 1:
        top = facts.provisions[0] if facts.provisions else None
        if top:
            head = f"{head} {_render_provision(top)}"
        return [head]
    return [head] + [_render_provision(p) for p in facts.provisions[: count - 1]]


def _compose_llm(facts: Facts, count: int, budget: int) -> list[str]:
    system = render(
        "compose",
        editorial_policy=editorial_policy(),
        tweet_count=count,
        budget=budget,
        law_name=facts.law_name,
    )
    data = llm.complete_json(
        system,
        json.dumps(facts.as_dict(), ensure_ascii=False),
        label=f"compose {facts.law_name}",
        schema=COMPOSE_SCHEMA,
        max_tokens=settings.compose_max_tokens,
    )
    tweets = [str(t).strip() for t in (data.get("tweets") or []) if str(t).strip()]
    if not tweets:
        log.warning("compose returned no tweets, falling back to the template")
        return _compose_template(facts, count)
    return tweets[:count]


def _shorten(text: str, budget: int, *, law_name: str) -> str:
    """One bounded re-ask, then hard truncation."""
    if len(text) <= budget:
        return text

    log.warning("tweet is %d chars, over the %d budget — re-asking", len(text), budget)
    try:
        # Rewriting a sentence under a length cap isn't a reasoning task — thinking
        # off, low effort, keeps this a cheap, fast call.
        data = llm.complete_json(
            "Συντομεύεις κείμενα για δημοσίευση στο X, στα ελληνικά. "
            "Διατηρείς κάθε αριθμό, ποσό και ημερομηνία.",
            f"Το κείμενο έχει {len(text)} χαρακτήρες. Ξαναγράψ' το σε λιγότερους "
            f"από {budget} χαρακτήρες, χωρίς να χάσεις την ουσία.\n\n{text}",
            label=f"shorten {law_name}",
            schema=SHORTEN_SCHEMA,
            max_tokens=settings.shorten_max_tokens,
            thinking=False,
            effort="low",
        )
        shortened = str(data.get("text") or "").strip()
        if shortened and len(shortened) <= budget:
            return shortened
        if shortened:
            text = shortened
    except RuntimeError as exc:
        log.warning("shorten call failed (%s), truncating instead", exc)

    return _truncate(text, budget)


def compose(facts: Facts, doc: FekDoc) -> list[str]:
    """Return the ready-to-post tweet texts, length- and privacy-checked."""
    if facts.contains_personal_names:
        raise ComposeRejected(
            f"{doc.label}: extraction flagged personal names, refusing to post"
        )
    if not facts.provisions and not facts.headline:
        raise ComposeRejected(f"{doc.label}: nothing substantive to report")

    count = _tweet_count(facts)
    numbering = count > 1
    # Worst-case prefix width, e.g. "4/4 ".
    prefix_cost = len(f"{count}/{count} ") if numbering else 0
    body_budget = TWEET_LIMIT - prefix_cost

    if settings.compose_mode == "llm":
        texts = _compose_llm(facts, count, body_budget - LINK_COST)
    else:
        texts = _compose_template(facts, count)

    banned = private_names(doc)
    finished: list[str] = []
    for index, text in enumerate(texts):
        is_last = index == len(texts) - 1
        budget = body_budget - (LINK_COST if (is_last and settings.include_link) else 0)
        text = _shorten(text, budget, law_name=facts.law_name)
        text = _truncate(text, budget)  # belt and braces after the re-ask

        folded = _fold(text)
        hit = next((name for name in banned if name in folded), None)
        if hit:
            raise ComposeRejected(
                f"{doc.label}: composed text contains a private individual's name"
            )
        if _ID_NUMBER.search(text) or _NAME_MARKER.search(text):
            raise ComposeRejected(
                f"{doc.label}: composed text contains personal identifiers"
            )

        if is_last and settings.include_link:
            text = f"{text} {doc.pdf_url}"
        if numbering:
            text = f"{index + 1}/{len(texts)} {text}"
        finished.append(text)

    for text in finished:
        effective = len(text) - (
            len(doc.pdf_url) - 23 if doc.pdf_url in text else 0
        )
        if effective > TWEET_LIMIT:
            raise ComposeRejected(
                f"{doc.label}: composed tweet is {effective} weighted chars"
            )

    log.info("composed %d tweet(s) for %s", len(finished), doc.label)
    return finished
