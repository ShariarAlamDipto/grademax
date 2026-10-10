"""
Prove which mark scheme belongs to which question paper, sitting by sitting and
question by question, before any 2018-2026 yearwise book is built.

Linkage is the book's top priority (user, 2026-10-04): a student who turns to
the answers must land on THIS paper's answers. So nothing here trusts a slot,
a filename or a DB row. Each candidate file from `collect_yearwise_all_sources`
is identified from its own text, and a sitting is LINKED only when the evidence
agrees end to end.

THE EVIDENCE, strongest first

  MS publication code   `4PH1_1P_2306_MS`, `WCH11_01_2301_MS`, or the 8-digit
                        publication-date form. Names unit, paper and session.
                        (The 8-digit form is a RELEASE date; `session_of` maps
                        it back -- the autumn series publishes in Jan/Feb.)
  QP cover code         `4PH1/1P`, `WPH14/01`. Names unit and paper and, via
                        the spec digit, catches legacy-spec papers (4PH0,
                        WPH04, WMA01 C12) filed in a new-spec slot.
  QP cover date         absent on many 2021-2023 covers (set in an image),
                        where an absent date is evidence of nothing.
  pairing               every QP scored against every MS of the unit on the
                        numbers they share, weighted by rarity. The one it
                        matches best must be its own. This is what identifies
                        a QP whose cover carries no readable date.
  per-question marks    the QP's `(Total for Question 3 = 8 marks)` sequence
                        against the scheme's own per-question totals --
                        `Total for Question 3 = 8` (sciences) or the in-order
                        `Total 8 marks` tallies (Maths B). Agreement here means
                        the scheme covers the same questions with the same
                        tariffs, which no near-duplicate paper survives.

VERDICTS
  LINKED   both documents identified, pairing confirms, per-question agrees
           (or the scheme states no per-question totals to compare).
  REVIEW   nothing contradicts, but a piece of evidence is missing.
  FAIL     a contradiction, or a document missing.
  LEGACY   the only paper held is the old specification's.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path

import fitz

from lib.yearwise_all_catalogue import ROOT, SEASONS, UNITS, WORK, Unit, sitting_of

# Every real unit/spec code a title may name, legacy ones included.
KNOWN_UNITS = frozenset(code for u in UNITS for code in u.pub_units)
from lib.ms_bands import find_tallies
from lib.yearwise_sources import (
    COVER_DATE, NUMERIC, SEASON_MM, SEASON_MONTHS, affinity, rarity, session_of)

# A reprint adds R, and a second reprint RR (`P66027RRA`, FPM Oct 2021).
ITEM_CODE = re.compile(r"\*?(P\d{5}R{0,2}A)\d{4}\*?")

PUB_CODE = re.compile(
    r"Publications?\s*Code\s*[:\s]?\s*([A-Z0-9]{4,5})_([0-9A-Z]{1,3})_"
    r"(?:(?:r?ms|msc|MS)_)?(\d{8}|\d{4})", re.I)
QP_TOTAL = re.compile(r"\(\s*Total\s+for\s+Question\s+(\d+)\s*(?:is|=)\s*(\d+)\s+marks?\s*\)", re.I)
# IAL practical schemes (WPH16) print "Total for question 7" where 7 is the
# MARKS, the question number omitted -- an in-order tally, not a pair.
MS_BARE_QTOTAL = re.compile(r"Total\s+for\s+[Qq]uestion\s+(\d+)(?=\s+[A-Za-z(])")
# A one-question section states only "TOTAL FOR SECTION C = 20 MARKS".
SECTION_TOTAL = re.compile(r"TOTAL\s+FOR\s+SECTION\s+[A-Z]\s*(?:=|IS)\s*(\d+)\s+MARKS", re.I)
MS_QTOTAL = re.compile(r"Total\s+for\s+[Qq]uestion\s+(\d+)\s*(?:=|is|:)?\s*(\d+)(?!\d)", re.I)
MS_TALLY = re.compile(r"\bTotal\s+(\d+)\s+marks?\b", re.I)
# Fallback per-question closers, in order of trust: IAL P1-P4 schemes end a
# question "(6 marks)"; some FPM schemes end it "[3]".
MS_PAREN_TOTAL = re.compile(r"\((\d{1,2})\s*marks\)", re.I)
MS_BRACKET_TOTAL = re.compile(r"\[\s*(\d{1,2})\s*\]")
PAPER_TOTAL = re.compile(r"TOTAL\s+FOR\s+PAPER\s+(?:IS|=)\s+(\d+)\s+MARKS", re.I)
# A scheme's title page names itself: "Mark Scheme (Results) Summer 2019 ...
# Mathematics B (4MB1) Paper 02". Stronger than the publication code, which
# carries Pearson's slips (2018 4MB1 Paper 2 coded `4MB1_01`; year-only `2021`).
MS_TITLE = re.compile(
    r"Mark\s*Scheme\s*\((?:Results?|Final|Provisional)\)\s*"
    r"(January|Summer|June|May|Autumn|October|November)\s*(20\d\d)", re.I)
# "(4MB1) Paper 02", "(WCH12) Paper 01R", and bracket-less "WPH12/01" (the
# 2026 IAL Physics style -- missing it let a WPH12 scheme pass as WPH11's).
MS_TITLE_PAPER = re.compile(
    r"\(?\b((?=[0-9A-Z]*[A-Z])(?=[0-9A-Z]*\d)[0-9A-Z]{4,5})\)?"
    r"\s*(?:/\s*|Paper\s*:?\s*)(\d{1,2}[A-Z]{0,2})\b")
# Rare words pair the near-numberless Biology schemes (IAL 95/95 own-best vs
# 57/95 on numbers); numbers win everywhere else (Maths B 36/36 vs 19/36).
WORD = re.compile(r"[a-z]{6,}")
TITLE_SEASON = {"january": "Jan", "summer": "May-Jun", "june": "May-Jun", "may": "May-Jun",
                "autumn": "Oct-Nov", "october": "Oct-Nov", "november": "Oct-Nov"}
SESSION_MONTHS = {"Jan": ("01", "02"), "May-Jun": ("05", "06"), "Oct-Nov": ("10", "11")}
# The scheme names the exact paper it marks: "Question Paper Log Number
# P66310A". Present on ~60% of schemes; when present it is the strongest link
# there is, so it outranks the number match and settles pairing disputes.
MS_LOG = re.compile(r"Paper\s*Log\s*Number\s*:?\s*(P\d{5}R{0,2}A)", re.I)
# Any Edexcel cover code, to explain a rejection ("cover reads 4PH1/1PR").
ANY_CODE = re.compile(r"\b(4[A-Z]{2}[01]\s*/\s*\w{1,3}|W[A-Z]{2}\d{2}\s*/\s*\d{2}\w?)\b")

MARGIN = 0.05
SOURCE_RANK = {"db": 0, "pearson": 0, "local": 1, "paperlords": 2}
IDENT_CACHE = WORK / "ident_cache.json"
_cache: dict | None = None


@dataclass
class Doc:
    """What one PDF says about itself."""
    path: str
    source: str
    pages: int = 0
    chars_per_page: int = 0
    item_code: str | None = None
    item_code_pages: int = 0
    text_pages: int = 0
    cover_codes: list = field(default_factory=list)
    cover_month: str | None = None
    cover_year: int | None = None
    pub_unit: str | None = None
    pub_paper: str | None = None
    pub_session: str | None = None
    title_season: str | None = None
    title_year: int | None = None
    title_unit: str | None = None
    title_paper: str | None = None
    log_number: str | None = None
    qp_totals: list = field(default_factory=list)     # [(q, marks)]
    ms_qtotals: list = field(default_factory=list)    # [(q, marks)]
    ms_tallies: list = field(default_factory=list)    # [marks] in order
    ms_bare: list = field(default_factory=list)       # [marks] in order, WPH16 style
    section_totals: list = field(default_factory=list)
    paper_total: int | None = None
    numbers: list = field(default_factory=list)
    words: list = field(default_factory=list)
    # Pages with a text layer but no item code -- appended inserts (Equation
    # Booklet, Unit 5 Scientific Article) are a trailing run of these.
    no_code_pages: list = field(default_factory=list)
    insert_pages: list = field(default_factory=list)


def _tallies(path: Path, body: str) -> list[int]:
    """A scheme's per-question totals in order, from whichever closer it uses."""
    found = [t.marks for t in find_tallies(path)]
    if found:
        return found
    for rx in (MS_PAREN_TOTAL, MS_BRACKET_TOTAL):
        found = [int(x) for x in rx.findall(body)]
        if len(found) >= 3:
            return found
    return []


