"""Thin Anthropic wrapper: schema-enforced JSON, bounded retries, token accounting.

Two things differ from a naive port of an OpenAI client, and both bite silently:

1. Sonnet 5 runs adaptive thinking by default, and ``max_tokens`` caps thinking
   *plus* response text. Budgets sized for a model that only produced an answer
   will truncate the JSON mid-object, so the ceilings here are deliberately high
   and a `max_tokens` stop is treated as a configuration error rather than
   something to retry.
2. Safety classifiers can decline a request — HTTP 200, ``stop_reason ==
   "refusal"``, empty or partial content. Reading ``content[0]`` without
   checking would raise on a perfectly normal response.
"""

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
usage: dict[str, int] = {"input_tokens": 0, "output_tokens": 0, "calls": 0}


class RefusedError(RuntimeError):
    """The model declined the request. Skip this document, try the next one."""


@functools.lru_cache(maxsize=1)
def _client():
    import anthropic

    key = secrets().get("anthropic_api_key")
    if not key:
        raise RuntimeError(
            "No Anthropic key: set ANTHROPIC_API_KEY or the SSM parameter "
            f"{settings.ssm_prefix}/anthropic_api_key"
        )
    return anthropic.Anthropic(api_key=key, timeout=settings.anthropic_timeout)


def _text_of(response) -> str:
    """The first text block. With thinking on, content[0] is a thinking block."""
    for block in response.content:
        if block.type == "text":
            return block.text
    return ""


def complete_json(
    system: str,
    user: str,
    *,
    label: str,
    schema: dict[str, Any] | None = None,
    max_tokens: int = 8000,
    thinking: bool = True,
    effort: str | None = None,
) -> dict[str, Any]:
    """Run a message and return the parsed JSON object.

    ``schema`` is enforced by the API rather than merely requested in the prompt,
    so a successful response is structurally valid by construction. Callers still
    coerce values (see pipeline/extract.py) because the schema constrains shape,
    not sense.
    """
    import anthropic

    request: dict[str, Any] = {
        "model": settings.anthropic_model,
        "max_tokens": max_tokens,
        "system": system,
        "messages": [{"role": "user", "content": user}],
        "output_config": {"effort": effort or settings.effort},
        "thinking": {"type": "adaptive"} if thinking else {"type": "disabled"},
    }
    if schema:
        request["output_config"]["format"] = {
            "type": "json_schema",
            "schema": schema,
        }

    last: Exception | None = None
    for attempt in range(_RETRIES):
        try:
            response = _client().messages.create(**request)

            if response.usage:
                usage["input_tokens"] += response.usage.input_tokens
                usage["output_tokens"] += response.usage.output_tokens
            usage["calls"] += 1

            if response.stop_reason == "refusal":
                detail = getattr(response, "stop_details", None)
                raise RefusedError(
                    f"{label}: declined"
                    + (f" ({detail.category})" if detail and detail.category else "")
                )

            if response.stop_reason == "max_tokens":
                # Retrying cannot help — thinking plus output exceeded the budget.
                raise RuntimeError(
                    f"{label}: hit the {max_tokens}-token ceiling, so the JSON is "
                    "truncated. Raise the matching *_max_tokens setting."
                )

            log.info(
                "%s: %d in + %d out tokens",
                label,
                response.usage.input_tokens if response.usage else 0,
                response.usage.output_tokens if response.usage else 0,
            )
            return json.loads(_text_of(response))

        except (anthropic.RateLimitError, anthropic.APITimeoutError) as exc:
            last = exc
            if attempt < _RETRIES - 1:
                backoff = 2**attempt
                log.warning("%s rate-limited (%s), retrying in %ss", label, exc, backoff)
                time.sleep(backoff)
        except anthropic.APIConnectionError as exc:
            last = exc
            if attempt < _RETRIES - 1:
                time.sleep(2**attempt)
        except anthropic.APIStatusError as exc:
            # 4xx other than 429 is our bug — a bad schema, a bad model id.
            if exc.status_code < 500:
                raise
            last = exc
            if attempt < _RETRIES - 1:
                time.sleep(2**attempt)
        except json.JSONDecodeError as exc:
            # Near-impossible with an enforced schema, but a truncated response
            # would land here rather than in the max_tokens branch above.
            last = exc
            log.warning("%s returned unparseable JSON: %s", label, exc)
            if attempt < _RETRIES - 1:
                time.sleep(1)

    raise RuntimeError(f"{label} failed after {_RETRIES} attempts: {last}")
