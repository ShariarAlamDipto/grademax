"""
Independently re-check the finished yearwise books: right papers, right years,
right order, and no worked-solutions document standing in for an exam.

DELIBERATELY STANDS ALONE. It imports nothing from `lib/yearwise_*` and reads
no audit JSON, no print index, no archive. It opens the finished, watermarked
PDFs that actually ship and checks them against Edexcel's own printing and
against a list of sittings typed out from Pearson's catalogue. A check that
shares a library with the thing it checks can only confirm that the library is
self-consistent -- this project has already been burned by five probes that
agreed with a broken parser.

WHAT IT ASKS OF EACH BOOK

  1. EVERY SITTING IS PRESENT, AND NOTHING ELSE IS. Against the list below,
     which is not derived from our archive.

  2. THE ORDER IS CHRONOLOGICAL. A book of past papers that jumps from June
     2021 back to January 2021 is wrong even if every paper in it is right.

  3. EACH PAPER IS THE SESSION THE BOOK SAYS IT IS. The running header is the
     book's CLAIM; the evidence is the board's own printing underneath it --
     the item code repeated on every page, and the exam date on the cover.
     Claim and evidence have to agree.

  4. NO PAPER IS A WORKED-SOLUTIONS DOCUMENT. This is the failure that started
     the whole M1 effort: PMT "Model Answer" files filed under `_QP` names.
     They are scans of handwriting, so they carry no item code and almost no
     text. A real paper prints `*P54879A0120*` on every single page.

  5. NO TWO PAPERS IN A BOOK ARE THE SAME EXAM. Every wrong slot found in this
     project was a duplicate of a neighbouring session. Compared on the papers'
     own question text, so a duplicate cannot hide behind a different label.

  6. EVERY PAPER IS A COMPLETE 75-MARK EXAM, by its own printed mark fences.

  7. THE PRINTED CONTENTS LANDS. Every row is read off the page as a reader
     reads it, and the page it names is opened: that session has to start
     there. Since the per-question map was dropped, these rows are the book's
     only navigation.

  8. THE MARK SCHEME VOLUME MATCHES. Same sittings, same order, and each scheme
     identified by the Pearson publication code it prints rather than by where
     the book filed it.

    python scripts/verify_yearwise_books.py
"""

from __future__ import annotations

import math
import re
import sys
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

import fitz

ROOT = Path(__file__).resolve().parents[1]

# The sittings each unit actually had, typed from Pearson's published
# catalogue, NOT read back out of our own archive or audit files. The summer
# 2020 series was cancelled worldwide; its paper was sat that October, so it
# appears once, as October.
SITTINGS = {
    "M1": [(y, s) for y in range(2017, 2024) for s in ("Jan", "Jun", "Oct")],
    "S1": [(y, s) for y in range(2019, 2024) for s in ("Jan", "Jun", "Oct")],
    "P4": [(2020, "Oct")] + [(y, s) for y in (2021, 2022, 2023)
                             for s in ("Jan", "Jun", "Oct")],
}
for unit in ("M1", "S1"):
    SITTINGS[unit].remove((2020, "Jun"))

BOOKS = {
    "M1": ("Mechanics M1", "WME01", "m1"),
    "S1": ("Statistics S1", "WST01", "s1"),
    "P4": ("Pure Mathematics P4", "WMA14", "p4"),
}


def volume(slug: str, token: str, kind: str) -> Path:
    tail = "" if kind == "questions" else "_MarkSchemes"
    return (ROOT / "data" / "workbook" / f"{slug}_yearwise" / "final"
            / f"GradeMax_{token}_Yearwise_Workbook{tail}.pdf")


# What a mark scheme prints instead of an item code: the Pearson publication
# code, unit_paper_session_kind, on its last page. Eight digits are a
# PUBLICATION date, not a session -- summer publishes in August, January in
# March, the autumn series the following January or February.
PUB_CODE = re.compile(
    r"Publications?\s*Code\s*[:\s]\s*([A-Z0-9]+)_(\d{2})_"
    r"(?:(?:r?ms|MS)_)?(\d{8}|\d{4})", re.I)


def pub_session(when: str) -> str:
    if len(when) == 4:
        return when
    year, month = int(when[0:4]), int(when[4:6])
    if month <= 2:
        return f"{(year - 1) % 100:02d}10"
    if month <= 4:
        return f"{year % 100:02d}01"
    if month <= 9:
        return f"{year % 100:02d}06"
    return f"{year % 100:02d}10"

