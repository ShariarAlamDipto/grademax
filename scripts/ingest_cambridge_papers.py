#!/usr/bin/env python3
"""
Ingest Cambridge (CAIE) past papers: clean watermarks, stamp GradeMax,
upload full-paper PDFs to R2 and create Supabase subjects/papers rows.

Dedicated Cambridge-only script (never add other boards here). Source tree is
the scraper repo:

  <data-root>/Cambridge A Level/<Subject>/<Year>/<Session>/<file>.pdf
  <data-root>/Cambridge IGCSE/<Subject>/<Year>/<Session>/<file>.pdf

  filename = <Subject>_<Year>_<Session>_Paper_<code>_<QP|MS>.pdf

Per PDF (in memory — source files are never modified):
  1. Redact third-party watermarks (gceguide, papacambridge, xtremepapers, …)
     anywhere on any page. Official Cambridge text/URLs are left untouched.
  2. Stamp "GradeMax" top-right on every page (Times-Roman 11pt, same
     treatment watermark_final.py gave the Edexcel trees).
  3. Upload to R2:  cambridge/<igcse|a-level>/<Subject>/<year>/<season>/<file>

DB (production Supabase — additive INSERT/UPSERT only, no schema changes):
  subjects: code=<syllabus code from PDF front page, e.g. 9702>,
            name="Cambridge IGCSE Physics" (matches src/lib/subjects-cambridge.ts
            dbName), board="cambridge", level="igcse"|"a-level"
  papers:   (subject_id, year, season, paper_number) unique,
            pdf_url / markscheme_pdf_url -> R2 public URLs

Paper codes are normalised by stripping leading zeros (Paper_01 == Paper_1)
to fix the known zero-padding QP/MS pairing bug. Variant codes (11, 12, 21…)
are preserved as-is.

Idempotent: R2 uploads are skipped when the key already exists (HEAD), and
papers rows are upserted on the unique constraint.

Usage:
    python -X utf8 scripts/ingest_cambridge_papers.py --dry-run
    python -X utf8 scripts/ingest_cambridge_papers.py --level igcse --subject Physics
    python -X utf8 scripts/ingest_cambridge_papers.py --workers 8
"""
from __future__ import annotations

import argparse
import csv
import io
import json
import os
import re
import sys
import time
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from pathlib import Path

import fitz  # PyMuPDF
from dotenv import load_dotenv

if sys.stdout.encoding != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

REPO_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(REPO_ROOT / ".env.local")

try:
    import boto3
    from botocore.config import Config
    from botocore.exceptions import ClientError
except ImportError:
    print("ERROR: pip install boto3")
    sys.exit(1)

try:
    from supabase import create_client
except ImportError:
    print("ERROR: pip install supabase")
    sys.exit(1)

# ── CLI ──────────────────────────────────────────────────────────────────────

parser = argparse.ArgumentParser(description="Ingest Cambridge past papers to R2 + Supabase")
parser.add_argument("--data-root", default=r"C:\Users\shari\grademax scraper\grademax-scraper\data")
parser.add_argument("--level", choices=["igcse", "a-level"], help="only one level")
parser.add_argument("--subject", help="only one subject folder name, e.g. Physics")
parser.add_argument("--workers", type=int, default=8)
parser.add_argument("--limit", type=int, help="max papers per subject (for testing)")
parser.add_argument("--dry-run", action="store_true", help="no uploads, no DB writes")
parser.add_argument("--force", action="store_true", help="re-upload even if R2 key exists")
args = parser.parse_args()

DATA_ROOT = Path(args.data_root)
DRY_RUN = args.dry_run

# ── Config ───────────────────────────────────────────────────────────────────

