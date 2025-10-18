#!/usr/bin/env python3
"""
UNIVERSAL PAGE-BASED INGESTION PIPELINE (Physics v2.5 Standard)
================================================================
Works for ANY subject: Physics, Further Pure Maths, Chemistry, Biology, etc.

Key Features:
- Page-level extraction (preserves format, diagrams, spacing)
- Topic arrays: topics TEXT[] for multi-topic support
- QP/MS 1:1 linking via question number matching
- Offline LM Studio classification (no Gemini)
- GIN-indexed topic queries
- Year/season/paper metadata from papers table

Architecture:
- Split QP by question boundaries (Q1, Q2, etc.)
- Extract MS pages matching question numbers
- Classify with LM Studio (subject-aware model routing)
- Upload to: subjects/{SubjectName}/pages/{Year}_{Season}_{Paper}/q{N}.pdf
- Store in pages table with topics array

Usage:
    python scripts/universal_page_ingest.py \
        "data/raw/IGCSE/Further Pure Maths/2012/Jan/Paper 1.pdf" \
        "data/raw/IGCSE/Further Pure Maths/2012/Jan/Paper 1_MS.pdf"
"""

import os
import sys
import json
import time
import fitz
import re
from pathlib import Path
from dataclasses import dataclass, asdict
from typing import Dict, List, Optional
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).parent.parent / "grademax-llm-hybrid" / "scripts"))

from lmstudio_client import LMStudioClient
from supabase_client import SupabaseClient

load_dotenv()


@dataclass
class ProcessedPage:
    """Represents a processed page with QP/MS linkage"""
    page_number: int
    question_number: str
    topics: List[str]           # Array: ["1", "3"]
    difficulty: str
    confidence: float
    qp_page_path: str
    ms_page_path: Optional[str]
    qp_storage_url: str
    ms_storage_url: Optional[str]
    has_diagram: bool
    text_excerpt: str


class QuestionSplitter:
    """Split PDF into individual question pages"""
    
    QUESTION_PATTERNS = [
        r'^Q(?:uestion)?\s*(\d+)',           # Q1, Question 1
        r'^\d+\.\s+',                         # 1.
        r'^Total for Question \d+',          # End marker
    ]
    
    def __init__(self, pdf_path: str, output_dir: Path):
        self.pdf_path = pdf_path
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.doc = fitz.open(pdf_path)
    
    def detect_question_boundaries(self) -> List[Dict]:
        """Detect where each question starts/ends"""
        questions = []
        current_q = None
        
        for page_num in range(len(self.doc)):
            page = self.doc[page_num]
            text = page.get_text()
            lines = text.split('\n')
            
            for line in lines[:20]:  # Check first 20 lines
                line = line.strip()
                
                # Check for question start
                for pattern in self.QUESTION_PATTERNS:
                    match = re.match(pattern, line, re.IGNORECASE)
                    if match:
                        # Save previous question
                        if current_q:
                            current_q['end_page'] = page_num - 1
                            questions.append(current_q)
                        
                        # Start new question
                        q_num = match.group(1) if match.groups() else str(len(questions) + 1)
                        current_q = {
                            'question_number': q_num,
                            'start_page': page_num,
                            'end_page': page_num,
                            'has_diagram': self._has_diagram(page)
                        }
                        break
        
        # Close last question
        if current_q:
            current_q['end_page'] = len(self.doc) - 1
            questions.append(current_q)
        
        return questions
    
    def _has_diagram(self, page) -> bool:
        """Check if page contains images/diagrams"""
        return len(page.get_images()) > 0
    
    def extract_question(self, question_info: Dict) -> str:
        """Extract a question as a separate PDF"""
        q_num = question_info['question_number']
        output_path = self.output_dir / f"q{q_num}.pdf"
        
        new_doc = fitz.open()
        for page_num in range(question_info['start_page'], question_info['end_page'] + 1):
            new_doc.insert_pdf(self.doc, from_page=page_num, to_page=page_num)
        
        new_doc.save(str(output_path))
        new_doc.close()
        
        return str(output_path)
    
    def process_all(self) -> List[Dict]:
        """Split entire paper into questions"""
        questions = self.detect_question_boundaries()
        
        for q in questions:
            q['pdf_path'] = self.extract_question(q)
        
        return questions
    
    def close(self):
        self.doc.close()


