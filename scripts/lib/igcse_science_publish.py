"""
Publish the rebuilt IGCSE science segments (lib.igcse_science_rebuild) through
lib.live_segments_publish -- ONE copy of each paper only.

The archive holds many science papers twice: the site's plain "1"/"1R" and
Pearson's "1C"/"1CR" (Chemistry) or "1B"/"1BR" (Biology), same paper, same
Pearson reference on the cover. The rebuild cuts every papers row, and the
publisher INSERTS a row for each proven question that has no live row, so
handing it both copies would put every duplicate question back into the
tools (368 rows were hidden for exactly that on 2026-10-10).

So per Pearson reference (data/analysis/all_topic_audit/paper_covers.json)
one copy is the paper: the one the tools already serve, else the plain-named
one ("1R" over "1CR"). Every copy's EXISTING rows are updated to its own
proven cut (hidden duplicate rows are still what saved tests point at, so
they get correct schemes too), but new rows are inserted only for the kept
copy -- duplicates never re-enter the tools.
"""

from __future__ import annotations

import glob
import json
from collections import defaultdict
from pathlib import Path

from lib.igcse_science_rebuild import PUBLISHABLE
from lib.live_paper_sources import (REBUILD_DIR, ROOT, fetch_rows, r2_reader, subject_id,
                                    supabase_client)
from lib.live_segments_publish import build_plan, execute

COVERS = ROOT / "data" / "analysis" / "all_topic_audit" / "paper_covers.json"
TWIN_LETTER = {"4CH1": "C", "4BI1": "B", "4HB1": "\0"}


def hidden_duplicates() -> set[str]:
    ids: set[str] = set()
    for path in glob.glob(str(ROOT / "data" / "backups" / "hide_duplicate_papers_*.json")):
        ids |= {p["hide_paper_id"] for p in json.loads(Path(path).read_text(encoding="utf-8"))}
    return ids


def served_paper_ids(code: str) -> set[str]:
    sb = supabase_client()
    sid = subject_id(sb, code)
    papers = [p["id"] for p in fetch_rows(lambda o: sb.table("papers").select("id")
                                          .eq("subject_id", sid).range(o, o + 999))]
    served: set[str] = set()
    for i in range(0, len(papers), 50):
        part = papers[i:i + 50]
        served |= {r["paper_id"] for r in fetch_rows(
            lambda o, part=part: sb.table("pages").select("paper_id").in_("paper_id", part)
            .eq("is_question", True).not_.is_("qp_page_url", "null").range(o, o + 999))}
    return served


def duplicate_copies(code: str, served: set[str]) -> set[str]:
    """Paper ids that are the second copy of a paper (same Pearson reference)."""
    groups: dict[str, list[dict]] = defaultdict(list)
    for paper in json.loads(COVERS.read_text(encoding="utf-8")):
        if paper["code"] == code and paper.get("ref"):
            groups[paper["ref"]].append(paper)
    drop: set[str] = set()
    for copies in groups.values():
        if len(copies) < 2:
            continue
        keep = (next((p for p in copies if p["id"] in served), None)
                or next((p for p in copies if TWIN_LETTER[code] not in p["paper_number"]), None)
                or copies[0])
        drop |= {p["id"] for p in copies if p["id"] != keep["id"]}
    return drop


def load_topics(code: str, rows: list[dict]) -> dict[tuple[str, str], list[str]]:
    """(paper_id, question) -> topics for every rebuilt question that is new or
    whose cut now holds a different question than the live row did: Claude
    read each one (data/analysis/live_rebuild/<CODE>/topics_new.json)."""
    path = REBUILD_DIR / code / "topics_new.json"
    if not path.is_file():
        return {}
    wanted = json.loads(path.read_text(encoding="utf-8"))
    paper_ids = {r["paper"]: r["paper_id"] for r in rows}
    return {(paper_ids[key.split("|")[0]], key.split("|")[1]): topics
            for key, topics in wanted.items() if key.split("|")[0] in paper_ids}


def apply_topics(topics: dict[tuple[str, str], list[str]]) -> None:
    sb = supabase_client()
    done = 0
    for (paper_id, question), codes in topics.items():
        rows = (sb.table("pages").select("id").eq("paper_id", paper_id)
                .eq("question_number", question).not_.is_("qp_page_url", "null").execute().data)
        for row in rows:
            sb.table("pages").update({"topics": codes}).eq("id", row["id"]).execute()
            if sb.table("questions").select("id").eq("id", row["id"]).execute().data:
                sb.table("question_tags").delete().eq("question_id", row["id"]).execute()
                sb.table("question_tags").insert([{"question_id": row["id"], "topic": t}
                                                  for t in codes]).execute()
            done += 1
    print(f"  chapter tags set on {done} rows")


def run(code: str, r2_folder: str, *, do_execute: bool) -> int:
    stage = REBUILD_DIR / code
    verdicts = json.loads((stage / "verdicts.json").read_text(encoding="utf-8"))
    served = served_paper_ids(code)
    drop = hidden_duplicates() | duplicate_copies(code, served)
    rows = verdicts["rows"]
    copies = sorted({r["paper"] for r in rows if r["paper_id"] in drop})
    unproven = [f"{r['paper']} q{r['question']} {r['verdict']}" for r in rows
                if r["verdict"] not in PUBLISHABLE and r["paper_id"] not in drop]
    print(f"{code}: {len(rows)} rebuilt rows; {len(copies)} duplicate copies get their own proven "
          f"cuts on their existing (hidden) rows but NO new rows: {copies}")
    print(f"  unproven in served papers (scheme withheld): {len(unproven)} {unproven}")

    live_audit = json.loads((ROOT / "data" / "analysis" / "live_ms_linkage" / f"{code}.json")
                            .read_text(encoding="utf-8"))
    _, prefix = r2_reader()
    plan, pages_rows = build_plan(code, r2_folder, {"rows": rows}, live_audit, PUBLISHABLE, prefix)
    blocked = [i for i in plan.inserts if i["paper_id"] in drop]
    plan.inserts = [i for i in plan.inserts if i["paper_id"] not in drop]
    plan.counts["new question inserted (unclassified)"] = len(plan.inserts)
    print(f"=== {code} -> live pages  [{'EXECUTE' if do_execute else 'DRY RUN'}] ===")
    for name, n in sorted(plan.counts.items(), key=lambda kv: -kv[1]):
        print(f"  {n:5}  {name}")
    print(f"  inserts blocked on duplicate copies: {len(blocked)}")
    print(f"  uploads planned: {len({k for _, k in plan.uploads})}")
    (stage / "publish_inserts.json").write_text(json.dumps(plan.inserts, indent=1), encoding="utf-8")
    topics = load_topics(code, rows)
    print(f"  chapter tags to set after publishing (new + changed questions): {len(topics)}")
    if do_execute:
        execute(code, plan, pages_rows)
        apply_topics(topics)
    else:
        print("Dry run only. Re-run with --execute to write.")
    return 0
