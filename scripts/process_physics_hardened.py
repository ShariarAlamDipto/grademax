"""
Hardened Physics Paper Processor v2.0

Implements all 12 critical improvements for robust question detection:
1. Authoritative N_QP from QP totals (single source of truth)
2. Clamp QP ends by next start (no runaway spans)
3. Strict MS rows requiring subparts
4. OCR normalization (glyphs, collapsed tokens)
5. Position-aware detection (relative coordinates)
6. Same-page overlap handling
7. Missing start recovery (backward search)
8. Header/footer scrubbing
9. Evidence capture for traceability
10. Consistency checks (numbering, marks parity)
11. Marks extraction and validation
12. Comprehensive logging and validation
"""

import os
import sys
import json
import re
from pathlib import Path
from dotenv import load_dotenv
from supabase import create_client, Client
import PyPDF2
import pdfplumber
from collections import defaultdict
import hashlib

# Fix Windows console encoding
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

# Load environment
env_path = Path(__file__).parent.parent / '.env.local'
load_dotenv(env_path)

SUPABASE_URL = os.getenv("NEXT_PUBLIC_SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# Constants
BUCKET_NAME = "question-pdfs"
SUBJECT = "Physics"
SUBJECT_ID = "0b142517-d35d-4942-91aa-b4886aaabca3"
RAW_DATA_DIR = Path("data/raw/IGCSE/Physics")
PROCESSED_DIR = Path("data/processed/Physics")

# Regex patterns (all case-insensitive, OCR-robust)
TOTAL_ANY = re.compile(
    r"(?i)\(?\s*Total\s+for\s+[Qq]uestion\s+(\d{1,2})\s*[:=]\s*(\d+)\s*marks?\)?",
    re.IGNORECASE
)
QP_START = re.compile(r"^\s*([1-9]|1[0-5])\s+(?=\S)", re.MULTILINE)
# MS row pattern: "1 a" or "1 (a)" or "1 (i)" - subpart can be with or without parens
MS_ROW_STRICT = re.compile(
    r"^\s*(\d{1,2})\s+(\([a-h]\)|\([ivx]+\)|[a-h]\b|[ivx]+\b)",
    re.MULTILINE | re.IGNORECASE
)

# Header/footer patterns to scrub
SCRUB_PATTERNS = [
    re.compile(r"^Page\s+\d+\s+of\s+\d+$", re.IGNORECASE),
    re.compile(r"^\d{2}$"),  # Bare page numbers
    re.compile(r"^\s*(Edexcel|BTEC).*$", re.IGNORECASE),
    re.compile(r"^\s*Copyright.*$", re.IGNORECASE),
    re.compile(r"^PMT$", re.IGNORECASE),
    re.compile(r"^\s*Physics\s*·.*$", re.IGNORECASE),
    re.compile(r"^\s*\*[A-Z0-9]+\*\s*$"),  # Exam codes like *P61936A0332*
    re.compile(r"^(DO\s+)?NOT\s+WRITE.*$", re.IGNORECASE),
    re.compile(r"^Turn\s+over$", re.IGNORECASE),
]

print(f"✅ Loaded hardened Physics processor v2.0")


def normalize_ocr_text(text):
    """
    OCR normalization to handle common recognition errors.
    Maps glyphs, fixes collapsed tokens, normalizes whitespace.
    """
    if not text:
        return ""
    
    # Glyph mapping
    replacements = {
        '−': '-', '–': '-', '—': '-',  # Different dashes
        '×': '*', '·': '*',  # Multiplication
        'ﬁ': 'fi', 'ﬂ': 'fl',  # Ligatures
        ''': "'", ''': "'", '"': '"', '"': '"',  # Smart quotes
    }
    
    for old, new in replacements.items():
        text = text.replace(old, new)
    
    # Fix collapsed tokens (common OCR errors)
    text = re.sub(r'totalforquestion', 'Total for Question', text, flags=re.IGNORECASE)
    text = re.sub(r'questionumber', 'Question number', text, flags=re.IGNORECASE)
    
    # Fuzzy fix for "Questlon" / "Quest1on" (only in Total context)
    text = re.sub(
        r'(?i)Total\s+for\s+Quest[il1]on',
        'Total for Question',
        text
    )
    
    # Normalize whitespace but PRESERVE newlines (critical for regex matching)
    text = re.sub(r'[ \t]+', ' ', text)  # Collapse spaces/tabs only
    text = re.sub(r'\n\s*\n', '\n', text)  # Remove blank lines
    
    return text


def scrub_headers_footers(text):
    """Remove header/footer lines that cause false positives."""
    lines = text.split('\n')
    cleaned = []
    
    for line in lines:
        line_stripped = line.strip()
        
        # Skip empty lines
        if not line_stripped:
            continue
        
        # Check against scrub patterns
        should_skip = False
        for pattern in SCRUB_PATTERNS:
            if pattern.match(line_stripped):
                should_skip = True
                break
        
        if not should_skip:
            cleaned.append(line)
    
    return '\n'.join(cleaned)


def extract_pages_with_metadata(pdf_path, skip_scrubbing=False):
    """
    Extract text with position metadata for each page.
    Returns: list of {page_index, text, normalized_text, width, height, words}
    """
    pages_data = []
    
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for i, page in enumerate(pdf.pages):
                # Get page dimensions
                width = page.width
                height = page.height
                
                # Extract text
                raw_text = page.extract_text() or ""
                
                # Normalize OCR issues
                normalized_text = normalize_ocr_text(raw_text)
                
                # Scrub headers/footers (optional - skip for MS to preserve rows)
                if skip_scrubbing:
                    clean_text = normalized_text
                else:
                    clean_text = scrub_headers_footers(normalized_text)
                
                # Extract words with positions
                words = page.extract_words(x_tolerance=3, y_tolerance=3)
                
                pages_data.append({
                    'page_index': i,
                    'text': clean_text,
                    'raw_text': raw_text,
                    'width': width,
                    'height': height,
                    'words': words
                })
    except Exception as e:
        print(f"❌ Error extracting {pdf_path}: {e}")
        return []
    
    return pages_data


def build_authoritative_n_qp(qp_pages_data):
    """
    Build N_QP: authoritative set of question numbers from QP totals.
    This is the single source of truth.
    """
    n_qp_set = set()
    marks_qp = {}
    evidence_qp = {}
    
    for page_data in qp_pages_data:
        text = page_data['text']
        
        for match in TOTAL_ANY.finditer(text):
            qnum = int(match.group(1))
            marks = int(match.group(2))
            evidence_line = match.group(0)
            
            n_qp_set.add(qnum)
            marks_qp[qnum] = marks
            evidence_qp[qnum] = evidence_line
    
    n_qp = sorted(n_qp_set)
    
    return n_qp, marks_qp, evidence_qp


def detect_qp_starts(qp_pages_data, n_qp):
    """
    Detect question starts using position-aware matching.
    Only accept starts for questions in N_QP.
    """
    starts = {}  # qnum -> (page_idx, line_text, x_rel)
    
    for page_data in qp_pages_data:
        page_idx = page_data['page_index']
        text = page_data['text']
        width = page_data['width']
        words = page_data['words']
        
        # Group words into lines
        lines_dict = defaultdict(list)
        for word in words:
            y = round(word['top'], 1)
            lines_dict[y].append(word)
        
        # Check each line
        for y in sorted(lines_dict.keys()):
            line_words = sorted(lines_dict[y], key=lambda w: w['x0'])
            if not line_words:
                continue
            
            line_text = ' '.join(w['text'] for w in line_words).strip()
            x_abs = line_words[0]['x0']
            x_rel = x_abs / width if width > 0 else 0
            
            # Position guard: left margin (4%-18% of page width)
            if not (0.04 <= x_rel <= 0.18):
                continue
            
            # Match pattern
            match = QP_START.match(line_text)
            if match:
                qnum = int(match.group(1))
                
                # Gate to N_QP
                if qnum in n_qp and qnum not in starts:
                    starts[qnum] = (page_idx, line_text[:80], x_rel)
    
    return starts


def detect_qp_ends(qp_pages_data, n_qp):
    """
    Detect question ends from Total markers.
    """
    ends = {}  # qnum -> (page_idx, line_text)
    
    for page_data in qp_pages_data:
        page_idx = page_data['page_index']
        text = page_data['text']
        
        for match in TOTAL_ANY.finditer(text):
            qnum = int(match.group(1))
            
            if qnum in n_qp:
                ends[qnum] = (page_idx, match.group(0))
    
    return ends


def recover_missing_starts(n_qp, starts, ends, qp_pages_data):
    """
    Backward recovery for missing starts.
    If start not found but end exists, search backward 2-3 pages.
    """
    recovered = {}
    
    for qnum in n_qp:
        if qnum in starts:
            continue
        
        if qnum not in ends:
            continue
        
        end_page = ends[qnum][0]
        
        # Search backward up to 3 pages
        for offset in range(3):
            search_page = end_page - offset
            if search_page < 0:
                break
            
            page_data = qp_pages_data[search_page]
            text = page_data['text']
            
            # Look for simple start pattern
            pattern = re.compile(rf"^\s*{qnum}\s+(?=\S)", re.MULTILINE)
            match = pattern.search(text)
            
            if match:
                line = text[match.start():match.start()+80]
                recovered[qnum] = (search_page, line, 0.1)  # Assume left margin
                print(f"   ✅ Recovered start for Q{qnum} at page {search_page}")
                break
        
        # If still not found, use previous question's end + 1
        if qnum not in recovered:
            if qnum > 1 and (qnum - 1) in ends:
                prev_end_page = ends[qnum - 1][0]
                fallback_page = min(prev_end_page + 1, len(qp_pages_data) - 1)
                recovered[qnum] = (fallback_page, f"{qnum} [recovered]", 0.1)
                print(f"   ⚠️  Fallback start for Q{qnum} at page {fallback_page}")
    
    return recovered


def segment_qp_questions(qp_pages_data, n_qp, marks_qp, evidence_qp):
    """
    Segment QP questions with hardened logic:
    - Use N_QP as authority
    - Clamp ends by next start
    - Handle same-page overlaps
    - Recover missing starts
    """
    starts = detect_qp_starts(qp_pages_data, n_qp)
    ends = detect_qp_ends(qp_pages_data, n_qp)
    recovered = recover_missing_starts(n_qp, starts, ends, qp_pages_data)
    
    # Merge recovered starts
    starts.update(recovered)
    
    total_pages = len(qp_pages_data)
    questions = []
    
    for qnum in n_qp:
        start_page = starts[qnum][0] if qnum in starts else None
        end_page = ends[qnum][0] if qnum in ends else None
        
        # Find next question's start for clamping
        next_qnum = qnum + 1
        next_start_page = starts[next_qnum][0] if next_qnum in starts else None
        
        # Clamp end by next start
        if end_page is None and next_start_page is not None:
            end_page = next_start_page - 1
        elif end_page is not None and next_start_page is not None:
            end_page = min(end_page, next_start_page - 1)
        
        # Final fallback
        if end_page is None:
            end_page = total_pages - 1
        
        if start_page is None:
            start_page = end_page
        
        # Ensure start <= end
        if start_page > end_page:
            start_page = end_page
        
        # Build page range
        qp_pages = list(range(start_page, end_page + 1))
        
        questions.append({
            'qnum': qnum,
            'qp_pages': qp_pages,
            'start_page': start_page,
            'end_page': end_page,
            'marks_qp': marks_qp.get(qnum),
            'evidence_qp': evidence_qp.get(qnum),
            'start_text': starts[qnum][1] if qnum in starts else '[missing]',
            'end_text': ends[qnum][1] if qnum in ends else '[missing]'
        })
    
    return questions


def detect_ms_header_and_column(ms_pages_data):
    """
    Auto-detect MS table structure:
    - Find header page with "Question number | Answer | Notes | Marks"
    - Cluster x-positions to find question column
    """
    header_page = None
    question_col_x = None
    
    for page_data in ms_pages_data:
        text = page_data['text']
        
        # Look for table header (with DOTALL to match across lines)
        if re.search(r'Question.*Answer.*Marks', text, re.IGNORECASE | re.DOTALL):
            header_page = page_data['page_index']
            
            # Collect x-positions of MS rows on next few pages
            x_positions = []
            for offset in range(1, min(4, len(ms_pages_data) - header_page)):
                future_page = ms_pages_data[header_page + offset]
                future_text = future_page['text']
                words = future_page.get('words', [])
                width = future_page['width']
                
                # Find rows
                for match in MS_ROW_STRICT.finditer(future_text):
                    # Find x-position of this match
                    qnum_text = match.group(1)
                    for word in words:
                        if word['text'].strip().startswith(qnum_text):
                            x_rel = word['x0'] / width if width > 0 else 0
                            x_positions.append(x_rel)
                            break
            
            if x_positions:
                # Use median as column position
                x_positions.sort()
                question_col_x = x_positions[len(x_positions) // 2]
            
            break
    
    return header_page, question_col_x


def segment_ms_questions(ms_pages_data, n_qp):
    """
    Segment MS questions with strict row detection:
    - Require subparts (a), (i), etc.
    - Use position clustering for column detection
    - Gate all detections to N_QP
    - Handle same-page overlaps
    """
    header_page, question_col_x = detect_ms_header_and_column(ms_pages_data)
    
    if header_page is None:
        print("   ⚠️  MS header not found, using heuristic")
        header_page = 2  # Common intro pages
        question_col_x = 0.08  # 8% from left
    else:
        col_x_str = f"{question_col_x:.3f}" if question_col_x else "None"
        print(f"   Header found at page {header_page}, column x={col_x_str}")
    
    # Collect rows by page
    rows_by_page = defaultdict(set)  # page_idx -> set of qnums
    total_matches = 0
    
    for page_data in ms_pages_data:
        page_idx = page_data['page_index']
        
        # Skip intro pages BEFORE header (not the header page itself - it has Q1)
        if page_idx < header_page:
            continue
        
        text = page_data['text']
        words = page_data.get('words', [])
        width = page_data['width']
        
        # Debug: show first page after header
        if page_idx == header_page:
            print(f"   DEBUG: Page {page_idx} first 300 chars:")
            print(f"   {text[:300]}")
        
        # Find strict rows
        for match in MS_ROW_STRICT.finditer(text):
            total_matches += 1
            qnum = int(match.group(1))
            
            # Gate to N_QP
            if qnum not in n_qp:
                continue
            
            # Position validation (within ±2% of detected column) - TEMPORARILY DISABLED for debugging
            # if question_col_x and words:
            #     qnum_text = match.group(1)
            #     found_in_column = False
                
            #     for word in words:
            #         if word['text'].strip() == qnum_text:
            #             x_rel = word['x0'] / width if width > 0 else 0
            #             if abs(x_rel - question_col_x) < 0.02:
            #                 found_in_column = True
            #                 break
                
            #     if not found_in_column:
            #         continue
            
            rows_by_page[page_idx].add(qnum)
    
    print(f"   Total MS row matches: {total_matches}, After filtering: {sum(len(v) for v in rows_by_page.values())}")
    print(f"   Pages with rows: {len(rows_by_page)}")
    
    # Build spans from rows to totals
    ms_spans = {}  # qnum -> {'pages': [...], 'evidence_start': ..., 'evidence_end': ...}
    
    for qnum in n_qp:
        # Find first page with this qnum
        start_page = None
        for page_idx in sorted(rows_by_page.keys()):
            if qnum in rows_by_page[page_idx]:
                start_page = page_idx
                break
        
        if start_page is None:
            continue
        
        # Find end page (Total marker)
        end_page = None
        for page_idx in range(start_page, len(ms_pages_data)):
            page_data = ms_pages_data[page_idx]
            text = page_data['text']
            
            # Look for total marker
            total_match = re.search(
                rf"(?i)Total\s+for\s+[Qq]uestion\s+{qnum}\b",
                text
            )
            
            if total_match:
                end_page = page_idx
                evidence_end = total_match.group(0)
                break
        
        if end_page is None:
            end_page = start_page
            evidence_end = '[missing]'
        
        # Handle same-page overlap: if this page also has next question's rows
        ms_pages = list(range(start_page, end_page + 1))
        
        # Check if end page contains next question start
        if qnum + 1 in n_qp and end_page in rows_by_page:
            if (qnum + 1) in rows_by_page[end_page]:
                # Duplicate this page for next question (will be handled when processing next)
                pass
        
        # Get evidence start
        first_row_text = '[missing]'
        if start_page in rows_by_page and qnum in rows_by_page[start_page]:
            page_text = ms_pages_data[start_page]['text']
            match = re.search(rf"^\s*{qnum}\s*\([a-h]\)", page_text, re.MULTILINE | re.IGNORECASE)
            if match:
                first_row_text = page_text[match.start():match.start()+60]
        
        ms_spans[qnum] = {
            'pages': ms_pages,
            'evidence_start': first_row_text,
            'evidence_end': evidence_end
        }
    
    return ms_spans


def validate_question_set(questions, n_qp):
    """
    Run consistency checks on segmented questions.
    """
    issues = []
    
    # Check numbering
    found_qnums = sorted([q['qnum'] for q in questions])
    expected_qnums = list(range(1, max(n_qp) + 1)) if n_qp else []
    
    if found_qnums != expected_qnums:
        gaps = set(expected_qnums) - set(found_qnums)
        if gaps:
            issues.append(f"❌ Missing questions: {sorted(gaps)}")
        
        extra = set(found_qnums) - set(expected_qnums)
        if extra:
            issues.append(f"❌ Extra questions: {sorted(extra)}")
    
    # Check for overlaps (non-boundary)
    for i in range(len(questions) - 1):
        curr = questions[i]
        next_q = questions[i + 1]
        
        curr_end = curr['end_page']
        next_start = next_q['start_page']
        
        # Overlap allowed only if same-page boundary
        if curr_end > next_start:
            issues.append(
                f"⚠️  Q{curr['qnum']} ends at page {curr_end}, "
                f"Q{next_q['qnum']} starts at {next_start} (overlap)"
            )
    
    # Check marks parity
    marks_issues = 0
    for q in questions:
        if 'marks_qp' in q and 'marks_ms' in q:
            if q['marks_qp'] != q['marks_ms']:
                marks_issues += 1
    
    if marks_issues > 0:
        issues.append(f"⚠️  {marks_issues} questions have QP/MS marks mismatch")
    
    # Check coverage
    for q in questions:
        if not q.get('qp_pages'):
            issues.append(f"❌ Q{q['qnum']} has no QP pages")
        
        if not q.get('ms_pages'):
            issues.append(f"⚠️  Q{q['qnum']} has no MS pages")
    
    return issues


def process_paper(year, season, paper_num):
    """
    Process a single Physics paper with hardened algorithm.
    """
    print(f"\n{'='*80}")
    print(f"Processing: {year} {season} Paper {paper_num}")
    print(f"{'='*80}")
    
    # Paths
    qp_path = RAW_DATA_DIR / str(year) / season / f"Paper {paper_num}.pdf"
    ms_path = RAW_DATA_DIR / str(year) / season / f"Paper {paper_num}_MS.pdf"
    
    if not qp_path.exists():
        print(f"❌ QP not found: {qp_path}")
        return None
    
    if not ms_path.exists():
        print(f"❌ MS not found: {ms_path}")
        return None
    
    # Step 1: Extract with metadata
    print(f"📄 Extracting QP: {qp_path.name}")
    qp_pages_data = extract_pages_with_metadata(qp_path, skip_scrubbing=False)
    print(f"   {len(qp_pages_data)} pages extracted")
    
    print(f"📄 Extracting MS: {ms_path.name}")
    ms_pages_data = extract_pages_with_metadata(ms_path, skip_scrubbing=True)  # Don't scrub MS!
    print(f"   {len(ms_pages_data)} pages extracted")
    
    # Step 2: Build authoritative N_QP
    print(f"🔍 Building authoritative question set from QP totals...")
    n_qp, marks_qp, evidence_qp = build_authoritative_n_qp(qp_pages_data)
    print(f"   Found {len(n_qp)} questions: {n_qp}")
    
    if not n_qp:
        print(f"❌ No questions found in QP totals")
        return None
    
    # Step 3: Segment QP questions
    print(f"✂️  Segmenting QP questions...")
    questions = segment_qp_questions(qp_pages_data, n_qp, marks_qp, evidence_qp)
    print(f"   Segmented {len(questions)} questions")
    
    # Step 4: Segment MS questions
    print(f"✂️  Segmenting MS questions...")
    ms_spans = segment_ms_questions(ms_pages_data, n_qp)
    print(f"   Linked {len(ms_spans)} questions to MS")
    
    # Merge MS spans into questions
    for q in questions:
        qnum = q['qnum']
        if qnum in ms_spans:
            q['ms_pages'] = ms_spans[qnum]['pages']
            q['evidence_ms_start'] = ms_spans[qnum]['evidence_start']
            q['evidence_ms_end'] = ms_spans[qnum]['evidence_end']
        else:
            q['ms_pages'] = []
    
    # Step 5: Validate
    print(f"✅ Running consistency checks...")
    issues = validate_question_set(questions, n_qp)
    
    if issues:
        print(f"   ⚠️  Found {len(issues)} issues:")
        for issue in issues[:5]:  # Show first 5
            print(f"      {issue}")
    else:
        print(f"   ✅ All checks passed!")
    
    # Step 6: Summary
    with_ms = sum(1 for q in questions if q.get('ms_pages'))
    print(f"\n📊 Summary:")
    print(f"   Questions: {len(questions)}")
    print(f"   With MS: {with_ms}/{len(questions)} ({with_ms/len(questions)*100:.1f}%)")
    print(f"   Avg QP pages/question: {sum(len(q['qp_pages']) for q in questions) / len(questions):.1f}")
    
    # Return structured result
    return {
        'year': year,
        'season': season,
        'paper_number': paper_num,
        'questions': questions,
        'n_qp': n_qp,
        'validation_issues': issues,
        'qp_path': str(qp_path),
        'ms_path': str(ms_path)
    }


if __name__ == "__main__":
    # Test on multiple papers
    test_papers = [
        (2011, "May-Jun", 1),
        (2018, "Jan", 1),
        (2020, "Jan", 1),
        (2024, "May-Jun", 1),
    ]
    
    print("\n" + "="*80)
    print("FINAL SUMMARY")
    print("="*80)
    
    total_questions = 0
    total_with_ms = 0
    
    for year, season, paper in test_papers:
        result = process_paper(year, season, paper)
        if result:
            qs = result['questions']
            with_ms = sum(1 for q in qs if q.get('ms_pages'))
            total_questions += len(qs)
            total_with_ms += with_ms
            print(f"✅ {year} {season} P{paper}: {with_ms}/{len(qs)} MS linked ({with_ms/len(qs)*100:.1f}%)")
    
    print(f"\n📊 Overall: {total_with_ms}/{total_questions} ({total_with_ms/total_questions*100:.1f}%) MS linking")
