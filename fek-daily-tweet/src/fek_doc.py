"""Deterministic structure extraction from a ΦΕΚ PDF.

No LLM is involved here. The point is to turn a gazette issue — which can run to
112 pages and 460k characters — into a small table of contents that a model can
triage cheaply, plus per-article text that can be fetched on demand.

Three text artefacts of the source PDFs are handled explicitly:

1. Line-break hyphenation: ``Στρατη-\\nγική``, ``Δι -\\nαχείρισης``.
2. Kerning spaces inside words: ``ΟΡΓ ΑΝΙΣΜΟΣ``, ``Γ ραμματείας``. Not repaired
   (that needs a lexicon and would risk merging genuinely separate words) —
   instead every structural anchor is matched whitespace-insensitively.
3. Latin/Greek confusables: the largest laws spell it ``NOMOΣ`` with a Latin N
   and O. Anchors are matched against a transliterated copy of the text.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field

from pypdf import PdfReader

log = logging.getLogger(__name__)

# Uppercase Latin letters that are visually identical to Greek ones. Applied only
# to a shadow copy used for anchor matching; str.translate is 1:1 so offsets into
# the original text stay valid.
_CONFUSABLES = str.maketrans("ABEZHIKMNOPTXY", "ΑΒΕΖΗΙΚΜΝΟΡΤΧΥ")

_LOWER = "α-ωάέήίόύώϊϋΐΰςa-z"

# Page furniture repeated on every page of every issue.
_FURNITURE = re.compile(
    r"(?m)^(?:"
    r"ΕΦΗΜΕΡΙΔΑ\s+ΤΗΣ\s+ΚΥΒΕΡΝΗΣΕΩΣ"
    r"|ΤΗΣ\s+ΕΛΛΗΝΙΚΗΣ\s+ΔΗΜΟΚΡΑΤΙΑΣ"
    r"|E"
    r"|\d*\s*Τεύχος\s+[Α-ΩA-Z]['’]?\s*\d+/\d{2}\.\d{2}\.\d{4}\s*\d*"
    r"|\d{1,6}"
    r")\s*$"
)

_ARTICLE = re.compile(r"(?m)^[ \t]*Άρθρο\s+(\d+)(?:[ \t]+(.*))?$")
_LAW_HEADING = re.compile(
    r"(ΝΟΜΟΣ|ΠΡΟΕΔΡΙΚΟ\s+ΔΙΑΤΑΓΜΑ|ΠΡΑΞΗ\s+ΝΟΜΟΘΕΤΙΚΟΥ\s+ΠΕΡΙΕΧΟΜΕΝΟΥ)"
    r"\s+ΥΠ['’]?\s*ΑΡΙΘΜ\.?\s*(\d+)"
)
# Acts of the Cabinet head differently: "Πράξη 22 της 30-7-2026" under a
# "ΠΡΑΞΕΙΣ ΥΠΟΥΡΓΙΚΟΥ ΣΥΜΒΟΥΛΙΟΥ" banner (which kerning may split as "ΣΥΜΒΟΥ ΛΙΟΥ").
_PYS_HEADING = re.compile(r"(?m)^[ \t]*Πράξη\s+(\d+)\s+της\s+([\d./-]+)")
_LAW_BODY_START = re.compile(
    r"(?m)^\s*(?:Ο|Η|ΟΙ|ΤΟ)\s+"
    r"(?:ΠΡΟΕΔΡΟΣ|ΥΠΟΥΡΓΟΣ|ΥΠΟΥΡΓΟΙ|ΑΝΤΙΠΡΟΕΔΡΟΣ|ΥΠΟΥΡΓΙΚΟ)\b"
)
_TOC_ANCHOR_A = re.compile(r"ΠΙΝΑΚΑΣΠΕΡΙΕΧΟΜΕΝΩΝ")
_TOC_ANCHOR_B = re.compile(r"ΠΕΡΙΕΧΟΜΕΝΑ")
_PART = re.compile(r"(?m)^[ \t]*(ΜΕΡΟΣ|ΚΕΦΑΛΑΙΟ)\s+([Α-Ω]+['’]?)\s*[:.]?\s*(.*)$")
# Τεύχος Β table of contents: "1 Κοστολόγηση ... 56349"
_TOC_ITEM_B = re.compile(r"(?m)^[ \t]*(\d{1,3})[ \t]+(\S.*)$")
# Acts within a Τεύχος Β issue are delimited by an "(n)" marker tying them back to
# the ΠΕΡΙΕΧΟΜΕΝΑ list. It sits either at the end of an "Αριθμ. …" protocol line or,
# for acts with no protocol number, alone on its own line.
_ACT_HEADING_B = re.compile(r"(?m)^[ \t]*(?:Αριθμ\.?[ \t]*(\S[^\n]*?)[ \t]*)?\((\d{1,3})\)[ \t]*$")

_TYPE_LABELS = {
    "ΝΟΜΟΣ": "Ν.",
    "ΠΡΟΕΔΡΙΚΟ ΔΙΑΤΑΓΜΑ": "Π.Δ.",
    "ΠΡΑΞΗ ΝΟΜΟΘΕΤΙΚΟΥ ΠΕΡΙΕΧΟΜΕΝΟΥ": "Π.Ν.Π.",
}

LAW_NAME_MAX = 400

# Free-form documents (national strategies approved by a cabinet act, for one)
# carry no headings at all, so they are chunked to give triage something to pick.
CHUNK_CHARS = 6000
CHUNK_PREVIEW = 180


@dataclass
class TocEntry:
    """One addressable unit of the document."""

    number: int  # Άρθρο number (Τεύχος Α) or ΑΠΟΦΑΣΕΙΣ item number (Τεύχος Β)
    title: str
    part: str = ""  # enclosing ΜΕΡΟΣ, for context
    chapter: str = ""  # enclosing ΚΕΦΑΛΑΙΟ

    def render(self) -> str:
        return f"{self.number}. {self.title}"


@dataclass
class Section:
    number: int
    title: str
    text: str


@dataclass
class FekDoc:
    fek_id: str
    label: str
    issue_group: int
    pdf_url: str
    page_count: int
    law_type: str  # "Ν." / "Π.Δ." / "Π.Ν.Π." / "" for Τεύχος Β
    law_number: str
    law_title: str
    toc: list[TocEntry] = field(default_factory=list)
    sections: list[Section] = field(default_factory=list)
    full_text: str = ""

    @property
    def law_name(self) -> str:
        """Short citable name, e.g. ``Ν. 5324/2026`` or ``ΦΕΚ Β' 5013/2026``."""
        if self.law_type and self.law_number:
            year = self.label.rsplit("/", 1)[-1]
            return f"{self.law_type} {self.law_number}/{year}"
        return f"ΦΕΚ {self.label}"

    def render_toc(self, limit: int | None = None) -> str:
        """Flatten the table of contents for a prompt.

        ΜΕΡΟΣ/ΚΕΦΑΛΑΙΟ headings are emitted only when they change rather than
        repeated on every entry — on the largest law that is the difference
        between 36k and 13k characters of prompt.
        """
        entries = self.toc[:limit] if limit else self.toc
        lines: list[str] = []
        part = chapter = ""
        for entry in entries:
            if entry.part and entry.part != part:
                part, chapter = entry.part, ""
                lines.append(f"\n{part}")
            if entry.chapter and entry.chapter != chapter:
                chapter = entry.chapter
                lines.append(chapter)
            lines.append(entry.render())
        return "\n".join(lines).strip()

    def section_text(self, numbers: list[int], max_chars: int) -> str:
        """Concatenate the named sections, truncated to a character budget."""
        wanted = [s for s in self.sections if s.number in set(numbers)]
        if not wanted:
            wanted = self.sections[:1]
        out, used = [], 0
        for section in wanted:
            block = f"Άρθρο {section.number} {section.title}\n{section.text}".strip()
            if used + len(block) > max_chars:
                block = block[: max(0, max_chars - used)]
            out.append(block)
            used += len(block)
            if used >= max_chars:
                break
        return "\n\n".join(out)


