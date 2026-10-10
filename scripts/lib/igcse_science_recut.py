"""
Re-cut individual IGCSE science papers (Chemistry, Biology, Human Biology) whose
LIVE question segments are wrong, and publish the new cuts in place.

Found by the 2026-10-10 chapter-tag audit (data/analysis/all_topic_audit/):

  * wrong source  -- the paper row's own PDF is right but every q<n>.pdf was cut
                     from ANOTHER paper (Chem 2016 Jan P1 held 2015 Jan P1;
                     Bio and Chem 2022 May-Jun P1 held Paper 2R);
  * shifted cuts  -- fixed 2-page slices that ignore where questions start
                     (Bio 2019 Jan P2, Human Bio 2012 May-Jun P1/P2 and 2019
                     Jan P2: covers, fragments and blank pages);
  * the mark schemes of all of them were page slices too, so q3_ms.pdf began
    at question 2's scheme.

These subjects have no workbook segmenter, so the cut is simpler than
lib.live_rebuild_common: IGCSE science questions start at the top of a page
with the number hard against the left margin, so a question is a PAGE RANGE
(how every other live row of these subjects is cut). Mark schemes are banded
with lib.ms_bands (question-number labels in the margin column; a question
whose label is unreadable starts just past the previous question's tally).

The question and scheme counts must agree, every question start must be found
in order, and a contact sheet of every cut is written for a human look before
anything is published.

Publishing follows lib.live_segments_publish: new content-hashed R2 objects
under <r2_folder>/pages-v2/, existing pages rows UPDATED in place (ids kept for
saved tests), surplus rows hidden (URLs nulled), missing rows inserted, the
`questions` mirror and `question_tags` kept in step, and a backup first. The
old rows' topics described the WRONG questions, so every row takes the topics
recorded for the new cut in the subject's topics file.
"""

from __future__ import annotations

import datetime as dt
import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path

import fitz

from lib import ms_bands
from lib.live_paper_sources import ROOT, r2_reader, subject_id, supabase_client
from lib.live_rebuild_common import is_scrambled, ocr_copy

STAGE_ROOT = ROOT / "data" / "analysis" / "live_recut_20261010"
PAGE_BASE = 1000          # same convention as live_segments_publish
LEFT_MARGIN_MAX_X = 75.0  # question numbers sit at x 43-71
FIRST_LINE_MAX_Y = 140.0  # ...on the first text line below the header
END_MARKERS = ("TOTAL FOR PAPER",)
BLANK_RE = re.compile(r"BLANK\s+PAGE", re.I)
# Our own stamp lines: "GradeMax", "Biology · 2012 · Jan · Paper 1 · MS", "4HB0 | 2012 | ...".
STAMP_RE = re.compile(r"GradeMax|·|\|")


@dataclass(frozen=True)
class PaperSpec:
    code: str          # subject code, e.g. "4CH1"
    r2_folder: str     # e.g. "subjects/Chemistry"
    year: int
    season: str        # papers.season, e.g. "may-jun"
    paper_number: str  # papers.paper_number, e.g. "1"
    live_key: str      # folder name, e.g. "2016_Jan_1"


@dataclass(frozen=True)
class Cut:
    question: int
    qp: Path
    ms: Path
    qp_pages: tuple[int, ...]
    page_count: int
    text: str


# ── reading ─────────────────────────────────────────────────────────────────

def readable(pdf: Path) -> Path:
    """The OCR'd copy when the text layer is scrambled or image-only."""
    return ocr_copy(pdf) if is_scrambled(pdf) else pdf


def question_starts(qp_read: Path) -> dict[int, int]:
    """Question number -> 0-based page where it starts, taken strictly in order."""
    starts: dict[int, int] = {}
    expected = 1
    with fitz.open(qp_read) as doc:
        for index, page in enumerate(doc):
            height = page.rect.height
            for word in page.get_text("words"):
                x0, y0, text = word[0], word[1], word[4]
                if x0 >= LEFT_MARGIN_MAX_X or not (50 < y0 < height - 60):
                    continue
                if text != str(expected):
                    continue
                if expected > 1 and y0 > FIRST_LINE_MAX_Y:
                    continue
                starts[expected] = index
                expected += 1
                break
    return starts


