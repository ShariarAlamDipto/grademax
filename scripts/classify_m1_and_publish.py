#!/usr/bin/env python3
"""Classify every Mechanics 1 (WME01) question and publish topics to Supabase.

Context
-------
M1 was re-segmented from clean question papers into
`data/processed/Mechanics_1_resegmented/` and pushed to R2 + Supabase, but every
`pages` row still carried the fallback topic `['1']` -- classification had never
run, so the topic filter could not discriminate.

This script closes that gap:
  1. read each per-question QP PDF from the re-segmented set
  2. extract text with PyMuPDF (NOT PyPDF2 -- these PDFs need fitz)
  3. classify to one M1 topic via MistralTopicClassifier (Groq)
  4. write topics / difficulty / confidence onto the matching `pages` row

Rows are matched to files by the FILENAME in `qp_page_url`, which is exactly the
local PDF name (e.g. `2012_Jan_P1_Q1.pdf`) -- an exact join, no guessing.

LLM results are cached to `--cache` so re-runs are free and idempotent.

Dry-run by default; pass --commit to write to Supabase.

Usage:
    python -X utf8 scripts/classify_m1_and_publish.py                 # dry-run
    python -X utf8 scripts/classify_m1_and_publish.py --commit
    python -X utf8 scripts/classify_m1_and_publish.py --commit --prune-orphans
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from collections import Counter
from pathlib import Path

import fitz  # PyMuPDF
import requests
from dotenv import load_dotenv

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).parent))

SEGMENTED_DIR = REPO_ROOT / "data" / "processed" / "Mechanics_1_resegmented"
QP_DIR = SEGMENTED_DIR / "pages"
TOPICS_YAML = REPO_ROOT / "classification" / "mechanics_1_topics.yaml"
DEFAULT_CACHE = REPO_ROOT / "data" / "analysis" / "m1_classification_cache.json"

SUBJECT_CODE = "WME01"
SUBJECT_ID = "4d54f2aa-ee9c-470a-814b-8f6095ec9278"

# The YAML carries both an id ("M1.3") and a short code ("KINEM"); the classifier
# may return either, but `pages.topics` must hold the DB topic code -> "M1.x".
CODE_TO_ID = {
    "MODEL": "M1.1", "VECT": "M1.2", "KINEM": "M1.3", "DYNAM": "M1.4",
    "MOMENT": "M1.5", "FRICT": "M1.6", "STATIC": "M1.7", "MOMENTS": "M1.8",
}
VALID_TOPICS = {f"M1.{i}" for i in range(1, 9)}
MIN_TEXT_CHARS = 40
REQUEST_DELAY_S = 0.4

# --- syllabus correction -------------------------------------------------------
# M1.7 is "Statics of a PARTICLE". Both Groq models (8B and 70B agree) routinely
# label rigid-body problems -- a rod/beam/plank/girder resting on supports, or on
# the point of tipping -- as M1.7, when the syllabus places them under M1.8
# Moments. A rod is not a particle, so this is decidable from the text and does
# not need the LLM. Verified by hand against the flagged questions.
RIGID_BODY_RE = re.compile(
    r"\b(uniform rod|non-uniform rod|rod AB|beam|plank|ladder|uniform bar|girder)\b",
    re.IGNORECASE,
)
LEVER_RE = re.compile(
    r"(moments? about|taking moments|two supports|point of tipping|about to tilt|"
    r"about to tip|tilt about|pivot|hinge|supports? at)",
    re.IGNORECASE,
)


def apply_syllabus_correction(topic: str | None, text: str) -> tuple[str | None, bool]:
    """Return (topic, corrected). Rigid-body equilibrium belongs to M1.8 Moments."""
    if topic and topic != "M1.8" and RIGID_BODY_RE.search(text) and LEVER_RE.search(text):
        return "M1.8", True
    return topic, False


def load_env() -> tuple[str, str]:
    load_dotenv(REPO_ROOT / ".env.local")
    url = os.getenv("SUPABASE_URL") or os.getenv("NEXT_PUBLIC_SUPABASE_URL")
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    if not (url and key):
        raise SystemExit("ERROR: SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY missing from .env.local")
    return url.rstrip("/"), key


def extract_text(pdf_path: Path) -> str:
    """Question text via PyMuPDF. These PDFs put content in layers that PyPDF2 drops."""
    try:
        with fitz.open(pdf_path) as doc:
            return "\n".join(page.get_text() for page in doc).strip()
    except Exception as exc:  # noqa: BLE001
        print(f"   [warn] unreadable {pdf_path.name}: {type(exc).__name__}")
        return ""


def normalise_topic(raw: str | None) -> str | None:
    if not raw:
        return None
    t = str(raw).strip().upper()
    if t in CODE_TO_ID:
        return CODE_TO_ID[t]
    t = t.replace("M1-", "M1.").replace(" ", "")
    if t in VALID_TOPICS:
        return t
    if t.isdigit() and 1 <= int(t) <= 8:   # bare index -> M1.n
        return f"M1.{int(t)}"
    return None


def fetch_pages(sb: str, key: str) -> list[dict]:
    """All `pages` rows for WME01, keyed later by qp_page_url filename."""
    h = {"apikey": key, "Authorization": f"Bearer {key}"}
    papers = requests.get(
        f"{sb}/rest/v1/papers", headers=h,
        params={"select": "id", "subject_id": f"eq.{SUBJECT_ID}", "limit": "500"},
        timeout=60,
    ).json()
    if not papers:
        return []
    ids = ",".join(p["id"] for p in papers)
    rows: list[dict] = []
    start = 0
    while True:
        resp = requests.get(
            f"{sb}/rest/v1/pages",
            headers={**h, "Range": f"{start}-{start + 999}"},
            params={"select": "id,question_number,topics,qp_page_url",
                    "paper_id": f"in.({ids})"},
            timeout=90,
        )
        chunk = resp.json()
        if not isinstance(chunk, list):
            raise SystemExit(f"pages query failed: {str(chunk)[:200]}")
        rows += chunk
        if len(chunk) < 1000:
            return rows
        start += 1000


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--commit", action="store_true", help="write results to Supabase")
    ap.add_argument("--limit", type=int, default=0, help="classify at most N questions")
    ap.add_argument("--cache", type=Path, default=DEFAULT_CACHE)
    ap.add_argument("--reclassify", action="store_true", help="ignore the cache")
    ap.add_argument("--prune-orphans", action="store_true",
                    help="delete pages rows whose PDF does not exist")
    args = ap.parse_args()

    sb, key = load_env()
    headers = {"apikey": key, "Authorization": f"Bearer {key}",
               "Content-Type": "application/json"}

    if not QP_DIR.exists():
        raise SystemExit(f"ERROR: missing {QP_DIR}")

    pdfs = sorted(QP_DIR.glob("*.pdf"))
    print(f"local per-question QP PDFs : {len(pdfs)}")
    rows = fetch_pages(sb, key)
    by_file: dict[str, dict] = {}
    for r in rows:
        fname = (r.get("qp_page_url") or "").split("/")[-1]
        if fname:
            by_file[fname] = r
    print(f"supabase pages rows        : {len(rows)}")

    orphans = [r for f, r in by_file.items() if not (QP_DIR / f).exists()]
    print(f"orphan rows (no PDF)       : {len(orphans)}")

    cache: dict[str, dict] = {}
    if args.cache.exists() and not args.reclassify:
        cache = json.loads(args.cache.read_text(encoding="utf-8"))
        print(f"cached classifications     : {len(cache)}")

    todo = [p for p in pdfs if p.name not in cache]
    if args.limit:
        todo = todo[: args.limit]

    if todo:
        from mistral_classifier import MistralTopicClassifier  # noqa: PLC0415
        groq = os.getenv("GROQ_API_KEY")
        if not groq:
            raise SystemExit("ERROR: GROQ_API_KEY missing from .env.local")
        clf = MistralTopicClassifier(topics_yaml_path=str(TOPICS_YAML), groq_api_key=groq)
        print(f"to classify                : {len(todo)}\n")

        for i, pdf in enumerate(todo, 1):
            text = extract_text(pdf)
            if len(text) < MIN_TEXT_CHARS:
                print(f"[{i:3}/{len(todo)}] SKIP {pdf.name} -- only {len(text)} chars")
                cache[pdf.name] = {"topic": None, "reason": "text too short"}
                continue
            try:
                res = clf.classify(text, pdf.stem)
            except Exception as exc:  # noqa: BLE001
                print(f"[{i:3}/{len(todo)}] FAIL {pdf.name} -- {type(exc).__name__}")
                continue
            topic = normalise_topic(getattr(res, "topic", None)) if res else None
            cache[pdf.name] = {
                "topic": topic,
                "difficulty": getattr(res, "difficulty", None) if res else None,
                "confidence": getattr(res, "confidence", None) if res else None,
                "raw": getattr(res, "topic", None) if res else None,
            }
            print(f"[{i:3}/{len(todo)}] {pdf.name:26} -> {topic or 'UNRESOLVED'} "
                  f"({cache[pdf.name]['difficulty']}, {cache[pdf.name]['confidence']})")
            if i % 20 == 0:
                args.cache.parent.mkdir(parents=True, exist_ok=True)
                args.cache.write_text(json.dumps(cache, indent=1), encoding="utf-8")
            time.sleep(REQUEST_DELAY_S)

        args.cache.parent.mkdir(parents=True, exist_ok=True)
        args.cache.write_text(json.dumps(cache, indent=1), encoding="utf-8")
        print(f"\ncache saved -> {args.cache}")

    resolved = {f: c for f, c in cache.items() if c.get("topic") in VALID_TOPICS}

    # Syllabus correction pass -- runs over cached results too, so it never costs
    # an extra LLM call and stays consistent across re-runs.
    corrected = 0
    for fname, c in resolved.items():
        pdf = QP_DIR / fname
        if not pdf.exists():
            continue
        topic, changed = apply_syllabus_correction(c["topic"], extract_text(pdf))
        if changed:
            c["topic"] = topic
            c["corrected_from"] = c.get("raw")
            corrected += 1
    if corrected:
        print(f"\nsyllabus corrections (-> M1.8 Moments): {corrected}")
        args.cache.write_text(json.dumps(cache, indent=1), encoding="utf-8")

    print(f"\nclassified OK              : {len(resolved)}/{len(pdfs)}")
    print("topic distribution:")
    for t, n in sorted(Counter(c["topic"] for c in resolved.values()).items()):
        print(f"   {t}: {n}")
    diffs = Counter(c.get("difficulty") for c in resolved.values())
    print("difficulty:", dict(diffs))

    # ---- publish ----
    updated = missing = 0
    for fname, c in resolved.items():
        row = by_file.get(fname)
        if not row:
            missing += 1
            continue
        payload = {"topics": [c["topic"]]}
        if c.get("difficulty") in ("easy", "medium", "hard"):
            payload["difficulty"] = c["difficulty"]
        if isinstance(c.get("confidence"), (int, float)):
            payload["confidence"] = float(c["confidence"])
        if args.commit:
            resp = requests.patch(
                f"{sb}/rest/v1/pages", headers=headers,
                params={"id": f"eq.{row['id']}"}, json=payload, timeout=60,
            )
            if resp.status_code not in (200, 204):
                print(f"   [err] {fname}: {resp.status_code} {resp.text[:120]}")
                continue
        updated += 1

    print(f"\nrows {'updated' if args.commit else 'to update'} : {updated}")
    if missing:
        print(f"classified but no DB row  : {missing}")

    if orphans:
        if args.prune_orphans and args.commit:
            for r in orphans:
                requests.delete(f"{sb}/rest/v1/pages", headers=headers,
                                params={"id": f"eq.{r['id']}"}, timeout=60)
            print(f"orphan rows deleted       : {len(orphans)}")
        else:
            print(f"orphan rows left in place : {len(orphans)}  (use --prune-orphans --commit)")

    if not args.commit:
        print("\nDRY-RUN -- nothing written. Re-run with --commit to apply.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
