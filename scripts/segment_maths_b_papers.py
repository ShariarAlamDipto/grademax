#!/usr/bin/env python3
"""
Segment Mathematics B papers from raw PDFs into individual questions

This script:
1. Reads raw PDF papers from data/raw/IGCSE/Maths B/
2. Splits them into individual question PDFs
3. Links question papers with mark schemes
4. Outputs to data/processed/Maths B/

Usage:
    python scripts/segment_maths_b_papers.py
    python scripts/segment_maths_b_papers.py --year 2019
    python scripts/segment_maths_b_papers.py --dry-run
"""

import fitz  # PyMuPDF
import json
import shutil
import argparse
from pathlib import Path
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass
import re
import sys

sys.path.append(str(Path(__file__).parent))
from splitting_config_loader import SplittingConfigLoader, ConfigurableQuestionDetector
from extract_paper_metadata import extract_metadata_from_pdf, PaperMetadata


@dataclass
class QuestionInfo:
    """Information about a detected question"""
    question_number: str
    page_start: int
    page_end: int
    pages: List[int]
    page_count: int


class MathsBPaperProcessor:
    """Processes Maths B papers using configurable question detection"""
    
    def __init__(self, qp_path: Path, ms_path: Optional[Path], output_dir: Path, 
                 config, year: Optional[int] = None, paper_number: Optional[str] = None,
                 session: Optional[str] = None):
        self.qp_path = qp_path
        self.ms_path = ms_path
        self.output_dir = output_dir
        self.config = config
        self.year = year
        self.paper_number = paper_number
        self.session = session
        self.detector = ConfigurableQuestionDetector(config)
        
        # Extract metadata from PDF first page (authoritative source)
        self.qp_metadata: Optional[PaperMetadata] = None
        self.ms_metadata: Optional[PaperMetadata] = None
        self._extract_metadata()
    
    def _extract_metadata(self):
        """Extract metadata from QP and MS first pages"""
        # Extract from Question Paper
        self.qp_metadata = extract_metadata_from_pdf(self.qp_path)
        if self.qp_metadata:
            print(f"   📋 QP Metadata: {self.qp_metadata.watermark()} (confidence: {self.qp_metadata.confidence:.0%})")
            # Use PDF-extracted values as authoritative
            self.year = self.qp_metadata.year
            self.session = self.qp_metadata.session
            self.paper_number = self.qp_metadata.paper_number
        
        # Extract from Mark Scheme
        if self.ms_path and self.ms_path.exists():
            self.ms_metadata = extract_metadata_from_pdf(self.ms_path)
            if self.ms_metadata:
                print(f"   📋 MS Metadata: {self.ms_metadata.watermark()} (confidence: {self.ms_metadata.confidence:.0%})")
    
    def _get_watermark(self, paper_type: str) -> str:
        """
        Generate watermark in standard format: Subject Code | Year | Session | Paper Type
        Example: 4MB1 | 2024 | Jun | QP
        """
        subject_code = self.config.subject_code if self.config else "4MB1"
        
        # Use metadata if available, otherwise fall back to constructor values
        if paper_type == "MS" and self.ms_metadata:
            return self.ms_metadata.watermark()
        elif paper_type == "QP" and self.qp_metadata:
            return self.qp_metadata.watermark()
        
        # Fallback watermark
        year = self.year or 2024
        session = self.session or "Jun"
        return f"{subject_code} | {year} | {session} | {paper_type}"
    
    def detect_questions(self, pdf_path: Path, is_markscheme: bool = False) -> List[QuestionInfo]:
        """
        Detect all questions in a PDF using fence-based approach.
        
        For question papers: Uses "Total for Question N" markers as fences.
        For mark schemes: Uses question number headers in table format.
        
        Each question maps to the pages where it appears (can be partial pages).
        """
        doc = fitz.open(str(pdf_path))
        
        try:
            if is_markscheme:
                return self._detect_markscheme_questions(doc)
            else:
                return self._detect_qp_questions_fence_based(doc)
        finally:
            doc.close()
    
    def _detect_qp_questions_fence_based(self, doc) -> List[QuestionInfo]:
        """
        Fence-based detection for question papers.
        Uses "Total for Question N" markers to identify question boundaries.
        Note: Does NOT close the doc - caller is responsible for that.
        """
        # First pass: collect all text and find all fences
        all_pages_text = []
        fences = []  # List of (question_number, page_num)
        
        fence_pattern = re.compile(r'\(Total for Question (\d+)', re.IGNORECASE)
        
        for page_num in range(len(doc)):
            page = doc[page_num]
            text = page.get_text()
            all_pages_text.append(text)
            
            # Find all fences on this page
            for match in fence_pattern.finditer(text):
                q_num = match.group(1)
                fences.append((q_num, page_num))
        
        # Note: Don't close doc here - let detect_questions handle it
        
        if not fences:
            print("   [WARN] No question fences found - falling back to question start detection")
            return self._detect_questions_fallback(all_pages_text)
        
        # Build question list from fences
        # Each fence marks where a question ENDS
        questions = []
        seen_questions = set()
        
        for q_num, page_num in fences:
            if q_num in seen_questions:
                continue  # Skip duplicate fences
            seen_questions.add(q_num)
            
            # Find the page where this question starts
            # Look backwards from the fence page to find the question number
            start_page = self._find_question_start_page(
                all_pages_text, int(q_num), page_num
            )
            
            # Collect all pages from start to fence
            pages = list(range(start_page, page_num + 1))
            
            questions.append(QuestionInfo(
                question_number=q_num,
                page_start=start_page,
                page_end=page_num,
                pages=pages,
                page_count=len(pages)
            ))
        
        # Sort by question number
        questions.sort(key=lambda q: int(q.question_number))
        
        return questions
    
    def _find_question_start_page(self, all_pages_text: List[str], q_num: int, fence_page: int) -> int:
        """Find the page where a question starts, given its fence (end) page."""
        # Pattern to find question start: "N\t" or "N  " at start of line
        q_start_pattern = re.compile(
            rf'^\s*{q_num}\s+(?:[A-Z(]|[a-z])',
            re.MULTILINE
        )
        
        # Search from fence page backwards
        for page_num in range(fence_page, -1, -1):
            text = all_pages_text[page_num]
            if q_start_pattern.search(text):
                return page_num
        
        # If not found, assume it starts on the fence page
        return fence_page
    
    def _detect_questions_fallback(self, all_pages_text: List[str]) -> List[QuestionInfo]:
        """Fallback detection when no fences are found - use question starts."""
        questions = []
        q_start_pattern = re.compile(r'^\s*(\d{1,2})\s+(?:[A-Z(])', re.MULTILINE)
        
        current_question = None
        current_pages = []
        
        for page_num, text in enumerate(all_pages_text):
            # Skip non-content pages
            text_lower = text.lower()[:500]
            if any(skip in text_lower for skip in self.config.skip_patterns):
                continue
            
            # Find all question starts on this page
            matches = list(q_start_pattern.finditer(text))
            
            if matches:
                # First match on page
                first_q = matches[0].group(1)
                
                if current_question is None or first_q != current_question:
                    # Save previous question
                    if current_question:
                        questions.append(QuestionInfo(
                            question_number=current_question,
                            page_start=current_pages[0],
                            page_end=current_pages[-1],
                            pages=current_pages,
                            page_count=len(current_pages)
                        ))
                    current_question = first_q
                    current_pages = [page_num]
                else:
                    current_pages.append(page_num)
            else:
                if current_question:
                    current_pages.append(page_num)
        
        # Save last question
        if current_question:
            questions.append(QuestionInfo(
                question_number=current_question,
                page_start=current_pages[0],
                page_end=current_pages[-1],
                pages=current_pages,
                page_count=len(current_pages)
            ))
        
        return questions
    
    def _detect_markscheme_questions(self, doc) -> List[QuestionInfo]:
        """
        Detect questions in mark scheme using table format.
        
        Maths B mark schemes have a table format with rows like:
        Question | Working | Answer | Mark | Notes
        1        |         | 1/40   | 2    | M1...
        
        Each question starts a new table section.
        """
        questions = []
        current_question = None
        current_pages = []
        
        # Pattern for MS: "Question\n1" or "Question\nWorking" header followed by question number
        # The table structure means question numbers appear after "Question" header
        question_row_pattern = re.compile(r'^(\d{1,2})\s*$', re.MULTILINE)
        question_header_pattern = re.compile(r'Question\s*\n\s*Working', re.IGNORECASE)
        total_marks_pattern = re.compile(r'Total\s+(\d+)\s+marks', re.IGNORECASE)
        
        # First pass: find all question numbers in their positions
        page_questions = {}  # page_num -> set of question numbers
        
        for page_num in range(len(doc)):
            page = doc[page_num]
            text = page.get_text()
            
            # Skip intro pages
            if page_num < 3 and ('General Marking Guidance' in text or 
                                'Edexcel and BTEC' in text or
                                'Mark Scheme (Results)' in text):
                continue
            
            # Look for Total X marks patterns (most reliable indicator)
            total_matches = total_marks_pattern.findall(text)
            if total_matches:
                for total_marks in total_matches:
                    # This page contains a question ending
                    if page_num not in page_questions:
                        page_questions[page_num] = set()
            
            # Also look for question headers with numbers
            # Format: "Question\n1\n" or just "1\n" at start of table row
            if 'Question' in text:
                lines = text.split('\n')
                for i, line in enumerate(lines):
                    line = line.strip()
                    # Look for standalone numbers (question identifiers)
                    if line.isdigit() and 1 <= int(line) <= 30:
                        q_num = line
                        if page_num not in page_questions:
                            page_questions[page_num] = set()
                        page_questions[page_num].add(q_num)
        
        # Second pass: Build question ranges
        # Go through pages sequentially and track question boundaries
        all_questions_found = set()
        for page_num in sorted(page_questions.keys()):
            all_questions_found.update(page_questions[page_num])
        
        # Sort questions numerically
        sorted_questions = sorted(all_questions_found, key=lambda x: int(x))
        
        # For each question, find its page range
        for q_num in sorted_questions:
            # Find first page where this question appears
            start_page = None
            end_page = None
            
            for page_num in sorted(page_questions.keys()):
                if q_num in page_questions[page_num]:
                    if start_page is None:
                        start_page = page_num
                    end_page = page_num
            
            if start_page is not None:
                questions.append(QuestionInfo(
                    question_number=q_num,
                    page_start=start_page,
                    page_end=end_page,
                    pages=list(range(start_page, end_page + 1)),
                    page_count=end_page - start_page + 1
                ))
        
        # Sort by question number
        questions.sort(key=lambda q: int(q.question_number))
        
        return questions
    
    def save_question_pdf(self, pdf_path: Path, question: QuestionInfo, 
                          output_subdir: str, prefix: str = "q",
                          watermark_text: str = None) -> Path:
        """Save a question as a separate PDF with optional watermark"""
        doc = fitz.open(str(pdf_path))
        new_doc = fitz.open()
        
        # Add all pages for this question
        for page_idx in question.pages:
            new_doc.insert_pdf(doc, from_page=page_idx, to_page=page_idx)
        
        # Add watermark to each page if specified
        if watermark_text:
            for page in new_doc:
                # Add watermark text in top-left corner
                # Use a semi-transparent gray color
                text_point = fitz.Point(10, 20)  # Top-left position
                page.insert_text(
                    text_point,
                    watermark_text,
                    fontsize=10,
                    fontname="helv",
                    color=(0.3, 0.3, 0.3),  # Dark gray
                )
        
        # Save
        output_path = self.output_dir / output_subdir / f"{prefix}{question.question_number}.pdf"
        output_path.parent.mkdir(parents=True, exist_ok=True)
        new_doc.save(str(output_path))
        
        new_doc.close()
        doc.close()
        
        return output_path
    
    def process(self) -> Dict:
        """Process QP and MS, link questions to markschemes"""
        print(f"\n[FILE] {self.qp_path.name}")
        
        # Get watermarks using PDF-extracted metadata (authoritative source)
        qp_watermark = self._get_watermark("QP")
        ms_watermark = self._get_watermark("MS")
        
        print(f"   🏷️  QP Watermark: {qp_watermark}")
        print(f"   🏷️  MS Watermark: {ms_watermark}")
        
        # Detect questions in QP
        qp_questions = self.detect_questions(self.qp_path)
        print(f"   Questions found: {len(qp_questions)}")
        
        # Show question numbers
        q_nums = [q.question_number for q in qp_questions]
        print(f"   Question numbers: {', '.join(q_nums[:10])}{'...' if len(q_nums) > 10 else ''}")
        
        # Validate question count
        expected_range = self.config.validation.get('expected_range', [5, 25])
        if not (expected_range[0] <= len(qp_questions) <= expected_range[1]):
            print(f"   [WARN] Warning: Expected {expected_range[0]}-{expected_range[1]} questions, found {len(qp_questions)}")
        
        # Detect questions in MS (if exists)
        ms_questions = []
        if self.ms_path and self.ms_path.exists():
            ms_questions = self.detect_questions(self.ms_path, is_markscheme=True)
            print(f"   Markscheme questions: {len(ms_questions)}")
        
        # Save QP questions with watermark
        questions_data = []
        for q in qp_questions:
            qp_pdf_path = self.save_question_pdf(self.qp_path, q, "pages", "q", watermark_text=qp_watermark)
            
            # Find matching MS question - NOW WITH WATERMARK
            ms_pdf_path = None
            ms_pages = None
            for ms_q in ms_questions:
                if ms_q.question_number == q.question_number:
                    ms_pdf_path = self.save_question_pdf(
                        self.ms_path, ms_q, "markschemes", "q", watermark_text=ms_watermark
                    )
                    ms_pages = ms_q.pages
                    break
            
            questions_data.append({
                'question_number': q.question_number,
                'qp_pages': q.pages,
                'qp_page_count': q.page_count,
                'qp_pdf_path': str(qp_pdf_path.relative_to(self.output_dir.parent)),
                'ms_pages': ms_pages,
                'ms_pdf_path': str(ms_pdf_path.relative_to(self.output_dir.parent)) if ms_pdf_path else None,
                'has_markscheme': ms_pdf_path is not None,
                'watermark': qp_watermark  # Store watermark for reference
            })
        
        # Save manifest with enhanced metadata
        manifest = {
            'qp_file': str(self.qp_path),
            'ms_file': str(self.ms_path) if self.ms_path else None,
            'subject_code': self.config.subject_code,
            'subject_name': self.config.subject_name,
            'year': self.year,
            'session': self.session,
            'paper_number': self.paper_number,
            'qp_watermark': qp_watermark,
            'ms_watermark': ms_watermark,
            'metadata_extracted': {
                'qp': self.qp_metadata.to_dict() if self.qp_metadata else None,
                'ms': self.ms_metadata.to_dict() if self.ms_metadata else None
            },
            'total_questions': len(questions_data),
            'questions_with_markschemes': sum(1 for q in questions_data if q['has_markscheme']),
            'questions': questions_data
        }
        
        manifest_path = self.output_dir / "manifest.json"
        with open(manifest_path, 'w', encoding='utf-8') as f:
            json.dump(manifest, f, indent=2)
        
        print(f"   [OK] Saved {len(questions_data)} questions")
        print(f"   [INFO] Linked {manifest['questions_with_markschemes']} markschemes")
        
        return manifest


