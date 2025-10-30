#!/usr/bin/env python3
"""
Extract text from PDF pages for classification

This script:
1. Downloads each page's PDF from Supabase storage
2. Extracts text using PyPDF2 or pdfplumber
3. Stores the extracted text in the text_excerpt field
4. Preserves the full page content for classification
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv
from supabase import create_client
import requests
from io import BytesIO

# Try to import PDF libraries
try:
    import pdfplumber
    PDF_LIBRARY = "pdfplumber"
except ImportError:
    try:
        import PyPDF2
        PDF_LIBRARY = "PyPDF2"
    except ImportError:
        print("❌ No PDF library found!")
        print("   Install with: pip install pdfplumber")
        print("   Or: pip install PyPDF2")
        sys.exit(1)

SUBJECT_ID = "0b142517-d35d-4942-91aa-b4886aaabca3"  # Physics


def init_supabase():
    """Initialize Supabase client"""
    load_dotenv('.env.local')
    url = os.getenv('NEXT_PUBLIC_SUPABASE_URL')
    key = os.getenv('SUPABASE_SERVICE_ROLE_KEY')
    
    if not url or not key:
        print("❌ Missing Supabase credentials in .env.local")
        sys.exit(1)
    
    return create_client(url, key)


def extract_text_pdfplumber(pdf_bytes):
    """Extract text using pdfplumber (better quality)"""
    try:
        with pdfplumber.open(BytesIO(pdf_bytes)) as pdf:
            text = ""
            for page in pdf.pages:
                text += page.extract_text() or ""
            return text.strip()
    except Exception as e:
        print(f"      ❌ pdfplumber error: {e}")
        return None


def extract_text_pypdf2(pdf_bytes):
    """Extract text using PyPDF2 (fallback)"""
    try:
        pdf_reader = PyPDF2.PdfReader(BytesIO(pdf_bytes))
        text = ""
        for page in pdf_reader.pages:
            text += page.extract_text() or ""
        return text.strip()
    except Exception as e:
        print(f"      ❌ PyPDF2 error: {e}")
        return None


def download_pdf(url):
    """Download PDF from URL"""
    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        return response.content
    except Exception as e:
        print(f"      ❌ Download error: {e}")
        return None


def extract_text_from_pdf(pdf_url):
    """Extract text from PDF URL"""
    # Download PDF
    pdf_bytes = download_pdf(pdf_url)
    if not pdf_bytes:
        return None
    
    # Extract text
    if PDF_LIBRARY == "pdfplumber":
        text = extract_text_pdfplumber(pdf_bytes)
    else:
        text = extract_text_pypdf2(pdf_bytes)
    
    return text


def main():
    print("=" * 70)
    print("📄 PDF TEXT EXTRACTION FOR CLASSIFICATION")
    print("=" * 70)
    print()
    print(f"Using PDF library: {PDF_LIBRARY}")
    print()
    
    supabase = init_supabase()
    
    # Get all Physics papers
    print("1️⃣  Loading Physics papers...")
    papers_response = supabase.table('papers')\
        .select('id,year,season,paper_number')\
        .eq('subject_id', SUBJECT_ID)\
        .order('year')\
        .order('season')\
        .order('paper_number')\
        .execute()
    
    papers = papers_response.data
    print(f"   ✅ Found {len(papers)} papers")
    
    # Get all pages
    print("\n2️⃣  Loading pages...")
    all_pages = []
    for paper in papers:
        pages_response = supabase.table('pages')\
            .select('id,page_number,qp_page_url,text_excerpt')\
            .eq('paper_id', paper['id'])\
            .order('page_number')\
            .execute()
        
        for page in pages_response.data:
            page['paper'] = paper
            all_pages.append(page)
    
    print(f"   📊 Total pages: {len(all_pages)}")
    
    # Filter pages that need text extraction
    needs_extraction = [
        p for p in all_pages 
        if not p.get('text_excerpt') or len(p.get('text_excerpt', '')) < 50
    ]
    
    print(f"   🔄 Need extraction: {len(needs_extraction)}")
    print(f"   ✅ Already extracted: {len(all_pages) - len(needs_extraction)}")
    
    if not needs_extraction:
        print("\n   ✅ All pages already have text!")
        return
    
    # Extract text from PDFs
    print(f"\n3️⃣  Extracting text from {len(needs_extraction)} pages...")
    print()
    
    extracted = 0
    failed = 0
    current_paper_id = None
    
    for i, page in enumerate(needs_extraction, 1):
        paper = page['paper']
        
        # Show paper header
        if paper['id'] != current_paper_id:
            current_paper_id = paper['id']
            print(f"\n   📄 Paper: {paper['year']} {paper['season']} Paper {paper['paper_number']}")
        
        print(f"      Q{page['page_number']}: ", end="", flush=True)
        
        # Extract text from PDF
        pdf_url = page.get('qp_page_url')
        if not pdf_url:
            print("❌ No PDF URL")
            failed += 1
            continue
        
        text = extract_text_from_pdf(pdf_url)
        
        if text and len(text) > 10:
            # Update database
            try:
                supabase.table('pages')\
                    .update({'text_excerpt': text})\
                    .eq('id', page['id'])\
                    .execute()
                
                extracted += 1
                print(f"✅ {len(text)} chars")
            except Exception as e:
                print(f"❌ DB error: {e}")
                failed += 1
        else:
            print("❌ No text extracted")
            failed += 1
        
        # Progress update every 50 pages
        if i % 50 == 0:
            print(f"\n      ⏱️  Progress: {i}/{len(needs_extraction)} | {extracted} extracted | {failed} failed\n")
    
    # Final summary
    print("\n" + "=" * 70)
    print("✅ EXTRACTION COMPLETE!")
    print("=" * 70)
    print()
    print(f"📊 Results:")
    print(f"   Extracted: {extracted}")
    print(f"   Failed: {failed}")
    print(f"   Success rate: {extracted / max(1, len(needs_extraction)) * 100:.1f}%")
    print()
    print("🎉 Next step:")
    print("   Run: python scripts/run_hybrid_classification_v23.py")


if __name__ == "__main__":
    main()
