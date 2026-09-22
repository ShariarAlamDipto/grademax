#!/usr/bin/env python3
"""Fill missing Edexcel past-paper QP/MS files from local archives.

For every `papers` row whose `pdf_url` or `markscheme_pdf_url` is NULL, this
locates the matching PDF in the local scraper archives, cleans third-party
watermarks + stamps "GradeMax" (reusing ingest_cambridge_papers.clean_and_stamp
so the output is byte-for-byte consistent with the rest of the catalogue),
uploads it to R2 at the exact key convention already used for that subject, and
patches the DB row.

Safety:
  * URL builder is derived from that subject's EXISTING rows and self-verified
    against them before any upload — a subject whose builder can't reproduce a
    known URL is skipped.
  * Dry-run by default. Pass --commit to upload + write the DB.
  * Idempotent: HEAD-skips R2 keys that already exist; only NULL columns are
    written.

Input plan: the validated match list produced by the audit
(scratchpad/gap_fill_validated.json), passed via --plan.

Usage:
    python -X utf8 scripts/fill_edexcel_paper_gaps.py --plan <plan.json>            # dry-run
    python -X utf8 scripts/fill_edexcel_paper_gaps.py --plan <plan.json> --commit
    python -X utf8 scripts/fill_edexcel_paper_gaps.py --plan <plan.json> --commit --subject "Physics"
"""

import argparse
import io
import json
import os
import re
import sys
from collections import defaultdict
from pathlib import Path

import requests
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).parent))
# ingest_cambridge_papers parses argv at import time; neutralise it so our own
# CLI args don't reach its parser. Only clean_and_stamp (a pure helper) is used.
_saved_argv = sys.argv
sys.argv = [sys.argv[0]]
from ingest_cambridge_papers import clean_and_stamp  # noqa: E402
sys.argv = _saved_argv

if sys.stdout.encoding != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env.local")

