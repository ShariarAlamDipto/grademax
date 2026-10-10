"""
Mark-scheme linkage audit for the IGCSE Biology (4BI1) yearwise book.

The checks live in `lib/yearwise_linkage.py`; this names the book and the
specification codes that count as legacy for it. Run
`collect_yearwise_all_sources.py --book igcse_biology` first.

    python -X utf8 scripts/audit_igcse_biology_yearwise_linkage.py [-v]
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from lib.yearwise_linkage_report import run_book  # noqa: E402

# Identities read off image-only covers by eye.
SETTLED = {
    ("4BI1_P2", "2019 Jan"): {"item": "P55731A", "spec": "4BI0", "why": "cover image reads Monday 14 January 2019, "
                                                     "4BI0/2B, P55731A"},
}

if __name__ == "__main__":
    sys.exit(run_book("igcse_biology", legacy_specs={"4BI0"}, verbose="-v" in sys.argv,
                     settled=SETTLED,
                     # Biology schemes are near-numberless: pair on rare words.
                     signal="words"))