def _read(path: Path, kind: str) -> dict:
    with fitz.open(path) as doc:
        texts = [p.get_text() for p in doc]
    blob = "\n".join(texts)
    flat = re.sub(r"\s+", " ", blob)
    head = re.sub(r"\s+", " ", "\n".join(texts[:3]))
    codes = sorted({m.group(1) for m in ITEM_CODE.finditer(blob)})
    cm = COVER_DATE.search("\n".join(texts[:2]))
    pub = None
    for m in PUB_CODE.finditer(flat):
        pub = m                                  # the last one is the scheme's own
    pt = PAPER_TOTAL.search(flat)
    tm = MS_TITLE.search(head) if kind == "MS" else None
    tp = MS_TITLE_PAPER.search(head) if kind == "MS" else None
    lg = MS_LOG.search(flat) if kind == "MS" else None
    body = "\n".join(texts[4:]) if kind == "MS" else blob
    return {
        "pages": len(texts),
        "chars_per_page": len(blob) // max(1, len(texts)),
        "item_code": codes[0] if codes else None,
        "item_code_pages": sum(1 for t in texts if ITEM_CODE.search(t)),
        # Image-only pages carry nothing but our stamp (~100 chars).
        "text_pages": sum(1 for t in texts if len(t) > 150),
        "cover_codes": sorted({re.sub(r"\s+", "", m.group(1)) for m in ANY_CODE.finditer(head)}),
        "cover_month": cm.group(1) if cm else None,
        "cover_year": int(cm.group(2)) if cm else None,
        "pub_unit": pub.group(1).upper() if pub else None,
        "pub_paper": pub.group(2).upper() if pub else None,
        "pub_session": (pub.group(3) if len(pub.group(3)) == 4 and pub.group(3).startswith("20")
                        else session_of(pub.group(3))) if pub else None,
        "title_season": TITLE_SEASON[tm.group(1).lower()] if tm else None,
        "title_year": int(tm.group(2)) if tm else None,
        "title_unit": tp.group(1) if tp else None,
        "title_paper": tp.group(2).upper() if tp else None,
        "log_number": lg.group(1) if lg else None,
        "qp_totals": [(int(a), int(b)) for a, b in QP_TOTAL.findall(flat)] if kind == "QP" else [],
        "ms_qtotals": [(int(a), int(b)) for a, b in MS_QTOTAL.findall(flat)] if kind == "MS" else [],
        "ms_bare": [int(a) for a in MS_BARE_QTOTAL.findall(flat)] if kind == "MS" else [],
        "section_totals": [int(a) for a in SECTION_TOTAL.findall(flat)] if kind == "QP" else [],
        "ms_tallies": _tallies(path, body) if kind == "MS" else [],
        "paper_total": int(pt.group(1)) if pt else None,
        "numbers": sorted(set(NUMERIC.findall(body))),
        "words": sorted(set(WORD.findall(body.lower()))),
        "no_code_pages": [i for i, t in enumerate(texts)
                          if len(t) > 150 and not ITEM_CODE.search(t)],
        # Insert pages (Scientific Article, Equation Booklet) print the
        # paper's item code bare -- "P67793A" -- instead of the barcode form.
        "insert_pages": [i for i, t in enumerate(texts)
                         if not ITEM_CODE.search(t)
                         and codes and re.search(rf"\b{re.escape(codes[0])}\b", t)],
        "head": head[:4000],
    }


