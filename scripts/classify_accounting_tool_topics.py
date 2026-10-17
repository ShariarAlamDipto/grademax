#!/usr/bin/env python3
"""
Chapter tags for every published IGCSE Accounting (4AC1) tool question ->
data/analysis/live_rebuild/4AC1/topics_new.json, read by
apply_accounting_tool_topics.py.

Chapters are the 4AC1 specification sections (scripts/lib/accounting_topics.py).
The keyword lexicon only proposes; every question is read and the decision is
recorded in topic_reads.json {"<paper>|<q>": ["3.2", "2.2"]} (primary first).
A question with no recorded read is never tagged.

    python -X utf8 scripts/classify_accounting_tool_topics.py --dump
        # write review.txt: each question's text, mark scheme head and proposals
    python -X utf8 scripts/classify_accounting_tool_topics.py
        # validate reads, write topics_new.json, report coverage
"""
from __future__ import annotations

import argparse
import io
import json
import re
import sys
from collections import Counter
from pathlib import Path

import fitz

sys.path.insert(0, str(Path(__file__).resolve().parent))

from lib.accounting_topics import CHAPTERS, CODE, propose  # noqa: E402
from lib.live_paper_sources import REBUILD_DIR, ROOT  # noqa: E402

if sys.stdout.encoding != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

STAGE = REBUILD_DIR / CODE
READS = STAGE / 'topic_reads.json'
OUT = STAGE / 'topics_new.json'
REVIEW = STAGE / 'review.txt'
PUBLISHED = {'PROVEN', 'LABEL_PROVEN'}
FURNITURE_RE = re.compile(
    r'GradeMax|PhysicsAndMathsTutor\S*|Turn over|DO NOT WRITE IN THIS AREA|\.{4,}|_{4,}|'
    r'\(Total for Question \d+ (?:is|=) ?\d+ marks?\)|\*P\d+A?\d*\*|P\d{5}[A-Z]?\d*|'
    r'©\s*\d{4} Pearson Education Ltd\.?', re.I)


def published_rows() -> list[dict]:
    rows = json.loads((STAGE / 'verdicts.json').read_text(encoding='utf-8'))['rows']
    return [r for r in rows if r['verdict'] in PUBLISHED]


def key_of(row: dict) -> str:
    return f"{row['paper']}|{row['question']}"


def paper_of(row: dict) -> str:
    match = re.search(r'_P([12])R?$', row['paper'])
    if not match:
        raise ValueError(f"cannot read paper number from {row['paper']}")
    return match[1]


def cut_text(rel: str) -> str:
    with fitz.open(ROOT / rel) as doc:
        text = ' '.join(page.get_text() for page in doc)
    return ' '.join(FURNITURE_RE.sub(' ', text).split())


PART_RE = re.compile(r'\((?:[a-h]|i{1,3}|iv|vi?)\)\s')
HEADER_RE = re.compile(r'4AC1 \| \d{4} \| [^|]+\| Paper \dR? \||Accounting · \d{4} · [^·]+· Paper \dR? · QP')


def parts_view(text: str, preamble: int = 260, each: int = 230) -> str:
    """Every lettered part's own prompt, so a long question is read in full scope."""
    text = HEADER_RE.sub(' ', text)
    cuts = [m.start() for m in PART_RE.finditer(text)]
    if not cuts:
        return text[:900]
    pieces = [text[:min(cuts[0], preamble)]]
    pieces += [text[a:a + each] for a in cuts]
    return ' | '.join(' '.join(p.split()) for p in pieces)


def dump(rows: list[dict]) -> None:
    out = []
    for r in rows:
        qp = cut_text(r['qp'])
        ms = cut_text(r['ms'])
        ranked = propose(qp + ' ' + ms, paper_of(r))
        out.append(f"### {key_of(r)}  [{r['marks']}m]  proposed: "
                   + ', '.join(f'{c}x{n}' for c, n in ranked[:5]))
        out.append('Q: ' + (parts_view(qp) if r['marks'] >= 15 else qp[:900]))
        out.append('MS: ' + ms[:200])
        out.append('')
    REVIEW.write_text('\n'.join(out), encoding='utf-8')
    print(f'wrote {REVIEW.relative_to(ROOT)} ({len(rows)} questions)')


def validate(reads: dict, keys: set[str]) -> None:
    unknown = sorted(set(reads) - keys)
    if unknown:
        raise ValueError(f'reads for questions that are not published: {unknown[:10]}')
    for k, codes in reads.items():
        if not codes or not isinstance(codes, list):
            raise ValueError(f'{k}: empty read')
        bad = [c for c in codes if c not in CHAPTERS]
        if bad:
            raise ValueError(f'{k}: unknown chapter codes {bad}')
        if len(set(codes)) != len(codes):
            raise ValueError(f'{k}: duplicate codes {codes}')


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--dump', action='store_true')
    args = ap.parse_args()
    rows = published_rows()
    if args.dump:
        dump(rows)
        return 0
    reads = json.loads(READS.read_text(encoding='utf-8')) if READS.exists() else {}
    keys = {key_of(r) for r in rows}
    validate(reads, keys)
    missing = sorted(keys - set(reads))
    out = {k: reads[k] for k in sorted(reads)}
    OUT.write_text(json.dumps(out, indent=1), encoding='utf-8')
    counts = Counter(c for codes in out.values() for c in codes)
    print(f'{CODE}: {len(rows)} published, {len(out)} read, {len(missing)} unread')
    for code, (name, _) in CHAPTERS.items():
        print(f'  {code:4s} {name:42s} {counts.get(code, 0):4d}')
    if missing:
        print('  UNREAD:', missing[:20])
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
