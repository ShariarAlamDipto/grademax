"""
Mark-scheme linkage audit for the IAL Chemistry (WCH11-16) yearwise book.

The checks live in `lib/yearwise_linkage.py`; this names the book and the
specification codes that count as legacy for it. Run
`collect_yearwise_all_sources.py --book ial_chemistry` first.

    python -X utf8 scripts/audit_ial_chemistry_yearwise_linkage.py [-v]
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from lib.yearwise_linkage_report import run_book  # noqa: E402

# Identities read off the cover by eye (image covers, scans, legacy papers).
SETTLED = {
    # Legacy-spec papers in new-spec slots (2019 ran both specs side by side).
    ("WCH16", "2019 Jan"): {"item": "P54564A", "spec": "WCH0", "why": "cover image reads Thursday 24 January 2019, WCH06/01, P54564A"},
    ("WCH13", "2019 May-Jun"): {"item": "P55637A", "spec": "WCH0", "why": "cover image reads Tuesday 7 May 2019, WCH03/01, P55637A"},
}

if __name__ == "__main__":
    sys.exit(run_book("ial_chemistry", legacy_specs={"WCH0"}, verbose="-v" in sys.argv,
                     settled=SETTLED))
