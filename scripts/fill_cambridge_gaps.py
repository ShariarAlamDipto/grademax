#!/usr/bin/env python3
"""
Fill missing QP/MS gaps in the hosted Cambridge past-paper set.

For every `papers` row (Cambridge board) that has a QP but no MS (or vice
versa), fetch the missing counterpart from a public Cambridge mirror, verify
it really belongs to the subject, strip third-party watermarks, stamp
"GradeMax", upload to R2 alongside its partner, and set the missing URL column.

Source: papacambridge flat store (primary) — files are addressed purely by the
Cambridge filename `{code}_{sess}{yy}_{type}_{variant}.pdf`, so no directory
crawling is needed. dynamicpapers / bestexamhelp / pastpapers.co are fallbacks.

Idempotent: skips rows that already have both files; HEAD-skips R2 keys that
already exist. Re-verifies each download's front-page syllabus code against the
subject's known code set (reusing the ingest guard) so a wrong-subject or error
page can never be published.

Usage:
    python -X utf8 scripts/fill_cambridge_gaps.py --dry-run
    python -X utf8 scripts/fill_cambridge_gaps.py --apply
    python -X utf8 scripts/fill_cambridge_gaps.py --apply --subject "Cambridge A Level Chemistry"
"""
from __future__ import annotations

import argparse
import csv
import io
import sys
import time
import urllib.request
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

if sys.stdout.encoding != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

REPO_ROOT = Path(__file__).resolve().parent.parent

# Import the ingest module for its cleaning pipeline, clients and code sets.
# It parses argv + builds R2/Supabase clients at import, so neutralise argv first.
_saved_argv = sys.argv
sys.argv = [_saved_argv[0]]
sys.path.insert(0, str(REPO_ROOT / "scripts"))
import ingest_cambridge_papers as ing  # noqa: E402
sys.argv = _saved_argv

import fitz  # noqa: E402  (already a dep of the ingest module)

# ── CLI ──────────────────────────────────────────────────────────────────────
parser = argparse.ArgumentParser(description="Fill missing Cambridge QP/MS from public mirrors")
parser.add_argument("--apply", action="store_true", help="download + upload + write DB (default: dry-run)")
parser.add_argument("--dry-run", action="store_true", help="probe availability only")
parser.add_argument("--subject", help="limit to one DB subject name")
parser.add_argument("--workers", type=int, default=6)
parser.add_argument("--limit", type=int, help="cap number of gaps processed (testing)")
args = parser.parse_args()
APPLY = args.apply and not args.dry_run

# ── Mirrors (flat filename stores first) ─────────────────────────────────────
HOSTS = [
    "https://pastpapers.papacambridge.com/directories/CAIE/CAIE-pastpapers/upload/{f}",
    "https://dynamicpapers.com/wp-content/uploads/2015/09/{f}",
    "https://bestexamhelp.com/exam/{path}/{f}",  # needs subject path — used only when known
]
FLAT_HOSTS = [HOSTS[0], HOSTS[1]]
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"}

SESS_LETTER = {"may-jun": "s", "oct-nov": "w", "feb-mar": "m"}
SEASON_FOLDER = {"may-jun": "May-Jun", "oct-nov": "Oct-Nov", "feb-mar": "Feb-Mar"}

# subject dbName -> set of valid syllabus codes (base + alternates), from the
# ingest allow-list so alternate "9-to-1" grading codes are also tried.
def _build_code_map() -> dict[str, set[str]]:
    m: dict[str, set[str]] = {}
    for level_folder, subjects in ing.VERIFIED_SUBJECTS.items():
        prefix = "Cambridge IGCSE" if "IGCSE" in level_folder else "Cambridge A Level"
        for folder, codes in subjects.items():
            db_name = f"{prefix} {folder.replace('_', ' ')}"
            m[db_name] = set(codes)
    return m

CODE_MAP = _build_code_map()


def db_name_to_folder(db_name: str) -> tuple[str, str, str]:
    """Return (level_db, key_level, source_folder) for a Cambridge dbName."""
    if db_name.startswith("Cambridge IGCSE "):
        return "igcse", "igcse", db_name[len("Cambridge IGCSE "):].replace(" ", "_")
    return "a-level", "a-level", db_name[len("Cambridge A Level "):].replace(" ", "_")


def candidate_filenames(codes: set[str], season: str, year: int, dtype: str, variant: str) -> list[str]:
    yy = str(year)[2:]
    sess = SESS_LETTER[season] + yy
    t = dtype.lower()
    variants = [variant]
    if variant.isdigit() and len(variant) == 1:
        variants.append(variant.zfill(2))  # some stores pad single components
    names = []
    for code in sorted(codes):
        for v in variants:
            names.append(f"{code}_{sess}_{t}_{v}.pdf")
    return names


def try_download(filename: str) -> bytes | None:
    for tmpl in FLAT_HOSTS:
        url = tmpl.format(f=filename)
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=30) as r:
                data = r.read()
            if len(data) > 3000 and data[:5] == b"%PDF-":
                return data
        except Exception:
            continue
    return None


