#!/usr/bin/env python3
"""
Complete Mathematics B Processing Pipeline

This script:
1. Reads raw PDF papers (not pre-segmented)
2. Extracts questions directly from full papers
3. Classifies using the smart hybrid classifier
4. Stores everything in the database

This approach is better because:
- No pre-segmentation errors
- Full question context preserved
- Faster (fewer files to process)
- More accurate classification
"""

import os
import sys
import json
import time
import re
from pathlib import Path
from dataclasses import dataclass
from typing import List, Dict, Tuple, Optional

import fitz  # PyMuPDF
from dotenv import load_dotenv
from supabase import create_client, Client

# Add scripts to path
sys.path.insert(0, str(Path(__file__).parent))
from smart_classifier import HybridClassifier, ClassificationResult

# Load environment
load_dotenv('.env.local')
load_dotenv('.env.ingest')

SUPABASE_URL = os.getenv("NEXT_PUBLIC_SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    print("Missing Supabase credentials")
    sys.exit(1)

# Initialize
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# Paths
RAW_DIR = Path(__file__).parent.parent / "data" / "raw" / "IGCSE" / "Maths B"
TOPICS_YAML = Path(__file__).parent.parent / "classification" / "maths_b_topics.yaml"
SUBJECT_CODE = "4MB1"


@dataclass
class ExtractedQuestion:
    """A question extracted from a paper"""
    number: str
    text: str
    page_start: int
    page_end: int
    marks: Optional[int] = None


def extract_questions_from_pdf(pdf_path: Path) -> List[ExtractedQuestion]:
    """
    Extract all questions from a paper PDF
    
    Detects question starts based on:
    - Number at start of line followed by content
    - Handles multi-page questions
    """
    doc = fitz.open(str(pdf_path))
    questions = []
    
    current_q = None
    current_text = []
    current_start_page = None
    
    for page_num in range(len(doc)):
        page = doc[page_num]
        text = page.get_text()
        lines = text.split('\n')
        
        for line in lines:
            line_stripped = line.strip()
            
            # Skip empty lines and common non-question content
            if not line_stripped:
                continue
            if any(skip in line for skip in [
                '*P', '......', 'DO NOT WRITE', 'Turn over', 
                'Leave blank', 'Total for Question', 'BLANK PAGE',
                'Pearson Edexcel', 'Paper Reference', 'Centre Number',
                'Candidate Number'
            ]):
                continue
            
            # Check for new question start
            # Pattern: number followed by text or (a)
            match = re.match(r'^\s*(\d{1,2})\s+(?:[A-Z(]|\()', line)
            if match:
                q_num = match.group(1)
                try:
                    num_val = int(q_num)
                    # Reasonable question number (1-30 for Math B Paper 1)
                    if 1 <= num_val <= 30:
                        # Check it's not a page number (usually standalone)
                        if len(line_stripped) > 5:  # Not just "3" alone
                            # Save previous question
                            if current_q is not None:
                                questions.append(ExtractedQuestion(
                                    number=current_q,
                                    text='\n'.join(current_text),
                                    page_start=current_start_page,
                                    page_end=page_num
                                ))
                            
                            # Start new question
                            current_q = q_num
                            current_text = [line]
                            current_start_page = page_num
                            continue
                except ValueError:
                    pass
            
            # Check for "Question X continued"
            if current_q and f"Question {current_q} continued" in line:
                continue  # Skip this line but keep current question
            
            # Continue accumulating current question
            if current_q is not None:
                # Only add substantive content
                if len(line_stripped) > 2:
                    current_text.append(line)
    
    # Save last question
    if current_q is not None:
        questions.append(ExtractedQuestion(
            number=current_q,
            text='\n'.join(current_text),
            page_start=current_start_page,
            page_end=len(doc) - 1
        ))
    
    doc.close()
    
    # Deduplicate (sometimes same question detected twice)
    seen = set()
    unique_questions = []
    for q in questions:
        if q.number not in seen:
            seen.add(q.number)
            unique_questions.append(q)
    
    return unique_questions


def find_paper_files() -> List[Tuple[Path, Optional[Path], int, str, str]]:
    """
    Find all QP/MS pairs in the raw directory
    
    Returns: [(qp_path, ms_path, year, season, paper_number), ...]
    """
    pairs = []
    
    for year_dir in sorted(RAW_DIR.iterdir()):
        if not year_dir.is_dir():
            continue
        try:
            year = int(year_dir.name)
        except ValueError:
            continue
        
        for season_dir in year_dir.iterdir():
            if not season_dir.is_dir():
                continue
            
            season = season_dir.name
            # Normalize season
            if "May" in season or "Jun" in season:
                season_norm = "Jun"
            elif "Oct" in season or "Nov" in season:
                season_norm = "Nov"
            elif "Jan" in season:
                season_norm = "Jan"
            else:
                season_norm = season.replace("-", "_")
            
            # Find paper files
            for pdf_file in season_dir.glob("Paper*.pdf"):
                if "_MS" in pdf_file.name:
                    continue
                
                # Extract paper number
                match = re.search(r'Paper\s*(\d+)', pdf_file.name)
                if not match:
                    continue
                paper_num = match.group(1)
                
                # Find matching MS
                ms_path = None
                for ms_pattern in [
                    f"Paper {paper_num}_MS.pdf",
                    f"Paper {paper_num} MS.pdf",
                    f"Paper{paper_num}_MS.pdf",
                ]:
                    potential_ms = season_dir / ms_pattern
                    if potential_ms.exists():
                        ms_path = potential_ms
                        break
                
                pairs.append((pdf_file, ms_path, year, season_norm, paper_num))
    
    return pairs


def get_subject_id() -> str:
    """Get Mathematics B subject ID"""
    result = supabase.table("subjects").select("id").eq("code", SUBJECT_CODE).execute()
    if result.data:
        return result.data[0]["id"]
    raise ValueError(f"Subject {SUBJECT_CODE} not found. Run: python scripts/add_subject.py maths_b")


def get_or_create_paper(subject_id: str, year: int, season: str, 
                       paper_number: str, total_questions: int) -> Tuple[str, bool]:
    """Get existing paper or create new one"""
    existing = supabase.table("papers")\
        .select("id")\
        .eq("subject_id", subject_id)\
        .eq("year", year)\
        .eq("season", season)\
        .eq("paper_number", paper_number)\
        .execute()
    
    if existing.data:
        return existing.data[0]["id"], False
    
    result = supabase.table("papers").insert({
        "subject_id": subject_id,
        "year": year,
        "season": season,
        "paper_number": paper_number,
        "total_pages": total_questions
    }).execute()
    
    return result.data[0]["id"], True


def create_page(paper_id: str, question: ExtractedQuestion, 
               classification: ClassificationResult) -> bool:
    """Create a page/question entry in database"""
    try:
        # Check if exists
        existing = supabase.table("pages")\
            .select("id")\
            .eq("paper_id", paper_id)\
            .eq("question_number", question.number)\
            .execute()
        
        if existing.data:
            # Update existing
            supabase.table("pages")\
                .update({
                    "topics": [classification.primary_topic],
                    "difficulty": "medium",
                    "confidence": classification.confidence,
                    "text_excerpt": question.text[:500]
                })\
                .eq("id", existing.data[0]["id"])\
                .execute()
            return True
        
        # Create new
        supabase.table("pages").insert({
            "paper_id": paper_id,
            "page_number": int(question.number),
            "question_number": question.number,
            "is_question": True,
            "topics": [classification.primary_topic],
            "difficulty": "medium",
            "confidence": classification.confidence,
            "text_excerpt": question.text[:500],
            "has_diagram": False,
            "page_count": question.page_end - question.page_start + 1
        }).execute()
        return True
        
    except Exception as e:
        print(f"      Error creating page Q{question.number}: {str(e)[:50]}")
        return False


def process_all_papers():
    """Main processing function"""
    print("\n" + "=" * 80)
    print("MATHEMATICS B - COMPLETE PROCESSING PIPELINE")
    print("=" * 80)
    
    # Get subject
    try:
        subject_id = get_subject_id()
        print(f"\nSubject ID: {subject_id[:8]}...")
    except ValueError as e:
        print(f"\nError: {e}")
        return
    
    # Find all papers
    papers = find_paper_files()
    print(f"Found {len(papers)} papers to process")
    
    # Initialize classifier
    print("\nInitializing classifier...")
    classifier = HybridClassifier(str(TOPICS_YAML), GROQ_API_KEY)
    print(f"  Loaded {len(classifier.topics)} topics")
    
    # Process each paper
    stats = {
        "papers": 0,
        "questions": 0,
        "classified": 0,
        "keyword_only": 0,
        "llm_used": 0
    }
    
    print("\n" + "-" * 80)
    print("Processing Papers")
    print("-" * 80)
    
    for i, (qp_path, ms_path, year, season, paper_num) in enumerate(papers, 1):
        print(f"\n[{i}/{len(papers)}] {year} {season} Paper {paper_num}")
        
        # Extract questions from QP
        questions = extract_questions_from_pdf(qp_path)
        print(f"  Extracted {len(questions)} questions")
        
        if not questions:
            print("  WARNING: No questions found!")
            continue
        
        # Get/create paper in DB
        paper_id, is_new = get_or_create_paper(subject_id, year, season, paper_num, len(questions))
        print(f"  Paper ID: {paper_id[:8]}... {'(new)' if is_new else '(existing)'}")
        
        stats["papers"] += 1
        
        # Classify and store each question
        for q in questions:
            stats["questions"] += 1
            
            # Classify
            result = classifier.classify(q.text, f"Q{q.number}")
            
            # Store
            if create_page(paper_id, q, result):
                stats["classified"] += 1
                method_icon = "K" if result.method == "keyword" else "L"
                print(f"    Q{q.number}: Topic {result.primary_topic} ({result.topic_name}) " +
                      f"[{method_icon}] conf={result.confidence:.2f}")
            
            # Brief pause to avoid rate limits
            if result.method == "llm":
                stats["llm_used"] += 1
                time.sleep(2)  # Longer pause after LLM call
            else:
                stats["keyword_only"] += 1
                time.sleep(0.1)  # Brief pause
    
    # Final summary
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"  Papers processed: {stats['papers']}")
    print(f"  Questions extracted: {stats['questions']}")
    print(f"  Questions classified: {stats['classified']}")
    print(f"  Keyword-only classifications: {stats['keyword_only']} " +
          f"({100*stats['keyword_only']/max(1,stats['classified']):.0f}%)")
    print(f"  LLM classifications: {stats['llm_used']} " +
          f"({100*stats['llm_used']/max(1,stats['classified']):.0f}%)")
    
    classifier_stats = classifier.get_stats()
    print(f"\nClassifier stats: {classifier_stats}")


if __name__ == "__main__":
    process_all_papers()
