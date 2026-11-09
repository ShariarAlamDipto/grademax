"""
Re-cut and republish IGCSE Economics (4EC1) and Business (4BS1) mark schemes.

The commerce stage (onboard_igcse_commerce.py) cut these schemes with the
science banding, which does not fit them: an audit on 2026-11-07 found the
last question's cut stopping one to three pages early (the level descriptors
of its 12-mark part dropped) in nearly every paper, 2026 Jun P1/P1R Q2 cut to
one page of Q1, and Q3 of those papers spread over twelve pages.

These schemes have a simple shape the cut can follow instead: every question
starts on a new page, at its first "N(a)" label, and runs to the page before
the next question starts (the last one to the last page before Pearson's back
cover). A re-cut is accepted only when the new cut prints labels of its own
question and no other, and covers every part letter its QP prints.

  recut    writes changed cuts, records each as an ms_regions decision in
           manual_review.json (so a fresh stage reproduces it) and marks the
           row REVIEWED_PROVEN in verdicts.json. Local files only.
  publish  points the live pages/questions rows at the re-cut PDFs: back up,
           upload, update guarded on the old URL, re-read. Rows not yet live
           are left to publish-commerce-questions.mjs.

Each subject has its own entry script (rule 4); this module is their shared body.
"""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import re
from collections import Counter
from pathlib import Path

import fitz

from lib.igcse_science_rebuild import PUBLISHABLE, upright, write_cut
from lib.live_paper_sources import REBUILD_DIR, ROOT, fetch_rows, subject_id, supabase_client

LABEL_RE = re.compile(r"(?<![\d(])([1-9])\s?\(([a-h])\)")
QP_PART_RE = re.compile(r"(?:^|\s)\(([a-h])\)(?=\s)")
# A part Pearson printed without its number ("(c)" over "AO2 (4 marks)...", 2023 Jun P1R Q4).
BARE_PART_RE = re.compile(r"(?:^|\n)\s*\(([a-h])\)\s*\n\s*AO\d")
BACK_COVER_RE = re.compile(r"Pearson Education Limited|Registered company|80 Strand")
WORD_RE = re.compile(r"[a-z]{4,}")
FOLDERS = {"4EC1": "economics", "4BS1": "business"}


def _words(text: str) -> list[str]:
    return [w for w in WORD_RE.findall(text.lower()) if w != "grademax"]


def is_back_cover(page: fitz.Page) -> bool:
    text = page.get_text()
    if not BACK_COVER_RE.search(text):
        return False
    rest = BACK_COVER_RE.split(text)[0]
    return len(_words(rest)) < 15


def question_pages(src: fitz.Document) -> dict[int, list[int]]:
    """Question number -> 0-based source pages it owns. Raises if a question
    does not start on a fresh page."""
    labels = [[int(n) for n, _ in LABEL_RE.findall(page.get_text())] for page in src]
    start: dict[int, int] = {}
    for i, found in enumerate(labels):
        for n in found:
            start.setdefault(n, i)
    for n, i in start.items():
        if any(m < n for m in labels[i]):
            raise ValueError(f"Q{n} starts on page {i + 1}, which also holds an earlier question")
    order = sorted(start)
    if [start[n] for n in order] != sorted(start.values()):
        raise ValueError(f"question starts out of order: {start}")
    end = len(src)
    while end > 0 and is_back_cover(src[end - 1]):
        end -= 1
    return {n: list(range(start[n], start[order[k + 1]] if k + 1 < len(order) else end))
            for k, n in enumerate(order)}


def cut_labels(doc: fitz.Document) -> set[tuple[int, str]]:
    return {(int(n), part) for page in doc for n, part in LABEL_RE.findall(page.get_text())}


def qp_parts(qp: Path) -> set[str]:
    with fitz.open(qp) as doc:
        return set(QP_PART_RE.findall(" ".join(page.get_text() for page in doc)))


