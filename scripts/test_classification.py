#!/usr/bin/env python3
"""
Test classification on a small sample before running full batch
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv
from supabase import create_client, Client
import fitz  # PyMuPDF
import requests
from io import BytesIO

sys.path.insert(0, str(Path(__file__).parent))
from single_topic_classifier import SingleTopicClassifier

# Load environment
load_dotenv('.env.local')

# Initialize Supabase
url = os.getenv('NEXT_PUBLIC_SUPABASE_URL')
service_role_key = os.getenv('SUPABASE_SERVICE_ROLE_KEY')
gemini_api_key = os.getenv('GEMINI_API_KEY')
supabase: Client = create_client(url, service_role_key)

PHYSICS_SUBJECT_ID = '0b142517-d35d-4942-91aa-b4886aaabca3'
TOPICS_YAML = Path(__file__).parent.parent / 'config' / 'physics_topics.yaml'


def download_pdf_from_url(url: str) -> bytes:
    """Download PDF from storage URL"""
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        return response.content
    except Exception as e:
        print(f"❌ Error downloading PDF: {e}")
        return None


def extract_text_from_pdf(pdf_bytes: bytes) -> str:
    """Extract text from PDF bytes"""
    try:
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        text = ""
        for page in doc:
            text += page.get_text()
        doc.close()
        return text
    except Exception as e:
        print(f"❌ Error extracting text: {e}")
        return ""


def main():
    print("=" * 70)
    print("🧪 Test Classification on Sample Pages")
    print("=" * 70)
    print()
    
    # Initialize classifier
    print("1️⃣  Initializing classifier...")
    classifier = SingleTopicClassifier(str(TOPICS_YAML), gemini_api_key)
    print(f"   ✅ Loaded {len(classifier.topics)} topics\n")
    
    # Get first Physics paper
    print("2️⃣  Getting sample pages...")
    papers = supabase.table('papers').select('id, year, season, paper_number').eq('subject_id', PHYSICS_SUBJECT_ID).order('year').limit(1).execute()
    
    if not papers.data:
        print("   ❌ No papers found")
        return
    
    paper = papers.data[0]
    print(f"   📄 Using: {paper['year']} {paper['season']} Paper {paper['paper_number']}\n")
    
    # Get first 3 pages
    pages = supabase.table('pages').select('*').eq('paper_id', paper['id']).eq('is_question', True).limit(3).execute()
    
    if not pages.data:
        print("   ❌ No pages found")
        return
    
    print(f"3️⃣  Testing classification on {len(pages.data)} pages...\n")
    
    for i, page in enumerate(pages.data, 1):
        print(f"   [{i}/{len(pages.data)}] Question {page['question_number']}")
        print(f"      URL: {page['qp_page_url'][:80]}...")
        
        # Download PDF
        pdf_bytes = download_pdf_from_url(page['qp_page_url'])
        if not pdf_bytes:
            continue
        
        # Extract text
        text = extract_text_from_pdf(pdf_bytes)
        if not text or len(text.strip()) < 20:
            print("      ⚠️  No text extracted")
            continue
        
        print(f"      Text length: {len(text)} chars")
        print(f"      Preview: {text[:100].strip()}...")
        
        # Classify
        try:
            result = classifier.classify(text, page['question_number'])
            print(f"      ✅ Classification:")
            print(f"         Has question: {result.page_has_question}")
            print(f"         Topic: {result.topic}")
            print(f"         Difficulty: {result.difficulty}")
            print(f"         Confidence: {result.confidence:.2f}")
            print()
        except Exception as e:
            print(f"      ❌ Error: {e}\n")
    
    print("\n" + "=" * 70)
    print("✅ Test complete!")
    print("=" * 70)
    print("\nIf classifications look good, run:")
    print("  python scripts/classify_physics_pages.py")
    print()


if __name__ == '__main__':
    main()