class MarkSchemeExtractor:
    """Extract mark scheme pages matching question numbers"""
    
    def __init__(self, ms_pdf_path: str, output_dir: Path):
        self.ms_pdf_path = ms_pdf_path
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        if Path(ms_pdf_path).exists():
            self.doc = fitz.open(ms_pdf_path)
        else:
            self.doc = None
            print(f"   ⚠️  Mark scheme not found: {ms_pdf_path}")
    
    def extract_for_question(self, question_number: str) -> Optional[str]:
        """Extract MS pages for specific question number"""
        if not self.doc:
            return None
        
        matching_pages = []
        
        # Search for question number in MS
        for page_num in range(len(self.doc)):
            page = self.doc[page_num]
            text = page.get_text()
            
            # Look for various formats: "Q1", "Question 1", "1)", etc.
            if (f"{question_number})" in text or 
                f"Question {question_number}" in text or
                f"Q{question_number}" in text or
                f"{question_number} " in text[:100]):  # First 100 chars
                matching_pages.append(page_num)
        
        if not matching_pages:
            # Fallback: Use page proximity (if Q1 at page 5, MS likely near page 5)
            try:
                q_num_int = int(question_number)
                if q_num_int <= len(self.doc):
                    matching_pages = [q_num_int - 1]  # Approximate
            except:
                return None
        
        if not matching_pages:
            return None
        
        # Create PDF with matching pages
        output_path = self.output_dir / f"q{question_number}_ms.pdf"
        new_doc = fitz.open()
        
        for page_num in matching_pages:
            new_doc.insert_pdf(self.doc, from_page=page_num, to_page=page_num)
        
        new_doc.save(str(output_path))
        new_doc.close()
        
        return str(output_path)
    
    def close(self):
        if self.doc:
            self.doc.close()


