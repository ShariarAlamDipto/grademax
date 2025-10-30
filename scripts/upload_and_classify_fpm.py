#!/usr/bin/env python3
"""
UPLOAD AND CLASSIFY ALL FPM PAPERS
Reads processed papers from local folder, uploads to database, then classifies with LLM
"""

import os
import sys
import json
import time
from pathlib import Path
from dotenv import load_dotenv
from supabase import create_client, Client
import PyPDF2

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
PROCESSED_DIR = Path(__file__).parent.parent / "data" / "processed" / "Further Pure Maths Processed"
TOPICS_YAML = Path(__file__).parent.parent / "classification" / "further_pure_maths_topics.yaml"


def get_fpm_subject_id():
    """Get the subject ID for Further Pure Mathematics"""
    response = supabase.table("subjects").select("id, name, code").eq("code", "9FM0").execute()
    if response.data and len(response.data) > 0:
        return response.data[0]["id"], response.data[0]["name"]
    else:
        raise ValueError("Subject 9FM0 (Further Pure Mathematics) not found in database")


def parse_paper_folder(folder_name: str):
    """Parse folder name like '2019_Jun_1P' into components"""
    parts = folder_name.split('_')
    if len(parts) >= 3:
        year = int(parts[0])
        season = parts[1]  # Jun, Jan, Nov
        paper_number = parts[2]  # 1P, 2P, 1RP, etc.
        return year, season, paper_number
    return None


def upload_paper(subject_id: str, year: int, season: str, paper_number: str, manifest_path: Path):
    """Upload or update a paper in the database"""
    
    # Check if paper already exists
    existing = supabase.table("papers")\
        .select("id")\
        .eq("subject_id", subject_id)\
        .eq("year", year)\
        .eq("season", season)\
        .eq("paper_number", paper_number)\
        .execute()
    
    if existing.data:
        # Paper exists, return its ID
        return existing.data[0]["id"], False
    
    # Load manifest to get total pages
    with open(manifest_path, 'r', encoding='utf-8') as f:
        manifest = json.load(f)
    
    total_pages = len(manifest.get("questions", []))
    
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


def extract_text_from_pdf(pdf_path: Path) -> str:
    """Extract text from a PDF file"""
    try:
        with open(pdf_path, 'rb') as f:
            pdf_reader = PyPDF2.PdfReader(f)
            text = ""
            for page in pdf_reader.pages:
                page_text = page.extract_text() or ""
                text += page_text
            return text.strip()
    except Exception as e:
        print(f"         ❌ Error extracting text from {pdf_path.name}: {str(e)[:50]}")
        return ""


def upload_pages(paper_id: str, manifest_path: Path, pages_dir: Path):
    """Upload all pages for a paper"""
    
    # Check if pages already exist
    existing = supabase.table("pages").select("id").eq("paper_id", paper_id).execute()
    if existing.data:
        return len(existing.data), 0  # Already uploaded
    
    # Load manifest
    with open(manifest_path, 'r', encoding='utf-8') as f:
        manifest = json.load(f)
    
    pages_data = []
    
    for question in manifest.get("questions", []):
        q_num = question.get("question_number")
        
        # Extract text from PDF
        q_pdf = pages_dir / f"q{q_num}.pdf"
        text_excerpt = ""
        if q_pdf.exists():
            full_text = extract_text_from_pdf(q_pdf)
            text_excerpt = full_text[:500]  # First 500 chars for excerpt
        
        page_data = {
            "paper_id": paper_id,
            "page_number": int(q_num),
            "question_number": str(q_num),
            "is_question": True,
            "topics": [],  # Will be filled by classification
            "text_excerpt": text_excerpt,
            "has_diagram": False,  # Could detect from PDF metadata
            "page_count": 1
        }
        pages_data.append(page_data)
    
    if pages_data:
        response = supabase.table("pages").insert(pages_data).execute()
        return len(response.data), len(response.data)
    
    return 0, 0


def classify_paper_pages(paper_id: str, classifier: MistralTopicClassifier):
    """Classify all pages for a paper"""
    
    # Get pages that need classification
    pages = supabase.table("pages")\
        .select("id, page_number, question_number, text_excerpt")\
        .eq("paper_id", paper_id)\
        .order("page_number")\
        .execute()
    
    if not pages.data:
        return 0, 0
    
    classified_count = 0
    failed_count = 0
    
    for page in pages.data:
        page_id = page["id"]
        page_num = page["page_number"]
        text = page.get("text_excerpt", "")
        
        if not text or len(text.strip()) < 50:
            failed_count += 1
            continue
        
        try:
            # Classify
            result = classifier.classify(text, f"Q{page_num}")
            
            # Update database
            if result.page_has_question:
                supabase.table("pages")\
                    .update({
                        "topics": [result.topic],
                        "difficulty": result.difficulty,
                        "confidence": result.confidence
                    })\
                    .eq("id", page_id)\
                    .execute()
                
                classified_count += 1
                print(f"      ✅ Q{page_num}: Topic {result.topic} | {result.difficulty} | {result.confidence:.2f}")
            else:
                failed_count += 1
                print(f"      ⚠️  Q{page_num}: No question detected")
                
        except Exception as e:
            print(f"      ❌ Q{page_num}: Error - {str(e)[:50]}")
            failed_count += 1
            continue
    
    return classified_count, failed_count


