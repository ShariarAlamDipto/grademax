#!/usr/bin/env python3
"""
Make IGCSE Economics chapterwise in the test builder and worksheet generator.

The published questions carry only whole-paper topics ("1"/"2"). Every question
is read and the read is recorded in
data/analysis/live_rebuild/<code>/topic_reads.json:
    {"<paper>|<q>": {"topics": [...primary first], "difficulty": "...",
                     "reason": "...", "qp_sha256": "...", "ms_sha256": "..."}}

    python -X utf8 scripts/chapterwise_igcse_economics.py dump              # review.txt (unread only)
    python -X utf8 scripts/chapterwise_igcse_economics.py check             # validate, write topics_new.json
    python -X utf8 scripts/chapterwise_igcse_economics.py apply             # dry run against live
    python -X utf8 scripts/chapterwise_igcse_economics.py apply --execute   # back up, write, re-read
    python -X utf8 scripts/chapterwise_igcse_economics.py restamp-ms --note '...' [--execute]
        # after a mark-scheme re-cut: re-pin MS hashes where the QP is unchanged
"""
from __future__ import annotations

import argparse
import io
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from lib import commerce_chapters as cc  # noqa: E402
from lib.economics_topics import SUBJECT  # noqa: E402
from lib.live_paper_sources import ROOT, supabase_client  # noqa: E402

if sys.stdout.encoding != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('step', choices=['dump', 'check', 'apply', 'restamp-ms'])
    ap.add_argument('--execute', action='store_true')
    ap.add_argument('--note', default='', help='restamp-ms: why the mark schemes changed')
    ap.add_argument('--all', action='store_true', help='dump: include questions already read')
    args = ap.parse_args()
    if args.step == 'dump':
        path = cc.dump(SUBJECT, cc.published_rows(SUBJECT), only_unread=not args.all)
        print(f'wrote {path.relative_to(ROOT)}')
        return 0
    if args.step == 'restamp-ms':
        if not args.note.strip():
            ap.error('restamp-ms needs --note')
        return cc.restamp_ms(SUBJECT, args.note, args.execute)
    if args.step == 'check':
        return cc.check(SUBJECT)
    return cc.apply(SUBJECT, supabase_client(), args.execute)


if __name__ == '__main__':
    sys.exit(main())
