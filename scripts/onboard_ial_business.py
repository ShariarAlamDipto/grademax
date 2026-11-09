#!/usr/bin/env python3
"""
IAL Business (WBS11-WBS14) in the worksheet generator and test builder.

A question is one section of a paper: its Source Booklet extracts followed by its
question pages (lines-only answer pages dropped), with its own mark-scheme pages.
lib/ial_business_stage.py has the cut and the proof; only PUBLISHABLE questions are
published (AGENTS.md rule 5). Chapters (the 20 specification topics) are read from
every question and pinned to both PDFs' SHA-256 in
data/analysis/live_rebuild/WBS/topic_reads.json (rule 6).

    python -X utf8 scripts/onboard_ial_business.py stage
    python -X utf8 scripts/onboard_ial_business.py dump
    python -X utf8 scripts/onboard_ial_business.py check
    python -X utf8 scripts/onboard_ial_business.py publish [--execute]
"""
from __future__ import annotations

import argparse
import io
import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from lib import commerce_chapters as cc  # noqa: E402
from lib.ial_business_stage import stage_paper  # noqa: E402
from lib.ial_business_topics import CHAPTERS, SUBJECT  # noqa: E402
from lib.igcse_science_rebuild import PUBLISHABLE  # noqa: E402
from lib.live_paper_sources import ROOT, load_live_papers  # noqa: E402
from lib.live_rebuild_common import pairing_verified  # noqa: E402
from lib.new_subject_publish import publish  # noqa: E402

if sys.stdout.encoding != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

R2_FOLDER = 'ial/business/pages-v2'
MARKS_FILE = ROOT / 'src' / 'lib' / 'ialBusinessQuestionMarks.json'


def stage() -> int:
    papers = sorted(load_live_papers('WBS'), key=lambda p: p.key)
    paired = pairing_verified(papers)
    notes, rows = {}, []
    for paper in papers:
        try:
            note, staged = stage_paper(paper, SUBJECT.stage / 'segments', paper.paper_id in paired)
        except ValueError as exc:
            note, staged = f'HELD: {exc}', []
        notes[paper.key] = note
        rows.extend(staged)
        print(f'WBS {paper.key:22} {note}')
    result = {'scope': 'section extracts + question pages; complete questions; chapter filters',
              'chapters': {code: name for code, (name, _) in CHAPTERS.items()},
              'papers': notes, 'rows': sorted(rows, key=lambda r: (r['paper'], r['question']))}
    (SUBJECT.stage / 'verdicts.json').write_text(json.dumps(result, indent=1), encoding='utf-8')
    tally = Counter(r['verdict'] for r in rows)
    print(f"WBS: {dict(tally)}; publishable {sum(n for v, n in tally.items() if v in PUBLISHABLE)}")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('step', choices=['stage', 'dump', 'check', 'publish'])
    ap.add_argument('--execute', action='store_true')
    args = ap.parse_args()
    if args.step == 'stage':
        return stage()
    if args.step == 'dump':
        print(f'wrote {cc.dump(SUBJECT, cc.published_rows(SUBJECT)).relative_to(ROOT)}')
        return 0
    if args.step == 'check':
        return cc.check(SUBJECT)
    return publish(SUBJECT, R2_FOLDER, MARKS_FILE, args.execute)


if __name__ == '__main__':
    sys.exit(main())
