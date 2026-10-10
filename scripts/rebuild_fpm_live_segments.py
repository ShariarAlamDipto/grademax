#!/usr/bin/env python3
"""
Rebuild every live IGCSE Further Pure Maths (4PM1/4PM0) question + mark-scheme
segment the test builder and worksheet generator serve, from the whole-paper
PDFs, and PROVE each pair before it can be published.

    python scripts/rebuild_fpm_live_segments.py            # build + verify (staging only)
    python scripts/rebuild_fpm_live_segments.py --paper 2018_jan_P2 --verbose
    python scripts/rebuild_fpm_live_segments.py --render   # draw unproven pairs

Writes only to data/analysis/live_rebuild/4PM1/. Publishing is
publish_fpm_live_segments.py.

WHY: the 2026-10-07 live audit proved only 316 of 833 live FPM pairs; 69
question files hold several questions and 90 questions have no scheme.

Cutting reuses build_fpm_workbook_segments.py (fences, whole-page question
ranges, banded schemes with the truncated-header recovery). Its EXCLUDED
2017 Oct-Nov papers are the 2016 specimens refiled; they stay unrebuilt, so
the publisher keeps their questions and shows a scheme only where the live
audit already proved it.
"""

import dataclasses
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import build_fpm_workbook_segments as seg  # noqa: E402
from lib import ms_label_blocks  # noqa: E402
from lib.live_paper_sources import LivePaper  # noqa: E402
from lib.live_rebuild_common import install_safe_extract, run  # noqa: E402

CODE = "4PM1"
install_safe_extract(seg)

_original_process = seg.process_paper


def process_paper_with_labels(source):
    """
    FPM's own reader returns bands; questions it leaves without a scheme (all
    eleven of 2011 May-Jun P2, whose column is headed "Q.") are filled from
    the margin-label reader. The proof gate still decides.
    """
    result = _original_process(source)
    missing = [s.number for s in result.segments if not s.ms_regions]
    if not missing or source.ms_path is None:
        return result
    fences = {s.number: (0, s.marks) for s in result.segments}
    notes: list[str] = []
    found = ms_label_blocks.label_blocks(source.ms_path, fences, notes)
    filled = [n for n in missing if n in found]
    if filled:
        result.segments = [
            dataclasses.replace(s, ms_regions=found[s.number]) if s.number in filled else s
            for s in result.segments
        ]
        result.warnings.extend(notes + [f"label reader filled schemes for {filled}"])
    return result


ms_label_blocks._REGION[0] = seg.Region
seg.process_paper = process_paper_with_labels


def to_source(paper: LivePaper):
    if paper.qp_path is None:
        return None
    key = f"{paper.year}_{paper.season}_{paper.paper_number}"
    return seg.PaperSource(key=key, year=paper.year, season=paper.season,
                           paper_number=paper.paper_number,
                           qp_path=paper.qp_path, ms_path=paper.ms_path)


if __name__ == "__main__":
    sys.exit(run(CODE, seg, to_source))
