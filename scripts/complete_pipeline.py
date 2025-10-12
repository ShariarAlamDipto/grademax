#!/usr/bin/env python3
"""
Complete Ingestion Pipeline with Mark Scheme Integration
- Split QP and MS into individual questions
- Classify each question into ONE topic
- Upload to subject/topic folder structure
- Link MS to each question
"""

import os
import sys
import json
import time
import fitz
from pathlib import Path
from dataclasses import dataclass, asdict
from typing import Dict, List, Optional
from dotenv import load_dotenv

# Add scripts to path
sys.path.insert(0, str(Path(__file__).parent))

from split_pages import PageSplitter
from single_topic_classifier import SingleTopicClassifier
from supabase_client import SupabaseClient

# Load environment variables from .env.ingest
load_dotenv('.env.ingest')


@dataclass
class ProcessedQuestion:
    """Represents a processed question with all metadata"""
    question_number: str
    topic_code: str
    difficulty: str
    confidence: float
    qp_pdf_path: str  # Local path to QP PDF
    ms_pdf_path: str  # Local path to MS PDF
    qp_storage_url: str  # Storage URL for QP
    ms_storage_url: str  # Storage URL for MS
    page_count: int
    has_diagram: bool
    

class MarkSchemeExtractor:
    """Extract mark scheme pages for specific questions"""
    
    def __init__(self, ms_pdf_path: str, output_dir: Path):
        self.ms_pdf_path = ms_pdf_path
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.doc = fitz.open(ms_pdf_path)
        
    def extract_for_question(self, question_number: str) -> Optional[str]:
        """
        Extract mark scheme pages for a specific question
        Returns path to saved MS PDF
        """
        # Simple approach: scan for question number in text
        # More sophisticated: use page ranges from manifest
        
        matching_pages = []
        search_pattern = f"Question {question_number}"
        
        for page_num in range(len(self.doc)):
            page = self.doc[page_num]
            text = page.get_text()
            
            # Look for question number
            if (f"{question_number})" in text or 
                f"Question {question_number}" in text or
                f"Q{question_number}" in text):
                matching_pages.append(page_num)
        
        if not matching_pages:
            print(f"   ⚠️  No MS found for Q{question_number}")
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
        self.doc.close()


