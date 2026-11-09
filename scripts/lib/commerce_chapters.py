"""Shared steps for making an already-published IGCSE commerce subject chapterwise.

Business (4BS1) and Economics (4EC1) were published by onboard_igcse_commerce.py
with only whole-paper topics ("1"/"2"). Each subject's own script
(chapterwise_igcse_<subject>.py) supplies its specification chapters; this
module does the parts they share:

  dump   -> review.txt: every lettered part's own prompt, for reading
  check  -> validate topic_reads.json (topics, difficulty, reason, both SHA-256s)
            against the published set and the current segment PDFs, and write
            topics_new.json
  apply  -> back up, create chapter topic rows, write pages.topics/difficulty
            guarded by the old value, mirror difficulty to `questions`, sync
            `question_tags`, re-read, then retire the paper-scope topics.

A read whose PDF hash no longer matches is stale and blocks the run (rule 6).
"""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import re
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

import fitz

from lib.igcse_science_rebuild import PUBLISHABLE
from lib.live_paper_sources import REBUILD_DIR, ROOT, fetch_rows

# The pairing gate (AGENTS.md rule 5) is imported, never copied, so it cannot drift.
PUBLISHED = frozenset(PUBLISHABLE)
DIFFICULTIES = frozenset({'easy', 'medium', 'hard'})
PAPER_SCOPE_CODES = ('1', '2')
FURNITURE_RE = re.compile(
    r'GradeMax|PhysicsAndMathsTutor\S*|Turn over|DO NOT WRITE IN THIS AREA|\.{4,}|_{4,}|'
    r'\(Total for Question \d+ (?:is|=) ?\d+ marks?\)|\*P\d+A?\d*\*|P\d{5}[A-Z]?\d*|'
    r'©\s*\d{4} Pearson Education Ltd\.?|\S+ \| \d{4} \| [^|]+\| Paper \dR? \|', re.I)
PART_RE = re.compile(r'\((?:[a-h]|i{1,3}|iv|vi?)\)\s')


@dataclass(frozen=True)
class Subject:
    code: str
    subject_id: str
    chapters: dict[str, tuple[str, str]]   # code -> (name, specification topic)
    spec_label: str                        # used in topic descriptions

    @property
    def stage(self) -> Path:
        return REBUILD_DIR / self.code


def sha256(rel: str) -> str:
    return hashlib.sha256((ROOT / rel).read_bytes()).hexdigest()


def published_rows(subject: Subject) -> list[dict]:
    rows = json.loads((subject.stage / 'verdicts.json').read_text(encoding='utf-8'))['rows']
    return [r for r in rows if r['verdict'] in PUBLISHED]


def key_of(row: dict) -> str:
    return f"{row['paper']}|{row['question']}"


def cut_text(rel: str) -> str:
    with fitz.open(ROOT / rel) as doc:
        text = ' '.join(page.get_text() for page in doc)
    return ' '.join(FURNITURE_RE.sub(' ', text).split())


RUNNING_HEAD_RE = re.compile(r'[A-Z][A-Za-z ]+ · \d{4} · [^·]+ · Paper \dR? · (?:QP|MS)|\* ?[A-Z]?\d{3,6} ?\*')


def parts_view(text: str, head: int = 190, tail: int = 150) -> str:
    """Each lettered part once: its prompt, then the case setup leading into the next part."""
    text = ' '.join(RUNNING_HEAD_RE.sub(' ', text).split())
    cuts = [m.start() for m in PART_RE.finditer(text)]
    if not cuts:
        return text[:1200]
    pieces = [text[max(0, cuts[0] - 220):cuts[0]]]
    for a, b in zip(cuts, cuts[1:] + [len(text)]):
        piece = text[a:b]
        pieces.append(piece if len(piece) <= head + tail + 5 else f'{piece[:head]} … {piece[-tail:]}')
    return '\n   '.join(pieces)


def dump(subject: Subject, rows: list[dict], only_unread: bool = True) -> Path:
    reads = load_reads(subject)
    out = []
    for r in rows:
        if only_unread and key_of(r) in reads:
            continue
        out.append(f"### {key_of(r)}  [{r['marks']}m]")
        out.append('Q: ' + parts_view(cut_text(r['qp'])))
        out.append('')
    path = subject.stage / 'review.txt'
    path.write_text('\n'.join(out), encoding='utf-8')
    return path


