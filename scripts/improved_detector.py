#!/usr/bin/env python3
"""
Improved Paper Processor v2
- Adds fuzzy matching for question numbers
- Detects old-style specimen markscheme format
- Better handling of edge cases
"""

import fitz
import re
from pathlib import Path
from typing import List, Optional, Dict
from dataclasses import dataclass


@dataclass
class QuestionInfo:
    """Information about a detected question"""
    question_number: str
    page_start: int
    page_end: int
    pages: List[int]
    page_count: int


class ImprovedQuestionDetector:
    """Enhanced question detection with multiple format support"""
    
    # Patterns for Question Papers
    QP_PATTERNS = [
        r'^\s*(\d+)\s+[A-Z(]',
        r'^\s*(\d+)\s{2,}[A-Z]',
        r'^Question\s+(\d+)',
        r'^\s*(\d+)\s*\(',
        r'^\s*(\d+)\s+This\s+question',
    ]
    
    # Patterns for Modern Markschemes (table format)
    MS_MODERN_PATTERNS = [
        r'Question\s+number.*?(\d+)',  # "Question number" followed by number
    ]
    
    # Patterns for Old-style Markschemes (specimen format)
    MS_OLD_PATTERNS = [
        r'!"#$%&\'\(\)\s*\("(\d+)\)',  # Old garbled format
        r'\(Question\s+(\d+)\)',
        r'^(\d+)\s*\([a-z]\)',  # "1 (a)"
    ]
    
    @staticmethod
    def normalize_question_number(q_num: str) -> str:
        """Normalize question numbers for fuzzy matching"""
        # Remove leading zeros
        q_num = q_num.lstrip('0')
        
        # Handle special cases
        if not q_num or q_num == '0':
            return '0'
        
        # Convert to int and back to remove any other issues
        try:
            return str(int(q_num))
        except ValueError:
            return q_num
    
    @staticmethod
    def fuzzy_match_question_numbers(qp_numbers: List[str], ms_numbers: List[str]) -> Dict[str, str]:
        """
        Create fuzzy matching between QP and MS question numbers
        Returns: {qp_number: ms_number} mapping
        """
        matches = {}
        
        # Normalize all numbers
        qp_norm = {q: ImprovedQuestionDetector.normalize_question_number(q) for q in qp_numbers}
        ms_norm = {m: ImprovedQuestionDetector.normalize_question_number(m) for m in ms_numbers}
        
        # Direct matches
        for qp, qp_n in qp_norm.items():
            if qp_n in ms_norm.values():
                # Find the original MS number
                for ms, ms_n in ms_norm.items():
                    if ms_n == qp_n:
                        matches[qp] = ms
                        break
        
        # Handle special cases
        # Q0 often means "no actual question" - skip it
        for qp in qp_numbers:
            if qp_norm[qp] == '0':
                matches[qp] = None  # Mark as skip
        
        # Very high numbers (>50) are likely errors - skip
        for qp in qp_numbers:
            try:
                if int(qp_norm[qp]) > 50:
                    matches[qp] = None
            except ValueError:
                pass
        
        return matches
    
    @staticmethod
    def detect_markscheme_format(pdf_path: Path) -> str:
        """
        Detect which markscheme format is used
        Returns: 'modern', 'old', or 'unknown'
        """
        doc = fitz.open(str(pdf_path))
        
        sample_pages = min(5, len(doc))
        
        for page_num in range(sample_pages):
            text = doc[page_num].get_text()
            
            # Check for modern format
            if 'Question\nnumber' in text or 'Question number' in text:
                doc.close()
                return 'modern'
            
            # Check for old format markers
            if '!"#$%&\'()' in text or '("*+#,' in text:
                doc.close()
                return 'old'
        
        doc.close()
        return 'unknown'
    
    @staticmethod
    def detect_question_start(text: str, is_markscheme: bool = False, 
                            ms_format: str = 'modern') -> Optional[str]:
        """Detect if page starts with a question number"""
        
        # For markschemes
        if is_markscheme:
            if ms_format == 'modern':
                # Modern table format
                match = re.search(r'Question\s+number.*?(\d+)', text[:500], 
                                re.DOTALL | re.IGNORECASE)
                if match:
                    q_num = match.group(1)
                    try:
                        if 1 <= int(q_num) <= 30:
                            return q_num
                    except ValueError:
                        pass
            
            elif ms_format == 'old':
                # Old specimen format - try multiple patterns
                for pattern in ImprovedQuestionDetector.MS_OLD_PATTERNS:
                    match = re.search(pattern, text[:800], re.MULTILINE)
                    if match:
                        q_num = match.group(1)
                        try:
                            if 1 <= int(q_num) <= 30:
                                return q_num
                        except (ValueError, IndexError):
                            continue
            
            return None
        
        # For question papers
        lines = text.strip().split('\n')[:30]
        
        for line in lines:
            # Skip headers/footers
            skip_patterns = [
                'DO NOT WRITE', 'Turn over', 'Answer ALL', 
                '*P', 'Leave', 'blank', 'Pearson', 'Edexcel',
                'Mark Scheme', 'Marks', 'Answer', 'Notes'
            ]
            if any(skip in line for skip in skip_patterns):
                continue
            
            # Try each pattern
            for pattern in ImprovedQuestionDetector.QP_PATTERNS:
                match = re.search(pattern, line, re.MULTILINE | re.IGNORECASE)
                if match:
                    q_num = match.group(1)
                    try:
                        if 1 <= int(q_num) <= 30:
                            return q_num
                    except ValueError:
                        continue
        
        return None


