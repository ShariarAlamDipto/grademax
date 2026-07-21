#!/usr/bin/env python3
"""Re-classify Mechanics 1 (WME01) questions with a VISION model and publish topics.

Why vision
----------
Text classification (`scripts/classify_m1_and_publish.py`) fails on ~16% of M1
questions whose PDFs use a shifted subset font: the text layer extracts as garbage
("/HDYH EODQN" for "Leave blank"), so the LLM sees nonsense and defaults to a wrong
topic. It also systematically mislabels rigid-body Moments (M1.8) as Statics of a
Particle (M1.7) and static-friction questions as Dynamics. The glyphs RENDER
correctly, so a vision model reads the real question and classifies from the physics.

Each question's first content page is rendered to PNG and sent to the model with the
8 M1 topic definitions; the model returns one topic id (M1.1 .. M1.8). Results are
cached so re-runs are free. A deterministic rigid-body -> M1.8 backstop stays as
cheap insurance.

Dry-run by default; --commit writes `pages.topics` for WME01.

Usage:
    python -X utf8 scripts/classify_m1_vision.py                 # dry-run
    python -X utf8 scripts/classify_m1_vision.py --commit
"""

from __future__ import annotations

import argparse
import base64
import json
import os
import re
import sys
import time
from collections import Counter
from pathlib import Path

import fitz
import requests
from dotenv import load_dotenv

REPO_ROOT = Path(__file__).resolve().parent.parent
QP_DIR = REPO_ROOT / "data" / "processed" / "Mechanics_1_resegmented" / "pages"
CACHE = REPO_ROOT / "data" / "analysis" / "m1_vision_classification_cache.json"

SUBJECT_ID = "4d54f2aa-ee9c-470a-814b-8f6095ec9278"  # WME01 (IAL M1), NOT 4ME1
# Tried in order per question; first to return a valid id wins. Paid models first
# (best quality) then free fallbacks so the batch still completes without credit.
MODELS = [
    "google/gemini-2.5-flash",
    "nvidia/nemotron-nano-12b-v2-vl:free",
    "google/gemma-4-31b-it:free",
]
VALID = {f"M1.{i}" for i in range(1, 9)}
RENDER_DPI = 120
REQUEST_DELAY_S = 0.3
MAX_RETRIES = 4

TOPICS = """M1.1 Modelling & Assumptions - stating/justifying modelling assumptions as the MAIN task
M1.2 Vectors in Mechanics - position/velocity vectors in i,j form, bearings, closest approach, resultant vectors
M1.3 Kinematics - motion in a straight line, suvat, vertical motion under gravity, velocity-time graphs
M1.4 Dynamics - Newton's second law F=ma, connected particles over a pulley, lifts, tow bars
M1.5 Momentum & Impulse - collisions, coalescing particles, impulse, conservation of momentum, jerk in a string
M1.6 Friction - coefficient of friction is the focus; limiting equilibrium, on the point of sliding, rough-plane statics
M1.7 Statics of a Particle - a PARTICLE in equilibrium under forces (strings, pegs, inclined plane)
M1.8 Moments - a RIGID BODY (rod, beam, plank, ladder, girder) in equilibrium; reactions at supports; tilting/tipping"""

PROMPT = (
    "You are classifying an Edexcel International A-Level Mechanics 1 exam question "
    "into exactly ONE topic. Topics:\n\n" + TOPICS +
    "\n\nReply with ONLY the topic id (e.g. M1.4) for the single PRIMARY topic the "
    "question mainly tests. A rod/beam/plank/ladder in equilibrium is ALWAYS M1.8, "
    "never M1.7 (M1.7 is only for a particle)."
)

RIGID_BODY_RE = re.compile(
    r"\b(uniform rod|non-uniform rod|rod AB|beam|plank|ladder|uniform bar|girder|see-?saw)\b", re.I)
EQUIL_RE = re.compile(
    r"equilibrium|moments?|tilt|tipping|supports?|reaction|suspended|resting on|rests? (horizontally|in)", re.I)


def render_first_page(pdf: Path) -> str:
    d = fitz.open(pdf)
    try:
        idx = next((i for i, pg in enumerate(d) if pg.get_text().strip()), 0)
        png = d[idx].get_pixmap(dpi=RENDER_DPI).tobytes("png")
    finally:
        d.close()
    return base64.b64encode(png).decode()


def rigid_body_text(pdf: Path) -> str:
    d = fitz.open(pdf)
    try:
        return " ".join(pg.get_text() for pg in d)
    finally:
        d.close()