# The running header the book prints, read back off the finished page.
HEADER_SESSION = re.compile(
    r"^(January|May/June|October/November)\s+(20\d\d)$", re.M)
# The separator is written as U+00B7 MIDDLE DOT and comes back out of the text
# layer as U+2022 BULLET -- PyMuPDF's base-14 Helvetica remaps it, the same
# substitution class that turns an en dash into a middot on the page. Accept
# either, or this reads 43 of 44 papers as absent from books that are correct.
HEADER_REF = re.compile(r"(W[A-Z]{2}\d\d)/0?1\s*[·•]\s*(P\d{5}R?A)")
# Edexcel's item code, printed on every page of a real question paper.
ITEM_CODE = re.compile(r"\*?(P\d{5}R?A)(\d{2})(\d{2})\*?")
EXAM_DATE = re.compile(
    r"(?:Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)\s+"
    r"(\d{1,2})\s+(January|February|March|April|May|June|July|August|"
    r"September|October|November|December)\s+(20\d\d)")
TOTAL = re.compile(
    r"\(\s*Total\s+(?:for\s+Question\s+\d{1,2}\s+(?:is|=)\s+)?(\d{1,3})\s+marks?\s*\)",
    re.I)
WORD = re.compile(r"[A-Za-z]{4,}")

SEASON_OF_HEADER = {"January": "Jan", "May/June": "Jun", "October/November": "Oct"}
MONTH_SEASON = {
    "January": "Jan", "February": "Jan",
    "May": "Jun", "June": "Jun",
    "October": "Oct", "November": "Oct",
}
# A real paper's pages are dense with print. A scan of handwriting extracts
# almost nothing; this is far below anything a genuine page reaches.
MIN_CHARS_PER_PAGE = 200
PAPER_TOTAL_MARKS = 75
# See check 5 for how this was calibrated, and against what.
DUPLICATE_SIMILARITY = 0.95


def rarity(docs: list[set]) -> dict[str, float]:
    """How rare each word is across the papers, so common ones count for little."""
    n = len(docs)
    seen: Counter = Counter()
    for d in docs:
        seen.update(d)
    return {w: math.log(n / c) for w, c in seen.items()}


def affinity(a: set, b: set, idf: dict[str, float]) -> float:
    shared = sum(idf.get(w, 0.0) for w in a & b)
    na = math.sqrt(sum(idf.get(w, 0.0) for w in a if w in idf))
    nb = math.sqrt(sum(idf.get(w, 0.0) for w in b if w in idf))
    return shared / (na * nb) if na and nb else 0.0


@dataclass
class Found:
    """One paper as the finished book presents it."""
    year: int
    season: str
    unit_code: str
    reference: str              # the item code the running header claims
    first_page: int             # printed page number in the book
    pages: list[int] = field(default_factory=list)
    codes: Counter = field(default_factory=Counter)
    coded_pages: int = 0
    chars: int = 0
    exam_date: str | None = None
    exam_season: str | None = None
    exam_year: int | None = None
    marks: int = 0
    tariffs: int = 0
    words: set = field(default_factory=set, repr=False)

    @property
    def label(self) -> str:
        return f"{self.year} {self.season}"


def scan(path: Path) -> list[Found]:
    """Walk the finished book and group its sheets into papers."""
    doc = fitz.open(path)
    papers: list[Found] = []
    for index in range(doc.page_count):
        text = doc[index].get_text()
        flat = re.sub(r"[ \t]+", " ", text)
        session = HEADER_SESSION.search(flat)
        ref = HEADER_REF.search(re.sub(r"\s+", " ", text))
        if not session or not ref:
            continue                      # front matter carries no header
        year, season = int(session.group(2)), SEASON_OF_HEADER[session.group(1)]
        unit_code, reference = ref.group(1), ref.group(2)

        if (not papers or papers[-1].year != year or papers[-1].season != season
                or papers[-1].reference != reference):
            papers.append(Found(year=year, season=season, unit_code=unit_code,
                                reference=reference, first_page=index + 1))
        paper = papers[-1]
        paper.pages.append(index + 1)
        paper.chars += len(text.strip())

        codes = {m.group(1) for m in ITEM_CODE.finditer(text)}
        if codes:
            paper.coded_pages += 1
            paper.codes.update(codes)

        if paper.exam_date is None:
            when = EXAM_DATE.search(re.sub(r"\s+", " ", text))
            if when:
                paper.exam_date = when.group(0)
                paper.exam_season = MONTH_SEASON.get(when.group(2))
                paper.exam_year = int(when.group(3))

        for m in TOTAL.finditer(re.sub(r"\s+", " ", text)):
            paper.marks += int(m.group(1))
            paper.tariffs += 1
        paper.words.update(WORD.findall(text.lower()))
    doc.close()
    return papers


