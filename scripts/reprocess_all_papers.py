#!/usr/bin/env python3
"""
Complete Reprocessing Script
1. Deletes all processed question and markscheme PDFs
2. Re-splits all papers from raw directory
3. Links each question with its corresponding markscheme
"""

import fitz  # PyMuPDF
import re
import json
import os
import shutil
from pathlib import Path
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass
import time


@dataclass
class QuestionInfo:
    """Information about a detected question"""
    question_number: str
    page_start: int
    page_end: int
    pages: List[int]
    page_count: int


class QuestionDetector:
    """Detects question boundaries in exam papers"""
    
    # Patterns for Question Papers
    QP_PATTERNS = [
        r'^\s*(\d+)\s+[A-Z(]',          # "1 The" or "1 ("
        r'^\s*(\d+)\s{2,}[A-Z]',        # "1        This" (multiple spaces)
        r'^Question\s+(\d+)',            # "Question 1"
        r'^\s*(\d+)\s*\(',               # "1 ("
        r'^\s*(\d+)\s+This\s+question', # "1 This question"
    ]
    
    # Patterns for Markschemes (different format)
    MS_PATTERNS = [
        r'^Question\s*\n\s*number\s*\n\s*(\d+)',  # Table format: "Question\nnumber\n1"
        r'^\s*(\d+)\s*\n\s*\(a\)',                # "1\n(a)"
        r'^Total\s+for\s+Question\s+(\d+)',       # "Total for Question 1"
    ]
    
    @staticmethod
    def detect_question_start(text: str, is_markscheme: bool = False) -> Optional[str]:
        """Detect if page starts with a question number"""
        
        # For markschemes, look for the table format
        if is_markscheme:
            # The markscheme has a table: "Question\nnumber\nScheme\nMarks\n5  a"
            # The question number appears RIGHT AFTER "Marks" in the table
            # It's typically formatted as "5  a" or "5 a" or just "5"
            lines = text[:1000].split('\n')
            found_marks = False
            
            for i, line in enumerate(lines):
                line_stripped = line.strip().lower()
                
                # Look for "marks" line in the table header
                if 'marks' in line_stripped and len(line_stripped) < 10:
                    found_marks = True
                    # The question number should be in one of the next few lines
                    for j in range(i+1, min(i+5, len(lines))):
                        next_line = lines[j].strip()
                        # Look for pattern like "5  a" or "5 a" or just "5"
                        # Question number at start, possibly followed by part letter
                        match = re.match(r'^(\d+)\s*[a-z]?', next_line)
                        if match:
                            q_num = match.group(1)
                            try:
                                num = int(q_num)
                                if 1 <= num <= 10:
                                    return q_num
                            except ValueError:
                                pass
                    break
            
            return None
        
        # For question papers, look for number at START of line (left margin)
        # followed by text (not just a standalone page number)
        lines = text.strip().split('\n')
        
        # Skip formulae sheet pages
        text_lower = text.lower()
        if 'formulae' in text_lower or 'formula' in text_lower:
            return None
        
        # For older papers (2011-2015), question numbers appear very early (line 2-3)
        # For newer papers (2016+), they appear after headers (line 5+)
        # Check if there's a question number pattern early in the document
        start_line = 0
        
        # First pass: check if this looks like an old or new format
        # Old format: question number appears within first 10 lines with question keywords
        # Page numbers also appear early but WITHOUT question keywords nearby
        for i in range(min(10, len(lines))):
            line_stripped = lines[i].strip()
            
            # Skip obvious page number patterns (just a number on line 0-2 followed by header code)
            if i < 3 and re.match(r'^(\d+)\s*$', line_stripped):
                # Check if next line is a header code like "*P38647A0328*"
                if i+1 < len(lines) and '*P' in lines[i+1]:
                    continue  # This is a page number, skip it
            
            # Check for question number with immediate text
            if re.match(r'^(\d+)\s+[A-Z]', line_stripped):
                q_num = re.match(r'^(\d+)', line_stripped).group(1)
                try:
                    num = int(q_num)
                    if 1 <= num <= 10:
                        start_line = 0  # Start from beginning for old format
                        break
                except ValueError:
                    pass
            
            # Check for standalone number followed by question content
            if re.match(r'^(\d+)\s*(\([a-z]\))?$', line_stripped):
                q_num = re.match(r'^(\d+)', line_stripped).group(1)
                try:
                    num = int(q_num)
                    if 1 <= num <= 10 and i > 2:  # Must be after line 2 to avoid page numbers
                        # Check if next few lines have question-like content
                        for j in range(i+1, min(i+5, len(lines))):
                            next_text = lines[j].strip().lower()
                            if any(word in next_text for word in ['given', 'find', 'show', 'prove', 
                                                                    'calculate', 'write', 'solve', 
                                                                    'figure', 'diagram', 'hence', 'third term']):
                                start_line = 0  # Start from beginning for old format
                                break
                        if start_line == 0:
                            break
                except ValueError:
                    pass
        
        # If no early question found, skip header lines (new format)
        if start_line != 0:
            start_line = 5
        
        # Look for question number pattern
        # Priority 1: Number with immediate text (most reliable)
        # Priority 2: Standalone number with question content nearby
        
        best_match = None
        best_match_line = 999
        
        for i in range(start_line, min(start_line + 30, len(lines))):
            line = lines[i]
            line_stripped = line.strip()
            
            # Skip common headers/footers
            if any(x in line for x in ['*P', 'Turn over', 'DO NOT WRITE', 'Centre Number',
                                        'Candidate Number', 'continued', 'Answer all',
                                        'Write your answers', 'You must', 'Calculators', 'Total Marks']):
                continue
            
            # Skip empty lines
            if not line_stripped:
                continue
            
            # Skip page numbers: if this is line 0-2 and next line has *P code, it's a page number
            if i < 3 and i+1 < len(lines) and '*P' in lines[i+1]:
                continue
            
            # Priority 1: Number followed by space and text (most reliable for old format)
            # Example: "1 Solve..." or "1\tGiven that..." or "7 (a) Solve"
            match = re.match(r'^(\d+)[\t\s]+(\([a-z]\)\s+)?[A-Z]', line_stripped)
            if match:
                q_num = match.group(1)
                try:
                    num = int(q_num)
                    if 1 <= num <= 10:
                        # This is the most reliable pattern, return immediately
                        return q_num
                except ValueError:
                    continue
            
            # Priority 2: Standalone number or number with (a)
            # Example: "2" or "7 (a)"
            # Only consider if no Priority 1 match found yet
            if best_match is None:
                match = re.match(r'^(\d+)\s*(\([a-z]\))?$', line_stripped)
                if match:
                    q_num = match.group(1)
                    try:
                        num = int(q_num)
                        if 1 <= num <= 10:
                            # Verify next few lines contain question-like content
                            has_question_content = False
                            for j in range(i+1, min(i+15, len(lines))):
                                next_line = lines[j].strip().lower()
                                # Look for question indicators
                                if any(word in next_line for word in ['diagram', 'figure', 'given', 'find', 
                                                                        'show', 'calculate', 'prove', 'write',
                                                                        'hence', 'obtain', 'solve', 'third term',
                                                                        'curve', 'line', 'series', 'expression']):
                                    has_question_content = True
                                    break
                            
                            if has_question_content and i < best_match_line:
                                best_match = q_num
                                best_match_line = i
                    except ValueError:
                        continue
        
        return best_match


