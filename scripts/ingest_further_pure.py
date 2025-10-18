#!/usr/bin/env python3
"""
Ingestion Pipeline for Further Pure Mathematics
Uses LM Studio (offline) instead of Gemini for classification
"""

import os
import sys
import json
import re
from pathlib import Path
from typing import List, Dict, Optional
from dotenv import load_dotenv
from supabase import create_client
import PyPDF2

# Add LM Studio integration to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'grademax-llm-hybrid' / 'scripts'))

try:
    from integrate_llm import get_llm
    LLM_AVAILABLE = True
except ImportError:
    print("⚠️ LM Studio integration not available")
    print("   Make sure LM Studio is running and grademax-llm-hybrid is set up")
    LLM_AVAILABLE = False

# Load environment
load_dotenv('.env.local')

url = os.getenv('NEXT_PUBLIC_SUPABASE_URL')
key = os.getenv('SUPABASE_SERVICE_ROLE_KEY')

if not url or not key:
    print("❌ Missing Supabase credentials in .env.local")
    exit(1)

supabase = create_client(url, key)


class FurtherPureIngestion:
    """Ingestion pipeline for Further Pure Mathematics"""
    
    def __init__(self, subject_name: str = "Further Pure Mathematics"):
        self.subject_name = subject_name
        self.subject = None
        self.topics = []
        self.llm = None
        
        # Initialize LM Studio if available
        if LLM_AVAILABLE:
            try:
                self.llm = get_llm()
                print("✅ LM Studio connected")
            except Exception as e:
                print(f"⚠️ Could not connect to LM Studio: {e}")
                self.llm = None
        
        # Get subject from database
        self._load_subject()
        self._load_topics()
    
    def _load_subject(self):
        """Load subject from database"""
        subjects = supabase.table('subjects').select('*').execute()
        matches = [s for s in subjects.data if self.subject_name.lower() in s['name'].lower()]
        
        if matches:
            self.subject = matches[0]
            print(f"✅ Found subject: {self.subject['name']} (ID: {self.subject['id']})")
        else:
            print(f"❌ Subject '{self.subject_name}' not found in database")
            exit(1)
    
    def _load_topics(self):
        """Load topics for this subject"""
        result = supabase.table('topics').select('*').eq('subject_id', self.subject['id']).execute()
        self.topics = [t['name'] for t in result.data]
        print(f"✅ Loaded {len(self.topics)} topics")
    
    def extract_text_from_pdf(self, pdf_path: Path) -> Dict[int, str]:
        """Extract text from each page of PDF"""
        print(f"\n📄 Extracting text from: {pdf_path.name}")
        
        pages = {}
        try:
            with open(pdf_path, 'rb') as f:
                reader = PyPDF2.PdfReader(f)
                for i, page in enumerate(reader.pages, 1):
                    text = page.extract_text()
                    pages[i] = text
                    print(f"   Page {i}: {len(text)} characters")
        except Exception as e:
            print(f"❌ Error reading PDF: {e}")
            return {}
        
        return pages
    
    def detect_questions(self, text: str) -> List[Dict]:
        """
        Detect individual questions in extracted text
        Looks for patterns like:
        - Question 1
        - 1.
        - (a), (b), (c) for sub-questions
        """
        questions = []
        
        # Split by common question patterns
        # This is a simplified version - adjust regex based on actual PDF format
        question_pattern = r'(?:Question\s+)?(\d+)[\.\s]+(.*?)(?=(?:Question\s+)?\d+[\.\s]+|$)'
        matches = re.finditer(question_pattern, text, re.DOTALL | re.IGNORECASE)
        
        for match in matches:
            q_num = match.group(1)
            q_text = match.group(2).strip()
            
            if len(q_text) > 20:  # Filter out false positives
                questions.append({
                    'number': q_num,
                    'text': q_text[:1000],  # Limit length
                    'full_text': q_text
                })
        
        return questions
    
    def classify_with_lm_studio(self, question_text: str) -> Dict:
        """
        Classify question using LM Studio (offline)
        Returns topics, difficulty, etc.
        """
        if not self.llm:
            # Fallback: return empty classification
            return {
                'topics': [],
                'difficulty': 'medium',
                'reasoning': 'LM Studio not available - manual classification needed'
            }
        
        try:
            result = self.llm.classify_question(
                question_text=question_text,
                subject=self.subject_name,
                topics=self.topics
            )
            return result
        except Exception as e:
            print(f"⚠️ Classification error: {e}")
            return {
                'topics': [],
                'difficulty': 'medium',
                'reasoning': f'Error: {str(e)}'
            }
    
    def process_paper(
        self,
        qp_path: Path,
        ms_path: Optional[Path] = None,
        year: int = 2012,
        season: str = "Jan",
        paper_number: str = "1P"
    ) -> Dict:
        """
        Process a question paper and its mark scheme
        
        Args:
            qp_path: Path to question paper PDF
            ms_path: Path to mark scheme PDF
            year: Exam year
            season: Exam season (Jan, Jun, Oct)
            paper_number: Paper number (1P, 2P, 3P)
        
        Returns:
            Summary of processing results
        """
        print("\n" + "="*80)
        print(f"🔄 Processing: {year} {season} Paper {paper_number}")
        print("="*80)
        
        # 1. Extract questions
        qp_pages = self.extract_text_from_pdf(qp_path)
        
        # Combine all pages into one text for question detection
        full_text = "\n\n".join(qp_pages.values())
        questions = self.detect_questions(full_text)
        
        print(f"\n✅ Detected {len(questions)} questions")
        
        # 2. Extract mark scheme (if available)
        ms_pages = {}
        if ms_path and ms_path.exists():
            ms_pages = self.extract_text_from_pdf(ms_path)
        
        # 3. Get or create paper in database
        paper = self._get_or_create_paper(year, season, paper_number)
        
        # 4. Process each question
        results = {
            'paper_id': paper['id'],
            'total_questions': len(questions),
            'classified': 0,
            'uploaded': 0,
            'errors': []
        }
        
        for i, question in enumerate(questions, 1):
            print(f"\n📝 Processing Question {question['number']}...")
            
            try:
                # Classify with LM Studio
                classification = self.classify_with_lm_studio(question['text'])
                results['classified'] += 1
                
                print(f"   Topics: {', '.join(classification.get('topics', []))}")
                print(f"   Difficulty: {classification.get('difficulty', 'unknown')}")
                
                # Find corresponding mark scheme
                ms_text = self._find_mark_scheme(question['number'], ms_pages)
                
                # Upload to database
                page_data = {
                    'paper_id': paper['id'],
                    'question_number': question['number'],
                    'question_text': question['full_text'],
                    'mark_scheme_text': ms_text,
                    'topics': classification.get('topics', []),
                    'difficulty': classification.get('difficulty', 'medium'),
                    'marks_available': self._extract_marks(question['full_text'])
                }
                
                # Insert into pages table
                result = supabase.table('pages').insert(page_data).execute()
                results['uploaded'] += 1
                print(f"   ✅ Uploaded to database")
                
            except Exception as e:
                error_msg = f"Question {question['number']}: {str(e)}"
                results['errors'].append(error_msg)
                print(f"   ❌ Error: {e}")
        
        return results
    
    def _get_or_create_paper(self, year: int, season: str, paper_number: str) -> Dict:
        """Get existing paper or create new one"""
        # Check if exists
        existing = supabase.table('papers')\
            .select('*')\
            .eq('subject_id', self.subject['id'])\
            .eq('year', year)\
            .eq('season', season)\
            .eq('paper_number', paper_number)\
            .execute()
        
        if existing.data:
            print(f"✅ Found existing paper in database")
            return existing.data[0]
        
        # Create new paper
        paper_data = {
            'subject_id': self.subject['id'],
            'year': year,
            'season': season,
            'paper_number': paper_number
        }
        
        result = supabase.table('papers').insert(paper_data).execute()
        print(f"✅ Created new paper in database")
        return result.data[0]
    
    def _find_mark_scheme(self, question_number: str, ms_pages: Dict[int, str]) -> str:
        """Find mark scheme text for a question"""
        if not ms_pages:
            return ""
        
        # Combine all MS pages
        full_ms = "\n\n".join(ms_pages.values())
        
        # Look for the question number in mark scheme
        pattern = f"(?:Question\\s+)?{question_number}[\\s\\.]+(.*?)(?=(?:Question\\s+)?\\d+[\\s\\.]|$)"
        match = re.search(pattern, full_ms, re.DOTALL | re.IGNORECASE)
        
        if match:
            return match.group(1).strip()[:1000]
        
        return ""
    
    def _extract_marks(self, question_text: str) -> Optional[int]:
        """Extract marks available from question text"""
        # Look for patterns like [5 marks], (5 marks), [5]
        patterns = [
            r'\[(\d+)\s*marks?\]',
            r'\((\d+)\s*marks?\)',
            r'\[(\d+)\]'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, question_text, re.IGNORECASE)
            if match:
                return int(match.group(1))
        
        return None