def detect_questions_improved(pdf_path: Path, is_markscheme: bool = False) -> List[QuestionInfo]:
    """Improved question detection with format detection"""
    
    # Detect format for markschemes
    ms_format = 'modern'
    if is_markscheme:
        ms_format = ImprovedQuestionDetector.detect_markscheme_format(pdf_path)
        print(f"      Markscheme format: {ms_format}")
    
    doc = fitz.open(str(pdf_path))
    questions = []
    current_question = None
    current_pages = []
    detector = ImprovedQuestionDetector()
    
    for page_num in range(len(doc)):
        page = doc[page_num]
        text = page.get_text()
        
        # Detect question start
        q_number = detector.detect_question_start(text, is_markscheme, ms_format)
        
        if q_number:
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
            # Continue current question
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


def validate_pdf_quality(pdf_path: Path) -> Dict:
    """Check if PDF needs OCR or has issues"""
    doc = fitz.open(str(pdf_path))
    
    total_chars = 0
    corrupted = False
    
    for page_num in range(min(3, len(doc))):
        text = doc[page_num].get_text()
        total_chars += len(text)
        
        if '\x06' in text or '\x0f' in text or text.count('␦') > 10:
            corrupted = True
    
    doc.close()
    
    avg_chars = total_chars / min(3, len(doc))
    
    return {
        'is_valid': avg_chars > 100 and not corrupted,
        'avg_chars': avg_chars,
        'corrupted': corrupted,
        'needs_ocr': corrupted or avg_chars < 100
    }


# Add these functions to the reprocessing script
def get_improved_detector():
    """Return the improved detector class"""
    return ImprovedQuestionDetector()


if __name__ == "__main__":
    print("="*80)
    print("IMPROVED QUESTION DETECTION - TEST")
    print("="*80)
    
    # Test specimen markscheme
    specimen_ms = Path("data/raw/IGCSE/Physics/2017/Specimen/Paper 1_MS.pdf")
    if specimen_ms.exists():
        print(f"\n📄 Testing: {specimen_ms.name}")
        questions = detect_questions_improved(specimen_ms, is_markscheme=True)
        print(f"   Questions found: {len(questions)}")
        print(f"   Numbers: {[q.question_number for q in questions]}")
