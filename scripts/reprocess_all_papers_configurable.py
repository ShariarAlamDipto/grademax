#!/usr/bin/env python3
"""
Configurable Reprocessing Script
Uses subject-specific configurations from YAML for document splitting

This version supports different splitting logic for each subject:
- Further Pure Maths: Custom patterns for old/new format detection
- Physics: Different question patterns
- Easy to add new subjects via YAML config
"""

import fitz  # PyMuPDF
import json
import shutil
from pathlib import Path
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass
import time

# Import our configuration system
from splitting_config_loader import (
    SplittingConfigLoader, 
    ConfigurableQuestionDetector,
    SplittingConfig
)


@dataclass
class QuestionInfo:
    """Information about a detected question"""
    question_number: str
    page_start: int
    page_end: int
    pages: List[int]
    page_count: int


class ConfigurablePaperProcessor:
    """Processes papers using subject-specific configurations"""
    
    def __init__(self, qp_path: Path, ms_path: Optional[Path], output_dir: Path, 
                 config: SplittingConfig, year: Optional[int] = None):
        self.qp_path = qp_path
        self.ms_path = ms_path
        self.output_dir = output_dir
        self.config = config
        self.year = year
        self.detector = ConfigurableQuestionDetector(config)
    
    def detect_questions(self, pdf_path: Path, is_markscheme: bool = False) -> List[QuestionInfo]:
        """Detect all questions in a PDF using configured detector"""
        doc = fitz.open(str(pdf_path))
        questions = []
        current_question = None
        current_pages = []
        
        for page_num in range(len(doc)):
            page = doc[page_num]
            text = page.get_text()
            
            # Check for continuation pages
            if self.detector.is_continuation_page(text):
                if current_question:
                    current_pages.append(page_num)
                continue
            
            # Check if this page has a question number
            q_number = self.detector.detect_question_start(text, is_markscheme, self.year)
            
            if q_number:
                # Only start a NEW question if the number is DIFFERENT
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
        
        # Validate question count
        expected_range = self.config.validation.get('expected_range', [5, 20])
        if not (expected_range[0] <= len(qp_questions) <= expected_range[1]):
            print(f"   ⚠️  Warning: Expected {expected_range[0]}-{expected_range[1]} questions, found {len(qp_questions)}")
        
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
            'subject_code': self.config.subject_code,
            'subject_name': self.config.subject_name,
            'year': self.year,
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
    """Delete all existing processed files"""
    if not processed_dir.exists():
        return
    
    total_deleted = 0
    
    for subject_dir in processed_dir.iterdir():
        if not subject_dir.is_dir():
            continue
        
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
    
    print(f"   ✅ Cleaned {total_deleted} directories/files")


def process_subject_with_config(subject_name: str, raw_base: Path, 
                                processed_base: Path, config: SplittingConfig) -> Tuple[int, int, int]:
    """Process all papers for a subject using its configuration"""
    print(f"\n📚 Processing {subject_name}...")
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
        
        try:
            year = int(year_dir.name)
        except ValueError:
            continue
        
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
                season_short = season.split('-')[-1] if '-' in season else season
                output_name = f"{year}_{season_short}_{paper_num}"
                output_dir = subject_processed / output_name
                
                # Process
                try:
                    processor = ConfigurablePaperProcessor(
                        qp_path=files['qp'],
                        ms_path=files['ms'],
                        output_dir=output_dir,
                        config=config,
                        year=year
                    )
                    manifest = processor.process()
                    
                    total_papers += 1
                    total_questions += manifest['total_questions']
                    total_linked += manifest['questions_with_markschemes']
                    
                except Exception as e:
                    print(f"   ❌ Error: {e}")
    
    return (total_papers, total_questions, total_linked)


def process_all_subjects(raw_base: Path, processed_base: Path):
    """Process all configured subjects"""
    print("\n" + "="*70)
    print("📦 CONFIGURABLE PAPER PROCESSING")
    print("="*70)
    
    # Load configurations
    config_loader = SplittingConfigLoader()
    
    # Map subject names to their directory names
    subject_mapping = {
        "Further Pure Mathematics": "Further Pure Maths",
        "Physics": "Physics"
    }
    
    grand_total_papers = 0
    grand_total_questions = 0
    grand_total_linked = 0
    
    # Process each configured subject
    for config_name in config_loader.list_subjects():
        config = config_loader.get_config(config_name)
        
        # Get directory name
        dir_name = subject_mapping.get(config_name, config_name)
        
        # Process subject
        papers, questions, linked = process_subject_with_config(
            dir_name, raw_base, processed_base, config
        )
        
        grand_total_papers += papers
        grand_total_questions += questions
        grand_total_linked += linked
    
    print("\n" + "="*70)
    print("✅ PROCESSING COMPLETE")
    print("="*70)
    print(f"   Papers processed: {grand_total_papers}")
    print(f"   Total questions: {grand_total_questions}")
    print(f"   Questions with markschemes: {grand_total_linked}")
    
    if grand_total_questions > 0:
        success_rate = (grand_total_linked / grand_total_questions) * 100
        print(f"   Success rate: {success_rate:.1f}%")


if __name__ == "__main__":
    import sys
    
    start_time = time.time()
    
    # Parse arguments
    auto_yes = "--yes" in sys.argv
    
    print("="*70)
    print("🔄 CONFIGURABLE COMPLETE PAPER REPROCESSING")
    print("="*70)
    print()
    print("This will:")
    print("  1. Delete all processed question PDFs")
    print("  2. Delete all processed markscheme PDFs")
    print("  3. Re-split all papers using subject-specific configs")
    print("  4. Link each question with its markscheme")
    print()
    
    if not auto_yes:
        response = input("Continue? (yes/no): ")
        if response.lower() != 'yes':
            print("Cancelled.")
            sys.exit(0)
    
    raw_base = Path("data/raw")
    processed_base = Path("data/processed")
    
    # Clean
    print("\n" + "="*70)
    print("🧹 CLEANING PROCESSED DIRECTORY")
    print("="*70)
    clean_processed_directory(processed_base)
    
    # Process
    process_all_subjects(raw_base, processed_base)
    
    elapsed = time.time() - start_time
    print(f"\n⏱️  Total time: {elapsed:.1f} seconds")