def identify(rel_path: str, source: str, kind: str) -> tuple[Doc, str]:
    """Read (or recall) a file's own evidence. Returns the Doc and the cover text."""
    global _cache
    if _cache is None:
        _cache = json.loads(IDENT_CACHE.read_text(encoding="utf-8")) if IDENT_CACHE.exists() else {}
    path = ROOT / rel_path
    stat = path.stat()
    key = hashlib.sha1(f"{rel_path}|{stat.st_size}|{int(stat.st_mtime)}|{kind}|v10".encode()).hexdigest()
    if key not in _cache:
        _cache[key] = _read(path, kind)
    data = dict(_cache[key])
    head = data.pop("head")
    return Doc(path=rel_path, source=source, **data), head


def save_cache() -> None:
    if _cache is not None:
        IDENT_CACHE.write_text(json.dumps(_cache), encoding="utf-8")


@dataclass
class Sitting:
    year: int
    season: str
    qp: Doc | None = None
    ms: Doc | None = None
    spec: str | None = None
    verdict: str = "FAIL"
    evidence: list = field(default_factory=list)
    problems: list = field(default_factory=list)
    rejected: list = field(default_factory=list)
    pairing: dict = field(default_factory=dict)
    per_question: str = ""
    # Identity checked by eye (image-only covers), with the evidence.
    settled: str | None = None

    @property
    def label(self) -> str:
        return f"{self.year} {self.season}"