SEASON_MM = {"Jan": "01", "Jun": "06", "Oct": "10"}
# Pearson's own transposition: `2021` where January 2021 should read 2101, on
# two different units. The covers and the schemes both say January 2021.
PUB_TYPOS = {"WME01_01_2021": "2101", "WMA14_01_2021": "2101"}


def check_mark_schemes(unit: str, name: str, code: str, path: Path,
                       question_sessions: list[tuple[int, str]]) -> list[str]:
    """
    The mark scheme volume, checked the same way and against the same list.

    A scheme carries no item code -- it identifies itself by its publication
    code, which names the unit AND the session, so it is the stronger evidence.
    Landscape scheme pages carry no running header (a header printed sideways
    helps nobody), so a headerless page belongs to the scheme before it.
    """
    problems: list[str] = []
    if not path.exists():
        return [f"{name}: mark scheme volume not found at {path}"]

    doc = fitz.open(path)
    found: list[tuple[int, str]] = []
    codes: dict[tuple[int, str], set] = {}
    pages: Counter = Counter()
    current = None
    for index in range(doc.page_count):
        text = doc[index].get_text()
        session = HEADER_SESSION.search(re.sub(r"[ 	]+", " ", text))
        if session:
            key = (int(session.group(2)), SEASON_OF_HEADER[session.group(1)])
            if key != current:
                found.append(key)
                current = key
        if current is None:
            continue                      # front matter
        pages[current] += 1
        pub = PUB_CODE.search(re.sub(r"\s+", " ", text))
        if pub:
            codes.setdefault(current, set()).add(
                f"{pub.group(1)}_{pub.group(2)}_{pub.group(3)}")
    doc.close()

    print(f"{name} ({code})  --  {path.name}")
    print(f"  {'in the book':16} {'pages':>5}  publication code")
    for key in found:
        seen = sorted(codes.get(key, {"(none printed)"}))
        print(f"  {key[0]} {key[1]:11} {pages[key]:5}  {', '.join(seen)}")

    for sitting in question_sessions:
        if sitting not in found:
            problems.append(f"mark scheme for {sitting[0]} {sitting[1]} is missing")
    for sitting in found:
        if sitting not in question_sessions:
            problems.append(f"mark scheme {sitting[0]} {sitting[1]} has no "
                            "question paper in the other volume")
    for sitting, n in Counter(found).items():
        if n > 1:
            problems.append(f"mark scheme {sitting[0]} {sitting[1]} appears {n} times")

    order = {"Jan": 0, "Jun": 1, "Oct": 2}
    keys = [(y, order[s]) for y, s in found]
    if keys != sorted(keys):
        problems.append("the mark schemes are not in date order: "
                        + str([f"{y} {s}" for y, s in found]))

    for key in found:
        printed = codes.get(key)
        if not printed:
            problems.append(f"{key[0]} {key[1]}: no publication code printed")
            continue
        want = f"{key[0] % 100:02d}{SEASON_MM[key[1]]}"
        ok = False
        for c in printed:
            unit_part, _, when = c.split("_", 2)
            said = PUB_TYPOS.get(c, pub_session(when))
            if unit_part.upper().startswith(code) and said == want:
                ok = True
        if not ok:
            problems.append(f"{key[0]} {key[1]}: publication code {sorted(printed)} "
                            f"does not name {code} {want}")
    print(f"  {len(found)} mark schemes, matching the question volume's "
          f"{len(question_sessions)} papers")
    return problems


def contents_rows(doc: fitz.Document) -> list[tuple[int, str, int]]:
    """
    The contents as a reader reads it: (year, season, printed page) per row.

    Read in VISUAL order, top to bottom, because a row's year comes from the
    heading above it and nothing in the row itself says which year it is. Doing
    the grouping first and the year afterwards makes every row inherit the last
    heading on the page -- which reported all twenty M1 sittings as 2023.
    """
    rows: list[tuple[int, str, int]] = []
    year: int | None = None
    for index in range(doc.page_count):
        page = doc[index]
        if "Contents" not in page.get_text():
            continue
        spans = []
        for block in page.get_text("dict")["blocks"]:
            if block.get("type") != 0:
                continue
            for line in block["lines"]:
                for span in line["spans"]:
                    if span["text"].strip():
                        spans.append((span["bbox"][1], span["bbox"][0],
                                      span["text"].strip()))
        # Group into rows first, then walk the rows in order so the year
        # heading applies to what follows it.
        bands: dict[int, list[tuple[float, str]]] = {}
        for top, left, text in spans:
            bands.setdefault(round(top / 4), []).append((left, text))
        for key in sorted(bands):
            cells = sorted(bands[key])
            heading = next((t for x, t in cells
                            if x < 40 and re.fullmatch(r"20\d\d", t)), None)
            if heading:
                year = int(heading)
                continue
            label = next((t for x, t in cells
                          if 45 < x < 120 and t in SEASON_OF_HEADER), None)
            number = next((t for x, t in cells
                           if x > 500 and re.fullmatch(r"\d{1,4}", t)), None)
            if label and number and year is not None:
                rows.append((year, SEASON_OF_HEADER[label], int(number)))
    return rows


