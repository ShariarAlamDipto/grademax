#!/usr/bin/env python3
"""
Page Splitting Script - GradeMax Phase 2
Splits past paper PDFs into individual question pages
"""

import fitz  # PyMuPDF
import re
import json
import os
from pathlib import Path
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass, asdict
import argparse


@dataclass
class QuestionPage:
    """Represents a single question page"""
    question_number: str
    page_index: int
    page_count: int
    text: str
    text_excerpt: str  # First 3000 chars for LLM
    has_diagram: bool
    paper_id: str


@dataclass
class PaperManifest:
    """Manifest of all questions in a paper"""
    paper_id: str
    paper_path: str
    board: str
    level: str
    subject_code: str
    year: int
    season: str
    paper_number: str
    questions: List[Dict]  # List of question metadata
    total_pages: int


class QuestionDetector:
    """Detects question starts in exam papers"""
    
    # Patterns for question numbers
    QUESTION_PATTERNS = [
        r'^\s*(\d+)\s+[A-Z(]',          # "1 The" or "1 ("
        r'^\s*(\d+)\s{2,}[A-Z]',        # "1        This" (multiple spaces)
        r'^\s*(\d+)\s*\n',               # "1\n"
        r'^Question\s+(\d+)',            # "Question 1"
        r'^\s*(\d+)\s*\.',               # "1."
        r'^\s*(\d+)\s+This\s+question', # "1 This question" (common pattern)
    ]
    
    # Patterns for subparts
    SUBPART_PATTERNS = [
        r'^\s*\(([a-z])\)',      # "(a)"
        r'^\s*([a-z])\)',        # "a)"
        r'^\s*\(([ivx]+)\)',     # "(i)" or "(ii)"
    ]
    
    @staticmethod
    def detect_question_start(text: str) -> Optional[str]:
        """Detect if page starts with a question number"""
        lines = text.strip().split('\n')[:20]  # Check first 20 lines (covers instructions)
        
        for line in lines:
            # Skip common header text
            if any(skip in line for skip in ['DO NOT WRITE', 'Turn over', '*P', 'Answer ALL']):
                continue
                
            for pattern in QuestionDetector.QUESTION_PATTERNS:
                match = re.search(pattern, line, re.MULTILINE)
                if match:
                    return match.group(1)
        return None
    
    @staticmethod
    def extract_subparts(text: str) -> List[str]:
        """Extract subpart labels (a, b, c, i, ii, etc.)"""
        subparts = []
        for pattern in QuestionDetector.SUBPART_PATTERNS:
            matches = re.findall(pattern, text, re.MULTILINE)
            subparts.extend(matches)
        return list(set(subparts))  # Remove duplicates
    
    @staticmethod
    def has_diagram(page) -> bool:
        """Check if page contains images/diagrams"""
        try:
            image_list = page.get_images(full=True)
            return len(image_list) > 0
        except:
            return False


class PageSplitter:
    """Splits PDF into question pages"""
    
    def __init__(self, pdf_path: str, output_dir: str):
        self.pdf_path = Path(pdf_path)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        self.doc = fitz.open(str(self.pdf_path))
        self.detector = QuestionDetector()
    
    def extract_page_text(self, page_index: int, max_chars: int = None) -> str:
        """Extract text from a page"""
        page = self.doc[page_index]
        text = page.get_text()
        
        if max_chars:
            return text[:max_chars]
        return text
    
    def split_into_questions(self) -> List[Dict]:
        """
        Split PDF into questions based on page-level detection
        Returns list of question metadata
        """
        questions = []
        current_question = None
        current_pages = []
        
        for page_num in range(len(self.doc)):
            page = self.doc[page_num]
            text = page.get_text()
            
            # Check if this page starts a new question
            question_number = self.detector.detect_question_start(text)
            
            if question_number:
                # Save previous question if exists
                if current_question:
                    questions.append({
                        'question_number': current_question,
                        'page_start': current_pages[0],
                        'page_end': current_pages[-1],
                        'page_count': len(current_pages),
                        'pages': current_pages
                    })
                
                # Start new question
                current_question = question_number
                current_pages = [page_num]
            else:
                # Continue current question (multi-page question)
                if current_question:
                    current_pages.append(page_num)
                else:
                    # Page before first question (instructions, etc.)
                    pass
        
        # Save last question
        if current_question:
            questions.append({
                'question_number': current_question,
                'page_start': current_pages[0],
                'page_end': current_pages[-1],
                'page_count': len(current_pages),
                'pages': current_pages
            })
        
        return questions
    
    def save_question_pages(self, question: Dict, paper_id: str) -> str:
        """
        Save question pages as separate PDF
        Returns: path to saved PDF
        """
        q_num = question['question_number']
        output_path = self.output_dir / f"q{q_num}.pdf"
        
        # Create new PDF with only this question's pages
        new_doc = fitz.open()
        for page_idx in question['pages']:
            new_doc.insert_pdf(self.doc, from_page=page_idx, to_page=page_idx)
        
        new_doc.save(str(output_path))
        new_doc.close()
        
        return str(output_path)
    
    def process_paper(self, paper_id: str, metadata: Dict) -> PaperManifest:
        """
        Process entire paper and create manifest
        """
        print(f"📄 Processing: {self.pdf_path.name}")
        print(f"   Total pages: {len(self.doc)}")
        
        # Detect questions
        questions = self.split_into_questions()
        print(f"   Found {len(questions)} questions")
        
        # Process each question
        question_metadata = []
        for q in questions:
            # Extract text for each page in the question
            pages_data = []
            for page_idx in q['pages']:
                page = self.doc[page_idx]
                text = page.get_text()
                
                pages_data.append({
                    'page_index': page_idx,
                    'text': text,
                    'text_excerpt': text[:3000],  # For LLM classification
                    'has_diagram': self.detector.has_diagram(page),
                    'subparts': self.detector.extract_subparts(text)
                })
            
            # Save question PDF
            pdf_path = self.save_question_pages(q, paper_id)
            
            question_metadata.append({
                'question_number': q['question_number'],
                'page_start': q['page_start'],
                'page_end': q['page_end'],
                'page_count': q['page_count'],
                'pages': pages_data,
                'pdf_path': pdf_path
            })
        
        # Create manifest
        manifest = PaperManifest(
            paper_id=paper_id,
            paper_path=str(self.pdf_path),
            board=metadata.get('board', 'Unknown'),
            level=metadata.get('level', 'Unknown'),
            subject_code=metadata.get('subject_code', 'Unknown'),
            year=metadata.get('year', 0),
            season=metadata.get('season', 'Unknown'),
            paper_number=metadata.get('paper_number', 'Unknown'),
            questions=question_metadata,
            total_pages=len(self.doc)
        )
        
        return manifest
    
    def close(self):
        """Close PDF document"""
        if self.doc:
            self.doc.close()


