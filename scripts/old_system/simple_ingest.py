#!/usr/bin/env python3
"""
SIMPLIFIED Ingestion Pipeline
- ONE topic per question
- PDFs organized by topic folder
- Straightforward processing
"""

import os
import sys
import json
import time
from pathlib import Path
from dotenv import load_dotenv

# Add scripts to path
sys.path.insert(0, str(Path(__file__).parent))

from split_pages import PageSplitter
from single_topic_classifier import SingleTopicClassifier
from supabase_client import SupabaseClient

load_dotenv()


def process_paper(input_pdf: str, output_dir: str = "data/processed"):
    """
    Process a single past paper
    
    Args:
        input_pdf: Path to question paper PDF
        output_dir: Where to save processed data
    """
    print("="*70)
    print("📚 GRADEMAX INGESTION - SIMPLIFIED")
    print("="*70)
    
    input_path = Path(input_pdf)
    if not input_path.exists():
        print(f"❌ File not found: {input_pdf}")
        return False
    
    # Extract paper info from path
    # Expected: data/raw/IGCSE/4PH1/2019/Jun/4PH1_Jun19_QP_1P.pdf
    paper_code = "4PH1"  # Hard-coded for now
    year = None
    season = None
    
    for part in input_path.parts:
        if part.isdigit() and len(part) == 4:
            year = part
        if part in ['Jun', 'Nov', 'Mar']:
            season = part
    
    if not year or not season:
        print(f"❌ Cannot extract year/season from path")
        return False
    
    paper_id = f"{paper_code}_{year}_{season}_1P"
    output_path = Path(output_dir) / paper_id
    output_path.mkdir(parents=True, exist_ok=True)
    
    print(f"\n📄 Processing: {paper_id}")
    print(f"   Input: {input_pdf}")
    print(f"   Output: {output_path}")
    
    # ==================================================================
    # STEP 1: Split PDF by question
    # ==================================================================
    print(f"\n⚙️  STEP 1: Splitting PDF by question...")
    
    pages_dir = output_path / "pages"
    pages_dir.mkdir(exist_ok=True)
    
    questions = split_pdf_by_question(str(input_path), str(pages_dir))
    
    if not questions:
        print(f"❌ No questions found!")
        return False
    
    print(f"✅ Found {len(questions)} questions")
    
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
    
    for q in questions:
        q_num = q['question_number']
        print(f"\n📝 Question {q_num}:")
        
        # Read page text
        page_path = Path(q['pdf_path'])
        if not page_path.exists():
            print(f"   ⚠️  PDF not found, skipping")
            continue
        
        # Extract text (simplified - just use question number context)
        page_text = f"Question {q_num}"  # In real system, extract from PDF
        
        # Classify
        classification = classifier.classify(page_text, q_num)
        
        if not classification.page_has_question:
            print(f"   ⏭️  No question detected, skipping")
            continue
        
        print(f"   Topic: {classification.topic}")
        print(f"   Difficulty: {classification.difficulty}")
        print(f"   Confidence: {classification.confidence:.2f}")
        
        classified_questions.append({
            'question_number': q_num,
            'pdf_path': str(page_path),
            'topic': classification.topic,
            'difficulty': classification.difficulty,
            'confidence': classification.confidence
        })
    
    if not classified_questions:
        print(f"\n❌ No questions classified!")
        return False
    
    print(f"\n✅ Classified {len(classified_questions)} questions")
    
    # ==================================================================
    # STEP 3: Upload PDFs to storage by topic
    # ==================================================================
    print(f"\n☁️  STEP 3: Uploading to storage...")
    
    db = SupabaseClient()
    bucket = 'question-pdfs'
    
    for q in classified_questions:
        topic = q['topic']
        q_num = q['question_number']
        local_path = q['pdf_path']
        
        # Storage path: topics/1/Q2.pdf, topics/5/Q7.pdf
        storage_path = f"topics/{topic}/Q{q_num}.pdf"
        
        try:
            db.upload_file(bucket, local_path, storage_path)
            q['storage_url'] = storage_path
            print(f"   ✅ Q{q_num} → topics/{topic}/")
        except Exception as e:
            print(f"   ❌ Q{q_num} upload failed: {e}")
            q['storage_url'] = None
    
    # ==================================================================
    # STEP 4: Store in database
    # ==================================================================
    print(f"\n💾 STEP 4: Storing in database...")
    
    # Get or create paper
    paper_uuid = db.get_or_create_paper(
        subject_code=paper_code,
        year=year,
        season=season,
        paper_number="1P"
    )
    
    print(f"   Paper UUID: {paper_uuid}")
    
    # Insert questions with SINGLE topic
    for q in classified_questions:
        if not q.get('storage_url'):
            continue
        
        try:
            # Simple insert with ONE topic
            db.insert_question_with_topics(
                paper_id=paper_uuid,
                question_number=q['question_number'],
                text="",  # Not extracting text anymore
                difficulty={1: 'easy', 2: 'medium', 3: 'hard'}.get(
                    {'easy': 1, 'medium': 2, 'hard': 3}[q['difficulty']], 2
                ),
                qp_page_index=0,
                qp_page_count=1,
                page_pdf_url=q['storage_url'],
                has_diagram=True,  # Assume all have diagrams since they're full pages
                classification_confidence=q['confidence'],
                topics=[{
                    'topic_code': q['topic'],
                    'confidence': q['confidence'],
                    'method': 'llm_single'
                }]
            )
            print(f"   ✅ Q{q['question_number']} stored")
        except Exception as e:
            print(f"   ❌ Q{q['question_number']} failed: {e}")
    
    print(f"\n🎉 COMPLETE!")
    print(f"   Processed {len(classified_questions)} questions")
    print(f"   Paper: {paper_id}")
    print("="*70)
    
    return True


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python simple_ingest.py <pdf_path>")
        print("Example: python simple_ingest.py data/raw/IGCSE/4PH1/2019/Jun/4PH1_Jun19_QP_1P.pdf")
        sys.exit(1)
    
    success = process_paper(sys.argv[1])
    sys.exit(0 if success else 1)
