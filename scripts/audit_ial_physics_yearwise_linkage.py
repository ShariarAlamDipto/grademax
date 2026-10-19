"""
Mark-scheme linkage audit for the IAL Physics (WPH11-16) yearwise book.

The checks live in `lib/yearwise_linkage.py`; this names the book and the
specification codes that count as legacy for it. Run
`collect_yearwise_all_sources.py --book ial_physics` first.

    python -X utf8 scripts/audit_ial_physics_yearwise_linkage.py [-v]
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from lib.yearwise_linkage_report import run_book  # noqa: E402

# Identities read off the cover by eye (image covers, scans, legacy papers).
SETTLED = {
    # Legacy-spec papers in new-spec slots (2019 ran both specs side by side).
    ("WPH11", "2019 May-Jun"): {"item": "P56142A", "spec": "WPH0", "why": "cover image reads Tuesday 14 May 2019, WPH01/01, P56142A"},
    ("WPH15", "2019 May-Jun"): {"item": "P56144A", "spec": "WPH0", "why": "cover image reads Friday 24 May 2019, WPH05/01, P56144A"},
    ("WPH16", "2019 May-Jun"): {"item": "P56140A", "spec": "WPH0", "why": "cover image reads Wednesday 22 May 2019, WPH06/01, P56140A"},
    # A scan (no text layer) of the genuine paper.
    ("WPH16", "2021 May-Jun"): {"item": "P67822A", "spec": "WPH1", "why": "scanned copy; cover image reads WPH16/01, P67822A"},
}

if __name__ == "__main__":
    sys.exit(run_book("ial_physics", legacy_specs={"WPH0"}, verbose="-v" in sys.argv,
                     settled=SETTLED))
