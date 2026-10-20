#!/usr/bin/env python3
"""
Make IGCSE Accounting (4AC1) chapterwise in the test builder and worksheet generator.

Codex's onboarding (onboard_igcse_commerce.py) published 276 questions tagged
only "1"/"2" -- whole-paper topics -- with no difficulty. This replaces them
with the 20 specification chapters read by classify_accounting_tool_topics.py
(data/analysis/live_rebuild/4AC1/topics_new.json):

  1. create the 20 chapter rows in `topics` (codes "1.1" .. "5.4");
  2. write `pages.topics` + `pages.difficulty`, mirror difficulty to `questions`,
     and set `question_tags` to exactly the chapters;
  3. only then delete the two paper-scope topic rows, which nothing points at
     any more.

Difficulty follows the three 4AC1 question sizes (lib/accounting_topics.py):
1-mark MCQ easy, 5-mark short answer medium, 15/25-mark structured hard. The
test builder filters on difficulty, so untagged rows vanished from every
difficulty-filtered test.

Everything touched is backed up to data/backups/accounting_chapters_<stamp>/.

    python -X utf8 scripts/apply_accounting_tool_topics.py            # dry run
    python -X utf8 scripts/apply_accounting_tool_topics.py --execute
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from classify_accounting_tool_topics import key_of, published_rows, validate  # noqa: E402
from lib.accounting_topics import CHAPTERS, CODE, SUBJECT_ID, difficulty  # noqa: E402
from lib.live_paper_sources import REBUILD_DIR, ROOT, fetch_rows, supabase_client  # noqa: E402

STAGE = REBUILD_DIR / CODE
PAPER_SCOPE_CODES = {'1', '2'}


def load_plan() -> dict[tuple[str, str], dict]:
    rows = published_rows()
    tags = json.loads((STAGE / 'topics_new.json').read_text(encoding='utf-8'))
    validate(tags, {key_of(r) for r in rows})
    missing = [key_of(r) for r in rows if key_of(r) not in tags]
    if missing:
        raise SystemExit(f'refusing: {len(missing)} questions have no read, e.g. {missing[:5]}')
    return {(r['paper_id'], str(r['question'])): {'topics': tags[key_of(r)],
                                                   'difficulty': difficulty(int(r['marks']))}
            for r in rows}


def live_state(sb) -> tuple[dict, list, list, list]:
    paper_ids = [p['id'] for p in fetch_rows(
        lambda o: sb.table('papers').select('id').eq('subject_id', SUBJECT_ID).range(o, o + 999))]
    pages = []
    for i in range(0, len(paper_ids), 50):
        part = paper_ids[i:i + 50]
        pages += fetch_rows(lambda o: sb.table('pages').select('*').in_('paper_id', part)
                            .eq('is_question', True).range(o, o + 999))
    indexed = {}
    for page in pages:
        key = (page['paper_id'], str(page['question_number']))
        if key in indexed:
            raise SystemExit(f'duplicate live question {key}')
        indexed[key] = page
    ids = [p['id'] for p in pages]
    mirror, tags = [], []
    for i in range(0, len(ids), 100):
        part = ids[i:i + 100]
        mirror += fetch_rows(lambda o: sb.table('questions').select('*').in_('id', part).range(o, o + 999))
        tags += fetch_rows(lambda o: sb.table('question_tags').select('*').in_('question_id', part)
                           .range(o, o + 999))
    topics = sb.table('topics').select('*').eq('subject_id', SUBJECT_ID).execute().data
    return indexed, mirror, tags, topics


def backup(**tables) -> Path:
    folder = ROOT / 'data/backups' / f'accounting_chapters_{dt.datetime.now():%Y%m%d_%H%M%S}'
    folder.mkdir(parents=True, exist_ok=True)
    for name, rows in tables.items():
        (folder / f'{name}.json').write_text(json.dumps(rows, indent=1), encoding='utf-8')
    return folder


def create_topics(sb, existing: list[dict]) -> int:
    have = {t['code'] for t in existing}
    rows = [{'subject_id': SUBJECT_ID, 'code': code, 'name': name,
             'description': f'{topic} -- 4AC1 specification section {code}'}
            for code, (name, topic) in CHAPTERS.items() if code not in have]
    if rows:
        sb.table('topics').insert(rows).execute()
    return len(rows)


def write_questions(sb, plan, indexed, mirror, tags) -> dict:
    mirror_by_id = {q['id']: q for q in mirror}
    changed_pages, by_level = 0, {}
    desired = set()
    for key, want in plan.items():
        page = indexed[key]
        if page['topics'] != want['topics'] or page['difficulty'] != want['difficulty']:
            sb.table('pages').update({'topics': want['topics'], 'difficulty': want['difficulty']}) \
                .eq('id', page['id']).execute()
            changed_pages += 1
        if mirror_by_id[page['id']]['difficulty'] != want['difficulty']:
            by_level.setdefault(want['difficulty'], []).append(page['id'])
        desired.update((page['id'], c) for c in want['topics'])
    changed_mirror = 0
    for level, ids in by_level.items():
        for i in range(0, len(ids), 100):
            sb.table('questions').update({'difficulty': level}).in_('id', ids[i:i + 100]).execute()
            changed_mirror += len(ids[i:i + 100])
    current = {(t['question_id'], t['topic']) for t in tags}
    stale = [t['id'] for t in tags if (t['question_id'], t['topic']) not in desired]
    for i in range(0, len(stale), 100):
        sb.table('question_tags').delete().in_('id', stale[i:i + 100]).execute()
    added = [{'question_id': q, 'topic': c} for q, c in sorted(desired - current)]
    for i in range(0, len(added), 500):
        sb.table('question_tags').upsert(added[i:i + 500], on_conflict='question_id,topic').execute()
    return {'changed_pages': changed_pages, 'changed_mirror': changed_mirror,
            'added_tags': len(added), 'removed_tags': len(stale)}


def retire_paper_topics(sb) -> int:
    still = [p for p in fetch_rows(lambda o: sb.table('pages').select('id,topics,paper_id')
                                   .overlaps('topics', sorted(PAPER_SCOPE_CODES)).range(o, o + 999))]
    paper_ids = {p['id'] for p in fetch_rows(
        lambda o: sb.table('papers').select('id').eq('subject_id', SUBJECT_ID).range(o, o + 999))}
    if any(p['paper_id'] in paper_ids for p in still):
        raise SystemExit('refusing to retire paper topics: Accounting pages still use them')
    res = sb.table('topics').delete().eq('subject_id', SUBJECT_ID) \
        .in_('code', sorted(PAPER_SCOPE_CODES)).execute()
    return len(res.data or [])


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--execute', action='store_true')
    args = ap.parse_args()
    plan = load_plan()
    sb = supabase_client()
    indexed, mirror, tags, topics = live_state(sb)
    if set(indexed) != set(plan):
        only_live = sorted(set(indexed) - set(plan))[:5]
        only_plan = sorted(set(plan) - set(indexed))[:5]
        raise SystemExit(f'live questions differ from the reviewed set: live-only {only_live}, '
                         f'plan-only {only_plan}')
    if {q['id'] for q in mirror} != {p['id'] for p in indexed.values()}:
        raise SystemExit('questions mirror incomplete; repair publication first')
    print(f'{CODE}: {len(plan)} live questions, all read')
    print('  difficulty:', dict(Counter(v['difficulty'] for v in plan.values())))
    print('  chapters:', dict(sorted(Counter(c for v in plan.values() for c in v['topics']).items())))
    print('  topics now:', sorted(t['code'] for t in topics))
    if not args.execute:
        print('Dry run only. Re-run with --execute to write.')
        return 0
    folder = backup(pages=list(indexed.values()), questions=mirror, question_tags=tags, topics=topics)
    print(f'backup: {folder.relative_to(ROOT)}')
    created = create_topics(sb, topics)
    result = write_questions(sb, plan, indexed, mirror, tags)
    result.update(created_topics=created, retired_topics=retire_paper_topics(sb),
                  backup=str(folder.relative_to(ROOT)))
    (STAGE / 'chapter_apply.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
    print(json.dumps(result, indent=2))
    return 0


if __name__ == '__main__':
    sys.exit(main())