def classify_vision(key: str, pdf: Path) -> tuple[str | None, str | None]:
    """Return (topic, model). Tries each model with backoff on 402/429/5xx."""
    img = render_first_page(pdf)
    for model in MODELS:
        body = {
            "model": model,
            "messages": [{"role": "user", "content": [
                {"type": "text", "text": PROMPT},
                {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{img}"}},
            ]}],
            "max_tokens": 15, "temperature": 0,
        }
        for attempt in range(MAX_RETRIES):
            try:
                r = requests.post("https://openrouter.ai/api/v1/chat/completions",
                                  headers={"Authorization": f"Bearer {key}"}, json=body, timeout=90)
            except Exception:  # noqa: BLE001
                time.sleep(2 * (attempt + 1)); continue
            if r.status_code == 402:
                break  # no credit for this (paid) model -> next model
            if r.status_code == 429 or r.status_code >= 500:
                time.sleep(3 * (attempt + 1)); continue
            if r.status_code != 200:
                break
            try:
                choices = r.json().get("choices")
                if not choices:  # 200 OK but error/empty body (some free providers)
                    time.sleep(3 * (attempt + 1)); continue
                raw = choices[0]["message"]["content"]
            except (ValueError, KeyError, IndexError, TypeError):
                time.sleep(2 * (attempt + 1)); continue
            m = re.search(r"M1\.?\s*([1-8])", raw, re.I)
            if m:
                return f"M1.{m.group(1)}", model
            break  # answered but unparseable -> next model
    return None, None


def load_pages(sb: str, key: str) -> dict[str, dict]:
    h = {"apikey": key, "Authorization": f"Bearer {key}"}
    papers = requests.get(f"{sb}/rest/v1/papers", headers=h,
                          params={"select": "id", "subject_id": f"eq.{SUBJECT_ID}", "limit": "500"},
                          timeout=60).json()
    ids = ",".join(p["id"] for p in papers)
    rows, start = [], 0
    while ids:
        chunk = requests.get(f"{sb}/rest/v1/pages", headers={**h, "Range": f"{start}-{start+999}"},
                             params={"select": "id,topics,qp_page_url", "paper_id": f"in.({ids})"},
                             timeout=90).json()
        if not isinstance(chunk, list):
            raise SystemExit(f"pages query failed: {str(chunk)[:200]}")
        rows += chunk
        if len(chunk) < 1000:
            break
        start += 1000
    return {(r.get("qp_page_url") or "").split("/")[-1]: r for r in rows}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--commit", action="store_true")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--reclassify", action="store_true")
    args = ap.parse_args()

    load_dotenv(REPO_ROOT / ".env.local")
    ork = os.getenv("OPENROUTER_API_KEY")
    sb = (os.getenv("SUPABASE_URL") or os.getenv("NEXT_PUBLIC_SUPABASE_URL") or "").rstrip("/")
    sk = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    if not (ork and sb and sk):
        raise SystemExit("ERROR: OPENROUTER_API_KEY / SUPABASE_* missing from .env.local")

    pdfs = sorted(QP_DIR.glob("*.pdf"))
    cache = json.loads(CACHE.read_text(encoding="utf-8")) if (CACHE.exists() and not args.reclassify) else {}
    todo = [p for p in pdfs if p.name not in cache]
    if args.limit:
        todo = todo[: args.limit]
    print(f"local questions : {len(pdfs)}   cached : {len(cache)}   to classify : {len(todo)}\n")

    for i, pdf in enumerate(todo, 1):
        topic, model = classify_vision(ork, pdf)
        if topic is None:
            print(f"[{i:3}/{len(todo)}] FAIL {pdf.name} -- no model returned a topic")
            continue
        cache[pdf.name] = {"topic": topic, "model": model}
        print(f"[{i:3}/{len(todo)}] {pdf.name:26} -> {topic}  ({model.split('/')[-1]})")
        if i % 10 == 0:
            CACHE.write_text(json.dumps(cache, indent=1), encoding="utf-8")
        time.sleep(REQUEST_DELAY_S)
    CACHE.write_text(json.dumps(cache, indent=1), encoding="utf-8")

    # deterministic backstop: rigid body in equilibrium is always M1.8
    corrected = 0
    for pdf in pdfs:
        c = cache.get(pdf.name)
        if not c or c.get("topic") not in VALID:
            continue
        if c["topic"] != "M1.8":
            txt = rigid_body_text(pdf)
            if RIGID_BODY_RE.search(txt) and EQUIL_RE.search(txt) and "modelled as a particle" not in txt.lower():
                c["vision_topic"] = c["topic"]
                c["topic"] = "M1.8"
                corrected += 1
    if corrected:
        CACHE.write_text(json.dumps(cache, indent=1), encoding="utf-8")
        print(f"\nrigid-body backstop corrections -> M1.8: {corrected}")

    resolved = {f: c for f, c in cache.items() if c.get("topic") in VALID}
    print(f"\nclassified OK : {len(resolved)}/{len(pdfs)}")
    print("distribution :", dict(sorted(Counter(c["topic"] for c in resolved.values()).items())))

    by_file = load_pages(sb, sk)
    h = {"apikey": sk, "Authorization": f"Bearer {sk}", "Content-Type": "application/json"}
    updated = changed = 0
    for fname, c in resolved.items():
        row = by_file.get(fname)
        if not row:
            continue
        new = [c["topic"]]
        if (row.get("topics") or []) != new:
            changed += 1
        if args.commit:
            r = requests.patch(f"{sb}/rest/v1/pages", headers=h,
                               params={"id": f"eq.{row['id']}"}, json={"topics": new}, timeout=60)
            if r.status_code not in (200, 204):
                print(f"   [err] {fname}: {r.status_code} {r.text[:100]}"); continue
        updated += 1
    print(f"\nrows {'updated' if args.commit else 'to update'} : {updated}   (topic changed vs current: {changed})")
    if not args.commit:
        print("\nDRY-RUN -- nothing written. Re-run with --commit to apply.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
