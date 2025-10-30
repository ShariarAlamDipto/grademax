#!/usr/bin/env python3
"""
Complete Physics Processing Pipeline
1. Split PDFs into individual questions
2. Upload to Supabase storage
3. Create database records
4. Classify using dual API (Groq + OpenRouter)
"""

import os
import sys
import time
from pathlib import Path
from supabase import create_client
from dotenv import load_dotenv
import json

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from scripts.splitting_config_loader import SplittingConfigLoader, ConfigurableQuestionDetector
from scripts.reprocess_all_papers_configurable import ConfigurablePaperProcessor
from scripts.mistral_classifier import MistralTopicClassifier

# Load environment variables
env_path = project_root / '.env.local'
load_dotenv(env_path)

# Initialize Supabase client
supabase_url = os.getenv("NEXT_PUBLIC_SUPABASE_URL")
supabase_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
supabase = create_client(supabase_url, supabase_key)

# Physics subject ID
PHYSICS_SUBJECT_ID = "0b142517-d35d-4942-91aa-b4886aaabca3"
RAW_DATA_PATH = Path("data/raw/IGCSE/Physics")
PROCESSED_DATA_PATH = Path("data/processed/Physics Processed")


def split_all_physics_papers():
    """Step 1: Split all Physics PDFs into individual questions"""
    print("="*70)
    print("STEP 1: SPLITTING PHYSICS PAPERS INTO QUESTIONS")
    print("="*70)
    
    # Load Physics config
    config_loader = SplittingConfigLoader()
    physics_config = config_loader.get_config("Physics")
    
    if not physics_config:
        print("ERROR: Physics configuration not found!")
        return False
    
    total_papers = 0
    total_questions = 0
    
    # Walk through years
    for year_dir in sorted(RAW_DATA_PATH.iterdir()):
        if not year_dir.is_dir():
            continue
        
        try:
            year = int(year_dir.name)
        except ValueError:
            continue
        
        print(f"\n[YEAR] {year}")
        
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
            for paper_num, files in papers.items():
                if not files['qp']:
                    continue
                
                # Create output directory with Phy_ prefix
                output_name = f"Phy_{year}_{season}_{paper_num}"
                output_dir = PROCESSED_DATA_PATH / output_name
                
                print(f"  [PAPER] {output_name}")
                print(f"    QP: {files['qp'].name}")
                print(f"    MS: {files['ms'].name if files['ms'] else 'Not found'}")
                
                try:
                    processor = ConfigurablePaperProcessor(
                        qp_path=files['qp'],
                        ms_path=files['ms'],
                        output_dir=output_dir,
                        config=physics_config,
                        year=year
                    )
                    manifest = processor.process()
                    
                    total_papers += 1
                    total_questions += manifest['total_questions']
                    
                    print(f"    ✅ Split into {manifest['total_questions']} questions")
                    print(f"    ✅ {manifest['questions_with_markschemes']} with markschemes")
                    
                except Exception as e:
                    print(f"    ❌ Error: {e}")
    
    print(f"\n{'='*70}")
    print(f"SPLITTING COMPLETE: {total_papers} papers, {total_questions} questions")
    print(f"{'='*70}\n")
    
    return True


