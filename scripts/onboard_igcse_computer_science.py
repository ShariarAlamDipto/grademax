#!/usr/bin/env python3
"""Stage complete Edexcel 4CP0 questions under GradeMax's existing 4CP1 ID.

Reuse the established segmenter and pairing proof gate. Practical questions
requiring external files are held until those dependencies can be supplied.
Chapter decisions are direct reads pinned to both PDF hashes, never keywords.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import hashlib
from functools import partial
import json
from pathlib import Path
import re

import fitz

from onboard_igcse_commerce import cached_papers
from lib.igcse_science_rebuild import PUBLISHABLE, prove_paper, stage_paper
from lib.live_paper_sources import REBUILD_DIR, ROOT
from lib.live_rebuild_common import pairing_verified
from lib import igcse_science_rebuild as science
from lib.live_rebuild_common import TESSDATA
from lib.paper_fingerprint import identify, BARCODE_RE

CODE = '4CP1'
BASE = REBUILD_DIR / CODE
CHAPTERS = {
    '1': 'Problem solving', '2': 'Programming', '3': 'Data',
    '4': 'Computers', '5': 'Communication and the internet',
    '6': 'The bigger picture',
}


def ocr_picture_pages(path):
    """OCR sparse picture pages, retaining vector text and blank pages.

    Avoid garbage=3 deduplication: these Pearson files have deeply shared
    resources and that optional optimisation can spend minutes at save time.
    Atomic writes also keep an interrupted OCR cache from being reused.
    """
    out = path.with_name(path.stem + '.ocrp.pdf')
    if out.is_file() and out.stat().st_size:
        return out
    with fitz.open(path) as source, fitz.open() as result:
        for index, page in enumerate(source):
            if len(page.get_text().strip()) >= 250 or not page.get_images():
                result.insert_pdf(source, from_page=index, to_page=index)
            else:
                data = page.get_pixmap(dpi=200).pdfocr_tobytes(language='eng', tessdata=str(TESSDATA))
                with fitz.open('pdf', data) as single:
                    result.insert_pdf(single)
        temp = out.with_suffix('.tmp.pdf')
        result.save(temp, garbage=0, deflate=True)
    temp.replace(out)
    return out


DEPENDENCIES = re.compile(
    r'\bopen\s+(?:the\s+file\s+)?Q\d{1,2}[a-z]?\s+in\s+the\s+code\s+editor'
    r'|\b(?:open|load|amend|edit|complete|use)\b.{0,100}'
    r'(?:\.(?:py|cs|java|txt|csv)\b|\b(?:data|source|program) files?\b)', re.I | re.S)


def pdf_text(path):
    with fitz.open(path) as doc:
        return '\n'.join(p.get_text() for p in doc)


def fingerprint(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def validate_read(row, read):
    if not isinstance(read, dict) or not read.get('reason', '').strip():
        raise ValueError('Missing direct chapter read/reason')
    tags = read.get('topics')
    if not isinstance(tags, list) or not tags or any(t not in CHAPTERS for t in tags) or len(tags) != len(set(tags)):
        raise ValueError('Invalid chapter tags')
    if read.get('difficulty') not in ('easy', 'medium', 'hard'):
        raise ValueError('Invalid reviewed difficulty')
    for kind in ('qp', 'ms'):
        if read.get(f'{kind}_sha256') != fingerprint(ROOT / row[kind]):
            raise ValueError(f'Stale {kind} chapter read')
    return tags


def stage():
    science.ocr_image_pages = ocr_picture_pages
    science.write_cut = partial(science.write_cut, garbage=0)
    papers = cached_papers(CODE)
    pairing = pairing_verified(papers)
    decisions_file = BASE / 'manual_review.json'
    decisions = json.loads(decisions_file.read_text()) if decisions_file.exists() else {}
    rows, notes = [], {}
    for paper in sorted(papers, key=lambda p: (p.paper_number, p.key)):
        if not paper.qp_path or not paper.ms_path:
            notes[paper.key] = 'HELD: missing source'
            continue
        covers = [pdf_text(p).split('\f')[0] for p in (paper.qp_path, paper.ms_path)]
        identity = rf'\b4CP0\s*[/_]\s*0?{paper.paper_number}(?=[\W_]|$)'
        if not all(re.search(identity, text, re.I) for text in covers):
            notes[paper.key] = 'HELD: source identity mismatch'
            continue
        if str(paper.paper_number).startswith('2') and DEPENDENCIES.search(covers[0]):
            notes[paper.key] = 'HELD: practical paper requires external source/data files'
            print(paper.key, notes[paper.key], flush=True)
            continue
        staged = stage_paper(CODE, paper, BASE / 'segments', decisions)
        if isinstance(staged, str):
            notes[paper.key] = f'HELD: {staged}'
            print(paper.key, notes[paper.key], flush=True)
            continue
        proven = prove_paper(CODE, paper, staged, decisions, paper.paper_id in pairing)
        for row in proven:
            # Paper 2 is an on-screen assessment. A filename alone is not enough
            # to make its tasks usable in a standalone PDF worksheet.
            if str(paper.paper_number).startswith('2') and DEPENDENCIES.search(pdf_text(ROOT / row['qp'])):
                row['verdict'] = 'DEPENDENCY_HELD'
                row['detail'] = 'Practical task requires external source/data files'
        rows.extend(proven)
        notes[paper.key] = dict(Counter(r['verdict'] for r in proven))
        print(paper.key, notes[paper.key], flush=True)
    report = {'scope': 'Edexcel 4CP0; complete questions; reviewed specification chapters',
              'chapters': CHAPTERS, 'papers': notes, 'rows': rows}
    (BASE / 'verdicts.json').write_text(json.dumps(report, indent=2), encoding='utf-8')


def review_dump():
    report = json.loads((BASE / 'verdicts.json').read_text())
    chunks = []
    for row in report['rows']:
        chunks.append(f"### {row['paper']}|{row['question']} [{row['marks']} marks] {row['verdict']}")
        chunks.append('QP: ' + pdf_text(ROOT / row['qp']))
        chunks.append('MS: ' + pdf_text(ROOT / row['ms']))
    (BASE / 'review.txt').write_text('\n'.join(chunks), encoding='utf-8')


def audit():
    report = json.loads((BASE / 'verdicts.json').read_text())
    reads = json.loads((BASE / 'topic_reads.json').read_text())
    eligible = [r for r in report['rows'] if r['verdict'] in PUBLISHABLE]
    keys = {f"{r['paper']}|{r['question']}" for r in eligible}
    if set(reads) != keys:
        raise ValueError(f'Chapter read coverage mismatch: missing={sorted(keys - set(reads))}, stale={sorted(set(reads) - keys)}')
    counts = Counter()
    hashes = set()
    grouped = defaultdict(list)
    papers = {p.key: p for p in cached_papers(CODE)}
    paired = pairing_verified(list(papers.values()))
    identities = {}
    for key in {r['paper'] for r in eligible}:
        paper = papers[key]
        identity = {}
        for kind, source in [('qp', paper.qp_path), ('ms', paper.ms_path)]:
            with fitz.open(source) as doc:
                identity[kind] = identify([p.get_text() for p in doc])
            ident = identity[kind]
            if ident['unit'] != '4CP0' or int(ident['paper']) != 1:
                raise ValueError(f'{key}: wrong {kind} subject/paper')
            expected = (paper.year, paper.season)
            actual = (ident['year'], ident['season'])
            # Cancelled summer 2020 papers were used in the autumn series.
            deferred = (kind == 'qp' and expected == (2020, 'oct-nov') and actual == (2020, 'may-jun'))
            if actual != expected and not (paper.paper_id in paired and (ident['year'] is None or deferred)):
                raise ValueError(f'{key}: unverified {kind} sitting {actual}')
        if paper.paper_id not in paired:
            raise ValueError(f'{key}: missing current whole-paper pairing evidence')
        identities[key] = identity
    for row in eligible:
        key = f"{row['paper']}|{row['question']}"
        grouped[row['paper']].append(row)
        counts.update(validate_read(row, reads[key]))
        if not isinstance(row['marks'], int) or row['marks'] <= 0:
            raise ValueError(f'{key}: invalid marks')
        with fitz.open(ROOT / row['qp']) as doc:
            if len(doc) != row['page_count']:
                raise ValueError(f'{key}: wrong page count')
            text = '\n'.join(page.get_text() for page in doc)
            totals = science.QP_TOTAL_RE.findall(text)
            if totals != [(str(row['question']), str(row['marks']))]:
                raise ValueError(f'{key}: missing/wrong question fence {totals}')
            barcodes = set(BARCODE_RE.findall(text))
            if barcodes != {identities[row['paper']]['qp']['barcode']}:
                raise ValueError(f'{key}: wrong question source barcode')
        for kind in ('qp', 'ms'):
            path = ROOT / row[kind]
            digest = fingerprint(path)
            if digest in hashes:
                raise ValueError(f'{key}: duplicate PDF')
            hashes.add(digest)
            with fitz.open(path) as doc:
                if not len(doc):
                    raise ValueError(f'{key}: empty PDF')
    for key, paper_rows in grouped.items():
        if sorted(r['question'] for r in paper_rows) != list(range(1, 7)) or sum(r['marks'] for r in paper_rows) != 80:
            raise ValueError(f'{key}: incomplete question or mark coverage')
    result = {'questions': len(eligible), 'chapter_counts': dict(counts),
              'verdicts': dict(Counter(r['verdict'] for r in report['rows'])),
              'source_identity': identities,
              'verdicts_sha256': fingerprint(BASE / 'verdicts.json'),
              'reads_sha256': fingerprint(BASE / 'topic_reads.json'), 'failures': []}
    (BASE / 'artifact_audit.json').write_text(json.dumps(result, indent=2))
    print(json.dumps({k: v for k, v in result.items() if k != 'source_identity'}, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['stage', 'dump', 'audit'])
    args = parser.parse_args()
    {'stage': stage, 'dump': review_dump, 'audit': audit}[args.action]()
