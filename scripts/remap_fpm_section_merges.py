"""
One-off: remap already-classified FPM questions onto the merged section numbers.

Migration 13 merged six redundant sections and renumbered the rest contiguously
(47 -> 41). The 423 questions classified before that carry the OLD codes, and
re-running classification to pick up new numbers would waste the work and, worse,
churn assignments that were already fine.

The mapping is a pure renumbering plus six merges, so it can be applied
mechanically:

    1.3->1.2  1.4->1.3
    5.3->5.2  5.4->5.3
    6.2->6.1  6.3->6.2  6.4->6.2
    8.3->8.2  8.4->8.3  8.5->8.4
    9.7->9.6  9.8->9.7

Applies to both classification passes and the merged output. Idempotent: codes
already in the new scheme are left alone, so a second run is a no-op.

USAGE
-----
    python scripts/remap_fpm_section_merges.py            # dry run
    python scripts/remap_fpm_section_merges.py --execute
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
WORKBOOK_DIR = REPO_ROOT / "data" / "workbook"

CACHE_PATH = WORKBOOK_DIR / "fpm_classification_cache.json"
SECOND_PATH = WORKBOOK_DIR / "fpm_classification_second.json"
MERGED_PATH = WORKBOOK_DIR / "fpm_classifications.json"
ARCHETYPES_PATH = WORKBOOK_DIR / "fpm_archetypes.json"

# Old code -> new code. Codes absent from this map are unchanged.
SECTION_REMAP: dict[str, str] = {
    "1.3": "1.2",
    "1.4": "1.3",
    "5.3": "5.2",
    "5.4": "5.3",
    "6.2": "6.1",
    "6.3": "6.2",
    "6.4": "6.2",
    "8.3": "8.2",
    "8.4": "8.3",
    "8.5": "8.4",
    "9.7": "9.6",
    "9.8": "9.7",
}

# The 41 sections after migration 13 -- anything outside this is a bug.
VALID_SECTIONS = frozenset(
    [f"1.{i}" for i in range(1, 4)]
    + [f"2.{i}" for i in range(1, 5)]
    + [f"3.{i}" for i in range(1, 5)]
    + [f"4.{i}" for i in range(1, 5)]
    + [f"5.{i}" for i in range(1, 4)]
    + [f"6.{i}" for i in range(1, 3)]
    + [f"7.{i}" for i in range(1, 5)]
    + [f"8.{i}" for i in range(1, 5)]
    + [f"9.{i}" for i in range(1, 8)]
    + [f"10.{i}" for i in range(1, 7)]
)


def remap(code: str) -> str:
    return SECTION_REMAP.get(code, code)


def remap_result(result: dict | None) -> tuple[dict | None, int]:
    """Remap one classification. Returns (result, codes_changed)."""
    if not result:
        return result, 0

    changed = 0
    primary = remap(result["primary"])
    changed += primary != result["primary"]

    secondary: list[str] = []
    for code in result.get("secondary") or []:
        new_code = remap(code)
        changed += new_code != code
        # A merge can collapse a secondary onto the primary, or onto another
        # secondary. Drop the duplicate rather than carry it twice.
        if new_code != primary and new_code not in secondary:
            secondary.append(new_code)

    return {**result, "primary": primary, "secondary": secondary}, changed


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else None


def write_atomically(path: Path, payload: object) -> None:
    temp_path = path.with_suffix(path.suffix + ".tmp")
    temp_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    temp_path.replace(path)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute", action="store_true", help="write the remapped files")
    args = parser.parse_args()

    total_changed = 0
    invalid: Counter = Counter()
    distribution: Counter = Counter()
    outputs: list[tuple[Path, object]] = []

    for path in (CACHE_PATH, SECOND_PATH):
        data = load(path)
        if data is None:
            print(f"  skip (missing): {path.name}")
            continue

        changed = 0
        remapped = {}
        for key, result in data.items():
            new_result, delta = remap_result(result)
            changed += delta
            remapped[key] = new_result
            if path == CACHE_PATH:
                distribution[new_result["primary"]] += 1
            for code in [new_result["primary"], *new_result["secondary"]]:
                if code not in VALID_SECTIONS:
                    invalid[code] += 1

        total_changed += changed
        outputs.append((path, remapped))
        print(f"  {path.name:<40} {len(remapped):>4} entries, {changed:>3} codes remapped")

    merged = load(MERGED_PATH)
    if merged is not None:
        changed = 0
        for question in merged:
            question["classification"], delta = remap_result(question.get("classification"))
            changed += delta
            question["second_opinion"], delta = remap_result(question.get("second_opinion"))
            changed += delta
        total_changed += changed
        outputs.append((MERGED_PATH, merged))
        print(f"  {MERGED_PATH.name:<40} {len(merged):>4} entries, {changed:>3} codes remapped")

    archetypes = load(ARCHETYPES_PATH)
    if archetypes is not None:
        changed = 0
        for cluster in archetypes:
            new_section = remap(cluster["section"])
            changed += new_section != cluster["section"]
            cluster["section"] = new_section
        total_changed += changed
        outputs.append((ARCHETYPES_PATH, archetypes))
        print(f"  {ARCHETYPES_PATH.name:<40} {len(archetypes):>4} clusters, {changed:>3} remapped")

    print(f"\n  total codes remapped : {total_changed}")

    if invalid:
        print(f"  INVALID CODES        : {dict(invalid)}")
        print("  Refusing to write -- these are not sections in the merged taxonomy.")
        return 1

    empty = sorted(VALID_SECTIONS - set(distribution), key=lambda c: [int(p) for p in c.split(".")])
    print(f"  sections now used    : {len(distribution)} of {len(VALID_SECTIONS)}")
    print(f"  still empty          : {', '.join(empty) if empty else 'none'}")

    if args.execute:
        for path, payload in outputs:
            write_atomically(path, payload)
        print(f"\n  written: {len(outputs)} file(s)")
    else:
        print("\n  Dry run -- nothing written. Re-run with --execute.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