def find_paper_pairs(raw_dir: Path) -> List[Tuple[Path, Optional[Path], int, str]]:
    """Find all QP/MS pairs in the raw directory structure"""
    pairs = []
    
    # Structure: data/raw/IGCSE/Maths B/{year}/{season}/Paper X.pdf
    for year_dir in sorted(raw_dir.iterdir()):
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
            
            # Find all paper PDFs
            for pdf_file in sorted(season_dir.glob("Paper*.pdf")):
                if "_MS" in pdf_file.name:
                    continue  # Skip mark schemes
                
                # Extract paper number
                match = re.search(r'Paper\s*(\d+)', pdf_file.name)
                if not match:
                    continue
                
                paper_num = match.group(1)
                
                # Find matching MS
                ms_patterns = [
                    season_dir / f"Paper {paper_num}_MS.pdf",
                    season_dir / f"Paper {paper_num} MS.pdf",
                    season_dir / f"Paper{paper_num}_MS.pdf",
                ]
                
                ms_path = None
                for ms_pattern in ms_patterns:
                    if ms_pattern.exists():
                        ms_path = ms_pattern
                        break
                
                pairs.append((pdf_file, ms_path, year, season, paper_num))
    
    return pairs


def main():
    parser = argparse.ArgumentParser(description="Segment Mathematics B papers")
    parser.add_argument("--year", type=int, help="Process only specific year")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be processed")
    parser.add_argument("--clean", action="store_true", help="Clean output directory first")
    args = parser.parse_args()
    
    print("\n" + "=" * 80)
    print("MATHEMATICS B PAPER SEGMENTATION")
    print("=" * 80)
    
    # Paths
    raw_dir = Path(__file__).parent.parent / "data" / "raw" / "IGCSE" / "Maths B"
    processed_dir = Path(__file__).parent.parent / "data" / "processed" / "Maths B"
    config_path = Path(__file__).parent.parent / "config" / "document_splitting_config.yaml"
    
    # Check raw directory
    if not raw_dir.exists():
        print(f"\n[ERROR] Raw directory not found: {raw_dir}")
        print(f"\n   Please create the directory and add papers:")
        print(f"   {raw_dir}/2019/May-Jun/Paper 1.pdf")
        print(f"   {raw_dir}/2019/May-Jun/Paper 1_MS.pdf")
        print(f"   {raw_dir}/2019/May-Jun/Paper 2.pdf")
        print(f"   {raw_dir}/2019/May-Jun/Paper 2_MS.pdf")
        return
    
    # Load configuration
    print(f"\n[INFO] Loading configuration...")
    loader = SplittingConfigLoader(str(config_path))
    config = loader.get_config("maths_b")
    
    if not config:
        print(f"[ERROR] Configuration for 'maths_b' not found in {config_path}")
        return
    
    print(f"   [OK] Subject: {config.subject_name} ({config.subject_code})")
    print(f"   [OK] Expected questions: {config.validation.get('expected_range')}")
    
    # Find all paper pairs
    print(f"\n[INFO] Scanning for papers...")
    pairs = find_paper_pairs(raw_dir)
    
    if args.year:
        pairs = [(qp, ms, y, s, p) for qp, ms, y, s, p in pairs if y == args.year]
    
    print(f"   Found {len(pairs)} paper(s)")
    
    if len(pairs) == 0:
        print("\n   [WARN] No papers found!")
        print(f"   Expected structure: {raw_dir}/YYYY/Season/Paper X.pdf")
        return
    
    # Dry run - just show what would be processed
    if args.dry_run:
        print("\n[DRY RUN] Papers that would be processed:")
        for qp, ms, year, season, paper_num in pairs:
            ms_status = "YES" if ms else "NO"
            print(f"   {year} {season} Paper {paper_num} (MS: {ms_status})")
        return
    
    # Clean output directory if requested
    if args.clean and processed_dir.exists():
        print(f"\n[CLEAN] Cleaning output directory...")
        shutil.rmtree(processed_dir)
    
    # Create output directory
    processed_dir.mkdir(parents=True, exist_ok=True)
    
    # Process each paper
    print("\n[PROCESS] Processing papers...")
    stats = {
        'processed': 0,
        'questions': 0,
        'with_ms': 0,
        'errors': 0
    }
    
    for qp_path, ms_path, year, season, paper_num in pairs:
        # Normalize season name
        season_norm = season.replace("-", "_").replace("/", "_")
        if "May" in season or "Jun" in season:
            season_norm = "Jun"
        elif "Oct" in season or "Nov" in season:
            season_norm = "Nov"
        elif "Jan" in season:
            season_norm = "Jan"
        
        # Output directory: data/processed/Maths B/2019_Jun_1/
        output_dir = processed_dir / f"{year}_{season_norm}_{paper_num}"
        
        try:
            processor = MathsBPaperProcessor(
                qp_path=qp_path,
                ms_path=ms_path,
                output_dir=output_dir,
                config=config,
                year=year,
                paper_number=paper_num,
                session=season_norm  # Pass session to processor
            )
            
            manifest = processor.process()
            
            stats['processed'] += 1
            stats['questions'] += manifest['total_questions']
            stats['with_ms'] += manifest['questions_with_markschemes']
            
        except Exception as e:
            print(f"   [ERROR] Error processing {qp_path.name}: {e}")
            stats['errors'] += 1
    
    # Summary
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"   Papers processed: {stats['processed']}")
    print(f"   Total questions: {stats['questions']}")
    print(f"   Questions with mark schemes: {stats['with_ms']}")
    if stats['errors'] > 0:
        print(f"   Errors: {stats['errors']}")
    
    print(f"\n[OK] Output saved to: {processed_dir}")
    print(f"\n[NEXT STEPS]:")
    print(f"   1. Add subject to database: python scripts/add_subject.py maths_b")
    print(f"   2. Process and classify: python scripts/process_and_classify_all_maths_b.py")


if __name__ == "__main__":
    main()
