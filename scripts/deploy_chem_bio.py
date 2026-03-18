#!/usr/bin/env python3
"""
GradeMax -- Chemistry & Biology Chapter Deployment
==================================================
Runs all 4 deployment steps in order:
  1. Check DB connection and current state
  2. Replace old 5-topic entries with 31 (chem) + 27 (bio) chapter topics
  3. Reset pages.topics for chem/bio (ready for re-classification)
  4. Re-classify all pages using keyword scorer + Gemini fallback

Usage:
  python scripts/deploy_chem_bio.py                  # full deploy
  python scripts/deploy_chem_bio.py --step 1         # check only
  python scripts/deploy_chem_bio.py --step 2         # topics migration only
  python scripts/deploy_chem_bio.py --step 3         # reset pages only
  python scripts/deploy_chem_bio.py --step 4         # classify only
  python scripts/deploy_chem_bio.py --dry-run        # preview, no writes
"""

import os
import sys
import json
import time
import re
import argparse
import yaml
from pathlib import Path
from dotenv import load_dotenv

env_path = Path(__file__).parent.parent / '.env.local'
load_dotenv(env_path)

try:
    from supabase import create_client, Client
except ImportError:
    print("[ERR]  pip install supabase python-dotenv pyyaml")
    sys.exit(1)

try:
    import requests
except ImportError:
    print("[ERR]  pip install requests")
    sys.exit(1)

SUPABASE_URL = os.getenv('NEXT_PUBLIC_SUPABASE_URL')
SERVICE_KEY  = os.getenv('SUPABASE_SERVICE_ROLE_KEY')
GEMINI_KEY   = os.getenv('GEMINI_API_KEY')
CONFIG_DIR   = Path(__file__).parent.parent / 'config'

SUBJECTS = {
    'chemistry': {'code': '4CH1', 'yaml': 'chemistry_topics.yaml'},
    'biology':   {'code': '4BI1', 'yaml': 'biology_topics.yaml'},
}

# -----------------------------------------------------------------------------
# STEP 1 -- Health check
# -----------------------------------------------------------------------------

def step1_check(sb: Client):
    print("\n" + "="*60)
    print("STEP 1 -- Checking database state")
    print("="*60)

    all_ok = True
    for name, meta in SUBJECTS.items():
        code = meta['code']
        subj = sb.table('subjects').select('id,name,code').eq('code', code).execute()
        if not subj.data:
            print(f"  [ERR]  Subject {code} not found in DB")
            all_ok = False
            continue

        sid = subj.data[0]['id']
        print(f"  [OK]  {name.capitalize()} ({code})  id={sid[:8]}...")

        # current topics
        topics = sb.table('topics').select('code,name').eq('subject_id', sid).execute()
        codes  = [t['code'] for t in topics.data]
        print(f"      topics now : {sorted(codes)}")

        # paper + page counts
        papers = sb.table('papers').select('id').eq('subject_id', sid).execute()
        pids   = [p['id'] for p in papers.data]
        print(f"      papers     : {len(pids)}")

        if pids:
            pages = sb.table('pages').select('id,topics').in_('paper_id', pids).eq('is_question', True).execute()
            tagged   = sum(1 for p in pages.data if p.get('topics'))
            untagged = len(pages.data) - tagged
            print(f"      pages total: {len(pages.data)}  tagged={tagged}  untagged={untagged}")

        # check yaml exists
        yaml_path = CONFIG_DIR / meta['yaml']
        if yaml_path.exists():
            with open(yaml_path, encoding='utf-8') as f:
                cfg = yaml.safe_load(f)
            print(f"      yaml topics: {len(cfg['topics'])} chapters  [OK]")
        else:
            print(f"      [ERR]  yaml missing: {yaml_path}")
            all_ok = False

    if all_ok:
        print("\n  [OK]  All checks passed -- ready to deploy")
    else:
        print("\n  [ERR]  Fix above issues before continuing")
    return all_ok


# -----------------------------------------------------------------------------
# STEP 2 -- Replace topics table entries
# -----------------------------------------------------------------------------

