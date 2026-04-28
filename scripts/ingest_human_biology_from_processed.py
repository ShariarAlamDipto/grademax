#!/usr/bin/env python3
"""
GradeMax — Human Biology Ingest Script
=======================================
Reads segmented question PDFs from data/processed/Human_Biology/
Uploads to Supabase Storage (question-pdfs bucket) and creates pages rows.

Prerequisites:
  - segment_human_biology_papers.py must have run first
  - Subject row (4HB1) must exist in DB

Usage:
  python scripts/ingest_human_biology_from_processed.py
  python scripts/ingest_human_biology_from_processed.py --dry-run
"""

import json
import os
import sys
import time
import argparse
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from supabase import create_client, Client

try:
    import fitz
    HAVE_FITZ = True
except ImportError:
    HAVE_FITZ = False

load_dotenv(Path(__file__).parent.parent / ".env.local")

SUPABASE_URL = os.getenv("NEXT_PUBLIC_SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    print("[ERROR] Missing Supabase credentials in .env.local")
    sys.exit(1)

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

PROCESSED_BASE = Path(__file__).parent.parent / "data" / "processed" / "Human_Biology"
STORAGE_BUCKET = "question-pdfs"
SUBJECT_CODE   = "4HB1"
STORAGE_NAME   = "Human_Biology"


# ---------------------------------------------------------------------------
# DB helpers
# ---------------------------------------------------------------------------

def get_subject_id() -> str:
    result = supabase.table("subjects").select("id").eq("code", SUBJECT_CODE).execute()
    if not result.data:
        raise RuntimeError(f"Subject {SUBJECT_CODE} not found in DB — add it first")
    return result.data[0]["id"]


def find_paper(subject_id: str, year: int, season: str, paper_number: str) -> Optional[str]:
    result = (
        supabase.table("papers")
        .select("id")
        .eq("subject_id", subject_id)
        .eq("year", year)
        .eq("season", season)
        .eq("paper_number", paper_number)
        .execute()
    )
    return result.data[0]["id"] if result.data else None


def find_or_create_paper(
    subject_id: str, year: int, season: str, paper_number: str, dry_run: bool
) -> Optional[str]:
    paper_id = find_paper(subject_id, year, season, paper_number)
    if paper_id:
        return paper_id

    stripped = paper_number
    for _ in range(3):
        if not stripped or not stripped[-1].isalpha():
            break
        stripped = stripped[:-1]
        paper_id = find_paper(subject_id, year, season, stripped)
        if paper_id:
            return paper_id

    if dry_run:
        return "DRY_RUN_PAPER_ID"
    result = supabase.table("papers").insert({
        "subject_id":   subject_id,
        "year":         year,
        "season":       season,
        "paper_number": paper_number,
    }).execute()
    return result.data[0]["id"]


def get_existing_page(paper_id: str, question_number: str) -> Optional[tuple]:
    result = (
        supabase.table("pages")
        .select("id, qp_page_url")
        .eq("paper_id", paper_id)
        .eq("question_number", question_number)
        .execute()
    )
    if result.data:
        row = result.data[0]
        return row["id"], bool(row.get("qp_page_url"))
    return None


def create_page(paper_id: str, question_number: str, page_number: int, text_excerpt: str) -> str:
    result = supabase.table("pages").insert({
        "paper_id":        paper_id,
        "page_number":     page_number,
        "question_number": question_number,
        "is_question":     True,
        "has_diagram":     False,
        "topics":          [],
        "text_excerpt":    text_excerpt[:500],
    }).execute()
    return result.data[0]["id"]


def update_page_urls(page_id: str, qp_url: Optional[str], ms_url: Optional[str], dry_run: bool) -> None:
    if dry_run:
        return
    update = {}
    if qp_url:
        update["qp_page_url"] = qp_url
    if ms_url:
        update["ms_page_url"] = ms_url
    if not update:
        return
    for attempt in range(4):
        try:
            supabase.table("pages").update(update).eq("id", page_id).execute()
            return
        except Exception as e:
            if attempt == 3:
                print(f"      [DB ERR] update_page_urls: {e}")
            time.sleep(2 ** attempt)


# ---------------------------------------------------------------------------
# Storage helpers
# ---------------------------------------------------------------------------

def upload_file(file_path: Path, storage_path: str, dry_run: bool) -> Optional[str]:
    if dry_run:
        return f"DRY_RUN::{storage_path}"
    try:
        with open(file_path, "rb") as f:
            pdf_bytes = f.read()
        supabase.storage.from_(STORAGE_BUCKET).upload(
            storage_path,
            pdf_bytes,
            {"content-type": "application/pdf", "upsert": "true"},
        )
    except Exception as e:
        err = str(e).lower()
        if "already exists" not in err and "duplicate" not in err:
            print(f"      [UPLOAD ERR] {storage_path}: {e}")
            return None
    return supabase.storage.from_(STORAGE_BUCKET).get_public_url(storage_path)


# ---------------------------------------------------------------------------
# Text extraction fallback
# ---------------------------------------------------------------------------

def extract_text_from_pdf(pdf_path: Path) -> str:
    if not HAVE_FITZ or not pdf_path.exists():
        return ""
    try:
        doc = fitz.open(str(pdf_path))
        text = "\n".join(doc[i].get_text("text") for i in range(len(doc)))
        doc.close()
        return text.strip()
    except Exception:
        return ""


# ---------------------------------------------------------------------------
# Folder processor
# ---------------------------------------------------------------------------

def process_folder(folder: Path, subject_id: str, dry_run: bool, stats: dict) -> None:
    manifest_path = folder / "manifest.json"
    if not manifest_path.exists():
        print(f"  [SKIP] No manifest.json in {folder.name}")
        return

    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except Exception as e:
        print(f"  [ERR] Bad manifest in {folder.name}: {e}")
        stats["errors"] += 1
        return

    year         = manifest.get("year")
    season       = manifest.get("season")
    paper_number = manifest.get("paper_number")
    questions    = manifest.get("questions", [])

    if not all([year, season, paper_number]) or not questions:
        print(f"  [SKIP] Incomplete manifest: {folder.name}")
        return

    paper_id = find_or_create_paper(subject_id, year, season, paper_number, dry_run)
    if paper_id is None:
        print(f"  [ERR] Cannot get/create paper for {folder.name}")
        stats["missing_papers"] += 1
        return

    pages_dir      = folder / "pages"
    ms_dir         = folder / "markschemes"
    storage_folder = f"{year}_{season}_{paper_number}"

    folder_pages    = 0
    folder_uploaded = 0

    for i, q in enumerate(questions):
        q_num    = str(q["question_number"])
        page_num = i + 1

        existing        = get_existing_page(paper_id, q_num)
        already_has_url = False

        if existing is not None:
            page_id, already_has_url = existing
        else:
            text = q.get("text_excerpt") or ""
            if not text:
                text = extract_text_from_pdf(pages_dir / f"q{q_num}.pdf")
            if not dry_run:
                page_id = create_page(paper_id, q_num, page_num, text)
                stats["pages_created"] += 1
            else:
                page_id = "DRY_RUN_PAGE_ID"
                stats["pages_created"] += 1

        folder_pages += 1

        if already_has_url and not dry_run:
            folder_uploaded += 1
            stats["uploaded"] += 1
            continue

        qp_file = pages_dir / f"q{q_num}.pdf"
        if not qp_file.exists():
            stats["missing_qp"] += 1
            continue

        ms_file = ms_dir / f"q{q_num}.pdf" if ms_dir.exists() else None
        if ms_file and not ms_file.exists():
            ms_file = None

        storage_qp = f"subjects/{STORAGE_NAME}/pages/{storage_folder}/q{q_num}.pdf"
        qp_url = upload_file(qp_file, storage_qp, dry_run)

        ms_url = None
        if ms_file:
            storage_ms = f"subjects/{STORAGE_NAME}/pages/{storage_folder}/q{q_num}_ms.pdf"
            ms_url = upload_file(ms_file, storage_ms, dry_run)

        if qp_url:
            update_page_urls(page_id, qp_url, ms_url, dry_run)
            folder_uploaded += 1
            stats["uploaded"] += 1

    print(f"  {folder.name}: {folder_pages} questions, {folder_uploaded} uploaded")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Upload Human Biology (4HB1) question PDFs to Supabase"
    )
    parser.add_argument("--dry-run", action="store_true",
                        help="Print plan without writing to DB or storage")
    args = parser.parse_args()

    print(f"\n{'='*60}")
    print(f"  HUMAN BIOLOGY ({SUBJECT_CODE})  {'[DRY RUN]' if args.dry_run else ''}")
    print(f"{'='*60}")

    if not PROCESSED_BASE.exists():
        print(f"  [WARN] Processed dir not found: {PROCESSED_BASE}")
        print(f"         Run segment_human_biology_papers.py first.")
        sys.exit(1)

    subject_id = get_subject_id()
    print(f"  Subject ID : {subject_id}")

    folders = sorted(f for f in PROCESSED_BASE.iterdir() if f.is_dir())
    print(f"  Folders    : {len(folders)}\n")

    stats = {
        "missing_papers": 0,
        "pages_created":  0,
        "uploaded":       0,
        "missing_qp":     0,
        "errors":         0,
    }

    for folder in folders:
        process_folder(folder, subject_id, args.dry_run, stats)
        if not args.dry_run:
            time.sleep(0.05)

    print(f"\n  Summary:")
    print(f"    Papers missing/created : {stats['missing_papers']}")
    print(f"    Page rows created      : {stats['pages_created']}")
    print(f"    Files uploaded         : {stats['uploaded']}")
    print(f"    QP files missing       : {stats['missing_qp']}")
    print(f"    Errors                 : {stats['errors']}")
    print("\n[DONE]  Ingestion complete.")


if __name__ == "__main__":
    main()
