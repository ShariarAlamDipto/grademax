#!/usr/bin/env python3
"""Read and audit the staged Maths A PDFs and tags without changing live data."""

from __future__ import annotations

import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path
from types import SimpleNamespace

import fitz

import rebuild_mathsa_live_segments  # installs Maths A evidence-reader rules
from classify_mathsa_tool_topics import validate_tags
from lib.live_ms_linkage import QP_TOTAL_RE
from lib.live_ms_review import load_decisions
from lib.live_paper_sources import LivePaper, fetch_rows, subject_id, supabase_client
from lib.live_rebuild_common import PUBLISHABLE, pairing_verified, verify_paper

ROOT = Path(__file__).resolve().parent.parent
STAGE = ROOT / "data/analysis/live_rebuild/4MA1"


def verified_document_ids() -> set[str]:
    """Read current URLs so a stale whole-paper identity audit cannot qualify."""
    sb = supabase_client()
    sid = subject_id(sb, "4MA1")
    rows = fetch_rows(lambda offset: sb.table("papers")
                      .select("id,year,season,paper_number,pdf_url,markscheme_pdf_url")
                      .eq("subject_id", sid).range(offset, offset + 999))
    papers = [LivePaper(r["id"], r["year"], r["season"], str(r["paper_number"]),
                        r["pdf_url"], r["markscheme_pdf_url"], None, None) for r in rows]
    return pairing_verified(papers)


def main() -> int:
    report = json.loads((STAGE / "verdicts.json").read_text(encoding="utf-8"))
    topics = json.loads((STAGE / "topics_new.json").read_text(encoding="utf-8"))
    sources = json.loads((STAGE / "topic_sources.json").read_text(encoding="utf-8"))
    decisions = load_decisions(STAGE / "manual_review.json")
    document_ids = verified_document_ids()
    rows = report["rows"]
    keys = {f"{r['paper']}|{r['question']}" for r in rows}
    validate_tags(topics, keys)
    failures, no_fence = [], []
    if len(keys) != len(rows):
        failures.append("duplicate question keys")
    if keys != set(topics) or keys != set(sources):
        failures.append("topic/source coverage differs from verdict question keys")
    if any(s.startswith("claude_needed") for s in sources.values()):
        failures.append("unresolved topic reads")
    grouped = defaultdict(list)
    hashes = {"qp": defaultdict(list), "ms": defaultdict(list)}
    for row in rows:
        key = f"{row['paper']}|{row['question']}"
        grouped[row["paper"]].append(row)
        for role in ("qp", "ms"):
            path = ROOT / row[role] if row.get(role) else None
            if path is None or not path.is_file():
                failures.append(f"{key}: missing {role}")
                continue
            hashes[role][hashlib.sha256(path.read_bytes()).hexdigest()].append(key)
            with fitz.open(path) as doc:
                if not doc.page_count or any(min(p.rect.width, p.rect.height) <= 0 for p in doc):
                    failures.append(f"{key}: empty/invalid {role} pages")
                if role == "qp":
                    text = " ".join(p.get_text() for p in doc)
                    totals = {(int(q), int(m)) for q, m in QP_TOTAL_RE.findall(text)}
                    expected = (int(row["question"]), int(row["marks"]))
                    if totals and totals != {expected}:
                        failures.append(f"{key}: wrong/bundled question fences {sorted(totals)}")
                    if not totals:
                        no_fence.append(key)
    for role, found in hashes.items():
        for duplicates in found.values():
            if len(duplicates) > 1:
                failures.append(f"duplicate {role} artifacts: {duplicates}")
    counts = Counter()
    for paper, paper_rows in sorted(grouped.items()):
        paper_rows.sort(key=lambda r: int(r["question"]))
        if [int(r["question"]) for r in paper_rows] != list(range(1, len(paper_rows) + 1)):
            failures.append(f"{paper}: question-number gap")
        if sum(int(r["marks"]) for r in paper_rows) != 100:
            failures.append(f"{paper}: marks do not total 100")
        if any(not r.get("ms") or not (ROOT / r["ms"]).is_file() for r in paper_rows):
            continue
        segments = [SimpleNamespace(number=int(r["question"]), marks=int(r["marks"]),
                                    qp_pages=(r["page_number"] - 1,
                                              r["page_number"] + r["page_count"] - 2))
                    for r in paper_rows]
        directory = (ROOT / paper_rows[0]["qp"]).parent.parent
        audited = verify_paper(ROOT, directory, paper, segments, decisions,
                               document_verified=paper_rows[0]["paper_id"] in document_ids,
                               manual_proven=paper in
                               rebuild_mathsa_live_segments.seg.MANUAL_QP_RANGES)
        for row in audited:
            counts[row["verdict"]] += 1
            if row["verdict"] not in PUBLISHABLE:
                failures.append(f"{paper}|{row['question']}: {row['verdict']} {row['detail']}")
        print(f"{paper}: {len(audited)} pairs checked", flush=True)
    held = [k for k, v in report["papers"].items() if v["status"] != "OK"]
    if held or len(grouped) != len(report["papers"]):
        failures.append(f"held or missing papers: {held}")
    result = {
        "subject": "4MA1", "papers": len(grouped), "questions": len(rows),
        "question_pdfs": sum(len(v) for v in hashes["qp"].values()),
        "markscheme_pdfs": sum(len(v) for v in hashes["ms"].values()),
        "tagged": len(topics), "topic_sources": dict(Counter(sources.values())),
        "primary_sections": dict(sorted(Counter(v[0] for v in topics.values()).items())),
        "fresh_pair_verdicts": dict(counts), "questions_without_text_fence": no_fence,
        "papers_with_current_document_identity": len({r["paper_id"] for r in rows}
                                                     & document_ids),
        "failures": failures, "passed": not failures,
    }
    (STAGE / "artifact_audit.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result, indent=2))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
