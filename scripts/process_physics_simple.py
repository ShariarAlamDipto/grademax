#!/usr/bin/env python3
"""
Simple Physics Page-by-Page Processor
- Extracts EVERY page from QP and MS as separate PDFs
- Uploads to storage
- Creates database records
- Classifies using dual API

This is the SIMPLEST, most RELIABLE approach - no complex question detection
"""

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

# Load environment variables
env_path = project_root / '.env.local'
load_dotenv(env_path)

# Initialize Supabase
supabase_url = os.getenv("NEXT_PUBLIC_SUPABASE_URL")
supabase_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
supabase = create_client(supabase_url, supabase_key)

# Physics subject ID
PHYSICS_SUBJECT_ID = "0b142517-d35d-4942-91aa-b4886aaabca3"
RAW_DATA_PATH = Path("data/raw/IGCSE/Physics")
PROCESSED_DATA_PATH = Path("data/processed/Physics Processed")


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
        print(f"Error extracting page {page_num}: {e}")
        return None


def extract_text_from_pdf(pdf_path, page_num):
    """Extract text from a specific page."""
    try:
        with pdfplumber.open(pdf_path) as pdf:
            if page_num < len(pdf.pages):
                page = pdf.pages[page_num]
                text = page.extract_text()
                return text if text else ""
    except Exception as e:
        print(f"Error extracting text: {e}")
    return ""


