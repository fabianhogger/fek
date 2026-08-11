"""Parser tests against three real gazette issues.

The fixtures were chosen to cover the shapes that actually break naive parsing:
a 112-page law with a table of contents, a 2-page decree without one, and a
Τεύχος Β issue whose acts are delimited by bare "(n)" markers.
"""

import pytest
from conftest import fixture

import fek_doc


def _parse(fek_id, label, issue_group):
    return fek_doc.parse(
        fixture(fek_id),
        fek_id=fek_id,
        label=label,
        issue_group=issue_group,
        pdf_url=f"https://example.invalid/{fek_id}.pdf",
    )


@pytest.fixture(scope="module")
def law():
    """Ν. 5324/2026 — 112 pages, 141 articles, full ΠΙΝΑΚΑΣ ΠΕΡΙΕΧΟΜΕΝΩΝ."""
    return _parse("20260100121", "Α 121/2026", 1)


@pytest.fixture(scope="module")
def decree():
    """Π.Δ. 47/2026 — 2 pages, no table of contents."""
    return _parse("20260100127", "Α 127/2026", 1)


@pytest.fixture(scope="module")
def issue_b():
    """ΦΕΚ Β 5013/2026 — three acts, two of them about named individuals."""
    return _parse("20260205013", "Β 5013/2026", 2)


@pytest.fixture(scope="module")
def cabinet_act():
    """Π.Υ.Σ. 22/2026 — no articles, and a 76-page annex in a broken encoding."""
    return _parse("20260100126", "Α 126/2026", 1)


class TestLawName:
    def test_latin_lookalike_heading(self, law):
        # This issue spells it "NOMOΣ" with a Latin N and O. Matching the Greek
        # spelling alone silently fails on exactly the largest laws.
        assert law.law_type == "Ν."
        assert law.law_number == "5324"
        assert law.law_name == "Ν. 5324/2026"

    def test_decree(self, decree):
        assert decree.law_name == "Π.Δ. 47/2026"

    def test_title_is_dehyphenated(self, law):
        # Source reads "Δι -\nαχείρισης" across a line break.
        assert "Διαχείρισης" in law.law_title
        assert "Δι αχείρισης" not in law.law_title

    def test_title_stops_at_enacting_formula(self, law):
        assert "ΠΡΟΕΔΡΟΣ" not in law.law_title
        assert law.law_title.startswith("Σύσταση νομικού προσώπου")

    def test_issue_b_has_no_law_type(self, issue_b):
        assert issue_b.law_type == ""
        assert issue_b.law_name == "ΦΕΚ Β 5013/2026"


class TestTableOfContents:
    def test_full_toc_parsed(self, law):
        assert len(law.toc) == 141
        assert law.toc[0].number == 1
        assert law.toc[0].title == "Σκοπός"

    def test_toc_carries_structural_context(self, law):
        assert law.toc[0].part.startswith("ΜΕΡΟΣ Α")
        assert "ΓΕΝΙΚΕΣ ΔΙΑΤΑΞΕΙΣ" in law.toc[0].chapter

    def test_toc_is_far_smaller_than_the_document(self, law):
        # The whole point of triaging on the TOC: ~19k chars instead of ~454k.
        assert len(law.full_text) > 400_000
        assert len(law.render_toc()) < 30_000

    def test_short_document_gets_a_synthetic_toc(self, decree):
        assert len(decree.toc) == 3
        assert decree.toc[0].title == "Σίτιση και διαμονή Δοκίμων -"

    def test_issue_b_toc(self, issue_b):
        # pypdf renders this heading as "ΠΕΡΙΕΧΟΜΕΝΑ"; pdftotext splits it as
        # "ΠΕΡ ΙΕΧΟΜΕΝΑ", so the anchor is matched whitespace-insensitively.
        assert len(issue_b.toc) == 3
        assert issue_b.toc[0].title.startswith("Κοστολόγηση διαγνωστικής")

    def test_issue_b_toc_page_numbers_stripped(self, issue_b):
        assert not issue_b.toc[0].title.endswith("56349")