def _yymm(year: int, season: str) -> str:
    return f"{year % 100:02d}{SEASON_MM[season]}"


def _judge_qp(unit: Unit, s: Sitting, d: Doc, head: str) -> str | None:
    """None if the QP may be this sitting's paper, else why not.

    A cover with NO readable code (an image cover) is admitted; pairing must
    then single it out. A cover naming some OTHER paper is refused.
    """
    if not unit.qp_code.search(head) and d.cover_codes:
        return f"cover reads {', '.join(d.cover_codes)}, not {unit.label}"
    if d.cover_year is not None:
        ok = d.cover_month in SEASON_MONTHS[s.season] and d.cover_year == s.year
        deferred = ((s.year, s.season) == (2020, "Oct-Nov") and d.cover_year == 2020
                    and d.cover_month in SEASON_MONTHS["May-Jun"])
        if not (ok or deferred):
            return f"cover dated {d.cover_month} {d.cover_year}"
    return None


def _pub_session_ok(s: Sitting, session: str | None) -> bool | None:
    if not session:
        return None
    if session == str(s.year):                     # Pearson's year-only slip
        return None
    return session[:2] == f"{s.year % 100:02d}" and session[2:] in SESSION_MONTHS[s.season]


def _judge_ms(unit: Unit, s: Sitting, d: Doc) -> str | None:
    """The title page decides; the publication code may only corroborate."""
    if d.title_year is not None:
        deferred = ((s.year, s.season) == (2020, "Oct-Nov")
                    and (d.title_year, d.title_season) == (2020, "May-Jun"))
        if (d.title_year, d.title_season) != (s.year, s.season) and not deferred:
            return f"title page reads {d.title_season} {d.title_year}"
        # Only a REAL other unit code condemns a scheme: Pearson's own typos
        # ("(WB13)" on WBI13 Oct 2021) must not.
        if d.title_unit and d.title_unit not in unit.pub_units and d.title_unit in KNOWN_UNITS:
            return f"title page names {d.title_unit}, not {unit.label}"
        if d.title_paper and _foreign_paper(unit, d.title_paper):
            return f"title page names paper {d.title_paper}, not {unit.label}"
        # A title without a unit code still has to agree with the publication
        # code's UNIT (its paper digit carries Pearson's copy slips, so not that).
        if not d.title_unit and d.pub_unit and d.pub_unit not in unit.pub_units:
            return f"publication code names {d.pub_unit}, not {unit.label}"
        return None
    if d.pub_unit is None:
        return None                      # unidentified -- pairing must decide
    if d.pub_unit not in unit.pub_units or d.pub_paper not in unit.pub_paper:
        return f"publication code is {d.pub_unit}_{d.pub_paper}, not {unit.label}"
    if _pub_session_ok(s, d.pub_session) is False:
        return f"publication code names session {d.pub_session}"
    return None


def _foreign_paper(unit: Unit, paper: str) -> bool:
    """
    Does a title's paper token name some other paper?

    IGCSE: the digit and letter matter ("Paper 02" is not Paper 1; "1PR" is
    the time-zone variant). IAL: Pearson prints the digit any old way -- WPH15
    titles read "Paper 5", "Paper 0" and "Paper 05" -- so only a variant letter
    (01R time-zone, 01A adapted) means a different paper.
    """
    if unit.level == "IAL":
        return paper.rstrip("0123456789") != ""
    return paper.lstrip("0") not in {p.lstrip("0") for p in unit.pub_paper}


def _ms_ident(d: Doc) -> int:
    """2 = title page names it, 1 = only a publication code, 0 = nothing."""
    return 2 if d.title_year is not None else (1 if d.pub_unit else 0)


def _spec_of(unit: Unit, head: str) -> str | None:
    m = unit.qp_code.search(head)
    return m.group(1) if m else None


def _rank(d: Doc) -> tuple:
    """Prefer a copy whose text layer can be read, then the DB copy.

    The R2 copy of FPM 2019 Jun Paper 1 is image-only -- every page's text is
    our own stamp -- while the archive copy keeps the full text layer.
    """
    readable = bool(d.cover_codes) or d.item_code_pages > 0
    return (not readable, SOURCE_RANK[d.source.split(":")[0]], -d.item_code_pages, -d.pages)


