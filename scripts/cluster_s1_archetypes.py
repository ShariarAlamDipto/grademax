#!/usr/bin/env python3
"""
Phase 3 for S1 (WST01): group classified questions into recurring archetypes.

    python scripts/cluster_s1_archetypes.py              # dry run
    python scripts/cluster_s1_archetypes.py --execute
    python scripts/cluster_s1_archetypes.py --threshold 0.38   # to compare

Reads `s1_questions.json` and `s1_classification_cache.json`, writes
`s1_archetypes.json`. Deterministic: no model is involved, so a re-run after
re-segmentation produces the same book.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from lib.ial_archetypes import DEFAULT_THRESHOLD, cluster_questions  # noqa: E402
from lib.ial_classify import (  # noqa: E402
    latest_section_migration,
    sections_from_migration,
    write_json_atomically,
)

REPO_ROOT = Path(__file__).resolve().parent.parent
QUESTIONS_PATH = REPO_ROOT / "data" / "workbook" / "s1_questions.json"
CACHE_PATH = REPO_ROOT / "data" / "workbook" / "s1_classification_cache.json"
OUTPUT_PATH = REPO_ROOT / "data" / "workbook" / "s1_archetypes.json"
#: 0.32, matching P4 for consistency -- but see lib/ial_archetypes.py:
#: WST01 clusters weakly for a STRUCTURAL reason, not a tuning one. Its
#: questions share a statistical shape while their wording is contextual, so
#: most come out as singletons and the SECTION carries the pattern instead.
THRESHOLD = 0.32

SUBJECT_CODE = "WST01"
UNIT = "S1"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--threshold", type=float, default=THRESHOLD)
    args = parser.parse_args()

    questions = json.loads(QUESTIONS_PATH.read_text(encoding="utf-8"))
    cache = json.loads(CACHE_PATH.read_text(encoding="utf-8"))
    taxonomy = sections_from_migration(latest_section_migration(SUBJECT_CODE))
    section_of = {slug: entry["primary"] for slug, entry in cache.items()}

    archetypes = cluster_questions(questions, section_of, args.threshold)
    clustered = sum(a["size"] for a in archetypes)
    repeated = [a for a in archetypes if a["size"] > 1]
    in_repeat = sum(a["size"] for a in repeated)

    print(f"=== {UNIT} archetypes  threshold={args.threshold} ===\n")
    print(f"questions clustered : {clustered}")
    print(f"archetypes          : {len(archetypes)}")
    print(f"repeated shapes     : {len(repeated)} covering {in_repeat} questions "
          f"({in_repeat * 100 // max(clustered, 1)}%)")
    print(f"singletons          : {len(archetypes) - len(repeated)}")

    print("\nlargest:")
    for a in sorted(archetypes, key=lambda a: -a["size"])[:12]:
        print(f"  {a['section']:6s} x{a['size']:<3d} {taxonomy[a['section']][:34]:36s} {a['label'][:44]}")

    if args.execute:
        write_json_atomically(OUTPUT_PATH, archetypes)
        print(f"\nwrote {OUTPUT_PATH.relative_to(REPO_ROOT)}")
    else:
        print("\nDry run only. Re-run with --execute to write.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
