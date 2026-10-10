"""
Build the IGCSE Physics (4PH1) yearwise books, 2018-2026, from the sittings
the linkage audit proved (run audit_igcse_physics_yearwise_linkage.py first).

Allowance 2 (physics papers have almost no pure answer sides -- 1 in 968
sheets); the saving is the covers, BLANK PAGE sheets and the Equation Booklet /
formulae sheet printed once per volume. Measured 968 source sheets -> 780.

    python -X utf8 scripts/build_igcse_physics_yearwise_all.py [--execute]
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
    ap.add_argument("--allowance", type=int, default=2)
    a = ap.parse_args()
    sys.exit(build("igcse_physics", "Physics", "4PH1", "IGCSE",
                   lambda u: u.label.replace("Physics ", ""), a.allowance,
                   WORK / "books" / "igcse_physics", LOCKUP, a.execute))
