#!/usr/bin/env python3
"""
SIMPLIFIED Ingestion Pipeline v2
- ONE topic per question
- PDFs organized by topic folder: topics/1/Q2.pdf
- Straightforward processing
"""

import os
import sys
import json
import time
import re
import fitz  # PyMuPDF
from pathlib import Path
from dotenv import load_dotenv

# Add scripts to path
sys.path.insert(0, str(Path(__file__).parent))

from split_pages import PageSplitter
from single_topic_classifier import SingleTopicClassifier
from supabase_client import SupabaseClient

load_dotenv()


def extract_paper_metadata(pdf_path: str) -> dict:
    """Extract metadata from filename like: 4PH1_Jun19_QP_1P.pdf"""
    filename = Path(pdf_path).stem
    
    # Try to parse filename
    match = re.search(r'(\w+)_(\w+)(\d{2})_QP_(\w+)', filename)
    if match:
        subject_code, season, year, paper_num = match.groups()
        full_year = f"20{year}"
        return {
            'subject_code': subject_code,
            'season': season,
            'year': int(full_year),
            'paper_number': paper_num,
            'paper_id': f"{full_year}_{season}_{paper_num}"
        }
    
    # Fallback
    return {
        'subject_code': 'Unknown',
        'season': 'Unknown',
        'year': 2019,
        'paper_number': '1P',
        'paper_id': Path(pdf_path).stem
    }


