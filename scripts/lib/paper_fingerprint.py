"""What a past-paper PDF says it is, and what it actually contains.

Two independent signals, kept apart on purpose:

1. **Identity** -- read off the document's own cover and furniture:
   * MS: the Pearson publications code (`4PH1_1P_1906_MS`, `WMA11_01_2201_MS`)
     and the cover title (`Mark Scheme (Results) Summer 2019`).
   * QP: the exam date (`Monday 20 May 2019`), the paper reference
     (`4PH1/1P`, `WMA11/01`) and the barcode item code (`P61234A`).
   PMT / GradeMax stamp text is stripped first: it is the label that
   mislabelled the archive, so it must never count as evidence.

2. **Content** -- a rarity-weighted bag of the numbers and words in the body
   (the cover page and every calendar year are excluded, so this signal cannot
   echo the identity signal). A mark scheme repeats its own question paper's
   numbers, names and phrases; another paper's scheme does not. Proven on M1:
   right pairs score 0.25-0.46, wrong ones ~0.18 once weighted by rarity.
"""

from __future__ import annotations

import math
import re
from collections import Counter

import fitz  # PyMuPDF

# ── identity ────────────────────────────────────────────────────────────────

MONTH_SEASON = {
    "january": "jan", "february": "jan", "march": "jan", "winter": "jan",
    "april": "may-jun", "may": "may-jun", "june": "may-jun", "july": "may-jun",
    "summer": "may-jun",
    "august": "oct-nov", "september": "oct-nov", "october": "oct-nov",
    "november": "oct-nov", "december": "oct-nov", "autumn": "oct-nov",
}
MONTH_NUM_SEASON = {1: "jan", 2: "jan", 3: "jan", 4: "may-jun", 5: "may-jun",
                    6: "may-jun", 7: "may-jun", 8: "oct-nov", 9: "oct-nov",
                    10: "oct-nov", 11: "oct-nov", 12: "oct-nov"}

_MONTHS = ("January|February|March|April|May|June|July|August|September|"
           "October|November|December")
# Whitespace is optional throughout: OCR of outlined covers glues the words
# ("Monday13May2021").
EXAM_DATE_RE = re.compile(
    r"(?:Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)\s*,?\s*"
    rf"(\d{{1,2}})(?:st|nd|rd|th)?\s*({_MONTHS})\s*,?\s*(20\d{{2}})(?!\d)", re.I)
SESSION_RE = re.compile(rf"\b({_MONTHS}|Summer|Winter|Autumn)\s+(20\d{{2}})\b", re.I)
REISSUE_RE = re.compile(r"\((?:updated|revised|amended)[^)]{0,40}\)", re.I)
MS_RE = re.compile(r"mark\s*scheme|marking\s*scheme", re.I)
QP_COVER_RE = re.compile(
    r"candidate surname|centre number|please check the examination details|"
    r"total marks|you must have|instructions to candidates", re.I)
COPYRIGHT_RE = re.compile(r"(?:©|@|\(c\)|Copyright)\s*(20\d{2})\s*Pearson", re.I)
BARCODE_RE = re.compile(r"\*?\b(P\d{5}[A-Z]{1,2})(?:\d{4})?\*?")

# Unit / spec codes: IGCSE `4PH1`, IAL `WMA11`, `WPH11`, legacy `6677`, `8BI0`.
UNIT = r"(?:4[A-Z]{2}[01]|W[A-Z]{2}\d{2}|X[A-Z]{2}\d{2}|Y[A-Z]{2}\d{2}|\d{4}[A-Z]?)"
# `4PH1_1P_1906_MS`, `WMA11_01_2201_MS`, `WME01_01_rms_20240118`,
# `WPH11_01_MS_1906`. \d{8} before \d{4} or the year eats the date.
PUB_CODE_RE = re.compile(
    rf"\b({UNIT})_([0-9]{{1,2}}[A-Z]{{0,3}})_(?:(?:MS|ms|rms|RMS|MSC)_)?"
    r"(\d{8}|\d{4})(?:_(?:MS|ms|MSC|rms))?\b")
PAPER_REF_RE = re.compile(rf"\b({UNIT})\s*/\s*([0-9]{{1,2}}[A-Z]{{0,3}})(?![A-Za-z0-9])")
# MS cover names its unit in brackets: "(WME01)", "(6677_01R)", "(4PH1) Paper 1P".
MS_COVER_UNIT_RE = re.compile(rf"\(\s*({UNIT})(?:\s*[_/]\s*[0-9]{{1,2}}[A-Z]{{0,2}})?\s*\)")