def load_reads(subject: Subject) -> dict:
    path = subject.stage / 'topic_reads.json'
    return json.loads(path.read_text(encoding='utf-8')) if path.exists() else {}


def validate(subject: Subject, reads: dict, rows: list[dict]) -> list[str]:
    """Raise on a malformed or stale read; return the keys still unread."""
    by_key = {key_of(r): r for r in rows}
    unknown = sorted(set(reads) - set(by_key))
    if unknown:
        raise ValueError(f'reads for questions that are not published: {unknown[:10]}')
    for key, read in reads.items():
        codes = read.get('topics')
        if not codes or not isinstance(codes, list):
            raise ValueError(f'{key}: empty read')
        bad = [c for c in codes if c not in subject.chapters]
        if bad:
            raise ValueError(f'{key}: unknown chapter codes {bad}')
        if len(set(codes)) != len(codes):
            raise ValueError(f'{key}: duplicate codes {codes}')
        if read.get('difficulty') not in DIFFICULTIES:
            raise ValueError(f'{key}: difficulty must be one of {sorted(DIFFICULTIES)}')
        if not str(read.get('reason', '')).strip():
            raise ValueError(f'{key}: no reason recorded')
        row = by_key[key]
        for side in ('qp', 'ms'):
            if read.get(f'{side}_sha256') != sha256(row[side]):
                raise ValueError(f'{key}: {side.upper()} PDF changed since it was read; read it again')
    return sorted(set(by_key) - set(reads))


def check(subject: Subject) -> int:
    rows = published_rows(subject)
    reads = load_reads(subject)
    missing = validate(subject, reads, rows)
    out = {k: {'topics': reads[k]['topics'], 'difficulty': reads[k]['difficulty']} for k in sorted(reads)}
    (subject.stage / 'topics_new.json').write_text(json.dumps(out, indent=1), encoding='utf-8')
    counts = Counter(c for v in out.values() for c in v['topics'])
    print(f'{subject.code}: {len(rows)} published, {len(out)} read, {len(missing)} unread')
    print('  difficulty:', dict(Counter(v['difficulty'] for v in out.values())))
    for code, (name, _) in subject.chapters.items():
        print(f'  {code:6s} {name:48s} {counts.get(code, 0):4d}')
    if missing:
        print('  UNREAD:', missing[:20])
        return 1
    return 0


def stamp_hashes(subject: Subject, key: str, read: dict) -> dict:
    """Return a copy of `read` carrying the current SHA-256 of both PDFs."""
    row = {key_of(r): r for r in published_rows(subject)}[key]
    return {**read, 'qp_sha256': sha256(row['qp']), 'ms_sha256': sha256(row['ms'])}


# ---------------------------------------------------------------- apply

def _live_state(sb, subject: Subject):
    paper_ids = [p['id'] for p in fetch_rows(
        lambda o: sb.table('papers').select('id').eq('subject_id', subject.subject_id).range(o, o + 999))]
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
    topics = sb.table('topics').select('*').eq('subject_id', subject.subject_id).execute().data
    return indexed, mirror, tags, topics


def _plan(subject: Subject) -> dict:
    """Every staged publishable question's read, keyed by (paper_id, question).
    All of them must be read, including rows not yet live, so a later publish
    can never insert a question without chapters."""
    rows = published_rows(subject)
    reads = load_reads(subject)
    missing = validate(subject, reads, rows)
    if missing:
        raise SystemExit(f'refusing: {len(missing)} questions have no read, e.g. {missing[:5]}')
    return {(r['paper_id'], str(r['question'])): {k: reads[key_of(r)][k] for k in ('topics', 'difficulty')}
            for r in rows}


