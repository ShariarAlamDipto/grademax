#!/usr/bin/env python3
"""Remove Edexcel IGCSE `papers` rows for sessions that never happened, where the
content already lives under the session it really belongs to.

Two shapes, both discovered from the documents themselves rather than hardcoded:

1. **Mark-scheme-only phantom.** The row has no question paper, and its mark
   scheme's cover announces a *different* session. Example: Accounting `2024/jan`
   holds only a mark scheme that says "November 2023". Edexcel ran no January 2024
   Accounting series; the real `2023/oct-nov` row already carries that same mark
   scheme.

2. **Whole-row duplicate.** Every file on the row is the same Edexcel document
   (same barcode) as a row in another session. Example: Economics `2024/jan`
   carries P75954A / P75955A, which are the `2024/oct-nov` papers.

A row is deleted **only** when a surviving row elsewhere demonstrably holds the
same document -- matched on Pearson barcode where the cover prints one, otherwise
on (paper code, session, page count). Anything unmatched is reported and kept.

Backs up every deleted object to
`data/quarantine/igcse_phantom_rows/` together with a JSON manifest of the rows.

Dry-run by default; --commit to delete.

Usage:
    python -X utf8 scripts/fix_igcse_edexcel_phantom_rows.py
    python -X utf8 scripts/fix_igcse_edexcel_phantom_rows.py --commit
"""

from __future__ import annotations

import argparse
import io
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

import fitz  # PyMuPDF
import requests
from dotenv import load_dotenv

if sys.stdout.encoding != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

REPO_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(REPO_ROOT / ".env.local")