R2_ACCOUNT_ID = os.getenv("R2_ACCOUNT_ID")
R2_ACCESS_KEY = os.getenv("R2_ACCESS_KEY_ID")
R2_SECRET = os.getenv("R2_SECRET_ACCESS_KEY")
R2_BUCKET = os.getenv("R2_BUCKET_NAME", "grademax-papers")
R2_PUBLIC_URL = (os.getenv("NEXT_PUBLIC_R2_PUBLIC_URL") or "").rstrip("/")
SUPABASE_URL = os.getenv("NEXT_PUBLIC_SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

for k, v in [
    ("R2_ACCOUNT_ID", R2_ACCOUNT_ID), ("R2_ACCESS_KEY_ID", R2_ACCESS_KEY),
    ("R2_SECRET_ACCESS_KEY", R2_SECRET), ("NEXT_PUBLIC_R2_PUBLIC_URL", R2_PUBLIC_URL),
    ("NEXT_PUBLIC_SUPABASE_URL", SUPABASE_URL), ("SUPABASE_SERVICE_ROLE_KEY", SUPABASE_KEY),
]:
    if not v:
        print(f"ERROR: {k} not in .env.local")
        sys.exit(1)

# level folder -> (db level value, key segment, DB-name prefix)
LEVELS = {
    "Cambridge IGCSE": ("igcse", "igcse", "Cambridge IGCSE"),
    "Cambridge A Level": ("a-level", "a-level", "Cambridge A Level"),
}

# ── Verified subject allow-list ──────────────────────────────────────────────
# The scraper systematically misfiled many minor subjects (2026-07-08 audit:
# "Marine_Science" holds Music 9703, A Level "French" holds German 9717, …).
# Only folders whose front-page syllabus codes match the folder name are
# ingested, and EVERY file is re-verified against these code sets — a file
# whose page 1 shows a different code is skipped and logged.
#
# Excluded pending data repair —
#   A Level: Afrikaans, Art_and_Design, Chinese, Divinity, Dutch, French,
#     German, Global_Perspectives_Research, Korean, Malay, Marine_Science,
#     Physical_Education
#   IGCSE: Arabic_First_Language, Child_Development, Chinese_Second_Language,
#     Drama, Dutch_First_Language, French_First_Language, Hindi_First_Language,
#     Hindi_as_Second_Language, Humanities, Indonesian_First_Language,
#     Indonesian_Second_Language, Italian_First_Language,
#     Japanese_First_Language, Pakistan_Studies, Portuguese, Psychology,
#     Russian, Sociology, Spanish, Turkish_First_Language

VERIFIED_SUBJECTS: dict[str, dict[str, set[str]]] = {
    "Cambridge A Level": {
        "Accounting": {"9706"},
        "Biology": {"9700"},
        "Business": {"9609", "9707"},  # 9707 = pre-2016 "Business Studies" (renumbered)
        "Chemistry": {"9701"},
        "Computer_Science": {"9608", "9618"},
        "Economics": {"9708"},
        "English_Language": {"9093"},
        "English_Literature": {"9695"},
        "Further_Mathematics": {"9231"},
        "Geography": {"9696"},
        "History": {"9389", "9489"},
        "Information_Technology": {"9626"},
        "Law": {"9084"},
        "Mathematics": {"9709"},
        "Physics": {"9702"},
        "Psychology": {"9990"},
        "Sociology": {"9699"},
    },
    "Cambridge IGCSE": {
        "Accounting": {"0452", "0985"},
        "Additional_Mathematics": {"0606"},
        "Afrikaans_Second_Language": {"0548"},
        "Art_and_Design": {"0400", "0989"},
        "Biology": {"0610", "0970"},
        "Business_Studies": {"0450", "0986"},
        "Chemistry": {"0620", "0971"},
        "Chinese_First_Language": {"0509"},
        "Co-ordinated_Sciences": {"0654", "0973"},
        "Combined_Science": {"0653"},
        "Computer_Science": {"0478", "0984"},
        "Design_and_Technology": {"0445", "0979"},
        "Economics": {"0455", "0987"},
        "English_First_Language": {"0500", "0990", "0522", "0524"},
        "English_Literature": {"0486", "0477", "0475", "0992"},
        "English_Second_Language": {"0510", "0511", "0991", "0993"},
        "Environmental_Management": {"0680"},
        "French": {"0520", "7156"},
        "Geography": {"0460", "0976"},
        "German": {"0525", "7159"},
        "Global_Perspectives": {"0457"},
        "History": {"0470", "0977"},
        "ICT": {"0417", "0983"},
        "International_Mathematics": {"0607"},
        "Malay_First_Language": {"0696"},
        "Malay_Second_Language": {"0546"},
        "Mathematics": {"0580", "0980"},
        "Physics": {"0625", "0972"},
        "Religious_Studies": {"0490"},
        "Spanish_First_Language": {"0502"},
        "Travel_and_Tourism": {"0471"},
    },
}

SEASON_SLUG = {"May-Jun": "may-jun", "Oct-Nov": "oct-nov", "Feb-Mar": "feb-mar"}

FNAME_RE = re.compile(r"^(.+)_(\d{4})_([A-Za-z-]+)_Paper_([0-9A-Za-z]+)_(QP|MS)\.pdf$")

# Syllabus code on the CAIE front page, e.g. "9702/22" or "0625/61"
SYLLABUS_RE = re.compile(r"\b(\d{4})/\d{1,3}\b")

OUT_DIR = REPO_ROOT / "data" / "cambridge_ingest"

# ── Watermark cleaning ───────────────────────────────────────────────────────
# Third-party marks only — official Cambridge text/URLs must survive.

THIRD_PARTY_PATTERNS = [
    r"gceguide", r"gce\s*guide", r"papacambridge", r"xtremepape",
    r"dynamicpapers", r"bestexamhelp", r"onlineexamhelp", r"maxpapers",
    r"savemyexams", r"smartexamresources", r"exam-mate", r"cienotes",
    r"igcseexamguru", r"physicsandmathstutor", r"\bpmt\b", r"paperlords",
    r"revisely", r"vedantu", r"tutopiya", r"pastpapers\.co",
]
THIRD_PARTY_RE = re.compile("|".join(THIRD_PARTY_PATTERNS), re.IGNORECASE)

# Any URL in the extreme top/bottom page strips is a scraper-site stamp
# (e.g. "https://xtremepape.rs/") — unless it's an official Cambridge domain,
# which appears in body text ("available at www.cambridgeinternational.org").
URL_RE = re.compile(r"https?://|www\.|\.\w{2,3}/\s*$", re.IGNORECASE)
OFFICIAL_RE = re.compile(r"cambridgeinternational\.org|cie\.org\.uk|cambridge\.org", re.IGNORECASE)
TOP_STRIP_PT = 42.0
BOTTOM_STRIP_PT = 30.0

GM_TEXT = "GradeMax"
GM_FONT = "tiro"       # Times-Roman builtin — same as watermark_final.py
GM_FONT_SIZE = 11.0
GM_RIGHT_MARGIN = 8.0
GM_BASELINE_Y = 14.0   # top strip, clear of the top-left metadata line


class CodeMismatch(Exception):
    """Front-page syllabus code doesn't belong to this subject folder."""


def clean_and_stamp(pdf_bytes: bytes, expected_codes: set[str] | None = None) -> tuple[bytes, int, str | None]:
    """Redact third-party watermarks + stamp GradeMax on every page.

    When `expected_codes` is given, the first page must reference one of those
    syllabus codes — otherwise CodeMismatch is raised (misfiled scraper file).
    Returns (out_bytes, redaction_count, syllabus_code or None).
    Raises on unreadable PDFs — caller decides what to do.
    """
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    redactions = 0
    syllabus_code: str | None = None

    gm_width = fitz.get_text_length(GM_TEXT, fontname=GM_FONT, fontsize=GM_FONT_SIZE)

    for page_idx, page in enumerate(doc):
        text = page.get_text()
        if page_idx == 0:
            found_codes = set(SYLLABUS_RE.findall(text))
            if found_codes:
                syllabus_code = sorted(found_codes)[0]
            # Quarantine only when the page shows a REAL, readable syllabus code
            # that belongs to a different subject. Many 2024–2025 papers embed
            # subset fonts with no ToUnicode map, so extraction yields garbage
            # and no code is found — those can't be verified per-file, so we
            # trust the folder-level content audit (allow-list) and let them
            # through rather than dropping legitimate papers.
            if expected_codes and found_codes and not (found_codes & expected_codes):
                doc.close()
                raise CodeMismatch(
                    f"page-1 codes {sorted(found_codes)} not in {sorted(expected_codes)}"
                )

        page_redacted = False
        bottom_edge = page.rect.height - BOTTOM_STRIP_PT
        if THIRD_PARTY_RE.search(text) or URL_RE.search(text):
            for block in page.get_text("dict")["blocks"]:
                if block.get("type") != 0:
                    continue
                for line in block["lines"]:
                    for span in line["spans"]:
                        span_text = span.get("text", "")
                        if not span_text.strip():
                            continue
                        bbox = fitz.Rect(span["bbox"])
                        in_strip = bbox.y1 <= TOP_STRIP_PT or bbox.y0 >= bottom_edge
                        is_third_party = bool(THIRD_PARTY_RE.search(span_text))
                        is_strip_url = (
                            in_strip
                            and URL_RE.search(span_text)
                            and not OFFICIAL_RE.search(span_text)
                            and "grademax" not in span_text.lower()
                        )
                        if is_third_party or is_strip_url:
                            page.add_redact_annot(bbox, fill=(1, 1, 1))
                            redactions += 1
                            page_redacted = True

        # Vector watermarks: some scraper stamps (e.g. "https://xtremepape.rs/")
        # are drawn as line art, invisible to text extraction. A small drawing
        # confined to the bottom strip is a stamp — real content never lives
        # entirely down there. (Top strip is excluded: mark-scheme tables start
        # their top border around y=35.) These are painted over in white rather
        # than redacted, so a connected table path can never be collateral.
        whiteouts: list[fitz.Rect] = []
        for d in page.get_cdrawings():
            r = fitz.Rect(d["rect"])
            if not r.is_empty and r.y0 >= bottom_edge and r.height <= 15 and r.width <= 350:
                whiteouts.append(r)

        if page_redacted:
            # graphics=NONE: never let a text redaction pull out nearby line art
            page.apply_redactions(graphics=fitz.PDF_REDACT_LINE_ART_NONE)
        for r in whiteouts:
            page.draw_rect(r + (-1, -1, 1, 1), color=None, fill=(1, 1, 1), overlay=True)
            redactions += 1

        # Stamp GradeMax top-right unless this page already carries it
        if "grademax" not in text.lower():
            x = page.rect.width - gm_width - GM_RIGHT_MARGIN
            page.insert_text(
                (x, GM_BASELINE_Y), GM_TEXT,
                fontname=GM_FONT, fontsize=GM_FONT_SIZE, color=(0, 0, 0),
                overlay=True,
            )

    out = doc.tobytes(garbage=3, deflate=True)
    doc.close()
    return out, redactions, syllabus_code


# ── Filename parsing / grouping ──────────────────────────────────────────────

def normalize_paper_code(code: str) -> str:
    """Strip leading zeros: 01 -> 1, 02 -> 2. Variant codes (11, 21) unchanged."""
    stripped = code.lstrip("0")
    return stripped if stripped else code


@dataclass
class PaperEntry:
    year: int
    season_slug: str
    season_folder: str
    paper_code: str                       # normalised
    qp: Path | None = None
    ms: Path | None = None
    qp_url: str | None = None
    ms_url: str | None = None
    notes: list[str] = field(default_factory=list)


def collect_subject_papers(level_folder: str, subject_dir: Path) -> dict[tuple, PaperEntry]:
    """Group a subject's PDFs into (year, season, paper) -> PaperEntry."""
    entries: dict[tuple, PaperEntry] = {}
    for pdf in sorted(subject_dir.rglob("*.pdf")):
        rel = pdf.relative_to(subject_dir)
        if len(rel.parts) != 3:  # Year/Session/file.pdf
            continue
        year_s, session, fname = rel.parts
        m = FNAME_RE.match(fname)
        if not m or session not in SEASON_SLUG or not year_s.isdigit():
            print(f"    SKIP unparseable: {level_folder}/{subject_dir.name}/{rel}")
            continue
        _, _, _, raw_code, dtype = m.groups()
        code = normalize_paper_code(raw_code)
        key = (int(year_s), SEASON_SLUG[session], code)
        e = entries.get(key)
        if e is None:
            e = PaperEntry(int(year_s), SEASON_SLUG[session], session, code)
            entries[key] = e
        # Prefer the non-zero-padded filename when both Paper_1 and Paper_01 exist
        if dtype == "QP":
            if e.qp is None or raw_code == code:
                e.qp = pdf
        else:
            if e.ms is None or raw_code == code:
                e.ms = pdf
    return entries


# ── R2 ───────────────────────────────────────────────────────────────────────

r2 = boto3.client(
    "s3",
    endpoint_url=f"https://{R2_ACCOUNT_ID}.r2.cloudflarestorage.com",
    aws_access_key_id=R2_ACCESS_KEY,
    aws_secret_access_key=R2_SECRET,
    region_name="auto",
    config=Config(retries={"max_attempts": 5, "mode": "standard"}, max_pool_connections=32),
)


def r2_exists(key: str) -> bool:
    try:
        r2.head_object(Bucket=R2_BUCKET, Key=key)
        return True
    except ClientError:
        return False


def r2_upload(key: str, data: bytes) -> None:
    for attempt in range(3):
        try:
            r2.put_object(
                Bucket=R2_BUCKET, Key=key, Body=data,
                ContentType="application/pdf",
                CacheControl="public, max-age=31536000, immutable",
            )
            return
        except ClientError:
            if attempt == 2:
                raise
            time.sleep(1.5 ** attempt)


# ── Per-file pipeline (worker thread) ────────────────────────────────────────

def process_and_upload(pdf_path: Path, key: str, expected_codes: set[str]) -> dict:
    """Clean + stamp + upload one PDF. Returns a result record."""
    rec: dict = {"key": key, "src": str(pdf_path), "status": "ok",
                 "redactions": 0, "code": None, "skipped": False}
    if not args.force and not DRY_RUN and r2_exists(key):
        rec["skipped"] = True
        return rec
    raw = pdf_path.read_bytes()
    try:
        cleaned, redactions, code = clean_and_stamp(raw, expected_codes)
        rec["redactions"] = redactions
        rec["code"] = code
    except CodeMismatch as e:  # misfiled content — never publish it
        rec["status"] = f"code-mismatch: {e}"
        rec["mismatch"] = True
        return rec
    except Exception as e:  # unreadable/corrupt PDF — ship the original
        rec["status"] = f"clean-failed: {e}"
        cleaned = raw
    if not DRY_RUN:
        r2_upload(key, cleaned)
    return rec


# ── Supabase ─────────────────────────────────────────────────────────────────

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)