def _dehyphenate(text: str) -> str:
    """Rejoin words split across a line break.

    Only joins when the character after the break is lowercase, so genuine dashes
    between words (``Κληρονομιάς - Στρατηγική``) survive.
    """
    return re.sub(rf"([{_LOWER}])\s*-\s*\n\s*([{_LOWER}])", r"\1\2", text)


def _squash(text: str) -> str:
    """Strip all whitespace, for anchor matching that survives kerning artefacts."""
    return re.sub(r"\s+", "", text)


def _normalise(text: str) -> str:
    """Transliterate Latin lookalikes to Greek. 1:1, so offsets are preserved."""
    return text.translate(_CONFUSABLES)


def _clean(text: str) -> str:
    text = text.replace("\xa0", " ").replace("­", "")
    text = _FURNITURE.sub("", text)
    text = _dehyphenate(text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def extract_text(pdf_path: str, max_pages: int | None = None) -> tuple[str, int]:
    """Return (cleaned text, page count)."""
    reader = PdfReader(pdf_path)
    pages = reader.pages if max_pages is None else reader.pages[:max_pages]
    raw = "\n".join(page.extract_text() or "" for page in pages)
    return _clean(raw), len(reader.pages)


def _title_after(text: str, offset: int) -> str:
    """The act's title: everything between a heading and the enacting formula."""
    tail = text[offset:]
    end = _LAW_BODY_START.search(tail)
    title = tail[: end.start()] if end else tail[:LAW_NAME_MAX]
    return re.sub(r"\s*\n\s*", " ", title).strip()[:LAW_NAME_MAX]


def _parse_law_heading(text: str) -> tuple[str, str, str]:
    """Return (type label, number, title) for a Τεύχος Α document."""
    normalised = _normalise(text)

    match = _LAW_HEADING.search(normalised)
    if match:
        kind = re.sub(r"\s+", " ", match.group(1))
        return (
            _TYPE_LABELS.get(kind, kind),
            match.group(2),
            _title_after(text, match.end()),
        )

    cabinet = _PYS_HEADING.search(normalised)
    if cabinet:
        return "Π.Υ.Σ.", cabinet.group(1), _title_after(text, cabinet.end())

    return "", "", ""


def _split_toc_body(text: str) -> int:
    """Return the offset where the article body starts.

    Table-of-contents entries and body headings share the ``Άρθρο N`` form, but the
    body restarts numbering, so the split is the first point where the article
    number stops increasing.
    """
    matches = list(_ARTICLE.finditer(text))
    if len(matches) < 2:
        return 0
    previous = 0
    for match in matches:
        current = int(match.group(1))
        if current <= previous:
            return match.start()
        previous = current
    return 0


def _parse_toc_a(toc_text: str) -> list[TocEntry]:
    """Parse the ΠΙΝΑΚΑΣ ΠΕΡΙΕΧΟΜΕΝΩΝ of a Τεύχος Α law."""
    entries: list[TocEntry] = []
    part = chapter = ""

    # Entry titles wrap across lines, so walk line by line and accumulate.
    pending: TocEntry | None = None
    for line in toc_text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue

        structural = _PART.match(line)
        if structural:
            pending = None
            label = f"{structural.group(1)} {structural.group(2)}: {structural.group(3)}".strip()
            if structural.group(1) == "ΜΕΡΟΣ":
                part, chapter = label, ""
            else:
                chapter = label
            continue

        article = _ARTICLE.match(line)
        if article:
            pending = TocEntry(
                number=int(article.group(1)),
                title=(article.group(2) or "").strip(),
                part=part,
                chapter=chapter,
            )
            entries.append(pending)
        elif pending is not None:
            pending.title = f"{pending.title} {stripped}".strip()

    return entries


def _parse_toc_b(text: str) -> list[TocEntry]:
    """Parse the numbered ΑΠΟΦΑΣΕΙΣ list of a Τεύχος Β issue."""
    squashed = _squash(text)
    if not _TOC_ANCHOR_B.search(squashed):
        return []

    # Work on the slice between ΠΕΡΙΕΧΟΜΕΝΑ and the second ΑΠΟΦΑΣΕΙΣ heading, which
    # is where the acts themselves begin.
    start = text.find("ΑΠΟΦΑΣΕΙΣ")
    if start < 0:
        return []
    body = text.find("ΑΠΟΦΑΣΕΙΣ", start + 1)
    toc_text = text[start + len("ΑΠΟΦΑΣΕΙΣ") : body if body > 0 else None]

    entries: list[TocEntry] = []
    pending: TocEntry | None = None
    for line in toc_text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        item = _TOC_ITEM_B.match(line)
        if item:
            pending = TocEntry(number=int(item.group(1)), title=item.group(2).strip())
            entries.append(pending)
        elif pending is not None:
            pending.title = f"{pending.title} {stripped}".strip()

    # Trailing page numbers ("… Signature". 56349") are an artefact of the layout.
    for entry in entries:
        entry.title = re.sub(r"\s*\d{4,6}\s*$", "", entry.title).strip()
    return entries


def is_garbled(text: str) -> bool:
    """True when text came out of an undecodable font encoding.

    Some issues embed subset fonts with no ToUnicode map — the 76-page strategy
    annex of Π.Υ.Σ. 22/2026, for instance, extracts as ``D\\}ZR^l}N]\\aRXRg}``
    under both pypdf and poppler. It is not recoverable, so it must be detected
    and dropped rather than summarised.

    Two signals together, because either alone has false positives: almost no
    Greek letters, and a high rate of the delimiter characters that these
    encodings map spaces and punctuation onto.
    """
    if len(text) < 200:
        return False
    letters = [c for c in text if c.isalpha()]
    if not letters:
        return False
    greek = sum(1 for c in letters if "Ͱ" <= c <= "Ͽ" or "ἀ" <= c <= "῿")
    delimiters = sum(text.count(c) for c in "}~\\")
    return greek / len(letters) < 0.5 and delimiters / len(text) > 0.02


def _first_line(text: str, limit: int = 200) -> str:
    """First non-empty line, used when a heading carries no inline title."""
    for line in text.splitlines():
        if line.strip():
            return line.strip()[:limit]
    return ""


def _parse_sections_a(body_text: str) -> list[Section]:
    matches = list(_ARTICLE.finditer(body_text))
    sections = []
    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(body_text)
        text = body_text[match.end() : end].strip()
        # In the body the article title usually sits on the line below the heading.
        title = (match.group(2) or "").strip() or _first_line(text)
        sections.append(Section(number=int(match.group(1)), title=title, text=text))
    return sections


def _chunk(text: str, chunk_chars: int = CHUNK_CHARS) -> list[Section]:
    """Split an unstructured document into addressable blocks.

    Used for acts with no ``Άρθρο`` headings — an 80-page national strategy
    approved by a cabinet act, say. Each block is titled with its opening words so
    triage still has something to choose between.
    """
    if not text.strip():
        return []

    blocks: list[str] = []
    current: list[str] = []
    size = 0
    for paragraph in re.split(r"\n\s*\n", text):
        paragraph = paragraph.strip()
        if not paragraph:
            continue
        if size and size + len(paragraph) > chunk_chars:
            blocks.append("\n\n".join(current))
            current, size = [], 0
        current.append(paragraph)
        size += len(paragraph)
    if current:
        blocks.append("\n\n".join(current))

    return [
        Section(
            number=index,
            title=re.sub(r"\s+", " ", block[:CHUNK_PREVIEW]).strip() + "…",
            text=block,
        )
        for index, block in enumerate(blocks, 1)
    ]


def _parse_sections_b(text: str, toc: list[TocEntry]) -> list[Section]:
    """Split a Τεύχος Β issue into its individual acts.

    Each act starts at an ``Αριθμ. <protocol>`` heading; the trailing ``(n)`` marker
    ties it back to its ΠΕΡΙΕΧΟΜΕΝΑ entry when present.
    """
    start = text.find("ΑΠΟΦΑΣΕΙΣ")
    body_start = text.find("ΑΠΟΦΑΣΕΙΣ", start + 1) if start >= 0 else -1
    body = text[body_start:] if body_start > 0 else text

    matches = list(_ACT_HEADING_B.finditer(body))
    titles = {entry.number: entry.title for entry in toc}
    sections = []
    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(body)
        number = int(match.group(2))
        text = body[match.end() : end].strip()
        sections.append(
            Section(
                number=number,
                title=titles.get(number) or _first_line(text),
                text=text,
            )
        )
    return sections


def parse(
    pdf_path: str,
    *,
    fek_id: str,
    label: str,
    issue_group: int,
    pdf_url: str,
) -> FekDoc:
    """Parse a downloaded gazette PDF into an addressable document."""
    text, page_count = extract_text(pdf_path)
    return parse_text(
        text,
        page_count=page_count,
        fek_id=fek_id,
        label=label,
        issue_group=issue_group,
        pdf_url=pdf_url,
    )


def parse_text(
    text: str,
    *,
    page_count: int,
    fek_id: str,
    label: str,
    issue_group: int,
    pdf_url: str,
) -> FekDoc:
    """Parse already-extracted gazette text. Separated from PDF reading so the
    structural logic can be tested without shipping large binaries."""
    law_type, law_number, law_title = _parse_law_heading(text[:8000])

    if issue_group == 2:
        toc = _parse_toc_b(text)
        sections = _parse_sections_b(text, toc)
        if not law_title and toc:
            law_title = toc[0].title
    else:
        split = _split_toc_body(text)
        has_toc = bool(_TOC_ANCHOR_A.search(_squash(text[:split or 8000])))
        if split and has_toc:
            toc = _parse_toc_a(text[:split])
            sections = _parse_sections_a(text[split:])
        else:
            # Short acts (the median Τεύχος Α is 3 pages) carry no table of contents.
            toc = []
            sections = _parse_sections_a(text)
            if not sections:
                # No articles either — a free-form document such as a national
                # strategy approved by a cabinet act. Chunk it so triage still has
                # a choice to make instead of one 190k-character blob.
                sections = _chunk(text)
                log.info("%s has no article structure, chunked into %d blocks", label, len(sections))

    # Fall back to the table of contents when article headings could not be split out.
    if not sections and toc:
        sections = [Section(number=e.number, title=e.title, text="") for e in toc]

    # Drop anything that came out of an undecodable font encoding — feeding it to
    # the model would produce a confident summary of nothing.
    readable = [s for s in sections if not is_garbled(s.text)]
    if len(readable) != len(sections):
        dropped = len(sections) - len(readable)
        log.warning("%s: dropped %d unreadable section(s) of %d", label, dropped, len(sections))
        kept = {s.number for s in readable}
        sections = readable
        toc = [e for e in toc if e.number in kept] if toc else toc

    # Short acts carry no table of contents; derive one from the sections so that
    # triage sees the same shape regardless of document size.
    if not toc and sections:
        toc = [TocEntry(number=s.number, title=s.title) for s in sections]

    log.info(
        "parsed %s: %d pages, %d chars, %d toc entries, %d sections",
        label,
        page_count,
        len(text),
        len(toc),
        len(sections),
    )
    return FekDoc(
        fek_id=fek_id,
        label=label,
        issue_group=issue_group,
        pdf_url=pdf_url,
        page_count=page_count,
        law_type=law_type,
        law_number=law_number,
        law_title=law_title,
        toc=toc,
        sections=sections,
        full_text=text,
    )