def restamp_ms(subject: Subject, note: str, execute: bool) -> int:
    """Re-pin ms_sha256 on reads whose mark scheme was re-cut but whose question
    paper is byte-identical. Chapters are read from the question, so the decision
    stands; the re-cut is recorded on the read. A changed QP is never re-stamped:
    that question must be read again."""
    by_key = {key_of(r): r for r in published_rows(subject)}
    reads = load_reads(subject)
    changed, qp_stale = {}, []
    for key, read in reads.items():
        row = by_key.get(key)
        if row is None:
            continue
        if read['qp_sha256'] != sha256(row['qp']):
            qp_stale.append(key)
            continue
        new_ms = sha256(row['ms'])
        if read['ms_sha256'] != new_ms:
            changed[key] = {**read, 'ms_sha256': new_ms, 'ms_restamped': note}
    print(f'{subject.code}: {len(changed)} reads to re-stamp (MS re-cut, QP unchanged); '
          f'{len(qp_stale)} with a changed QP (must be read again): {qp_stale[:10]}')
    if execute and changed:
        merged = {**reads, **changed}
        (subject.stage / 'topic_reads.json').write_text(
            json.dumps(dict(sorted(merged.items())), indent=1, ensure_ascii=False), encoding='utf-8')
        print('  written')
    return 1 if qp_stale else 0


def _pg_array(values: list[str] | None) -> str:
    return '{' + ','.join(f'"{v}"' for v in (values or [])) + '}'


def _write(sb, subject: Subject, plan, indexed, mirror, tags) -> dict:
    mirror_by_id = {q['id']: q for q in mirror}
    changed, by_level, desired = 0, {}, set()
    for key, want in plan.items():
        page = indexed[key]
        if page['topics'] != want['topics'] or page['difficulty'] != want['difficulty']:
            query = sb.table('pages').update({'topics': want['topics'], 'difficulty': want['difficulty']}) \
                .eq('id', page['id'])
            # Guard on the old values; NULL needs IS NULL, an '{}' literal never matches it.
            query = query.is_('topics', 'null') if page['topics'] is None \
                else query.filter('topics', 'eq', _pg_array(page['topics']))
            query = query.is_('difficulty', 'null') if page['difficulty'] is None \
                else query.eq('difficulty', page['difficulty'])
            res = query.execute()
            if len(res.data or []) != 1:
                raise SystemExit(f'guard failed for page {page["id"]}: row changed since it was read. '
                                 f'{changed} pages already written; re-run apply to resume from live '
                                 f'state (do not restore the backup over newer rows)')
            changed += 1
        if mirror_by_id[page['id']]['difficulty'] != want['difficulty']:
            by_level.setdefault(want['difficulty'], []).append(page['id'])
        desired.update((page['id'], c) for c in want['topics'])
    mirrored = 0
    for level, ids in by_level.items():
        for i in range(0, len(ids), 100):
            sb.table('questions').update({'difficulty': level}).in_('id', ids[i:i + 100]).execute()
            mirrored += len(ids[i:i + 100])
    current = {(t['question_id'], t['topic']) for t in tags}
    stale = [t['id'] for t in tags if (t['question_id'], t['topic']) not in desired]
    for i in range(0, len(stale), 100):
        sb.table('question_tags').delete().in_('id', stale[i:i + 100]).execute()
    added = [{'question_id': q, 'topic': c} for q, c in sorted(desired - current)]
    for i in range(0, len(added), 500):
        sb.table('question_tags').upsert(added[i:i + 500], on_conflict='question_id,topic').execute()
    return {'changed_pages': changed, 'changed_mirror': mirrored,
            'added_tags': len(added), 'removed_tags': len(stale)}


def _create_topics(sb, subject: Subject, existing: list[dict], used: set[str]) -> int:
    """Create the chapter rows that at least one question uses; an empty chapter
    would only show students a filter that returns nothing."""
    have = {t['code'] for t in existing}
    rows = [{'subject_id': subject.subject_id, 'code': code, 'name': name,
             'description': f'{topic} -- {subject.spec_label} section {code}'}
            for code, (name, topic) in subject.chapters.items() if code not in have and code in used]
    if rows:
        sb.table('topics').insert(rows).execute()
    return len(rows)


