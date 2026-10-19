"""
Mark-scheme linkage audit for the IAL Biology (WBI11-16) yearwise book.

The checks live in `lib/yearwise_linkage.py`; this names the book and the
specification codes that count as legacy for it. Run
`collect_yearwise_all_sources.py --book ial_biology` first.

    python -X utf8 scripts/audit_ial_biology_yearwise_linkage.py [-v]
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from lib.yearwise_linkage_report import run_book  # noqa: E402

# Identities read off the cover by eye (scans).
SETTLED = {
    ("WBI14", "2026 May-Jun"): {"item": "P79214A", "spec": "WBI1", "why": "scanned copy; cover image reads "
                                                                     "Thursday 28 May 2026, WBI14/01, P79214A"},
}

if __name__ == "__main__":
    sys.exit(run_book("ial_biology", legacy_specs={"WBI0"}, verbose="-v" in sys.argv,
                     settled=SETTLED,
                     # Biology schemes are near-numberless: pair on rare words.
                     signal="words"))
