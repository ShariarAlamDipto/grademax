"""Insert-only publisher for a subject onboarded with chapter reads from the start.

Used by each subject's own onboarding script (rule 4: one script per subject; this
is the shared body). It publishes only PUBLISHABLE staged questions, and only when
every one of them has a current read (lib/commerce_chapters.validate):

  dry run   counts what would be inserted and which chapter rows are missing;
  --execute backs up the subject's live pages and topics, uploads every PDF to R2
            before any row points at it, creates the chapter rows the questions use,
            inserts pages + questions mirror + question_tags, writes the subject's
            marks file, then re-reads and reports any mismatch.

It never updates or deletes a live row. A live row whose chapters or difficulty
differ from its read stops the run (change tags with a guarded update instead).
"""
from __future__ import annotations

import datetime as dt
import hashlib
import json
from collections import Counter
from pathlib import Path

from lib import commerce_chapters as cc
from lib.live_paper_sources import ROOT, fetch_rows, supabase_client


def _sha256(rel: str) -> str:
    return hashlib.sha256((ROOT / rel).read_bytes()).hexdigest()


def _live(sb, subject: cc.Subject) -> tuple[list[str], dict, list[dict]]:
    paper_ids = [p['id'] for p in fetch_rows(
        lambda o: sb.table('papers').select('id').eq('subject_id', subject.subject_id).range(o, o + 999))]
    pages = []
    for i in range(0, len(paper_ids), 50):
        part = paper_ids[i:i + 50]
        pages += fetch_rows(lambda o: sb.table('pages').select('*').in_('paper_id', part).range(o, o + 999))
    by_key = {(p['paper_id'], str(p['question_number'])): p for p in pages if p.get('is_question')}
    topics = sb.table('topics').select('*').eq('subject_id', subject.subject_id).execute().data or []
    return paper_ids, by_key, topics


def publish(subject: cc.Subject, r2_folder: str, marks_file: Path, execute: bool) -> int:
    import ingest_2026_papers as ing  # noqa: PLC0415 -- needs the env loaded by live_paper_sources

    rows = cc.published_rows(subject)
    reads = cc.load_reads(subject)
    missing = cc.validate(subject, reads, rows)
    if missing:
        raise SystemExit(f'refusing: {len(missing)} publishable questions have no read, e.g. {missing[:5]}')
    sb = supabase_client()
    paper_ids, live, topics = _live(sb, subject)
    prefix = ing.R2_PUBLIC_URL + '/'
    inserts, uploads, tally = [], {}, Counter()
    for row in rows:
        if row['paper_id'] not in paper_ids:
            raise SystemExit(f"{row['paper']}: paper is not a {subject.code} paper")
        read = reads[cc.key_of(row)]
        current = live.get((row['paper_id'], str(row['question'])))
        if current is not None:
            if current['topics'] != read['topics'] or current['difficulty'] != read['difficulty']:
                raise SystemExit(f'{cc.key_of(row)}: live row differs from the read; reconcile first')
            tally['already live'] += 1
            continue
        urls = {}
        for kind, suffix in (('qp', ''), ('ms', '_ms')):
            key = f"{r2_folder}/{row['live_key']}/q{row['question']}{suffix}-{_sha256(row[kind])[:16]}.pdf"
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
    new_topics = [{'subject_id': subject.subject_id, 'code': code, 'name': subject.chapters[code][0],
                   'description': f'{subject.chapters[code][1]}. Complete questions keep all subparts '
                                  f'and may cover several chapters.'}
                  for code in sorted(used - have)]
    print(f"{subject.code} [{'EXECUTE' if execute else 'DRY RUN'}]: {dict(tally)}; {len(uploads)} PDFs; "
          f"{len(new_topics)} chapter rows to create")
    print('  chapters:', dict(sorted(Counter(c for r in rows for c in reads[cc.key_of(r)]['topics']).items())))
    if not execute:
        print('Dry run only. Re-run with --execute to write.')
        return 0
    folder = ROOT / 'data' / 'backups' / f'{subject.code}_onboarding_{dt.datetime.now():%Y%m%d_%H%M%S}'
    folder.mkdir(parents=True, exist_ok=True)
    (folder / 'before.json').write_text(json.dumps({'pages': list(live.values()), 'topics': topics}, indent=1),
                                        encoding='utf-8')
    print(f'backup: {folder.relative_to(ROOT)}')
    r2 = ing.get_r2()
    for key, data in uploads.items():
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
    write_marks(rows, marks_file)
    _, after, _ = _live(sb, subject)
    wrong = [cc.key_of(r) for r in rows
             if (after.get((r['paper_id'], str(r['question']))) or {}).get('topics') != reads[cc.key_of(r)]['topics']]
    print(f'  inserted {len(created)} questions; re-read mismatches: {wrong[:5] or "none"}')
    return 1 if wrong else 0


def write_marks(rows: list[dict], marks_file: Path) -> None:
    """paperId|question -> printed marks, for the PDF covers (src/lib/questionMarks.ts)."""
    marks = json.loads(marks_file.read_text(encoding='utf-8')) if marks_file.is_file() else {}
    marks.update({f"{r['paper_id']}|{r['question']}": r['marks'] for r in rows})
    marks_file.write_text(json.dumps(dict(sorted(marks.items())), indent=2) + '\n', encoding='utf-8')