def opens_on(doc: fitz.Document, printed: int) -> tuple[int, str] | None:
    """Which session the sheet bearing this printed page number belongs to."""
    # The printed numbering starts at the title page, which is the file's
    # SECOND sheet because the front cover comes first: printed N is page N+1,
    # index N.
    if not 0 <= printed < doc.page_count:
        return None
    found = HEADER_SESSION.search(re.sub(r"[ 	]+", " ", doc[printed].get_text()))
    if not found:
        return None
    return int(found.group(2)), SEASON_OF_HEADER[found.group(1)]


def check_printed_contents(name: str, path: Path,
                           sessions: list[tuple[int, str]]) -> list[str]:
    """
    Open every page the CONTENTS names and confirm that session starts there.

    The workbook audit already checks the page numbers the builder recorded in
    `print_index.json`. That is the builder's own note to itself. This reads the
    contents off the printed page and then turns to the page it points at.
    Since the per-question map was dropped, these rows are the book's only
    navigation, so nothing else stands between a reader and a wrong number.
    """
    problems: list[str] = []
    doc = fitz.open(path)
    rows = contents_rows(doc)

    print(f"{name}  --  contents rows read off the printed page")
    for year, season, printed in rows:
        landed = opens_on(doc, printed)
        ok = landed == (year, season)
        shown = f"{landed[0]} {landed[1]}" if landed else "no running header"
        print(f"  {year} {season:4} -> printed page {printed:4}  "
              f"opens on {shown}{'' if ok else '   <- WRONG'}")
        if not ok:
            problems.append(f"contents sends {year} {season} to printed page "
                            f"{printed}, which opens on {shown}")

    listed = [(y, s) for y, s, _ in rows]
    for sitting in sessions:
        if sitting not in listed:
            problems.append(f"{sitting[0]} {sitting[1]} has no row in the "
                            "printed contents")
    for sitting in listed:
        if sitting not in sessions:
            problems.append(f"the printed contents lists {sitting[0]} "
                            f"{sitting[1]}, which is not in the book")
    for sitting, n in Counter(listed).items():
        if n > 1:
            problems.append(f"the printed contents lists {sitting[0]} "
                            f"{sitting[1]} {n} times")

    pages = [p for _, _, p in rows]
    if pages != sorted(pages):
        problems.append(f"the contents page numbers do not increase: {pages}")

    print(f"  {len(rows)} rows, {len(sessions)} sessions expected")
    doc.close()
    return problems


