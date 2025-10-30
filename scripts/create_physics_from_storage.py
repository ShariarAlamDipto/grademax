#!/usr/bin/env python3
"""
Create Physics database records from existing Supabase storage PDFs
Then classify using multi-model LLM with JSON output

This script:
1. Scans Physics PDFs in Supabase storage
2. Creates paper records in database
3. Creates page records with correct URLs
4. Extracts text from storage PDFs
5. Classifies using multi-model LLM (same as FPM)
"""

import os
import sys
import time
from pathlib import Path
from dotenv import load_dotenv
from supabase import create_client, Client
import PyPDF2
from io import BytesIO
import requests

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

# Paths
BUCKET_NAME = 'question-pdfs'
PHYSICS_STORAGE_PATH = 'subjects/Physics/pages'
TOPICS_YAML = Path(__file__).parent.parent / "classification" / "physics_topics.yaml"

# Get Physics subject ID
def get_physics_subject():
    """Get Physics subject from database"""
    response = supabase.table("subjects").select("id, name, code").eq("code", "4PH1").execute()
    if not response.data:
        print("❌ Physics subject (4PH1) not found in database!")
        sys.exit(1)
    return response.data[0]

PHYSICS_SUBJECT = get_physics_subject()
SUBJECT_ID = PHYSICS_SUBJECT["id"]

print(f"[OK] Found subject: {PHYSICS_SUBJECT['name']} (Code: {PHYSICS_SUBJECT['code']}, ID: {SUBJECT_ID})")


def parse_folder_name(folder_name: str):
    """Parse folder name like '2019_Jun_1P' into components"""
    parts = folder_name.split('_')
    if len(parts) >= 3:
        year = int(parts[0])
        season = parts[1]  # Jun, Jan
        paper_number = parts[2]  # 1P, 2P
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


def download_and_extract_text(pdf_url: str) -> str:
    """Download PDF from storage and extract text"""
    try:
        response = requests.get(pdf_url, timeout=30)
        response.raise_for_status()
        
        pdf_reader = PyPDF2.PdfReader(BytesIO(response.content))
        text = ""
        for page in pdf_reader.pages:
            text += page.extract_text()
        return text.strip()
    except Exception as e:
        print(f"    ⚠️  Error extracting text: {str(e)[:50]}")
        return ""


def process_storage_folder(folder_name: str):
    """Process one folder from storage - create paper and pages"""
    
    # Parse folder name
    parsed = parse_folder_name(folder_name)
    if not parsed:
        print(f"\n⚠️  Skipping {folder_name}: Could not parse folder name")
        return None, 0, 0
    
    year, season, paper_number = parsed
    
    # Get list of PDFs in this folder
    try:
        folder_path = f"{PHYSICS_STORAGE_PATH}/{folder_name}"
        files = supabase.storage.from_(BUCKET_NAME).list(folder_path)
        
        # Get only question PDFs (not mark schemes)
        question_pdfs = [f for f in files if f['name'].endswith('.pdf') and not f['name'].endswith('_ms.pdf')]
        question_pdfs.sort(key=lambda x: int(x['name'].replace('q', '').replace('.pdf', '')))
        
        total_pages = len(question_pdfs)
        
    except Exception as e:
        print(f"\n⚠️  Error listing files in {folder_name}: {e}")
        return None, 0, 0
    
    print(f"\n📄 Processing: {folder_name} ({total_pages} questions)")
    
    # Create or get paper
    paper_id, is_new = create_or_get_paper(
        SUBJECT_ID, 
        year, 
        season, 
        paper_number, 
        total_pages
    )
    
    if is_new:
        print(f"   ✅ Paper created in database")
    else:
        print(f"   ℹ️  Paper already exists")
    
    # Check if pages already exist
    existing_pages = supabase.table("pages").select("id").eq("paper_id", paper_id).execute()
    if existing_pages.data and len(existing_pages.data) > 0:
        print(f"   ℹ️  Pages already exist ({len(existing_pages.data)} pages)")
        return paper_id, 0, 0
    
    # Create pages for each question PDF
    pages_created = 0
    print(f"   📝 Creating pages...")
    
    for pdf_file in question_pdfs:
        q_num_str = pdf_file['name'].replace('q', '').replace('.pdf', '')
        q_num = int(q_num_str)
        
        # Build URLs (following FPM format exactly!)
        qp_url = f"{SUPABASE_URL}/storage/v1/object/public/{BUCKET_NAME}/{folder_path}/q{q_num}.pdf"
        ms_url = f"{SUPABASE_URL}/storage/v1/object/public/{BUCKET_NAME}/{folder_path}/q{q_num}_ms.pdf"
        
        # Download and extract text for classification
        text = download_and_extract_text(qp_url)
        
        if not text:
            print(f"      ⚠️  Q{q_num}: No text extracted")
            continue
        
        # Create page in database with URLs set immediately!
        page_data = {
            "paper_id": paper_id,
            "page_number": q_num,
            "question_number": str(q_num),
            "is_question": True,
            "topics": [],  # Will be filled by classification
            "text_excerpt": text[:500],  # First 500 chars
            "has_diagram": False,
            "page_count": 1,
            "qp_page_url": qp_url,  # ⚠️ CRITICAL: Set URL during creation!
            "ms_page_url": ms_url   # ⚠️ CRITICAL: Set URL during creation!
        }
        
        try:
            supabase.table("pages").insert(page_data).execute()
            pages_created += 1
        except Exception as e:
            print(f"      ❌ Error creating page Q{q_num}: {str(e)[:50]}")
            continue
    
    print(f"   ✅ Created {pages_created} pages with URLs")
    return paper_id, pages_created, pages_created