def end_page(qp_read: Path) -> int:
    """Last page holding question content: the TOTAL FOR PAPER page."""
    with fitz.open(qp_read) as doc:
        for index in range(doc.page_count - 1, -1, -1):
            text = doc[index].get_text().upper()
            if any(marker in text for marker in END_MARKERS):
                return index
        return doc.page_count - 1


def is_blank_sheet(page: fitz.Page) -> bool:
    return bool(BLANK_RE.search(page.get_text())) and len(page.get_text("words")) < 40


# ── cutting ─────────────────────────────────────────────────────────────────

def cut_questions(qp: Path, qp_read: Path, out_dir: Path) -> dict[int, tuple[Path, tuple[int, ...], str]]:
    starts = question_starts(qp_read)
    if not starts:
        raise SystemExit(f"{qp.name}: no question starts found")
    last = end_page(qp_read)
    numbers = sorted(starts)
    cuts: dict[int, tuple[Path, tuple[int, ...], str]] = {}
    with fitz.open(qp) as src, fitz.open(qp_read) as read:
        for position, number in enumerate(numbers):
            first = starts[number]
            stop = starts[numbers[position + 1]] - 1 if position + 1 < len(numbers) else last
            pages = tuple(p for p in range(first, stop + 1)
                          if p == first or not is_blank_sheet(read[p]))
            target = out_dir / f"q{number}.pdf"
            with fitz.open() as new:
                for p in pages:
                    new.insert_pdf(src, from_page=p, to_page=p)
                new.save(target, garbage=3, deflate=True)
            text = "\n".join(read[p].get_text() for p in pages)
            cuts[number] = (target, pages, text)
    return cuts


def _scheme_headers(ms_read: Path, count: int) -> tuple[list[ms_bands.BlockHeader], dict[int, int]]:
    """First margin label of each question, falling back to the previous tally."""
    labels = ms_bands.find_question_labels(ms_read)
    tallies = ms_bands.find_tallies(ms_read)
    first: dict[int, ms_bands.BlockHeader] = {}
    for label in labels:
        if label.question is not None and 1 <= label.question <= count:
            first.setdefault(label.question, label)
    for number in range(2, count + 1):
        if number not in first and len(tallies) == count:
            closing = tallies[number - 2]
            first[number] = ms_bands.BlockHeader(page=closing.page, lo=closing.hi + 2.0,
                                                 question=number, axis=closing.axis)
    missing = [n for n in range(1, count + 1) if n not in first]
    if missing:
        raise SystemExit(f"{ms_read.name}: no scheme start for question(s) {missing}")
    ordered = [first[n] for n in range(1, count + 1)]
    if any((b.page, b.lo) <= (a.page, a.lo) for a, b in zip(ordered, ordered[1:])):
        raise SystemExit(f"{ms_read.name}: scheme starts out of order")
    return ordered, {n: n - 1 for n in range(1, count + 1)}


def _scheme_last_page(ms_read: Path, count: int) -> int:
    tallies = ms_bands.find_tallies(ms_read)
    if len(tallies) >= count:
        return tallies[count - 1].page
    with fitz.open(ms_read) as doc:
        last = doc.page_count - 1
        # Drop the Pearson back matter: trailing pages with no scheme marks.
        while last > 0 and not re.search(r"\(\w\)|\bM\d\b|accept|ignore",
                                         doc[last].get_text(), re.I):
            last -= 1
        return last


def _is_empty_strip(sheet: fitz.Page) -> bool:
    """Nothing but our stamp / footer lines (the tail of a page after a tally)."""
    lines = [ln for ln in sheet.get_text().splitlines()
             if ln.strip() and not STAMP_RE.search(ln) and not re.fullmatch(r"\s*\d+\s*", ln)]
    return sum(len(ln.strip()) for ln in lines) < 15


