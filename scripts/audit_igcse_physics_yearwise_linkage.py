"""
Mark-scheme linkage audit for the IGCSE Physics (4PH1) yearwise book.

The checks live in `lib/yearwise_linkage.py`; this names the book and the
specification codes that count as legacy for it. Run
`collect_yearwise_all_sources.py --book igcse_physics` first.

    python -X utf8 scripts/audit_igcse_physics_yearwise_linkage.py [-v]
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from lib.yearwise_linkage_report import run_book  # noqa: E402

# Identities read off image-only covers by eye.
SETTLED = {
    # Every copy held is image-only; the cover is genuine.
    ("4PH1_P1", "2019 May-Jun"): {"item": "P58372A", "spec": "4PH1", "why": "cover image reads Wednesday 22 May 2019, "
                                                         "4PH1/1P 4SD0/1P, P58372A"},
}

if __name__ == "__main__":
    sys.exit(run_book("igcse_physics", legacy_specs={"4PH0"}, verbose="-v" in sys.argv,
                     settled=SETTLED))
