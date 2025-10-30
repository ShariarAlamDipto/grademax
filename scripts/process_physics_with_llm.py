"""
Complete Physics Processing Pipeline using LLM-based Question Detection

This script:
1. Analyzes QP and MS using LLM to detect questions
2. Extracts question PDFs (q1.pdf, q2.pdf, etc.)
3. Extracts mark scheme PDFs (q1_ms.pdf, q2_ms.pdf, etc.)
4. Uploads to Supabase storage
5. Creates database records
6. Classifies using dual API
"""

import os
import sys
import json
import time
from pathlib import Path
import PyPDF2
from datetime import datetime
from supabase import create_client, Client
from dotenv import load_dotenv

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

from scripts.analyze_physics_llm import analyze_paper_with_llm

# Load environment
env_path = Path(__file__).parent.parent / '.env.local'
if not env_path.exists():
    print("❌ .env.local not found!")
    sys.exit(1)
load_dotenv(env_path)

SUPABASE_URL = os.getenv("NEXT_PUBLIC_SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    print("❌ Missing Supabase credentials in .env.local")
    sys.exit(1)

# Initialize Supabase
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# Constants
BUCKET_NAME = "question-pdfs"
SUBJECT = "Physics"
SUBJECT_ID = "0b142517-d35d-4942-91aa-b4886aaabca3"
RAW_DATA_DIR = Path("data/raw/IGCSE/Physics")
PROCESSED_DIR = Path("data/processed/Physics")

# Initialize classifier once (will be used by all classify_question calls)
TOPICS_YAML = Path(__file__).parent.parent / "classification" / "physics_topics.yaml"
CLASSIFIER = None

def get_classifier():
    """Get or create the classifier instance"""
    global CLASSIFIER
    if CLASSIFIER is None:
        from scripts.mistral_classifier import MistralTopicClassifier
        CLASSIFIER = MistralTopicClassifier(str(TOPICS_YAML))
    return CLASSIFIER

def extract_pdf_pages(input_pdf_path: str, output_pdf_path: str, page_indices: list[int]):
    """
    Extract specific pages from a PDF and save to a new PDF.
    
    Args:
        input_pdf_path: Path to source PDF
        output_pdf_path: Path to save extracted pages
        page_indices: List of page indices (0-based) to extract
    """
    reader = PyPDF2.PdfReader(input_pdf_path)
    writer = PyPDF2.PdfWriter()
    
    for page_idx in sorted(page_indices):
        if 0 <= page_idx < len(reader.pages):
            writer.add_page(reader.pages[page_idx])
    
    os.makedirs(os.path.dirname(output_pdf_path), exist_ok=True)
    with open(output_pdf_path, 'wb') as output_file:
        writer.write(output_file)

def upload_to_storage(local_path: str, storage_path: str) -> str:
    """
    Upload a file to Supabase storage.
    
    Returns:
        Public URL of uploaded file
    """
    with open(local_path, 'rb') as f:
        file_data = f.read()
    
    # Upload to storage
    supabase.storage.from_(BUCKET_NAME).upload(
        storage_path,
        file_data,
        file_options={"content-type": "application/pdf"}
    )
    
    # Get public URL
    url_response = supabase.storage.from_(BUCKET_NAME).get_public_url(storage_path)
    return url_response

def get_or_create_paper_id(year: int, season: str, paper_number: int, total_pages: int) -> str:
    """
    Get existing paper_id or create new paper record.
    
    Returns:
        paper_id (UUID string)
    """
    # Check if paper exists
    response = supabase.table("papers").select("id").eq("subject_id", SUBJECT_ID).eq("year", year).eq("season", season).eq("paper_number", paper_number).execute()
    
    if response.data and len(response.data) > 0:
        return response.data[0]["id"]
    
    # Create new paper
    paper_data = {
        "subject_id": SUBJECT_ID,
        "year": year,
        "season": season,
        "paper_number": paper_number,
        "total_pages": total_pages
    }
    
    insert_response = supabase.table("papers").insert(paper_data).execute()
    return insert_response.data[0]["id"]

def create_page_record(paper_id: str, question_number: int, qp_url: str, ms_url: str, text_excerpt: str):
    """
    Create a page record in the database.
    """
    page_data = {
        "paper_id": paper_id,
        "page_number": question_number,  # Using question number as page number
        "question_number": question_number,
        "topics": [],  # Will be filled by classifier
        "qp_page_url": qp_url,
        "ms_page_url": ms_url,
        "text_excerpt": text_excerpt[:500] if text_excerpt else ""
    }
    
    supabase.table("pages").insert(page_data).execute()

def classify_question(text_excerpt: str, qp_url: str) -> dict:
    """
    Classify a question using the dual API classifier.
    
    Returns:
        Classification result with topic and confidence
    """
    classifier = get_classifier()
    
    # Classify
    result = classifier.classify_topics(
        page_text=text_excerpt,
        page_url=qp_url
    )
    
    return result

def process_paper(year: int, season: str, paper_number: int, qp_path: str, ms_path: str):
    """
    Process a single paper: analyze with LLM, extract PDFs, upload, create records, classify.
    """
    print(f"\n{'='*80}")
    print(f"Processing: {year} {season} Paper {paper_number}")
    print(f"{'='*80}")
    
    # Step 1: Analyze with LLM
    print("\n[1/6] Analyzing with LLM...")
    analysis = analyze_paper_with_llm(qp_path, ms_path, year, season, paper_number)
    
    if not analysis or "questions" not in analysis:
        print("❌ LLM analysis failed")
        return
    
    questions = analysis["questions"]
    print(f"✅ Found {len(questions)} questions")
    
    # Step 2: Create paper record
    print("\n[2/6] Creating paper record...")
    total_pages = len(questions)  # Each question = one "page" in our system
    paper_id = get_or_create_paper_id(year, season, paper_number, total_pages)
    print(f"✅ Paper ID: {paper_id}")
    
    # Step 3: Extract and upload question PDFs
    print("\n[3/6] Extracting question PDFs...")
    storage_prefix = f"subjects/{SUBJECT}/pages/Phy_{year}_{season}_{paper_number}"
    local_dir = PROCESSED_DIR / f"{year}_{season}_Paper{paper_number}"
    
    question_data = []  # Store for classification step
    
    for q in questions:
        qnum = q["qnum"]
        qp_pages = q["qp_pages"]
        ms_pages = q["ms_pages"]
        
        print(f"\n  Question {qnum}:")
        print(f"    QP pages: {qp_pages}")
        print(f"    MS pages: {ms_pages}")
        
        # Extract QP
        qp_local = local_dir / f"q{qnum}.pdf"
        extract_pdf_pages(qp_path, str(qp_local), qp_pages)
        print(f"    ✅ Extracted QP: {qp_local}")
        
        # Extract MS
        ms_local = local_dir / f"q{qnum}_ms.pdf"
        extract_pdf_pages(ms_path, str(ms_local), ms_pages)
        print(f"    ✅ Extracted MS: {ms_local}")
        
        # Upload QP
        qp_storage_path = f"{storage_prefix}/q{qnum}.pdf"
        qp_url = upload_to_storage(str(qp_local), qp_storage_path)
        print(f"    ✅ Uploaded QP: {qp_url}")
        
        # Upload MS
        ms_storage_path = f"{storage_prefix}/q{qnum}_ms.pdf"
        ms_url = upload_to_storage(str(ms_local), ms_storage_path)
        print(f"    ✅ Uploaded MS: {ms_url}")
        
        # Extract text for classification
        try:
            reader = PyPDF2.PdfReader(str(qp_local))
            text_excerpt = ""
            for page in reader.pages[:2]:  # First 2 pages for classification
                text_excerpt += page.extract_text() + "\n"
        except:
            text_excerpt = f"Question {qnum}"
        
        question_data.append({
            "qnum": qnum,
            "qp_url": qp_url,
            "ms_url": ms_url,
            "text_excerpt": text_excerpt
        })
    
    # Step 4: Create page records
    print("\n[4/6] Creating page records...")
    for qdata in question_data:
        create_page_record(
            paper_id=paper_id,
            question_number=int(qdata["qnum"]),
            qp_url=qdata["qp_url"],
            ms_url=qdata["ms_url"],
            text_excerpt=qdata["text_excerpt"]
        )
    print(f"✅ Created {len(question_data)} page records")
    
    # Step 5: Classify questions
    print("\n[5/6] Classifying questions...")
    for qdata in question_data:
        try:
            classification = classify_question(qdata["text_excerpt"], qdata["qp_url"])
            print(f"  Q{qdata['qnum']}: {classification.get('topic', 'Unknown')} (confidence: {classification.get('confidence', 0):.2f})")
            
            # Update page record with topics
            if classification.get("topic"):
                supabase.table("pages").update(
                    {"topics": [classification["topic"]]}
                ).eq("paper_id", paper_id).eq("question_number", int(qdata["qnum"])).execute()
            
            time.sleep(5)  # Rate limiting
        except Exception as e:
            print(f"  ❌ Q{qdata['qnum']}: Classification failed - {e}")
    
    print(f"\n[6/6] ✅ Paper complete: {year} {season} Paper {paper_number}")

def get_all_papers() -> list[dict]:
    """
    Scan raw data directory for all Physics papers.
    
    Returns:
        List of dicts with year, season, paper_number, qp_path, ms_path
    """
    papers = []
    
    if not RAW_DATA_DIR.exists():
        print(f"❌ Raw data directory not found: {RAW_DATA_DIR}")
        return papers
    
    for year_dir in sorted(RAW_DATA_DIR.iterdir()):
        if not year_dir.is_dir():
            continue
        
        year = int(year_dir.name)
        
        for season_dir in sorted(year_dir.iterdir()):
            if not season_dir.is_dir():
                continue
            
            season = season_dir.name
            
            # Find all Paper N.pdf and Paper N_MS.pdf pairs
            qp_files = list(season_dir.glob("Paper *.pdf"))
            qp_files = [f for f in qp_files if not f.name.endswith("_MS.pdf")]
            
            for qp_file in qp_files:
                # Extract paper number
                paper_number = int(qp_file.stem.replace("Paper ", ""))
                
                # Find corresponding MS
                ms_file = season_dir / f"Paper {paper_number}_MS.pdf"
                
                if ms_file.exists():
                    papers.append({
                        "year": year,
                        "season": season,
                        "paper_number": paper_number,
                        "qp_path": str(qp_file),
                        "ms_path": str(ms_file)
                    })
                else:
                    print(f"⚠️  Missing MS for {year} {season} Paper {paper_number}")
    
    return papers

def main():
    """
    Main processing function.
    """
    print("="*80)
    print("PHYSICS COMPLETE PROCESSING PIPELINE")
    print("="*80)
    print(f"Subject: {SUBJECT} ({SUBJECT_ID})")
    print(f"Raw data: {RAW_DATA_DIR}")
    print(f"Processed: {PROCESSED_DIR}")
    print(f"Storage: {BUCKET_NAME}/subjects/{SUBJECT}/pages/")
    
    # Get all papers
    print("\nScanning for papers...")
    papers = get_all_papers()
    print(f"✅ Found {len(papers)} papers to process")
    
    # Process each paper
    success_count = 0
    fail_count = 0
    
    for i, paper in enumerate(papers, 1):
        print(f"\n\n{'#'*80}")
        print(f"# Paper {i}/{len(papers)}")
        print(f"{'#'*80}")
        
        try:
            process_paper(
                year=paper["year"],
                season=paper["season"],
                paper_number=paper["paper_number"],
                qp_path=paper["qp_path"],
                ms_path=paper["ms_path"]
            )
            success_count += 1
        except Exception as e:
            print(f"\n❌ FAILED: {paper['year']} {paper['season']} Paper {paper['paper_number']}")
            print(f"   Error: {e}")
            fail_count += 1
            # Continue to next paper
    
    # Final summary
    print("\n\n" + "="*80)
    print("PROCESSING COMPLETE")
    print("="*80)
    print(f"✅ Successful: {success_count}/{len(papers)}")
    print(f"❌ Failed: {fail_count}/{len(papers)}")
    
    # Query database stats
    papers_response = supabase.table("papers").select("*", count="exact").eq("subject_id", SUBJECT_ID).execute()
    pages_response = supabase.table("pages").select("*", count="exact").execute()
    
    print(f"\n📊 Database Stats:")
    print(f"   Papers: {papers_response.count}")
    print(f"   Pages: {pages_response.count}")

if __name__ == "__main__":
    main()
