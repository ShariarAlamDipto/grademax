#!/usr/bin/env python3
"""
Extract paper metadata from PDF first page.

Reads the first page of a PDF and extracts:
- Subject code (e.g., 4MB1)
- Year (e.g., 2024)
- Session (e.g., Jun, Jan, Nov)
- Paper number (e.g., 1, 1R, 2)
- Paper type (QP or MS)

This is the AUTHORITATIVE source for metadata - extracted directly from the 
paper's first page, not from folder structure or filename.

Format output: Subject Code | Year | Session | Paper Type
Example: 4MB1 | 2024 | Jun | QP
"""

import fitz
import re
from pathlib import Path
from typing import Dict, Optional, Tuple
from dataclasses import dataclass


@dataclass
class PaperMetadata:
    """Extracted paper metadata"""
    subject_code: str      # 4MB1
    year: int              # 2024
    session: str           # Jun, Jan, Nov
    paper_number: str      # 1, 1R, 2, 2R
    paper_type: str        # QP or MS
    raw_paper_ref: str     # Original paper reference (e.g., 4MB1/01R)
    confidence: float      # 0.0-1.0 confidence score
    
    def watermark(self) -> str:
        """Generate watermark string in standard format"""
        return f"{self.subject_code} | {self.year} | {self.session} | {self.paper_type}"
    
    def to_dict(self) -> Dict:
        return {
            'subject_code': self.subject_code,
            'year': self.year,
            'session': self.session,
            'paper_number': self.paper_number,
            'paper_type': self.paper_type,
            'raw_paper_ref': self.raw_paper_ref,
            'confidence': self.confidence,
            'watermark': self.watermark()
        }


def extract_metadata_from_pdf(pdf_path: str | Path) -> Optional[PaperMetadata]:
    """
    Extract metadata from the first page of a PDF.
    
    Works for both Question Papers and Mark Schemes.
    
    Args:
        pdf_path: Path to the PDF file
        
    Returns:
        PaperMetadata object or None if extraction fails
    """
    pdf_path = Path(pdf_path)
    
    if not pdf_path.exists():
        print(f"[ERROR] PDF not found: {pdf_path}")
        return None
    
    try:
        doc = fitz.open(str(pdf_path))
        
        # Get text from first page (sometimes metadata spans first 2 pages)
        first_page_text = doc[0].get_text()
        second_page_text = doc[1].get_text() if len(doc) > 1 else ""
        combined_text = first_page_text + "\n" + second_page_text
        
        doc.close()
        
        # Determine paper type (QP vs MS)
        paper_type = _detect_paper_type(combined_text, pdf_path)
        
        # Extract based on paper type
        if paper_type == "MS":
            return _extract_markscheme_metadata(combined_text, pdf_path)
        else:
            return _extract_question_paper_metadata(combined_text, pdf_path)
            
    except Exception as e:
        print(f"[ERROR] Failed to extract metadata from {pdf_path}: {e}")
        return None


def _detect_paper_type(text: str, pdf_path: Path) -> str:
    """Detect if this is a Question Paper or Mark Scheme"""
    # Check text content
    if "Mark Scheme" in text or "mark scheme" in text.lower():
        return "MS"
    
    # Check filename
    filename = pdf_path.name.lower()
    if "_ms" in filename or "ms.pdf" in filename or "markscheme" in filename:
        return "MS"
    
    return "QP"