def upload_to_storage_and_create_records():
    """Step 2: Upload to Supabase storage and create database records"""
    print("="*70)
    print("STEP 2: UPLOADING TO STORAGE & CREATING DATABASE RECORDS")
    print("="*70)
    
    total_papers = 0
    total_pages = 0
    
    # Walk through processed folders
    for paper_dir in sorted(PROCESSED_DATA_PATH.iterdir()):
        if not paper_dir.is_dir():
            continue
        
        # Parse folder name: Phy_2011_May-Jun_1P
        parts = paper_dir.name.split('_')
        if len(parts) < 4 or parts[0] != 'Phy':
            continue
        
        year = int(parts[1])
        season = parts[2]
        paper_number = parts[3]
        
        print(f"\n[PAPER] {paper_dir.name}")
        
        # Read manifest
        manifest_file = paper_dir / "manifest.json"
        if not manifest_file.exists():
            print(f"  ⚠️  No manifest found, skipping")
            continue
        
        with open(manifest_file, 'r') as f:
            manifest = json.load(f)
        
        # Create or get paper record
        try:
            result = supabase.table("papers").select("id, total_pages").eq(
                "subject_id", PHYSICS_SUBJECT_ID
            ).eq("year", year).eq("season", season).eq("paper_number", paper_number).execute()
            
            if result.data and len(result.data) > 0:
                paper_id = result.data[0]['id']
                print(f"  📄 Paper exists (ID: {paper_id})")
            else:
                paper_data = {
                    "subject_id": PHYSICS_SUBJECT_ID,
                    "year": year,
                    "season": season,
                    "paper_number": paper_number,
                    "total_pages": 0
                }
                result = supabase.table("papers").insert(paper_data).execute()
                paper_id = result.data[0]['id']
                print(f"  ✅ Created paper (ID: {paper_id})")
        
        except Exception as e:
            print(f"  ❌ Error creating paper: {e}")
            continue
        
        # Process each question
        pages_dir = paper_dir / "pages"
        if not pages_dir.exists():
            print(f"  ⚠️  No pages directory")
            continue
        
        question_count = 0
        for question in manifest.get('questions', []):
            q_num = question['question_number']
            qp_file = pages_dir / f"q{q_num}.pdf"
            
            if not qp_file.exists():
                continue
            
            # Read PDF bytes
            with open(qp_file, 'rb') as f:
                qp_bytes = f.read()
            
            # Upload question PDF
            storage_path = f"subjects/Physics/pages/{paper_dir.name}/q{q_num}.pdf"
            try:
                supabase.storage.from_("question-pdfs").upload(
                    storage_path,
                    qp_bytes,
                    {"content-type": "application/pdf", "upsert": "true"}
                )
                qp_url = supabase.storage.from_("question-pdfs").get_public_url(storage_path)
            except Exception as e:
                print(f"  ⚠️  Upload failed for q{q_num}: {e}")
                continue
            
            # Upload markscheme if exists
            ms_url = None
            ms_file = paper_dir / "markschemes" / f"q{q_num}_ms.pdf"
            if ms_file.exists():
                with open(ms_file, 'rb') as f:
                    ms_bytes = f.read()
                
                ms_storage_path = f"subjects/Physics/pages/{paper_dir.name}/q{q_num}_ms.pdf"
                try:
                    supabase.storage.from_("question-pdfs").upload(
                        ms_storage_path,
                        ms_bytes,
                        {"content-type": "application/pdf", "upsert": "true"}
                    )
                    ms_url = supabase.storage.from_("question-pdfs").get_public_url(ms_storage_path)
                except Exception as e:
                    pass
            
            # Extract text excerpt (first 500 chars from question text if available)
            text_excerpt = question.get('text', '')[:500] if question.get('text') else ""
            
            # Create page record
            try:
                # Check if page already exists
                result = supabase.table("pages").select("id").eq(
                    "paper_id", paper_id
                ).eq("question_number", int(q_num)).execute()
                
                if result.data and len(result.data) > 0:
                    # Update existing page
                    supabase.table("pages").update({
                        "qp_page_url": qp_url,
                        "ms_page_url": ms_url,
                        "text_excerpt": text_excerpt
                    }).eq("id", result.data[0]['id']).execute()
                else:
                    # Create new page
                    page_data = {
                        "paper_id": paper_id,
                        "page_number": int(q_num),
                        "question_number": int(q_num),
                        "qp_page_url": qp_url,
                        "ms_page_url": ms_url,
                        "text_excerpt": text_excerpt,
                        "topics": []
                    }
                    supabase.table("pages").insert(page_data).execute()
                
                question_count += 1
                
            except Exception as e:
                print(f"  ⚠️  Database error for q{q_num}: {e}")
                continue
        
        # Update paper total_pages
        supabase.table("papers").update({"total_pages": question_count}).eq("id", paper_id).execute()
        
        print(f"  ✅ Uploaded {question_count} questions")
        total_papers += 1
        total_pages += question_count
    
    print(f"\n{'='*70}")
    print(f"UPLOAD COMPLETE: {total_papers} papers, {total_pages} questions")
    print(f"{'='*70}\n")
    
    return True