def _page_words(doc: fitz.Document) -> list[list[str]]:
    return [_words(page.get_text()) for page in doc]


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _check(n: int, cut: fitz.Document, qp: Path) -> str | None:
    labels = cut_labels(cut)
    others = sorted({m for m, _ in labels if m != n})
    if others:
        return f"cut prints labels of question(s) {others}"
    bare = {part for page in cut for part in BARE_PART_RE.findall(page.get_text())}
    missing = sorted(qp_parts(qp) - {part for _, part in labels} - bare)
    return f"cut lacks part(s) {missing} the QP prints" if missing else None


def recut(code: str, *, write: bool) -> int:
    stage = REBUILD_DIR / code
    verdicts_path, review_path = stage / "verdicts.json", stage / "manual_review.json"
    staged = json.loads(verdicts_path.read_text(encoding="utf-8"))
    decisions = json.loads(review_path.read_text(encoding="utf-8")) if review_path.is_file() else {}
    tally, refused, rows, ranges, pending = Counter(), [], [], {}, []
    today = dt.date.today().isoformat()
    for row in staged["rows"]:
        key = row["live_key"]
        if key not in ranges:
            with fitz.open(upright(stage / "sources" / f"{key}_ms.pdf")) as src:
                ranges[key] = question_pages(src)
        n = int(row["question"])
        pages = ranges[key].get(n)
        if not pages:
            refused.append((key, n, "question not found in the scheme"))
            rows.append(row)
            continue
        source = upright(stage / "sources" / f"{key}_ms.pdf")
        ms = ROOT / row["ms"]
        with fitz.open(source) as src, fitz.open(ms) as old, fitz.open() as proposed:
            for p in pages:
                proposed.insert_pdf(src, from_page=p, to_page=p)
            same = _page_words(proposed) == _page_words(old)
            why = None if same else _check(n, proposed, ROOT / row["qp"])
        if same:
            tally["unchanged"] += 1
            rows.append(row)
            continue
        if why:
            refused.append((key, n, why))
            rows.append(row)
            continue
        pending.append((source, pages, ms))
        tally["recut"] += 1
        decisions[f"{row['paper']}|{n}"] = {
            "decision": "CONFIRMED",
            "ms_regions": [[p, None, None] for p in pages],
            "reason": (f"{today} page-range recut (lib/commerce_ms_fix.py): Q{n} owns source pages "
                       f"{pages[0] + 1}-{pages[-1] + 1}; labels Q{n} only, every QP part present"),
        }
        rows.append({**row, "verdict": "REVIEWED_PROVEN", "page_count": len(pages),
                     "detail": f"page-range recut: source pages {pages[0] + 1}-{pages[-1] + 1}, "
                               f"labels Q{n} only, all QP parts present"})
    print(f"{code}: {dict(tally)}; refused {len(refused)}")
    for item in refused:
        print("  REFUSED", *item)
    if refused:
        print("Nothing written: every cut must pass before any is changed.")
        return 1
    if not write:
        print("Dry run only. Re-run with --write to write the cuts.")
        return 0
    for source, pages, ms in pending:
        with fitz.open(source) as src:
            write_cut(src, [(p, None, None) for p in pages], ms)
    verdicts_path.write_text(json.dumps({**staged, "rows": rows}, indent=1), encoding="utf-8")
    review_path.write_text(json.dumps(decisions, indent=1, ensure_ascii=False), encoding="utf-8")
    print(f"wrote {tally['recut']} cuts, {verdicts_path.relative_to(ROOT)} and {review_path.relative_to(ROOT)}")
    return 0


def _live_rows(sb, code: str) -> dict[tuple[str, str], dict]:
    sid = subject_id(sb, code)
    ids = [p["id"] for p in fetch_rows(lambda o: sb.table("papers").select("id")
                                        .eq("subject_id", sid).range(o, o + 999))]
    rows: list[dict] = []
    for i in range(0, len(ids), 50):
        part = ids[i:i + 50]
        rows += fetch_rows(lambda o, part=part: sb.table("pages")
                           .select("id,paper_id,question_number,qp_page_url,ms_page_url")
                           .in_("paper_id", part).range(o, o + 999))
    return {(r["paper_id"], str(r["question_number"])): r for r in rows if r["qp_page_url"]}