def _extract_question_paper_metadata(text: str, pdf_path: Path) -> Optional[PaperMetadata]:
    """
    Extract metadata from Question Paper first page.
    
    Example content:
    - Paper reference: 4MB1/01R
    - Date: Tuesday 14 May 2024
    - Title: Mathematics B PAPER 1R
    """
    confidence = 0.0
    subject_code = None
    year = None
    session = None
    paper_number = None
    raw_paper_ref = None
    
    # Pattern 1: Paper reference like "4MB1/01R" or "4MB1/02"
    paper_ref_pattern = re.compile(r'(\d[A-Z]{2}\d)/(\d+[A-Z]?)', re.IGNORECASE)
    match = paper_ref_pattern.search(text)
    if match:
        subject_code = match.group(1).upper()
        raw_paper_ref = f"{subject_code}/{match.group(2)}"
        # Extract paper number from reference (01R -> 1R, 02 -> 2)
        paper_num_str = match.group(2).lstrip('0')
        paper_number = paper_num_str if paper_num_str else "1"
        confidence += 0.4
    
    # Pattern 2: Year from date like "14 May 2024" or "Summer 2024"
    year_patterns = [
        re.compile(r'\d{1,2}\s+\w+\s+(20\d{2})'),  # "14 May 2024"
        re.compile(r'(Summer|Winter|Spring|Autumn)\s+(20\d{2})'),  # "Summer 2024"
        re.compile(r'(20\d{2})\s+examination'),  # "2024 examination"
    ]
    
    for pattern in year_patterns:
        match = pattern.search(text)
        if match:
            year_str = match.group(2) if match.lastindex >= 2 else match.group(1)
            if year_str.isdigit():
                year = int(year_str)
                confidence += 0.3
                break
    
    # Pattern 3: Session from month/season
    session = _detect_session(text)
    if session:
        confidence += 0.3
    
    # Fallback: Extract from folder structure if not found
    if not subject_code or not year or not session:
        fallback = _extract_from_path(pdf_path)
        if not subject_code:
            subject_code = fallback.get('subject_code', '4MB1')
        if not year:
            year = fallback.get('year', 2024)
        if not session:
            session = fallback.get('session', 'Jun')
        if not paper_number:
            paper_number = fallback.get('paper_number', '1')
    
    if not raw_paper_ref:
        raw_paper_ref = f"{subject_code}/{paper_number}"
    
    return PaperMetadata(
        subject_code=subject_code or '4MB1',
        year=year or 2024,
        session=session or 'Jun',
        paper_number=paper_number or '1',
        paper_type='QP',
        raw_paper_ref=raw_paper_ref or '',
        confidence=min(confidence, 1.0)
    )


def _extract_markscheme_metadata(text: str, pdf_path: Path) -> Optional[PaperMetadata]:
    """
    Extract metadata from Mark Scheme first page.
    
    Example content:
    - Title: Mark Scheme (Results) Summer 2024
    - Subject: Pearson Edexcel International GCSE In Mathematics B (4MB1) Paper 01R
    """
    confidence = 0.0
    subject_code = None
    year = None
    session = None
    paper_number = None
    raw_paper_ref = None
    
    # Pattern 1: Season + Year like "Summer 2024" or "January 2023"
    season_year_pattern = re.compile(r'(Summer|Winter|January|Jan|May|June|Jun|October|Oct|November|Nov)\s*(20\d{2})', re.IGNORECASE)
    match = season_year_pattern.search(text)
    if match:
        season_word = match.group(1).lower()
        year = int(match.group(2))
        session = _season_word_to_session(season_word)
        confidence += 0.4
    
    # Pattern 2: Subject code like "(4MB1)" or "4MB1"
    subject_pattern = re.compile(r'\((\d[A-Z]{2}\d)\)|(\d[A-Z]{2}\d)[^/\d]', re.IGNORECASE)
    match = subject_pattern.search(text)
    if match:
        subject_code = (match.group(1) or match.group(2)).upper()
        confidence += 0.3
    
    # Pattern 3: Paper number like "Paper 01R" or "Paper 1"
    paper_pattern = re.compile(r'Paper\s*(\d+[A-Z]?)', re.IGNORECASE)
    match = paper_pattern.search(text)
    if match:
        paper_num_str = match.group(1).lstrip('0')
        paper_number = paper_num_str if paper_num_str else "1"
        confidence += 0.3
    
    # Fallback: Extract from folder structure
    if not subject_code or not year or not session:
        fallback = _extract_from_path(pdf_path)
        if not subject_code:
            subject_code = fallback.get('subject_code', '4MB1')
        if not year:
            year = fallback.get('year', 2024)
        if not session:
            session = fallback.get('session', 'Jun')
        if not paper_number:
            paper_number = fallback.get('paper_number', '1')
    
    raw_paper_ref = f"{subject_code}/{paper_number}" if subject_code and paper_number else ''
    
    return PaperMetadata(
        subject_code=subject_code or '4MB1',
        year=year or 2024,
        session=session or 'Jun',
        paper_number=paper_number or '1',
        paper_type='MS',
        raw_paper_ref=raw_paper_ref,
        confidence=min(confidence, 1.0)
    )


def _detect_session(text: str) -> Optional[str]:
    """Detect session from text content"""
    text_lower = text.lower()
    
    # Check for explicit months
    if any(m in text_lower for m in ['may', 'june', 'jun']):
        return 'Jun'
    elif any(m in text_lower for m in ['october', 'october', 'november', 'nov']):
        return 'Nov'
    elif any(m in text_lower for m in ['january', 'jan']):
        return 'Jan'
    
    # Check for season words
    if 'summer' in text_lower:
        return 'Jun'
    elif 'winter' in text_lower or 'autumn' in text_lower:
        return 'Nov'
    
    return None


