#!/usr/bin/env python3
"""
Re-tag every live IGCSE Maths B (4MB1) question with the right chapter.

The test builder and worksheet generator filter on `pages.topics`. Measured
2026-10-09: on the 1,046 questions the verified chapterwise workbook also holds,
only 55% of the live tags agreed with the workbook, and Algebra was a catch-all
(628 of 2,158 rows). The workbook sections were checked by hand, so they are the
truth wherever they exist:

  * a live row whose (paper, question number) is a verified workbook question
    takes that question's chapter (workbook chapter 11 Calculus -> live topic 4,
    whose description already covers differentiation);
  * every other row takes the topic Claude assigned after reading the question,
    recorded with its stem in data/analysis/mathsb_topic_audit/claude_read_topics.json.

Writes pages.topics and mirrors question_tags for rows that have a `questions`
mirror. Backs up every row's previous topics first.

    python scripts/fix_mathsb_live_chapter_topics.py            # dry run
    python scripts/fix_mathsb_live_chapter_topics.py --execute
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from lib.live_paper_sources import ROOT, fetch_rows, subject_id, supabase_client  # noqa: E402

CODE = "4MB1"
CALCULUS_CHAPTER = 11
CALCULUS_LIVE_TOPIC = "4"
RECORD = ROOT / "data" / "analysis" / "mathsb_topic_audit" / "claude_read_topics.json"
BACKUP_DIR = ROOT / "data" / "backups"
VALID_TOPICS = {str(n) for n in range(1, 11)}


def workbook_topics(sb, sid: str) -> dict[tuple[str, int], str]:
    chapters = sb.table("workbook_chapters").select("id,number").eq("subject_id", sid).execute().data
    number = {c["id"]: c["number"] for c in chapters}
    sections = (sb.table("workbook_sections").select("id,chapter_id")
                .in_("chapter_id", list(number)).execute().data)
    chapter_of = {s["id"]: number[s["chapter_id"]] for s in sections}
    rows = fetch_rows(lambda o: sb.table("workbook_questions")
                      .select("section_id,source_paper_key,source_question_number,verified_at")
                      .eq("subject_id", sid).not_.is_("verified_at", "null").range(o, o + 999))
    out = {}
    for row in rows:
        chapter = chapter_of[row["section_id"]]
        topic = CALCULUS_LIVE_TOPIC if chapter == CALCULUS_CHAPTER else str(chapter)
        out[(row["source_paper_key"], int(row["source_question_number"]))] = topic
    return out


def live_rows(sb, sid: str) -> list[dict]:
    papers = fetch_rows(lambda o: sb.table("papers").select("id,year,season,paper_number")
                        .eq("subject_id", sid).range(o, o + 999))
    key = {p["id"]: f"{p['year']}_{p['season']}_{p['paper_number']}" for p in papers}
    ids = list(key)
    rows: list[dict] = []
    for i in range(0, len(ids), 50):
        chunk = ids[i:i + 50]
        rows += fetch_rows(lambda o: sb.table("pages")
                           .select("id,paper_id,question_number,topics,qp_page_url")
                           .in_("paper_id", chunk).range(o, o + 999))
    for row in rows:
        row["paper_key"] = key[row["paper_id"]]
    return rows


def plan(rows: list[dict], workbook: dict, read: dict) -> tuple[list[dict], list[str]]:
    changes, problems = [], []
    for row in rows:
        number = row["question_number"]
        wb_key = (row["paper_key"], int(number)) if str(number).isdigit() else None
        if wb_key in workbook:
            topic, source = workbook[wb_key], "workbook"
        elif row["id"] in read:
            topic, source = read[row["id"]], "claude_read"
        else:
            problems.append(f"{row['paper_key']} Q{number} ({row['id']}): no topic source")
            continue
        if topic not in VALID_TOPICS:
            problems.append(f"{row['paper_key']} Q{number}: invalid topic {topic!r}")
            continue
        changes.append({**row, "new": [topic], "source": source})
    return changes, problems


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()

    sb = supabase_client()
    sid = subject_id(sb, CODE)
    workbook = workbook_topics(sb, sid)
    read = {r["id"]: r["topic"] for r in json.loads(RECORD.read_text(encoding="utf-8"))["rows"]}
    rows = live_rows(sb, sid)
    changes, problems = plan(rows, workbook, read)

    differ = [c for c in changes if sorted(c["topics"] or []) != c["new"]]
    print(f"{CODE}: {len(rows)} live rows | workbook-sourced "
          f"{sum(c['source'] == 'workbook' for c in changes)} | Claude-read "
          f"{sum(c['source'] == 'claude_read' for c in changes)} | changing {len(differ)}")
    print("  before:", sorted(Counter(t for r in rows for t in (r["topics"] or [])).items(),
                              key=lambda kv: int(kv[0])))
    print("  after: ", sorted(Counter(c["new"][0] for c in changes).items(), key=lambda kv: int(kv[0])))
    if problems:
        print(f"  {len(problems)} problem(s) -- nothing written:")
        for line in problems[:20]:
            print("   ", line)
        return 1
    if not args.execute:
        print("Dry run only. Re-run with --execute to write.")
        return 0

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup = BACKUP_DIR / f"mathsb_live_topics_{stamp}.json"
    backup.parent.mkdir(parents=True, exist_ok=True)
    backup.write_text(json.dumps([{"id": r["id"], "topics": r["topics"]} for r in rows], indent=1),
                      encoding="utf-8")
    print(f"  backup: {backup.relative_to(ROOT)}")

    by_topic: dict[str, list[str]] = {}
    for change in differ:
        by_topic.setdefault(change["new"][0], []).append(change["id"])
    for topic, ids in by_topic.items():
        for i in range(0, len(ids), 100):
            sb.table("pages").update({"topics": [topic]}).in_("id", ids[i:i + 100]).execute()

    mirrored = {r["id"] for i in range(0, len(changes), 150)
                for r in sb.table("questions").select("id")
                .in_("id", [c["id"] for c in changes[i:i + 150]]).execute().data}
    for change in changes:
        if change["id"] in mirrored:
            sb.table("question_tags").delete().eq("question_id", change["id"]).execute()
            sb.table("question_tags").insert({"question_id": change["id"],
                                              "topic": change["new"][0]}).execute()

    after = {r["id"]: r["topics"] for r in live_rows(sb, sid)}
    wrong = [c for c in changes if after.get(c["id"]) != c["new"]]
    print(f"  written {len(differ)} pages rows; question_tags mirrored for {len(mirrored)}; "
          f"verification mismatches: {len(wrong)}")
    return 0 if not wrong else 1


if __name__ == "__main__":
    sys.exit(main())