def classify_paper_pages(paper_id: str, classifier: MistralTopicClassifier):
    """Classify all pages for a paper"""
    
    # Get all unclassified pages for this paper
    pages = supabase.table("pages")\
        .select("id, page_number, question_number, qp_page_url, text_excerpt")\
        .eq("paper_id", paper_id)\
        .order("page_number")\
        .execute()
    
    if not pages.data:
        return 0, 0
    
    classified_count = 0
    failed_count = 0
    
    print(f"   🤖 Classifying {len(pages.data)} pages...")
    
    for page in pages.data:
        q_num = page["question_number"]
        
        # Use text_excerpt if available, otherwise download PDF
        text = page.get("text_excerpt", "")
        if not text or len(text) < 50:
            if page.get("qp_page_url"):
                text = download_and_extract_text(page["qp_page_url"])
        
        if not text:
            failed_count += 1
            continue
        
        try:
            # Classify using multi-model LLM with JSON output
            result = classifier.classify(text, q_num)
            
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
                topic_names = ', '.join(str(t) for t in result['topics'][:2])
                print(f"      ✅ Q{q_num}: {topic_names} ({result.get('confidence', 0.0):.2f})")
            else:
                failed_count += 1
                print(f"      ⚠️  Q{q_num}: No classification")
                
        except Exception as e:
            failed_count += 1
            print(f"      ❌ Q{q_num}: {str(e)[:50]}")
            continue
    
    return classified_count, failed_count


def main():
    """Main processing pipeline"""
    print("\n" + "="*60)
    print("🔬 PHYSICS DATABASE CREATION & CLASSIFICATION")
    print("   From Existing Supabase Storage")
    print("="*60)
    
    if not TOPICS_YAML.exists():
        print(f"\n❌ Topics YAML not found: {TOPICS_YAML}")
        sys.exit(1)
    
    # Initialize multi-model classifier
    print(f"\n📊 Initializing multi-model classifier...")
    print(f"   Topics file: {TOPICS_YAML.name}")
    classifier = MistralTopicClassifier(
        str(TOPICS_YAML), 
        GROQ_API_KEY
    )
    print(f"   ✅ Classifier ready with {len(classifier.available_models)} models")
    
    # Get all folders from storage
    print(f"\n📁 Scanning storage: {PHYSICS_STORAGE_PATH}")
    try:
        folders = supabase.storage.from_(BUCKET_NAME).list(PHYSICS_STORAGE_PATH)
        folder_names = [f['name'] for f in folders if f.get('name')]
        folder_names.sort()
    except Exception as e:
        print(f"❌ Error accessing storage: {e}")
        sys.exit(1)
    
    print(f"   Found {len(folder_names)} Physics paper folders")
    
    # Statistics
    papers_created = 0
    papers_existed = 0
    total_pages_created = 0
    total_classified = 0
    total_failed = 0
    
    # Process each folder
    for folder_name in folder_names:
        paper_id, pages_created, pages_new = process_storage_folder(folder_name)
        
        if not paper_id:
            continue
        
        if pages_new > 0:
            papers_created += 1
            total_pages_created += pages_new
        else:
            papers_existed += 1
        
        # Classify pages if they were just created
        if pages_created > 0:
            classified, failed = classify_paper_pages(paper_id, classifier)
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
    print(f"Papers created:        {papers_created}")
    print(f"Papers existed:        {papers_existed}")
    print(f"Pages created:         {total_pages_created}")
    print(f"Pages classified:      {total_classified}")
    print(f"Classification failed: {total_failed}")
    
    if total_pages_created > 0:
        success_rate = (total_classified / total_pages_created) * 100
        print(f"\n✅ Classification success rate: {success_rate:.1f}%")
    
    print("\n✅ Processing complete!")
    print("\nNext steps:")
    print("  1. Run: python scripts/test_physics_urls.py")
    print("  2. Test worksheet generation via web UI")


if __name__ == "__main__":
    main()

