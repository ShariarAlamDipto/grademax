#!/usr/bin/env python3
"""
Add the IGCSE Business papers the first onboarding held back to the tool bank.

The 4BS1 bank holds 140 questions: every 4BS1 paper has only four 20-mark
questions. onboard_igcse_commerce.py held two kinds of paper:

  * Oct/Nov 2025 Paper 1 and 2 -- the site has no mark scheme (Pearson
    time-locks the series). Pearson's schemes were obtained from Paperlords and
    are checked here against our own question papers.
  * the 4BS0 papers of 2011-2018 -- the previous specification, five 20-mark
    questions on the same business content, read into the 4BS1 chapters.

Only these paper keys are staged; the 140 live questions and their cuts are never
touched. Questions are cut by the shared total-line segmenter (with the formulae
sheet and shared case study added, as for every 4BS1 question); schemes are cut by
position from each question's start marker to the next (lib/ial_accounting_stage).

A question is publishable only when the paper's identity is proven (QP and MS
codes, session and year agree; the question totals add up to the paper total) and
its scheme cut names only its own question and covers every part it prints. It is
LABEL_PROVEN when the content-pairing audit also judged the paper OK, and
REVIEWED_PROVEN when a recorded review decision in manual_review.json carries the
evidence for a paper the audit never saw (Oct/Nov 2025). Anything else is HELD.

    python -X utf8 scripts/extend_igcse_business_bank.py import-ms --paper 2025_oct-nov_P1 --file <pdf>
    python -X utf8 scripts/extend_igcse_business_bank.py stage
    python -X utf8 scripts/chapterwise_igcse_business.py dump      # then read, then check
    node --env-file=.env.local scripts/publish-commerce-questions.mjs --subject 4BS1 [--execute]
    python -X utf8 scripts/chapterwise_igcse_business.py apply [--execute]
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import re
import shutil
import sys
import tempfile
from pathlib import Path

import fitz

sys.path.insert(0, str(Path(__file__).resolve().parent))

from lib.ial_accounting_stage import _fingerprint, scheme_check, scheme_regions, write_stable  # noqa: E402
from lib.igcse_science_rebuild import PUBLISHABLE, stage_paper  # noqa: E402
from lib.live_paper_sources import REBUILD_DIR, ROOT  # noqa: E402
from lib.live_rebuild_common import pairing_verified  # noqa: E402
from onboard_igcse_commerce import add_business_formulae, cached_papers  # noqa: E402

if sys.stdout.encoding != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

CODE = '4BS1'
STAGE = REBUILD_DIR / CODE
TARGETS = [f'{y}_may-jun_P1' for y in range(2011, 2019)] + ['2025_oct-nov_P1', '2025_oct-nov_P2']
SEASON_WORDS = {'may-jun': ('June', 'Summer'), 'oct-nov': ('November', 'October'), 'jan': ('January',)}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _flat(doc: fitz.Document, pages: int | None = None) -> str:
    return ' '.join(' '.join(p.get_text().split()) for p in list(doc)[:pages])


def identity(paper, qp: fitz.Document, ms: fitz.Document) -> str | None:
    """None when the QP and MS are both this paper's; otherwise why not."""
    legacy = paper.year <= 2018
    code = '4BS0' if legacy else '4BS1'
    number = paper.paper_number.rstrip('R')
    cover = _flat(qp, 2)
    if not re.search(rf'{code}\s*/\s*0?{number}', cover):
        return f'QP cover does not print {code}/0{number}'
    ms_cover = _flat(ms, 2)
    # Old schemes print the code with the letter O ("4BSO_01"), so match loosely.
    if not re.search(rf'4BS[01O]\s*[/_|( ]*\s*0?{number}\b|{code}\)? Paper 0?{number}', ms_cover) \
            and not (legacy and '4BS0' in ms_cover):
        return f'mark scheme cover is not {code} paper {number}'
    if str(paper.year) not in ms_cover:
        return f'mark scheme cover is not {paper.year}'
    if not any(w in ms_cover for w in SEASON_WORDS[paper.season]):
        return f'mark scheme cover is not the {paper.season} session'
    return None


def _settle(fresh: Path, target: Path) -> None:
    """Move a cut into place, keeping the existing bytes when the content is unchanged."""
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.is_file() and _fingerprint(target) == _fingerprint(fresh):
        fresh.unlink()
    else:
        shutil.move(str(fresh), str(target))