class TestSections:
    def test_articles_segmented(self, law):
        assert len(law.sections) == 141
        assert law.sections[0].number == 1
        assert law.sections[0].title == "Σκοπός"
        assert "εκσυγχρονισμός" in law.sections[0].text

    def test_article_numbers_are_unique_and_ordered(self, law):
        numbers = [s.number for s in law.sections]
        assert numbers == sorted(numbers)
        assert len(numbers) == len(set(numbers))

    def test_toc_body_split_does_not_leak_toc_into_sections(self, law):
        # If the split point were wrong, article 1's text would be the TOC listing.
        assert "ΠΙΝΑΚΑΣ ΠΕΡΙΕΧΟΜΕΝΩΝ" not in law.sections[0].text
        assert len(law.sections[0].text) < 3000

    def test_issue_b_acts_split_on_bare_markers(self, issue_b):
        # Acts 2 and 3 have no "Αριθμ." line — only a "(2)" / "(3)" marker.
        assert [s.number for s in issue_b.sections] == [1, 2, 3]
        assert "λαθρεμπορίας" in issue_b.sections[1].text

    def test_section_text_respects_budget(self, law):
        text = law.section_text([1, 2, 3], max_chars=500)
        assert len(text) <= 520  # allows for the joining separator


class TestCabinetAct:
    """Acts of the Cabinet head differently and often carry no articles at all."""

    def test_heading_recognised(self, cabinet_act):
        assert cabinet_act.law_name == "Π.Υ.Σ. 22/2026"
        assert cabinet_act.law_title == "Έγκριση της Εθνικής Στρατηγικής για τα Ύδατα."

    def test_unstructured_body_is_not_one_giant_blob(self, cabinet_act):
        # Without chunking this parsed as a single 190k-character section, which
        # gives triage nothing to choose between.
        assert len(cabinet_act.sections) > 1

    def test_undecodable_annex_is_dropped(self, cabinet_act):
        # The strategy annex uses a subset font with no ToUnicode map; poppler
        # fails on it identically, so it cannot be recovered — only discarded.
        for section in cabinet_act.sections:
            assert not fek_doc.is_garbled(section.text)

    def test_readable_operative_text_survives(self, cabinet_act):
        combined = " ".join(s.text for s in cabinet_act.sections)
        assert "Εφημερίδα" in combined


class TestGarbledDetection:
    def test_flags_broken_encoding(self):
        sample = (
            "D\\}ZR^l}N]\\aRXRg}a\\Z}]\\XbaVYlaR^\\}cb`VWl}]l^\\}WNV}a\\}URYoXV\\}"
            "WnUR}Y\\^cp_}Sfp_}W\\VZfZVWp_}\\^PnZf`T_}WNV}\\VW\\Z\\YVWp_}Q^N`aT^VlaTaN_~}"
        ) * 3
        assert fek_doc.is_garbled(sample)

    def test_accepts_normal_greek(self, law):
        assert not fek_doc.is_garbled(law.sections[5].text)

    def test_accepts_greek_with_english_terms(self, issue_b):
        # This act is full of "Prosigna Breast Cancer Prognostic Gene Signature".
        assert not fek_doc.is_garbled(issue_b.sections[0].text)

    def test_ignores_short_strings(self):
        assert not fek_doc.is_garbled("}~\\}~\\")


class TestTextCleaning:
    def test_page_furniture_removed(self, law):
        assert "ΕΦΗΜΕΡΙΔΑ ΤΗΣ ΚΥΒΕΡΝΗΣΕΩΣ" not in law.sections[10].text

    def test_dehyphenation_keeps_real_dashes(self):
        text = "Κληρονομιάς - Στρατη-\nγική και δια-\nνομή"
        cleaned = fek_doc._dehyphenate(text)
        assert "Στρατηγική" in cleaned
        assert "διανομή" in cleaned
        assert "Κληρονομιάς - " in cleaned

    def test_squash_survives_kerning(self):
        assert fek_doc._squash("ΠΕΡ ΙΕΧΟΜΕΝΑ") == "ΠΕΡΙΕΧΟΜΕΝΑ"

    def test_confusable_normalisation_preserves_offsets(self):
        source = "NOMOΣ ΥΠ’ ΑΡΙΘΜ 5324"
        assert len(fek_doc._normalise(source)) == len(source)
        assert fek_doc._normalise(source).startswith("ΝΟΜΟΣ")
