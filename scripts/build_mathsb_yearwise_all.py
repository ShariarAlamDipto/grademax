"""
Build the IGCSE Mathematics B (4MB1) yearwise books, 2018-2026, from the sittings
the linkage audit proved (run audit_mathsb_yearwise_linkage.py first).

Allowance 0: a question keeps its own sheets and the sheet carrying its total
band -- no extra ruled sides. Measured: 1,068 source sheets -> 863 (2 volume
pairs); allowance 1 gives 908 and allowance 2 gives 968, both needing 3.

    python -X utf8 scripts/build_mathsb_yearwise_all.py [--execute]
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from lib.yearwise_all_build import build  # noqa: E402
from lib.yearwise_all_catalogue import WORK  # noqa: E402

LOCKUP = (Path.home() / "OneDrive" / "Desktop" / "FPM cover" / "Final Cover"
          / "Final Water Mark" / "FINAL WATERMARK.png")

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--execute", action="store_true")
    ap.add_argument("--allowance", type=int, default=0)
    a = ap.parse_args()
    sys.exit(build("igcse_mathsb", "Mathematics B", "4MB1", "IGCSE",
                   lambda u: u.label.replace("Mathematics B ", ""), a.allowance,
                   WORK / "books" / "igcse_mathsb", LOCKUP, a.execute))
