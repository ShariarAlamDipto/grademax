#!/usr/bin/env python3
"""
Process and classify all Physics papers from local processed folder
- Reads PDFs from local processed folder
- Extracts text and creates pages in database
- Classifies pages with multi-model LLM topic tagger using JSON output
- Uses the exact same structure as FPM for consistency
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
    print("❌ .env.local not found!")
    sys.exit(1)
load_dotenv(env_path)

SUPABASE_URL = os.getenv("NEXT_PUBLIC_SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    print("❌ Missing Supabase credentials in .env.local")
    sys.exit(1)

# Initialize Supabase
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# Paths - Physics specific
DATA_DIR = Path(__file__).parent.parent / "data"
PROCESSED_DIR = DATA_DIR / "processed" / "Physics Processed"
TOPICS_YAML = Path(__file__).parent.parent / "config" / "physics_topics.yaml"

# Get Physics subject ID
def get_physics_subject():
    """Get Physics subject from database"""
    response = supabase.table("subjects").select("id, name, code").eq("code", "4PH1").execute()
    if not response.data:
        print("❌ Physics subject (4PH1) not found in database!")
        print("   Please add it to the subjects table first.")
        sys.exit(1)
    return response.data[0]

PHYSICS_SUBJECT = get_physics_subject()
SUBJECT_ID = PHYSICS_SUBJECT["id"]

print(f"✅ Found subject: {PHYSICS_SUBJECT['name']} (Code: {PHYSICS_SUBJECT['code']}, ID: {SUBJECT_ID})")


def extract_text_from_pdf(pdf_path: Path) -> str:
    """Extract text content from PDF file"""
    try:
        with open(pdf_path, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)
            text = ""
            for page in pdf_reader.pages:
                text += page.extract_text()
            return text.strip()
    except Exception as e:
        print(f"    ⚠️  Error extracting text from {pdf_path.name}: {str(e)[:50]}")
        return ""


def parse_folder_name(folder_name: str):
    """Parse folder name like '2019_Jun_1P' into components"""
    parts = folder_name.split('_')
    if len(parts) >= 3:
        year = int(parts[0])
        season = parts[1]  # Jun, Jan, Nov
        paper_number = parts[2]  # 1P, 2P, 1RP, etc.
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


def process_paper_pages(paper_id: str, pages_dir: Path, manifest_path: Path, folder_name: str):
    """Extract text from PDFs and create pages in database with correct URLs"""
    
    # Check if pages already exist for this paper
    existing_pages = supabase.table("pages").select("id").eq("paper_id", paper_id).execute()
    if existing_pages.data and len(existing_pages.data) > 0:
        return len(existing_pages.data), 0  # Already processed
    
    # Load manifest to get question list
    with open(manifest_path, 'r', encoding='utf-8') as f:
        manifest = json.load(f)
    
    questions = manifest.get("questions", [])
    pages_created = 0
    
    # Build URLs using correct format (learning from FPM mistakes!)
    base_url = SUPABASE_URL
    bucket = 'question-pdfs'
    
    for question in questions:
        q_num = question.get("question_number")
        q_file = pages_dir / f"q{q_num}.pdf"
        
        if not q_file.exists():
            continue
        
        # Extract text from PDF
        full_text = extract_text_from_pdf(q_file)
        if not full_text:
            continue
        
        # CRITICAL: Build URLs correctly (avoiding FPM mistakes)
        # Format: {base}/storage/v1/object/public/question-pdfs/subjects/Physics/pages/{folder}/q{num}.pdf
        qp_url = f"{base_url}/storage/v1/object/public/{bucket}/subjects/Physics/pages/{folder_name}/q{q_num}.pdf"
        ms_url = f"{base_url}/storage/v1/object/public/{bucket}/subjects/Physics/pages/{folder_name}/q{q_num}_ms.pdf"
        
        # Create page in database
        page_data = {
            "paper_id": paper_id,
            "page_number": int(q_num),
            "question_number": str(q_num),
            "is_question": True,
            "topics": [],  # Will be filled by classification
            "text_excerpt": full_text[:500],  # First 500 chars
            "has_diagram": False,
            "page_count": 1,
            "qp_page_url": qp_url,  # ⚠️ CRITICAL: Set URLs during creation!
            "ms_page_url": ms_url   # ⚠️ CRITICAL: Set URLs during creation!
        }
        
        try:
            supabase.table("pages").insert(page_data).execute()
            pages_created += 1
        except Exception as e:
            print(f"        ❌ Error creating page Q{q_num}: {str(e)[:50]}")
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
        q_num = page["question_number"]
        q_file = pages_dir / f"q{q_num}.pdf"
        
        if not q_file.exists():
            failed_count += 1
            continue
        
        # Extract full text for classification
        full_text = extract_text_from_pdf(q_file)
        if not full_text:
            failed_count += 1
            continue
        
        try:
            # Classify using multi-model LLM with JSON output
            result = classifier.classify(full_text, q_num)
            
            if result and result.get('topics'):
                # Update page with classification results
                update_data = {
                    "topics": result['topics'],
                    "confidence": result.get('confidence', 0.0)
                }
                
                supabase.table("pages")\
                    .update(update_data)\
                    .eq("id", page["id"])\
                    .execute()
                
                classified_count += 1
                print(f"        ✅ Q{q_num}: {result['topics']} ({result.get('confidence', 0.0):.2f})")
            else:
                failed_count += 1
                print(f"        ⚠️  Q{q_num}: No classification")
                
        except Exception as e:
            failed_count += 1
            print(f"        ❌ Q{q_num}: {str(e)[:50]}")
            continue
    
    return classified_count, failed_count


def main():
    """Main processing pipeline"""
    print("\n" + "="*60)
    print("🔬 PHYSICS PAPER PROCESSING & CLASSIFICATION")
    print("="*60)
    
    if not PROCESSED_DIR.exists():
        print(f"\n❌ Processed directory not found: {PROCESSED_DIR}")
        sys.exit(1)
    
    if not TOPICS_YAML.exists():
        print(f"\n❌ Topics YAML not found: {TOPICS_YAML}")
        sys.exit(1)
    
    # Initialize multi-model classifier with JSON output
    print(f"\n📊 Initializing multi-model classifier...")
    print(f"   Topics file: {TOPICS_YAML.name}")
    classifier = MistralTopicClassifier(
        str(TOPICS_YAML), 
        GROQ_API_KEY
    )
    print(f"   ✅ Classifier ready with {len(classifier.groq_models)} models")
    
    # Get all paper folders
    paper_folders = [f for f in PROCESSED_DIR.iterdir() if f.is_dir()]
    paper_folders.sort()
    
    print(f"\n📁 Found {len(paper_folders)} Physics paper folders")
    
    # Statistics
    papers_created = 0
    papers_existed = 0
    total_pages_created = 0
    total_classified = 0
    total_failed = 0
    
    for folder in paper_folders:
        manifest_path = folder / "manifest.json"
        pages_dir = folder / "pages"
        
        # Skip if no manifest
        if not manifest_path.exists():
            print(f"\n⚠️  Skipping {folder.name}: No manifest.json")
            continue
        
        # Skip if no pages directory
        if not pages_dir.exists():
            print(f"\n⚠️  Skipping {folder.name}: No pages/ directory")
            continue
        
        # Parse folder name
        parsed = parse_folder_name(folder.name)
        if not parsed:
            print(f"\n⚠️  Skipping {folder.name}: Could not parse folder name")
            continue
        
        year, season, paper_number = parsed
        
        # Load manifest to get page count
        with open(manifest_path, 'r', encoding='utf-8') as f:
            manifest = json.load(f)
        
        total_pages = len(manifest.get("questions", []))
        
        print(f"\n📄 Processing: {folder.name} ({total_pages} pages)")
        
        # Create or get paper
        paper_id, is_new = create_or_get_paper(
            SUBJECT_ID, 
            year, 
            season, 
            paper_number, 
            total_pages
        )
        
        if is_new:
            papers_created += 1
            print(f"   ✅ Paper created in database")
        else:
            papers_existed += 1
            print(f"   ℹ️  Paper already exists in database")
        
        # Process pages
        print(f"   📝 Extracting and creating pages...")
        pages_created, pages_new = process_paper_pages(paper_id, pages_dir, manifest_path, folder.name)
        total_pages_created += pages_new
        
        if pages_new > 0:
            print(f"   ✅ Created {pages_new} pages with URLs")
        else:
            print(f"   ℹ️  Pages already exist ({pages_created} total)")
        
        # Classify pages
        if pages_created > 0:
            print(f"   🤖 Classifying pages...")
            classified, failed = classify_paper(paper_id, pages_dir, classifier)
            total_classified += classified
            total_failed += failed
            
            if classified > 0:
                print(f"   ✅ Classified {classified}/{pages_created} pages")
            if failed > 0:
                print(f"   ⚠️  {failed} pages failed classification")
    
    # Final summary
    print("\n" + "="*60)
    print("📊 PROCESSING SUMMARY")
    print("="*60)
    print(f"Papers created:     {papers_created}")
    print(f"Papers existed:     {papers_existed}")
    print(f"Pages created:      {total_pages_created}")
    print(f"Pages classified:   {total_classified}")
    print(f"Classification failed: {total_failed}")
    
    if total_pages_created > 0:
        success_rate = (total_classified / total_pages_created) * 100
        print(f"\n✅ Classification success rate: {success_rate:.1f}%")
    
    print("\n✅ Processing complete!")


if __name__ == "__main__":
    main()