def main():
    """Main ingestion process"""
    print("="*80)
    print("🚀 FURTHER PURE MATHEMATICS INGESTION")
    print("="*80)
    
    # Check LM Studio availability
    if not LLM_AVAILABLE:
        print("\n⚠️ WARNING: LM Studio integration not available")
        print("   Questions will be uploaded but not classified")
        print("   To enable classification:")
        print("   1. Start LM Studio server")
        print("   2. Run: pip install -r grademax-llm-hybrid/requirements.txt")
        print("\nContinue anyway? (y/n): ", end='')
        
        response = input().lower()
        if response != 'y':
            print("Aborted.")
            return
    
    # Initialize ingestion
    ingestion = FurtherPureIngestion()
    
    # Define paths
    pdf_dir = Path("data/raw/IGCSE/Further Pure Maths/2012/Jan")
    qp_path = pdf_dir / "Paper 1.pdf"
    ms_path = pdf_dir / "Paper 1_MS.pdf"
    
    if not qp_path.exists():
        print(f"❌ Question paper not found: {qp_path}")
        return
    
    # Process the paper
    results = ingestion.process_paper(
        qp_path=qp_path,
        ms_path=ms_path if ms_path.exists() else None,
        year=2012,
        season="Jan",
        paper_number="1P"
    )
    
    # Print summary
    print("\n" + "="*80)
    print("📊 INGESTION SUMMARY")
    print("="*80)
    print(f"Total Questions Detected: {results['total_questions']}")
    print(f"Successfully Classified: {results['classified']}")
    print(f"Uploaded to Database: {results['uploaded']}")
    
    if results['errors']:
        print(f"\n⚠️ Errors ({len(results['errors'])}):")
        for error in results['errors']:
            print(f"   - {error}")
    
    if results['uploaded'] > 0:
        print(f"\n✅ SUCCESS! {results['uploaded']} questions uploaded")
        print("\nNext steps:")
        print("1. Visit dashboard to view questions")
        print("2. Generate a worksheet to test")
        print("3. Run: python scripts/verify_pipeline.py")
    
    print("="*80)


if __name__ == "__main__":
    main()