def load_existing_subjects() -> dict[str, dict]:
    rows = supabase.table("subjects").select("id, code, name, board, level").execute().data
    return {r["name"]: r for r in rows}


def synth_code(level_db: str, folder: str) -> str:
    prefix = "CAM-IG" if level_db == "igcse" else "CAM-AL"
    return f"{prefix}-{folder.upper().replace('_', '').replace('-', '')[:16]}"


def ensure_subject(existing: dict[str, dict], used_codes: set[str],
                   db_name: str, level_db: str, folder: str,
                   syllabus_code: str | None) -> str:
    """Insert the subjects row if missing; returns subject id."""
    row = existing.get(db_name)
    if row:
        return row["id"]
    code = syllabus_code if (syllabus_code and syllabus_code not in used_codes) else synth_code(level_db, folder)
    if code in used_codes:
        code = f"{code}-{level_db.upper()[:2]}"
    if DRY_RUN:
        print(f"    [dry] would insert subject {db_name!r} code={code}")
        existing[db_name] = {"id": f"dry-{db_name}", "code": code}
        used_codes.add(code)
        return existing[db_name]["id"]
    res = supabase.table("subjects").insert({
        "code": code, "name": db_name, "board": "cambridge", "level": level_db,
    }).execute()
    row = res.data[0]
    existing[db_name] = row
    used_codes.add(code)
    print(f"    + subject {db_name!r} code={code} id={row['id']}")
    return row["id"]


