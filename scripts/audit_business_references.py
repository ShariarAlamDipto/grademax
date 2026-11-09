"""Read-only check of formulae, shared cases, and five missed pre-Q1 cases.

The source-introduction anchors below were read during the 21 October audit.
They locate document content, not chapter classifications or pairing proofs.
"""
from collections import Counter
import hashlib
import json
from pathlib import Path
import re

import fitz

from lib.igcse_science_rebuild import PUBLISHABLE, first_question_spot
from lib.live_paper_sources import ROOT

INTRO_ANCHORS = {
    '2021_may-jun_P2': 'NEXT is a well-known clothing retailer',
    '2021_oct-nov_P2': 'Huawei is a leading global provider',
    '2026_may-jun_P1': 'Crumb',
    '2026_may-jun_P1R': 'Ernie Rhodes started a family business',
    '2026_may-jun_P2R': 'Apple was started in the US in 1976',
}


def words(text):
    return Counter(re.findall(r'\w+', text.lower()))


def main():
    base = ROOT / 'data/analysis/live_rebuild/4BS1'
    out = base / 'audit_2026-10-21'
    out.mkdir(parents=True, exist_ok=True)
    staged = json.loads((base / 'verdicts.json').read_text())['rows']
    rows = [r for r in staged if r['verdict'] in PUBLISHABLE]
    introductions = {}
    for paper, anchor in INTRO_ANCHORS.items():
        with fitz.open(base / 'sources' / f'{paper}_qp.pdf') as source:
            first = first_question_spot(source)
            page = source[first.page]
            matches = page.search_for(anchor)
            if not matches:
                raise RuntimeError(f'{paper}: reviewed introduction anchor missing')
            start = min(r.y0 for r in matches)
            rect = fitz.Rect(40, start - 1, page.rect.width - 40, first.top - 4)
            text = ' '.join(page.get_text(clip=rect).split())
            if len(text.split()) < 40:
                raise RuntimeError(f'{paper}: introduction extraction unexpectedly short')
            introductions[paper] = {'sourcePage': first.page + 1,
                                    'sourceRegion': list(rect), 'text': text}
    checks = []
    for r in rows:
        with fitz.open(ROOT / r['qp']) as cut:
            text = ' '.join(p.get_text() for p in cut)
        actual = words(text)
        has_formulae = bool(re.search('FORMULAE FOR INTERNATIONAL GCSE BUSINESS', text, re.I))
        case = base / 'segments' / r['paper'] / 'case_study.pdf'
        expected = introductions.get(r['paper'])
        if expected is None and case.exists():
            with fitz.open(case) as doc:
                case_text = ' '.join(p.get_text() for p in doc)
            # A known raw crop starts with the margin fragment "OT WRITE...".
            case_text = re.sub(r'\b(?:DO N)?OT WRITE IN THIS A(?:REA)?\b', '', case_text)
            expected = {'text': case_text}
        missing = list((words(expected['text']) - actual).elements()) if expected else []
        checks.append({'paper': r['paper'], 'question': r['question'],
                       'hasFormulaSheet': has_formulae,
                       'caseReference': 'reviewed source introduction' if r['paper'] in introductions else 'staged shared case',
                       'caseAvailableForCheck': expected is not None,
                       'missingCaseWords': missing,
                       'qpSha256': hashlib.sha256((ROOT / r['qp']).read_bytes()).hexdigest(),
                       'msSha256': hashlib.sha256((ROOT / r['ms']).read_bytes()).hexdigest()})
    failures = [r for r in checks if not r['hasFormulaSheet'] or not r['caseAvailableForCheck'] or r['missingCaseWords']]
    report = {'code': '4BS1', 'questions': len(checks), 'reviewedIntroductions': introductions,
              'checks': checks, 'failures': failures}
    (out / 'references-audit.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(f'{len(checks)} questions checked; {len(failures)} fail reference completeness')
    for r in failures:
        print(r['paper'], r['question'], 'missing introduction words:', len(r['missingCaseWords']))


if __name__ == '__main__':
    main()