SUPABASE_URL = os.getenv("SUPABASE_URL") or os.getenv("NEXT_PUBLIC_SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
H = {"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}"}
R2_BUCKET = os.getenv("R2_BUCKET_NAME", "grademax-papers")
BACKUP = REPO_ROOT / "data" / "quarantine" / "igcse_phantom_rows"

MS_RE = re.compile(r"mark scheme|marking scheme", re.I)
SESSION_RE = re.compile(r"\b(January|February|March|May|June|Summer|October|November|Winter)\s+(20\d{2})\b", re.I)
PAPER_RE = re.compile(r"\bPAPER\s*:?\s*([0-9]{1,2}[A-Z]{0,3})(?![A-Za-z0-9])", re.I)
REF_RE = re.compile(r"\b4[A-Z]{2}[01]\s*/\s*([0-9]{1,2}[A-Z]{0,3})(?![A-Za-z0-9])")
BARCODE_RE = re.compile(r"\*([A-Z]\d{5,6}[A-Z]?)\d{4}\*")

MONTH_SEASON = {
    "january": "jan", "february": "jan", "march": "jan", "winter": "jan",
    "may": "may-jun", "june": "may-jun", "summer": "may-jun",
    "october": "oct-nov", "november": "oct-nov",
}


def r2_client():
    import boto3
    from botocore.config import Config
    return boto3.client(
        "s3", endpoint_url=f"https://{os.getenv('R2_ACCOUNT_ID')}.r2.cloudflarestorage.com",
        aws_access_key_id=os.getenv("R2_ACCESS_KEY_ID"),
        aws_secret_access_key=os.getenv("R2_SECRET_ACCESS_KEY"),
        region_name="auto", config=Config(retries={"max_attempts": 3}))


def key_of(url):
    m = re.search(r"\.r2\.dev/(.+)$", url or "")
    return m.group(1) if m else None


class Reader:
    """Reads and identifies R2 documents, memoised (rows share files)."""

    def __init__(self, client):
        self.client = client
        self.cache: dict[str, dict] = {}

    def get(self, key: str) -> dict:
        if key in self.cache:
            return self.cache[key]
        try:
            body = self.client.get_object(Bucket=R2_BUCKET, Key=key)["Body"].read()
            with fitz.open(stream=body, filetype="pdf") as d:
                page1 = " ".join(d[0].get_text().split())
                head = " ".join(" ".join(d[i].get_text()
                                         for i in range(min(3, d.page_count))).split())
                pages = d.page_count
        except Exception as exc:  # noqa: BLE001
            info = {"error": f"{type(exc).__name__}"}
            self.cache[key] = info
            return info
        m = SESSION_RE.search(page1)
        pm = REF_RE.search(head) or PAPER_RE.search(head)
        bc = BARCODE_RE.search(page1)
        info = {
            "kind": "MS" if MS_RE.search(page1) else "QP",
            "paper": pm.group(1).upper() if pm else None,
            "year": m.group(2) if m else None,
            "season": MONTH_SEASON.get(m.group(1).lower()) if m else None,
            "session_text": m.group(0) if m else None,
            "pages": pages, "barcode": bc.group(1) if bc else None,
        }
        self.cache[key] = info
        return info

    def identity(self, key):
        """A comparable fingerprint of the underlying Edexcel document."""
        i = self.get(key)
        if i.get("error"):
            return None
        if i["barcode"]:
            return ("bc", i["barcode"])
        return ("sig", i["kind"], i["paper"], i["year"], i["season"], i["pages"])


def fetch_all(path):
    out, off = [], 0
    while True:
        r = requests.get(f"{SUPABASE_URL}/rest/v1/{path}&limit=1000&offset={off}",
                         headers=H, timeout=60)
        r.raise_for_status()
        b = r.json()
        out += b
        if len(b) < 1000:
            return out
        off += 1000


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--commit", action="store_true")
    ap.add_argument("--subject", help="limit to one DB subject name")
    args = ap.parse_args()

    subjects = [s for s in fetch_all("subjects?select=id,name,level")
                if (s.get("level") or "").lower() == "igcse"
                and not s["name"].startswith("Cambridge")]
    if args.subject:
        subjects = [s for s in subjects if s["name"].lower() == args.subject.lower()]
    client = r2_client()
    reader = Reader(client)

    manifest = {"generated": datetime.now(timezone.utc).isoformat(),
                "committed": args.commit, "deleted": []}
    total_rows = total_objs = 0
    kept = []

    for s in sorted(subjects, key=lambda s: s["name"]):
        rows = fetch_all(f"papers?select=id,year,season,paper_number,pdf_url,"
                         f"markscheme_pdf_url&subject_id=eq.{s['id']}&order=year")
        if not rows:
            continue
        # index every document held by every row of this subject
        holders: dict[tuple, list] = {}
        for r in rows:
            for col in ("pdf_url", "markscheme_pdf_url"):
                k = key_of(r.get(col))
                if not k:
                    continue
                ident = reader.identity(k)
                if ident:
                    holders.setdefault(ident, []).append((r, col))

        victims = []
        for r in rows:
            qp_k, ms_k = key_of(r.get("pdf_url")), key_of(r.get("markscheme_pdf_url"))
            row_season, row_year = r["season"], str(r["year"])

            # shape 1 -- mark-scheme-only row whose MS belongs to another session
            if ms_k and not qp_k:
                info = reader.get(ms_k)
                if info.get("error") or not info.get("year"):
                    continue
                if info["year"] == row_year and info["season"] == row_season:
                    continue
                ident = reader.identity(ms_k)
                elsewhere = [(o, c) for o, c in holders.get(ident, [])
                             if o["id"] != r["id"]
                             and str(o["year"]) == info["year"]
                             and o["season"] == info["season"]]
                if elsewhere:
                    victims.append((r, f"MS-only; says {info['session_text']}; "
                                       f"same doc already at {info['year']}/{info['season']}"))
                else:
                    kept.append((s["name"], f"{row_year}/{row_season} p{r['paper_number']}",
                                 f"MS says {info['session_text']} but no row there holds it"))
                continue

            # shape 2 -- every file on the row duplicates a row in another session
            if not qp_k and not ms_k:
                continue
            dup_of = set()
            all_dup = True
            for k in (qp_k, ms_k):
                if not k:
                    continue
                ident = reader.identity(k)
                other = [(o, c) for o, c in holders.get(ident, [])
                         if o["id"] != r["id"]
                         and (str(o["year"]), o["season"]) != (row_year, row_season)]
                if not other:
                    all_dup = False
                    break
                dup_of.update((str(o["year"]), o["season"]) for o, _c in other)
            if all_dup and dup_of:
                # only act when the row's own session contradicts the documents
                doc_sessions = set()
                for k in (qp_k, ms_k):
                    if k:
                        i = reader.get(k)
                        if i.get("year"):
                            doc_sessions.add((i["year"], i["season"]))
                if doc_sessions and (row_year, row_season) not in doc_sessions:
                    tgt = sorted(dup_of)
                    victims.append((r, f"whole row duplicates {tgt}; "
                                       f"documents say {sorted(doc_sessions)}"))
                elif not doc_sessions and row_season != "specimen" and \
                        any(se == "specimen" for _y, se in dup_of):
                    # Specimen ("Sample Assessment Materials") papers print no
                    # session at all, so the contradiction above cannot fire. A
                    # real exam session holding a byte-equal copy of a specimen
                    # paper is nonetheless a session that never ran.
                    victims.append((r, f"duplicates the specimen session "
                                       f"{sorted(dup_of)}; specimen papers, no exam session"))

        if not victims:
            continue
        print(f"\n{s['name']}")
        for r, why in victims:
            keys = [k for k in (key_of(r.get("pdf_url")),
                                key_of(r.get("markscheme_pdf_url"))) if k]
            print(f"   {r['year']}/{r['season']}/paper {str(r['paper_number']):4} -- {why}")
            total_rows += 1
            total_objs += len(keys)
            manifest["deleted"].append({
                "subject": s["name"], "id": r["id"], "year": r["year"],
                "season": r["season"], "paper_number": r["paper_number"],
                "reason": why, "keys": keys,
                "pdf_url": r.get("pdf_url"), "markscheme_pdf_url": r.get("markscheme_pdf_url"),
            })
            if args.commit:
                dest = BACKUP / s["name"].replace(" ", "_")
                dest.mkdir(parents=True, exist_ok=True)
                for k in keys:
                    try:
                        (dest / k.split("/")[-1]).write_bytes(
                            client.get_object(Bucket=R2_BUCKET, Key=k)["Body"].read())
                    except Exception as exc:  # noqa: BLE001
                        print(f"      backup failed {k}: {exc}")
                for k in keys:
                    client.delete_object(Bucket=R2_BUCKET, Key=k)
                resp = requests.delete(f"{SUPABASE_URL}/rest/v1/papers?id=eq.{r['id']}",
                                       headers=H, timeout=60)
                if resp.status_code not in (200, 204):
                    print(f"      DB delete failed: {resp.status_code} {resp.text[:120]}")

    BACKUP.mkdir(parents=True, exist_ok=True)
    (BACKUP / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print("\n" + "=" * 72)
    print(f"{'COMMITTED' if args.commit else 'DRY-RUN'}: "
          f"{total_rows} row(s), {total_objs} R2 object(s)")
    if kept:
        print(f"\nreported but KEPT (no equivalent elsewhere -- needs sourcing):")
        for name, where, why in kept:
            print(f"   {name:22} {where:24} {why}")
    print(f"\nmanifest -> {(BACKUP / 'manifest.json').relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