def _verify(plan: dict, after: tuple) -> list[str]:
    """Problems left after the write: pages, the `questions` mirror and
    `question_tags` must all match the plan before paper topics are retired."""
    pages, mirror, tags, _ = after
    mirror_by_id = {q['id']: q for q in mirror}
    tags_by_id: dict[str, set[str]] = {}
    for t in tags:
        tags_by_id.setdefault(t['question_id'], set()).add(t['topic'])
    problems = []
    for key, want in plan.items():
        page = pages.get(key)
        if page is None:
            problems.append(f'{key}: page missing')
            continue
        if page['topics'] != want['topics'] or page['difficulty'] != want['difficulty']:
            problems.append(f'{key}: page topics/difficulty')
        if mirror_by_id.get(page['id'], {}).get('difficulty') != want['difficulty']:
            problems.append(f'{key}: questions mirror difficulty')
        if tags_by_id.get(page['id'], set()) != set(want['topics']):
            problems.append(f'{key}: question_tags')
    return problems


def _retire_paper_topics(sb, subject: Subject, indexed_after: dict) -> int:
    if any(set(p['topics'] or []) & set(PAPER_SCOPE_CODES) for p in indexed_after.values()):
        raise SystemExit('refusing to retire paper topics: pages still use them')
    # Any page of the subject, question or not, still pointing at a paper topic blocks it.
    paper_ids = [p['id'] for p in fetch_rows(
        lambda o: sb.table('papers').select('id').eq('subject_id', subject.subject_id).range(o, o + 999))]
    for i in range(0, len(paper_ids), 50):
        part = paper_ids[i:i + 50]
        still = sb.table('pages').select('id').in_('paper_id', part) \
            .overlaps('topics', list(PAPER_SCOPE_CODES)).limit(1).execute().data
        if still:
            raise SystemExit(f'refusing to retire paper topics: page {still[0]["id"]} still uses them')
    res = sb.table('topics').delete().eq('subject_id', subject.subject_id) \
        .in_('code', list(PAPER_SCOPE_CODES)).execute()
    return len(res.data or [])


def apply(subject: Subject, sb, execute: bool) -> int:
    staged = _plan(subject)
    indexed, mirror, tags, topics = _live_state(sb, subject)
    live_only = sorted(set(indexed) - set(staged))
    if live_only:
        raise SystemExit(f'live questions with no staged read: {live_only[:5]}')
    plan = {k: v for k, v in staged.items() if k in indexed}
    not_live = len(staged) - len(plan)
    if not_live:
        print(f'  {not_live} staged questions are not live yet; they are read and will be '
              f'tagged when published')
    if {q['id'] for q in mirror} != {p['id'] for p in indexed.values()}:
        raise SystemExit('questions mirror incomplete; repair publication first')
    to_change = sum(1 for k, w in plan.items()
                    if indexed[k]['topics'] != w['topics'] or indexed[k]['difficulty'] != w['difficulty'])
    print(f'{subject.code}: {len(plan)} live questions, all read; {to_change} pages to change')
    print('  difficulty:', dict(Counter(v['difficulty'] for v in plan.values())))
    print('  chapters:', dict(sorted(Counter(c for v in plan.values() for c in v['topics']).items())))
    print('  topics now:', sorted(t['code'] for t in topics))
    if not execute:
        print('Dry run only. Re-run with --execute to write.')
        return 0
    folder = ROOT / 'data/backups' / f'{subject.code}_chapters_{dt.datetime.now():%Y%m%d_%H%M%S}'
    folder.mkdir(parents=True, exist_ok=True)
    for name, data in (('pages', list(indexed.values())), ('questions', mirror),
                       ('question_tags', tags), ('topics', topics)):
        (folder / f'{name}.json').write_text(json.dumps(data, indent=1), encoding='utf-8')
    print(f'backup: {folder.relative_to(ROOT)}')
    used = {c for v in plan.values() for c in v['topics']}
    result = {'created_topics': _create_topics(sb, subject, topics, used)}
    result.update(_write(sb, subject, plan, indexed, mirror, tags))
    after = _live_state(sb, subject)
    problems = _verify(plan, after)
    if problems:
        raise SystemExit(f're-read mismatch ({len(problems)}), e.g. {problems[:3]}; paper topics kept. '
                         f'Re-run apply to converge; backup in {folder}')
    result['retired_topics'] = _retire_paper_topics(sb, subject, after[0])
    result['backup'] = str(folder.relative_to(ROOT))
    (subject.stage / 'chapter_apply.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
    print(json.dumps(result, indent=2))
    return 0
