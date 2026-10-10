"""
Audit the papers a yearwise workbook is built from, for any Edexcel unit.

Extracted from the M1 audit once a second and third unit needed the same five
checks. The per-unit entry points stay separate -- `audit_m1_yearwise_sources.py`,
`audit_s1_...`, `audit_p4_...` -- and each hands its own `Subject` here.

THE FIVE CHECKS

  1. GENUINE QUESTION PAPER, not a worked-solutions document filed under a `_QP`
     name. A Model Answer is a scan of handwriting: the board's item code,
     printed on every page of a real paper, is absent and the text layer is
     nearly empty. NOTE the code reads `P51413RA0228` on a reprinted paper -- a
     bare `P\\d{5}A` pattern condemns real papers as forgeries.

  2. GRADEMAX STAMPED on every page, with no third-party branding left behind.

  3. THE MARK SCHEME IS THE SESSION IT CLAIMS. Edexcel prints a publication code
     -- `WME01_01_1806_MS`, unit, paper, YYMM, kind -- on the last page. It is
     the only session identifier in either document that cannot be wrong, and it
     is what catches a slot holding the legacy GCE unit's mark scheme instead of
     the international one.

  4. THE QUESTION PAPER IS THE SESSION IT CLAIMS, from the exam date on its
     cover. Two exceptions are real and must not be "fixed": a cancelled series
     whose paper was sat in a later one, and the covers from 2021 on that set
     the date in an image, where an absent date is evidence of nothing.

  5. THE PAIR BELONGS TOGETHER. A cover cannot catch a paper that is a copy of
     another session's, because the copy's cover is honest about being that
     other session. Each paper is scored against every mark scheme on the
     numbers they share, weighted by how rare each number is across the mark
     schemes, and the one it matches best must be its own.

     Raw overlap is useless -- unweighted, `9.8`, `75` and the page numbers put
     every session within 0.02 of every other. Weighted, a right pair scores
     0.25-0.46 and a wrong one 0.18.

     THE SCORE IS EVIDENCE, NOT A VERDICT. On P4 it flagged January 2021, which
     turned out to be byte-identical to Pearson's own copy: both 2021 P4 papers
     open with a binomial expansion, which is enough shared vocabulary to beat
     the margin. Anything this flags is hand-checked against the exam date or
     the publisher's copy before the file is touched.

WHAT A SUBJECT HAS TO DECLARE

The sittings that EXIST, rather than a year range. P4 has no 2019 papers at all
-- WMA14's first sitting is October 2020, confirmed against Pearson's
catalogue, Paperlords and PMT -- so iterating a range and calling the rest
"missing" would report nine holes that are not holes.
"""

from __future__ import annotations

import math
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path

import fitz

ROOT = Path(__file__).resolve().parents[2]

# `R` = a reprinted paper; leaving it out condemns real papers as Model Answers.
ITEM_CODE = re.compile(r"\*?(P\d{5}R?A)\d{4}\*?")
# \d{8} first: the alternation is ordered, and `\d{4}` would otherwise swallow
# the year out of a publication date and call 20240118 "2024".
PUB_CODE = re.compile(
    r"Publications?\s*Code\s*[:\s]\s*([A-Z0-9]+)_(\d{2})_"
    r"(?:(?:r?ms|MS)_)?(\d{8}|\d{4})(?:_(?:MS|ms))?", re.I)
COVER_DATE = re.compile(
    r"\b(January|February|March|April|May|June|July|August|September|October|"
    r"November|December)\s+(20\d\d)\b")
THIRD_PARTY = re.compile(
    r"physicsandmathstutor|pmt\.education|pmt\.physics|paperlords|automatepapers", re.I)
GRADEMAX = re.compile(r"grademax", re.I)
NUMERIC = re.compile(r"\d+\.\d+|\b\d{1,4}\b")

SEASONS = ("Jan", "May-Jun", "Oct-Nov")
SEASON_MM = {"Jan": "01", "May-Jun": "06", "Oct-Nov": "10"}
SEASON_MONTHS = {
    "Jan": {"January", "February"},
    "May-Jun": {"May", "June"},
    "Oct-Nov": {"October", "November"},
}

# A worked-solutions document's text layer holds our own stamp and little else.
MIN_TEXT_CHARS_PER_PAGE = 300
# How much better a foreign mark scheme must score before the pair is doubted.
MISMATCH_MARGIN = 0.05


@dataclass(frozen=True)
class Archive:
    """One place a unit's papers may be filed, and how they are named there."""
    label: str
    root: Path
    pattern: str            # formatted with year, season, kind

    def locate(self, year: int, season: str, kind: str) -> Path:
        return (self.root / str(year) / season /
                self.pattern.format(year=year, season=season, kind=kind))


