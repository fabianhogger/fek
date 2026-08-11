"""Posting to X via the v2 API (OAuth 1.0a user context)."""

from __future__ import annotations

import functools
import logging

from config import secrets

log = logging.getLogger(__name__)

_REQUIRED = ("consumer_key", "consumer_secret", "access_token", "access_token_secret")


@functools.lru_cache(maxsize=1)
def _client():
    import tweepy

    creds = secrets()
    missing = [key for key in _REQUIRED if not creds.get(key)]
    if missing:
        raise RuntimeError(f"missing X credentials: {', '.join(missing)}")

    return tweepy.Client(
        consumer_key=creds["consumer_key"],
        consumer_secret=creds["consumer_secret"],
        access_token=creds["access_token"],
        access_token_secret=creds["access_token_secret"],
    )


def post_thread(tweets: list[str], on_posted=None) -> list[str]:
    """Post ``tweets`` as a chain of replies. Returns the ids created.

    ``on_posted`` is invoked after each successful tweet so callers can persist
    progress; a failure partway through a thread leaves the earlier tweets up and
    recorded rather than orphaned.
    """
    client = _client()
    ids: list[str] = []
    reply_to = None

    for index, text in enumerate(tweets):
        try:
            response = client.create_tweet(text=text, in_reply_to_tweet_id=reply_to)
        except Exception:
            log.error("failed to post tweet %d/%d", index + 1, len(tweets))
            if ids and on_posted:
                on_posted(ids)
            raise
        tweet_id = str(response.data["id"])
        ids.append(tweet_id)
        reply_to = tweet_id
        log.info("posted %d/%d → %s", index + 1, len(tweets), tweet_id)
        if on_posted:
            on_posted(ids)

    return ids
