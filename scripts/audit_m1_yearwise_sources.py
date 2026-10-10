"""
Audit the M1 (WME01) source papers the yearwise workbook is built from.

The checks live in `lib/yearwise_sources.py`, shared with S1 and P4; this file
is what is particular to M1.

    python scripts/audit_m1_yearwise_sources.py
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from lib.yearwise_sources import (  # noqa: E402
    ROOT, Archive, Subject, as_json, audit, report)

OUT = ROOT / "data" / "analysis" / "m1_yearwise_source_audit.json"

# M1 is the one unit filed in two places. The 2017-2019 papers are in the IGCSE
# tree -- the IAL Mathematics tree's copies of those years were the PMT Model
# Answers this project quarantined -- and 2020 onwards are in the IAL tree.
M1 = Subject(
    unit="WME01",
    name="Mechanics M1",
    paper_code=re.compile(r"WME01\s*/?\s*0?1|\b6677\b"),
    archives=(
        Archive("IGCSE/Mechanics_1",
                ROOT / "data" / "Ultimate Final IGCSE" / "Mechanics_1",
                "Mechanics_1_{year}_{season}_Paper_1_{kind}.pdf"),
        Archive("IAL/Mathematics",
                ROOT / "data" / "Ultimate Final IAL" / "Mathematics",
                "Mathematics_M1_{year}_{season}_{kind}.pdf"),
    ),
    # Every Jan/Jun/Oct sitting from 2017 to 2023, including the cancelled
    # summer 2020 slot, which the archive fills and the book prints once.
    sittings=tuple((y, s) for y in range(2017, 2024)
                   for s in ("Jan", "May-Jun", "Oct-Nov")),
    cancelled=frozenset({(2020, "May-Jun")}),
    reissued=frozenset({"P65760A"}),
    # `2021` for January 2021 is a transposition of 2101 -- the cover reads
    # January 2021 and the schemes match that session's paper.
    pub_typos={"WME01_01_2021": "2101"},
)


def main() -> int:
    order, rejected = audit(M1)
    bad = report(M1, order, rejected)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(as_json(order), indent=2), encoding="utf-8")
    print(f"\nwrote {OUT.relative_to(ROOT)}")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
