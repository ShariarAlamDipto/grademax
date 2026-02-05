#!/usr/bin/env python3
"""
Process and classify all Mathematics B papers from local processed folder
- Reads PDFs from local processed folder
- Extracts text and creates pages in database
- Classifies pages with LLM topic tagger

Usage:
    python scripts/process_and_classify_all_maths_b.py
"""

import os
import sys
import json
import time
from pathlib import Path
from dotenv import load_dotenv
from supabase import create_client, Client
import PyPDF2
from io import BytesIO

# Add parent directory to path
sys.path.append(str(Path(__file__).parent))
from mistral_classifier import MistralTopicClassifier

# Load environment
env_path = Path(__file__).parent.parent / '.env.local'
if not env_path.exists():
    # Try .env.ingest
    env_path = Path(__file__).parent.parent / '.env.ingest'
if not env_path.exists():
    print("[ERROR] .env.local or .env.ingest not found!")
    sys.exit(1)
load_dotenv(env_path)

SUPABASE_URL = os.getenv("NEXT_PUBLIC_SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    print("[ERROR] Missing Supabase credentials")
    sys.exit(1)

if not GROQ_API_KEY:
    print("[ERROR] Missing GROQ_API_KEY")
    sys.exit(1)

# Initialize Supabase
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# Paths
PROCESSED_DIR = Path(__file__).parent.parent / "data" / "processed" / "Maths B"
TOPICS_YAML = Path(__file__).parent.parent / "classification" / "maths_b_topics.yaml"
SUBJECT_CODE = "4MB1"


def extract_text_from_pdf(pdf_path: Path) -> str:
    """Extract text from a PDF file"""
    try:
        with open(pdf_path, 'rb') as f:
            pdf_reader = PyPDF2.PdfReader(f)
            text = ""
            for page in pdf_reader.pages:
                text += page.extract_text() or ""
            return text.strip()
    except Exception as e:
        print(f"        [ERROR] Error extracting text: {str(e)[:50]}")
        return ""


def get_maths_b_subject_id():
    """Get the subject ID for Mathematics B"""
    response = supabase.table("subjects").select("id, name, code").eq("code", SUBJECT_CODE).execute()
    if response.data and len(response.data) > 0:
        return response.data[0]["id"], response.data[0]["name"]
    else:
        raise ValueError(f"Subject {SUBJECT_CODE} (Mathematics B) not found in database. Run: python scripts/add_subject.py maths_b")


def parse_paper_folder(folder_name: str):
    """Parse folder name like '2019_Jun_1' into components"""
    parts = folder_name.split('_')
    if len(parts) >= 3:
        year = int(parts[0])
        season = parts[1]  # Jun, Jan, Nov
        paper_number = parts[2]  # 1, 2
        return year, season, paper_number
    return None


def create_or_get_paper(subject_id: str, year: int, season: str, paper_number: str, total_pages: int):
    """Create or get existing paper"""
    # Check if paper exists
    existing = supabase.table("papers")\
        .select("id")\
        .eq("subject_id", subject_id)\
        .eq("year", year)\
        .eq("season", season)\
        .eq("paper_number", paper_number)\
        .execute()
    
    if existing.data:
        return existing.data[0]["id"], False
    
    # Create new paper
    paper_data = {
        "subject_id": subject_id,
        "year": year,
        "season": season,
        "paper_number": paper_number,
        "total_pages": total_pages
    }
    
    response = supabase.table("papers").insert(paper_data).execute()
    return response.data[0]["id"], True


def process_paper_pages(paper_id: str, pages_dir: Path, manifest_path: Path):
    """Extract text from PDFs and create pages in database"""
    
    # Check if pages already exist for this paper
    existing_pages = supabase.table("pages").select("id").eq("paper_id", paper_id).execute()
    if existing_pages.data and len(existing_pages.data) > 0:
        return len(existing_pages.data), 0  # Already processed
    
    # Load manifest to get question list
    with open(manifest_path, 'r', encoding='utf-8') as f:
        manifest = json.load(f)
    
    questions = manifest.get("questions", [])
    pages_created = 0
    
    for question in questions:
        q_num = question.get("question_number")
        q_file = pages_dir / f"q{q_num}.pdf"
        
        if not q_file.exists():
            continue
        
        # Extract text from PDF
        full_text = extract_text_from_pdf(q_file)
        if not full_text:
            continue
        
        # Create page in database
        page_data = {
            "paper_id": paper_id,
            "page_number": int(q_num),
            "question_number": str(q_num),
            "is_question": True,
            "topics": [],  # Will be filled by classification
            "text_excerpt": full_text[:500],  # First 500 chars
            "has_diagram": False,
            "page_count": 1
        }
        
        try:
            supabase.table("pages").insert(page_data).execute()
            pages_created += 1
        except Exception as e:
            print(f"        [ERROR] Error creating page Q{q_num}: {str(e)[:50]}")
            continue
    
    return pages_created, pages_created


def classify_paper(paper_id: str, pages_dir: Path, classifier: MistralTopicClassifier):
    """Classify all pages for a paper using full PDF text"""
    
    # Get all pages for this paper
    pages = supabase.table("pages")\
        .select("id, page_number, question_number")\
        .eq("paper_id", paper_id)\
        .order("page_number")\
        .execute()
    
    if not pages.data:
        return 0, 0
    
    classified_count = 0
    failed_count = 0
    
    for page in pages.data:
        page_id = page["id"]
        q_num = page["question_number"]
        q_file = pages_dir / f"q{q_num}.pdf"
        
        if not q_file.exists():
            failed_count += 1
            continue
        
        # Extract full text for classification
        full_text = extract_text_from_pdf(q_file)
        
        if not full_text or len(full_text.strip()) < 50:
            failed_count += 1
            continue
        
        # Retry with exponential backoff
        max_retries = 3
        for attempt in range(max_retries):
            try:
                # Classify using full text
                result = classifier.classify(full_text, f"Q{q_num}")
                
                if result.page_has_question:
                    # Update page with classification
                    supabase.table("pages")\
                        .update({
                            "topics": [result.topic],
                            "difficulty": result.difficulty,
                            "confidence": result.confidence
                        })\
                        .eq("id", page_id)\
                        .execute()
                    
                    classified_count += 1
                    print(f"        [OK] Q{q_num}: Topic {result.topic} | {result.difficulty} | {result.confidence:.2f}")
                else:
                    failed_count += 1
                break  # Success, exit retry loop
                    
            except Exception as e:
                if "429" in str(e) or "rate" in str(e).lower():
                    wait_time = 10 * (2 ** attempt)  # 10, 20, 40 seconds
                    print(f"        [WAIT] Rate limited, waiting {wait_time}s (attempt {attempt+1}/{max_retries})...")
                    time.sleep(wait_time)
                else:
                    print(f"        [ERROR] Q{q_num}: {str(e)[:60]}")
                    failed_count += 1
                    break  # Non-rate-limit error, don't retry
        
        # Rate limiting - 2.5 seconds between requests for Groq with model rotation
        time.sleep(2.5)
    
    return classified_count, failed_count


def main():
    print("\n" + "=" * 80)
    print("PROCESS AND CLASSIFY ALL MATHEMATICS B PAPERS")
    print("=" * 80)
    
    # Get subject
    try:
        subject_id, subject_name = get_maths_b_subject_id()
        print(f"\n[OK] Subject: {subject_name} (ID: {subject_id[:8]}...)")
    except ValueError as e:
        print(f"\n[ERROR] Error: {e}")
        return
    
    # Check processed directory
    if not PROCESSED_DIR.exists():
        print(f"\n[ERROR] Processed directory not found: {PROCESSED_DIR}")
        print(f"   Please create: data/processed/Maths B/")
        print(f"   With structure: YYYY_Season_PaperNum/pages/q1.pdf, q2.pdf, etc.")
        return
    
    # Get all paper folders
    paper_folders = sorted([d for d in PROCESSED_DIR.iterdir() if d.is_dir()])
    print(f"\n[INFO] Found {len(paper_folders)} paper folders in {PROCESSED_DIR.name}")
    
    if len(paper_folders) == 0:
        print("\n   [WARN] No paper folders found!")
        print("   Expected structure: data/processed/Maths B/2019_Jun_1/pages/q1.pdf")
        return
    
    # Check topics YAML
    if not TOPICS_YAML.exists():
        print(f"\n[ERROR] Topics YAML not found: {TOPICS_YAML}")
        return
    
    # Initialize classifier
    print("\n[INIT] Initializing Classifier")
    print("=" * 80)
    classifier = MistralTopicClassifier(
        topics_yaml_path=str(TOPICS_YAML),
        groq_api_key=GROQ_API_KEY,
        model_name="llama-3.1-8b-instant"
    )
    print(f"   [OK] Loaded {len(classifier.topics)} Mathematics B topics")
    print(f"   [OK] Subject: {classifier.subject_name}")
    
    # Process each paper
    print("\n[PROCESS] Processing Papers")
    print("=" * 80)
    
    stats = {
        "papers_new": 0,
        "papers_existing": 0,
        "pages_created": 0,
        "pages_classified": 0,
        "pages_failed": 0
    }
    
    for i, folder in enumerate(paper_folders, 1):
        parsed = parse_paper_folder(folder.name)
        if not parsed:
            print(f"\n   [{i}/{len(paper_folders)}] [WARN] Skipping invalid folder: {folder.name}")
            continue
        
        year, season, paper_number = parsed
        print(f"\n   [{i}/{len(paper_folders)}] {year} {season} Paper {paper_number}")
        
        # Check for required files
        manifest_path = folder / "manifest.json"
        pages_dir = folder / "pages"
        
        if not manifest_path.exists():
            print(f"      [WARN] No manifest.json")
            continue
        
        if not pages_dir.exists():
            print(f"      [WARN] No pages directory")
            continue
        
        # Load manifest to get page count
        with open(manifest_path, 'r', encoding='utf-8') as f:
            manifest = json.load(f)
        total_pages = len(manifest.get("questions", []))
        
        try:
            # Create or get paper
            paper_id, is_new = create_or_get_paper(subject_id, year, season, paper_number, total_pages)
            if is_new:
                print(f"      [OK] Created paper (ID: {paper_id[:8]}...)")
                stats["papers_new"] += 1
            else:
                print(f"      [INFO] Paper exists (ID: {paper_id[:8]}...)")
                stats["papers_existing"] += 1
            
            # Process pages (extract text and create in DB)
            total, created = process_paper_pages(paper_id, pages_dir, manifest_path)
            if created > 0:
                print(f"      [OK] Created {created} pages in database")
                stats["pages_created"] += created
            elif total > 0:
                print(f"      [INFO] {total} pages already exist")
            
            # Classify pages
            classified, failed = classify_paper(paper_id, pages_dir, classifier)
            stats["pages_classified"] += classified
            stats["pages_failed"] += failed
            
        except Exception as e:
            print(f"      [ERROR] Error: {str(e)[:100]}")
            continue
    
    # Final summary
    print("\n" + "=" * 80)
    print("FINAL SUMMARY")
    print("=" * 80)
    print(f"   Papers processed: {len(paper_folders)}")
    print(f"   Papers created: {stats['papers_new']}")
    print(f"   Papers already existed: {stats['papers_existing']}")
    print(f"   Pages created: {stats['pages_created']}")
    print(f"   Pages classified: {stats['pages_classified']}")
    print(f"   Pages failed: {stats['pages_failed']}")
    
    if stats['pages_classified'] + stats['pages_failed'] > 0:
        success_rate = (stats['pages_classified'] / (stats['pages_classified'] + stats['pages_failed'])) * 100
        print(f"   Classification success rate: {success_rate:.1f}%")
    print()


if __name__ == "__main__":
    main()
