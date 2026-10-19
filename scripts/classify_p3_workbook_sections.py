#!/usr/bin/env python3
"""
Phase 3 for the IAL Pure Mathematics 3 (WMA13) workbook: assign every question
a primary taxonomy section, plus any secondary sections it also drills.

    python scripts/classify_p3_workbook_sections.py --check-taxonomy
    python scripts/classify_p3_workbook_sections.py              # pass 1
    python scripts/classify_p3_workbook_sections.py --second-pass
    python scripts/classify_p3_workbook_sections.py --report
    python scripts/classify_p3_workbook_sections.py --report --write

Reads `data/workbook/p3_questions.json`; caches to
`p3_classification_cache.json` (pass 1) and `p3_classification_second.json`
(pass 2). Both resume from cache, so an interrupted run costs nothing.

MULTI-LABEL IS NOT A NICETY, IT IS WHAT FIXES THE SKEW
------------------------------------------------------
Single-tagging put 111 of 431 4PM1 questions into one chapter. Multi-label
spread them into a usable distribution, and 86% of questions carried a
secondary section -- that is the mechanism that fixed it, not a better prompt.

WHAT THIS UNIT'S TAXONOMY DEPENDS ON
-----------------------------------
The disambiguation rules below are the load-bearing part. Without them a topic
that appears as the SETTING of most questions absorbs the book -- the failure
mode 4PM1 hit with one chapter taking 111 of 431 questions, and the reason P4
scopes parametric equations explicitly. See RULES.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).resolve().parent))

from lib.ial_classify import (  # noqa: E402
    BATCH_SIZE,
    PRIMARY_MODEL,
    SECOND_MODEL,
    classify_batch,
    latest_section_migration,
    load_cache,
    review_priority,
    sections_from_migration,
    taxonomy_block,
    write_json_atomically,
)

REPO_ROOT = Path(__file__).resolve().parent.parent
QUESTIONS_PATH = REPO_ROOT / "data" / "workbook" / "p3_questions.json"
CACHE_PATH = REPO_ROOT / "data" / "workbook" / "p3_classification_cache.json"
SECOND_CACHE_PATH = REPO_ROOT / "data" / "workbook" / "p3_classification_second.json"
MERGED_PATH = REPO_ROOT / "data" / "workbook" / "p3_classifications.json"

SUBJECT_CODE = "WMA13"

RULES = """
DISAMBIGUATION RULES -- these override any general impression:

* 1.2 is domain, range and composition; 1.3 is specifically an INVERSE function
  or its graph. A question doing both takes its primary from where the marks are.
* The modulus function is 1.4, including |f(x)| sketches and solving
  |ax + b| = c -- not 1.5, even though a transformation is involved.
* 1.5 is a COMBINED transformation of a named curve.
* Trigonometry: 2.1 for sec/cosec/cot and arcsin/arccos/arctan, 2.2 for proving
  an identity, 2.3 for compound or double angle formulae, and 2.4 ONLY when
  a cos t + b sin t is written as r cos (t +- a) or r sin (t +- a), or an
  equation of that form is solved.
* 3.3 is using a LOGARITHMIC GRAPH to estimate parameters of y = ax^n or
  y = kb^x -- a plot of log y against log x or against x. Ordinary
  exponential-equation solving is 3.2.
* Differentiation: 4.2 when the product, quotient or chain rule is the point;
  4.1 for the standard derivatives themselves; 4.3 for exponential growth and
  decay in context.
* Numerical methods are 6.1 (change of sign locating a root) and 6.2 (iteration
  or a recurrence). These exist in NO other pure unit, so a question about
  iteration belongs here and nowhere else.
"""

def system_prompt(taxonomy: dict[str, str]) -> str:
    return f"""You classify Edexcel International A Level Pure Mathematics 3 (WMA13) exam questions into workbook sections.

SECTIONS:
{taxonomy_block(taxonomy)}
{RULES}
For each question return the single best `primary` section, and any `secondary`
sections the question also genuinely drills. Most questions have at least one
secondary. Use ONLY section codes from the list above.

