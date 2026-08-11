"""Lambda entry point: one gazette document summarised and posted per run.

Invoked by EventBridge Scheduler at 21:00 Europe/Athens on weekdays. Accepts an
optional ``{"date": "YYYY-MM-DD"}`` payload for manual replays, and
``{"dry_run": true}`` to compose without posting.
"""

from __future__ import annotations

import logging
import os
import tempfile
from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

import et_client
import fek_doc
import llm
import state
import tweeter
from config import settings
from pipeline import select
from pipeline.compose import ComposeRejected, compose
from pipeline.extract import extract
from pipeline.triage import triage

logging.basicConfig(
    level=os.environ.get("LOG_LEVEL", "INFO"),
    format="%(levelname)s %(name)s %(message)s",
)
log = logging.getLogger("fek")


def _today() -> str:
    return datetime.now(ZoneInfo(settings.timezone)).strftime("%Y-%m-%d")


def run(date_iso: str | None = None, dry_run: bool | None = None) -> dict[str, Any]:
    date_iso = date_iso or _today()
    dry_run = settings.dry_run if dry_run is None else dry_run

    publications = et_client.list_publications(date_iso)
    if not publications:
        # Weekends and holidays. Expected, not an error.
        log.info("no publications for %s", date_iso)
        return {"status": "no_publications", "date": date_iso}

    ranked = select.candidates(publications)
    if not ranked:
        log.info("nothing in Τεύχος Α or Β for %s", date_iso)
        return {"status": "no_candidates", "date": date_iso}

    skipped: list[str] = []
    with tempfile.TemporaryDirectory(dir="/tmp") as workdir:
        for publication in ranked:
            if state.already_posted(publication.fek_id):
                skipped.append(f"{publication.label} (already posted)")
                continue

            try:
                result = _process(publication, workdir, date_iso, dry_run)
            except (et_client.EtError, ComposeRejected) as exc:
                log.warning("skipping %s: %s", publication.label, exc)
                skipped.append(f"{publication.label} ({exc})")
                continue

            if result is None:
                skipped.append(f"{publication.label} (below newsworthiness threshold)")
                continue

            result["skipped"] = skipped
            result["usage"] = dict(llm.usage)
            return result

    log.info("no candidate cleared the bar for %s", date_iso)
    return {"status": "nothing_newsworthy", "date": date_iso, "skipped": skipped}


def _process(
    publication: et_client.Publication,
    workdir: str,
    date_iso: str,
    dry_run: bool,
) -> dict[str, Any] | None:
    pdf_path = os.path.join(workdir, f"{publication.fek_id}.pdf")
    et_client.download_pdf(publication, pdf_path, settings.max_pdf_bytes)

    doc = fek_doc.parse(
        pdf_path,
        fek_id=publication.fek_id,
        label=publication.label,
        issue_group=publication.issue_group,
        pdf_url=publication.pdf_url,
    )

    verdict = triage(doc)
    if not verdict.passes:
        log.info(
            "%s scored %d (< %d), moving on",
            publication.label,
            verdict.newsworthiness,
            settings.min_newsworthiness,
        )
        return None

    facts = extract(doc, verdict.selected)
    tweets = compose(facts, doc)

    if dry_run:
        log.info("DRY RUN — not posting")
        for index, text in enumerate(tweets, 1):
            log.info("  [%d/%d] (%d chars) %s", index, len(tweets), len(text), text)
        return {
            "status": "dry_run",
            "date": date_iso,
            "fek_id": publication.fek_id,
            "label": publication.label,
            "newsworthiness": verdict.newsworthiness,
            "tweets": tweets,
            "facts": facts.as_dict(),
        }

    tweet_ids = tweeter.post_thread(
        tweets,
        on_posted=lambda ids: state.mark_posted(
            publication.fek_id,
            label=publication.label,
            tweet_ids=ids,
            facts=facts.as_dict(),
            tweets=tweets,
        ),
    )

    return {
        "status": "posted",
        "date": date_iso,
        "fek_id": publication.fek_id,
        "label": publication.label,
        "newsworthiness": verdict.newsworthiness,
        "tweet_ids": tweet_ids,
        "tweets": tweets,
    }


def lambda_handler(event: dict | None, context: Any = None) -> dict[str, Any]:
    event = event or {}
    result = run(date_iso=event.get("date"), dry_run=event.get("dry_run"))
    log.info("run finished: %s", result.get("status"))
    return result