@dataclass(frozen=True)
class Subject:
    unit: str                                   # WME01
    name: str                                   # Mechanics M1
    paper_code: re.Pattern                      # what the cover must say
    archives: tuple[Archive, ...]
    sittings: tuple[tuple[int, str], ...]       # the exams that were actually sat
    # (year, season) slots the archive fills but no exam happened in.
    cancelled: frozenset = frozenset()
    # Item codes that legitimately serve two slots, because a cancelled series'
    # paper was sat in a later one.
    reissued: frozenset = frozenset()
    # Pearson's own slips in the publication code, code -> the YYMM it meant.
    pub_typos: dict = field(default_factory=dict)
    # Slots whose pairing was doubted by check 5 and then settled by hand,
    # mapped to the evidence that settled it. The mismatch is reported as a
    # note carrying that evidence rather than suppressed, so a future reader
    # can see what was checked instead of finding a silent exception.
    settled: dict = field(default_factory=dict)


@dataclass
class Paper:
    key: str
    year: int
    season: str
    kind: str
    source: str
    path: str
    pages: int
    item_code: str | None = None
    item_code_pages: int = 0
    paper_code: str | None = None
    pub_code: str | None = None
    pub_session: str | None = None
    cover_month: str | None = None
    cover_year: int | None = None
    grademax_pages: int = 0
    third_party_pages: int = 0
    chars_per_page: int = 0
    best_ms: str | None = None
    best_ms_score: float = 0.0
    own_ms_score: float = 0.0
    problems: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
    numbers: set = field(default_factory=set, repr=False, compare=False)

    @property
    def verdict(self) -> str:
        return "FAIL" if self.problems else ("OK" if not self.notes else "OK*")


def session_of(when: str) -> str:
    """
    Reduce a publication code's date part to the YYMM of the session it covers.

    Four digits ARE the session (`WME01_01_1806_MS` is June 2018). Eight are the
    PUBLICATION date (`WME01_01_rms_20240118`), which is not the same thing and
    for the autumn series is not even the same year -- Pearson releases a
    November mark scheme the following January. Read literally, that code makes
    the October 2023 paper look like January 2024. The release windows are
    tight and identical across subjects: summer lands in August, January in
    March, and the autumn series in the January or February after it.
    """
    if len(when) == 4:
        return when
    year, month = int(when[0:4]), int(when[4:6])
    if month <= 2:                      # the autumn series, published late
        return f"{(year - 1) % 100:02d}10"
    if month <= 4:
        return f"{year % 100:02d}01"
    if month <= 9:
        return f"{year % 100:02d}06"
    return f"{year % 100:02d}10"


def read(subject: Subject, year: int, season: str, kind: str,
         source: str, path: Path) -> Paper:
    doc = fitz.open(path)
    texts = [doc[i].get_text() for i in range(doc.page_count)]
    doc.close()
    blob = "\n".join(texts)

    codes = {m.group(1) for m in ITEM_CODE.finditer(blob)}
    pc = subject.paper_code.search(blob)
    cm = COVER_DATE.search("\n".join(texts[:2]))

    pub_code = pub_session = None
    pub = PUB_CODE.search(re.sub(r"\s+", " ", blob))
    if pub:
        pub_code = f"{pub.group(1)}_{pub.group(2)}_{pub.group(3)}"
        pub_session = session_of(pub.group(3))

    paper = Paper(
        key=f"{year}_{season}_{kind}", year=year, season=season, kind=kind,
        source=source, path=str(path.relative_to(ROOT)).replace("\\", "/"),
        pages=len(texts),
        item_code=sorted(codes)[0] if codes else None,
        item_code_pages=sum(1 for t in texts if ITEM_CODE.search(t)),
        paper_code=pc.group(0).replace(" ", "") if pc else None,
        pub_code=pub_code, pub_session=pub_session,
        cover_month=cm.group(1) if cm else None,
        cover_year=int(cm.group(2)) if cm else None,
        grademax_pages=sum(1 for t in texts if GRADEMAX.search(t)),
        third_party_pages=sum(1 for t in texts if THIRD_PARTY.search(t)),
        chars_per_page=len(blob) // max(1, len(texts)),
    )
    # A mark scheme's front matter is boilerplate every session shares, so the
    # fingerprint is taken from the schemes themselves.
    body = "\n".join(texts[4:]) if kind == "MS" else blob
    paper.numbers = set(NUMERIC.findall(body))
    return paper


def pub_matches(subject: Subject, p: Paper) -> bool:
    """Does the Pearson publication code name this slot's unit and session?"""
    if not p.pub_session:
        return False
    session = subject.pub_typos.get(p.pub_code, p.pub_session)
    return (p.pub_code.startswith(subject.unit)
            and session == f"{p.year % 100:02d}{SEASON_MM[p.season]}")


