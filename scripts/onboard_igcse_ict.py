#!/usr/bin/env python3
"""
IGCSE ICT (4IT1) Paper 1 questions in the worksheet generator and test builder.

Paper 1 (written, 4IT1/01 and /01R) has five 20-mark questions. Paper 2 is an
on-screen practical that needs data files, so it is held, like Computer Science
Paper 2. Questions are cut by the shared total-line segmenter; schemes are cut by
position from each question's start marker to the next (table header rows travel
with their question, lib/ial_accounting_stage.scheme_regions).

A question is published (LABEL_PROVEN) only when the QP and MS covers print the
same 4IT1 paper, the MS cover names the row's session and year, the content-
pairing audit judged the pair OK, the paper has questions 1..5 totalling 100, and
the scheme cut names only its own question and covers every part it prints.
Chapters (specification sections 1.1-5.4) are read from every question and pinned
to both PDFs' SHA-256 in data/analysis/live_rebuild/4IT1/topic_reads.json.

    python -X utf8 scripts/onboard_igcse_ict.py stage
    python -X utf8 scripts/onboard_igcse_ict.py dump
    python -X utf8 scripts/onboard_igcse_ict.py check
    python -X utf8 scripts/onboard_igcse_ict.py publish [--execute]
"""
from __future__ import annotations

import argparse
import io
import json
import re
import shutil
import sys
import tempfile
from collections import Counter
from pathlib import Path

import fitz

sys.path.insert(0, str(Path(__file__).resolve().parent))

from lib import commerce_chapters as cc  # noqa: E402
from lib.ial_accounting_stage import _fingerprint, scheme_regions, write_stable  # noqa: E402
from lib.igcse_ict_topics import CHAPTERS, SUBJECT  # noqa: E402
from lib.igcse_science_rebuild import PUBLISHABLE, stage_paper  # noqa: E402
from lib.live_paper_sources import ROOT, load_live_papers  # noqa: E402
from lib.live_rebuild_common import pairing_verified  # noqa: E402
from lib.new_subject_publish import publish  # noqa: E402

if sys.stdout.encoding != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

STAGE = SUBJECT.stage
R2_FOLDER = 'igcse/ict/pages-v2'
MARKS_FILE = ROOT / 'src' / 'lib' / 'ictQuestionMarks.json'
SEASON_WORDS = {'may-jun': ('June', 'Summer'), 'oct-nov': ('November', 'October'), 'jan': ('January',)}
# ICT schemes label parts "1ai", "1biii", "1g" (older ones "1(a)(i)") at the start of a row.
LABEL_RE = re.compile(r'^\s*([1-5])(?:\(([a-h])\)|([a-h]))(?:\(?(?:i{1,3}|iv|vi?)\)?)?(?=[\s(]|$)')
QP_PART_RE = re.compile(r'(?:^|\s)\(([a-h])\)')


def _labels(doc: fitz.Document) -> set[tuple[int, str]]:
    from lib.ial_accounting_stage import _rows  # noqa: PLC0415
    out = set()
    for page in doc:
        for text, _ in _rows(page):
            m = LABEL_RE.match(text)
            if m:
                out.add((int(m[1]), m[2] or m[3]))
    return out


def ict_scheme_check(n: int, ms_cut: fitz.Document, qp_cut: fitz.Document) -> str | None:
    """The scheme cut labels only question n and covers every part letter it prints."""
    labels = _labels(ms_cut)
    others = sorted({q for q, _ in labels if q != n})
    if others:
        return f'scheme cut labels question(s) {others}'
    qp_parts = set(QP_PART_RE.findall(' '.join(p.get_text() for p in qp_cut)))
    missing = sorted(qp_parts - {part for _, part in labels})
    return f'scheme cut lacks part(s) {missing} the question prints' if missing else None


def identity(paper, qp: fitz.Document, ms: fitz.Document) -> str | None:
    number = paper.paper_number
    cover = ' '.join(qp[0].get_text().split())
    if not re.search(rf'4IT1/0{re.escape(number)}\b', cover):
        return f'QP cover does not print 4IT1/0{number}'
    ms_cover = ' '.join(' '.join(p.get_text().split()) for p in list(ms)[:2])
    if not re.search(rf'4IT1\s*[/_]\s*0?{number[0]}', ms_cover):
        return f'mark scheme cover is not 4IT1 paper {number}'
    if str(paper.year) not in ms_cover or not any(w in ms_cover for w in SEASON_WORDS[paper.season]):
        return f'mark scheme cover is not {paper.season} {paper.year}'
    return None


def _settle(fresh: Path, target: Path) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.is_file() and _fingerprint(target) == _fingerprint(fresh):
        fresh.unlink()
    else:
        shutil.move(str(fresh), str(target))


