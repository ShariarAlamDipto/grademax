"""Read-only structural and source-content checks, shared by subject audits.

This does not classify chapters or promote pairing verdicts. It records signals
for a reviewer, including source-region completeness and independent MS labels.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import asdict
import hashlib
import json
from pathlib import Path
import re
import sys

import fitz

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from lib.igcse_science_rebuild import PUBLISHABLE, question_segments, upright
from lib.live_ms_linkage import read_evidence, judge
from lib.live_paper_sources import ROOT


def visible_words(page):
    # show_pdf_page retains hidden source text outside the visible crop.
    return page.get_text('words', clip=page.rect)


def scheme_tail(cut_path, source_path):
    """Find the last cut page in the whole MS, then inspect every later page.

    Unlike the segmenter's content heuristic, assessment-grid pages and answer
    continuations count as content even if they repeat no question labels.
    Publisher address pages are reported separately, never as missing answers.
    """
    with fitz.open(cut_path) as cut, fitz.open(source_path) as source:
        text = ' '.join(w[4] for w in visible_words(cut[-1]))
        words = Counter(re.findall(r'\w+', text.lower()))
        scores = []
        for page in source:
            sw = Counter(re.findall(r'\w+', page.get_text().lower()))
            scores.append(sum((words & sw).values()) / max(1, sum(words.values())))
        index = max(range(len(scores)), key=scores.__getitem__)
        omitted, publisher = [], []
        for i in range(index + 1, len(source)):
            text = ' '.join(source[i].get_text().split())
            if text.startswith('Pearson Education Limited.'):
                publisher.append(i + 1)
                continue
            clean = re.sub(r'GradeMax|\b4(?:AC|BS|EC)1\b', '', text)
            if len(re.findall(r'[A-Za-z]{3,}', clean)) >= 8:
                omitted.append({'sourcePage': i + 1, 'text': text})
        return {'lastSourcePageCovered': index + 1, 'sourcePages': len(source),
                'lastPageMatch': round(scores[index], 4), 'omitted': omitted,
                'publisherPagesExcluded': publisher}


def audit_pdf_bank(code: str):
    base = ROOT / 'data/analysis/live_rebuild' / code
    out = base / 'audit_2026-10-21'
    out.mkdir(parents=True, exist_ok=True)
    staged = json.loads((base / 'verdicts.json').read_text(encoding='utf-8'))
    rows = [r for r in staged['rows'] if r['verdict'] in PUBLISHABLE]
    by_paper = defaultdict(list)
    for r in rows:
        by_paper[r['paper']].append(r)
    results, papers = [], []
    for paper, published in sorted(by_paper.items()):
        source = base / 'sources' / f'{paper}_qp.pdf'
        with fitz.open(upright(source)) as doc:
            segments, why = question_segments(doc)
            segments_by_number = {s.number: s for s in segments}
            source_cover = ' '.join(doc[0].get_text().split())
            papers.append({'paper': paper, 'sourceCover': source_cover, 'sourceSegmentationIssue': why,
                           'sourceQuestions': len(segments), 'publishedQuestions': len(published),
                           'publishedMarks': sum(r['marks'] for r in published),
                           'sourceMarks': sum(s.marks or 0 for s in segments)})
            for r in published:
                signals = []
                qp_path, ms_path = ROOT / r['qp'], ROOT / r['ms']
                qp, ms = read_evidence(qp_path, is_ms=False), read_evidence(ms_path, is_ms=True)
                v, detail = judge(r['question'], qp, ms)
                if v not in ('PROVEN', 'LABEL_ONLY'):
                    signals.append({'issue': 'independent pairing needs review', 'verdict': v, 'detail': detail})
                labels = sorted(set(ms.labels))
                if labels != [r['question']]:
                    signals.append({'issue': 'MS labels need review', 'labels': labels})
                page_info = {}
                for kind, path in [('qp', qp_path), ('ms', ms_path)]:
                    with fitz.open(path) as cut:
                        page_info[kind] = [{'width': round(p.rect.width, 2), 'height': round(p.rect.height, 2),
                                            'visibleWords': len(visible_words(p))} for p in cut]
                        if any(p.rect.height < 24 for p in cut):
                            signals.append({'issue': 'very short crop', 'kind': kind})
                s = segments_by_number.get(r['question'])
                comparisons = []
                if s:
                    with fitz.open(qp_path) as cut:
                        # Business prepends the formula sheet and shared case. The
                        # final pages must still contain every own-question region.
                        own_pages = list(cut)[-len(s.regions):]
                        if len(own_pages) != len(s.regions):
                            signals.append({'issue': 'QP page count below source regions'})
                        else:
                            for cp, (source_page, top, bottom) in zip(own_pages, s.regions):
                                sp = doc[source_page]
                                rect = fitz.Rect(0, top or 0, sp.rect.width, bottom if bottom is not None else sp.rect.height)
                                expected = [w[4] for w in sp.get_text('words', clip=rect)]
                                actual = [w[4] for w in visible_words(cp)]
                                # A word comparison catches missing prompts/table
                                # values; graphics get a separate visual review.
                                ec, ac = Counter(expected), Counter(actual)
                                missing, extra = list((ec-ac).elements()), list((ac-ec).elements())
                                comparisons.append({'sourcePage': source_page + 1, 'missingWords': missing, 'extraWords': extra})
                                if missing or extra:
                                    signals.append({'issue': 'QP visible content differs from source region', 'sourcePage': source_page + 1,
                                                    'missingWords': missing, 'extraWords': extra})
                else:
                    signals.append({'issue': 'cannot reconstruct question source regions'})
                tail = None
                if r['question'] == len(segments):
                    tail = scheme_tail(ms_path, base / 'sources' / f'{paper}_ms.pdf')
                    if tail['omitted']:
                        signals.append({'issue': 'MS omits trailing answer or assessment pages',
                                        'sourcePages': [p['sourcePage'] for p in tail['omitted']]})
                results.append({'paper': paper, 'question': r['question'], 'marks': r['marks'],
                                'stagedVerdict': r['verdict'], 'independentVerdict': v, 'detail': detail,
                                'qpEvidence': asdict(qp), 'msEvidence': asdict(ms), 'msLabels': labels,
                                'pageInfo': page_info, 'sourceComparisons': comparisons, 'schemeTail': tail,
                                'qpSha256': hashlib.sha256(qp_path.read_bytes()).hexdigest(),
                                'msSha256': hashlib.sha256(ms_path.read_bytes()).hexdigest(), 'signals': signals})
        print(f'{code} {paper}: {len(published)} pairs checked', flush=True)
    report = {'code': code, 'questions': len(results), 'papers': papers, 'rows': results,
              'independentVerdicts': dict(Counter(r['independentVerdict'] for r in results)),
              'signalCounts': dict(Counter(s['issue'] for r in results for s in r['signals']))}
    (out / 'pdf-audit.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(json.dumps({k: v for k, v in report.items() if k not in ('papers', 'rows')}, indent=2), flush=True)

