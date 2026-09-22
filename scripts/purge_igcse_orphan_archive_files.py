#!/usr/bin/env python3
"""Delete local archive files that no `papers` row points at.

Earlier repair passes removed phantom rows (sessions Pearson never ran, R-variant
mark schemes with no matching paper, whole-session duplicates) from Supabase and
R2. They did not touch `data/Ultimate Final IGCSE`, so the archive still holds the
files. That matters for two reasons: the label audit keeps reporting defects that
production no longer has, and any future re-ingest from the archive would put them
straight back.

A file is removed only when it is BOTH unreferenced by any `papers` row AND
reported MISMATCH by the label audit. That intersection matters: plenty of archive
files are unreferenced simply because they have never been ingested (eight
Mechanics 1 papers, for instance), and those are future content, not rubbish.
Deleting on "unreferenced" alone would throw them away. Unreferenced-but-clean
files are therefore listed and kept.

Everything removed is copied to data/quarantine/ first, with a manifest.

Dry-run by default; --commit to delete.

Usage:
    python -X utf8 scripts/purge_igcse_orphan_archive_files.py
    python -X utf8 scripts/purge_igcse_orphan_archive_files.py --commit
"""

from __future__ import annotations

import argparse
import io
import json
import os
import re
import shutil
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

import requests
from dotenv import load_dotenv

if sys.stdout.encoding != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

REPO_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(REPO_ROOT / ".env.local")

SUPABASE_URL = os.getenv("SUPABASE_URL") or os.getenv("NEXT_PUBLIC_SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
H = {"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}"}
ARCHIVE = REPO_ROOT / "data" / "Ultimate Final IGCSE"
AUDIT_JSON = REPO_ROOT / "data" / "analysis" / "igcse_edexcel_label_audit.json"
QUARANTINE = REPO_ROOT / "data" / "quarantine" / "igcse_orphan_archive_files"

# DB subject name -> archive folder
FOLDER = {
    "Accounting": "Accounting", "Bangla": "Bangla", "Biology": "Biology",
    "Business Studies": "Business_Studies", "Chemistry": "Chemistry",
    "Commerce": "Commerce", "Computer Science": "Computer_Science",
    "Economics": "Economics", "English Language A": "English_A",
    "English Language B": "English_B", "Further Pure Mathematics": "Further_Pure_Maths",
    "Geography": "Geography", "Human Biology": "Human_Biology", "ICT": "ICT",
    "Mathematics A": "Mathematics_A", "Mathematics B": "Mathematics_B",
    "Mechanics 1": "Mechanics_1", "Physics": "Physics",
}


def fetch_all(path: str) -> list[dict]:
    out: list[dict] = []
    off = 0
    while True:
        r = requests.get(f"{SUPABASE_URL}/rest/v1/{path}&limit=1000&offset={off}",
                         headers=H, timeout=60)
        r.raise_for_status()
        batch = r.json()
        out += batch
        if len(batch) < 1000:
            return out
        off += 1000


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--commit", action="store_true")
    ap.add_argument("--subject", help="archive folder name, e.g. ICT")
    args = ap.parse_args()

    subjects = [s for s in fetch_all("subjects?select=id,name,level")
                if (s.get("level") or "").lower() == "igcse"
                and not s["name"].startswith("Cambridge")]

    referenced: set[str] = set()
    folders_covered: set[str] = set()
    for s in subjects:
        folder = FOLDER.get(s["name"])
        if not folder:
            continue
        folders_covered.add(folder)
        for r in fetch_all(f"papers?select=pdf_url,markscheme_pdf_url"
                           f"&subject_id=eq.{s['id']}"):
            for col in ("pdf_url", "markscheme_pdf_url"):
                m = re.search(r"\.r2\.dev/(.+)$", r.get(col) or "")
                if m:
                    referenced.add(m.group(1).split("/")[-1])

    if not referenced:
        print("refusing to run: no paper URLs came back from Supabase", file=sys.stderr)
        return 1

    audit = json.loads(AUDIT_JSON.read_text("utf-8"))
    mismatched = {Path(r["file"]).name for r in audit if r["status"] == "MISMATCH"}

    orphans = defaultdict(list)
    keep = defaultdict(list)
    for folder in sorted(folders_covered):
        if args.subject and folder.lower() != args.subject.lower():
            continue
        for p in sorted((ARCHIVE / folder).rglob("*.pdf")):
            if p.name in referenced:
                continue
            (orphans if p.name in mismatched else keep)[folder].append(p)

    total = sum(len(v) for v in orphans.values())
    kept = sum(len(v) for v in keep.values())
    if kept:
        print(f"unreferenced but correctly labelled -- KEPT ({kept}); these have "
              f"simply never been ingested:")
        for folder, paths in sorted(keep.items()):
            print(f"   {folder}: {', '.join(p.name for p in paths)}")
    if not total:
        print("\nno mislabelled orphans to purge")
        return 0

    manifest = []
    for folder, paths in orphans.items():
        print(f"\n{folder}: {len(paths)} mislabelled orphan(s)")
        for p in paths:
            rel = p.relative_to(REPO_ROOT)
            print(f"   {rel}")
            manifest.append({"file": str(rel), "subject": folder,
                             "bytes": p.stat().st_size})

    if args.commit:
        QUARANTINE.mkdir(parents=True, exist_ok=True)
        for folder, paths in orphans.items():
            dest = QUARANTINE / folder
            dest.mkdir(parents=True, exist_ok=True)
            for p in paths:
                shutil.move(str(p), str(dest / p.name))
        (QUARANTINE / "manifest.json").write_text(
            json.dumps({"removed_at": datetime.now(timezone.utc).isoformat(),
                        "files": manifest}, indent=1), encoding="utf-8")
        print(f"\nCOMMITTED: moved {total} file(s) -> "
              f"{QUARANTINE.relative_to(REPO_ROOT)}")
    else:
        print(f"\nDRY-RUN: {total} orphan(s) would be quarantined")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