SUPABASE_URL = os.getenv("SUPABASE_URL") or os.getenv("NEXT_PUBLIC_SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
R2_PUBLIC_URL = (os.getenv("NEXT_PUBLIC_R2_PUBLIC_URL") or "").rstrip("/")
R2_ACCOUNT_ID = os.getenv("R2_ACCOUNT_ID")
R2_ACCESS_KEY = os.getenv("R2_ACCESS_KEY_ID")
R2_SECRET = os.getenv("R2_SECRET_ACCESS_KEY")
R2_BUCKET = os.getenv("R2_BUCKET_NAME", "grademax-papers")

H = {"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}"}


def title_season(season: str) -> str:
    return "-".join(w.capitalize() for w in str(season).split("-"))


def make_shape(url: str, year, season, paper_number) -> str:
    """Turn a concrete URL into a template with {Y}/{s}/{S}/{P} placeholders."""
    y = str(year)
    s_low = str(season).lower()
    s_tit = title_season(season)
    pn = str(paper_number)
    shape = url.replace(y, "{Y}")
    shape = shape.replace(s_low, "{s}")
    shape = shape.replace(s_tit, "{S}")
    shape = re.sub(re.escape("_" + pn + "_"), "_{P}_", shape)
    return shape


def fill_shape(shape: str, year, season, paper_number) -> str:
    return (shape.replace("{Y}", str(year))
                 .replace("{s}", str(season).lower())
                 .replace("{S}", title_season(season))
                 .replace("{P}", str(paper_number)))


def fetch_subject_rows(subject_id: str) -> list:
    rows = []
    offset = 0
    while True:
        r = requests.get(
            f"{SUPABASE_URL}/rest/v1/papers?select=id,year,season,paper_number,pdf_url,markscheme_pdf_url"
            f"&subject_id=eq.{subject_id}&limit=1000&offset={offset}", headers=H, timeout=60).json()
        rows.extend(r)
        if len(r) < 1000:
            return rows
        offset += 1000


def derive_shapes(rows: list) -> tuple[str | None, str | None, list[str]]:
    """Return (qp_shape, ms_shape, verification_errors)."""
    qp_shapes, ms_shapes = defaultdict(int), defaultdict(int)
    for row in rows:
        if row.get("pdf_url"):
            qp_shapes[make_shape(row["pdf_url"], row["year"], row["season"], row["paper_number"])] += 1
        if row.get("markscheme_pdf_url"):
            ms_shapes[make_shape(row["markscheme_pdf_url"], row["year"], row["season"], row["paper_number"])] += 1
    qp = max(qp_shapes, key=qp_shapes.get) if qp_shapes else None
    ms = max(ms_shapes, key=ms_shapes.get) if ms_shapes else None
    if ms is None and qp is not None:
        ms = qp[::-1].replace("PQ_", "SM_", 1)[::-1]  # swap last _QP -> _MS
    # verify: rebuild every existing url and confirm equality
    errs = []
    for row in rows:
        if row.get("pdf_url") and qp:
            built = fill_shape(qp, row["year"], row["season"], row["paper_number"])
            if built != row["pdf_url"]:
                errs.append(f"QP mismatch {row['year']} {row['season']} {row['paper_number']}: built={built} stored={row['pdf_url']}")
        if row.get("markscheme_pdf_url") and ms:
            built = fill_shape(ms, row["year"], row["season"], row["paper_number"])
            if built != row["markscheme_pdf_url"]:
                errs.append(f"MS mismatch {row['year']} {row['season']} {row['paper_number']}: built={built} stored={row['markscheme_pdf_url']}")
    return qp, ms, errs


def get_r2():
    import boto3
    from botocore.config import Config
    return boto3.client(
        "s3", endpoint_url=f"https://{R2_ACCOUNT_ID}.r2.cloudflarestorage.com",
        aws_access_key_id=R2_ACCESS_KEY, aws_secret_access_key=R2_SECRET,
        region_name="auto", config=Config(retries={"max_attempts": 3}))


def r2_key_from_url(url: str) -> str:
    return url[len(R2_PUBLIC_URL) + 1:]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--plan", required=True)
    ap.add_argument("--commit", action="store_true")
    ap.add_argument("--subject", default=None)
    ap.add_argument("--limit", type=int, default=0)
    args = ap.parse_args()

    plan = json.loads(Path(args.plan).read_text(encoding="utf-8"))
    items = plan["validated"] + plan.get("whitelisted", [])
    if args.subject:
        items = [i for i in items if i["subject"] == args.subject]
    if args.limit:
        items = items[: args.limit]

    # group by subject to derive shapes once
    by_subject = defaultdict(list)
    for it in items:
        by_subject[it["subject"]].append(it)

    # subject name -> id
    subs = {}
    offset = 0
    while True:
        r = requests.get(f"{SUPABASE_URL}/rest/v1/subjects?select=id,name&limit=1000&offset={offset}", headers=H, timeout=60).json()
        for s in r:
            subs[s["name"]] = s["id"]
        if len(r) < 1000:
            break
        offset += 1000

    r2 = get_r2() if args.commit else None
    done = skipped = failed = 0
    report = []

    for subject, its in by_subject.items():
        sid = subs.get(subject)
        if not sid:
            print(f"!! no subject id for {subject}; skipping {len(its)} items")
            failed += len(its)
            continue
        rows = fetch_subject_rows(sid)
        row_by_id = {r["id"]: r for r in rows}
        qp_shape, ms_shape, errs = derive_shapes(rows)
        if errs:
            print(f"!! {subject}: URL builder self-check FAILED ({len(errs)} errors) — skipping subject")
            for e in errs[:3]:
                print("     ", e)
            failed += len(its)
            continue

        print(f"\n=== {subject}  (QP shape ok, MS shape ok) ===")
        for it in its:
            kind = it["kind"]
            shape = qp_shape if kind == "QP" else ms_shape
            if not shape:
                print(f"  !! no {kind} shape for {subject}; skip")
                failed += 1
                continue
            url = fill_shape(shape, it["year"], it["season"], it["paper_number"])
            key = r2_key_from_url(url)
            col = "pdf_url" if kind == "QP" else "markscheme_pdf_url"

            # confirm DB column is still null (idempotency)
            cur = row_by_id.get(it["paper_id"])
            if cur and cur.get(col):
                print(f"  ~ already set: {it['year']} {it['season']} {it['paper_number']} {kind}")
                skipped += 1
                continue

            local = Path(it["local_file"])
            if not local.exists():
                print(f"  !! missing local file: {local}")
                failed += 1
                continue

            print(f"  {'[DRY] ' if not args.commit else ''}{kind} {it['year']} {it['season']} {it['paper_number']} -> {key}")
            report.append({"paper_id": it["paper_id"], "subject": subject, "kind": kind, "url": url, "key": key, "local": str(local)})

            if not args.commit:
                done += 1
                continue

            # clean + stamp
            raw = local.read_bytes()
            try:
                out, redactions, _ = clean_and_stamp(raw)
            except Exception as e:
                print(f"     !! clean_and_stamp failed: {e}")
                failed += 1
                continue

            # upload (skip if exists)
            from botocore.exceptions import ClientError
            try:
                r2.head_object(Bucket=R2_BUCKET, Key=key)
                print("     R2 object already exists — reusing")
            except ClientError:
                r2.put_object(Bucket=R2_BUCKET, Key=key, Body=out, ContentType="application/pdf")

            # patch DB (only if still null)
            resp = requests.patch(
                f"{SUPABASE_URL}/rest/v1/papers?id=eq.{it['paper_id']}&{col}=is.null",
                headers={**H, "Content-Type": "application/json", "Prefer": "return=representation"},
                json={col: url}, timeout=60)
            if resp.status_code not in (200, 204):
                print(f"     !! DB patch failed {resp.status_code}: {resp.text[:200]}")
                failed += 1
                continue
            done += 1

    print(f"\n{'COMMITTED' if args.commit else 'DRY-RUN'}: filled={done} skipped={skipped} failed={failed}")
    outp = Path(args.plan).parent / "fill_report.json"
    outp.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"report: {outp}")


if __name__ == "__main__":
    main()
