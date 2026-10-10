"""
Mark-scheme linkage audit for the IGCSE Mathematics B (4MB1) yearwise book.

The checks live in `lib/yearwise_linkage.py`; this names the book and the
specification codes that count as legacy for it. Run
`collect_yearwise_all_sources.py --book igcse_mathsb` first.

    python -X utf8 scripts/audit_mathsb_yearwise_linkage.py [-v]
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from lib.yearwise_linkage_report import run_book  # noqa: E402

if __name__ == "__main__":
    sys.exit(run_book("igcse_mathsb", legacy_specs={"4MB0"}, verbose="-v" in sys.argv))
