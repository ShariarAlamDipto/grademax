"""
Entry-point body for the per-subject live mark-scheme linkage audits.

Loads one subject's live `pages` rows, downloads every question and mark scheme
segment once (direct R2 reads, cached), judges each link by content with
`lib.live_ms_linkage`, and writes

    data/analysis/live_ms_linkage/<CODE>.json   every row with its evidence
    data/analysis/live_ms_linkage/<CODE>.csv    one line per row, for reading

Read-only against R2 and the database.
"""

from __future__ import annotations

import csv
import json
import os
import sys
from dataclasses import asdict
from pathlib import Path

from dotenv import load_dotenv
from supabase import create_client

ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = ROOT / "data" / "analysis" / "live_ms_linkage"
CACHE_DIR = OUT_DIR / "cache"


def _fetch(query) -> list[dict]:
    rows: list[dict] = []
    offset = 0
    while True:
        chunk = query(offset).execute().data or []
        rows.extend(chunk)
        if len(chunk) < 1000:
            return rows
        offset += 1000


def run(subject_code: str) -> int:
    load_dotenv(ROOT / ".env.local")
    sys.path.insert(0, str(ROOT / "scripts"))
    import ingest_2026_papers as ing  # noqa: PLC0415 -- needs env loaded first

    from lib.live_ms_linkage import audit_rows, fetch_all, summarise  # noqa: PLC0415

    sb = create_client(os.environ["NEXT_PUBLIC_SUPABASE_URL"],
                       os.environ["SUPABASE_SERVICE_ROLE_KEY"])
    subject = sb.table("subjects").select("id").eq("code", subject_code).execute().data
    if not subject:
        raise SystemExit(f"no subject {subject_code}")
    sid = subject[0]["id"]
    papers = _fetch(lambda o: sb.table("papers")
                    .select("id,year,season,paper_number").eq("subject_id", sid)
                    .range(o, o + 999))
    label = {p["id"]: f"{p['year']} {p['season']} P{p['paper_number']}" for p in papers}
    rows: list[dict] = []
    ids = list(label)
    for i in range(0, len(ids), 50):
        part = ids[i:i + 50]
        rows += _fetch(lambda o, part=part: sb.table("pages")
                       .select("id,paper_id,question_number,qp_page_url,ms_page_url")
                       .in_("paper_id", part).not_.is_("qp_page_url", "null")
                       .eq("is_question", True)  # what the two tools actually serve
                       .range(o, o + 999))
    print(f"{subject_code}: {len(papers)} papers, {len(rows)} live questions")

    r2 = ing.get_r2()
    prefix = ing.R2_PUBLIC_URL + "/"

    def get_bytes(url: str) -> bytes | None:
        if not url.startswith(prefix):
            return None
        obj = r2.get_object(Bucket=ing.R2_BUCKET, Key=url[len(prefix):])
        return obj["Body"].read()

    urls = [r["qp_page_url"] for r in rows] + [r["ms_page_url"] for r in rows if r["ms_page_url"]]
    files = fetch_all(urls, CACHE_DIR, get_bytes)
    missing = sum(1 for p in files.values() if p is None)
    print(f"  downloaded {len(files)} segments ({missing} failed)")

    results = audit_rows(subject_code, rows, label, files)
    results.sort(key=lambda r: (r.paper, int("".join(c for c in r.question if c.isdigit()) or 0)))
    counts = summarise(results)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / f"{subject_code}.json").write_text(
        json.dumps({"subject": subject_code, "counts": dict(counts),
                    "rows": [asdict(r) for r in results]}, indent=1), encoding="utf-8")
    with (OUT_DIR / f"{subject_code}.csv").open("w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        writer.writerow(["paper", "question", "verdict", "detail", "qp_url", "ms_url"])
        for r in results:
            writer.writerow([r.paper, r.question, r.verdict, r.detail, r.qp_url, r.ms_url])

    total = len(results)
    print(f"\n{subject_code} live mark-scheme linkage ({total} questions)")
    for verdict, n in counts.most_common():
        print(f"  {verdict:<11} {n:>5}  {100 * n / total:5.1f}%")
    return 0
