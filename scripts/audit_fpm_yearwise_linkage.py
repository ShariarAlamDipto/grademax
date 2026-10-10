"""
Mark-scheme linkage audit for the IGCSE Further Pure Mathematics (4PM1) yearwise book.

The checks live in `lib/yearwise_linkage.py`; this names the book, the
specification codes that count as legacy for it, and the sittings whose
identity was settled by eye because no text layer can say it. Run
`collect_yearwise_all_sources.py --book igcse_fpm` first.

    python -X utf8 scripts/audit_fpm_yearwise_linkage.py [-v]
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from lib.yearwise_linkage_report import run_book  # noqa: E402

SETTLED = {
    # Cover is an image; it reads "Paper Reference 4PM0/01" -- the LEGACY spec.
    ("4PM1_P1", "2019 Jan"): {"item": "P55887A", "spec": "4PM0", "why": "cover image reads Friday 11 January 2019, "
                                                     "4PM0/01, P55887A"},
    # Every copy held (R2 and archive) is image-only; the cover is genuine.
    ("4PM1_P1", "2019 May-Jun"): {"item": "P58286A", "spec": "4PM1", "why": "cover image reads Monday 17 June 2019, "
                                                         "4PM1/01, P58286A"},
    # The scheme states no per-question totals and the number match leans to
    # Jan 2022's scheme; read side by side, Q1 "Differentiate e^(3x) cos 2x"
    # (3 marks) is the scheme's Q1 product-rule row, M1A1A1 (3).
    ("4PM1_P1", "2020 Oct-Nov"): {"item": "P62280A", "spec": "4PM1", "why": "Q1 (differentiate e^3x cos 2x, 3 marks) "
                                                         "matches the scheme's Q1 M1A1A1 (3) row"},
}

if __name__ == "__main__":
    sys.exit(run_book("igcse_fpm", legacy_specs={"4PM0"}, verbose="-v" in sys.argv,
                      settled=SETTLED))