def process_gap(gap: dict) -> dict:
    """Attempt to fetch + clean + upload the one missing file for a gap."""
    db_name = gap["subject"]
    dtype = gap["need"]  # "QP" | "MS"
    variant = str(gap["paper"])
    year = gap["year"]
    season = gap["season"]
    codes = CODE_MAP.get(db_name, set())
    rec = {**gap, "status": "no-source", "url": None, "filename": None, "redactions": 0}
    if not codes:
        rec["status"] = "no-code-map"
        return rec

    names = candidate_filenames(codes, season, year, dtype, variant)
    data = None
    used = None
    for fn in names:
        data = try_download(fn)
        if data:
            used = fn
            break
    if not data:
        return rec  # no-source (tried all code/variant combos)
    rec["filename"] = used

    # verify subject via front-page code, then clean + stamp
    try:
        cleaned, redactions, code = ing.clean_and_stamp(data, codes)
        rec["redactions"] = redactions
    except ing.CodeMismatch as e:
        rec["status"] = f"code-mismatch:{e}"
        return rec
    except Exception as e:
        rec["status"] = f"clean-failed:{e}"
        cleaned = data

    # R2 key mirrors the ingest layout; filename mirrors the partner already hosted
    _, key_level, folder = db_name_to_folder(db_name)
    disp = folder.replace("_", " ")
    fname = f"{folder}_{year}_{SEASON_FOLDER[season]}_Paper_{variant}_{dtype}.pdf"
    key = f"cambridge/{key_level}/{folder}/{year}/{season}/{fname}"
    url = f"{ing.R2_PUBLIC_URL}/{key}"
    rec["url"] = url

    rec["key"] = key
    if not APPLY:
        rec["status"] = "would-fill"
        return rec

    # Upload only (boto3 is thread-safe). DB write is done by the main thread
    # because the shared Supabase httpx client is NOT safe for concurrent use.
    if not ing.r2_exists(key):
        ing.r2_upload(key, cleaned)
    rec["status"] = "uploaded"
    return rec


def load_gaps() -> list[dict]:
    sb = ing.supabase
    cam = sb.table("subjects").select("id,name").eq("board", "cambridge").execute().data
    id2name = {s["id"]: s["name"] for s in cam}
    ids = list(id2name)
    rows = []
    for i in range(0, len(ids), 25):
        chunk = ids[i:i+25]
        off = 0
        while True:
            r = (sb.table("papers")
                 .select("subject_id,year,season,paper_number,pdf_url,markscheme_pdf_url")
                 .in_("subject_id", chunk).range(off, off+999).execute().data)
            if not r:
                break
            rows.extend(r)
            if len(r) < 1000:
                break
            off += 1000
    gaps = []
    for r in rows:
        name = id2name[r["subject_id"]]
        if args.subject and name != args.subject:
            continue
        if not r["pdf_url"]:
            gaps.append({"subject": name, "subject_id": r["subject_id"], "year": r["year"],
                         "season": r["season"], "paper": r["paper_number"], "need": "QP"})
        if not r["markscheme_pdf_url"]:
            gaps.append({"subject": name, "subject_id": r["subject_id"], "year": r["year"],
                         "season": r["season"], "paper": r["paper_number"], "need": "MS"})
    # only seasons we can address
    gaps = [g for g in gaps if g["season"] in SESS_LETTER]
    if args.limit:
        gaps = gaps[:args.limit]
    return gaps


def main() -> int:
    gaps = load_gaps()
    print("=" * 72)
    print(f"Cambridge gap-fill {'[APPLY]' if APPLY else '[DRY-RUN]'} — {len(gaps)} missing files to source")
    print("=" * 72)
    results = []
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futs = {pool.submit(process_gap, g): g for g in gaps}
        for fut in as_completed(futs):
            results.append(fut.result())

    # Sequential DB writes on the main thread (Supabase client is single-threaded).
    if APPLY:
        wrote = 0
        for r in results:
            if r["status"] != "uploaded":
                continue
            col = "pdf_url" if r["need"] == "QP" else "markscheme_pdf_url"
            try:
                ing.supabase.table("papers").update({col: r["url"]}) \
                    .eq("subject_id", r["subject_id"]).eq("year", r["year"]) \
                    .eq("season", r["season"]).eq("paper_number", str(r["paper"])).execute()
                r["status"] = "filled"
                wrote += 1
            except Exception as e:
                r["status"] = f"db-failed:{e}"
        print(f"DB rows updated: {wrote}")

    status = Counter(r["status"].split(":")[0] for r in results)
    filled = [r for r in results if r["status"] in ("filled", "would-fill", "uploaded")]
    print(f"\nresults: {dict(status)}")
    print(f"fillable/filled: {len(filled)} / {len(gaps)}")

    by_subj = Counter(r["subject"] for r in filled)
    print("\n== fillable by subject ==")
    for s, n in by_subj.most_common():
        print(f"  {n:3d}  {s}")

    unresolved = [r for r in results if r["status"] not in ("filled", "would-fill")]
    outdir = REPO_ROOT / "data" / "cambridge_ingest"
    outdir.mkdir(parents=True, exist_ok=True)
    with open(outdir / "gap_fill_unresolved.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["subject", "year", "season", "paper", "need", "status"])
        w.writeheader()
        for r in unresolved:
            w.writerow({k: r.get(k) for k in ["subject", "year", "season", "paper", "need", "status"]})
    print(f"\nunresolved ({len(unresolved)}) -> data/cambridge_ingest/gap_fill_unresolved.csv")
    return 0


if __name__ == "__main__":
    sys.exit(main())