def _season_word_to_session(season_word: str) -> str:
    """Convert season/month word to standard session code"""
    season_word = season_word.lower()
    
    if season_word in ['summer', 'may', 'june', 'jun']:
        return 'Jun'
    elif season_word in ['winter', 'autumn', 'october', 'oct', 'november', 'nov']:
        return 'Nov'
    elif season_word in ['january', 'jan', 'spring']:
        return 'Jan'
    
    return 'Jun'  # Default


def _extract_from_path(pdf_path: Path) -> Dict:
    """
    Fallback: Extract metadata from file path.
    Expected structure: data/raw/IGCSE/Maths B/2024/May-Jun/Paper 1.pdf
    """
    parts = pdf_path.parts
    result = {}
    
    # Find year (4-digit number)
    for part in parts:
        if part.isdigit() and len(part) == 4:
            result['year'] = int(part)
            break
    
    # Find session from folder name
    for part in parts:
        part_lower = part.lower()
        if 'may' in part_lower or 'jun' in part_lower:
            result['session'] = 'Jun'
            break
        elif 'oct' in part_lower or 'nov' in part_lower:
            result['session'] = 'Nov'
            break
        elif 'jan' in part_lower:
            result['session'] = 'Jan'
            break
    
    # Find paper number from filename
    filename = pdf_path.stem
    match = re.search(r'Paper\s*(\d+)', filename, re.IGNORECASE)
    if match:
        result['paper_number'] = match.group(1)
    
    # Subject code - hardcoded for Maths B
    if 'maths b' in str(pdf_path).lower():
        result['subject_code'] = '4MB1'
    
    return result


def extract_all_from_directory(directory: str | Path) -> Dict[str, PaperMetadata]:
    """
    Extract metadata from all PDFs in a directory (recursively).
    
    Returns:
        Dict mapping file path to PaperMetadata
    """
    directory = Path(directory)
    results = {}
    
    for pdf_file in directory.rglob("*.pdf"):
        metadata = extract_metadata_from_pdf(pdf_file)
        if metadata:
            results[str(pdf_file)] = metadata
    
    return results


def validate_metadata_against_path(metadata: PaperMetadata, pdf_path: Path) -> Tuple[bool, list]:
    """
    Validate extracted metadata against folder structure.
    
    Returns:
        (is_valid, list_of_warnings)
    """
    warnings = []
    path_metadata = _extract_from_path(pdf_path)
    
    if path_metadata.get('year') and metadata.year != path_metadata['year']:
        warnings.append(f"Year mismatch: PDF says {metadata.year}, path says {path_metadata['year']}")
    
    if path_metadata.get('session') and metadata.session != path_metadata['session']:
        warnings.append(f"Session mismatch: PDF says {metadata.session}, path says {path_metadata['session']}")
    
    return len(warnings) == 0, warnings


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Extract paper metadata from PDF")
    parser.add_argument("pdf_path", help="Path to PDF file or directory")
    parser.add_argument("--validate", action="store_true", help="Validate against path structure")
    args = parser.parse_args()
    
    path = Path(args.pdf_path)
    
    if path.is_file():
        metadata = extract_metadata_from_pdf(path)
        if metadata:
            print(f"\n{'='*60}")
            print(f"FILE: {path.name}")
            print(f"{'='*60}")
            print(f"Subject Code: {metadata.subject_code}")
            print(f"Year: {metadata.year}")
            print(f"Session: {metadata.session}")
            print(f"Paper Number: {metadata.paper_number}")
            print(f"Paper Type: {metadata.paper_type}")
            print(f"Raw Reference: {metadata.raw_paper_ref}")
            print(f"Confidence: {metadata.confidence:.0%}")
            print(f"\nWATERMARK: {metadata.watermark()}")
            
            if args.validate:
                is_valid, warnings = validate_metadata_against_path(metadata, path)
                if warnings:
                    print(f"\n⚠️  VALIDATION WARNINGS:")
                    for w in warnings:
                        print(f"   - {w}")
                else:
                    print(f"\n✅ Validation passed")
    
    elif path.is_dir():
        print(f"\nScanning directory: {path}")
        results = extract_all_from_directory(path)
        
        print(f"\nFound {len(results)} PDFs:")
        for pdf_path, metadata in sorted(results.items()):
            print(f"  {Path(pdf_path).name}: {metadata.watermark()}")
    
    else:
        print(f"[ERROR] Path not found: {path}")
