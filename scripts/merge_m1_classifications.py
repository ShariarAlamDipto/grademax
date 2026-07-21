#!/usr/bin/env python3
"""Build the best-available M1 topic per question and publish to Supabase.

Precedence per question (highest first):
  1. VISION result (data/analysis/m1_vision_classification_cache.json) -- gold
     standard; validated 7/7 vs 1/7 for the keyword classifier on hard cases.
  2. KEYWORD result on DECODED text, for garbled-font questions. Those PDFs use a
     subset font whose text layer is a uniform +29 character shift ("/HDYH EODQN"
     -> "Leave blank"); the keyword classifier saw garbage and guessed. We recover
     the words deterministically and re-run the keyword classifier on them.
  3. KEYWORD result (data/analysis/m1_classification_cache.json) otherwise.
Then a deterministic backstop: a rigid body (rod/beam/plank/ladder/girder) in
equilibrium is ALWAYS M1.8 Moments (M1.7 is Statics of a *particle*).

This is a stopgap until the vision pass covers all 223 (blocked today by the
OpenRouter free-models-per-day cap). Re-running after vision fills in is safe.

Dry-run by default; --commit writes pages.topics for WME01.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from collections import Counter
from pathlib import Path

import fitz
import requests
from dotenv import load_dotenv

REPO = Path(__file__).resolve().parent.parent
QP_DIR = REPO / "data" / "processed" / "Mechanics_1_resegmented" / "pages"
VISION = REPO / "data" / "analysis" / "m1_vision_classification_cache.json"
KEYWORD = REPO / "data" / "analysis" / "m1_classification_cache.json"
TOPICS_YAML = REPO / "classification" / "mechanics_1_topics.yaml"
SUBJECT_ID = "4d54f2aa-ee9c-470a-814b-8f6095ec9278"
VALID = {f"M1.{i}" for i in range(1, 9)}

CODE_TO_ID = {"MODEL": "M1.1", "VECT": "M1.2", "KINEM": "M1.3", "DYNAM": "M1.4",
              "MOMENT": "M1.5", "FRICT": "M1.6", "STATIC": "M1.7", "MOMENTS": "M1.8"}
RIGID_BODY_RE = re.compile(
    r"\b(uniform rod|non-uniform rod|rod AB|beam|plank|ladder|uniform bar|girder|see-?saw)\b", re.I)
EQUIL_RE = re.compile(r"equilibrium|moments?|tilt|tipping|supports?|reaction|suspended|rests?", re.I)
ENGLISH = re.compile(r"\b(the|of|and|mass|particle|force|plane|string|find|figure)\b", re.I)


def norm(t):
    if not t:
        return None
    t = str(t).strip().upper().replace("M1-", "M1.").replace(" ", "")
    if t in CODE_TO_ID:
        return CODE_TO_ID[t]
    return t if t in VALID else (f"M1.{t}" if t.isdigit() and 1 <= int(t) <= 8 else None)


def read_text(pdf: Path) -> str:
    with fitz.open(pdf) as d:
        return "\n".join(p.get_text() for p in d)


def decode_shift(s: str) -> str:
    """Undo a uniform printable-ASCII shift; pick the shift maximising English words."""
    best, best_hits = s, len(ENGLISH.findall(s))
    for k in range(-40, 41):
        if k == 0:
            continue
        dec = "".join(chr((ord(c) - 32 + k) % 95 + 32) if 32 <= ord(c) < 127 else " " for c in s)
        hits = len(ENGLISH.findall(dec))
        if hits > best_hits:
            best, best_hits = dec, hits
    return best


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--commit", action="store_true")
    args = ap.parse_args()

    load_dotenv(REPO / ".env.local")
    sb = (os.getenv("SUPABASE_URL") or os.getenv("NEXT_PUBLIC_SUPABASE_URL") or "").rstrip("/")
    sk = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    vision = json.loads(VISION.read_text(encoding="utf-8")) if VISION.exists() else {}
    keyword = json.loads(KEYWORD.read_text(encoding="utf-8")) if KEYWORD.exists() else {}

    sys.path.insert(0, str(REPO / "scripts"))
    from mistral_classifier import MistralTopicClassifier  # noqa: PLC0415
    clf = MistralTopicClassifier(topics_yaml_path=str(TOPICS_YAML), groq_api_key=os.getenv("GROQ_API_KEY"))

    final: dict[str, dict] = {}
    src = Counter()
    for pdf in sorted(QP_DIR.glob("*.pdf")):
        name = pdf.name
        v = norm(vision.get(name, {}).get("topic"))
        if v:
            final[name] = {"topic": v, "source": "vision"}; src["vision"] += 1
            continue
        text = read_text(pdf)
        body = re.sub(r"\*[A-Z0-9]+\*|Leave blank|DO NOT WRITE IN THIS AREA", "", text)
        garbled = len(body) > 150 and len(ENGLISH.findall(body)) / max(len(body.split()), 1) < 0.03
        if garbled:
            decoded = decode_shift(body)
            res = clf.classify(decoded[:3000], name)
            t = norm(getattr(res, "topic", None)) if res else None
            if t:
                final[name] = {"topic": t, "source": "decoded+keyword"}; src["decoded"] += 1
                text = decoded  # use decoded text for the rigid-body backstop too
            else:
                final[name] = {"topic": norm(keyword.get(name, {}).get("topic")), "source": "keyword"}; src["keyword"] += 1
        else:
            final[name] = {"topic": norm(keyword.get(name, {}).get("topic")), "source": "keyword"}; src["keyword"] += 1

        # rigid-body backstop (skip vision rows -- those are trusted as-is)
        c = final[name]
        if c["topic"] and c["topic"] != "M1.8" and RIGID_BODY_RE.search(text) \
                and EQUIL_RE.search(text) and "modelled as a particle" not in text.lower():
            c["was"] = c["topic"]; c["topic"] = "M1.8"; c["source"] += "+rigidbody"; src["rigidbody_fix"] += 1

    resolved = {f: c for f, c in final.items() if c["topic"] in VALID}
    print(f"questions: {len(final)}   resolved: {len(resolved)}")
    print("source:", dict(src))
    print("distribution:", dict(sorted(Counter(c["topic"] for c in resolved.values()).items())))

    # publish
    h = {"apikey": sk, "Authorization": f"Bearer {sk}", "Content-Type": "application/json"}
    papers = requests.get(f"{sb}/rest/v1/papers", headers=h,
                          params={"select": "id", "subject_id": f"eq.{SUBJECT_ID}", "limit": "500"}, timeout=60).json()
    ids = ",".join(p["id"] for p in papers)
    rows, start = [], 0
    while True:
        d = requests.get(f"{sb}/rest/v1/pages", headers={**h, "Range": f"{start}-{start+999}"},
                         params={"select": "id,topics,qp_page_url", "paper_id": f"in.({ids})"}, timeout=90).json()
        rows += d
        if len(d) < 1000:
            break
        start += 1000
    by_file = {(r.get("qp_page_url") or "").split("/")[-1]: r for r in rows}

    updated = changed = 0
    for fname, c in resolved.items():
        row = by_file.get(fname)
        if not row:
            continue
        new = [c["topic"]]
        if (row.get("topics") or []) != new:
            changed += 1
        if args.commit:
            requests.patch(f"{sb}/rest/v1/pages", headers=h, params={"id": f"eq.{row['id']}"},
                           json={"topics": new}, timeout=60)
        updated += 1
    print(f"\nrows {'updated' if args.commit else 'to update'}: {updated}  (changed vs current: {changed})")
    if not args.commit:
        print("\nDRY-RUN -- nothing written. Re-run with --commit to apply.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