def cut_schemes(ms: Path, ms_read: Path, count: int, out_dir: Path) -> dict[int, Path]:
    headers, assignment = _scheme_headers(ms_read, count)
    last = _scheme_last_page(ms_read, count)
    bands = ms_bands.bands_from_headers(headers, assignment, last_page=last)
    out: dict[int, Path] = {}
    with fitz.open(ms) as src:
        for number in range(1, count + 1):
            band = bands[number]
            target = out_dir / f"q{number}_ms.pdf"
            with fitz.open() as new:
                for page_no in range(band.start_page, band.end_page + 1):
                    page = src[page_no]
                    top = band.start_at if page_no == band.start_page else None
                    bottom = band.end_at if page_no == band.end_page else None
                    if band.axis != ms_bands.AXIS_Y or page.rotation or (top is None and bottom is None):
                        new.insert_pdf(src, from_page=page_no, to_page=page_no)
                        continue
                    top = max(0.0, top or 0.0)
                    bottom = min(page.rect.height, bottom or page.rect.height)
                    if bottom - top < ms_bands.MIN_BAND_EXTENT:
                        continue
                    clip = fitz.Rect(0, top, page.rect.width, bottom)
                    sheet = new.new_page(width=clip.width, height=clip.height)
                    sheet.show_pdf_page(sheet.rect, src, page_no, clip=clip)
                empty = [i for i, sheet in enumerate(new) if _is_empty_strip(sheet)]
                if len(empty) < new.page_count:
                    for i in reversed(empty):
                        new.delete_page(i)
                if new.page_count == 0:
                    new.insert_pdf(src, from_page=band.start_page, to_page=band.start_page)
                new.save(target, garbage=3, deflate=True)
            out[number] = target
    return out


def contact_sheet(cuts: list[Cut], target: Path) -> None:
    """First page of every question and scheme cut, side by side, for a look."""
    thumb_w, thumb_h = 300, 424
    with fitz.open() as sheet:
        page = sheet.new_page(width=thumb_w * 2 + 30, height=(thumb_h + 20) * len(cuts) + 10)
        for row, cut in enumerate(cuts):
            y = 10 + row * (thumb_h + 20)
            for col, pdf in enumerate((cut.qp, cut.ms)):
                with fitz.open(pdf) as doc:
                    src = doc[0]
                    scale = min(thumb_w / src.rect.width, thumb_h / src.rect.height)
                    rect = fitz.Rect(10 + col * (thumb_w + 10), y,
                                     10 + col * (thumb_w + 10) + src.rect.width * scale,
                                     y + src.rect.height * scale)
                    page.show_pdf_page(rect, doc, 0)
            page.insert_text((10, y - 2), f"Q{cut.question}  qp pages {list(cut.qp_pages)}",
                             fontsize=8)
        pix = page.get_pixmap(dpi=40)
        pix.save(target)


def stage(spec: PaperSpec, sources: dict[str, str]) -> list[Cut]:
    """Download, cut and check one paper. Returns its cuts (nothing published)."""
    get, _ = r2_reader()
    work = STAGE_ROOT / spec.code / spec.live_key
    work.mkdir(parents=True, exist_ok=True)
    qp, ms = work / "source_qp.pdf", work / "source_ms.pdf"
    if not qp.is_file():
        qp.write_bytes(get(sources["qp"]))
    if not ms.is_file():
        ms.write_bytes(get(sources["ms"]))
    qp_read, ms_read = readable(qp), readable(ms)

    questions = cut_questions(qp, qp_read, work)
    count = max(questions)
    if sorted(questions) != list(range(1, count + 1)):
        raise SystemExit(f"{spec.live_key}: question starts not 1..{count}")
    schemes = cut_schemes(ms, ms_read, count, work)
    cuts = [Cut(question=n, qp=questions[n][0], ms=schemes[n], qp_pages=questions[n][1],
                page_count=len(questions[n][1]), text=questions[n][2])
            for n in range(1, count + 1)]
    contact_sheet(cuts, work / "contact.png")
    (work / "texts.json").write_text(json.dumps(
        {c.question: re.sub(r"\s+", " ", c.text)[:1500] for c in cuts}, indent=1,
        ensure_ascii=False), encoding="utf-8")
    return cuts


