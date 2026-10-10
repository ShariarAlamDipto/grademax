"""
Settle every question's section for an IAL chapterwise book and write it in
print order -- the IAL counterpart of scripts/assign_physics_workbook_sections.py.

  agreed       both classifier passes chose the same primary section
  adjudicated  they disagreed (or a reviewer overrode them): the decision in
               data/workbook/<unit>_adjudications.json, made by reading the
               question, with its reason
  unresolved   disagreement with no adjudication -> the run FAILS and lists
               them, with both opinions and the stem; nothing is guessed

Print order within a section: difficulty (easy, medium, hard), marks, then
chronologically. The book file is data/workbook/<unit>_book.json, which the print
builder (lib/ial_workbook_print.py) reads. Slugs are the inventory's own
("P1.2019_jan.Q001"), so the book, the database and the classifier caches all
name a question the same way.
"""

from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path

from .ial_classify import latest_section_migration, sections_from_migration

ROOT = Path(__file__).resolve().parents[2]
WORKBOOK = ROOT / "data" / "workbook"
SEASON_ORDER = {"jan": 0, "may-jun": 1, "oct-nov": 2}
DIFFICULTY_ORDER = {"easy": 0, "medium": 1, "hard": 2}


def _chapters(subject_code: str) -> list[dict]:
    """Chapter numbers and titles out of the taxonomy migration."""
    import re

    migration = latest_section_migration(subject_code)
    text = migration.read_text(encoding="utf-8")
    out = []
    for chunk in text.split("INSERT INTO workbook_chapters")[1:]:
        head = chunk.split("INSERT INTO workbook_sections")[0]
        if f"'{subject_code}'" not in head:
            continue
        for number, title in re.findall(r"\((\d+),\s*'((?:[^']|'')+)',\s*'[^']*'\)", head):
            out.append({"number": int(number), "title": title.replace("''", "'")})
    return out


def settle(unit: str, subject_code: str, execute: bool, show_disputes: bool) -> int:
    questions = json.loads((WORKBOOK / f"{unit}_questions.json").read_text(encoding="utf-8"))
    first = json.loads((WORKBOOK / f"{unit}_classification_cache.json").read_text(encoding="utf-8"))
    second = json.loads((WORKBOOK / f"{unit}_classification_second.json").read_text(encoding="utf-8"))
    adj_path = WORKBOOK / f"{unit}_adjudications.json"
    adjudications = json.loads(adj_path.read_text(encoding="utf-8")) if adj_path.is_file() else {}
    taxonomy = sections_from_migration(latest_section_migration(subject_code), subject_code)
    valid = set(taxonomy)

    slugs = {q["slug"] for q in questions}
    stale = sorted(set(adjudications) - slugs)
    if stale:
        raise SystemExit(f"adjudications name questions not in the book: {stale}")

    rows, unresolved, counts = [], [], {"agreed": 0, "adjudicated": 0, "unresolved": 0}
    for q in questions:
        slug = q["slug"]
        a, b = first.get(slug), second.get(slug)
        if slug in adjudications:
            ruling = adjudications[slug]
            if ruling["primary"] not in valid:
                raise SystemExit(f"{slug}: adjudicated {ruling['primary']} not in the taxonomy")
            section = ruling["primary"]
            secondary = [c for c in ruling.get("secondary", []) if c in valid and c != section]
            how, reason = "adjudicated", ruling.get("reason")
        elif a and b and a["primary"] == b["primary"] and a["primary"] in valid:
            section = a["primary"]
            secondary = list(dict.fromkeys(c for c in a.get("secondary", []) + b.get("secondary", [])
                                           if c in valid and c != section))
            how, reason = "agreed", None
        else:
            counts["unresolved"] += 1
            unresolved.append((q, a, b))
            continue
        counts[how] += 1
        rows.append({**q, "section": section, "secondary_sections": secondary[:3],
                     "settled_by": how, "adjudication_reason": reason,
                     "first_opinion": a, "second_opinion": b})

    print(f"=== {unit.upper()} ({subject_code}) section settlement ===")
    print(f"  questions   : {len(questions)}")
    for key, value in counts.items():
        print(f"  {key:<11} : {value}")

    if unresolved or show_disputes:
        for q, a, b in unresolved:
            parts = ", ".join(f"{p.get('label')}:{p.get('marks')}" for p in (q.get("sub_parts") or []))
            print(f"\n  {q['slug']} [{q['marks']}m; {parts}] "
                  f"A={a and a['primary']} {a and a.get('secondary')}  "
                  f"B={b and b['primary']} {b and b.get('secondary')}")
            print(f"    {' '.join(q.get('stem', '').split())[:900]}")
    if unresolved:
        print(f"\n  {len(unresolved)} unresolved -- add them to {adj_path.name} first. Not written.")
        return 1

    by_section: dict[str, list[dict]] = defaultdict(list)
    for row in rows:
        by_section[row["section"]].append(row)
    ordered = []
    for code in sorted(by_section, key=lambda c: [int(p) for p in c.split(".")]):
        group = sorted(by_section[code], key=lambda r: (
            DIFFICULTY_ORDER.get(r["difficulty"], 1), r["marks"], r["year"],
            SEASON_ORDER.get(r["season"], 9), r["source_question_number"]))
        for ordinal, row in enumerate(group, 1):
            row["ordinal"] = ordinal
            ordered.append(row)

    print("\n  questions per section")
    for code in sorted(taxonomy, key=lambda c: [int(p) for p in c.split(".")]):
        print(f"    {code:<5} {taxonomy[code][:56]:<56} {len(by_section.get(code, [])):>3}")

    if execute:
        chapters = _chapters(subject_code)
        sections = [{"chapter": int(c.split(".")[0]), "number": int(c.split(".")[1]),
                     "title": t} for c, t in taxonomy.items()]
        payload = {"subject": subject_code, "unit": unit, "chapters": chapters,
                   "sections": sections, "questions": ordered}
        target = WORKBOOK / f"{unit}_book.json"
        target.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"\n  written: {target.relative_to(ROOT)} ({len(ordered)} questions)")
    else:
        print("\n  report only -- re-run with --execute to write")
    return 0
