"""A stub LLM for exercising the pipeline without an API key.

It verifies wiring, prompt formatting, response parsing, and every downstream
guard (length, threading, privacy). It says nothing about summary quality — for
that you need a real key and `local_run.py` without --fake-llm.
"""

from __future__ import annotations

import re


def install(llm_module, *, verbose: bool = False) -> None:
    """Replace llm.complete_json with a deterministic stand-in."""

    def fake(system: str, user: str, *, label: str, max_tokens: int = 2000) -> dict:
        if verbose:
            print(f"\n--- FAKE LLM [{label}] system prompt is {len(system)} chars, "
                  f"user payload {len(user)} chars")

        if label.startswith("triage"):
            # Pick the first few real article numbers out of the rendered TOC, so
            # downstream stages get numbers that actually exist in the document.
            numbers = [int(n) for n in re.findall(r"(?m)^(\d+)\.", user)][:4]
            return {
                "overall_newsworthiness": 8,
                "headline_angle": "Δοκιμαστική είδηση από τον stub",
                "selected": [
                    {"number": n, "score": 9 - i, "reason": f"δοκιμαστικός λόγος {i}"}
                    for i, n in enumerate(numbers)
                ],
            }

        if label.startswith("extract"):
            return {
                "headline": "Δοκιμαστικός τίτλος είδησης από τον stub",
                "contains_personal_names": False,
                "provisions": [
                    {
                        "what_changes": f"Δοκιμαστική ρύθμιση {i} " + "με αρκετό κείμενο " * 6,
                        "who_is_affected": "όλους τους πολίτες",
                        "amount": "100 ευρώ" if i == 0 else None,
                        "effective_date": "01/01/2027" if i == 1 else None,
                        "importance": 9 - i,
                    }
                    for i in range(3)
                ],
            }

        if label.startswith("compose"):
            return {"tweets": ["Δοκιμαστικό κείμενο " * 4, "Δεύτερο δοκιμαστικό κείμενο"]}

        if label.startswith("shorten"):
            # Mimic a model that ignores the budget, so truncation gets exercised.
            return {"text": user[-200:]}

        return {}

    llm_module.complete_json = fake