def check(unit: str, name: str, code: str, path: Path) -> list[str]:
    problems: list[str] = []
    if not path.exists():
        return [f"{name}: book not found at {path}"]

    papers = scan(path)
    expected = SITTINGS[unit]

    print(f"{name} ({code})  --  {path.name}")
    print(f"  {'in the book':16} {'item code':10} {'pages':>5} {'marks':>5} "
          f"{'Q':>2}  cover date")
    for p in papers:
        date = p.exam_date or "(set in an image)"
        print(f"  {p.label:16} {p.reference:10} {len(p.pages):5} {p.marks:5} "
              f"{p.tariffs:2}  {date}")

    # 1. every sitting present, nothing extra
    got = [(p.year, p.season) for p in papers]
    for sitting in expected:
        if sitting not in got:
            problems.append(f"{sitting[0]} {sitting[1]} is missing from the book")
    for sitting in got:
        if sitting not in expected:
            problems.append(f"{sitting[0]} {sitting[1]} is in the book but was "
                            "never a sitting of this unit")
    for sitting, n in Counter(got).items():
        if n > 1:
            problems.append(f"{sitting[0]} {sitting[1]} appears {n} times")

    # 2. chronological order
    order = {"Jan": 0, "Jun": 1, "Oct": 2}
    keys = [(y, order[s]) for y, s in got]
    if keys != sorted(keys):
        out = [f"{y} {s}" for y, s in got]
        problems.append(f"the papers are not in date order: {out}")

    for p in papers:
        # 3. the book's claim agrees with the board's printing
        if p.unit_code != code:
            problems.append(f"{p.label}: header says unit {p.unit_code}, not {code}")
        printed = set(p.codes)
        if printed and printed != {p.reference}:
            problems.append(f"{p.label}: header claims {p.reference} but the pages "
                            f"print {sorted(printed)}")
        if p.exam_year is not None:
            if (p.exam_year, p.exam_season) != (p.year, p.season):
                # The one legitimate case: the cancelled summer 2020 paper,
                # printed for June and sat that October.
                covid = (p.year, p.season) == (2020, "Oct") and \
                        (p.exam_year, p.exam_season) == (2020, "Jun")
                if covid:
                    print(f"  . {p.label}: cover reads {p.exam_date} -- the "
                          "cancelled summer paper, sat in October")
                else:
                    problems.append(
                        f"{p.label}: cover reads {p.exam_date}, which is "
                        f"{p.exam_year} {p.exam_season}")

        # 4. a real question paper, not a worked-solutions scan
        if p.coded_pages < len(p.pages):
            problems.append(
                f"{p.label}: item code on only {p.coded_pages}/{len(p.pages)} "
                "pages -- is this a worked-solutions document?")
        per_page = p.chars // max(1, len(p.pages))
        if per_page < MIN_CHARS_PER_PAGE:
            problems.append(
                f"{p.label}: only {per_page} characters a page -- scanned handwriting?")

        # 6. a complete exam
        if p.marks != PAPER_TOTAL_MARKS:
            problems.append(f"{p.label}: mark fences sum to {p.marks}, not "
                            f"{PAPER_TOTAL_MARKS}")

    # 5a. an item code identifies one exam, so it may not appear twice
    for code, n in Counter(p.reference for p in papers).items():
        if n > 1:
            where = ", ".join(p.label for p in papers if p.reference == code)
            problems.append(f"item code {code} appears on {n} papers: {where}")

    # 5b. no two papers are the same exam
    #
    # Plain word overlap is worthless here and saying so is the point: two
    # genuinely different M1 papers share 60-74% of their four-letter words,
    # because every mechanics paper says particle, velocity, horizontal, find,
    # constant, figure, shows. A flat threshold flags the whole book.
    #
    # Weighting each word by how rare it is across this unit's papers separates
    # the two cases completely. Calibrated against ground truth -- the three
    # duplicate papers this project actually caught, still in
    # data/quarantine/yearwise_wrong_session -- scored against the paper each
    # really was: all three land at 1.000, while genuinely distinct pairs
    # average 0.21 (S1) to 0.37 (P4). 0.95 sits in the empty space between.
    idf = rarity([p.words for p in papers])
    for i, a in enumerate(papers):
        for b in papers[i + 1:]:
            score = affinity(a.words, b.words, idf)
            if score > DUPLICATE_SIMILARITY:
                problems.append(
                    f"{a.label} and {b.label} are {score:.3f} alike on their "
                    f"rarest wording -- the same exam twice? "
                    f"(item codes {a.reference}, {b.reference})")

    span = f"{papers[0].label} to {papers[-1].label}" if papers else "empty"
    print(f"  {len(papers)} papers, {span}; {len(expected)} sittings expected")
    return problems


def main() -> int:
    problems: list[str] = []
    for unit, (name, code, slug) in BOOKS.items():
        qp = volume(slug, unit, "questions")
        problems += [f"[{unit}] {p}" for p in check(unit, name, code, qp)]
        sessions = [(p.year, p.season) for p in scan(qp)] if qp.exists() else []
        print()
        problems += [f"[{unit} TOC] {p}" for p in
                     check_printed_contents(name, qp, sessions)]
        print()
        problems += [f"[{unit} MS] {p}" for p in
                     check_mark_schemes(unit, name, code,
                                        volume(slug, unit, "markschemes"), sessions)]
        print()

    if problems:
        print(f"{len(problems)} problems:")
        for p in problems:
            print(f"  ! {p}")
        return 1
    print("both volumes of all three units: every sitting present, in order, each "
          "paper the exam it claims to be, none of them worked solutions, no "
          "duplicates, every mark scheme matched to its paper")
    return 0


if __name__ == "__main__":
    sys.exit(main())
