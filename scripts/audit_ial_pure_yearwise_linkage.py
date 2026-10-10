"""
Mark-scheme linkage audit for the IAL Pure Mathematics P1-P4 (WMA11-14) yearwise book.

The checks live in `lib/yearwise_linkage.py`; this names the book and the
specification codes that count as legacy for it. Run
`collect_yearwise_all_sources.py --book ial_pure` first.

    python -X utf8 scripts/audit_ial_pure_yearwise_linkage.py [-v]
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from lib.yearwise_linkage_report import run_book  # noqa: E402

# Identities read off the cover by eye (image covers, scans, legacy papers).
SETTLED = {
    # Not IAL at all: the legacy GCE Core Mathematics C2 paper.
    ("WMA12", "2018 May-Jun"): {"item": "P51519A", "spec": "GCE", "why": "cover reads Core Mathematics C2, 6664/01, 23 May 2018"},
    # P4 did not exist before October 2020; this slot holds the legacy GCE C4.
    ("WMA14", "2018 May-Jun"): {"item": "P51566A", "spec": "GCE", "why": "legacy GCE Core Mathematics C4 "
                                                                       "(6666/01); P4 was first sat Oct 2020"},
    # Settled in the P4 yearwise audit: byte-identical to Pearson's own copy.
    ("WMA14", "2021 Jan"): {"item": "P67754A", "spec": "WMA1", "why": "identical to Pearson's WMA14_01_que_20210304.pdf; "
                                               "cover reads Thursday 7 January 2021, P67754A"},
}

if __name__ == "__main__":
    sys.exit(run_book("ial_pure", legacy_specs={"WMA0", "GCE"}, verbose="-v" in sys.argv,
                     settled=SETTLED))