WATERMARK_RE = re.compile(
    r"(?<![0-9A-Za-z])[0-9A-Z]{4,6}\s*\|\s*20\d{2}\s*\|\s*[A-Za-z/ -]+\s*\|\s*"
    r"(?:Paper|Unit)\s*[0-9A-Za-z]+\s*\|?"
    r"|(?<![0-9A-Za-z])(?:GradeMax\s*)?[A-Za-z_][A-Za-z_0-9 ()]{0,40}·\s*20\d{2}\s*·"
    r"[^·]{2,14}·\s*(?:Paper|Unit)\s*[0-9A-Za-z]+\s*·\s*(?:QP|MS)"
    r"|PhysicsAndMathsTutor\.com|Physics\s*&\s*Maths\s*Tutor|PMT"
    r"|(?<![0-9A-Za-z])GradeMax(?:\.me)?",
    re.I)


# Codes that legitimately appear on another subject's documents: the Science
# Double Award `4SC0` is printed on Physics/Chemistry/Biology mark schemes, and
# Pearson mistyped FPM as `4MP0` on the June 2011 scheme.
UNIT_ALIASES = {"4SC": None, "4MP": "4PM"}


def unit_family(unit: str | None) -> str | None:
    """`4PH1`/`4PH0` -> `4PH` (spec digit varies by era); IAL units stay whole.
    None for a code that says nothing about the subject (4SC0)."""
    if not unit:
        return None
    if re.fullmatch(r"4[A-Z]{2}[01]", unit):
        fam = unit[:3]
        return UNIT_ALIASES.get(fam, fam)
    return unit


def option_letters(paper: str | None) -> str:
    """Option/tier letters of a paper token minus the R (re-sit/reissue) flag:
    `1B` -> `B`, `1DR` -> `D`, `01` -> ``. History options, Maths A tiers."""
    if not paper:
        return ""
    return re.sub(r"[^A-Z]", "", paper.upper()).replace("R", "")


def clean(text: str) -> str:
    return REISSUE_RE.sub(" ", WATERMARK_RE.sub(" ", " ".join(text.split())))


def _season_from_pub(digits: str, kind_hint: str) -> tuple[int | None, str | None, bool]:
    """(year, season, is_publication_date). A 4-digit code is YYMM of the
    session; an 8-digit one is the publication DATE (autumn publishes in the
    next Jan/Feb, summer in August), so it is only a weak hint."""
    if len(digits) == 4:
        yy, mm = int(digits[:2]), int(digits[2:])
        if 1 <= mm <= 12:
            return 2000 + yy, MONTH_NUM_SEASON[mm], False
        # Pearson's own typo: January 2021 printed as `2021`.
        if digits.startswith("20") and 10 <= int(digits[2:]) <= 35:
            return 2000 + int(digits[2:]), "jan", False
        return None, None, False
    y, m = int(digits[:4]), int(digits[4:6])
    if not (2000 <= y <= 2040 and 1 <= m <= 12):
        return None, None, True
    # publication month -> session it reports on
    if m in (1, 2, 3):
        return y - 1, "oct-nov", True   # could also be Jan of y; weak
    if m in (4, 5):
        return y, "jan", True
    return y, "may-jun", True


def identify(pages: list[str]) -> dict:
    """Identity from the first pages' text. Missing fields stay None."""
    head = clean(" ".join(pages[:3]))
    page1 = clean(pages[0]) if pages else ""
    kind = "MS" if MS_RE.search(page1 or head) else (
        "QP" if QP_COVER_RE.search(head) else None)
    ident: dict = {"kind": kind, "unit": None, "paper": None, "year": None,
                   "season": None, "evidence": None, "barcode": None,
                   "pubcode": None, "pub_year": None, "pub_season": None,
                   "pub_is_date": None, "cover_unit": None}

    if kind == "MS":
        m = SESSION_RE.search(page1)
        if m:
            ident.update(year=int(m.group(2)),
                         season=MONTH_SEASON[m.group(1).lower()], evidence=m.group(0))
        m = MS_COVER_UNIT_RE.search(page1)
        if m:
            ident["cover_unit"] = m.group(1)
    # publications code usually sits on page 1 or the last page; caller passes both
    allpub = list(PUB_CODE_RE.finditer(" ".join(clean(p) for p in pages)))
    if allpub:
        m = allpub[0]
        y, s, is_date = _season_from_pub(m.group(3), kind or "")
        ident.update(pubcode=m.group(0), unit=m.group(1), paper=m.group(2),
                     pub_year=y, pub_season=s, pub_is_date=is_date)
        if ident["year"] is None and y and not is_date:
            ident.update(year=y, season=s, evidence=m.group(0))

    if kind != "MS":
        m = EXAM_DATE_RE.search(head)
        if m:
            ident.update(year=int(m.group(3)),
                         season=MONTH_SEASON[m.group(2).lower()], evidence=m.group(0))
        refs = Counter((r.group(1), r.group(2)) for r in PAPER_REF_RE.finditer(head))
        if refs:
            (unit, paper), _n = refs.most_common(1)[0]
            ident.update(unit=ident["unit"] or unit, paper=ident["paper"] or paper)
        m = COPYRIGHT_RE.search(" ".join(pages[:2]))
        if m:
            ident["copy_year"] = int(m.group(1))
        bc = BARCODE_RE.search(" ".join(pages))
        if bc:
            ident["barcode"] = bc.group(1)
    elif ident["year"] is None and ident["pub_year"]:
        ident.update(year=ident["pub_year"], season=ident["pub_season"],
                     evidence=f"{ident['pubcode']} (publication date)")
    return ident


