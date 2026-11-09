#!/usr/bin/env python3
"""Stage Cambridge IGCSE Physics (0625) variant-2 structured papers for the tools.

Scope (user decision 2026-11-08): Paper 42 (Theory, Extended) and Paper 62
(Alternative to Practical), every live series 2015-2025. Whole questions with
every subpart; chapters are the six 2023-2025 syllabus topics. Chapter tags are
direct reads pinned to the SHA-256 of both PDFs, never keywords.

    .venv/Scripts/python -X utf8 scripts/onboard_cambridge_physics.py sources  # R2 -> sources/
    .venv/Scripts/python -X utf8 scripts/onboard_cambridge_physics.py stage    # cut + prove -> verdicts.json
    .venv/Scripts/python -X utf8 scripts/onboard_cambridge_physics.py dump     # review/*.txt for reading
    #   -> read every pair into reads/<batch>.json, then:
    .venv/Scripts/python -X utf8 scripts/onboard_cambridge_physics.py merge-reads  # -> topic_reads.json
    .venv/Scripts/python -X utf8 scripts/onboard_cambridge_physics.py audit    # artifact_audit.json
    .venv/Scripts/python -X utf8 scripts/onboard_cambridge_physics.py marks    # src/lib/printedMarks/0625.json
    node --env-file=.env.local scripts/publish-cambridge-physics-questions.mjs [--execute]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import fitz

sys.path.insert(0, str(Path(__file__).resolve().parent))

from lib.cambridge_physics_segments import PAPER_MARKS, stage_and_prove  # noqa: E402
from lib.igcse_science_rebuild import PUBLISHABLE  # noqa: E402
from lib.live_paper_sources import REBUILD_DIR, ROOT, LivePaper  # noqa: E402

CODE = "0625"
SUBJECT_ID = "94fab3eb-0755-41f8-90b4-dd00af2ed1ee"
COMPONENTS = ("42", "62")
BASE = REBUILD_DIR / CODE
CHAPTERS = {
    "1": "Motion, forces and energy",
    "2": "Thermal physics",
    "3": "Waves",
    "4": "Electricity and magnetism",
    "5": "Nuclear physics",
    "6": "Space physics",
}
DIFFICULTIES = ("easy", "medium", "hard")


def sha256(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def cached_papers() -> list[LivePaper]:
    rows = json.loads((BASE / "papers.json").read_text(encoding="utf-8"))
    out = []
    for row in rows:
        stem = f"{row['year']}_{row['season']}_P{row['paper_number']}"
        paths = [BASE / "sources" / f"{stem}_{kind}.pdf" for kind in ("qp", "ms")]
        out.append(LivePaper(row["id"], row["year"], row["season"], str(row["paper_number"]),
                             row["pdf_url"], row["markscheme_pdf_url"],
                             *[p if p.is_file() else None for p in paths]))
    return sorted(out, key=lambda p: (p.paper_number, p.year, p.season))


def sources() -> None:
    """Fetch the live (R2) copies of every 0625 Paper 42/62 into sources/."""
    from lib.live_paper_sources import r2_reader, supabase_client  # noqa: PLC0415
    sb = supabase_client()
    rows = (sb.table("papers").select("id,year,season,paper_number,pdf_url,markscheme_pdf_url")
            .eq("subject_id", SUBJECT_ID).in_("paper_number", list(COMPONENTS)).execute().data)
    rows = sorted(rows, key=lambda r: (r["year"], r["season"], r["paper_number"]))
    (BASE / "sources").mkdir(parents=True, exist_ok=True)
    (BASE / "papers.json").write_text(json.dumps(rows, indent=1), encoding="utf-8")
    get_bytes, _ = r2_reader()

    def one(row: dict) -> None:
        stem = f"{row['year']}_{row['season']}_P{row['paper_number']}"
        for url, kind in ((row["pdf_url"], "qp"), (row["markscheme_pdf_url"], "ms")):
            path = BASE / "sources" / f"{stem}_{kind}.pdf"
            if url and not path.is_file():
                data = get_bytes(url)
                if data:
                    path.write_bytes(data)

    with ThreadPoolExecutor(10) as pool:
        list(pool.map(one, rows))
    print(f"{len(rows)} papers cached")


def stage(only: str | None) -> None:
    review = BASE / "manual_review.json"
    decisions = json.loads(review.read_text(encoding="utf-8")) if review.is_file() else {}
    notes, rows = {}, []
    for paper in cached_papers():
        if only and only not in paper.key:
            continue
        if not paper.qp_path or not paper.ms_path:
            notes[paper.key] = "HELD: missing source"
            continue
        try:
            proved, why = stage_and_prove(paper, BASE / "segments", ROOT, decisions)
        except (ValueError, RuntimeError, IndexError) as exc:
            proved, why = [], f"cut failed: {exc}"
        if not proved:
            notes[paper.key] = f"HELD: {why}"
            print(f"  {paper.key:22} HELD  {why}", flush=True)
            continue
        ok = sum(r["verdict"] in PUBLISHABLE for r in proved)
        notes[paper.key] = f"{ok}/{len(proved)} proven"
        flag = "" if ok == len(proved) else "  <-- " + "; ".join(
            f"q{r['question']}:{r['verdict']} {r['detail']}" for r in proved if r["verdict"] not in PUBLISHABLE)
        print(f"  {paper.key:22} {ok:2}/{len(proved):2}{flag}", flush=True)
        rows += proved
    if only:
        previous = json.loads((BASE / "verdicts.json").read_text(encoding="utf-8"))
        notes = {**previous["papers"], **notes}
        rows = [r for r in previous["rows"] if only not in r["paper"]] + rows
    result = {"scope": "0625 Paper 42 + 62; complete questions; six syllabus topics",
              "chapters": CHAPTERS, "papers": dict(sorted(notes.items())),
              "rows": sorted(rows, key=lambda r: (r["paper"], r["question"]))}
    (BASE / "verdicts.json").write_text(json.dumps(result, indent=1), encoding="utf-8")
    print(f"{CODE}: {dict(Counter(r['verdict'] for r in rows))}; "
          f"{sum(v.startswith('HELD') for v in notes.values())} papers held")


def _text(path: Path) -> str:
    with fitz.open(path) as doc:
        return "\n".join(page.get_text() for page in doc)


def dump() -> None:
    """One review file per paper: each question's text and its scheme, for reading."""
    verdicts = json.loads((BASE / "verdicts.json").read_text(encoding="utf-8"))
    by_paper = defaultdict(list)
    for row in verdicts["rows"]:
        if row["verdict"] in PUBLISHABLE:
            by_paper[row["paper"]].append(row)
    out = BASE / "review"
    out.mkdir(exist_ok=True)
    for paper, rows in by_paper.items():
        chunks = []
        for row in rows:
            qp = " ".join(_text(ROOT / row["qp"]).split())
            ms = " ".join(_text(ROOT / row["ms"]).split())
            chunks.append(f"### {paper}|{row['question']} [{row['marks']} marks]\n"
                          f"qp_sha256={sha256(ROOT / row['qp'])} ms_sha256={sha256(ROOT / row['ms'])}\n"
                          f"QP: {qp}\nMS: {ms}\n")
        (out / f"{paper}.txt").write_text("\n".join(chunks), encoding="utf-8")
    print(f"{sum(len(r) for r in by_paper.values())} questions dumped to {out}")