class UniversalPagePipeline:
    """Universal page-based ingestion for all subjects"""
    
    def __init__(self, config_path: str = "grademax-llm-hybrid/config/llm.yaml"):
        self.db = SupabaseClient()
        self.llm = LMStudioClient(config_path=config_path)
        
        # Subject name mapping (auto-detect from folder structure)
        self.subject_map = {
            'Physics': 'Physics',
            '4PH1': 'Physics',
            'Chemistry': 'Chemistry',
            '4CH1': 'Chemistry',
            'Biology': 'Biology',
            '4BI1': 'Biology',
            'Mathematics': 'Mathematics',
            '4MA1': 'Mathematics',
            'Further Pure Maths': 'Further Pure Mathematics',
            'Further Pure Mathematics': 'Further Pure Mathematics',
            '9FM0': 'Further Pure Mathematics',
            'FurtherPureMaths': 'Further Pure Mathematics'
        }
    
    def _detect_subject(self, pdf_path: Path) -> str:
        """Detect subject from folder structure"""
        path_str = str(pdf_path)
        
        for key, subject_name in self.subject_map.items():
            if key in path_str:
                return subject_name
        
        # Fallback: Ask user
        print(f"❓ Could not detect subject from path: {pdf_path}")
        print("Available subjects:", list(set(self.subject_map.values())))
        subject = input("Enter subject name: ").strip()
        return subject
    
    def _parse_filename(self, filename: str, parent_dir: Path, pdf_path: str) -> Dict:
        """Parse year, season, paper from filename and path"""
        # Try to extract from path: .../2012/Jan/Paper 1.pdf
        parts = str(parent_dir).split(os.sep)
        
        year = None
        season = None
        paper_number = None
        
        # Look for year (4 digits)
        for part in parts:
            if re.match(r'^\d{4}$', part):
                year = int(part)
        
        # Look for season
        season_map = {
            'Jan': 'Jan', 'January': 'Jan',
            'Jun': 'Jun', 'June': 'Jun',
            'Oct': 'Oct', 'October': 'Oct',
            'Nov': 'Nov', 'November': 'Nov',
            'May': 'May'
        }
        for part in parts:
            if part in season_map:
                season = season_map[part]
        
        # Extract paper number from filename
        match = re.search(r'Paper\s*(\d+)', filename, re.IGNORECASE)
        if match:
            paper_number = match.group(1)
        else:
            # Fallback: Look for digit in filename
            match = re.search(r'(\d+)', filename)
            if match:
                paper_number = match.group(1)
        
        # Read PDF to check for watermark if year not found
        if not year:
            try:
                doc = fitz.open(pdf_path)
                first_page_text = doc[0].get_text()
                doc.close()
                
                # Look for year in first page
                year_match = re.search(r'\b(20\d{2})\b', first_page_text)
                if year_match:
                    year = int(year_match.group(1))
            except:
                pass
        
        return {
            'year': year or 2024,
            'season': season or 'unknown',
            'paper_number': paper_number or '1'
        }
    
    def _ensure_paper(self, paper_info: Dict, subject_id: str, qp_url: str, ms_url: str) -> str:
        """Get or create paper record in database"""
        # Check if paper exists
        result = self.db.select('papers', columns='id', filters={
            'subject_id': subject_id,
            'year': paper_info['year'],
            'season': paper_info['season'],
            'paper_number': paper_info['paper_number']
        })
        
        if result:
            return result[0]['id']
        
        # Create new paper
        paper_data = {
            'subject_id': subject_id,
            'year': paper_info['year'],
            'season': paper_info['season'],
            'paper_number': paper_info['paper_number'],
            'qp_source_path': qp_url,
            'ms_source_path': ms_url
        }
        
        result = self.db.insert('papers', paper_data)
        return result[0]['id']
    
    def process_paper_pair(self, qp_path: str, ms_path: str):
        """Process a QP and MS pair (main entry point)"""
        qp_path = Path(qp_path)
        ms_path = Path(ms_path)
        
        # Detect subject
        subject_name = self._detect_subject(qp_path)
        print(f"\n📚 Subject: {subject_name}")
        
        # Get subject ID from database
        result = self.db.select('subjects', columns='id', filters={'name': subject_name})
        if not result:
            raise ValueError(f"Subject '{subject_name}' not found in database")
        subject_id = result[0]['id']
        
        # Parse paper metadata
        paper_info = self._parse_filename(qp_path.name, qp_path.parent, str(qp_path))
        paper_id_str = f"{paper_info['year']}_{paper_info['season']}_{paper_info['paper_number']}"
        
        print(f"\n{'='*70}")
        print(f"📋 Processing: {paper_id_str}")
        print(f"   Year: {paper_info['year']}")
        print(f"   Season: {paper_info['season']}")
        print(f"   Paper: {paper_info['paper_number']}")
        print(f"{'='*70}")
        
        # Create output directory
        output_dir = Path("data/processed") / subject_name / paper_id_str
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # STEP 1: Create paper record
        print(f"\n1️⃣  Creating paper record...")
        paper_uuid = self._ensure_paper(paper_info, subject_id, str(qp_path), str(ms_path))
        print(f"   ✅ Paper UUID: {paper_uuid}")
        
        # STEP 2: Split QP into questions
        print(f"\n2️⃣  Splitting QP into questions...")
        qp_splitter = QuestionSplitter(str(qp_path), output_dir / "questions")
        questions = qp_splitter.process_all()
        print(f"   ✅ Split into {len(questions)} questions")
        qp_splitter.close()
        
        # STEP 3: Extract mark schemes
        print(f"\n3️⃣  Extracting mark schemes...")
        ms_extractor = MarkSchemeExtractor(str(ms_path), output_dir / "markschemes")
        ms_paths = {}
        for q in questions:
            q_num = q['question_number']
            ms_path_local = ms_extractor.extract_for_question(q_num)
            if ms_path_local:
                ms_paths[q_num] = ms_path_local
                print(f"   ✅ Q{q_num} MS linked")
            else:
                print(f"   ⚠️  Q{q_num} MS not found")
        ms_extractor.close()
        
        # STEP 4: Classify and upload pages
        print(f"\n4️⃣  Classifying with LM Studio and uploading...")
        processed_pages = []
        
        for i, q in enumerate(questions, 1):
            q_num = q['question_number']
            q_pdf = q['pdf_path']
            
            # Read PDF text for classification
            doc = fitz.open(q_pdf)
            text = ""
            for page in doc:
                text += page.get_text()
            doc.close()
            
            # Classify with LM Studio (subject-aware)
            try:
                classification = self.llm.classify_question(
                    question_text=text[:3000],
                    subject=subject_name
                )
                
                topics = classification.get('topics', [])
                difficulty = classification.get('difficulty', 'medium')
                confidence = classification.get('confidence', 0.5)
                
            except Exception as e:
                print(f"   ⚠️  [{i}/{len(questions)}] Q{q_num}: Classification failed - {e}")
                topics = []
                difficulty = 'medium'
                confidence = 0.0
            
            # Storage paths: subjects/{Subject}/pages/{Year}_{Season}_{Paper}/q{N}.pdf
            qp_storage_path = f"subjects/{subject_name}/pages/{paper_id_str}/q{q_num}.pdf"
            ms_storage_path = f"subjects/{subject_name}/pages/{paper_id_str}/q{q_num}_ms.pdf"
            
            # Upload QP
            try:
                self.db.upload_file(
                    bucket="question-pdfs",
                    file_path=q_pdf,
                    destination_path=qp_storage_path
                )
            except Exception as e:
                print(f"   ❌ [{i}/{len(questions)}] Q{q_num}: QP upload failed - {e}")
                continue
            
            # Upload MS (if exists)
            ms_url = None
            if q_num in ms_paths:
                try:
                    self.db.upload_file(
                        bucket="question-pdfs",
                        file_path=ms_paths[q_num],
                        destination_path=ms_storage_path
                    )
                    ms_url = ms_storage_path
                except Exception as e:
                    print(f"   ⚠️  Q{q_num} MS upload failed: {e}")
            
            processed_pages.append(ProcessedPage(
                page_number=i,
                question_number=q_num,
                topics=topics,  # Array: ["1", "3"]
                difficulty=difficulty,
                confidence=confidence,
                qp_page_path=q_pdf,
                ms_page_path=ms_paths.get(q_num),
                qp_storage_url=qp_storage_path,
                ms_storage_url=ms_url,
                has_diagram=q.get('has_diagram', False),
                text_excerpt=text[:500]
            ))
            
            print(f"   ✅ [{i}/{len(questions)}] Q{q_num} → Topics {topics} ({difficulty}, {confidence:.2f})")
            
            # Rate limiting for LM Studio
            if i < len(questions):
                time.sleep(1)  # Adjust based on server capacity
        
        # STEP 5: Store pages in database
        print(f"\n5️⃣  Storing {len(processed_pages)} pages in database...")
        
        for page in processed_pages:
            page_data = {
                'paper_id': paper_uuid,
                'topics': page.topics,  # PostgreSQL TEXT[] array
                'qp_page_url': page.qp_storage_url,
                'ms_page_url': page.ms_storage_url,
                'difficulty': page.difficulty,
                'confidence': page.confidence,
                'has_diagram': page.has_diagram
            }
            
            try:
                self.db.insert('pages', page_data)
                print(f"   ✅ Q{page.question_number} stored")
            except Exception as e:
                print(f"   ❌ Q{page.question_number} DB insert failed: {e}")
        
        print(f"\n{'='*70}")
        print(f"✅ Pipeline complete: {paper_id_str}")
        print(f"   Questions processed: {len(processed_pages)}")
        print(f"   Mark schemes linked: {sum(1 for p in processed_pages if p.ms_page_url)}")
        print(f"{'='*70}\n")


def main():
    if len(sys.argv) < 3:
        print("Usage: python universal_page_ingest.py <qp_path> <ms_path>")
        print("\nExample:")
        print('  python scripts/universal_page_ingest.py \\')
        print('    "data/raw/IGCSE/Further Pure Maths/2012/Jan/Paper 1.pdf" \\')
        print('    "data/raw/IGCSE/Further Pure Maths/2012/Jan/Paper 1_MS.pdf"')
        sys.exit(1)
    
    qp_path = sys.argv[1]
    ms_path = sys.argv[2]
    
    pipeline = UniversalPagePipeline()
    pipeline.process_paper_pair(qp_path, ms_path)


if __name__ == "__main__":
    main()