# ── publishing ──────────────────────────────────────────────────────────────

def _paper_row(sb, spec: PaperSpec) -> dict:
    rows = (sb.table("papers").select("id,pdf_url,markscheme_pdf_url")
            .eq("subject_id", subject_id(sb, spec.code)).eq("year", spec.year)
            .eq("season", spec.season).eq("paper_number", spec.paper_number).execute().data)
    if len(rows) != 1:
        raise SystemExit(f"{spec}: expected one papers row, found {len(rows)}")
    return rows[0]


def _key(spec: PaperSpec, path: Path, number: int, suffix: str) -> str:
    digest = hashlib.md5(path.read_bytes()).hexdigest()[:10]
    return f"{spec.r2_folder}/pages-v2/{spec.live_key}/q{number}{suffix}-{digest}.pdf"


def _excerpt(text: str) -> str:
    return text[:500]


def plan_paper(sb, spec: PaperSpec, cuts: list[Cut], topics: dict[str, list[str]],
               prefix: str) -> dict:
    paper = _paper_row(sb, spec)
    rows = sb.table("pages").select("*").eq("paper_id", paper["id"]).execute().data
    missing_topics = [c.question for c in cuts if not topics.get(str(c.question))]
    if missing_topics:
        raise SystemExit(f"{spec.live_key}: no topics recorded for {missing_topics}")

    by_number: dict[int, dict] = {}
    surplus: list[dict] = []
    for row in sorted(rows, key=lambda r: r["page_number"]):
        match = re.match(r"\d+", str(row["question_number"]))
        number = int(match.group()) if match else None
        if number is None or number in by_number or number > len(cuts):
            surplus.append(row)
        else:
            by_number[number] = row

    uploads, updates, inserts = [], [], []
    for cut in cuts:
        qp_key, ms_key = _key(spec, cut.qp, cut.question, ""), _key(spec, cut.ms, cut.question, "_ms")
        uploads += [(cut.qp, qp_key), (cut.ms, ms_key)]
        fields = {
            "qp_page_url": prefix + qp_key, "ms_page_url": prefix + ms_key,
            "topics": topics[str(cut.question)], "page_number": PAGE_BASE + cut.question,
            "page_count": cut.page_count, "text_excerpt": _excerpt(cut.text),
            "is_question": True,
        }
        row = by_number.get(cut.question)
        if row:
            updates.append({"id": row["id"], **fields})
        else:
            inserts.append({"paper_id": paper["id"], "question_number": str(cut.question),
                            "difficulty": None, "has_diagram": False, **fields})
    hides = [r["id"] for r in surplus if r["qp_page_url"] or r["is_question"]]
    return {"spec": spec, "paper_id": paper["id"], "rows": rows, "uploads": uploads,
            "updates": updates, "inserts": inserts, "hides": hides}


def backup(code: str, plans: list[dict]) -> Path:
    sb = supabase_client()
    stamp = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    out = ROOT / "data" / "backups" / f"live_recut_{code}_{stamp}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    ids = [r["id"] for p in plans for r in p["rows"]]
    mirror = sb.table("questions").select("*").in_("id", ids).execute().data if ids else []
    tags = sb.table("question_tags").select("*").in_("question_id", ids).execute().data if ids else []
    out.write_text(json.dumps({"pages": [r for p in plans for r in p["rows"]],
                               "questions": mirror, "question_tags": tags}, indent=1),
                   encoding="utf-8")
    return out


def _set_tags(sb, page_id: str, topics: list[str]) -> None:
    sb.table("question_tags").delete().eq("question_id", page_id).execute()
    if topics:
        sb.table("question_tags").insert([{"question_id": page_id, "topic": t} for t in topics]).execute()