def main():
    print("\n" + "=" * 80)
    print("📦 UPLOAD AND CLASSIFY ALL FPM PAPERS")
    print("=" * 80)
    
    # Get subject
    try:
        subject_id, subject_name = get_fpm_subject_id()
        print(f"\n✅ Subject: {subject_name} (ID: {subject_id})")
    except ValueError as e:
        print(f"\n❌ Error: {e}")
        return
    
    # Check processed directory
    if not PROCESSED_DIR.exists():
        print(f"\n❌ Processed directory not found: {PROCESSED_DIR}")
        return
    
    # Get all paper folders
    paper_folders = sorted([d for d in PROCESSED_DIR.iterdir() if d.is_dir()])
    print(f"\n📂 Found {len(paper_folders)} paper folders")
    
    # Initialize classifier
    print("\n📦 Initializing Classifier")
    print("=" * 80)
    classifier = MistralTopicClassifier(
        topics_yaml_path=str(TOPICS_YAML),
        api_key=GROQ_API_KEY,
        model_name="llama-3.1-8b-instant"
    )
    print(f"   ✅ Loaded {len(classifier.topics)} topics")
    
    # Process each paper
    print("\n📦 Processing Papers")
    print("=" * 80)
    
    total_papers_new = 0
    total_papers_existing = 0
    total_pages_uploaded = 0
    total_pages_classified = 0
    total_pages_failed = 0
    
    for i, folder in enumerate(paper_folders, 1):
        parsed = parse_paper_folder(folder.name)
        if not parsed:
            print(f"\n   ⚠️  Skipping invalid folder: {folder.name}")
            continue
        
        year, season, paper_number = parsed
        print(f"\n   [{i}/{len(paper_folders)}] {year} {season} Paper {paper_number}")
        
        # Check for manifest
        manifest_path = folder / "manifest.json"
        if not manifest_path.exists():
            print(f"      ⚠️  No manifest.json found, skipping")
            continue
        
        questions_dir = folder / "pages"
        if not questions_dir.exists():
            print(f"      ⚠️  No pages directory found, skipping")
            continue
        
        try:
            # Upload paper
            paper_id, is_new = upload_paper(subject_id, year, season, paper_number, manifest_path)
            if is_new:
                print(f"      ✅ Created paper (ID: {paper_id[:8]}...)")
                total_papers_new += 1
            else:
                print(f"      ℹ️  Paper already exists (ID: {paper_id[:8]}...)")
                total_papers_existing += 1
            
            # Upload pages
            total, uploaded = upload_pages(paper_id, manifest_path, questions_dir)
            if uploaded > 0:
                print(f"      ✅ Uploaded {uploaded} pages")
                total_pages_uploaded += uploaded
            elif total > 0:
                print(f"      ℹ️  {total} pages already exist")
            
            # Classify pages
            classified, failed = classify_paper_pages(paper_id, classifier)
            total_pages_classified += classified
            total_pages_failed += failed
            
            if classified > 0:
                print(f"      ✅ Classified {classified} pages")
            if failed > 0:
                print(f"      ⚠️  Failed/skipped {failed} pages")
            
        except Exception as e:
            print(f"      ❌ Error: {str(e)[:100]}")
            continue
    
    # Final summary
    print("\n" + "=" * 80)
    print("📊 FINAL SUMMARY")
    print("=" * 80)
    print(f"   Papers processed: {len(paper_folders)}")
    print(f"   Papers created: {total_papers_new}")
    print(f"   Papers already existed: {total_papers_existing}")
    print(f"   Pages uploaded: {total_pages_uploaded}")
    print(f"   Pages classified: {total_pages_classified}")
    print(f"   Pages failed/skipped: {total_pages_failed}")
    if total_pages_classified + total_pages_failed > 0:
        success_rate = (total_pages_classified / (total_pages_classified + total_pages_failed)) * 100
        print(f"   Classification success rate: {success_rate:.1f}%")
    print()


if __name__ == "__main__":
    main()