def step2_topics(sb: Client, dry_run: bool):
    print("\n" + "="*60)
    print("STEP 2 -- Replacing topic entries in DB")
    print("="*60)

    for name, meta in SUBJECTS.items():
        code  = meta['code']
        subj  = sb.table('subjects').select('id').eq('code', code).single().execute()
        sid   = subj.data['id']

        yaml_path = CONFIG_DIR / meta['yaml']
        with open(yaml_path, 'r', encoding='utf-8') as f:
            cfg = yaml.safe_load(f)

        print(f"\n  {name.upper()} ({code})  --  {len(cfg['topics'])} chapters")

        # Delete old topics
        existing = sb.table('topics').select('code').eq('subject_id', sid).execute()
        old_codes = [t['code'] for t in existing.data]
        print(f"    Removing {len(old_codes)} old topics: {sorted(old_codes)}")

        if not dry_run:
            sb.table('topics').delete().eq('subject_id', sid).execute()

        # Insert new topics
        rows = []
        for t in cfg['topics']:
            rows.append({
                'subject_id':  sid,
                'code':        t['id'],
                'name':        t['name'],
                'description': t.get('description', ''),
                'keywords':    t.get('keywords', []),
            })

        print(f"    Inserting {len(rows)} new chapter topics ...")
        if not dry_run:
            # Insert in batches of 20
            for i in range(0, len(rows), 20):
                batch = rows[i:i+20]
                sb.table('topics').insert(batch).execute()
                print(f"    ... {min(i+20, len(rows))}/{len(rows)}", end='\r')
            print()

        print(f"    [OK]  Done -- {len(rows)} topics {'(dry run)' if dry_run else 'inserted'}")

    print("\n  [OK]  Step 2 complete")


# -----------------------------------------------------------------------------
# STEP 3 -- Reset pages.topics for re-classification
# -----------------------------------------------------------------------------

def step3_reset_pages(sb: Client, dry_run: bool):
    print("\n" + "="*60)
    print("STEP 3 -- Resetting pages.topics for re-classification")
    print("="*60)

    for name, meta in SUBJECTS.items():
        code  = meta['code']
        subj  = sb.table('subjects').select('id').eq('code', code).single().execute()
        sid   = subj.data['id']

        papers = sb.table('papers').select('id').eq('subject_id', sid).execute()
        pids   = [p['id'] for p in papers.data]
        print(f"\n  {name.upper()}  --  {len(pids)} papers")

        if not pids:
            print("    No papers found, skipping")
            continue

        # Count pages
        pages = sb.table('pages').select('id').in_('paper_id', pids).eq('is_question', True).execute()
        print(f"    {len(pages.data)} question pages will be reset")

        if not dry_run:
            # Reset in batches
            ids = [p['id'] for p in pages.data]
            for i in range(0, len(ids), 100):
                batch = ids[i:i+100]
                sb.table('pages').update({
                    'topics': [],
                    'confidence': None,
                }).in_('id', batch).execute()
                print(f"    ... reset {min(i+100, len(ids))}/{len(ids)}", end='\r')
            print()
            print(f"    [OK]  Reset {len(ids)} pages")
        else:
            print(f"    (dry run) would reset {len(pages.data)} pages")

    print("\n  [OK]  Step 3 complete")


# -----------------------------------------------------------------------------
# STEP 4 -- Classify pages
# -----------------------------------------------------------------------------

EASY_WORDS  = ['define', 'state', 'name', 'identify', 'label', 'give', 'list',
               'write down', 'complete the table', 'write the formula', 'what is meant by']
HARD_WORDS  = ['design an experiment', 'evaluate', 'discuss', 'assess', 'justify',
               'suggest why', 'analyse', 'deduce', 'devise', 'plan an experiment']
MEDIUM_WORDS = ['calculate', 'explain', 'describe', 'compare', 'suggest', 'draw',
               'predict', 'show that', 'write an equation', 'balance', 'determine']

def estimate_difficulty(text: str) -> str:
    t = text.lower()
    for h in HARD_WORDS:
        if h in t:
            return 'hard'
    for e in EASY_WORDS:
        if t.strip().startswith(e) or f' {e} ' in t:
            return 'easy'
    for m in MEDIUM_WORDS:
        if m in t:
            return 'medium'
    return 'medium'


