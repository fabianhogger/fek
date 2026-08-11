"""Composition tests: length enforcement, threading, and the privacy rule.

These are the checks that stand between the pipeline and a bad post, so they run
without touching the network — the LLM shortening path is monkeypatched out.
"""

import os

import pytest
from conftest import FIXTURES

import fek_doc
from fek_doc import FekDoc
from pipeline import compose as compose_mod
from pipeline.compose import TWEET_LIMIT, ComposeRejected, compose
from pipeline.extract import Facts, Provision

PDF_URL = "https://ia37rg02wpsa01.blob.core.windows.net/fek/01/2026/20260100121.pdf"


@pytest.fixture(autouse=True)
def no_llm(monkeypatch):
    """Force the deterministic truncation path instead of an API call."""
    monkeypatch.setattr(
        compose_mod, "_shorten", lambda text, budget, **kw: compose_mod._truncate(text, budget)
    )
    monkeypatch.setattr(compose_mod.settings, "compose_mode", "template")
    monkeypatch.setattr(compose_mod.settings, "include_link", True)
    monkeypatch.setattr(compose_mod.settings, "thread_mode", "auto")
    monkeypatch.setattr(compose_mod.settings, "thread_max_tweets", 4)
    monkeypatch.setattr(compose_mod.settings, "thread_min_importance", 6)


def make_doc(full_text="", label="Α 121/2026"):
    return FekDoc(
        fek_id="20260100121",
        label=label,
        issue_group=1,
        pdf_url=PDF_URL,
        page_count=112,
        law_type="Ν.",
        law_number="5324",
        law_title="Σύσταση νομικού προσώπου",
        full_text=full_text,
    )


def make_facts(provisions, headline="Νέος οργανισμός πολιτιστικής κληρονομιάς"):
    return Facts(
        law_name="Ν. 5324/2026",
        headline=headline,
        provisions=provisions,
        pdf_url=PDF_URL,
    )


def weighted(text):
    """Replicate X's counting: any URL costs 23 regardless of real length."""
    return len(text) - (len(PDF_URL) - 23 if PDF_URL in text else 0)


class TestLength:
    def test_single_tweet_fits(self):
        facts = make_facts([Provision("Το παράβολο ορίζεται στα 100 ευρώ", "πολίτες", "100 ευρώ", None, 8)])
        tweets = compose(facts, make_doc())
        assert len(tweets) == 1
        assert weighted(tweets[0]) <= TWEET_LIMIT

    def test_overlong_provision_is_truncated(self):
        facts = make_facts([Provision("Α" * 600, "πολίτες", None, None, 9)])
        tweets = compose(facts, make_doc())
        assert weighted(tweets[0]) <= TWEET_LIMIT
        assert tweets[0].endswith(PDF_URL)

    def test_every_tweet_in_a_thread_fits(self):
        facts = make_facts(
            [Provision(f"Ρύθμιση {i} " + "λέξη " * 80, "όλους", None, None, 9) for i in range(4)]
        )
        tweets = compose(facts, make_doc())
        assert len(tweets) > 1
        for text in tweets:
            assert weighted(text) <= TWEET_LIMIT, f"{weighted(text)} chars: {text}"

    def test_truncation_lands_on_a_word_boundary(self):
        facts = make_facts([Provision("λέξη " * 200, "όλους", None, None, 9)])
        tweets = compose(facts, make_doc())
        assert tweets[0].split(PDF_URL)[0].rstrip().endswith("…")

    def test_link_is_omitted_when_disabled(self, monkeypatch):
        monkeypatch.setattr(compose_mod.settings, "include_link", False)
        facts = make_facts([Provision("Σύντομη ρύθμιση", "όλους", None, None, 8)])
        tweets = compose(facts, make_doc())
        assert PDF_URL not in tweets[0]


