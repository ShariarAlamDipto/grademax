"""
Upload Math B question pages to Supabase storage

This script:
1. For each paper, extracts pages for each question
2. Uploads to Supabase storage
3. Updates the database with URLs
"""

import os
import sys
import io
from pathlib import Path
from typing import Optional, Tuple
from dotenv import load_dotenv
from supabase import create_client

import fitz  # PyMuPDF

load_dotenv('.env.local')

SUPABASE_URL = os.getenv("NEXT_PUBLIC_SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    print("Missing Supabase credentials")
    sys.exit(1)

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

RAW_DIR = Path(__file__).parent.parent / "data" / "raw" / "IGCSE" / "Maths B"
STORAGE_BUCKET = "question-pdfs"
SUBJECT_NAME = "MathsB"


def extract_page_range(pdf_path: Path, start_page: int, end_page: int) -> Optional[bytes]:
    """Extract pages from PDF and return as bytes"""
    doc = fitz.open(str(pdf_path))
    
    # Validate page range
    if start_page >= len(doc) or start_page < 0:
        doc.close()
        return None
    
    end_page = min(end_page, len(doc) - 1)
    
    new_doc = fitz.open()
    
    for page_num in range(start_page, end_page + 1):
        new_doc.insert_pdf(doc, from_page=page_num, to_page=page_num)
    
    if len(new_doc) == 0:
        new_doc.close()
        doc.close()
        return None
    
    pdf_bytes = new_doc.tobytes()
    new_doc.close()
    doc.close()
    
    return pdf_bytes


def upload_to_storage(pdf_bytes: bytes, storage_path: str) -> Optional[str]:
    """Upload PDF bytes to Supabase storage and return public URL"""
    try:
        # Upload to storage
        result = supabase.storage.from_(STORAGE_BUCKET).upload(
            storage_path,
            pdf_bytes,
            {"content-type": "application/pdf", "upsert": "true"}
        )
        
        # Get public URL
        public_url = supabase.storage.from_(STORAGE_BUCKET).get_public_url(storage_path)
        return public_url
        
    except Exception as e:
        if "already exists" in str(e).lower() or "duplicate" in str(e).lower():
            # Already exists, just return the URL
            return supabase.storage.from_(STORAGE_BUCKET).get_public_url(storage_path)
        print(f"    Upload error: {e}")
        return None


def find_question_pages(pdf_path: Path) -> dict:
    """
    Find which pages contain which questions in a PDF
    Returns dict: question_number -> (start_page, end_page)
    """
    import re
    
    doc = fitz.open(str(pdf_path))
    questions = {}
    current_q = None
    current_start = None
    
    for page_num in range(len(doc)):
        page = doc[page_num]
        text = page.get_text()
        
        # Look for question numbers at start of lines
        for line in text.split('\n'):
            match = re.match(r'^\s*(\d{1,2})\s+(?:[A-Z(]|\()', line.strip())
            if match:
                q_num = int(match.group(1))
                if 1 <= q_num <= 30 and len(line.strip()) > 5:
                    # Save previous question
                    if current_q is not None:
                        questions[current_q] = (current_start, page_num - 1)
                    current_q = q_num
                    current_start = page_num
    
    # Save last question
    if current_q is not None:
        questions[current_q] = (current_start, len(doc) - 1)
    
    doc.close()
    return questions


def process_paper(paper_id: str, qp_path: Path, ms_path: Optional[Path], 
                  year: int, season: str, paper_num: str):
    """Process a single paper - extract questions and upload"""
    folder_name = f"{year}_{season}_P{paper_num}"
    storage_base = f"subjects/{SUBJECT_NAME}/pages/{folder_name}"
    
    # Get pages for this paper from database
    pages = supabase.table("pages")\
        .select("id, question_number")\
        .eq("paper_id", paper_id)\
        .execute().data
    
    if not pages:
        print(f"    No pages in database for this paper")
        return 0
    
    # Find question page ranges in QP
    qp_questions = find_question_pages(qp_path)
    
    # Find question page ranges in MS (if exists)
    ms_questions = {}
    if ms_path and ms_path.exists():
        ms_questions = find_question_pages(ms_path)
    
    updated = 0
    
    for page in pages:
        q_num = int(page["question_number"])
        page_id = page["id"]
        
        qp_url = None
        ms_url = None
        
        # Extract and upload QP
        if q_num in qp_questions:
            start, end = qp_questions[q_num]
            pdf_bytes = extract_page_range(qp_path, start, end)
            if pdf_bytes:
                storage_path = f"{storage_base}/q{q_num}.pdf"
                qp_url = upload_to_storage(pdf_bytes, storage_path)
        
        # Extract and upload MS
        if q_num in ms_questions and ms_path:
            start, end = ms_questions[q_num]
            pdf_bytes = extract_page_range(ms_path, start, end)
            if pdf_bytes:
                storage_path = f"{storage_base}/q{q_num}_ms.pdf"
                ms_url = upload_to_storage(pdf_bytes, storage_path)
        
        # Update database
        if qp_url:
            update_data = {"qp_page_url": qp_url}
            if ms_url:
                update_data["ms_page_url"] = ms_url
            
            supabase.table("pages")\
                .update(update_data)\
                .eq("id", page_id)\
                .execute()
            updated += 1
    
    return updated


def main():
    print("=" * 70)
    print("UPLOADING MATH B QUESTION PAGES TO STORAGE")
    print("=" * 70)
    
    # Get all Math B papers
    subject = supabase.table("subjects").select("id").eq("code", "4MB1").execute().data[0]
    papers = supabase.table("papers")\
        .select("id, year, season, paper_number")\
        .eq("subject_id", subject["id"])\
        .order("year")\
        .execute().data
    
    print(f"\nFound {len(papers)} papers to process")
    
    total_updated = 0
    
    for i, paper in enumerate(papers):
        year = paper["year"]
        season = paper["season"]
        paper_num = paper["paper_number"]
        paper_id = paper["id"]
        
        print(f"\n[{i+1}/{len(papers)}] {year} {season} Paper {paper_num}")
        
        # Find PDF files
        season_map = {"Jan": "Jan", "Jun": "May-Jun", "Nov": "Oct-Nov"}
        season_dir = RAW_DIR / str(year) / season_map.get(season, season)
        
        if not season_dir.exists():
            print(f"    Directory not found: {season_dir}")
            continue
        
        # Find QP
        qp_path = None
        for pattern in [f"Paper {paper_num}.pdf", f"Paper{paper_num}.pdf"]:
            potential = season_dir / pattern
            if potential.exists():
                qp_path = potential
                break
        
        if not qp_path:
            print(f"    QP not found")
            continue
        
        # Find MS
        ms_path = None
        for pattern in [f"Paper {paper_num}_MS.pdf", f"Paper{paper_num}_MS.pdf", 
                        f"Paper {paper_num} MS.pdf"]:
            potential = season_dir / pattern
            if potential.exists():
                ms_path = potential
                break
        
        # Process
        updated = process_paper(paper_id, qp_path, ms_path, year, season, paper_num)
        total_updated += updated
        print(f"    Updated {updated} pages")
    
    print("\n" + "=" * 70)
    print(f"COMPLETE: Updated {total_updated} pages with URLs")
    print("=" * 70)


if __name__ == "__main__":
    main()
