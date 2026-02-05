"""
Upload already-processed Maths B pages to Supabase storage
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv
from supabase import create_client

load_dotenv('.env.local')

SUPABASE_URL = os.getenv("NEXT_PUBLIC_SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    print("Missing Supabase credentials")
    sys.exit(1)

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

PROCESSED_DIR = Path(__file__).parent.parent / "data" / "processed" / "Maths B"
STORAGE_BUCKET = "question-pdfs"
SUBJECT_NAME = "MathsB"


def upload_file(file_path: Path, storage_path: str) -> str:
    """Upload a file to storage and return the public URL"""
    with open(file_path, 'rb') as f:
        pdf_bytes = f.read()
    
    try:
        supabase.storage.from_(STORAGE_BUCKET).upload(
            storage_path,
            pdf_bytes,
            {"content-type": "application/pdf", "upsert": "true"}
        )
    except Exception as e:
        if "already exists" not in str(e).lower() and "duplicate" not in str(e).lower():
            print(f"    Upload error: {e}")
            return None
    
    return supabase.storage.from_(STORAGE_BUCKET).get_public_url(storage_path)


def main():
    print("=" * 70)
    print("UPLOADING MATHS B PROCESSED PAGES TO STORAGE")
    print("=" * 70)
    
    # Get Maths B subject ID
    subject = supabase.table("subjects").select("id").eq("code", "4MB1").execute().data
    if not subject:
        print("Maths B subject not found!")
        return
    subject_id = subject[0]["id"]
    print(f"Subject ID: {subject_id}")
    
    # Get all Maths B papers
    papers = supabase.table("papers")\
        .select("id, year, season, paper_number")\
        .eq("subject_id", subject_id)\
        .order("year")\
        .execute().data
    
    print(f"Found {len(papers)} papers")
    
    total_uploaded = 0
    total_updated = 0
    
    for paper in papers:
        year = paper["year"]
        season = paper["season"]
        paper_num = paper["paper_number"]
        paper_id = paper["id"]
        
        # Build folder name: e.g., "2024_Jun_1"
        folder_name = f"{year}_{season}_{paper_num}"
        paper_dir = PROCESSED_DIR / folder_name / "pages"
        
        if not paper_dir.exists():
            # Try alternate formats
            for alt in [f"{year}_{season}_Paper{paper_num}", f"{year}_{season}_{paper_num}P"]:
                alt_dir = PROCESSED_DIR / alt / "pages"
                if alt_dir.exists():
                    paper_dir = alt_dir
                    break
        
        if not paper_dir.exists():
            print(f"  {folder_name}: Directory not found")
            continue
        
        # Get pages for this paper from database
        pages = supabase.table("pages")\
            .select("id, question_number, qp_page_url")\
            .eq("paper_id", paper_id)\
            .execute().data
        
        if not pages:
            print(f"  {folder_name}: No pages in database")
            continue
        
        uploaded_count = 0
        updated_count = 0
        
        for page in pages:
            q_num = page["question_number"]
            page_id = page["id"]
            
            # Check if already has URL
            if page.get("qp_page_url"):
                continue
            
            # Find the PDF file
            pdf_file = paper_dir / f"q{q_num}.pdf"
            if not pdf_file.exists():
                # Try alternate naming
                pdf_file = paper_dir / f"Q{q_num}.pdf"
                if not pdf_file.exists():
                    continue
            
            # Upload to storage
            storage_path = f"subjects/{SUBJECT_NAME}/pages/{folder_name}/q{q_num}.pdf"
            url = upload_file(pdf_file, storage_path)
            
            if url:
                uploaded_count += 1
                
                # Update database
                supabase.table("pages")\
                    .update({"qp_page_url": url})\
                    .eq("id", page_id)\
                    .execute()
                updated_count += 1
        
        if uploaded_count > 0:
            print(f"  {folder_name}: Uploaded {uploaded_count}, Updated {updated_count}")
            total_uploaded += uploaded_count
            total_updated += updated_count
    
    print("\n" + "=" * 70)
    print(f"COMPLETE: Uploaded {total_uploaded} files, Updated {total_updated} database records")
    print("=" * 70)


if __name__ == "__main__":
    main()