class KeywordClassifier:
    def __init__(self, config: dict):
        self.topics    = {t['id']: t for t in config['topics']}
        self.negatives = [n.lower() for n in config.get('negatives', [])]
        self._build_index(config)

    def _build_index(self, config: dict):
        self.index: dict[str, list[tuple[str, float]]] = {}
        for topic in config['topics']:
            tid = topic['id']
            for kw in topic.get('keywords', []):
                self.index.setdefault(kw.lower(), []).append((tid, 3.0))
            for f in topic.get('formulas', []):
                self.index.setdefault(f.lower(), []).append((tid, 5.0))
            for s in topic.get('synonyms', []):
                self.index.setdefault(s.lower(), []).append((tid, 2.0))
            for w in topic.get('description', '').lower().split():
                w = re.sub(r'[^a-z0-9]', '', w)
                if len(w) > 4:
                    self.index.setdefault(w, []).append((tid, 0.5))

    def classify(self, text: str) -> tuple[str | None, float]:
        t = text.lower()
        scores: dict[str, float] = {}
        for kw, hits in self.index.items():
            if kw in t:
                for tid, w in hits:
                    scores[tid] = scores.get(tid, 0.0) + w
        if not scores:
            return None, 0.0
        best   = max(scores, key=lambda k: scores[k])
        total  = sum(scores.values())
        conf   = min(scores[best] / (total + 1e-9), 1.0)
        sv     = sorted(scores.values(), reverse=True)
        if len(sv) > 1:
            margin = (sv[0] - sv[1]) / (sv[0] + 1e-9)
            conf   = min(conf + margin * 0.3, 1.0)
        return best, round(conf, 3)


def gemini_classify(text: str, topics: dict, api_key: str) -> tuple[str | None, float]:
    topic_list = '\n'.join(
        f"  {tid}: {t['name']} -- {t.get('description','')[:80]}"
        for tid, t in topics.items()
    )
    prompt = (
        "You are an Edexcel IGCSE examiner. "
        "Classify this exam question into ONE topic.\n\n"
        f"TOPICS:\n{topic_list}\n\n"
        f"QUESTION:\n{text[:500]}\n\n"
        'Return ONLY JSON: {"topic": "<id>", "confidence": 0.0-1.0}'
    )
    url = (
        "https://generativelanguage.googleapis.com/v1beta/models/"
        f"gemini-2.0-flash:generateContent?key={api_key}"
    )
    try:
        r = requests.post(url, json={
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": 0.1, "maxOutputTokens": 80}
        }, timeout=20)
        r.raise_for_status()
        raw = r.json()['candidates'][0]['content']['parts'][0]['text'].strip()
        raw = re.sub(r'^```[a-z]*\n?', '', raw).rstrip('`').strip()
        data = json.loads(raw)
        return str(data['topic']), float(data.get('confidence', 0.75))
    except Exception as e:
        return None, 0.0


