#!/usr/bin/env python3
"""
IAL Accounting (WAC11 Unit 1, WAC12 Unit 2) in the worksheet generator and test builder.

Questions are whole questions cut from each paper's Source Booklet; mark schemes are
cut from each question's start marker to the next. lib/ial_accounting_stage.py has
the cut and the proof; only PUBLISHABLE pairs are ever published (AGENTS.md rule 5).
Chapters are read from every question and recorded with both PDFs' SHA-256 in
data/analysis/live_rebuild/WAC/topic_reads.json (rule 6).

    python -X utf8 scripts/onboard_ial_accounting.py stage        # cut + prove -> verdicts.json
    python -X utf8 scripts/onboard_ial_accounting.py dump         # review.txt for reading (unread only)
    python -X utf8 scripts/onboard_ial_accounting.py check        # validate reads -> topics_new.json
    python -X utf8 scripts/onboard_ial_accounting.py publish      # dry run against live
    python -X utf8 scripts/onboard_ial_accounting.py publish --execute

Review decisions live in manual_review.json: {"<paper>|<q>": {"verdict": "REVIEWED_PROVEN",
"reason": ..., "qp_sha256": ..., "ms_sha256": ...}}. A decision applies only to a row
the checks held and only while both cuts are byte-identical to the ones reviewed.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import io
import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from lib import commerce_chapters as cc  # noqa: E402
from lib.ial_accounting_stage import stage_paper  # noqa: E402
from lib.ial_accounting_topics import CHAPTERS, SUBJECT  # noqa: E402
from lib.igcse_science_rebuild import PUBLISHABLE  # noqa: E402
from lib.live_paper_sources import ROOT, fetch_rows, load_live_papers, supabase_client  # noqa: E402
from lib.live_rebuild_common import pairing_verified  # noqa: E402

if sys.stdout.encoding != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

STAGE = SUBJECT.stage
R2_FOLDER = 'ial/accounting/pages-v2'
MARKS_FILE = ROOT / 'src' / 'lib' / 'ialAccountingQuestionMarks.json'


def sha256(rel: str) -> str:
    return hashlib.sha256((ROOT / rel).read_bytes()).hexdigest()


def apply_reviews(rows: list[dict]) -> list[dict]:
    """Rows with matching review decisions promoted to REVIEWED_PROVEN (new dicts)."""
    path = STAGE / 'manual_review.json'
    decisions = json.loads(path.read_text(encoding='utf-8')) if path.is_file() else {}
    out, used = [], set()
    for row in rows:
        key = cc.key_of(row)
        d = decisions.get(key)
        if d and row['verdict'] == 'HELD' and d.get('verdict') == 'REVIEWED_PROVEN' \
                and d.get('qp_sha256') == sha256(row['qp']) and d.get('ms_sha256') == sha256(row['ms']):
            out.append({**row, 'verdict': 'REVIEWED_PROVEN', 'detail': f"reviewed: {d['reason']}",
                        'held_because': row['detail']})
            used.add(key)
        else:
            out.append(row)
    stale = sorted(set(decisions) - used)
    if stale:
        print(f'  review decisions not applied (cut changed or row already proven): {stale}')
    return out


def stage() -> int:
    papers = sorted(load_live_papers('WAC'), key=lambda p: p.key)
    paired = pairing_verified(papers)
    notes, rows = {}, []
    for paper in papers:
        try:
            note, staged = stage_paper(paper, STAGE / 'segments', paper.paper_id in paired)
        except ValueError as exc:
            note, staged = f'HELD: {exc}', []
        notes[paper.key] = note
        rows.extend(staged)
        print(f'WAC {paper.key:22} {note}')
    rows = apply_reviews(rows)
    result = {'scope': 'Source Booklet questions; complete questions; chapter filters',
              'chapters': {code: name for code, (name, _) in CHAPTERS.items()},
              'papers': notes, 'rows': sorted(rows, key=lambda r: (r['paper'], r['question']))}
    (STAGE / 'verdicts.json').write_text(json.dumps(result, indent=1), encoding='utf-8')
    tally = Counter(r['verdict'] for r in rows)
    print(f"WAC: {dict(tally)}; publishable {sum(n for v, n in tally.items() if v in PUBLISHABLE)}")
    return 0


# ---------------------------------------------------------------- publish

def _live(sb) -> tuple[list[str], dict, list[dict]]:
    paper_ids = [p['id'] for p in fetch_rows(
        lambda o: sb.table('papers').select('id').eq('subject_id', SUBJECT.subject_id).range(o, o + 999))]
    pages = []
    for i in range(0, len(paper_ids), 50):
        part = paper_ids[i:i + 50]
        pages += fetch_rows(lambda o: sb.table('pages').select('*').in_('paper_id', part).range(o, o + 999))
    by_key = {(p['paper_id'], str(p['question_number'])): p for p in pages if p.get('is_question')}
    topics = sb.table('topics').select('*').eq('subject_id', SUBJECT.subject_id).execute().data or []
    return paper_ids, by_key, topics


def publish(execute: bool) -> int:
    import ingest_2026_papers as ing  # noqa: PLC0415 -- needs the env loaded by live_paper_sources

    rows = cc.published_rows(SUBJECT)
    reads = cc.load_reads(SUBJECT)
    missing = cc.validate(SUBJECT, reads, rows)
    if missing:
        raise SystemExit(f'refusing: {len(missing)} publishable questions have no read, e.g. {missing[:5]}')
    sb = supabase_client()
    paper_ids, live, topics = _live(sb)
    prefix = ing.R2_PUBLIC_URL + '/'
    inserts, uploads, tally = [], {}, Counter()
    for row in rows:
        if row['paper_id'] not in paper_ids:
            raise SystemExit(f"{row['paper']}: paper is not a WAC paper")
        read = reads[cc.key_of(row)]
        current = live.get((row['paper_id'], str(row['question'])))
        if current is not None:
            if current['topics'] != read['topics'] or current['difficulty'] != read['difficulty']:
                raise SystemExit(f'{cc.key_of(row)}: live row differs from the read; reconcile first')
            tally['already live'] += 1
            continue
        urls = {}
        for kind, suffix in (('qp', ''), ('ms', '_ms')):
            digest = sha256(row[kind])
            key = f"{R2_FOLDER}/{row['live_key']}/q{row['question']}{suffix}-{digest[:16]}.pdf"
            data = (ROOT / row[kind]).read_bytes()
            if not data.startswith(b'%PDF-'):
                raise SystemExit(f'{row[kind]} is not a PDF')
            uploads[key] = data
            urls[kind] = prefix + key
        inserts.append({'paper_id': row['paper_id'], 'question_number': str(row['question']),
                        'page_number': 1000 + row['question'], 'page_count': row['page_count'],
                        'is_question': True, 'topics': read['topics'], 'difficulty': read['difficulty'],
                        'qp_page_url': urls['qp'], 'ms_page_url': urls['ms'], 'has_diagram': False})
        tally['to insert'] += 1
    used = {c for r in rows for c in reads[cc.key_of(r)]['topics']}
    have = {t['code'] for t in topics}
    new_topics = [{'subject_id': SUBJECT.subject_id, 'code': code, 'name': CHAPTERS[code][0],
                   'description': f'{CHAPTERS[code][1]}. Complete questions keep all subparts '
                                  f'and may cover several chapters.'}
                  for code in sorted(used - have)]
    print(f"WAC [{'EXECUTE' if execute else 'DRY RUN'}]: {dict(tally)}; {len(uploads)} PDFs; "
          f"{len(new_topics)} chapter rows to create")
    print('  chapters:', dict(sorted(Counter(c for r in rows for c in reads[cc.key_of(r)]['topics']).items())))
    if not execute:
        print('Dry run only. Re-run with --execute to write.')
        return 0
    folder = ROOT / 'data' / 'backups' / f'WAC_onboarding_{dt.datetime.now():%Y%m%d_%H%M%S}'
    folder.mkdir(parents=True, exist_ok=True)
    (folder / 'before.json').write_text(json.dumps({'pages': list(live.values()), 'topics': topics}, indent=1),
                                        encoding='utf-8')
    print(f'backup: {folder.relative_to(ROOT)}')
    r2 = ing.get_r2()
    for key, data in uploads.items():  # every PDF is in R2 before any row points at it
        r2.put_object(Bucket=ing.R2_BUCKET, Key=key, Body=data, ContentType='application/pdf')
    print(f'  uploaded {len(uploads)} PDFs')
    if new_topics:
        sb.table('topics').insert(new_topics).execute()
    created = []
    for i in range(0, len(inserts), 50):
        data = sb.table('pages').insert(inserts[i:i + 50]).execute().data or []
        created += data
        (folder / 'created_page_ids.json').write_text(json.dumps([p['id'] for p in created]), encoding='utf-8')
        sb.table('questions').upsert([{'id': p['id'], 'paper_id': p['paper_id'],
                                       'question_number': p['question_number'], 'difficulty': p['difficulty'],
                                       'page_pdf_url': p['qp_page_url'], 'ms_pdf_url': p['ms_page_url'],
                                       'has_diagram': False} for p in data]).execute()
        sb.table('question_tags').upsert([{'question_id': p['id'], 'topic': t} for p in data for t in p['topics']],
                                         on_conflict='question_id,topic').execute()
    marks = json.loads(MARKS_FILE.read_text(encoding='utf-8')) if MARKS_FILE.is_file() else {}
    marks.update({f"{r['paper_id']}|{r['question']}": r['marks'] for r in rows})
    MARKS_FILE.write_text(json.dumps(dict(sorted(marks.items())), indent=2) + '\n', encoding='utf-8')
    _, after, _ = _live(sb)
    wrong = [cc.key_of(r) for r in rows
             if (after.get((r['paper_id'], str(r['question']))) or {}).get('topics') != reads[cc.key_of(r)]['topics']]
    print(f'  inserted {len(created)} questions; re-read mismatches: {wrong[:5] or "none"}')
    return 1 if wrong else 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('step', choices=['stage', 'dump', 'check', 'publish', 'restamp-ms'])
    ap.add_argument('--execute', action='store_true')
    ap.add_argument('--note', default='')
    args = ap.parse_args()
    if args.step == 'stage':
        return stage()
    if args.step == 'dump':
        path = cc.dump(SUBJECT, cc.published_rows(SUBJECT))
        print(f'wrote {path.relative_to(ROOT)}')
        return 0
    if args.step == 'check':
        return cc.check(SUBJECT)
    if args.step == 'restamp-ms':
        if not args.note.strip():
            ap.error('restamp-ms needs --note')
        return cc.restamp_ms(SUBJECT, args.note, args.execute)
    return publish(args.execute)


if __name__ == '__main__':
    sys.exit(main())
