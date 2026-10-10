#!/usr/bin/env python3
"""
Publish the practical-paper data files for the ICT subjects and link them on
`papers.data_file_url` (the past-papers page already shows a "Data files"
link whenever that column is set).

    python scripts/publish_ict_data_files.py             # dry run
    python scripts/publish_ict_data_files.py --execute

Sources (validated zips, see data/ict_data_files/):
  * Edexcel IGCSE ICT 4IT1 Paper 2 -- data/ict_data_files/edexcel/<year>_<season>.zip
    (Pearson "Data files and notes for centres"; 2025 sittings are secure
    centre-only content and are not available).
  * Cambridge IGCSE ICT 0417 / A Level IT 9626 practical papers --
    data/ict_data_files/cambridge/manifest.json (scripts/fetch_cambridge_ict_source_files.py).

Storage: each zip sits next to its own question paper in the one paper tree,
  <qp folder>/<qp name with _QP.pdf replaced by _Data_Files.zip>
so a paper's QP, MS and data files share one folder. Only rows whose
data_file_url is empty or already points at that same key are written.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lib.live_paper_sources import ROOT, fetch_rows, supabase_client  # noqa: E402

EDEXCEL_DIR = ROOT / "data" / "ict_data_files" / "edexcel"
CAMBRIDGE_MANIFEST = ROOT / "data" / "ict_data_files" / "cambridge" / "manifest.json"


def r2_client():
    import ingest_2026_papers as ing  # noqa: PLC0415 -- loads env on import
    return ing.get_r2(), ing.R2_BUCKET, ing.R2_PUBLIC_URL.rstrip("/") + "/"


def data_key(qp_url: str, public: str) -> str:
    key = qp_url[len(public):]
    if not key.endswith("_QP.pdf"):
        raise ValueError(f"unexpected QP key {key}")
    return key[: -len("_QP.pdf")] + "_Data_Files.zip"


def plan(sb, public: str) -> list[dict]:
    jobs: list[dict] = []
    subjects = {s["code"]: s["id"] for s in sb.table("subjects").select("id,code")
                .in_("code", ["4IT1", "0417", "9626"]).execute().data}
    # Edexcel: one zip per sitting, attached to that sitting's Paper 2.
    papers = fetch_rows(lambda o: sb.table("papers").select("id,year,season,paper_number,pdf_url,data_file_url")
                        .eq("subject_id", subjects["4IT1"]).range(o, o + 999))
    for p in papers:
        local = EDEXCEL_DIR / f"{p['year']}_{p['season']}.zip"
        if p["paper_number"] == "2" and local.is_file() and p["pdf_url"]:
            jobs.append({"paper_id": p["id"], "file": local, "qp": p["pdf_url"], "current": p["data_file_url"]})
    # Cambridge: one zip per practical paper.
    manifest = json.loads(CAMBRIDGE_MANIFEST.read_text(encoding="utf-8"))
    ok = {m["paper_id"]: ROOT / m["file"] for m in manifest if m["status"] == "ok"}
    ids = list(ok)
    for i in range(0, len(ids), 100):
        for p in sb.table("papers").select("id,pdf_url,data_file_url").in_("id", ids[i:i + 100]).execute().data:
            if p["pdf_url"]:
                jobs.append({"paper_id": p["id"], "file": ok[p["id"]], "qp": p["pdf_url"],
                             "current": p["data_file_url"]})
    for job in jobs:
        job["key"] = data_key(job["qp"], public)
        job["url"] = public + job["key"]
    return jobs


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()
    sb = supabase_client()
    r2, bucket, public = r2_client()
    jobs = plan(sb, public)
    conflicts = [j for j in jobs if j["current"] and j["current"] != j["url"]]
    todo = [j for j in jobs if j not in conflicts]
    print(f"data files planned: {len(jobs)}  (conflicting existing links left alone: {len(conflicts)})")
    for j in todo[:5]:
        print("  ", j["file"].relative_to(ROOT), "->", j["key"])
    if not args.execute:
        print("Dry run only. Re-run with --execute to write.")
        return 0
    for j in todo:
        r2.put_object(Bucket=bucket, Key=j["key"], Body=j["file"].read_bytes(),
                      ContentType="application/zip",
                      ContentDisposition=f'attachment; filename="{Path(j["key"]).name}"')
        sb.table("papers").update({"data_file_url": j["url"]}).eq("id", j["paper_id"]).execute()
    print(f"uploaded and linked: {len(todo)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