def validate_read(row: dict, read: dict) -> list[str]:
    problems = []
    tags = read.get("topics")
    if not isinstance(tags, list) or not tags or any(t not in CHAPTERS for t in tags) \
            or len(tags) != len(set(tags)):
        problems.append("invalid chapter tags")
    if read.get("difficulty") not in DIFFICULTIES:
        problems.append("invalid difficulty")
    if not str(read.get("reason", "")).strip():
        problems.append("missing reason")
    for kind in ("qp", "ms"):
        if read.get(f"{kind}_sha256") != sha256(ROOT / row[kind]):
            problems.append(f"stale {kind} read")
    return problems


def audit() -> int:
    verdicts_file, reads_file = BASE / "verdicts.json", BASE / "topic_reads.json"
    verdicts = json.loads(verdicts_file.read_text(encoding="utf-8"))
    reads = json.loads(reads_file.read_text(encoding="utf-8"))
    rows = [r for r in verdicts["rows"] if r["verdict"] in PUBLISHABLE]
    failures = []
    by_paper = defaultdict(list)
    for row in rows:
        by_paper[row["paper"]].append(row)
        key = f"{row['paper']}|{row['question']}"
        if key not in reads:
            failures.append(f"{key}: no chapter read")
            continue
        failures += [f"{key}: {p}" for p in validate_read(row, reads[key])]
    for paper, items in by_paper.items():
        numbers = sorted(r["question"] for r in items)
        if numbers != list(range(1, len(numbers) + 1)):
            failures.append(f"{paper}: questions {numbers} are not 1..N")
        total = sum(r["marks"] for r in items)
        if total != PAPER_MARKS[paper.split("_P")[1][0]]:
            failures.append(f"{paper}: marks add to {total}")
    hashes = Counter(sha256(ROOT / r[k]) for r in rows for k in ("qp", "ms"))
    failures += [f"duplicate PDF {h[:12]}" for h, n in hashes.items() if n > 1]
    extra = sorted(set(reads) - {f"{r['paper']}|{r['question']}" for r in rows})
    failures += [f"{k}: read for a question that is not proven" for k in extra]
    chapters = Counter(t for r in rows for t in reads.get(f"{r['paper']}|{r['question']}", {}).get("topics", []))
    result = {"questions": len(rows), "papers": len(by_paper), "failures": failures,
              "chapters": dict(sorted(chapters.items())),
              "difficulty": dict(Counter(reads[k]["difficulty"] for k in reads if k not in extra)),
              "verdicts_sha256": sha256(verdicts_file), "reads_sha256": sha256(reads_file)}
    (BASE / "artifact_audit.json").write_text(json.dumps(result, indent=1), encoding="utf-8")
    print(json.dumps({k: v for k, v in result.items() if k != "failures"}, indent=1))
    print(f"{len(failures)} failures", *failures[:40], sep="\n  ")
    return 1 if failures else 0