class TestThreading:
    def test_auto_stays_single_for_one_significant_provision(self):
        facts = make_facts(
            [
                Provision("Σημαντική ρύθμιση", "όλους", None, None, 9),
                Provision("Ασήμαντη ρύθμιση", "λίγους", None, None, 2),
            ]
        )
        assert len(compose(facts, make_doc())) == 1

    def test_auto_threads_for_several_significant_provisions(self):
        facts = make_facts([Provision(f"Ρύθμιση {i}", "όλους", None, None, 8) for i in range(3)])
        tweets = compose(facts, make_doc())
        assert len(tweets) == 4  # head + 3
        assert tweets[0].startswith("1/4 ")

    def test_thread_is_capped(self, monkeypatch):
        monkeypatch.setattr(compose_mod.settings, "thread_max_tweets", 2)
        facts = make_facts([Provision(f"Ρύθμιση {i}", "όλους", None, None, 9) for i in range(6)])
        assert len(compose(facts, make_doc())) == 2

    def test_single_mode_never_threads(self, monkeypatch):
        monkeypatch.setattr(compose_mod.settings, "thread_mode", "single")
        facts = make_facts([Provision(f"Ρύθμιση {i}", "όλους", None, None, 9) for i in range(5)])
        assert len(compose(facts, make_doc())) == 1

    def test_only_the_last_tweet_carries_the_link(self):
        facts = make_facts([Provision(f"Ρύθμιση {i}", "όλους", None, None, 8) for i in range(3)])
        tweets = compose(facts, make_doc())
        assert [PDF_URL in t for t in tweets] == [False, False, False, True]

    def test_head_names_the_law(self):
        facts = make_facts([Provision("Ρύθμιση", "όλους", None, None, 8)])
        assert compose(facts, make_doc())[0].startswith("Ν. 5324/2026:")


class TestPrivacy:
    def test_extraction_flag_blocks_posting(self):
        facts = make_facts([Provision("Κάτι", "κάποιους", None, None, 9)])
        facts.contains_personal_names = True
        with pytest.raises(ComposeRejected, match="personal names"):
            compose(facts, make_doc())

    def test_name_from_the_source_document_blocks_posting(self):
        # The name is discovered from the gazette's own (επ)/(ον) markers rather
        # than guessed from capitalisation, which would flag ministry names.
        doc = make_doc(full_text="Επιβολή τελών στον (επ) OMRAN (ον) SAMIR του SAMIR.")
        facts = make_facts([Provision("Επιβλήθηκε πρόστιμο στον Omran", "έναν", None, None, 9)])
        with pytest.raises(ComposeRejected, match="private individual"):
            compose(facts, doc)

    def test_leaked_marker_blocks_posting(self):
        facts = make_facts([Provision("Πρόστιμο στον (επ) ΤΙΣ (ον) ΤΑΔΕ", "έναν", None, None, 9)])
        with pytest.raises(ComposeRejected, match="personal identifiers"):
            compose(facts, make_doc())

    def test_ministry_names_are_not_flagged(self):
        doc = make_doc(full_text="ΟΙ ΥΠΟΥΡΓΟΙ ΕΘΝΙΚΗΣ ΟΙΚΟΝΟΜΙΑΣ ΚΑΙ ΟΙΚΟΝΟΜΙΚΩΝ")
        facts = make_facts([Provision("Το Υπουργείο Εθνικής Οικονομίας αναλαμβάνει", "όλους", None, None, 8)])
        assert compose(facts, doc)  # must not raise

    def test_real_issue_b_names_are_detected(self):
        """End-to-end against the actual gazette issue that names fined individuals."""
        doc = fek_doc.parse(
            os.path.join(FIXTURES, "20260205013.pdf"),
            fek_id="20260205013",
            label="Β 5013/2026",
            issue_group=2,
            pdf_url=PDF_URL,
        )
        names = compose_mod.private_names(doc)
        assert "OMRAN" in names
        assert "SAMIR" in names

    def test_nothing_to_report_is_rejected(self):
        with pytest.raises(ComposeRejected, match="nothing substantive"):
            compose(make_facts([], headline=""), make_doc())