Return ONLY a JSON array, one object per question, no prose and no code fence:
[{{"id": "<the id given>", "primary": "6.3", "secondary": ["5.3"]}}]
"""


def load_questions() -> list[dict]:
    if not QUESTIONS_PATH.exists():
        raise SystemExit(f"{QUESTIONS_PATH} missing -- run the enricher first")
    return json.loads(QUESTIONS_PATH.read_text(encoding="utf-8"))


def load_taxonomy() -> dict[str, str]:
    migration = latest_section_migration(SUBJECT_CODE)
    if migration is None:
        raise SystemExit(f"no migration seeds workbook_sections for {SUBJECT_CODE}")
    return sections_from_migration(migration, SUBJECT_CODE)


def check_taxonomy() -> int:
    migration = latest_section_migration(SUBJECT_CODE)
    print(f"taxonomy source: {migration.relative_to(REPO_ROOT) if migration else None}")
    taxonomy = load_taxonomy()
    print(f"{len(taxonomy)} sections")
    for code, title in sorted(taxonomy.items(), key=lambda kv: [int(p) for p in kv[0].split(".")]):
        print(f"  {code:6s} {title}")
    return 0


def run_pass(model: str, cache_path: Path, label: str) -> int:
    load_dotenv(REPO_ROOT / ".env.local")
    questions = load_questions()
    taxonomy = load_taxonomy()
    cache = load_cache(cache_path)

    todo = [q for q in questions if q["slug"] not in cache]
    print(f"=== P3 classification [{label}] model={model} ===")
    print(f"{len(questions)} questions, {len(cache)} cached, {len(todo)} to do\n")

    prompt = system_prompt(taxonomy)
    for index in range(0, len(todo), BATCH_SIZE):
        batch = todo[index : index + BATCH_SIZE]
        result = classify_batch(batch, prompt, taxonomy, model)
        cache.update(result)
        write_json_atomically(cache_path, cache)
        got = len(result)
        print(
            f"  batch {index // BATCH_SIZE + 1:3d}: {got}/{len(batch)} classified "
            f"({len(cache)}/{len(questions)} total)",
            flush=True,
        )
        if got == 0:
            print("    !! empty batch -- model returned nothing usable")

    print(f"\ncached {len(cache)}/{len(questions)}")
    return 0


def report(write: bool) -> int:
    questions = load_questions()
    taxonomy = load_taxonomy()
    first = load_cache(CACHE_PATH)
    second = load_cache(SECOND_CACHE_PATH)

    priorities: dict[str, int] = {}
    per_section: dict[str, int] = {}
    per_chapter: dict[str, int] = {}
    models: dict[str, int] = {}
    with_secondary = 0
    merged: list[dict] = []

    for question in questions:
        slug = question["slug"]
        primary = first.get(slug)
        opinion = second.get(slug)
        priority = review_priority(primary, opinion)
        priorities[priority] = priorities.get(priority, 0) + 1

        if primary:
            per_section[primary["primary"]] = per_section.get(primary["primary"], 0) + 1
            chapter = primary["primary"].split(".")[0]
            per_chapter[chapter] = per_chapter.get(chapter, 0) + 1
            models[primary.get("model", "?")] = models.get(primary.get("model", "?"), 0) + 1
            if primary["secondary"]:
                with_secondary += 1

        merged.append(
            {
                "slug": slug,
                "subject_code": question["subject_code"],
                "section": primary["primary"] if primary else None,
                "secondary_sections": primary["secondary"] if primary else [],
                "proposed_section": opinion["primary"] if opinion else None,
                "review_priority": priority,
                "model": primary.get("model") if primary else None,
                "second_model": opinion.get("model") if opinion else None,
            }
        )

    total = len(questions)
    print(f"=== P3 classification report ===\n")
    print(f"questions        : {total}")
    print(f"models used      : {models}")
    print(f"with a secondary : {with_secondary} ({with_secondary * 100 // max(total, 1)}%)")
    print(f"review priority  : {priorities}")
    print("\nper chapter:")
    for chapter in sorted(per_chapter, key=int):
        print(f"  ch{chapter:>2s}  {per_chapter[chapter]:3d}")
    print(f"\nsections used    : {len(per_section)}/{len(taxonomy)}")
    empty = sorted(set(taxonomy) - set(per_section), key=lambda c: [int(p) for p in c.split(".")])
    if empty:
        print(f"empty sections   : {empty}")
    print("\nper section:")
    for code in sorted(taxonomy, key=lambda c: [int(p) for p in c.split(".")]):
        print(f"  {code:6s} {per_section.get(code, 0):3d}  {taxonomy[code]}")

    if write:
        write_json_atomically(MERGED_PATH, merged)
        print(f"\nwrote {MERGED_PATH.relative_to(REPO_ROOT)}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check-taxonomy", action="store_true")
    parser.add_argument("--second-pass", action="store_true")
    parser.add_argument("--report", action="store_true")
    parser.add_argument("--write", action="store_true", help="with --report, write the merge")
    args = parser.parse_args()

    if args.check_taxonomy:
        return check_taxonomy()
    if args.report:
        return report(args.write)
    if args.second_pass:
        return run_pass(SECOND_MODEL, SECOND_CACHE_PATH, "pass 2 / second opinion")
    return run_pass(PRIMARY_MODEL, CACHE_PATH, "pass 1")


if __name__ == "__main__":
    sys.exit(main())
