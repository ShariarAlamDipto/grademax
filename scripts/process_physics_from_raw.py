import os
import sys
import time
from pathlib import Path
from supabase import create_client
from dotenv import load_dotenv
from PyPDF2 import PdfReader, PdfWriter
from io import BytesIO
import pdfplumber

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from scripts.mistral_classifier import MistralTopicClassifier

# Load environment variables from .env.local
env_path = project_root / '.env.local'
load_dotenv(env_path)

# Initialize Supabase client
supabase_url = os.getenv("NEXT_PUBLIC_SUPABASE_URL")
supabase_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
supabase = create_client(supabase_url, supabase_key)

# Physics subject ID
PHYSICS_SUBJECT_ID = "0b142517-d35d-4942-91aa-b4886aaabca3"
RAW_DATA_PATH = Path("data/raw/IGCSE/Physics")

def extract_text_from_pdf(pdf_path, page_num):
    """Extract text from a specific page of a PDF."""
    try:
        with pdfplumber.open(pdf_path) as pdf:
            if page_num < len(pdf.pages):
                page = pdf.pages[page_num]
                text = page.extract_text()
                return text if text else ""
    except Exception as e:
        print(f"Error extracting text from {pdf_path} page {page_num}: {e}")
    return ""

def extract_page_as_pdf(input_pdf_path, page_num):
    """Extract a single page from PDF and return as bytes."""
    try:
        reader = PdfReader(input_pdf_path)
        if page_num >= len(reader.pages):
            return None
        
        writer = PdfWriter()
        writer.add_page(reader.pages[page_num])
        
        output = BytesIO()
        writer.write(output)
        output.seek(0)
        return output.getvalue()
    except Exception as e:
        print(f"Error extracting page {page_num} from {input_pdf_path}: {e}")
        return None

def parse_paper_name(paper_filename):
    """Parse 'Paper 1.pdf' to get paper number."""
    # Expected format: "Paper 1.pdf" or "Paper 2.pdf"
    name = paper_filename.replace(".pdf", "")
    parts = name.split()
    if len(parts) == 2 and parts[0].lower() == "paper":
        return f"{parts[1]}P"  # "1P" or "2P"
    return None

def create_or_get_paper(year, season, paper_number):
    """Create or retrieve a paper record."""
    try:
        # Check if paper exists
        result = supabase.table("papers").select("id, total_pages").eq("subject_id", PHYSICS_SUBJECT_ID).eq("year", year).eq("season", season).eq("paper_number", paper_number).execute()
        
        if result.data and len(result.data) > 0:
            print(f"Paper already exists: Phy_{year}_{season}_{paper_number}")
            return result.data[0]['id'], result.data[0]['total_pages']
        
        # Create new paper
        paper_data = {
            "subject_id": PHYSICS_SUBJECT_ID,
            "year": year,
            "season": season,
            "paper_number": paper_number,
            "total_pages": 0  # Will update later
        }
        
        result = supabase.table("papers").insert(paper_data).execute()
        paper_id = result.data[0]['id']
        print(f"[CREATED] Paper: Phy_{year}_{season}_{paper_number} (ID: {paper_id})")
        return paper_id, 0
        
    except Exception as e:
        print(f"Error creating/getting paper Phy_{year}_{season}_{paper_number}: {e}")
        raise