def step4_classify(sb: Client, dry_run: bool):
    print("\n" + "="*60)
    print("STEP 4 -- Classifying pages (Keyword + Gemini fallback)")
    print("="*60)

    if not GEMINI_KEY:
        print("  [WARN]  GEMINI_API_KEY not set -- keyword-only mode")

    for name, meta in SUBJECTS.items():
        code = meta['code']
        subj = sb.table('subjects').select('id').eq('code', code).single().execute()
        sid  = subj.data['id']

        # Load config
        yaml_path = CONFIG_DIR / meta['yaml']
        with open(yaml_path, 'r', encoding='utf-8') as f:
            cfg = yaml.safe_load(f)
        classifier = KeywordClassifier(cfg)

        # Get valid topic codes from DB (post-migration)
        db_topics = sb.table('topics').select('code').eq('subject_id', sid).execute()
        valid_codes = {t['code'] for t in db_topics.data}
        print(f"\n  {name.upper()} -- {len(valid_codes)} topics in DB")

        # Fetch unclassified pages
        papers = sb.table('papers').select('id').eq('subject_id', sid).execute()
        pids   = [p['id'] for p in papers.data]
        if not pids:
            print("    No papers -- skipping")
            continue

        all_pages = (
            sb.table('pages')
            .select('id,text_excerpt,question_number')
            .in_('paper_id', pids)
            .eq('is_question', True)
            .execute()
        )
        pages_to_tag = [p for p in all_pages.data if not p.get('topics')]
        print(f"    Total question pages : {len(all_pages.data)}")
        print(f"    Unclassified (empty) : {len(pages_to_tag)}")

        if not pages_to_tag:
            print("    [OK]  All pages already classified")
            continue

        # Stats
        topic_counts      = {c: 0 for c in valid_codes}
        difficulty_counts = {'easy': 0, 'medium': 0, 'hard': 0}
        kw_hits  = 0
        llm_hits = 0
        fallback = 0
        errors   = 0

        updates: list[dict] = []
        total = len(pages_to_tag)

        for i, page in enumerate(pages_to_tag):
            text = (page.get('text_excerpt') or '').strip()
            if not text:
                errors += 1
                continue

            topic_id, conf = classifier.classify(text)

            # Gemini fallback for low confidence
            if GEMINI_KEY and (topic_id is None or conf < 0.45):
                llm_id, llm_conf = gemini_classify(
                    text, {t['id']: t for t in cfg['topics']}, GEMINI_KEY
                )
                if llm_id and llm_conf > conf:
                    topic_id, conf = llm_id, llm_conf
                    llm_hits += 1
                    time.sleep(0.35)  # ~3 req/s → well under 15 RPM limit
                else:
                    kw_hits += 1
            else:
                kw_hits += 1

            # Final fallback -- first valid code
            if topic_id not in valid_codes:
                topic_id = sorted(valid_codes)[0]
                conf     = 0.10
                fallback += 1

            difficulty = estimate_difficulty(text)

            topic_counts[topic_id]       = topic_counts.get(topic_id, 0) + 1
            difficulty_counts[difficulty] = difficulty_counts.get(difficulty, 0) + 1

            updates.append({
                'id':         page['id'],
                'topics':     [topic_id],
                'confidence': conf,
                'difficulty': difficulty,
            })

            # Flush every 50
            if len(updates) >= 50:
                if not dry_run:
                    for u in updates:
                        sb.table('pages').update({
                            'topics':     u['topics'],
                            'confidence': u['confidence'],
                            'difficulty': u['difficulty'],
                        }).eq('id', u['id']).execute()
                updates = []
                pct = (i + 1) / total * 100
                print(f"    Progress: {i+1}/{total} ({pct:.0f}%)  "
                      f"kw={kw_hits} llm={llm_hits} fallback={fallback}", end='\r')

        # Final flush
        if updates and not dry_run:
            for u in updates:
                sb.table('pages').update({
                    'topics':     u['topics'],
                    'confidence': u['confidence'],
                    'difficulty': u['difficulty'],
                }).eq('id', u['id']).execute()

        print(f"\n    [OK]  Classified {total - errors} pages  "
              f"(keyword={kw_hits}, gemini={llm_hits}, fallback={fallback}, no-text={errors})")

        # Topic distribution
        print(f"\n    Topic distribution ({name}):")
        for code in sorted(topic_counts.keys()):
            n   = topic_counts[code]
            bar = '#' * min(n // max(1, total // 40), 35)
            print(f"      {code:<6}  {n:>4}  {bar}")

        # Difficulty
        print(f"\n    Difficulty split:")
        total_tagged = sum(difficulty_counts.values()) or 1
        for diff in ['easy', 'medium', 'hard']:
            n   = difficulty_counts[diff]
            pct = n / total_tagged * 100
            print(f"      {diff:<8}  {n:>4}  ({pct:.0f}%)")

    print("\n  [OK]  Step 4 complete")


# -----------------------------------------------------------------------------
# MAIN
# -----------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description='Deploy Chemistry & Biology chapter topics')
    parser.add_argument('--step', type=int, choices=[1, 2, 3, 4],
                        help='Run a specific step only (default: all)')
    parser.add_argument('--dry-run', action='store_true',
                        help='Preview actions without writing to DB')
    args = parser.parse_args()

    if not SUPABASE_URL or not SERVICE_KEY:
        print("[ERR]  Missing NEXT_PUBLIC_SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY")
        sys.exit(1)

    sb: Client = create_client(SUPABASE_URL, SERVICE_KEY)

    print("\n== GradeMax -- Chemistry & Biology Chapter Deployment ==")
    if args.dry_run:
        print("    DRY RUN MODE -- no writes will happen\n")

    steps = [args.step] if args.step else [1, 2, 3, 4]

    if 1 in steps:
        ok = step1_check(sb)
        if not ok and not args.step:
            print("\n[ERR]  Aborting -- fix issues above before deploying")
            sys.exit(1)

    if 2 in steps:
        step2_topics(sb, args.dry_run)

    if 3 in steps:
        step3_reset_pages(sb, args.dry_run)

    if 4 in steps:
        step4_classify(sb, args.dry_run)

    print("\n" + "="*60)
    print("    Deployment complete!")
    print("="*60 + "\n")


if __name__ == '__main__':
    main()