def publish(code: str, *, execute: bool) -> int:
    import ingest_2026_papers as ing  # noqa: PLC0415 -- needs the env loaded by live_paper_sources

    stage = REBUILD_DIR / code
    staged = json.loads((stage / "verdicts.json").read_text(encoding="utf-8"))["rows"]
    prefix = ing.R2_PUBLIC_URL + "/"

    def key_for(row: dict, kind: str) -> str:
        suffix = "_ms" if kind == "ms" else ""
        digest = sha256(ROOT / row[kind])[:16]
        return f"igcse/{FOLDERS[code]}/pages-v2/{row['live_key']}/q{row['question']}{suffix}-{digest}.pdf"

    sb = supabase_client()
    live = _live_rows(sb, code)
    changes, tally = [], Counter()
    for row in staged:
        if row["verdict"] not in PUBLISHABLE:
            tally["not publishable"] += 1
            continue
        current = live.get((row["paper_id"], str(row["question"])))
        if current is None:
            tally["not live (publish-commerce-questions.mjs inserts it)"] += 1
            continue
        if current["qp_page_url"] != prefix + key_for(row, "qp"):
            raise SystemExit(f"refusing: live QP of {row['live_key']} q{row['question']} is not the staged cut")
        new = prefix + key_for(row, "ms")
        if current["ms_page_url"] == new:
            tally["already live"] += 1
            continue
        tally["to update"] += 1
        changes.append({"id": current["id"], "old": current["ms_page_url"], "new": new,
                        "key": key_for(row, "ms"), "file": ROOT / row["ms"]})
    print(f"{code} live mark schemes [{'EXECUTE' if execute else 'DRY RUN'}]: {dict(tally)}")
    if not execute or not changes:
        if changes:
            print("Dry run only. Re-run with --execute to write.")
        return 0

    ids = [c["id"] for c in changes]
    mirror = []
    for i in range(0, len(ids), 100):
        mirror += sb.table("questions").select("*").in_("id", ids[i:i + 100]).execute().data or []
    pages = []
    for i in range(0, len(ids), 100):
        pages += sb.table("pages").select("*").in_("id", ids[i:i + 100]).execute().data or []
    out = ROOT / "data" / "backups" / f"commerce_ms_recut_{dt.datetime.now():%Y%m%d_%H%M%S}"
    out.mkdir(parents=True, exist_ok=True)
    (out / f"{code}.json").write_text(json.dumps({"pages": pages, "questions": mirror,
                                                  "changes": [{k: str(v) for k, v in c.items()} for c in changes]},
                                                 indent=1), encoding="utf-8")
    print(f"backed up {len(pages)} pages + {len(mirror)} questions rows to {out.relative_to(ROOT)}")

    r2 = ing.get_r2()
    for c in changes:
        r2.put_object(Bucket=ing.R2_BUCKET, Key=c["key"], Body=c["file"].read_bytes(),
                      ContentType="application/pdf")
    print(f"uploaded {len(changes)} PDFs")
    mirrored = {m["id"]: m for m in mirror}
    for c in changes:
        done = sb.table("pages").update({"ms_page_url": c["new"]}).eq("id", c["id"]) \
            .eq("ms_page_url", c["old"]).execute().data
        if len(done or []) != 1:
            raise SystemExit(f"pages {c['id']}: live URL changed under us; stopped (backup in {out})")
        if c["id"] in mirrored and mirrored[c["id"]].get("ms_pdf_url") == c["old"]:
            sb.table("questions").update({"ms_pdf_url": c["new"]}).eq("id", c["id"]) \
                .eq("ms_pdf_url", c["old"]).execute()
    after = {r["id"]: r for i in range(0, len(ids), 100)
             for r in sb.table("pages").select("id,ms_page_url").in_("id", ids[i:i + 100]).execute().data}
    wrong = [c["id"] for c in changes if after.get(c["id"], {}).get("ms_page_url") != c["new"]]
    print(f"re-read: {len(changes) - len(wrong)}/{len(changes)} rows serve the re-cut scheme")
    return 1 if wrong else 0