def upsert_papers(rows: list[dict]) -> None:
    if DRY_RUN or not rows:
        return
    for i in range(0, len(rows), 500):
        chunk = rows[i:i + 500]
        supabase.table("papers").upsert(
            chunk, on_conflict="subject_id,year,season,paper_number"
        ).execute()


# ── Main ─────────────────────────────────────────────────────────────────────

def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    manifest_path = OUT_DIR / "manifest.jsonl"
    failures_path = OUT_DIR / "failures.csv"
    codes_path = OUT_DIR / "syllabus_codes.json"

    existing_subjects = load_existing_subjects()
    used_codes = {r["code"] for r in existing_subjects.values()}
    syllabus_codes: dict[str, str] = {}
    if codes_path.exists():
        syllabus_codes = json.loads(codes_path.read_text(encoding="utf-8"))

    totals = Counter()
    failures: list[dict] = []
    start = time.time()

    manifest_f = open(manifest_path, "a", encoding="utf-8")

    for level_folder, (level_db, key_level, name_prefix) in LEVELS.items():
        if args.level and level_db != args.level:
            continue
        level_dir = DATA_ROOT / level_folder
        if not level_dir.is_dir():
            print(f"WARNING: missing {level_dir}")
            continue

        verified = VERIFIED_SUBJECTS[level_folder]
        subject_dirs = sorted(d for d in level_dir.iterdir() if d.is_dir())
        if args.subject:
            subject_dirs = [d for d in subject_dirs if d.name.lower() == args.subject.lower()]

        for subject_dir in subject_dirs:
            folder = subject_dir.name
            if folder not in verified:
                print(f"\n[{level_db}] {folder}: EXCLUDED (failed content audit — see allow-list)")
                totals["excluded_subjects"] += 1
                continue
            expected_codes = verified[folder]
            display = folder.replace("_", " ")
            db_name = f"{name_prefix} {display}"
            entries = collect_subject_papers(level_folder, subject_dir)
            if not entries:
                continue
            keys = sorted(entries.keys())
            if args.limit:
                keys = keys[: args.limit]
            print(f"\n[{level_db}] {display}: {len(keys)} papers "
                  f"({sum(1 for k in keys if entries[k].qp)} QP / "
                  f"{sum(1 for k in keys if entries[k].ms)} MS files)")

            # ── clean + upload in parallel ─────────────────────────────────
            jobs: list[tuple[PaperEntry, str, str, Path]] = []
            for k in keys:
                e = entries[k]
                base = f"cambridge/{key_level}/{folder}/{e.year}/{e.season_slug}"
                if e.qp:
                    jobs.append((e, "qp", f"{base}/{e.qp.name}", e.qp))
                if e.ms:
                    jobs.append((e, "ms", f"{base}/{e.ms.name}", e.ms))

            subj_codes: Counter = Counter()
            ok = skip = fail = mismatched = 0
            with ThreadPoolExecutor(max_workers=args.workers) as pool:
                futs = {pool.submit(process_and_upload, path, key, expected_codes): (e, kind, key)
                        for (e, kind, key, path) in jobs}
                for fut in as_completed(futs):
                    e, kind, key = futs[fut]
                    try:
                        rec = fut.result()
                    except Exception as exc:
                        fail += 1
                        failures.append({"key": key, "error": str(exc)})
                        print(f"    FAIL {key}: {exc}")
                        continue
                    if rec.get("mismatch"):
                        mismatched += 1
                        failures.append({"key": key, "error": rec["status"]})
                        manifest_f.write(json.dumps(rec) + "\n")
                        continue  # no URL — misfiled file stays unpublished
                    url = f"{R2_PUBLIC_URL}/{key}"
                    if kind == "qp":
                        e.qp_url = url
                    else:
                        e.ms_url = url
                    if rec.get("code"):
                        subj_codes[rec["code"]] += 1
                    if rec["skipped"]:
                        skip += 1
                    elif rec["status"] == "ok":
                        ok += 1
                    else:
                        ok += 1  # uploaded original bytes
                        failures.append({"key": key, "error": rec["status"]})
                    manifest_f.write(json.dumps(rec) + "\n")

            # ── subject + paper rows ───────────────────────────────────────
            syl = syllabus_codes.get(db_name) or (subj_codes.most_common(1)[0][0] if subj_codes else None)
            if syl:
                syllabus_codes[db_name] = syl
            subject_id = ensure_subject(existing_subjects, used_codes,
                                        db_name, level_db, folder, syl)
            paper_rows = [
                {
                    "subject_id": subject_id,
                    "year": e.year,
                    "season": e.season_slug,
                    "paper_number": e.paper_code,
                    "pdf_url": e.qp_url,
                    "markscheme_pdf_url": e.ms_url,
                }
                for k in keys
                if (e := entries[k]).qp_url or e.ms_url
            ]
            upsert_papers(paper_rows)
            totals["papers"] += len(paper_rows)
            totals["uploaded"] += ok
            totals["skipped"] += skip
            totals["failed"] += fail
            totals["mismatched"] += mismatched
            print(f"    -> {len(paper_rows)} paper rows | uploads ok={ok} skip={skip} fail={fail} "
                  f"mismatch={mismatched} | code={syl or 'n/a'}")

    manifest_f.close()
    codes_path.write_text(json.dumps(syllabus_codes, indent=2), encoding="utf-8")
    if failures:
        with open(failures_path, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=["key", "error"])
            w.writeheader()
            w.writerows(failures)

    mins = (time.time() - start) / 60
    print("\n" + "=" * 72)
    print(f"DONE in {mins:.1f} min | papers={totals['papers']} uploaded={totals['uploaded']} "
          f"skipped={totals['skipped']} failed={totals['failed']} "
          f"mismatched-files={totals['mismatched']} excluded-subjects={totals['excluded_subjects']}")
    if failures:
        print(f"{len(failures)} failures -> {failures_path}")
    return 1 if totals["failed"] else 0


if __name__ == "__main__":
    sys.exit(main())
