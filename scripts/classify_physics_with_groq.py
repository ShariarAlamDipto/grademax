#!/usr/bin/env python3
"""
Classify Physics Questions Using Multiple Groq Models
Reads questions from database, extracts text from PDFs, classifies with LLM
Uses same multi-model approach as FPM for reliability and speed
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

# Fix Windows console encoding
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

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

if not GROQ_API_KEY:
    print("❌ Missing GROQ_API_KEY in .env.local")
    sys.exit(1)

# Initialize Supabase
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# Paths
PROCESSED_DIR = Path(__file__).parent.parent / "data" / "processed" / "Physics"
TOPICS_YAML = Path(__file__).parent.parent / "classification" / "physics_topics.yaml"

# Subject ID for Physics
SUBJECT_ID = "0b142517-d35d-4942-91aa-b4886aaabca3"


def get_physics_papers():
    """Get all Physics papers from database"""
    response = supabase.table("papers")\
        .select("id, year, season, paper_number, total_pages")\
        .eq("subject_id", SUBJECT_ID)\
        .order("year", desc=False)\
        .order("season")\
        .order("paper_number")\
        .execute()
    
    return response.data if response.data else []


def get_unclassified_pages(paper_id: str):
    """Get pages that need classification (no topics assigned)"""
    response = supabase.table("pages")\
        .select("id, page_number, question_number, qp_page_url")\
        .eq("paper_id", paper_id)\
        .order("page_number")\
        .execute()
    
    if not response.data:
        return []
    
    # Filter for unclassified (no topics or empty topics)
    unclassified = []
    for page in response.data:
        topics = page.get('topics', [])
        if not topics or len(topics) == 0:
            unclassified.append(page)
    
    return unclassified


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


def classify_page(page_id: str, page_number: int, question_number: str, 
                 paper_year: int, paper_season: str, paper_number: str,
                 classifier: MistralTopicClassifier):
    """Classify a single page"""
    
    # Find local PDF file
    # Format: data/processed/Physics/{YEAR}_{Season}_P{N}/pages/q{qnum}.pdf
    folder_name = f"{paper_year}_{paper_season}_{paper_number}"
    pdf_path = PROCESSED_DIR / folder_name / "pages" / f"q{question_number}.pdf"
    
    if not pdf_path.exists():
        print(f"      ⚠️  Q{question_number}: PDF not found at {pdf_path}")
        return False
    
    # Extract text
    text = extract_text_from_pdf(pdf_path)
    
    if not text or len(text.strip()) < 50:
        print(f"      ⚠️  Q{question_number}: Insufficient text (only {len(text)} chars)")
        return False
    
    try:
        # Classify with multi-model approach
        result = classifier.classify(text, f"Q{question_number}")
        
        if not result:
            print(f"      ❌ Q{question_number}: Classification returned None")
            return False
        
        # Update database
        if result.page_has_question:
            supabase.table("pages")\
                .update({
                    "topics": [result.topic],
                    "difficulty": result.difficulty,
                    "confidence": result.confidence,
                    "text_excerpt": text[:500]  # Store first 500 chars
                })\
                .eq("id", page_id)\
                .execute()
            
            print(f"      ✅ Q{question_number}: Topic {result.topic} | {result.difficulty} | {result.confidence:.2f}")
            return True
        else:
            print(f"      ⚠️  Q{question_number}: No question detected")
            return False
            
    except Exception as e:
        print(f"      ❌ Q{question_number}: Error - {str(e)[:100]}")
        return False


def main():
    print("\n" + "="*80)
    print("🔬 CLASSIFY PHYSICS QUESTIONS - MULTI-MODEL GROQ")
    print("="*80)
    
    # Check YAML exists
    if not TOPICS_YAML.exists():
        print(f"\n❌ Topics YAML not found: {TOPICS_YAML}")
        return
    
    # Check processed directory exists
    if not PROCESSED_DIR.exists():
        print(f"\n❌ Processed directory not found: {PROCESSED_DIR}")
        return
    
    # Initialize classifier with multi-model support
    print("\n📦 Initializing Multi-Model Classifier")
    print("="*80)
    classifier = MistralTopicClassifier(
        topics_yaml_path=str(TOPICS_YAML),
        groq_api_key=GROQ_API_KEY,
        model_name="llama-3.1-8b-instant"  # Start with fast model
    )
    print(f"   ✅ Loaded {len(classifier.topics)} Physics topics")
    print(f"   ✅ Available models: {[m['name'] for m in classifier.available_models]}")
    print(f"   ✅ Starting with: {classifier.model}")
    print(f"   ⏱️  Rate limit: 5s delay between requests (conservative)")
    
    # Get papers
    print("\n📂 Fetching Physics papers from database...")
    papers = get_physics_papers()
    
    if not papers:
        print("   ❌ No Physics papers found in database")
        print("   💡 Run upload_physics_to_database.py first!")
        return
    
    print(f"   ✅ Found {len(papers)} papers")
    
    # Count unclassified pages
    total_unclassified = 0
    for paper in papers:
        unclassified = get_unclassified_pages(paper['id'])
        total_unclassified += len(unclassified)
    
    print(f"   📊 Total unclassified pages: {total_unclassified}")
    
    if total_unclassified == 0:
        print("\n✅ All pages already classified!")
        return
    
    # Estimate time
    estimated_minutes = (total_unclassified * 5) / 60
    print(f"   ⏱️  Estimated time: ~{estimated_minutes:.0f} minutes")
    
    # Confirm
    response = input(f"\n❓ Classify {total_unclassified} Physics questions? (yes/no): ")
    if response.lower() != 'yes':
        print("❌ Cancelled")
        return
    
    # Process each paper
    print("\n" + "="*80)
    print("CLASSIFICATION")
    print("="*80)
    
    stats = {
        'total_papers': len(papers),
        'total_pages': 0,
        'classified': 0,
        'failed': 0,
        'skipped': 0
    }
    
    for i, paper in enumerate(papers, 1):
        paper_id = paper['id']
        year = paper['year']
        season = paper['season']
        paper_num = paper['paper_number']
        
        print(f"\n[{i}/{len(papers)}] {year} {season} {paper_num}")
        
        # Get unclassified pages
        unclassified = get_unclassified_pages(paper_id)
        
        if not unclassified:
            print(f"   ✅ Already classified ({paper['total_pages']} pages)")
            stats['skipped'] += paper['total_pages']
            continue
        
        print(f"   📝 {len(unclassified)} pages to classify")
        stats['total_pages'] += len(unclassified)
        
        # Classify each page
        for page in unclassified:
            success = classify_page(
                page['id'],
                page['page_number'],
                page['question_number'],
                year,
                season,
                paper_num,
                classifier
            )
            
            if success:
                stats['classified'] += 1
            else:
                stats['failed'] += 1
    
    # Final summary
    print("\n" + "="*80)
    print("📊 CLASSIFICATION SUMMARY")
    print("="*80)
    
    print(f"\n✅ Successfully classified: {stats['classified']}/{stats['total_pages']}")
    
    if stats['failed'] > 0:
        print(f"❌ Failed: {stats['failed']}/{stats['total_pages']}")
    
    if stats['skipped'] > 0:
        print(f"⏭️  Already classified: {stats['skipped']} pages")
    
    if stats['classified'] > 0:
        success_rate = (stats['classified'] / stats['total_pages'] * 100)
        print(f"\n📈 Success rate: {success_rate:.1f}%")
    
    print("\n" + "="*80)
    print("✨ CLASSIFICATION COMPLETE!")
    print("="*80)
    print("\n💡 Next steps:")
    print("   1. Check database to verify classifications")
    print("   2. Run worksheet generation tests")
    print("   3. Review any failed classifications")


if __name__ == "__main__":
    main()