def stage_one(paper, paired: bool, decisions: dict) -> tuple[str, list[dict]]:
    if not paper.qp_path or not paper.ms_path:
        return 'HELD: missing QP or MS source', []
    with fitz.open(paper.qp_path) as qp, fitz.open(paper.ms_path) as ms:
        why = identity(paper, qp, ms)
    if why:
        return f'HELD: {why}', []
    with tempfile.TemporaryDirectory() as tmp:
        staged = stage_paper(CODE, paper, Path(tmp))
        if isinstance(staged, str):
            return f'HELD: {staged}', []
        add_business_formulae(paper, staged)
        numbers = [s['number'] for s in staged]
        expected = 5 if paper.year <= 2018 else 4
        if numbers != list(range(1, expected + 1)) or any(s['marks'] != 20 for s in staged):
            return f'HELD: questions {[(s["number"], s["marks"]) for s in staged]} are not 1..{expected} x 20', []
        out = STAGE / 'segments' / paper.key
        rows = []
        with fitz.open(paper.ms_path) as ms:
            try:
                regions = scheme_regions(ms, numbers, lift_headers=True)
            except ValueError as exc:
                return f'HELD: {exc}', []
            for s in staged:
                qp_target = out / 'questions' / f"q{s['number']}.pdf"
                ms_target = out / 'markschemes' / f"q{s['number']}.pdf"
                _settle(Path(s['qp']), qp_target)
                ms_target.parent.mkdir(parents=True, exist_ok=True)
                write_stable(ms, regions[s['number']], ms_target)
                with fitz.open(ms_target) as ms_cut, fitz.open(qp_target) as qp_cut:
                    problem = scheme_check(s['number'], ms_cut, qp_cut)
                key = f'{paper.key}|{s["number"]}'
                decision = decisions.get(key, {})
                reviewed = (decision.get('verdict') == 'REVIEWED_PROVEN'
                            and decision.get('qp_sha256') == sha256(qp_target)
                            and decision.get('ms_sha256') == sha256(ms_target))
                if problem:
                    verdict, detail = 'HELD', problem
                elif paired:
                    verdict, detail = 'LABEL_PROVEN', ('identity proven; scheme cut names only this question '
                                                       'and covers every part; content-pairing audit OK')
                elif reviewed:
                    verdict, detail = 'REVIEWED_PROVEN', f"reviewed: {decision['reason']}"
                else:
                    verdict, detail = 'HELD', 'identity and cut proven, but no pairing evidence or review decision'
                rows.append({'paper': paper.key, 'question': s['number'], 'marks': 20, 'verdict': verdict,
                             'detail': detail, 'page_number': s['pages'][0], 'page_count': len(s['pages']),
                             'qp': str(qp_target.relative_to(ROOT)), 'ms': str(ms_target.relative_to(ROOT)),
                             'live_key': paper.key, 'paper_id': paper.paper_id,
                             'topic': paper.paper_number.rstrip('R')})
    proven = sum(r['verdict'] in PUBLISHABLE for r in rows)
    return f'{proven}/{len(rows)} proven', rows


def stage() -> int:
    papers = {p.key: p for p in cached_papers(CODE)}
    paired = pairing_verified(list(papers.values()))
    review_path = STAGE / 'manual_review.json'
    decisions = json.loads(review_path.read_text(encoding='utf-8')) if review_path.is_file() else {}
    verdicts_path = STAGE / 'verdicts.json'
    staged = json.loads(verdicts_path.read_text(encoding='utf-8'))
    keep = [r for r in staged['rows'] if r['paper'] not in TARGETS]
    new = []
    for key in TARGETS:
        paper = papers.get(key)
        if paper is None:
            print(f'{key:20} not a live paper')
            continue
        try:
            note, rows = stage_one(paper, paper.paper_id in paired, decisions)
        except (ValueError, RuntimeError, IndexError) as exc:
            note, rows = f'HELD: {exc}', []
        staged['papers'][key] = note
        new += rows
        print(f'{key:20} {note}')
        for r in rows:
            if r['verdict'] not in PUBLISHABLE:
                print(f"    q{r['question']}: {r['detail']}")
    staged['rows'] = sorted(keep + new, key=lambda r: (r['paper'], r['question']))
    verdicts_path.write_text(json.dumps(staged, indent=1), encoding='utf-8')
    print(f'4BS1 bank: {sum(r["verdict"] in PUBLISHABLE for r in staged["rows"])} publishable '
          f'({sum(r["verdict"] in PUBLISHABLE for r in new)} from these papers)')
    return 0


def import_ms(paper_key: str, file: Path) -> int:
    """Place a scheme obtained outside the live site into sources/ for staging."""
    if paper_key not in ('2025_oct-nov_P1', '2025_oct-nov_P2'):
        raise SystemExit('only the Oct/Nov 2025 schemes are imported this way')
    data = file.read_bytes()
    if not data.startswith(b'%PDF-'):
        raise SystemExit(f'{file} is not a PDF')
    target = STAGE / 'sources' / f'{paper_key}_ms.pdf'
    if target.is_file() and target.read_bytes() != data:
        raise SystemExit(f'{target} exists with different content; refusing to overwrite')
    target.write_bytes(data)
    print(f'wrote {target.relative_to(ROOT)} (sha256 {sha256(target)[:16]})')
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('step', choices=['stage', 'import-ms'])
    ap.add_argument('--paper')
    ap.add_argument('--file', type=Path)
    args = ap.parse_args()
    if args.step == 'import-ms':
        if not args.paper or not args.file:
            ap.error('import-ms needs --paper and --file')
        return import_ms(args.paper, args.file)
    return stage()


if __name__ == '__main__':
    sys.exit(main())