# ── content ─────────────────────────────────────────────────────────────────

NUM_RE = re.compile(r"(?<![\w.])(\d+(?:\.\d+)?)(?![\w])")
WORD_RE = re.compile(r"[a-z][a-z'-]{2,}")
# answer-shaped tokens: `5mu`, `0.67u`, `2m`, `x2`, `v_q`
MIXED_RE = re.compile(r"(?<![\w.])(?=[\w.]*\d)(?=[\w.]*[a-z])[a-z0-9][\w.]{1,11}(?![\w])", re.I)
YEAR_RANGE = range(1995, 2041)
# integers this small are page numbers, question numbers and mark tariffs --
# present in every paper, so they only add noise
SMALL_INT = 41
STOP = frozenset("""the and for with that this are from which what when where there their
then than them they have has had been being was were will would should could
can may might must not but its into onto per any all each other some such only
also more most much very your you our out use used using give given find show
state write answer answers question questions mark marks total paper page
blank leave area turn over continued write""".split())


def content_tokens(pages: list[str]) -> set[str]:
    """Body tokens: every page except the cover, stamps stripped, calendar
    years and small integers dropped; single words, answer-shaped mixed tokens
    and word bigrams (phrases are what a mark scheme quotes back)."""
    toks: set[str] = set()
    for text in pages[1:]:
        text = BARCODE_RE.sub(" ", clean(text))
        for m in NUM_RE.finditer(text):
            n = m.group(1)
            if "." not in n:
                v = int(n) if len(n) < 7 else -1
                if v in YEAR_RANGE or 0 <= v < SMALL_INT:
                    continue
            toks.add("#" + n)
        low = text.lower()
        for m in MIXED_RE.finditer(low):
            if not re.fullmatch(r"p\d{5}\w*", m.group(0)):
                toks.add("~" + m.group(0))
        words = [w.strip("'-") for w in WORD_RE.findall(low)]
        words = [w for w in words if w and w not in STOP]
        toks.update(w for w in words if len(w) >= 4)
        toks.update(f"{a} {b}" for a, b in zip(words, words[1:]))
    return toks


_COMMON = frozenset("the and of to in is for on with that are this be".split())


def _common_ratio(text: str) -> float:
    words = re.findall(r"[a-z]+", text.lower())
    return sum(w in _COMMON for w in words) / (len(words) or 1)


def demojibake(text: str) -> str:
    """Some Edexcel PDFs embed fonts whose glyphs are shifted by 29 code points
    ("/HDYH EODQN" = "Leave blank"). Undo the shift when it makes English."""
    if len(text) < 200 or _common_ratio(text) >= 0.03:
        return text
    shifted = "".join(chr(ord(c) + 29) if 33 <= ord(c) <= 93 else c for c in text)
    return shifted if _common_ratio(shifted) > 0.06 else text


def read_pdf(body: bytes) -> dict:
    """Text of the first 3 pages + last page for identity, all pages for content."""
    doc = fitz.open(stream=body, filetype="pdf")
    try:
        texts = [demojibake(p.get_text()) for p in doc]
    finally:
        doc.close()
    id_pages = texts[:3] + (texts[-1:] if len(texts) > 3 else [])
    ident = identify(id_pages)
    toks = content_tokens(texts)
    return {"ident": ident, "tokens": toks, "pages": len(texts),
            "chars": sum(len(t) for t in texts)}


class RarityScorer:
    """Binary TF-IDF cosine over one subject's documents. Tokens present in
    more than `max_df` of documents are boilerplate and carry no weight."""

    def __init__(self, docs: list[set[str]], max_df: float = 0.35):
        n = max(len(docs), 1)
        df = Counter(t for d in docs for t in d)
        self.w = {t: math.log(n / c) for t, c in df.items()
                  if c / n <= max_df and c >= 1}

    def vec_norm(self, toks: set[str]) -> float:
        return math.sqrt(sum(self.w.get(t, 0.0) ** 2 for t in toks)) or 1.0

    def score(self, a: set[str], b: set[str], na: float, nb: float) -> float:
        small, big = (a, b) if len(a) < len(b) else (b, a)
        return sum(self.w.get(t, 0.0) ** 2 for t in small if t in big) / (na * nb)