def classify_all_physics_pages():
    """Step 3: Classify all Physics pages using dual API"""
    print("="*70)
    print("STEP 3: CLASSIFYING PHYSICS PAGES")
    print("="*70)
    
    # Initialize classifier
    groq_key = os.getenv('GROQ_API_KEY')
    openrouter_key = os.getenv('OPENROUTER_API_KEY')
    
    if not groq_key and not openrouter_key:
        print("ERROR: At least one API key is required!")
        return False
    
    print(f"[INIT] Groq API: {'Available' if groq_key else 'Not available'}")
    print(f"[INIT] OpenRouter API: {'Available' if openrouter_key else 'Not available'}")
    
    classifier = MistralTopicClassifier(
        "classification/physics_topics.yaml",
        groq_key,
        openrouter_key
    )
    print(f"[INIT] Classifier ready with {len(classifier.topics)} topics")
    print(f"[INIT] Available models: {len(classifier.available_models)}\n")
    
    # Get all Physics papers
    result = supabase.table("papers").select("id, year, season, paper_number").eq(
        "subject_id", PHYSICS_SUBJECT_ID
    ).execute()
    
    papers = result.data
    print(f"Found {len(papers)} Physics papers to classify\n")
    
    total_classified = 0
    total_pages = 0
    
    for paper in papers:
        paper_id = paper['id']
        paper_name = f"Phy_{paper['year']}_{paper['season']}_{paper['paper_number']}"
        
        print(f"[PAPER] {paper_name}")
        
        # Get all pages for this paper that don't have topics
        result = supabase.table("pages").select("id, question_number, text_excerpt, topics").eq(
            "paper_id", paper_id
        ).execute()
        
        pages = result.data
        unclassified = [p for p in pages if not p.get('topics') or len(p['topics']) == 0]
        
        if len(unclassified) == 0:
            print(f"  ✅ All {len(pages)} pages already classified")
            continue
        
        print(f"  Classifying {len(unclassified)}/{len(pages)} pages...")
        
        for i, page in enumerate(unclassified, 1):
            try:
                text = page['text_excerpt'] or ""
                result = classifier.classify(text)
                
                # Extract topic from TopicClassification object
                if hasattr(result, 'topic'):
                    topics = [result.topic] if result.topic else []
                else:
                    topics = result if isinstance(result, list) else []
                
                if topics:
                    supabase.table("pages").update({"topics": topics}).eq("id", page['id']).execute()
                    total_classified += 1
                    print(f"    [{i}/{len(unclassified)}] Q{page['question_number']}: {topics}")
                else:
                    print(f"    [{i}/{len(unclassified)}] Q{page['question_number']}: No topics")
                
                # 5-second delay between classifications
                if i < len(unclassified):
                    time.sleep(5)
                
            except Exception as e:
                print(f"    ⚠️  Error Q{page['question_number']}: {e}")
        
        total_pages += len(pages)
    
    print(f"\n{'='*70}")
    print(f"CLASSIFICATION COMPLETE: {total_classified}/{total_pages} pages classified")
    print(f"{'='*70}\n")
    
    return True


def main():
    """Run complete Physics processing pipeline"""
    print("\n" + "="*70)
    print("COMPLETE PHYSICS PROCESSING PIPELINE")
    print("="*70)
    print("\nThis will:")
    print("  1. Split all Physics PDFs into individual questions")
    print("  2. Upload to Supabase storage with Phy_ prefix")
    print("  3. Create database records")
    print("  4. Classify all pages using dual API (Groq + OpenRouter)")
    print("\n" + "="*70 + "\n")
    
    start_time = time.time()
    
    # Step 1: Split PDFs
    if not split_all_physics_papers():
        print("❌ Splitting failed!")
        return
    
    # Step 2: Upload and create records
    if not upload_to_storage_and_create_records():
        print("❌ Upload failed!")
        return
    
    # Step 3: Classify
    if not classify_all_physics_pages():
        print("❌ Classification failed!")
        return
    
    elapsed = time.time() - start_time
    print(f"\n✅ COMPLETE PIPELINE FINISHED in {elapsed/60:.1f} minutes")


if __name__ == "__main__":
    main()