def process_paper_directory(input_path: str, output_base: str) -> Dict:
    """
    Process a paper directory (QP + MS)
    
    Expected structure:
    data/raw/IGCSE/4PH1/2019/Jun/
        ├── 4PH1_1P.pdf
        └── 4PH1_1P_MS.pdf
    """
    input_path = Path(input_path)
    
    # Find QP and MS files
    qp_file = None
    ms_file = None
    
    for pdf_file in input_path.glob("*.pdf"):
        filename = pdf_file.name.upper()
        if "_MS" in filename or "MARKSCHEME" in filename:
            ms_file = pdf_file
        else:
            qp_file = pdf_file
    
    if not qp_file:
        raise FileNotFoundError(f"No question paper found in {input_path}")
    
    print(f"\n{'='*60}")
    print(f"Processing: {input_path}")
    print(f"QP: {qp_file.name}")
    print(f"MS: {ms_file.name if ms_file else 'Not found'}")
    print(f"{'='*60}\n")
    
    # Parse metadata from path
    # Example: data/raw/IGCSE/4PH1/2019/Jun/
    parts = input_path.parts
    metadata = {
        'board': 'Edexcel',
        'level': parts[-4] if len(parts) >= 4 else 'IGCSE',
        'subject_code': parts[-3] if len(parts) >= 3 else '4PH1',
        'year': int(parts[-2]) if len(parts) >= 2 and parts[-2].isdigit() else 2019,
        'season': parts[-1] if len(parts) >= 1 else 'Jun',
        'paper_number': qp_file.stem.split('_')[-1] if '_' in qp_file.stem else '1P'
    }
    
    # Generate paper ID
    paper_id = f"{metadata['subject_code']}_{metadata['year']}_{metadata['season']}_{metadata['paper_number']}"
    
    # Create output directory
    output_dir = Path(output_base) / paper_id
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Process QP
    qp_splitter = PageSplitter(str(qp_file), str(output_dir / "pages"))
    qp_manifest = qp_splitter.process_paper(paper_id, metadata)
    qp_splitter.close()
    
    # Process MS (same logic)
    ms_manifest = None
    if ms_file:
        ms_splitter = PageSplitter(str(ms_file), str(output_dir / "markscheme_pages"))
        ms_metadata = {**metadata, 'paper_number': metadata['paper_number'] + '_MS'}
        ms_manifest = ms_splitter.process_paper(paper_id + "_MS", ms_metadata)
        ms_splitter.close()
    
    # Link MS pages to QP questions
    if ms_manifest:
        for qp_q in qp_manifest.questions:
            # Find matching MS question by number
            for ms_q in ms_manifest.questions:
                if ms_q['question_number'] == qp_q['question_number']:
                    qp_q['ms_pages'] = ms_q['pages']
                    qp_q['ms_pdf_path'] = ms_q['pdf_path']
                    break
    
    # Save manifest JSON
    manifest_path = output_dir / "manifest.json"
    with open(manifest_path, 'w', encoding='utf-8') as f:
        json.dump({
            'paper_id': paper_id,
            'metadata': metadata,
            'qp_file': str(qp_file),
            'ms_file': str(ms_file) if ms_file else None,
            'total_questions': len(qp_manifest.questions),
            'questions': qp_manifest.questions
        }, f, indent=2, ensure_ascii=False)
    
    print(f"\n✅ Manifest saved: {manifest_path}")
    print(f"   Questions: {len(qp_manifest.questions)}")
    print(f"   Total pages split: {sum(q['page_count'] for q in qp_manifest.questions)}")
    
    return {
        'paper_id': paper_id,
        'manifest_path': str(manifest_path),
        'qp_manifest': qp_manifest,
        'ms_manifest': ms_manifest
    }


def main():
    parser = argparse.ArgumentParser(description='Split past paper PDFs into question pages')
    parser.add_argument('input', help='Input directory containing PDF files')
    parser.add_argument('--output', default='data/processed', help='Output base directory')
    
    args = parser.parse_args()
    
    try:
        result = process_paper_directory(args.input, args.output)
        print(f"\n🎉 Success! Paper ID: {result['paper_id']}")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        raise


if __name__ == "__main__":
    main()
