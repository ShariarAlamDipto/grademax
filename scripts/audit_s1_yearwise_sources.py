"""
Audit the S1 (WST01) source papers the 2019-2023 yearwise workbook is built from.

The checks live in `lib/yearwise_sources.py`, shared with M1 and P4; this file
is what is particular to S1.

    python scripts/audit_s1_yearwise_sources.py
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from lib.yearwise_sources import (  # noqa: E402
    ROOT, Archive, Subject, as_json, audit, report)

OUT = ROOT / "data" / "analysis" / "s1_yearwise_source_audit.json"

S1 = Subject(
    unit="WST01",
    name="Statistics S1",
    paper_code=re.compile(r"WST01\s*/?\s*0?1"),
    archives=(
        Archive("IAL/Mathematics",
                ROOT / "data" / "Ultimate Final IAL" / "Mathematics",
                "Mathematics_S1_{year}_{season}_{kind}.pdf"),
    ),
    # Every Jan/Jun/Oct sitting 2019-2023, confirmed against Pearson's own
    # catalogue, EXCEPT summer 2020, which was cancelled -- the paper printed
    # for June 2020 was sat in October and the archive files it under both.
    sittings=tuple((y, s) for y in range(2019, 2024)
                   for s in ("Jan", "May-Jun", "Oct-Nov")),
    cancelled=frozenset({(2020, "May-Jun")}),
    reissued=frozenset({"P65761A"}),
)


def main() -> int:
    order, rejected = audit(S1)
    bad = report(S1, order, rejected)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(as_json(order), indent=2), encoding="utf-8")
    print(f"\nwrote {OUT.relative_to(ROOT)}")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
