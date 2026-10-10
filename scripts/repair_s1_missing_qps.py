"""
Fill the four holes in the S1 (WST01) archive for 2019-2023.

Two sessions are simply absent, and two slots hold a neighbouring session's
paper -- the duplicate defect that no cover check can see, because the copy's
cover honestly names the session it really is:

  2019 Oct-Nov  QP + MS   not held at all
  2020 Jan      QP + MS   not held at all
  2021 May-Jun  QP        the slot holds the OCTOBER 2021 paper (P71284A is in
                          both 2021 slots; it scores 0.391 against October's
                          mark scheme and 0.081 against June's)
  2023 May-Jun  QP        the slot holds the JANUARY 2023 paper (P72072A)

Pearson publishes five of the six itself. The October 2019 question paper is
the exception: it sits under `/content/dam/secure/...` and answers a 995-byte
login page, exactly as M1's October 2019 paper did, so it comes from the
Paperlords archive, whose copy carries no watermark of its own. Its mark scheme
IS public from Pearson, and the two copies are byte-identical at 473,410 bytes
-- a free cross-check on the third-party source.

    python scripts/repair_s1_missing_qps.py            # check only
    python scripts/repair_s1_missing_qps.py --commit
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from audit_s1_yearwise_sources import S1  # noqa: E402
from lib.yearwise_repair import Wanted, run  # noqa: E402

PEARSON = "https://qualifications.pearson.com/content/dam/pdf"
# Pearson files one unit's assets under three different folder spellings, and
# which one a paper lands in follows its publication date, not its unit. Do not
# guess: these came from the catalogue's own URLs.
#   2013 spec tree, "Exam materials" with a space   -- up to the 2020 sessions
#   2018 spec tree, "Exam-materials" hyphenated     -- 2021 onwards
#   2018 spec tree, hyphenated and lower case       -- 2023 onwards
SPEC13 = f"{PEARSON}/International%20Advanced%20Level/Mathematics/2013/Exam%20materials"
SPEC18 = f"{PEARSON}/International%20Advanced%20Level/Mathematics/2018/Exam-materials"
SPEC18L = f"{PEARSON}/International-Advanced-Level/Mathematics/2018/Exam-materials"
PAPERLORDS = "https://archive.paperlords.org/library/IAL/Maths"

WANTED = (
    Wanted(2019, "Oct-Nov", "QP",
           f"{PAPERLORDS}/Oct%202019/IAL_MATHS_2019_Oct_S1_QP.pdf",
           "Paperlords", "not held; Pearson serves it only behind a login"),
    Wanted(2019, "Oct-Nov", "MS",
           f"{SPEC13}/WST01_01_msc_20191023.pdf", "Pearson", "not held"),
    Wanted(2020, "Jan", "QP",
           f"{SPEC13}/WST01_01_que_20200305.pdf", "Pearson", "not held"),
    Wanted(2020, "Jan", "MS",
           f"{SPEC13}/WST01_01_rms_20200305.pdf", "Pearson", "not held"),
    Wanted(2021, "May-Jun", "QP",
           f"{SPEC18}/WST01_01_que_20210427.pdf", "Pearson",
           "slot holds the October 2021 paper"),
    Wanted(2023, "May-Jun", "QP",
           f"{SPEC18L}/wst01-01-que-20230512.pdf", "Pearson",
           "slot holds the January 2023 paper"),
)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--commit", action="store_true")
    args = ap.parse_args()
    return run(S1, "S1", WANTED, args.commit)


if __name__ == "__main__":
    sys.exit(main())