def process_paper_pages(paper_id, qp_path, ms_path, year, season, paper_number):
    """Process question paper and mark scheme, extract pages, upload to storage."""
    try:
        # Read PDFs
        qp_reader = PdfReader(qp_path)
        ms_reader = PdfReader(ms_path) if ms_path and ms_path.exists() else None
        
        qp_page_count = len(qp_reader.pages)
        ms_page_count = len(ms_reader.pages) if ms_reader else 0
        
        print(f"[INFO] QP: {qp_page_count} pages, MS: {ms_page_count} pages")
        
        # Create storage folder path with Phy_ prefix
        storage_folder = f"subjects/Physics/pages/Phy_{year}_{season}_{paper_number}"
        
        # Process question paper pages
        pages_created = 0
        for page_num in range(qp_page_count):
            try:
                # Extract page as PDF
                page_pdf_bytes = extract_page_as_pdf(qp_path, page_num)
                if not page_pdf_bytes:
                    continue
                
                # Extract text excerpt
                text_excerpt = extract_text_from_pdf(qp_path, page_num)
                text_excerpt = text_excerpt[:500] if text_excerpt else ""
                
                # Upload question page to storage
                qp_storage_path = f"{storage_folder}/q{page_num + 1}.pdf"
                supabase.storage.from_("question-pdfs").upload(
                    qp_storage_path,
                    page_pdf_bytes,
                    {"content-type": "application/pdf", "upsert": "true"}
                )
                
                qp_page_url = supabase.storage.from_("question-pdfs").get_public_url(qp_storage_path)
                
                # Upload corresponding mark scheme page if available
                ms_page_url = None
                if ms_reader and page_num < ms_page_count:
                    ms_page_pdf_bytes = extract_page_as_pdf(ms_path, page_num)
                    if ms_page_pdf_bytes:
                        ms_storage_path = f"{storage_folder}/q{page_num + 1}_ms.pdf"
                        supabase.storage.from_("question-pdfs").upload(
                            ms_storage_path,
                            ms_page_pdf_bytes,
                            {"content-type": "application/pdf", "upsert": "true"}
                        )
                        ms_page_url = supabase.storage.from_("question-pdfs").get_public_url(ms_storage_path)
                
                # Create page record in database
                page_data = {
                    "paper_id": paper_id,
                    "page_number": page_num + 1,
                    "question_number": page_num + 1,  # Assuming 1 question per page initially
                    "qp_page_url": qp_page_url,
                    "ms_page_url": ms_page_url,
                    "text_excerpt": text_excerpt,
                    "topics": []  # Will be filled by classifier
                }
                
                supabase.table("pages").insert(page_data).execute()
                pages_created += 1
                
                if (page_num + 1) % 5 == 0:
                    print(f"[PROGRESS] Processed {page_num + 1}/{qp_page_count} pages")
                    
            except Exception as e:
                print(f"Error processing page {page_num + 1}: {e}")
                continue
        
        # Update paper total_pages
        supabase.table("papers").update({"total_pages": pages_created}).eq("id", paper_id).execute()
        
        print(f"[SUCCESS] Created {pages_created} pages for Phy_{year}_{season}_{paper_number}")
        return pages_created
        
    except Exception as e:
        print(f"Error processing paper pages: {e}")
        raise

def classify_paper(paper_id, classifier):
    """Classify all pages in a paper."""
    try:
        # Get all pages for this paper
        result = supabase.table("pages").select("id, text_excerpt").eq("paper_id", paper_id).execute()
        
        pages = result.data
        if not pages:
            print(f"No pages found for paper {paper_id}")
            return
        
        print(f"[CLASSIFY] Classifying {len(pages)} pages...")
        
        classified_count = 0
        for i, page in enumerate(pages, 1):
            try:
                text = page['text_excerpt'] or ""
                result = classifier.classify(text)
                
                # Extract topic list from TopicClassification object
                if hasattr(result, 'topic'):
                    topics = [result.topic] if result.topic else []
                else:
                    topics = result if isinstance(result, list) else []
                
                if topics:
                    supabase.table("pages").update({"topics": topics}).eq("id", page['id']).execute()
                    classified_count += 1
                    print(f"[{i}/{len(pages)}] Page classified: {topics}")
                else:
                    print(f"[{i}/{len(pages)}] No topics found")
                
                # Rate limiting - increased delay for stability
                time.sleep(5)
                
            except Exception as e:
                print(f"Error classifying page {page['id']}: {e}")
                continue
        
        print(f"[COMPLETE] Classified {classified_count}/{len(pages)} pages")
        
    except Exception as e:
        print(f"Error classifying paper: {e}")
        raise

