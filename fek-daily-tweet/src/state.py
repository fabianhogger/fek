"""DynamoDB-backed dedupe and audit trail.

Checked before any download or model call, so a retried invocation costs nothing.
Thread tweet ids are recorded incrementally: if posting fails halfway through a
thread, a rerun must not repost the head.
"""

from __future__ import annotations

import functools
import json
import logging
import time
from datetime import datetime, timezone

from config import settings

log = logging.getLogger(__name__)


@functools.lru_cache(maxsize=1)
def _table():
    import boto3

    return boto3.resource("dynamodb").Table(settings.table_name)


def already_posted(fek_id: str) -> bool:
    try:
        item = _table().get_item(Key={"fek_id": fek_id}).get("Item")
    except Exception as exc:  # noqa: BLE001 — never let bookkeeping block a run
        log.warning("dedupe lookup failed for %s (%s), assuming not posted", fek_id, exc)
        return False
    if item:
        log.info("%s already posted at %s", fek_id, item.get("posted_at"))
        return True
    return False


def mark_posted(
    fek_id: str,
    *,
    label: str,
    tweet_ids: list[str],
    facts: dict | None = None,
    tweets: list[str] | None = None,
) -> None:
    """Record a completed (or partially completed) post.

    ``facts`` is stored so the editorial policy can be tuned against what the
    pipeline actually decided, without re-running it.
    """
    item = {
        "fek_id": fek_id,
        "label": label,
        "tweet_ids": tweet_ids,
        "tweets": tweets or [],
        "posted_at": datetime.now(timezone.utc).isoformat(),
        "expires_at": int(time.time()) + settings.ttl_days * 86400,
    }
    if facts:
        item["facts_json"] = json.dumps(facts, ensure_ascii=False)
    try:
        _table().put_item(Item=item)
        log.info("recorded %s (%d tweets)", fek_id, len(tweet_ids))
    except Exception as exc:  # noqa: BLE001
        log.error("failed to record %s (%s) — risk of a duplicate post", fek_id, exc)
