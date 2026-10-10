#!/usr/bin/env python3
"""
Rebuild every live IGCSE Maths B (4MB1/4MB0) question + mark-scheme segment
the test builder and worksheet generator serve, from the whole-paper PDFs, and
PROVE each pair before it can be published.

    python scripts/rebuild_mathsb_live_segments.py            # build + verify (staging only)
    python scripts/rebuild_mathsb_live_segments.py --paper 2016_jan_P1R --verbose
    python scripts/rebuild_mathsb_live_segments.py --render   # draw unproven pairs

Writes only to data/analysis/live_rebuild/4MB1/. Publishing is
publish_mathsb_live_segments.py.

WHY: the 2026-10-07 live audit found 773 of 1983 live Maths B question files
holding 2-3 questions (Paper 1 prints several per page and the old segmenter
cut whole pages) and 455 questions with no scheme at all.

Cutting reuses build_mathsb_workbook_segments.py (fences, y-crops, banded
schemes). Its scheme linker aligns MARKS sequences, which can pair a question
with a neighbour of equal tariff -- so here it only proposes; the gate in
lib/live_rebuild_common.py decides, reading the number each scheme prints.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import build_mathsb_workbook_segments as seg  # noqa: E402
from lib.live_paper_sources import LivePaper  # noqa: E402
from lib import ms_label_blocks  # noqa: E402
from lib.live_rebuild_common import install_safe_extract, run  # noqa: E402

CODE = "4MB1"
install_safe_extract(seg)
# Older schemes ("Question Number | Working | Notes | Mark", 2011-2019) print no
# per-question tally; cut those by their own margin numbers.
ms_label_blocks.install(seg)


def to_source(paper: LivePaper):
    if paper.qp_path is None:
        return None
    # The workbook segmenter's own key form, so its hand-verified tables apply.
    key = f"{paper.year}_{paper.season}_{paper.paper_number}"
    return seg.PaperSource(key=key, year=paper.year, season=paper.season,
                           paper_number=paper.paper_number,
                           qp_path=paper.qp_path, ms_path=paper.ms_path)


if __name__ == "__main__":
    sys.exit(run(CODE, seg, to_source))