def process_all_physics_papers():
    """Process all Physics papers page by page."""
    print("="*70)
    print("SIMPLE PHYSICS PAGE-BY-PAGE PROCESSOR")
    print("="*70)
    print("\nThis will:")
    print("  1. Extract EVERY page from QP and MS as separate PDFs")
    print("  2. Upload to Supabase storage")
    print("  3. Create database records")
    print("  4. Classify all pages\n")
    
    # Initialize classifier
    groq_key = os.getenv('GROQ_API_KEY')
    openrouter_key = os.getenv('OPENROUTER_API_KEY')
    
    if not groq_key and not openrouter_key:
        print("ERROR: At least one API key required!")
        return
    
    print(f"[INIT] Groq API: {'Available' if groq_key else 'Not available'}")
    print(f"[INIT] OpenRouter API: {'Available' if openrouter_key else 'Not available'}")
    
    classifier = MistralTopicClassifier(
        "classification/physics_topics.yaml",
        groq_key,
        openrouter_key
    )
    print(f"[INIT] Classifier ready with {len(classifier.topics)} topics")
    print(f"[INIT] Models: {len(classifier.available_models)}\n")
    
    total_papers = 0
    total_pages = 0
    total_classified = 0
    
    # Walk through years
    for year_dir in sorted(RAW_DATA_PATH.iterdir()):
        if not year_dir.is_dir():
            continue
        
        try:
            year = int(year_dir.name)
        except ValueError:
            continue
        
        print(f"\n{'='*70}")
        print(f"[YEAR] {year}")
        print('='*70)
        
        # Walk through seasons
        for season_dir in sorted(year_dir.iterdir()):
            if not season_dir.is_dir():
                continue
            
            season = season_dir.name
            
            # Find paper files
            pdf_files = list(season_dir.glob("*.pdf"))
            
            # Group by paper number
            papers = {}
            for pdf_file in pdf_files:
                name = pdf_file.stem
                
                # Determine paper number
                paper_num = None
                if "Paper 1" in name or "Paper_1" in name:
                    paper_num = "1P"
                elif "Paper 2" in name or "Paper_2" in name:
                    paper_num = "2P"
                else:
                    continue
                
                # Check if it's QP or MS
                if "_MS" in name:
                    if paper_num not in papers:
                        papers[paper_num] = {'qp': None, 'ms': None}
                    papers[paper_num]['ms'] = pdf_file
                else:
                    if paper_num not in papers:
                        papers[paper_num] = {'qp': None, 'ms': None}
                    papers[paper_num]['qp'] = pdf_file
            
            # Process each paper
            for paper_num, files in sorted(papers.items()):
                if not files['qp']:
                    continue
                
                paper_name = f"Phy_{year}_{season}_{paper_num}"
                print(f"\n[PAPER] {paper_name}")
                print(f"  QP: {files['qp'].name}")
                print(f"  MS: {files['ms'].name if files['ms'] else 'Not found'}")
                
                try:
                    # Create or get paper record
                    result = supabase.table("papers").select("id").eq(
                        "subject_id", PHYSICS_SUBJECT_ID
                    ).eq("year", year).eq("season", season).eq("paper_number", paper_num).execute()
                    
                    if result.data and len(result.data) > 0:
                        paper_id = result.data[0]['id']
                        print(f"  Paper exists (ID: {paper_id})")
                        
                        # Delete existing pages for this paper
                        supabase.table("pages").delete().eq("paper_id", paper_id).execute()
                        print(f"  Cleared old pages")
                    else:
                        paper_data = {
                            "subject_id": PHYSICS_SUBJECT_ID,
                            "year": year,
                            "season": season,
                            "paper_number": paper_num,
                            "total_pages": 0
                        }
                        result = supabase.table("papers").insert(paper_data).execute()
                        paper_id = result.data[0]['id']
                        print(f"  Created paper (ID: {paper_id})")
                    
                    # Read QP and MS
                    qp_reader = PdfReader(files['qp'])
                    ms_reader = PdfReader(files['ms']) if files['ms'] and files['ms'].exists() else None
                    
                    qp_page_count = len(qp_reader.pages)
                    ms_page_count = len(ms_reader.pages) if ms_reader else 0
                    
                    print(f"  QP: {qp_page_count} pages, MS: {ms_page_count} pages")
                    
                    # Create processed folder
                    processed_folder = PROCESSED_DATA_PATH / paper_name
                    processed_folder.mkdir(parents=True, exist_ok=True)
                    (processed_folder / "pages").mkdir(exist_ok=True)
                    (processed_folder / "markschemes").mkdir(exist_ok=True)
                    
                    # Storage folder
                    storage_folder = f"subjects/Physics/pages/{paper_name}"
                    
                    # Process each QP page
                    pages_created = 0
                    for page_num in range(qp_page_count):
                        try:
                            # Extract page as PDF
                            page_pdf_bytes = extract_page_as_pdf(files['qp'], page_num)
                            if not page_pdf_bytes:
                                continue
                            
                            # Save to processed folder
                            qp_file = processed_folder / "pages" / f"p{page_num + 1}.pdf"
                            with open(qp_file, 'wb') as f:
                                f.write(page_pdf_bytes)
                            
                            # Extract text
                            text_excerpt = extract_text_from_pdf(files['qp'], page_num)
                            text_excerpt = text_excerpt[:500] if text_excerpt else ""
                            
                            # Upload question page
                            qp_storage_path = f"{storage_folder}/p{page_num + 1}.pdf"
                            try:
                                supabase.storage.from_("question-pdfs").upload(
                                    qp_storage_path,
                                    page_pdf_bytes,
                                    {"content-type": "application/pdf", "upsert": "true"}
                                )
                                qp_url = supabase.storage.from_("question-pdfs").get_public_url(qp_storage_path)
                            except Exception as e:
                                print(f"    Upload error p{page_num + 1}: {e}")
                                continue
                            
                            # Upload corresponding MS page if available
                            ms_url = None
                            if ms_reader and page_num < ms_page_count:
                                ms_page_pdf_bytes = extract_page_as_pdf(files['ms'], page_num)
                                if ms_page_pdf_bytes:
                                    # Save to processed folder
                                    ms_file = processed_folder / "markschemes" / f"p{page_num + 1}_ms.pdf"
                                    with open(ms_file, 'wb') as f:
                                        f.write(ms_page_pdf_bytes)
                                    
                                    # Upload
                                    ms_storage_path = f"{storage_folder}/p{page_num + 1}_ms.pdf"
                                    try:
                                        supabase.storage.from_("question-pdfs").upload(
                                            ms_storage_path,
                                            ms_page_pdf_bytes,
                                            {"content-type": "application/pdf", "upsert": "true"}
                                        )
                                        ms_url = supabase.storage.from_("question-pdfs").get_public_url(ms_storage_path)
                                    except:
                                        pass
                            
                            # Create page record
                            page_data = {
                                "paper_id": paper_id,
                                "page_number": page_num + 1,
                                "question_number": page_num + 1,
                                "qp_page_url": qp_url,
                                "ms_page_url": ms_url,
                                "text_excerpt": text_excerpt,
                                "topics": []
                            }
                            
                            supabase.table("pages").insert(page_data).execute()
                            pages_created += 1
                            
                            if (page_num + 1) % 10 == 0:
                                print(f"    Processed {page_num + 1}/{qp_page_count} pages")
                        
                        except Exception as e:
                            print(f"    Error page {page_num + 1}: {e}")
                            continue
                    
                    # Update paper total_pages
                    supabase.table("papers").update({"total_pages": pages_created}).eq("id", paper_id).execute()
                    
                    print(f"  Created {pages_created} page records")
                    
                    # Classify pages
                    print(f"  Classifying {pages_created} pages...")
                    
                    result = supabase.table("pages").select("id, text_excerpt").eq("paper_id", paper_id).execute()
                    pages = result.data
                    
                    classified_count = 0
                    for i, page in enumerate(pages, 1):
                        try:
                            text = page['text_excerpt'] or ""
                            result = classifier.classify(text)
                            
                            # Extract topic
                            if hasattr(result, 'topic'):
                                topics = [result.topic] if result.topic else []
                            else:
                                topics = result if isinstance(result, list) else []
                            
                            if topics:
                                supabase.table("pages").update({"topics": topics}).eq("id", page['id']).execute()
                                classified_count += 1
                            
                            if i % 10 == 0:
                                print(f"    Classified {i}/{len(pages)}")
                            
                            # 5-second delay
                            if i < len(pages):
                                time.sleep(5)
                        
                        except Exception as e:
                            print(f"    Classification error: {e}")
                    
                    print(f"  Classified {classified_count}/{len(pages)} pages")
                    
                    total_papers += 1
                    total_pages += pages_created
                    total_classified += classified_count
                
                except Exception as e:
                    print(f"  ERROR: {e}")
                    continue
    
    print(f"\n{'='*70}")
    print(f"COMPLETE!")
    print(f"  Papers: {total_papers}")
    print(f"  Pages: {total_pages}")
    print(f"  Classified: {total_classified}")
    print(f"{'='*70}\n")


if __name__ == "__main__":
    process_all_physics_papers()