def merge_reads() -> None:
    """Combine reads/*.json (one file per reading batch) into topic_reads.json."""
    merged: dict[str, dict] = {}
    for path in sorted((BASE / "reads").glob("*.json")):
        batch = json.loads(path.read_text(encoding="utf-8"))
        clash = sorted(set(batch) & set(merged))
        if clash:
            raise SystemExit(f"{path.name} repeats reads for {clash[:5]}")
        merged.update(batch)
    fields = ("topics", "difficulty", "reason", "has_diagram", "qp_sha256", "ms_sha256")
    ordered = {k: {f: merged[k][f] for f in fields if f in merged[k]} for k in sorted(merged)}
    (BASE / "topic_reads.json").write_text(json.dumps(ordered, indent=1, ensure_ascii=False) + "\n",
                                           encoding="utf-8")
    print(f"{len(ordered)} reads -> topic_reads.json")


def marks() -> None:
    """src/lib/printedMarks/0625.json: each proven question's printed [Total: X]."""
    verdicts = json.loads((BASE / "verdicts.json").read_text(encoding="utf-8"))
    table = {f"{r['paper_id']}|{r['question']}": r["marks"]
             for r in verdicts["rows"] if r["verdict"] in PUBLISHABLE}
    out = ROOT / "src" / "lib" / "printedMarks" / f"{CODE}.json"
    out.write_text(json.dumps(dict(sorted(table.items())), indent=0) + "\n", encoding="utf-8")
    print(f"{len(table)} question marks -> {out.relative_to(ROOT)}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=["sources", "stage", "dump", "merge-reads", "audit", "marks"])
    parser.add_argument("--only", help="restage papers whose key contains this text")
    args = parser.parse_args()
    if args.command == "sources":
        sources()
    elif args.command == "stage":
        stage(args.only)
    elif args.command == "dump":
        dump()
    elif args.command == "marks":
        marks()
    elif args.command == "merge-reads":
        merge_reads()
    else:
        return audit()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