def rarity(schemes: list[Paper]) -> dict[str, float]:
    n = len(schemes)
    df: dict[str, int] = {}
    for ms in schemes:
        for t in ms.numbers:
            df[t] = df.get(t, 0) + 1
    return {t: math.log(n / d) for t, d in df.items()}


def affinity(qp: Paper, ms: Paper, idf: dict[str, float]) -> float:
    shared = sum(idf.get(t, 0.0) for t in qp.numbers & ms.numbers)
    qn = math.sqrt(sum(idf.get(t, 0.0) for t in qp.numbers if t in idf))
    mn = math.sqrt(sum(idf.get(t, 0.0) for t in ms.numbers))
    return shared / (qn * mn) if qn and mn else 0.0


def audit(subject: Subject) -> tuple[list[Paper], list[Paper]]:
    """Returns the chosen paper for every slot, and the copies not chosen."""
    chosen: dict[str, Paper] = {}
    rejected: list[Paper] = []

    for year, season in subject.sittings:
        for kind in ("QP", "MS"):
            found = []
            for archive in subject.archives:
                path = archive.locate(year, season, kind)
                if path.exists():
                    found.append(read(subject, year, season, kind, archive.label, path))
            if not found:
                continue
            if kind == "MS":
                # The copy whose publication code names this session, else the
                # longest. Choosing by length alone picked the legacy GCE unit's
                # mark scheme over the international one on M1's June 2018.
                named = [c for c in found if pub_matches(subject, c)]
                best = max(named or found, key=lambda c: c.pages)
            else:
                best = max(found, key=lambda c: (c.item_code_pages, c.pages))
            chosen[best.key] = best
            rejected += [c for c in found if c is not best]

    _check_each(subject, chosen)
    _check_pairs(subject, chosen)
    _check_duplicates(subject, chosen)

    for year, season in subject.sittings:
        for kind in ("QP", "MS"):
            key = f"{year}_{season}_{kind}"
            if key in chosen:
                continue
            gone = Paper(key=key, year=year, season=season, kind=kind,
                         source="-", path="-", pages=0)
            # A cancelled series produced no mark scheme of its own; the one
            # for the sitting it was deferred to is the only one there is.
            if (year, season) in subject.cancelled:
                gone.notes.append("this series was cancelled -- the paper was "
                                  "sat in a later one")
            else:
                gone.problems.append("not held in any archive")
            chosen[key] = gone

    order = sorted(chosen.values(),
                   key=lambda p: (p.year, SEASONS.index(p.season), p.kind))
    return order, rejected


def _check_each(subject: Subject, chosen: dict[str, Paper]) -> None:
    for p in chosen.values():
        if p.grademax_pages < p.pages:
            p.problems.append(
                f"GradeMax stamp on only {p.grademax_pages}/{p.pages} pages")
        if p.third_party_pages:
            p.problems.append(f"third-party branding on {p.third_party_pages} pages")

        if p.kind == "MS":
            if p.pub_session is None:
                p.notes.append("no Pearson publication code")
            elif not pub_matches(subject, p):
                said = (f"publication code {p.pub_code} is not {subject.unit} "
                        f"{p.year % 100:02d}{SEASON_MM[p.season]}")
                if (p.year, p.season) in subject.cancelled:
                    p.notes.append(said + " -- it is the later session's, because "
                                          "this series was cancelled")
                else:
                    p.problems.append(said)
            continue

        if p.item_code_pages < p.pages:
            p.problems.append(
                f"board item code on only {p.item_code_pages}/{p.pages} pages "
                "-- likely a worked-solutions document, not a question paper")
        if p.chars_per_page < MIN_TEXT_CHARS_PER_PAGE:
            p.problems.append(
                f"text layer nearly empty ({p.chars_per_page} chars/page)")
        if p.paper_code is None:
            p.notes.append(f"no {subject.unit} paper code in the text layer")

        if p.cover_year is None:
            p.notes.append("cover carries no exam date (it is set in an image)")
        elif p.cover_month not in SEASON_MONTHS[p.season] or p.cover_year != p.year:
            said = f"cover reads {p.cover_month} {p.cover_year}"
            if p.item_code in subject.reissued:
                p.notes.append(f"{said}: the cancelled series' paper, sat later "
                               "-- correct as filed")
            else:
                p.problems.append(f"{said}, filed as {p.year} {p.season}")


