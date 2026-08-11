"""Thin OpenAI wrapper: JSON mode, bounded retries, token accounting."""

from __future__ import annotations

import functools
import json
import logging
import time
from typing import Any

from config import secrets, settings

log = logging.getLogger(__name__)

_RETRIES = 3

# Accumulated across an invocation so the handler can log what a run cost.
usage: dict[str, int] = {"prompt_tokens": 0, "completion_tokens": 0, "calls": 0}


@functools.lru_cache(maxsize=1)
def _client():
    from openai import OpenAI

    key = secrets().get("openai_api_key")
    if not key:
        raise RuntimeError(
            "No OpenAI key: set OPENAI_API_KEY or the SSM parameter "
            f"{settings.ssm_prefix}/openai_api_key"
        )
    return OpenAI(api_key=key, timeout=settings.openai_timeout)


def complete_json(
    system: str, user: str, *, label: str, max_tokens: int = 2000
) -> dict[str, Any]:
    """Run a chat completion in JSON mode and return the parsed object."""
    from openai import APIError, APITimeoutError, RateLimitError

    last: Exception | None = None
    for attempt in range(_RETRIES):
        try:
            response = _client().chat.completions.create(
                model=settings.openai_model,
                response_format={"type": "json_object"},
                max_tokens=max_tokens,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
            )
            if response.usage:
                usage["prompt_tokens"] += response.usage.prompt_tokens
                usage["completion_tokens"] += response.usage.completion_tokens
            usage["calls"] += 1

            content = response.choices[0].message.content or "{}"
            parsed = json.loads(content)
            log.info(
                "%s: %d prompt + %d completion tokens",
                label,
                response.usage.prompt_tokens if response.usage else 0,
                response.usage.completion_tokens if response.usage else 0,
            )
            return parsed
        except (RateLimitError, APITimeoutError, APIError) as exc:
            last = exc
            if attempt < _RETRIES - 1:
                backoff = 2**attempt
                log.warning("%s failed (%s), retrying in %ss", label, exc, backoff)
                time.sleep(backoff)
        except json.JSONDecodeError as exc:
            # JSON mode makes this rare, but a truncated response can still break it.
            last = exc
            log.warning("%s returned unparseable JSON: %s", label, exc)
            if attempt < _RETRIES - 1:
                time.sleep(1)

    raise RuntimeError(f"{label} failed after {_RETRIES} attempts: {last}")