def process_paper(input_pdf: str):
    """
    Process a single past paper
    
    Steps:
    1. Split PDF by question using PageSplitter
    2. Classify each question with ONE topic
    3. Upload PDF to storage: topics/{code}/Q{num}.pdf
    4. Store in database with single topic link
    """
    
    input_path = Path(input_pdf)
    if not input_path.exists():
        print(f"❌ PDF not found: {input_pdf}")
        return False
    
    # Extract metadata
    metadata = extract_paper_metadata(str(input_path))
    paper_id = metadata['paper_id']
    
    # Setup output directory
    output_dir = Path("data/processed") / paper_id
    output_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"\n{'='*70}")
    print(f"📄 Processing: {paper_id}")
    print(f"   Input: {input_pdf}")
    print(f"   Output: {output_dir}")
    print(f"{'='*70}")
    
    # ==================================================================
    # STEP 1: Split PDF by question
    # ==================================================================
    print(f"\n⚙️  STEP 1: Splitting PDF by question...")
    
    pages_dir = output_dir / "pages"
    pages_dir.mkdir(exist_ok=True)
    
    # Use PageSplitter
    splitter = PageSplitter(str(input_path), str(pages_dir))
    manifest = splitter.process_paper(paper_id, metadata)
    
    if not manifest.questions:
        print(f"❌ No questions found!")
        return False
    
    print(f"✅ Found {len(manifest.questions)} questions")
    
    # ==================================================================
    # STEP 2: Classify each question with ONE topic
    # ==================================================================
    print(f"\n🤖 STEP 2: Classifying questions...")
    
    api_key = os.getenv('GEMINI_API_KEY')
    if not api_key:
        print(f"❌ GEMINI_API_KEY not set!")
        return False
    
    topics_yaml = "config/physics_topics.yaml"
    classifier = SingleTopicClassifier(topics_yaml, api_key)
    
    classified_questions = []
    
    for q in manifest.questions:
        q_num = q['question_number']
        print(f"\n📝 Question {q_num}:")
        
        # Read page PDF and extract text
        q_pdf_path = pages_dir / f"q{q_num}.pdf"
        if not q_pdf_path.exists():
            print(f"   ⚠️  PDF not found, skipping")
            continue
        
        # Extract text from PDF
        try:
            doc = fitz.open(str(q_pdf_path))
            page_text = ""
            for page in doc:
                page_text += page.get_text()
            doc.close()
            
            # Truncate to 3000 chars for API
            page_text = page_text[:3000]
        except Exception as e:
            print(f"   ⚠️  Failed to extract text: {e}")
            continue
        
        # Classify with Gemini
        try:
            classification = classifier.classify(page_text, q_num)
            
            if not classification.page_has_question:
                print(f"   ⏭️  No question detected, skipping")
                continue
            
            print(f"   Topic: {classification.topic}")
            print(f"   Difficulty: {classification.difficulty}")
            print(f"   Confidence: {classification.confidence:.2f}")
            
            # Add to results
            classified_questions.append({
                'question_number': q_num,
                'topic_code': classification.topic,
                'difficulty': classification.difficulty,
                'confidence': classification.confidence,
                'pdf_path': str(q_pdf_path),
                'text_excerpt': page_text[:500]
            })
            
        except Exception as e:
            print(f"   ❌ Classification failed: {e}")
            continue
    
    print(f"\n✅ Classified {len(classified_questions)} questions")
    
    # ==================================================================
    # STEP 3: Upload PDFs to storage (organized by topic)
    # ==================================================================
    print(f"\n☁️  STEP 3: Uploading PDFs to storage...")
    
    db = SupabaseClient()
    uploaded = []
    
    for q in classified_questions:
        q_num = q['question_number']
        topic_code = q['topic_code']
        pdf_path = q['pdf_path']
        
        # Storage path: topics/1/Q2.pdf
        storage_path = f"topics/{topic_code}/Q{q_num}.pdf"
        
        try:
            # Upload to storage
            result = db.upload_file(
                bucket='question-pdfs',
                file_path=pdf_path,
                destination_path=storage_path
            )
            
            print(f"   ✅ Q{q_num} → {storage_path}")
            
            q['storage_path'] = storage_path
            uploaded.append(q)
            
        except Exception as e:
            print(f"   ❌ Q{q_num} upload failed: {e}")
            continue
    
    print(f"\n✅ Uploaded {len(uploaded)} PDFs")
    
    # ==================================================================
    # STEP 4: Store in database
    # ==================================================================
    print(f"\n💾 STEP 4: Storing in database...")
    
    # First, ensure paper exists
    try:
        paper_data = {
            'board': 'Edexcel',
            'level': 'IGCSE',
            'subject_code': metadata['subject_code'],
            'year': metadata['year'],
            'season': metadata['season'],
            'paper_number': metadata['paper_number']
        }
        
        # Find existing paper
        filters = {
            'year': f'eq.{metadata["year"]}',
            'season': f'eq.{metadata["season"]}',
            'paper_number': f'eq.{metadata["paper_number"]}'
        }
        existing = db.select('papers', filters=filters)
        
        if existing and len(existing) > 0:
            print(f"   📄 Paper exists (ID: {existing[0]['id']})")
            paper_uuid = existing[0]['id']
        else:
            print(f"   📄 Creating paper record...")
            result = db.insert('papers', paper_data)
            if result and len(result) > 0:
                paper_uuid = result[0]['id']
            else:
                print(f"   ❌ Failed to create paper")
                return False
            
    except Exception as e:
        print(f"   ⚠️  Paper handling: {e}")
        return False
    
    # Insert questions with single topic
    for q in uploaded:
        q_num = q['question_number']
        topic_code = q['topic_code']
        storage_path = q['storage_path']
        
        try:
            question_data = {
                'paper_id': paper_uuid,  # Use UUID
                'question_number': q_num,
                'page_pdf_url': storage_path,
                'ms_pdf_url': None,  # TODO: Handle mark scheme
                'text': q['text_excerpt'],
                'has_diagram': True,  # Assume true for now
                'difficulty': q['difficulty'],
                'classification_confidence': q['confidence']
            }
            
            # Insert question
            result = db.insert('questions', question_data)
            
            if result and len(result) > 0:
                question_id = result[0]['id']
                
                # Link to single topic
                topic_link = {
                    'question_id': question_id,
                    'topic_code': topic_code
                }
                
                db.insert('question_topics', topic_link)
                
                print(f"   ✅ Q{q_num} → Topic {topic_code}")
            
        except Exception as e:
            print(f"   ❌ Q{q_num} database insert failed: {e}")
            continue
    
    print(f"\n✅ Stored {len(uploaded)} questions in database")
    print(f"\n{'='*70}")
    print(f"🎉 Processing complete!")
    print(f"{'='*70}")
    
    return True


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python simple_ingest_v2.py <path-to-pdf>")
        print("Example: python simple_ingest_v2.py data/raw/IGCSE/4PH1/2019/Jun/4PH1_Jun19_QP_1P.pdf")
        sys.exit(1)
    
    input_pdf = sys.argv[1]
    success = process_paper(input_pdf)
    
    sys.exit(0 if success else 1)
