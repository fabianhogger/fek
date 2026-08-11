"""Configuration: plain env vars for behaviour, SSM SecureStrings for secrets."""

from __future__ import annotations

import functools
import logging
import os
from dataclasses import dataclass

log = logging.getLogger(__name__)

PROMPT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "prompts")


def _int(name: str, default: int) -> int:
    try:
        return int(os.environ.get(name, default))
    except ValueError:
        log.warning("%s is not an integer, falling back to %s", name, default)
        return default


def _bool(name: str, default: bool) -> bool:
    return os.environ.get(name, str(default)).strip().lower() in ("1", "true", "yes")


@dataclass
class Settings:
    """Runtime knobs. Mutable so tests can override a single field."""

    # Behaviour
    dry_run: bool = _bool("DRY_RUN", True)
    include_link: bool = _bool("INCLUDE_LINK", True)
    timezone: str = os.environ.get("TZ_NAME", "Europe/Athens")

    # Selection
    max_candidates: int = _int("MAX_CANDIDATES", 8)
    min_newsworthiness: int = _int("MIN_NEWSWORTHINESS", 4)
    max_pdf_bytes: int = _int("MAX_PDF_BYTES", 120 * 1024 * 1024)

    # Triage / extraction
    triage_top_k: int = _int("TRIAGE_TOP_K", 4)
    max_toc_chars: int = _int("MAX_TOC_CHARS", 24_000)
    max_extract_chars: int = _int("MAX_EXTRACT_CHARS", 40_000)

    # Composition
    thread_mode: str = os.environ.get("THREAD_MODE", "auto")  # single|auto|always
    thread_max_tweets: int = _int("THREAD_MAX_TWEETS", 4)
    thread_min_importance: int = _int("THREAD_MIN_IMPORTANCE", 6)
    compose_mode: str = os.environ.get("COMPOSE_MODE", "template")  # template|llm

    # OpenAI
    openai_model: str = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")
    openai_timeout: int = _int("OPENAI_TIMEOUT", 90)

    # AWS
    table_name: str = os.environ.get("TABLE_NAME", "fek-posted-documents")
    ssm_prefix: str = os.environ.get("SSM_PREFIX", "/fek-daily-tweet")
    ttl_days: int = _int("TTL_DAYS", 90)


settings = Settings()


@functools.lru_cache(maxsize=1)
def secrets() -> dict[str, str]:
    """Fetch every SecureString under the configured prefix in one call.

    Cached at module scope, so warm Lambda invocations reuse it. Falls back to
    environment variables when SSM is unavailable, which is how local runs work.
    """
    resolved: dict[str, str] = {}
    try:
        import boto3

        client = boto3.client("ssm")
        paginator = client.get_paginator("get_parameters_by_path")
        for page in paginator.paginate(
            Path=settings.ssm_prefix, Recursive=True, WithDecryption=True
        ):
            for param in page["Parameters"]:
                key = param["Name"].rsplit("/", 1)[-1]
                resolved[key] = param["Value"]
        log.info("loaded %d parameters from %s", len(resolved), settings.ssm_prefix)
    except Exception as exc:  # noqa: BLE001 — local runs legitimately have no SSM
        log.warning("SSM unavailable (%s), falling back to environment variables", exc)

    for key, env in (
        ("openai_api_key", "OPENAI_API_KEY"),
        ("consumer_key", "TWITTER_CONSUMER_KEY"),
        ("consumer_secret", "TWITTER_CONSUMER_SECRET"),
        ("access_token", "TWITTER_ACCESS_TOKEN"),
        ("access_token_secret", "TWITTER_ACCESS_TOKEN_SECRET"),
    ):
        if not resolved.get(key) and os.environ.get(env):
            resolved[key] = os.environ[env]

    return resolved


@functools.lru_cache(maxsize=8)
def prompt(name: str) -> str:
    """Read a prompt template from src/prompts/, cached across invocations."""
    with open(os.path.join(PROMPT_DIR, f"{name}.md"), encoding="utf-8") as fh:
        return fh.read()


def editorial_policy() -> str:
    return prompt("editorial_policy")
