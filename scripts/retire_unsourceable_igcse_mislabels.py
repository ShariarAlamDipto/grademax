#!/usr/bin/env python3
"""Stop serving mislabelled Edexcel IGCSE documents that cannot be replaced.

A handful of slots hold the wrong document and the right one is not obtainable
from anywhere we can reach:

  * five 2025 mark schemes that Pearson publishes only under
    `/content/dam/secure/silver/...`, which answers HTTP 200 with a login page
    unless you have a centre account, and which PMT has not mirrored;
  * Business Studies November 2022, a session Pearson never ran at all -- the
    file sitting there is the Summer 2022 paper.

Leaving them alone means a student who opens "Paper 1 mark scheme" gets paper 2's
mark scheme, which is worse than getting nothing. So the document is withdrawn:
the R2 object is deleted and the column set NULL, which is a state the site
already handles (plenty of rows have no mark scheme yet). When that would leave a
row with neither a paper nor a mark scheme, the row itself goes -- that is the
phantom-session case, where the row should never have existed.

Everything removed is copied to data/quarantine/ first, with a manifest recording
the row id, column and R2 key so any of it can be put back.

Dry-run by default; --commit to write.

Usage:
    python -X utf8 scripts/retire_unsourceable_igcse_mislabels.py
    python -X utf8 scripts/retire_unsourceable_igcse_mislabels.py --commit
"""

from __future__ import annotations

import argparse
import io
import json
import os
import re
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

import requests
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).parent))
from audit_igcse_edexcel_labels import FILENAME_RE  # noqa: E402

if sys.stdout.encoding != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

REPO_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(REPO_ROOT / ".env.local")

SUPABASE_URL = os.getenv("SUPABASE_URL") or os.getenv("NEXT_PUBLIC_SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
H = {"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}",
     "Content-Type": "application/json"}
R2_BUCKET = os.getenv("R2_BUCKET_NAME", "grademax-papers")
AUDIT_JSON = REPO_ROOT / "data" / "analysis" / "igcse_edexcel_label_audit.json"
QUARANTINE = REPO_ROOT / "data" / "quarantine" / "igcse_unsourceable_mislabels"

COLUMN = {"QP": "pdf_url", "MS": "markscheme_pdf_url"}


def r2_client():
    import boto3
    from botocore.config import Config
    return boto3.client(
        "s3", endpoint_url=f"https://{os.getenv('R2_ACCOUNT_ID')}.r2.cloudflarestorage.com",
        aws_access_key_id=os.getenv("R2_ACCESS_KEY_ID"),
        aws_secret_access_key=os.getenv("R2_SECRET_ACCESS_KEY"),
        region_name="auto", config=Config(retries={"max_attempts": 3}))


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
    args = ap.parse_args()

    audit = json.loads(AUDIT_JSON.read_text("utf-8"))
    bad = {Path(r["file"]).name: r for r in audit if r["status"] == "MISMATCH"}
    if not bad:
        print("no mismatches left to retire")
        return 0

    rows = []
    for s in fetch_all("subjects?select=id,name,level"):
        if (s.get("level") or "").lower() != "igcse" or s["name"].startswith("Cambridge"):
            continue
        for r in fetch_all(f"papers?select=id,year,season,paper_number,pdf_url,"
                           f"markscheme_pdf_url&subject_id=eq.{s['id']}"):
            r["subject"] = s["name"]
            rows.append(r)

    actions = []
    for row in rows:
        for kind, col in COLUMN.items():
            name = (row.get(col) or "").split("/")[-1]
            if name not in bad:
                continue
            other = COLUMN["QP" if kind == "MS" else "MS"]
            drop_row = not row.get(other)
            actions.append({
                "subject": row["subject"], "row_id": row["id"],
                "year": row["year"], "season": row["season"],
                "paper_number": row.get("paper_number"),
                "column": col, "kind": kind, "filename": name,
                "key": re.sub(r"^.*\.r2\.dev/", "", row[col]),
                "drop_row": drop_row,
                "issues": bad[name]["issues"], "evidence": bad[name]["evidence"],
            })

    if not actions:
        print("none of the remaining mismatches is served by a papers row")
        return 0

    print(f"{len(actions)} document(s) to withdraw:\n")
    for a in actions:
        what = "DELETE ROW" if a["drop_row"] else f"NULL {a['column']}"
        print(f"  {a['subject']:<18} {a['year']}/{a['season']:<8} paper "
              f"{str(a['paper_number']):<4} {a['kind']}  ->  {what}")
        print(f"      holds: {'; '.join(a['issues'])}  [{a['evidence']}]")
        print(f"      key  : {a['key']}")

    if not args.commit:
        print(f"\nDRY-RUN: nothing written")
        return 0

    QUARANTINE.mkdir(parents=True, exist_ok=True)
    client = r2_client()
    done = 0
    for a in actions:
        local = None
        for p in (REPO_ROOT / "data" / "Ultimate Final IGCSE").rglob(a["filename"]):
            local = p
            break
        if local and local.exists():
            shutil.copy2(str(local), str(QUARANTINE / a["filename"]))

        try:
            client.delete_object(Bucket=R2_BUCKET, Key=a["key"])
        except Exception as exc:  # noqa: BLE001
            print(f"  !! R2 delete failed for {a['key']}: {exc}")
            continue

        if a["drop_row"]:
            resp = requests.delete(
                f"{SUPABASE_URL}/rest/v1/papers?id=eq.{a['row_id']}", headers=H, timeout=60)
        else:
            resp = requests.patch(
                f"{SUPABASE_URL}/rest/v1/papers?id=eq.{a['row_id']}", headers=H,
                json={a["column"]: None}, timeout=60)
        if resp.status_code >= 300:
            print(f"  !! Supabase write failed ({resp.status_code}): {resp.text[:120]}")
            continue

        if local and local.exists():
            local.unlink()
        done += 1
        print(f"  withdrawn: {a['filename']}")

    (QUARANTINE / "manifest.json").write_text(
        json.dumps({"retired_at": datetime.now(timezone.utc).isoformat(),
                    "actions": actions}, indent=1), encoding="utf-8")
    print(f"\nCOMMITTED: {done}/{len(actions)} withdrawn; "
          f"copies + manifest in {QUARANTINE.relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