def stage_one(paper, paired: bool) -> tuple[str, list[dict]]:
    if paper.paper_number.startswith('2'):
        return 'HELD: Paper 2 is an on-screen practical that needs data files', []
    if not paper.qp_path or not paper.ms_path:
        return 'HELD: missing QP or MS source', []
    if not paired:
        return 'HELD: content-pairing audit has no OK verdict for these URLs', []
    with fitz.open(paper.qp_path) as qp, fitz.open(paper.ms_path) as ms:
        why = identity(paper, qp, ms)
    if why:
        return f'HELD: {why}', []
    with tempfile.TemporaryDirectory() as tmp:
        staged = stage_paper(SUBJECT.code, paper, Path(tmp))
        if isinstance(staged, str):
            return f'HELD: {staged}', []
        numbers = [s['number'] for s in staged]
        if numbers != [1, 2, 3, 4, 5] or sum(s['marks'] for s in staged) != 100:
            return f'HELD: questions {[(s["number"], s["marks"]) for s in staged]} are not 1..5 totalling 100', []
        out = STAGE / 'segments' / paper.key
        rows = []
        with fitz.open(paper.ms_path) as ms:
            try:
                regions = scheme_regions(ms, numbers, lift_headers=True, start_re=LABEL_RE)
            except ValueError as exc:
                return f'HELD: {exc}', []
            for s in staged:
                qp_target = out / 'questions' / f"q{s['number']}.pdf"
                ms_target = out / 'markschemes' / f"q{s['number']}.pdf"
                _settle(Path(s['qp']), qp_target)
                ms_target.parent.mkdir(parents=True, exist_ok=True)
                write_stable(ms, regions[s['number']], ms_target)
                with fitz.open(ms_target) as ms_cut, fitz.open(qp_target) as qp_cut:
                    problem = ict_scheme_check(s['number'], ms_cut, qp_cut)
                rows.append({'paper': paper.key, 'question': s['number'], 'marks': s['marks'],
                             'verdict': 'HELD' if problem else 'LABEL_PROVEN',
                             'detail': problem or ('identity proven; scheme cut names only this question and '
                                                   'covers every part; content-pairing audit OK'),
                             'page_number': s['pages'][0], 'page_count': len(s['pages']),
                             'qp': str(qp_target.relative_to(ROOT)), 'ms': str(ms_target.relative_to(ROOT)),
                             'live_key': paper.key, 'paper_id': paper.paper_id})
    return f"{sum(r['verdict'] in PUBLISHABLE for r in rows)}/{len(rows)} proven", rows


def _sha256(rel: str) -> str:
    import hashlib  # noqa: PLC0415
    return hashlib.sha256((ROOT / rel).read_bytes()).hexdigest()


def apply_reviews(rows: list[dict]) -> list[dict]:
    """Promote a HELD row to REVIEWED_PROVEN when manual_review.json holds a
    decision for exactly these cuts (both SHA-256s match)."""
    path = STAGE / 'manual_review.json'
    decisions = json.loads(path.read_text(encoding='utf-8')) if path.is_file() else {}
    out = []
    for row in rows:
        d = decisions.get(cc.key_of(row))
        if (d and row['verdict'] == 'HELD' and d.get('verdict') == 'REVIEWED_PROVEN'
                and d.get('qp_sha256') == _sha256(row['qp']) and d.get('ms_sha256') == _sha256(row['ms'])):
            row = {**row, 'verdict': 'REVIEWED_PROVEN', 'detail': f"reviewed: {d['reason']}",
                   'held_because': row['detail']}
        out.append(row)
    return out


def stage() -> int:
    papers = sorted(load_live_papers(SUBJECT.code), key=lambda p: p.key)
    paired = pairing_verified(papers)
    notes, rows = {}, []
    for paper in papers:
        try:
            note, staged = stage_one(paper, paper.paper_id in paired)
        except (ValueError, RuntimeError, IndexError) as exc:
            note, staged = f'HELD: {exc}', []
        notes[paper.key] = note
        rows.extend(staged)
        print(f'4IT1 {paper.key:20} {note}')
        for r in staged:
            if r['verdict'] not in PUBLISHABLE:
                print(f"    q{r['question']}: {r['detail']}")
    rows = apply_reviews(rows)
    result = {'scope': 'Paper 1 written questions; complete questions; chapter filters',
              'chapters': {code: name for code, (name, _) in CHAPTERS.items()},
              'papers': notes, 'rows': sorted(rows, key=lambda r: (r['paper'], r['question']))}
    (STAGE / 'verdicts.json').write_text(json.dumps(result, indent=1), encoding='utf-8')
    tally = Counter(r['verdict'] for r in rows)
    print(f"4IT1: {dict(tally)}; publishable {sum(n for v, n in tally.items() if v in PUBLISHABLE)}")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('step', choices=['stage', 'dump', 'check', 'publish'])
    ap.add_argument('--execute', action='store_true')
    args = ap.parse_args()
    STAGE.mkdir(parents=True, exist_ok=True)
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
