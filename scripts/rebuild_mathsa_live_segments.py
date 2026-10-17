#!/usr/bin/env python3
"""
Build every IGCSE Mathematics A (4MA1/4MA0) question + mark-scheme segment the
test builder and worksheet generator will serve, from the whole-paper PDFs on
R2, and PROVE each pair before it can be published.

    python scripts/rebuild_mathsa_live_segments.py            # build + verify (staging only)
    python scripts/rebuild_mathsa_live_segments.py --paper 2019_jan_P1H --verbose
    python scripts/rebuild_mathsa_live_segments.py --render   # draw unproven pairs

Writes only to data/analysis/live_rebuild/4MA1/. Publishing is
publish_mathsa_live_segments.py.

WHICH ROWS: the Higher tier only, one row per real paper, chosen by what each
cover prints (scripts/audit_mathsa_r2_paper_identity.py):

  * 4MA1 1H/2H/1HR/2HR from June 2018 (the spec's first sitting) on;
  * 4MA0 3H/4H/3HR/4HR before that. Every pre-June-2018 "1H"/"2H"/"1HR"/"2HR"
    row holds the SAME 4MA0 3H/4H document as the correctly named row beside
    it (same Pearson barcode), so serving both would list each question twice;
  * except 2013 May-Jun "2H", whose cover is 4MA0/4H and which has no 4H row
    beside it -- it is the only copy of that paper (relabelled by
    fix_mathsa_2013_mj_4h_label.py).

Foundation is left out: its harder half is the Higher paper's easier half
(common questions), so serving both tiers would duplicate questions too.

Cutting reuses build_mathsa_workbook_segments.py (end fences + y-crops, banded
schemes). Its scheme linker aligns MARKS sequences, which can pair a question
with a neighbour of equal tariff -- so here it only proposes; the gate in
lib/live_rebuild_common.py decides, reading the number each scheme prints.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import build_mathsa_workbook_segments as seg  # noqa: E402
from lib.live_paper_sources import LivePaper  # noqa: E402
from lib import ms_bands, ms_label_blocks  # noqa: E402
from lib import live_rebuild_common  # noqa: E402
from lib.live_rebuild_common import install_safe_extract, run  # noqa: E402

CODE = "4MA1"
# Maths A schemes head their column "Q", never "Question"; without this every
# one of them looked scrambled and was swapped for a worse OCR copy.
live_rebuild_common.TRUST_ENGLISH_TEXT = True
NEW_SPEC_PAPERS = {"1H", "2H", "1HR", "2HR"}
OLD_SPEC_PAPERS = {"3H", "4H", "3HR", "4HR"}
SEASON_ORDER = {"jan": 0, "may-jun": 1, "oct-nov": 2}
NEW_SPEC_FROM = (2018, SEASON_ORDER["may-jun"])
# Cover-proven sole copies filed under a 4MA1-style name (see module docstring).
SOLE_COPY_ROWS = {"2013_may-jun_P2H"}

install_safe_extract(seg)
# Alternative-method tables carry their own "Total N marks"; fold each into its
# own question so the next question's scheme does not open on it. The paper's
# question count bounds how many may be folded.
_find_tallies = ms_bands.find_tallies
_questions_in_paper: list[int | None] = [None]
ms_bands.find_tallies = lambda ms_path: ms_bands.merge_alternative_tallies(
    ms_path, _find_tallies(ms_path), target=_questions_in_paper[0])
_locate_ms_blocks = seg.locate_ms_blocks


def _locate_with_count(ms_path, fences, *args, **kwargs):
    _questions_in_paper[0] = len(fences)
    try:
        return _locate_ms_blocks(ms_path, fences, *args, **kwargs)
    finally:
        _questions_in_paper[0] = None


seg.locate_ms_blocks = _locate_with_count
# Older 4MA0 schemes print no per-question tally; cut those by their margin numbers.
ms_label_blocks.install(seg)


def is_tool_row(paper: LivePaper) -> bool:
    if paper.key in SOLE_COPY_ROWS:
        return True
    sitting = (paper.year, SEASON_ORDER.get(paper.season, 9))
    if paper.paper_number in NEW_SPEC_PAPERS:
        return sitting >= NEW_SPEC_FROM
    return paper.paper_number in OLD_SPEC_PAPERS and sitting < NEW_SPEC_FROM


def to_source(paper: LivePaper):
    if paper.qp_path is None:
        return None
    # The workbook segmenter's own key form, so its hand-verified tables apply.
    key = f"{paper.year}_{paper.season}_{paper.paper_number}"
    return seg.PaperSource(key=key, year=paper.year, season=paper.season,
                           paper_number=paper.paper_number,
                           qp_path=paper.qp_path, ms_path=paper.ms_path)


if __name__ == "__main__":
    sys.exit(run(CODE, seg, to_source, include=is_tool_row))
