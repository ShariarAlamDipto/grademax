#!/usr/bin/env python3
"""
Phase 3 for the IAL Statistics 1 (WST01) workbook: assign every question
a primary taxonomy section, plus any secondary sections it also drills.

    python scripts/classify_s1_workbook_sections.py --check-taxonomy
    python scripts/classify_s1_workbook_sections.py              # pass 1
    python scripts/classify_s1_workbook_sections.py --second-pass
    python scripts/classify_s1_workbook_sections.py --report
    python scripts/classify_s1_workbook_sections.py --report --write

Reads `data/workbook/s1_questions.json`; caches to
`s1_classification_cache.json` (pass 1) and `s1_classification_second.json`
(pass 2). Both resume from cache, so an interrupted run costs nothing.

MULTI-LABEL IS NOT A NICETY, IT IS WHAT FIXES THE SKEW
------------------------------------------------------
Single-tagging put 111 of 431 4PM1 questions into one chapter. Multi-label
spread them into a usable distribution, and 86% of questions carried a
secondary section -- that is the mechanism that fixed it, not a better prompt.

WHAT THIS SUBJECT'S TAXONOMY DEPENDS ON
---------------------------------------
Measured over the 28 WST01 papers:

1. **Topic 1 is never a standalone question.** "Mathematical models in
   probability and statistics" is examined as the "comment on the suitability of
   this model" tail of a question about something else, so 1.1 should almost
   always be a SECONDARY label, never the primary one.
2. **Nearly every question computes a mean or a standard deviation**, because
   that is how statistics questions are built. Section 2.1 is for questions
   whose own subject is the summary statistic; where the mean is a step towards
   a regression line or a Normal probability, the destination section wins.
3. **The discrete uniform distribution (5.3) is named in only 2 of 28 papers.**
   It is kept because it is an explicit specification statement, and it is
   expected to stay thin rather than being filled by over-eager matching.
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
QUESTIONS_PATH = REPO_ROOT / "data" / "workbook" / "s1_questions.json"
CACHE_PATH = REPO_ROOT / "data" / "workbook" / "s1_classification_cache.json"
SECOND_CACHE_PATH = REPO_ROOT / "data" / "workbook" / "s1_classification_second.json"
MERGED_PATH = REPO_ROOT / "data" / "workbook" / "s1_classifications.json"

SUBJECT_CODE = "WST01"

RULES = """
DISAMBIGUATION RULES -- these override any general impression:

* 1.1 is almost never the primary. Use it as a SECONDARY label when a question
  ends by asking whether a model or distribution is suitable. Choose 1.1 as
  primary only if the whole question is about modelling assumptions.
* Almost every question computes a mean, a standard deviation or a probability.
  Ask what the question is FOR:
  - summarising or comparing data sets themselves        -> 2.1
  - a change of variable y = (x - a)/b to ease arithmetic -> 2.2
  - finding a median, quartile or percentile from grouped data by interpolation
                                                          -> 2.3
  - drawing or reading a histogram, or frequency density  -> 2.4
  - a stem and leaf diagram or a box plot                 -> 2.5
  - skewness, outliers, or comparing two distributions    -> 2.6
* Correlation and regression: computing Sxx/Sxy or drawing a scatter diagram is
  4.1; the product moment correlation coefficient and its interpretation is 4.2;
  finding or using the regression line, predicting, and coded regression is 4.3.
* Probability: use 3.2 for a question whose work is a Venn diagram, 3.3 for
  conditional probability or testing independence, and 3.4 for tree diagrams and
  sampling with or without replacement. Use 3.1 only for plain sample-space or
  addition-law work that fits none of those.
* A discrete random variable question is 5.1 when the work is the probability
  distribution or F(x), and 5.2 when it is E(X), E(X^2) or Var(X). Use 5.3 ONLY
  if the question names a discrete uniform distribution.
* A Normal question is 6.1 when it standardises and reads tables, and 6.2 when
  an unknown mean or standard deviation must be found, usually via simultaneous
  equations.
"""

def system_prompt(taxonomy: dict[str, str]) -> str:
    return f"""You classify Edexcel International A Level Statistics 1 (WST01) exam questions into workbook sections.

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
    return sections_from_migration(migration)


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
    print(f"=== S1 classification [{label}] model={model} ===")
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
    print(f"=== S1 classification report ===\n")
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
