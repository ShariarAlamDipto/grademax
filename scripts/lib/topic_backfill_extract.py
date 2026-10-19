"""
List a subject's live questions that have no topic tags, with the opening of
their question text, for classification by reading. Writes
data/analysis/live_rebuild/<CODE>/topic_backfill.json (entries without a
"topic" yet) and prints one numbered line per question.
"""

from __future__ import annotations

import json
import re

import fitz

from lib.live_paper_sources import REBUILD_DIR, fetch_rows, subject_id, supabase_client

NOISE = re.compile(r"DO NOT WRITE IN THIS AREA|GradeMax|\*P\d+A\d*\*|[^\n]*· QP|Turn over|\.{4,}")


def extract(code: str, chars: int = 280) -> list[dict]:
    sb = supabase_client()
    sid = subject_id(sb, code)
    papers = {p["id"]: p for p in fetch_rows(lambda o: sb.table("papers")
              .select("id,year,season,paper_number").eq("subject_id", sid).range(o, o + 999))}
    rows: list[dict] = []
    ids = list(papers)
    for i in range(0, len(ids), 50):
        part = ids[i:i + 50]
        rows += fetch_rows(lambda o, part=part: sb.table("pages")
                           .select("id,paper_id,question_number,topics")
                           .in_("paper_id", part).not_.is_("qp_page_url", "null")
                           .range(o, o + 999))
    verdicts = json.loads((REBUILD_DIR / code / "verdicts.json").read_text(encoding="utf-8"))
    qp_of = {(r["paper_id"], r["question"]): r["qp"] for r in verdicts["rows"]}
    need = []
    for r in rows:
        if r["topics"]:
            continue
        p = papers[r["paper_id"]]
        path = qp_of.get((r["paper_id"], int(r["question_number"])))
        text = ""
        if path:
            with fitz.open(path) as doc:
                text = " ".join(page.get_text() for page in doc)
        text = re.sub(r"\s+", " ", NOISE.sub(" ", text)).strip()[:chars]
        need.append({"id": r["id"], "key": f"{p['year']} {p['season']} P{p['paper_number']} q{r['question_number']}",
                     "text": text})
    (REBUILD_DIR / code / "topic_backfill.json").write_text(
        json.dumps({"mapped": [], "need": need}, indent=1), encoding="utf-8")
    return need