def _is_legacy(code: str | None, legacy_specs: set[str]) -> bool:
    return bool(code) and any(code.startswith(spec) for spec in legacy_specs)


def gather(unit: Unit, candidates: list[dict], legacy_specs: set[str] = frozenset()) -> list[Sitting]:
    """
    Choose each sitting's QP and MS from its candidates.

    In 2019 the old and new IAL specifications ran side by side, so a sitting
    can hold BOTH a legacy paper (WPH01, filed in our DB) and the new-spec one
    (WPH11, from Paperlords). The new spec always wins; the legacy paper is
    only chosen when it is all there is.
    """
    sittings: dict[tuple[int, str], Sitting] = {}
    for c in candidates:
        if not c.get("path"):
            continue
        year, season = sitting_of(c["year"], c["season"])
        s = sittings.setdefault((year, season), Sitting(year, season))
        doc, head = identify(c["path"], c["source"], c["kind"])
        why = _judge_qp(unit, s, doc, head) if c["kind"] == "QP" else _judge_ms(unit, s, doc)
        if why:
            s.rejected.append(f"{c['kind']} {c['source']} ({c['year']} {c['season']}): {why}")
            continue
        if c["kind"] == "QP":
            spec = _spec_of(unit, head)
            key = (_is_legacy(spec, legacy_specs), _rank(doc))
            if s.qp is None or key < (_is_legacy(s.spec, legacy_specs), _rank(s.qp)):
                if (s.qp and s.qp.item_code and doc.item_code and s.qp.item_code != doc.item_code
                        and _is_legacy(spec, legacy_specs) == _is_legacy(s.spec, legacy_specs)):
                    s.problems.append(f"two different papers claim this sitting: "
                                      f"{s.qp.item_code} and {doc.item_code}")
                s.qp, s.spec = doc, spec
        else:
            key = (_is_legacy(doc.title_unit or doc.pub_unit, legacy_specs), -_ms_ident(doc), _rank(doc))
            if s.ms is None or key < (_is_legacy(s.ms.title_unit or s.ms.pub_unit, legacy_specs),
                                      -_ms_ident(s.ms), _rank(s.ms)):
                s.ms = doc
    return sorted(sittings.values(), key=lambda s: (s.year, SEASONS.index(s.season)))


def pair(sittings: list[Sitting], signal: str = "numbers") -> None:
    """Score every QP against every MS of the unit on `signal` ("numbers" or "words")."""
    schemes = [s for s in sittings if s.ms]
    if not schemes:
        return

    class _N:                                     # affinity() wants `.numbers` as a set
        def __init__(self, doc: Doc) -> None:
            self.numbers = set(getattr(doc, signal))
    idf = rarity([_N(s.ms) for s in schemes])
    for s in sittings:
        if not s.qp:
            continue
        q = _N(s.qp)
        scored = sorted(((affinity(q, _N(o.ms), idf), o) for o in schemes), key=lambda t: -t[0])
        top_score, top = scored[0]
        own = next((sc for sc, o in scored if o is s), 0.0)
        runner = next((sc for sc, o in scored if o is not s), 0.0)
        s.pairing = {"own": round(own, 3), "best": top.label, "best_score": round(top_score, 3),
                     "runner_up": round(runner, 3)}
    # The other direction: which paper does each SCHEME fit best? A long
    # scheme is a "hub" that out-scores the right one for many papers (P1
    # Jan 2019 vs P1 Jun 2019), yet the right scheme still picks its own
    # paper out of the line-up.
    papers = [s for s in sittings if s.qp]
    for s in schemes:
        m = _N(s.ms)
        best = max(papers, key=lambda o: affinity(_N(o.qp), m, idf), default=None)
        if s.qp and best is not None:
            s.pairing["ms_best"] = best.label