def process_all_physics_papers():
    """Process all Physics papers from raw data."""
    print("=== Physics Paper Processing Pipeline ===\n")
    
    # Initialize classifier with both API keys
    print("[INIT] Loading Physics topics classifier...")
    groq_key = os.getenv('GROQ_API_KEY')
    openrouter_key = os.getenv('OPENROUTER_API_KEY')
    
    if not groq_key and not openrouter_key:
        print("ERROR: At least one API key (GROQ_API_KEY or OPENROUTER_API_KEY) is required!")
        return
    
    print(f"[INIT] Groq API: {'Available' if groq_key else 'Not available'}")
    print(f"[INIT] OpenRouter API: {'Available' if openrouter_key else 'Not available'}")
    
    classifier = MistralTopicClassifier(
        "classification/physics_topics.yaml",
        groq_key,
        openrouter_key
    )
    print(f"[INIT] Classifier ready with {len(classifier.topics)} topics")
    print(f"[INIT] Available models: {len(classifier.available_models)}\n")
    
    # Scan raw data directory
    total_papers = 0
    total_pages = 0
    
    for year_dir in sorted(RAW_DATA_PATH.iterdir()):
        if not year_dir.is_dir():
            continue
        
        year = year_dir.name
        print(f"\n{'='*60}")
        print(f"[YEAR] Processing {year}")
        print('='*60)
        
        for season_dir in sorted(year_dir.iterdir()):
            if not season_dir.is_dir():
                continue
            
            season = season_dir.name
            print(f"\n[SEASON] {year}/{season}")
            
            # Find all paper files
            paper_files = {}
            for file in season_dir.iterdir():
                if file.suffix.lower() == '.pdf':
                    if '_MS' in file.name:
                        # Mark scheme
                        paper_num = parse_paper_name(file.name.replace('_MS', ''))
                        if paper_num:
                            if paper_num not in paper_files:
                                paper_files[paper_num] = {"qp": None, "ms": None}
                            paper_files[paper_num]["ms"] = file
                    else:
                        # Question paper
                        paper_num = parse_paper_name(file.name)
                        if paper_num:
                            if paper_num not in paper_files:
                                paper_files[paper_num] = {"qp": None, "ms": None}
                            paper_files[paper_num]["qp"] = file
            
            # Process each paper
            for paper_num, files in sorted(paper_files.items()):
                if not files["qp"]:
                    print(f"[SKIP] No question paper for {paper_num}")
                    continue
                
                print(f"\n[PAPER] Phy_{year}_{season}_{paper_num}")
                print(f"  QP: {files['qp'].name}")
                print(f"  MS: {files['ms'].name if files['ms'] else 'Not found'}")
                
                try:
                    # Create paper record
                    paper_id, existing_pages = create_or_get_paper(year, season, paper_num)
                    
                    if existing_pages > 0:
                        print(f"[SKIP] Paper already has {existing_pages} pages")
                        continue
                    
                    # Process and upload pages
                    pages_created = process_paper_pages(
                        paper_id,
                        files["qp"],
                        files["ms"],
                        year,
                        season,
                        paper_num
                    )
                    
                    # Classify pages
                    classify_paper(paper_id, classifier)
                    
                    total_papers += 1
                    total_pages += pages_created
                    
                    print(f"[DONE] Phy_{year}_{season}_{paper_num} complete")
                    
                except Exception as e:
                    print(f"[ERROR] Failed to process Phy_{year}_{season}_{paper_num}: {e}")
                    continue
    
    print("\n" + "="*60)
    print(f"[SUMMARY] Processed {total_papers} papers, {total_pages} pages")
    print("="*60)

if __name__ == "__main__":
    process_all_physics_papers()