def execute(code: str, plans: list[dict]) -> None:
    import ingest_2026_papers as ing  # noqa: PLC0415 -- env loaded by r2_reader

    from lib.live_segments_publish import _put_with_retry  # noqa: PLC0415

    r2_reader()
    r2 = ing.get_r2()
    print(f"backup  : {backup(code, plans).relative_to(ROOT)}")
    for plan in plans:
        for local, key in plan["uploads"]:
            _put_with_retry(r2, ing.R2_BUCKET, key, local.read_bytes())

    sb = supabase_client()
    for plan in plans:
        ids = [r["id"] for r in plan["rows"]]
        mirrored = {r["id"] for r in sb.table("questions").select("id").in_("id", ids).execute().data} \
            if ids else set()
        for change in plan["updates"]:
            fields = {k: v for k, v in change.items() if k != "id"}
            sb.table("pages").update(fields).eq("id", change["id"]).execute()
            if change["id"] in mirrored:
                sb.table("questions").update({
                    "page_pdf_url": fields["qp_page_url"], "ms_pdf_url": fields["ms_page_url"],
                    "text_excerpt": fields["text_excerpt"]}).eq("id", change["id"]).execute()
                _set_tags(sb, change["id"], fields["topics"])
        for page_id in plan["hides"]:
            sb.table("pages").update({"qp_page_url": None, "ms_page_url": None,
                                      "is_question": False}).eq("id", page_id).execute()
            if page_id in mirrored:
                sb.table("questions").update({"page_pdf_url": None, "ms_pdf_url": None}) \
                    .eq("id", page_id).execute()
                _set_tags(sb, page_id, [])
        if plan["inserts"]:
            created = sb.table("pages").insert(plan["inserts"]).execute().data or []
            sb.table("questions").upsert([{
                "id": c["id"], "paper_id": c["paper_id"], "question_number": c["question_number"],
                "difficulty": None, "page_pdf_url": c["qp_page_url"], "ms_pdf_url": c["ms_page_url"],
                "has_diagram": False, "text_excerpt": c["text_excerpt"],
            } for c in created]).execute()
            for c in created:
                _set_tags(sb, c["id"], c["topics"])
        print(f"  {plan['spec'].live_key}: updated {len(plan['updates'])}, "
              f"inserted {len(plan['inserts'])}, hidden {len(plan['hides'])}")


def verify(plans: list[dict], cuts_by_key: dict[str, list[Cut]]) -> int:
    sb = supabase_client()
    bad = 0
    for plan in plans:
        live = sb.table("pages").select("question_number,qp_page_url,is_question,topics") \
            .eq("paper_id", plan["paper_id"]).execute().data
        served = sorted(int(r["question_number"]) for r in live
                        if r["is_question"] and r["qp_page_url"] and r["topics"])
        expected = [c.question for c in cuts_by_key[plan["spec"].live_key]]
        if served != expected:
            bad += 1
            print(f"  MISMATCH {plan['spec'].live_key}: served {served} expected {expected}")
    return bad


def run(code: str, specs: list[PaperSpec], topics_file: Path, *, do_execute: bool,
        stage_only: bool) -> int:
    sb = supabase_client()
    _, prefix = r2_reader()
    cuts_by_key: dict[str, list[Cut]] = {}
    for spec in specs:
        paper = _paper_row(sb, spec)
        cuts = stage(spec, {"qp": paper["pdf_url"], "ms": paper["markscheme_pdf_url"]})
        cuts_by_key[spec.live_key] = cuts
        print(f"staged {spec.live_key}: {len(cuts)} questions -> "
              f"{(STAGE_ROOT / spec.code / spec.live_key).relative_to(ROOT)}")
    if stage_only:
        return 0

    topics = json.loads(topics_file.read_text(encoding="utf-8"))
    plans = [plan_paper(sb, spec, cuts_by_key[spec.live_key], topics.get(spec.live_key, {}), prefix)
             for spec in specs]
    print(f"=== {code} [{'EXECUTE' if do_execute else 'DRY RUN'}] ===")
    for plan in plans:
        print(f"  {plan['spec'].live_key}: update {len(plan['updates'])}, "
              f"insert {len(plan['inserts'])}, hide {len(plan['hides'])}, "
              f"upload {len(plan['uploads'])}")
    if not do_execute:
        print("Dry run only. Re-run with --execute to write.")
        return 0
    execute(code, plans)
    bad = verify(plans, cuts_by_key)
    print(f"verification mismatches: {bad}")
    return 1 if bad else 0
