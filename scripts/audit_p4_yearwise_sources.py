"""
Audit the P4 (WMA14) source papers the yearwise workbook is built from.

The checks live in `lib/yearwise_sources.py`, shared with M1 and S1; this file
is what is particular to P4.

P4 DOES NOT REACH BACK TO 2019, and that is not a gap in our archive.

WMA14 is an A2 unit of the 2018 IAL Mathematics specification, first taught in
September 2018, so its units phased in: P1 and P2 from 2019, P3 from January
2020, P4 from the 2020 summer series. That series was cancelled, so P4's first
actual sitting is **October 2020**, using the paper printed for June 2020.
Three independent sources agree:

  * Pearson's catalogue holds 2,592 IAL Mathematics assets and the earliest
    WMA14 anything -- paper, mark scheme or examiner report -- is October 2020.
  * Paperlords lists, session by session: October 2019 = C12, C34, M1, P1, P2,
    S1; January 2020 adds P3; P4 first appears in May 2020.
  * PMT has no IAL P4 page at all.

The files sitting in the archive's 2019 "P4" folders are `WMA02` Core
Mathematics C34 -- a different qualification, 125 marks, 48-52 pages, carrying
trapezium rule and numerical iteration, which are P2/P3 content under this
spec. They are not listed as sittings here and the audit never opens them.

    python scripts/audit_p4_yearwise_sources.py
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from lib.yearwise_sources import (  # noqa: E402
    ROOT, Archive, Subject, as_json, audit, report)

OUT = ROOT / "data" / "analysis" / "p4_yearwise_source_audit.json"

P4 = Subject(
    unit="WMA14",
    name="Pure Mathematics P4",
    paper_code=re.compile(r"WMA14\s*/?\s*0?1"),
    archives=(
        Archive("IAL/Mathematics",
                ROOT / "data" / "Ultimate Final IAL" / "Mathematics",
                "Mathematics_P4_{year}_{season}_{kind}.pdf"),
    ),
    # The cancelled summer 2020 slot is listed because the archive fills it with
    # the paper that was sat in October; everything before it did not exist.
    sittings=((2020, "May-Jun"), (2020, "Oct-Nov"),
              *((y, s) for y in (2021, 2022, 2023)
                for s in ("Jan", "May-Jun", "Oct-Nov"))),
    cancelled=frozenset({(2020, "May-Jun")}),
    reissued=frozenset({"P65759A"}),
    # The same transposition Pearson made on M1: `2021` for January 2021, where
    # the cover and the schemes both say January 2021.
    pub_typos={"WMA14_01_2021": "2101"},
    settled={
        # The pairing check doubted this one. It is right as filed: the file is
        # identical to Pearson's own copy, WMA14_01_que_20210304.pdf, down to
        # the item code and the printed exam date. Both 2021 P4 papers open
        # with a binomial expansion, which is enough shared vocabulary to beat
        # the margin -- P4 scores lower across the board than the other units,
        # so its cover date carries more weight here than the pairing score.
        (2021, "Jan"): "identical to Pearson's own copy; cover reads "
                       "Thursday 7 January 2021, item code P67754A",
    },
)


def main() -> int:
    order, rejected = audit(P4)
    bad = report(P4, order, rejected)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(as_json(order), indent=2), encoding="utf-8")
    print(f"\nwrote {OUT.relative_to(ROOT)}")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