class PaperProcessor:
    """Processes a single paper (QP and MS)"""
    
    def __init__(self, qp_path: Path, ms_path: Optional[Path], output_dir: Path):
        self.qp_path = qp_path
        self.ms_path = ms_path
        self.output_dir = output_dir
        self.detector = QuestionDetector()
    
    def detect_questions(self, pdf_path: Path, is_markscheme: bool = False) -> List[QuestionInfo]:
        """Detect all questions in a PDF"""
        doc = fitz.open(str(pdf_path))
        questions = []
        current_question = None
        current_pages = []
        
        for page_num in range(len(doc)):
            page = doc[page_num]
            text = page.get_text()
            
            # Skip pages that say "Question X continued" - these are continuation pages
            if "continued" in text.lower() and "question" in text.lower():
                if current_question:
                    current_pages.append(page_num)
                continue
            
            # Check if this page has a question number
            q_number = self.detector.detect_question_start(text, is_markscheme)
            
            if q_number:
                # Only start a NEW question if the number is DIFFERENT from current
                # or if this is the very first question
                if current_question is None or q_number != current_question:
                    # Save previous question
                    if current_question:
                        questions.append(QuestionInfo(
                            question_number=current_question,
                            page_start=current_pages[0],
                            page_end=current_pages[-1],
                            pages=current_pages,
                            page_count=len(current_pages)
                        ))
                    
                    # Start new question
                    current_question = q_number
                    current_pages = [page_num]
                else:
                    # Same question number, continue adding pages
                    current_pages.append(page_num)
            else:
                # No question number found, continue current question (multi-page)
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
        
        doc.close()
        return questions
    
    def save_question_pdf(self, pdf_path: Path, question: QuestionInfo, 
                          output_subdir: str, prefix: str = "q") -> Path:
        """Save a question as a separate PDF"""
        doc = fitz.open(str(pdf_path))
        new_doc = fitz.open()
        
        # Add all pages for this question
        for page_idx in question.pages:
            new_doc.insert_pdf(doc, from_page=page_idx, to_page=page_idx)
        
        # Save
        output_path = self.output_dir / output_subdir / f"{prefix}{question.question_number}.pdf"
        output_path.parent.mkdir(parents=True, exist_ok=True)
        new_doc.save(str(output_path))
        
        new_doc.close()
        doc.close()
        
        return output_path
    
    def process(self) -> Dict:
        """Process QP and MS, link questions to markschemes"""
        print(f"\n📄 {self.qp_path.name}")
        
        # Detect questions in QP
        qp_questions = self.detect_questions(self.qp_path)
        print(f"   Questions found: {len(qp_questions)}")
        
        # Detect questions in MS (if exists)
        ms_questions = []
        if self.ms_path and self.ms_path.exists():
            ms_questions = self.detect_questions(self.ms_path, is_markscheme=True)
            print(f"   Markscheme questions: {len(ms_questions)}")
        
        # Save QP questions
        questions_data = []
        for q in qp_questions:
            qp_pdf_path = self.save_question_pdf(self.qp_path, q, "pages", "q")
            
            # Find matching MS question
            ms_pdf_path = None
            ms_pages = None
            for ms_q in ms_questions:
                if ms_q.question_number == q.question_number:
                    ms_pdf_path = self.save_question_pdf(
                        self.ms_path, ms_q, "markschemes", "q"
                    )
                    ms_pages = ms_q.pages
                    break
            
            questions_data.append({
                'question_number': q.question_number,
                'qp_pages': q.pages,
                'qp_page_count': q.page_count,
                'qp_pdf_path': str(qp_pdf_path.relative_to(self.output_dir.parent.parent)),
                'ms_pages': ms_pages,
                'ms_pdf_path': str(ms_pdf_path.relative_to(self.output_dir.parent.parent)) if ms_pdf_path else None,
                'has_markscheme': ms_pdf_path is not None
            })
        
        # Save manifest
        manifest = {
            'qp_file': str(self.qp_path),
            'ms_file': str(self.ms_path) if self.ms_path else None,
            'total_questions': len(questions_data),
            'questions_with_markschemes': sum(1 for q in questions_data if q['has_markscheme']),
            'questions': questions_data
        }
        
        manifest_path = self.output_dir / "manifest.json"
        with open(manifest_path, 'w', encoding='utf-8') as f:
            json.dump(manifest, f, indent=2)
        
        print(f"   ✅ Saved {len(questions_data)} questions")
        print(f"   📋 Linked {manifest['questions_with_markschemes']} markschemes")
        
        return manifest


