"""
Settle every Physics workbook question's section and write the book's order.

Reads the two classifier passes (data/workbook/physics_classifications.json,
written by classify_physics_workbook_sections.py --report --write) and the
ADJUDICATIONS file, and writes data/workbook/physics_book.json, which
build_physics_workbook_print.py and load_physics_workbook_to_db.py both read.

HOW A SECTION IS SETTLED
------------------------
  agreed        both models chose the same primary section -> taken as is
  adjudicated   the models disagreed (or a reviewer overrode an agreement) ->
                the decision recorded in physics_adjudications.json, made by
                reading the question, with a one-line reason
  unresolved    disagreement with no adjudication -> the run FAILS and lists
                them; nothing is guessed

A model's self-reported confidence is never used to break a tie -- measured on
FPM, Maths B and Maths A, it carries no signal.

PRINT ORDER
-----------
Within a section: difficulty band (easy, medium, hard), then marks, then the
paper chronologically, then question number. A student meets the section's
short questions first and the long multi-part ones last.

Slugs (PHY.CH01.S02.Q007) are issued from that order. The database loader keeps
a slug once issued, so re-running this after the book has been loaded does not
renumber anything a student's progress points at.

USAGE
-----
    python scripts/assign_physics_workbook_sections.py            # report only
    python scripts/assign_physics_workbook_sections.py --execute
    python scripts/assign_physics_workbook_sections.py --disputes # list them
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
CLASSIFIED = REPO_ROOT / "data" / "workbook" / "physics_classifications.json"
ADJUDICATIONS = REPO_ROOT / "data" / "workbook" / "physics_adjudications.json"
BOOK = REPO_ROOT / "data" / "workbook" / "physics_book.json"

sys.path.insert(0, str(Path(__file__).resolve().parent))
from apply_physics_workbook_taxonomy import MIGRATION, parse_migration  # noqa: E402

SEASON_ORDER = {"jan": 0, "may-jun": 1, "oct-nov": 2}
DIFFICULTY_ORDER = {"easy": 0, "medium": 1, "hard": 2}


def question_id(question: dict) -> str:
    return f"{question['paper_key']}:{question['question_number']}"


def load_adjudications() -> dict[str, dict]:
    if not ADJUDICATIONS.is_file():
        return {}
    return json.loads(ADJUDICATIONS.read_text(encoding="utf-8"))


def settle(question: dict, adjudications: dict[str, dict],
           valid: set[str]) -> tuple[dict | None, str]:
    """(decision, how) where decision = {primary, secondary}."""
    key = question_id(question)
    first = question.get("classification")
    second = question.get("second_opinion")

    if key in adjudications:
        ruling = adjudications[key]
        primary = ruling["primary"]
        if primary not in valid:
            raise SystemExit(f"{key}: adjudicated section {primary} is not in the taxonomy")
        secondary = [c for c in ruling.get("secondary", []) if c in valid and c != primary]
        return {"primary": primary, "secondary": secondary[:3],
                "reason": ruling.get("reason", "")}, "adjudicated"

    if first and second and first["primary"] == second["primary"]:
        merged = [c for c in first["secondary"] + second["secondary"]
                  if c != first["primary"]]
        secondary = list(dict.fromkeys(merged))[:3]
        return {"primary": first["primary"], "secondary": secondary}, "agreed"

    return None, "unresolved"


def sort_key(row: dict) -> tuple:
    year, season, _ = row["source_paper_key"].split("_")
    return (DIFFICULTY_ORDER[row["difficulty"]], row["marks"], int(year),
            SEASON_ORDER.get(season, 9), row["source_paper_key"],
            row["source_question_number"])


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute", action="store_true", help="write physics_book.json")
    parser.add_argument("--disputes", action="store_true",
                        help="print every unresolved question with both opinions")
    args = parser.parse_args()

    chapters, sections = parse_migration(MIGRATION)
    valid = {f"{s['chapter_number']}.{s['number']}" for s in sections}
    questions = json.loads(CLASSIFIED.read_text(encoding="utf-8"))
    adjudications = load_adjudications()

    stale = set(adjudications) - {question_id(q) for q in questions}
    if stale:
        raise SystemExit(f"adjudications name questions that do not exist: {sorted(stale)}")

    rows: list[dict] = []
    unresolved: list[dict] = []
    how_counts: Counter = Counter()

    for question in questions:
        decision, how = settle(question, adjudications, valid)
        how_counts[how] += 1
        if decision is None:
            unresolved.append(question)
            continue
        first = question.get("classification") or {}
        rows.append({
            "section": decision["primary"],
            "secondary_sections": decision["secondary"],
            "settled_by": how,
            "adjudication_reason": decision.get("reason"),
            "archetype": first.get("archetype", ""),
            "marks": question["marks"],
            "difficulty": question["difficulty"],
            "source_paper_key": question["paper_key"],
            "source_question_number": question["question_number"],
            "spec": question.get("spec"),
            "qp_pdf": question["qp_pdf"],
            "ms_pdf": question["ms_pdf"],
            "sub_parts": question.get("sub_parts"),
            "stem": question["stem"],
            "text_status": question["text_status"],
            "classification": question.get("classification"),
            "second_opinion": question.get("second_opinion"),
        })

    print(f"{'=' * 74}\nPHYSICS WORKBOOK — SECTION SETTLEMENT\n{'=' * 74}")
    print(f"  questions        : {len(questions)}")
    for how in ("agreed", "adjudicated", "unresolved"):
        print(f"  {how:<16} : {how_counts.get(how, 0)}")

    if args.disputes or unresolved:
        print(f"\n  {len(unresolved)} unresolved:")
        for q in unresolved:
            a, b = q.get("classification") or {}, q.get("second_opinion") or {}
            print(f"\n  {question_id(q)}  ({q['marks']} marks)  "
                  f"A={a.get('primary')} {a.get('secondary')}  "
                  f"B={b.get('primary')} {b.get('secondary')}")
            print(f"    {q['stem'][:700]}")
    if unresolved:
        print("\n  Not written: every disagreement needs an adjudication first.")
        return 1

    # Order, then number.
    by_section: dict[str, list[dict]] = defaultdict(list)
    for row in rows:
        by_section[row["section"]].append(row)
    ordered: list[dict] = []
    for code in sorted(by_section, key=lambda c: [int(p) for p in c.split(".")]):
        chapter, section = (int(p) for p in code.split("."))
        for ordinal, row in enumerate(sorted(by_section[code], key=sort_key), 1):
            row["ordinal"] = ordinal
            row["slug"] = f"PHY.CH{chapter:02}.S{section:02}.Q{ordinal:03}"
            ordered.append(row)

    print("\n  Questions per section")
    for chapter in chapters:
        codes = [f"{chapter['number']}.{s['number']}" for s in sections
                 if s["chapter_number"] == chapter["number"]]
        total = sum(len(by_section.get(c, [])) for c in codes)
        print(f"    {chapter['number']}  {chapter['title']:<40} {total:>4}")
        for code in codes:
            title = next(s["title"] for s in sections
                         if f"{s['chapter_number']}.{s['number']}" == code)
            print(f"        {code:<5} {title[:52]:<52} {len(by_section.get(code, [])):>3}")

    empty = sorted(valid - set(by_section), key=lambda c: [int(p) for p in c.split(".")])
    if empty:
        print(f"\n  sections with no questions (the book skips them): {', '.join(empty)}")

    if args.execute:
        payload = {
            "subject": "4PH1",
            "chapters": [{"number": c["number"], "title": c["title"]} for c in chapters],
            "sections": [{"chapter": s["chapter_number"], "number": s["number"],
                          "title": s["title"]} for s in sections],
            "questions": ordered,
        }
        BOOK.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"\n  written: {BOOK.relative_to(REPO_ROOT)}  ({len(ordered)} questions)")
    else:
        print("\n  Report only -- re-run with --execute to write.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