def _agree_numbered(want: dict[int, int], pairs: list) -> tuple[str, int, int]:
    have: dict[int, int] = {}
    for q, m in pairs:
        have.setdefault(q, m)
    common = [q for q in want if q in have]
    agreed = sum(want[q] == have[q] for q in common)
    differ = len(common) - agreed
    # One or two differing totals amid strong agreement is the right scheme
    # with a misprinted or misread total (reported, not failed); a different
    # scheme disagrees on most questions it shares.
    if differ > agreed:
        return "mismatch", agreed, len(want)
    # Some schemes print totals on only some questions (WPH11 Oct 2019: 7 of
    # 17), so a third of the paper agreeing, none against, suffices.
    if agreed >= max(3, len(want) // 3) and differ <= max(1, agreed // 4):
        return "agree", agreed, len(want)
    return "none", agreed, len(want)


def _agree_sequence(seq: list[int], tallies: list[int]) -> tuple[str, int, int]:
    """Unnumbered tallies: align the sequences. A tally the text layer lost
    leaves the scheme a clean subsequence (extra = 0) -- still the right one."""
    hit = _lcs(seq, tallies)
    extra = len(tallies) - hit
    if hit >= len(seq) - 1 or (hit >= 3 and extra <= max(1, hit // 4)):
        return "agree", hit, len(seq)
    if extra > hit:
        return "mismatch", hit, len(seq)
    return "none", hit, len(seq)


def question_agreement(qp: Doc, ms: Doc) -> tuple[str, int, int]:
    """
    How well a scheme's per-question totals fit this paper's, by whichever
    reading of the scheme fits best. Returns (status, agreed, of); status is
    "agree", "mismatch" or "none" (nothing to compare).
    """
    if not qp.qp_totals:
        return "none", 0, 0
    seq = [m for _, m in qp.qp_totals]
    readings = []
    if ms.ms_qtotals:
        readings.append(_agree_numbered(dict(qp.qp_totals), ms.ms_qtotals))
    if ms.ms_tallies:
        readings.append(_agree_sequence(seq, ms.ms_tallies))
    if len(ms.ms_bare) >= 3:
        readings.append(_agree_sequence(seq, ms.ms_bare))
    if not readings:
        return "none", 0, len(seq)
    rank = {"agree": 0, "none": 1, "mismatch": 2}
    return min(readings, key=lambda r: (rank[r[0]], -r[1]))


def compare_questions(s: Sitting) -> None:
    qp, ms = s.qp, s.ms
    status, hit, of = question_agreement(qp, ms)
    if not qp.qp_totals:
        s.per_question = "QP states no per-question totals"
    elif status == "none" and not (ms.ms_qtotals or ms.ms_tallies or ms.ms_bare):
        s.per_question = "scheme states no per-question totals"
    elif status == "none":
        s.per_question = f"too few scheme totals ({hit}/{of})"
    elif status == "agree":
        s.per_question = f"agree on {hit}/{of} questions"
        differ = _differing(qp, ms)
        if differ:
            s.per_question += f"; totals differ on {differ} -- check these in print"
    elif ms.ms_qtotals:
        s.per_question = f"MISMATCH {hit}/{of} agree; differ on {_differing(qp, ms)}"
    else:
        seq = [m for _, m in qp.qp_totals]
        s.per_question = f"MISMATCH {hit}/{of} agree: paper {seq} vs scheme tallies {ms.ms_tallies}"


def _differing(qp: Doc, ms: Doc) -> str:
    """'Q4 10v9, Q7 12v13' -- paper total v scheme total, for numbered totals."""
    have: dict[int, int] = {}
    for q, m in ms.ms_qtotals:
        have.setdefault(q, m)
    return ", ".join(f"Q{q} {m}v{have[q]}" for q, m in qp.qp_totals
                     if q in have and have[q] != m)


def _total_gap(q: Doc) -> str | None:
    """
    Do the question totals add up to the paper total?

    A shortfall with a HOLE in the question numbering (Q8, Q9 absent between
    Q7 and Q10) is an unreadable page -- an image-only page or a total set
    outside the text layer -- and the paper is still complete. A shortfall
    with consecutive numbering means questions are really missing.
    """
    if not (q.paper_total and q.qp_totals):
        return None
    got = sum(m for _, m in q.qp_totals)
    if got == q.paper_total:
        return None
    nums = sorted({n for n, _ in q.qp_totals})
    holes = [n for n in range(1, nums[-1] + 1) if n not in nums]
    if q.paper_total - got in q.section_totals:
        return (f"note: question totals sum to {got}/{q.paper_total}; the remaining "
                f"{q.paper_total - got} is a one-question section stating only its section total")
    if holes and got < q.paper_total:
        return (f"note: Q{', Q'.join(map(str, holes))} total not in the text layer; "
                f"the other questions sum to {got}/{q.paper_total}")
    return f"QP question totals sum to {got}, paper says {q.paper_total} -- questions missing?"


def p_best_is_own(s: Sitting) -> bool:
    return s.pairing.get("best") == s.label


def _lcs(a: list[int], b: list[int]) -> int:
    row = [0] * (len(b) + 1)
    for x in a:
        prev = 0
        for j, y in enumerate(b, 1):
            cur = row[j]
            row[j] = prev + 1 if x == y else max(row[j], row[j - 1])
            prev = cur
    return row[-1]


def _strip_r(code: str) -> str:
    return re.sub(r"R+A$", "A", code)


def _log_link(s: Sitting) -> bool | None:
    """True: the scheme names this paper. False: it names another. None: unknown."""
    if not (s.ms.log_number and s.qp.item_code):
        return None
    return _strip_r(s.ms.log_number) == _strip_r(s.qp.item_code)


def _judge_pairing(s: Sitting, by_label: dict[str, Sitting], review: list[str]) -> None:
    """
    The number match is evidence, not a verdict -- P4 and FPM pairs sit within
    0.02 of their runners-up. When the paper is identified by its cover and its
    own scheme agrees question by question while the rival's does NOT, the
    questions win and the number match is recorded as overruled.
    """
    p = s.pairing
    if s.settled and p.get("best") != s.label:
        s.evidence.append(f"note: number match prefers the {p.get('best')} scheme; "
                          f"identity settled by hand: {s.settled}")
        return
    log = _log_link(s)
    if log is False:
        # Pearson reuses scheme templates without updating the log number
        # (WBI12 Jun 2026 names the Jun 2022 paper; WMA12 Jun 2021 names
        # P4's). A stale log is harmless when the content picks this paper
        # out; it is a wrong scheme only when the content does not.
        said = f"scheme names paper {s.ms.log_number}, but the paper is {s.qp.item_code}"
        if p.get("best") == s.label and p["own"] >= p["runner_up"] + MARGIN:
            s.evidence.append(f"note: {said} -- stale template log number; "
                              f"content pairs it ({p['own']} vs next {p['runner_up']})")
        else:
            s.problems.append(said)
        return
    if log:
        s.evidence.append(f"scheme names this paper: log number {s.ms.log_number}")
    if not p or p.get("best") == s.label:
        return
    if log:
        s.evidence.append(f"note: number match prefers the {p['best']} scheme "
                          f"({p['best_score']} vs {p['own']}); overruled by the log number")
        return
    if p.get("ms_best") == s.label and s.spec is not None:
        s.evidence.append(f"note: the paper's number match prefers the {p['best']} scheme "
                          f"({p['best_score']} vs {p['own']}), but this scheme's best paper is this one")
        return
    rival = by_label[p["best"]].ms
    own_q = question_agreement(s.qp, s.ms)
    rival_q = question_agreement(s.qp, rival) if rival else ("none", 0, 0)
    said = (f"number match prefers the {p['best']} scheme ({p['best_score']}) "
            f"over its own ({p['own']})")
    if own_q[0] == "agree" and rival_q[0] != "agree" and s.spec is not None:
        s.evidence.append(f"note: {said}; overruled -- own scheme agrees on "
                          f"{own_q[1]}/{own_q[2]} questions, that one on {rival_q[1]}/{rival_q[2]}")
    elif p.get("best_score", 0) > p.get("own", 0) + MARGIN:
        s.problems.append(said)
    else:
        review.append(f"pairing margin thin: {said}")


def judge(unit: Unit, sittings: list[Sitting], legacy_specs: set[str],
          settled: dict | None = None) -> None:
    """
    `settled` maps (unit key, "2019 May-Jun") -> {"spec": "4PM1", "why": "..."}
    for papers identified by eye because the cover is an image. The spec it
    states is used as the cover's; the reason travels with the verdict.
    """
    by_label = {x.label: x for x in sittings}
    for s in sittings:
        hand = (settled or {}).get((unit.key, s.label))
        # A settled identity belongs to the copy that was looked at: it applies
        # only when the chosen QP is that paper (or has no readable code).
        if hand and s.qp and s.qp.item_code in (None, hand.get("item")):
            s.spec, s.settled = hand["spec"], hand["why"]
            s.evidence.append(f"identified by eye: {hand['why']}")
        if s.spec in legacy_specs:
            s.verdict = "LEGACY"
            s.evidence.append(f"cover spec {s.spec} (legacy)")
            continue
        if not s.qp or not s.ms:
            s.problems.append("no acceptable " + ("QP" if not s.qp else "MS"))
            s.verdict = "FAIL"
            continue
        q, m = s.qp, s.ms
        review = []
        s.evidence.append(f"QP {q.item_code or '?'} cover {s.spec}"
                          + (f" {q.cover_month} {q.cover_year}" if q.cover_year else " (date in image)"))
        if m.title_year is not None:
            s.evidence.append(f"MS title {m.title_season} {m.title_year} {m.title_unit or ''} "
                              f"paper {m.title_paper or '?'}")
            if m.pub_unit and (m.pub_paper not in unit.pub_paper or _pub_session_ok(s, m.pub_session) is False):
                s.evidence.append(f"note: publication code {m.pub_unit}_{m.pub_paper}_{m.pub_session} "
                                  "disagrees with the title page (Pearson slip)")
        elif m.pub_unit:
            s.evidence.append(f"MS publication code {m.pub_unit}_{m.pub_paper} session {m.pub_session}")
        else:
            review.append("MS names no session (no title, no publication code)")
        if s.spec is None:
            strong = _log_link(s) or (
                p_best_is_own(s) and s.pairing.get("own", 0) >= 0.2
                and s.pairing["own"] >= s.pairing["runner_up"] + MARGIN)
            (s.evidence if strong else review).append(
                "QP cover code unreadable; " + ("identified by pairing" if strong
                                                else "pairing too weak to identify it"))
        _judge_pairing(s, by_label, review)
        compare_questions(s)
        if s.per_question.startswith("MISMATCH"):
            s.problems.append(s.per_question)
        gap = _total_gap(q)
        if gap:
            # A settled scan's totals are unreadable, not missing.
            (s.evidence if gap.startswith("note") or s.settled else review).append(gap)
        # Pages without the barcode are fine when they are this paper's own
        # insert (bare item code) or an appended booklet at the very back.
        insert = set(q.insert_pages)
        unexplained = [i for i in q.no_code_pages if i not in insert]
        trailing = (bool(unexplained)
                    and unexplained == list(range(unexplained[0], unexplained[0] + len(unexplained)))
                    and unexplained[-1] >= q.pages - 3 and len(unexplained) <= 10)
        if insert:
            s.evidence.append(f"note: pages {min(insert) + 1}-{max(insert) + 1} are this paper's own "
                              f"insert (bare item code {q.item_code}); it travels with the paper")
        if len(unexplained) > 2 and trailing:
            s.evidence.append(f"note: last {len(unexplained)} pages carry no item code -- an appended "
                              "booklet (e.g. Equation Booklet)")
        elif len(unexplained) > 2 and not s.settled:
            review.append(f"item code missing on text pages {[i + 1 for i in unexplained]}")
        s.verdict = "FAIL" if s.problems else ("REVIEW" if review else "LINKED")
        s.problems += review if s.verdict == "REVIEW" else []


def dedupe_papers(sittings: list[Sitting]) -> None:
    """One paper filed under two sittings is printed once -- flag the later copy."""
    seen: dict[str, Sitting] = {}
    for s in sittings:
        if s.qp and s.qp.item_code and s.verdict in ("LINKED", "REVIEW"):
            if s.qp.item_code in seen:
                s.problems.append(f"same paper ({s.qp.item_code}) as {seen[s.qp.item_code].label}")
                s.verdict = "FAIL"
            else:
                seen[s.qp.item_code] = s


def run_unit(unit: Unit, candidates: list[dict], legacy_specs: set[str],
             signal: str = "numbers", settled: dict | None = None) -> list[Sitting]:
    sittings = gather(unit, candidates, legacy_specs)
    pair(sittings, signal)
    judge(unit, sittings, legacy_specs, settled)
    dedupe_papers(sittings)
    return sittings


def as_json(unit: Unit, sittings: list[Sitting]) -> dict:
    def doc(d: Doc | None):
        if d is None:
            return None
        out = asdict(d)
        out.pop("numbers")
        out.pop("words")
        return out
    return {"unit": unit.key, "label": unit.label, "sittings": [
        {"sitting": s.label, "verdict": s.verdict, "spec": s.spec, "qp": doc(s.qp), "ms": doc(s.ms),
         "pairing": s.pairing, "per_question": s.per_question, "evidence": s.evidence,
         "problems": s.problems, "rejected": s.rejected} for s in sittings]}