def clean_processed_directory(processed_dir: Path):
    """Delete all existing processed files but preserve structure"""
    print("\n" + "="*70)
    print("🧹 CLEANING PROCESSED DIRECTORY")
    print("="*70)
    
    if not processed_dir.exists():
        print("   ⏭️  Directory doesn't exist, nothing to clean")
        return
    
    total_deleted = 0
    
    # Handle both old structure and new subject-based structure
    for subject_dir in processed_dir.iterdir():
        if not subject_dir.is_dir():
            continue
        
        # Check if this is a subject folder (e.g., "Physics Processed")
        # or a paper folder (e.g., "2023_Jan_1P")
        if "Processed" in subject_dir.name:
            # This is a subject folder, recurse into it
            for paper_dir in subject_dir.iterdir():
                if not paper_dir.is_dir():
                    continue
                
                # Delete pages directory
                pages_dir = paper_dir / "pages"
                if pages_dir.exists():
                    shutil.rmtree(pages_dir)
                    total_deleted += 1
                
                # Delete markschemes directory
                ms_dir = paper_dir / "markschemes"
                if ms_dir.exists():
                    shutil.rmtree(ms_dir)
                    total_deleted += 1
                
                # Delete manifest
                manifest_file = paper_dir / "manifest.json"
                if manifest_file.exists():
                    manifest_file.unlink()
        else:
            # Old structure - paper folder directly under processed
            paper_dir = subject_dir
            
            # Delete pages directory
            pages_dir = paper_dir / "pages"
            if pages_dir.exists():
                shutil.rmtree(pages_dir)
                total_deleted += 1
            
            # Delete markschemes directory
            ms_dir = paper_dir / "markschemes"
            if ms_dir.exists():
                shutil.rmtree(ms_dir)
                total_deleted += 1
            
            # Delete manifest
            manifest_file = paper_dir / "manifest.json"
            if manifest_file.exists():
                manifest_file.unlink()
    
    print(f"   ✅ Cleaned {total_deleted} directories/files")


