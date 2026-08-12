#!/usr/bin/env python3
"""Run the pipeline locally against a real date, without AWS.

    python scripts/local_run.py --date 2026-07-31 --dry-run --explain

Credentials come from the environment (ANTHROPIC_API_KEY, TWITTER_*) when SSM is
unavailable. --stage lets you stop early: `parse` needs no API key at all.
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
import tempfile

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_ROOT, "src"))
sys.path.insert(0, os.path.join(_ROOT, "scripts"))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", required=True, help="YYYY-MM-DD")
    parser.add_argument("--dry-run", action="store_true", default=None)
    parser.add_argument("--post", action="store_true", help="actually post to X")
    parser.add_argument("--explain", action="store_true", help="dump every stage")
    parser.add_argument(
        "--stage",
        choices=["list", "parse", "triage", "extract", "compose"],
        default="compose",
    )
    parser.add_argument("--label", help="force a specific issue, e.g. 'Α 121/2026'")
    parser.add_argument(
        "--fake-llm",
        action="store_true",
        help="stub out the LLM to exercise the wiring without an API key",
    )
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s %(message)s")
    os.environ.setdefault("DRY_RUN", "false" if args.post else "true")

    if args.fake_llm:
        import fake_llm
        import llm as llm_module

        fake_llm.install(llm_module, verbose=args.explain)
        print("!!! --fake-llm: stubbed model, output is meaningless by design")

    import et_client
    import fek_doc
    import llm
    from config import settings
    from pipeline import select
    from pipeline.compose import compose
    from pipeline.extract import extract
    from pipeline.triage import triage

    publications = et_client.list_publications(args.date)
    print(f"\n=== {len(publications)} publications on {args.date}")
    for pub in publications[:20]:
        print(f"    {pub.label:24} {pub.pages:>4}p  {pub.pdf_url}")
    if args.stage == "list" or not publications:
        return 0

    ranked = select.candidates(publications)
    if args.label:
        ranked = [p for p in publications if p.label == args.label] or ranked
    if not ranked:
        print("\nno Τεύχος Α or Β candidates")
        return 0

    pub = ranked[0]
    print(f"\n=== selected {pub.label} ({pub.pages} pages)")

    with tempfile.TemporaryDirectory() as workdir:
        path = os.path.join(workdir, f"{pub.fek_id}.pdf")
        et_client.download_pdf(pub, path, settings.max_pdf_bytes)
        doc = fek_doc.parse(
            path,
            fek_id=pub.fek_id,
            label=pub.label,
            issue_group=pub.issue_group,
            pdf_url=pub.pdf_url,
        )

        print(f"\n=== parsed: {doc.law_name}")
        print(f"    title      : {doc.law_title[:300]}")
        print(f"    full text  : {len(doc.full_text):,} chars")
        print(f"    toc        : {len(doc.toc)} entries ({len(doc.render_toc()):,} chars)")
        print(f"    sections   : {len(doc.sections)}")
        if args.explain:
            for entry in doc.toc[:15]:
                print(f"      · {entry.render()[:160]}")
            if len(doc.toc) > 15:
                print(f"      … {len(doc.toc) - 15} more")
        if args.stage == "parse":
            return 0

        verdict = triage(doc)
        print(f"\n=== triage: score {verdict.newsworthiness}/10")
        print(f"    angle: {verdict.headline_angle}")
        for number in verdict.selected:
            title = next((s.title for s in doc.sections if s.number == number), "")
            print(f"      · Άρθρο {number}: {title[:80]}")
            print(f"        → {verdict.reasons.get(number, '')}")
        if not verdict.passes:
            print(f"\n    BELOW THRESHOLD ({settings.min_newsworthiness}) — would move on")
        if args.stage == "triage":
            return 0

        facts = extract(doc, verdict.selected)
        print(f"\n=== extract: {len(facts.provisions)} provisions")
        if args.explain:
            print(json.dumps(facts.as_dict(), ensure_ascii=False, indent=2))
        else:
            print(f"    headline: {facts.headline}")
            for prov in facts.provisions:
                print(f"      [{prov.importance}] {prov.what_changes[:120]}")
        if args.stage == "extract":
            return 0

        tweets = compose(facts, doc)
        print(f"\n=== composed {len(tweets)} tweet(s)")
        for index, text in enumerate(tweets, 1):
            flag = "OK " if len(text) <= 280 else "OVER"
            print(f"\n  [{flag} {len(text):>3} chars] {text}")

        print(f"\n=== tokens: {llm.usage}")

        if args.post:
            import tweeter

            ids = tweeter.post_thread(tweets)
            print(f"\nposted: {ids}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