class CompletePipeline:
    """Complete processing pipeline"""
    
    def __init__(self, config_path: str = "config/physics_topics.yaml"):
        self.db = SupabaseClient()
        api_key = os.getenv('GEMINI_API_KEY')
        if not api_key:
            raise ValueError("GEMINI_API_KEY environment variable not set")
        self.classifier = SingleTopicClassifier(config_path, api_key)
        self.subject = "Physics"
        
    def process_paper_pair(self, qp_path: str, ms_path: str, output_base: str = "data/processed"):
        """
        Process a QP and MS pair
        
        Args:
            qp_path: Path to question paper PDF
            ms_path: Path to mark scheme PDF
            output_base: Base directory for processed files
        """
        qp_path = Path(qp_path)
        ms_path = Path(ms_path)
        
        # Extract paper metadata from filename
        # Example: 4PH1_Jun19_QP_1P.pdf → year=2019, season=Jun, paper=1P
        paper_info = self._parse_filename(qp_path.name)
        paper_id = f"{paper_info['year']}_{paper_info['season']}_{paper_info['paper']}"
        
        print(f"\n{'='*70}")
        print(f"📋 Processing Paper: {paper_id}")
        print(f"{'='*70}")
        
        # Create output directory
        output_dir = Path(output_base) / paper_id
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # STEP 1: Split QP into questions
        print(f"\n1️⃣  Splitting QP into questions...")
        qp_splitter = PageSplitter(
            pdf_path=str(qp_path),
            output_dir=str(output_dir / "pages")
        )
        
        manifest = qp_splitter.process_paper(
            paper_id=paper_id,
            metadata=paper_info
        )
        
        print(f"   ✅ Split into {len(manifest.questions)} questions")
        
        # STEP 2: Extract mark schemes
        print(f"\n2️⃣  Extracting mark schemes...")
        ms_extractor = MarkSchemeExtractor(
            ms_pdf_path=str(ms_path),
            output_dir=output_dir / "markschemes"
        )
        
        ms_paths = {}
        for q in manifest.questions:
            q_num = q['question_number']
            ms_path_local = ms_extractor.extract_for_question(q_num)
            if ms_path_local:
                ms_paths[q_num] = ms_path_local
                print(f"   ✅ Q{q_num} MS extracted")
        
        ms_extractor.close()
        
        # STEP 3: Classify each question
        print(f"\n3️⃣  Classifying questions with Gemini AI...")
        classifications = {}
        
        for i, q in enumerate(manifest.questions, 1):
            q_num = q['question_number']
            q_pdf = output_dir / "pages" / f"q{q_num}.pdf"
            
            # Read PDF for classification
            doc = fitz.open(str(q_pdf))
            text = ""
            for page in doc:
                text += page.get_text()
            doc.close()
            
            # Classify
            result = self.classifier.classify(text[:3000])  # First 3000 chars
            classifications[q_num] = result
            
            print(f"   [{i}/{len(manifest.questions)}] Q{q_num} → Topic {result.topic} ({result.difficulty}) [confidence: {result.confidence:.2f}]")
            
            # Rate limiting
            if i < len(manifest.questions):
                time.sleep(4.5)
        
        # STEP 4: Upload to storage
        print(f"\n4️⃣  Uploading to Supabase Storage...")
        processed_questions = []
        
        for q in manifest.questions:
            q_num = q['question_number']
            classification = classifications[q_num]
            
            if not classification.page_has_question:
                print(f"   ⏭️  Skipping Q{q_num} (no question detected)")
                continue
            
            topic_code = classification.topic
            
            # Storage paths: subjects/Physics/topics/1/2019_Jun_1P_Q1.pdf
            qp_storage_path = f"subjects/{self.subject}/topics/{topic_code}/{paper_id}_Q{q_num}.pdf"
            ms_storage_path = f"subjects/{self.subject}/topics/{topic_code}/{paper_id}_Q{q_num}_MS.pdf"
            
            # Upload QP
            qp_local_path = str(output_dir / "pages" / f"q{q_num}.pdf")
            qp_url = self.db.upload_file(
                bucket="question-pdfs",
                file_path=qp_local_path,
                destination_path=qp_storage_path
            )
            
            # Upload MS (if exists)
            ms_url = None
            if q_num in ms_paths:
                ms_url = self.db.upload_file(
                    bucket="question-pdfs",
                    file_path=ms_paths[q_num],
                    destination_path=ms_storage_path
                )
            
            processed_questions.append(ProcessedQuestion(
                question_number=q_num,
                topic_code=topic_code,
                difficulty=classification.difficulty,
                confidence=classification.confidence,
                qp_pdf_path=qp_local_path,
                ms_pdf_path=ms_paths.get(q_num),
                qp_storage_url=qp_storage_path,
                ms_storage_url=ms_storage_path if ms_url else None,
                page_count=q['page_count'],
                has_diagram=q.get('has_diagram', False)
            ))
            
            print(f"   ✅ Q{q_num} uploaded to Topic {topic_code}")
        
        # STEP 5: Store in database
        print(f"\n5️⃣  Storing in database...")
        
        # Insert paper record
        paper_data = {
            'board': paper_info['board'],
            'level': paper_info['level'],
            'subject': self.subject,
            'year': paper_info['year'],
            'season': paper_info['season'],
            'paper_number': paper_info['paper'],
            'qp_path': str(qp_path),
            'ms_path': str(ms_path),
            'total_questions': len(processed_questions)
        }
        
        paper_record = self.db.insert('papers', paper_data)
        paper_id_db = paper_record[0]['id']
        
        # Insert question records
        for pq in processed_questions:
            question_data = {
                'paper_id': paper_id_db,
                'question_number': pq.question_number,
                'topic_code': pq.topic_code,
                'difficulty': pq.difficulty,
                'page_pdf_url': pq.qp_storage_url,
                'ms_pdf_url': pq.ms_storage_url,
                'has_diagram': pq.has_diagram,
                'page_count': pq.page_count,
                'confidence': pq.confidence
            }
            
            self.db.insert('questions', question_data)
        
        print(f"   ✅ Stored {len(processed_questions)} questions")
        
        print(f"\n{'='*70}")
        print(f"✅ COMPLETE: {paper_id}")
        print(f"   Questions: {len(processed_questions)}")
        print(f"   Topics: {set(pq.topic_code for pq in processed_questions)}")
        print(f"{'='*70}\n")
        
        return processed_questions
    
    def _parse_filename(self, filename: str) -> Dict:
        """
        Parse paper filename to extract metadata
        Examples: 
          - 4PH1_Jun19_QP_1P.pdf → year=2019, season=Jun, paper=1P
          - 4PH1_1P.pdf → year=2019 (from folder), season=Jun, paper=1P
        """
        parts = filename.replace('.pdf', '').split('_')
        
        # Extract components
        level = parts[0]  # 4PH1
        
        # Handle different filename formats
        if len(parts) == 2:
            # Format: 4PH1_1P.pdf
            paper = parts[1]  # 1P
            season = "Jun"  # Default, should be read from folder structure
            year = 2019  # Default, should be read from folder structure
        elif len(parts) >= 3:
            # Format: 4PH1_Jun19_QP_1P.pdf
            season_year = parts[1]  # Jun19
            paper = parts[-1]  # Last part is paper number
            
            # Parse season and year
            if len(season_year) >= 3:
                # Extract letters and numbers
                import re
                season_match = re.match(r'([A-Za-z]+)(\d+)', season_year)
                if season_match:
                    season = season_match.group(1)  # Jun
                    year_short = season_match.group(2)  # 19
                    year = 2000 + int(year_short) if len(year_short) == 2 else int(year_short)
                else:
                    season = season_year
                    year = 2020
            else:
                season = "Unknown"
                year = 2020
        else:
            paper = "1P"
            season = "Unknown"
            year = 2020
        
        return {
            'board': 'IGCSE',
            'level': level,
            'season': season,
            'year': year,
            'paper': paper
        }


def main():
    if len(sys.argv) < 3:
        print("Usage: python complete_pipeline.py <qp_pdf> <ms_pdf>")
        print("Example: python complete_pipeline.py data/raw/.../QP_1P.pdf data/raw/.../MS_1P.pdf")
        sys.exit(1)
    
    qp_path = sys.argv[1]
    ms_path = sys.argv[2]
    
    pipeline = CompletePipeline()
    pipeline.process_paper_pair(qp_path, ms_path)


if __name__ == "__main__":
    main()