def process_subject(subject_name: str, raw_base: Path, processed_base: Path) -> Tuple[int, int, int]:
    """Process all papers for a single subject
    
    Returns: (total_papers, total_questions, total_linked)
    """
    print(f"\n� Processing {subject_name}...")
    print("-" * 70)
    
    subject_dir = raw_base / "IGCSE" / subject_name
    
    if not subject_dir.exists():
        print(f"❌ {subject_name} directory not found: {subject_dir}")
        return (0, 0, 0)
    
    # Output goes to subject-specific processed folder
    subject_processed = processed_base / f"{subject_name} Processed"
    subject_processed.mkdir(parents=True, exist_ok=True)
    
    total_papers = 0
    total_questions = 0
    total_linked = 0
    
    # Walk through years
    for year_dir in sorted(subject_dir.iterdir()):
        if not year_dir.is_dir():
            continue
        
        year = year_dir.name
        
        # Walk through seasons
        for season_dir in sorted(year_dir.iterdir()):
            if not season_dir.is_dir():
                continue
            
            season = season_dir.name
            
            # Find paper files
            pdf_files = list(season_dir.glob("*.pdf"))
            
            # Group by paper number (Paper 1, Paper 2, Paper 1R, Paper 2R, etc.)
            papers = {}
            for pdf_file in pdf_files:
                name = pdf_file.stem
                
                # Determine paper number (handle both regular and resit papers)
                paper_num = None
                if "Paper 1R" in name or "Paper_1R" in name:
                    paper_num = "1RP"
                elif "Paper 2R" in name or "Paper_2R" in name:
                    paper_num = "2RP"
                elif "Paper 1" in name or "Paper_1" in name:
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
                
                # Create output directory name
                # Convert "May-Jun" to "Jun", "Oct-Nov" to "Nov"
                season_short = season.split('-')[-1] if '-' in season else season
                output_name = f"{year}_{season_short}_{paper_num}"
                output_dir = subject_processed / output_name
                
                # Process
                try:
                    processor = PaperProcessor(
                        qp_path=files['qp'],
                        ms_path=files['ms'],
                        output_dir=output_dir
                    )
                    manifest = processor.process()
                    
                    total_papers += 1
                    total_questions += manifest['total_questions']
                    total_linked += manifest['questions_with_markschemes']
                    
                except Exception as e:
                    print(f"   ❌ Error: {e}")
    
    return (total_papers, total_questions, total_linked)


def process_all_papers(raw_base: Path, processed_base: Path):
    """Process all papers from raw directory for all subjects"""
    print("\n" + "="*70)
    print("📦 PROCESSING ALL PAPERS")
    print("="*70)
    
    # List of subjects to process
    subjects = ["Further Pure Maths"]  # Only process Further Pure Maths
    
    grand_total_papers = 0
    grand_total_questions = 0
    grand_total_linked = 0
    
    # Process each subject
    for subject in subjects:
        papers, questions, linked = process_subject(subject, raw_base, processed_base)
        grand_total_papers += papers
        grand_total_questions += questions
        grand_total_linked += linked
    
    print("\n" + "="*70)
    print("✅ PROCESSING COMPLETE")
    print("="*70)
    print(f"   Papers processed: {grand_total_papers}")
    print(f"   Total questions: {grand_total_questions}")
    print(f"   Questions with markschemes: {grand_total_linked}")
    print(f"   Success rate: {100*grand_total_linked/max(1,grand_total_questions):.1f}%")


def main():
    """Main execution"""
    import sys
    
    raw_base = Path("data/raw")
    processed_base = Path("data/processed")
    
    print("="*70)
    print("🔄 COMPLETE PAPER REPROCESSING")
    print("="*70)
    print()
    print("This will:")
    print("  1. Delete all processed question PDFs")
    print("  2. Delete all processed markscheme PDFs")
    print("  3. Re-split all papers from raw directory")
    print("  4. Link each question with its markscheme")
    print()
    
    # Check for --yes flag
    if "--yes" not in sys.argv:
        response = input("Continue? (yes/no): ").strip().lower()
        
        if response != "yes":
            print("❌ Cancelled")
            return
    
    start_time = time.time()
    
    # Step 1: Clean
    clean_processed_directory(processed_base)
    
    # Step 2: Process all papers
    process_all_papers(raw_base, processed_base)
    
    elapsed = time.time() - start_time
    print(f"\n⏱️  Total time: {elapsed:.1f} seconds")


if __name__ == "__main__":
    main()