def _check_pairs(subject: Subject, chosen: dict[str, Paper]) -> None:
    schemes = [p for p in chosen.values() if p.kind == "MS"]
    if not schemes:
        return
    idf = rarity(schemes)
    for qp in [p for p in chosen.values() if p.kind == "QP"]:
        scores = sorted(((affinity(qp, ms, idf), ms) for ms in schemes),
                        key=lambda t: -t[0])
        top_score, top = scores[0]
        own = next((s for s, ms in scores
                    if ms.year == qp.year and ms.season == qp.season), 0.0)
        qp.best_ms, qp.best_ms_score, qp.own_ms_score = (
            f"{top.year} {top.season}", round(top_score, 3), round(own, 3))
        if (top.year, top.season) == (qp.year, qp.season):
            continue
        if top_score <= own + MISMATCH_MARGIN:
            continue
        said = (f"content matches the {top.year} {top.season} mark scheme "
                f"({top_score:.3f}) better than its own ({own:.3f})")
        # A cancelled sitting has no mark scheme of its own to match, so of
        # course its paper matches the session it was actually sat in. That is
        # the fact being recorded, not a defect.
        if (qp.year, qp.season) in subject.cancelled:
            qp.notes.append(said + " -- this series was cancelled")
        elif (qp.year, qp.season) in subject.settled:
            qp.notes.append(f"{said}; checked by hand: {subject.settled[(qp.year, qp.season)]}")
        else:
            qp.problems.append(said)


def _check_duplicates(subject: Subject, chosen: dict[str, Paper]) -> None:
    by_code: dict[str, list[Paper]] = {}
    for qp in [p for p in chosen.values() if p.kind == "QP" and p.item_code]:
        by_code.setdefault(qp.item_code, []).append(qp)
    for code, group in by_code.items():
        if len(group) < 2:
            continue
        where = ", ".join(f"{g.year} {g.season}" for g in group)
        for g in group:
            msg = f"item code {code} is also filed as {where}"
            (g.notes if code in subject.reissued else g.problems).append(msg)

    by_text: dict[frozenset, list[Paper]] = {}
    for ms in [p for p in chosen.values() if p.kind == "MS"]:
        by_text.setdefault(frozenset(ms.numbers), []).append(ms)
    for group in by_text.values():
        if len(group) < 2:
            continue
        where = ", ".join(f"{g.year} {g.season}" for g in group)
        # One slot being a cancelled series explains the whole group: there is
        # one mark scheme because there was one exam.
        cancelled = any((g.year, g.season) in subject.cancelled for g in group)
        for g in group:
            msg = f"the same mark scheme is filed as {where}"
            (g.notes if cancelled else g.problems).append(msg)


def report(subject: Subject, order: list[Paper], rejected: list[Paper]) -> int:
    hdr = (f"{'session':17} {'kind':3} {'archive':18} {'pp':>3} {'identifier':17} "
           f"{'cover':15} {'stamp':>6}  verdict")
    print(f"{subject.name} ({subject.unit})  -- {len(subject.sittings)} sittings\n")
    print(hdr)
    print("-" * len(hdr))
    for p in order:
        ident = p.pub_code or p.item_code or "-"
        cover = f"{p.cover_month or '-'} {p.cover_year or ''}".strip()
        stamp = f"{p.grademax_pages}/{p.pages}" if p.pages else "-"
        print(f"{p.year} {p.season:12} {p.kind:3} {p.source:18} {p.pages:3} "
              f"{ident:17} {cover:15} {stamp:>6}  {p.verdict}")
        for m in p.problems:
            print(f"{'':21}! {m}")
        for m in p.notes:
            print(f"{'':21}- {m}")

    print()
    print(f"{'question paper':17} {'best mark scheme':18} {'score':>6} {'its own':>8}")
    for p in order:
        if p.kind == "QP" and p.best_ms:
            off = (p.best_ms != f"{p.year} {p.season}"
                   and p.best_ms_score > p.own_ms_score + MISMATCH_MARGIN)
            # A slot the unit has already explained -- a cancelled series, or a
            # pairing settled by hand -- is not flagged here either, so the
            # table and the verdicts above it cannot disagree.
            known = ((p.year, p.season) in subject.cancelled
                     or (p.year, p.season) in subject.settled)
            mark = "   <- mismatch" if off and not known else (
                "   (explained above)" if off else "")
            print(f"{p.year} {p.season:12} {p.best_ms:18} {p.best_ms_score:6.3f} "
                  f"{p.own_ms_score:8.3f}{mark}")

    bad = [p for p in order if p.verdict == "FAIL"]
    print(f"\n{len(order)} slots: {len(order) - len(bad)} usable, {len(bad)} not")

    if rejected:
        print("\nother copies of the same session, not chosen:")
        for p in sorted(rejected, key=lambda p: (p.year, SEASONS.index(p.season), p.kind)):
            why = (f"publication code {p.pub_code}" if p.kind == "MS" and p.pub_code
                   else f"item code on {p.item_code_pages}pp")
            print(f"  {p.year} {p.season:8} {p.kind}  {p.source:18} {p.pages:3}pp  {why}")
    return len(bad)


def as_json(order: list[Paper]) -> list[dict]:
    out = []
    for p in order:
        d = asdict(p)
        d.pop("numbers", None)
        d["verdict"] = p.verdict
        out.append(d)
    return out
