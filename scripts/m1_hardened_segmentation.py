"""
IAL Mechanics 1 Hardened Segmentation Processor
Based on production-grade prompt pack with all improvements:
- Auto-margin detection
- Dual-authority N_QP (QP or MS)
- MS marks summing with OR-block handling
- Continuation hints
- Robust normalization & scrubbing
"""

import os
import re
import json
import pdfplumber
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Set
from statistics import median
from collections import defaultdict
from dataclasses import dataclass
from PyPDF2 import PdfReader, PdfWriter

@dataclass
class PageData:
    index: int
    text: str
    raw_text: str
    width: float
    height: float
    words: List[Dict]
    lines: List[Dict]

class M1Processor:
    def __init__(self):
        # Regex patterns (hardened per prompt pack)
        # IAL M1 uses format: "Q1 (Total 6 marks)" which may span lines or have underscores
        self.QP_END_AUTHORITY = re.compile(
            r'Q(\d{1,2})\s*(?:\n|\r\n?|\s|_)*\(Total\s+(\d+)\s+marks?\)',
            re.IGNORECASE | re.MULTILINE
        )
        # Question starts: "1. " or "2. " at line start
        self.QP_START = re.compile(r'(?m)^(\d{1,2})\.\s+')
        self.MS_HEADER = re.compile(r'(?i)Question\s*Number.*Scheme.*Marks(?:.*Notes)?')
        # MS row pattern: Allow no space between number and subpart (e.g., "6(a)")
        self.MS_ROW = re.compile(
            r'(?m)^\s*(\d{1,2})\s*\(([a-h]|ix|iv|v?i{0,3})\)',
            re.IGNORECASE
        )
        self.MS_END = re.compile(r'(?i)Total\s+for\s+Question\s+(\d{1,2})')
        
        # Continuation hints
        self.RE_CONT = re.compile(r'(?i)\bQuestion\s+(\d{1,2})\s+(continued|contd\.?)\b')
        self.RE_CONT_NEXT = re.compile(r'(?i)\b(continued|continues)\s+on\s+next\s+page\b')
        
        # Marks extraction
        self.RE_MARK_EOL = re.compile(r'(?<![A-Za-z])(\d{1,2})(?![A-Za-z0-9])$')
        self.BLACKLIST_NEAR = re.compile(r'\b(MP\d+|AO\d+|ECF|QWC|BOD|penalty|ft)\b', re.I)
        self.OR_LINE = re.compile(r'^\s*(or|alternatively|any one of|either|accept EITHER|award max of)\b', re.I)
        
    def normalize_ocr_text(self, text: str) -> str:
        """Hardened normalization per prompt pack"""
        # 1) Glyph mapping - avoid quote conflicts
        text = text.replace('−', '-').replace('–', '-').replace('—', '-')
        text = text.replace('×', '*').replace('·', '*')
        text = text.replace('ﬁ', 'fi').replace('ﬂ', 'fl')
        # Handle smart quotes carefully
        text = text.replace('\u201c', '"').replace('\u201d', '"')  # ""
        text = text.replace('\u2018', "'").replace('\u2019', "'")  # ''
        text = text.replace('\u2032', "'").replace('\u2033', '"')  # ′″
        
        # 2) Fix common OCR collapses
        text = re.sub(r'total\s*for\s*quest(?:il|i|1)on', 'Total for Question', text, flags=re.I)
        
        # 3) De-hyphenate line breaks
        text = re.sub(r'([A-Za-z0-9])-\n([A-Za-z0-9])', r'\1\2', text)
        
        # 4) Collapse spaces/tabs only; keep newlines
        text = re.sub(r'[ \t]+', ' ', text)
        text = re.sub(r'\n\s*\n', '\n', text)  # Remove blank lines
        
        return text
    
    def scrub_qp_headers(self, text: str) -> str:
        """Aggressive QP header/footer scrubbing"""
        lines = []
        for L in text.splitlines():
            if re.search(r'^\s*Page\s+\d+\s+of\s+\d+\s*$', L): continue
            if re.search(r'^\s*(Edexcel|Pearson|BTEC|Copyright)\b', L, re.I): continue
            if re.search(r'^\s*\*[A-Z0-9]+\*\s*$', L): continue  # *PxxxxxAyyzz*
            if re.search(r'^\s*(DO\s+NOT\s+WRITE|Turn\s+over)\s*$', L, re.I): continue
            lines.append(L)
        return '\n'.join(lines)
    
    def extract_pages_with_metadata(self, pdf_path: str, skip_scrubbing: bool = False) -> List[PageData]:
        """Extract pages with full metadata for position-aware detection"""
        pages_data = []
        
        with pdfplumber.open(pdf_path) as pdf:
            for i, page in enumerate(pdf.pages):
                width = page.width
                height = page.height
                
                # Extract text
                raw_text = page.extract_text() or ""
                
                # Normalize
                normalized = self.normalize_ocr_text(raw_text)
                
                # Conditional scrubbing
                clean_text = normalized if skip_scrubbing else self.scrub_qp_headers(normalized)
                
                # Extract words and lines for position-aware detection
                words = page.extract_words(x_tolerance=3, y_tolerance=3) or []
                
                # Group words into lines (simple grouping by y-position)
                lines = self._group_words_into_lines(words, width)
                
                pages_data.append(PageData(
                    index=i,
                    text=clean_text,
                    raw_text=raw_text,
                    width=width,
                    height=height,
                    words=words,
                    lines=lines
                ))
        
        return pages_data
    
    def _group_words_into_lines(self, words: List[Dict], page_width: float) -> List[Dict]:
        """Group words into lines by y-position"""
        if not words:
            return []
        
        # Sort by top position
        sorted_words = sorted(words, key=lambda w: (w['top'], w['x0']))
        
        lines = []
        current_line = {'words': [], 'top': sorted_words[0]['top'], 'text': ''}
        y_threshold = 3  # pixels
        
        for word in sorted_words:
            if abs(word['top'] - current_line['top']) <= y_threshold:
                current_line['words'].append(word)
            else:
                # Finalize current line
                current_line['text'] = ' '.join(w['text'] for w in current_line['words'])
                current_line['leftmost_word'] = min(current_line['words'], key=lambda w: w['x0'])
                lines.append(current_line)
                
                # Start new line
                current_line = {'words': [word], 'top': word['top'], 'text': ''}
        
        # Add last line
        if current_line['words']:
            current_line['text'] = ' '.join(w['text'] for w in current_line['words'])
            current_line['leftmost_word'] = min(current_line['words'], key=lambda w: w['x0'])
            lines.append(current_line)
        
        return lines
    
    def _mad(self, vals: List[float], m: Optional[float] = None) -> float:
        """Median Absolute Deviation"""
        if not vals:
            return 0.0
        m = m if m is not None else median(vals)
        return median([abs(v - m) for v in vals]) or 1e-6
    
    def auto_qp_left_margin(self, pages: List[PageData], allowed_qnums: Set[int]) -> Tuple[Tuple[float, float], Dict]:
        """Auto-detect left margin for question starts"""
        xs = []
        
        for p in pages:
            if not p.words or not p.width:
                continue
            
            for line in p.lines:
                m = self.QP_START.match(line['text'])
                if not m:
                    continue
                
                q = int(m.group(1))
                if q not in allowed_qnums:
                    continue
                
                x0 = line['leftmost_word']['x0'] / p.width
                xs.append(x0)
        
        if not xs:
            # Sane fallback
            return (0.04, 0.20), {'method': 'fallback', 'n': 0}
        
        # Median + MAD band (wider tolerance for IAL M1)
        med = median(xs)
        mad = self._mad(xs, med)
        band = max(0.05, 5.0 * mad)  # Wider band for position variations
        lo, hi = max(0.0, med - band), min(1.0, med + band)
        
        return (lo, hi), {'method': 'median_mad', 'median': med, 'mad': mad, 'n': len(xs)}
    
    def auto_ms_columns(self, ms_pages: List[PageData]) -> Dict:
        """Learn MS question and marks columns"""
        qx, mx = [], []
        
        for p in ms_pages:
            if not p.width:
                continue
            
            # Question column
            for line in p.lines:
                if self.MS_ROW.match(line['text']):
                    qx.append(line['leftmost_word']['x0'] / p.width)
            
            # Marks column (numeric tokens at far right)
            for w in p.words:
                t = w['text']
                if len(t) <= 3 and t.isdigit():
                    xrel = w['x0'] / p.width
                    if xrel > 0.55:  # Right side candidate
                        mx.append(xrel)
        
        def _window(xs):
            if not xs:
                return None
            med = median(xs)
            mad = self._mad(xs, med)
            return (max(0.0, med - 3*mad), min(1.0, med + 3*mad), {'median': med, 'mad': mad, 'n': len(xs)})
        
        return {
            'question_col': _window(qx),
            'marks_col': _window(mx)
        }
    
    def build_authoritative_n_qp(self, qp_pages: List[PageData], ms_pages: List[PageData]) -> Set[int]:
        """Dual-authority N_QP: prefer QP totals, fallback to MS"""
        n_qp = set()
        
        # Try QP totals first
        for page in qp_pages:
            for m in self.QP_END_AUTHORITY.finditer(page.text):
                qnum = int(m.group(1))
                if 1 <= qnum <= 20:  # Reasonable range
                    n_qp.add(qnum)
        
        if n_qp:
            print(f"   Built N_QP from QP totals: {sorted(n_qp)}")
            return n_qp
        
        # Fallback to MS first-column numbers
        print("   ⚠️  No QP totals found, using MS as authority...")
        for page in ms_pages:
            for m in self.MS_ROW.finditer(page.text):
                qnum = int(m.group(1))
                if 1 <= qnum <= 20:
                    n_qp.add(qnum)
        
        if n_qp:
            print(f"   Built N_QP from MS rows: {sorted(n_qp)}")
        else:
            print("   ❌ Could not build N_QP from QP or MS!")
        
        return n_qp
    
    def detect_qp_spans(self, qp_pages: List[PageData], n_qp: Set[int], margin_window: Tuple[float, float]) -> Dict[int, Dict]:
        """Detect QP question spans with clamping and continuation hints"""
        lo, hi = margin_window
        starts = {}
        ends = {}
        
        # Detect starts (position-aware)
        for page in qp_pages:
            for line in page.lines:
                m = self.QP_START.match(line['text'])
                if not m:
                    continue
                
                qnum = int(m.group(1))
                if qnum not in n_qp:
                    continue
                
                # Position validation
                x_rel = line['leftmost_word']['x0'] / page.width
                if not (lo <= x_rel <= hi):
                    continue
                
                if qnum not in starts:
                    starts[qnum] = page.index
        
        # Detect ends from totals
        for page in qp_pages:
            for m in self.QP_END_AUTHORITY.finditer(page.text):
                qnum = int(m.group(1))
                if qnum in n_qp:
                    ends[qnum] = page.index
        
        # Recover missing starts (search backward from end)
        for qnum in n_qp:
            if qnum in starts:
                continue
            if qnum not in ends:
                continue
            
            end_page = ends[qnum]
            for offset in range(3):
                search_page = end_page - offset
                if search_page < 0:
                    break
                
                pattern = re.compile(rf'^\s*{qnum}\s+(?=\S)', re.MULTILINE)
                if pattern.search(qp_pages[search_page].text):
                    starts[qnum] = search_page
                    break
            
            # Final fallback: use prev end + 1
            if qnum not in starts and qnum > 1 and (qnum - 1) in ends:
                starts[qnum] = ends[qnum - 1] + 1
        
        # Apply continuation hints
        for page in qp_pages:
            m = self.RE_CONT.search(page.text)
            if m:
                qnum = int(m.group(1))
                if qnum in n_qp and qnum in ends:
                    ends[qnum] = max(ends[qnum], page.index)
        
        # Build spans with clamping
        spans = {}
        sorted_qnums = sorted(n_qp)
        
        for i, qnum in enumerate(sorted_qnums):
            start = starts.get(qnum, 0)
            end = ends.get(qnum, len(qp_pages) - 1)
            
            # Clamp by next start
            if i + 1 < len(sorted_qnums):
                next_qnum = sorted_qnums[i + 1]
                if next_qnum in starts:
                    end = min(end, starts[next_qnum] - 1)
            
            spans[qnum] = {
                'start': start,
                'end': end,
                'pages': list(range(start, end + 1))
            }
        
        return spans
    
    def segment_ms_questions(self, ms_pages: List[PageData], n_qp: Set[int], columns: Dict) -> Dict[int, Dict]:
        """Segment MS with shared page handling"""
        # Find header page
        header_page = 0
        for i, page in enumerate(ms_pages):
            if self.MS_HEADER.search(page.text):
                header_page = i
                break
        
        # Get column windows
        qwin = columns.get('question_col')
        q_lo, q_hi = (qwin[0], qwin[1]) if qwin else (0.0, 0.25)
        
        # Collect rows by page
        rows_by_page = defaultdict(set)
        
        for page in ms_pages:
            if page.index < header_page:
                continue
            
            for m in self.MS_ROW.finditer(page.text):
                qnum = int(m.group(1))
                if qnum not in n_qp:
                    continue
                
                # Optional position validation (commented out for now - MS layouts vary)
                # x_rel = ... position check ...
                
                rows_by_page[page.index].add(qnum)
        
        # Build spans (pages can be shared between questions)
        ms_spans = {}
        
        for qnum in n_qp:
            # Find all pages with this question
            pages_with_q = [p for p, qs in rows_by_page.items() if qnum in qs]
            
            if not pages_with_q:
                continue
            
            start_page = min(pages_with_q)
            end_page = start_page
            
            # Extend to total marker
            for page_idx in range(start_page, len(ms_pages)):
                text = ms_pages[page_idx].text
                if self.MS_END.search(text):
                    for m in self.MS_END.finditer(text):
                        if int(m.group(1)) == qnum:
                            end_page = page_idx
                            break
            
            ms_spans[qnum] = {
                'start': start_page,
                'end': end_page,
                'pages': list(range(start_page, end_page + 1))
            }
        
        return ms_spans
    
    def sum_marks_for_question(self, ms_pages: List[PageData], qnum: int, qpages: List[int], mwin: Optional[Tuple]) -> Tuple[Optional[int], Dict]:
        """Sum marks for a question with OR-block handling"""
        if not qpages:
            return None, {'mode': 'no_pages'}
        
        lo_m, hi_m = (mwin[0], mwin[1]) if mwin else (0.70, 0.98)
        total = 0
        block_max = None
        
        for page_idx in qpages:
            if page_idx >= len(ms_pages):
                continue
            
            page = ms_pages[page_idx]
            
            # Check for explicit total
            for m in re.finditer(r'(?i)Total\s+for\s+Question\s+(\d{1,2})\s*[:=]\s*(\d{1,2})', page.text):
                if int(m.group(1)) == qnum:
                    return int(m.group(2)), {'mode': 'explicit_total'}
            
            # Sum from lines
            for line_text in page.text.splitlines():
                t = line_text.strip()
                if not t or self.BLACKLIST_NEAR.search(t):
                    continue
                
                # OR block detection
                if self.OR_LINE.search(t):
                    if block_max is not None:
                        total += block_max
                    block_max = 0
                
                # Extract mark
                got = None
                m = self.RE_MARK_EOL.search(t)
                if m:
                    got = int(m.group(1))
                
                if got is not None:
                    if block_max is None:
                        total += got
                    else:
                        block_max = max(block_max, got)
        
        # Flush pending OR block
        if block_max is not None:
            total += block_max
        
        return total if total > 0 else None, {'mode': 'summed'}
    
    def process_paper(self, qp_path: str, ms_path: str, year: int, season: str, paper_number: str) -> Dict:
        """Process a complete paper"""
        print(f"\n{'='*80}")
        print(f"Processing: {year} {season} Paper {paper_number}")
        print(f"{'='*80}")
        
        # Extract pages
        print("\n1️⃣ Extracting QP pages...")
        qp_pages = self.extract_pages_with_metadata(qp_path, skip_scrubbing=False)
        print(f"   ✅ Extracted {len(qp_pages)} QP pages")
        
        print("\n2️⃣ Extracting MS pages...")
        ms_pages = self.extract_pages_with_metadata(ms_path, skip_scrubbing=True)
        print(f"   ✅ Extracted {len(ms_pages)} MS pages")
        
        # Build N_QP
        print("\n3️⃣ Building authoritative N_QP...")
        n_qp = self.build_authoritative_n_qp(qp_pages, ms_pages)
        
        if not n_qp:
            return {'error': 'Could not determine question numbers'}
        
        # Auto-detect margins/columns
        print("\n4️⃣ Auto-detecting QP margins...")
        margin_window, margin_meta = self.auto_qp_left_margin(qp_pages, n_qp)
        print(f"   ✅ Margin: {margin_window[0]:.3f}-{margin_window[1]:.3f} (method: {margin_meta['method']})")
        
        print("\n5️⃣ Auto-detecting MS columns...")
        columns = self.auto_ms_columns(ms_pages)
        q_col_str = f"{columns['question_col'][0]:.3f}-{columns['question_col'][1]:.3f}" if columns['question_col'] else 'auto'
        m_col_str = f"{columns['marks_col'][0]:.3f}-{columns['marks_col'][1]:.3f}" if columns['marks_col'] else 'auto'
        print(f"   ✅ Question column: {q_col_str}")
        print(f"   ✅ Marks column: {m_col_str}")
        
        # Segment questions
        print("\n6️⃣ Segmenting QP questions...")
        qp_spans = self.detect_qp_spans(qp_pages, n_qp, margin_window)
        print(f"   ✅ Segmented {len(qp_spans)} questions")
        
        print("\n7️⃣ Segmenting MS questions...")
        ms_spans = self.segment_ms_questions(ms_pages, n_qp, columns)
        ms_link_pct = len(ms_spans) / len(n_qp) * 100 if n_qp else 0
        print(f"   ✅ Linked {len(ms_spans)}/{len(n_qp)} questions ({ms_link_pct:.1f}%)")
        
        # Build questions
        print("\n8️⃣ Building question metadata...")
        questions = []
        
        for qnum in sorted(n_qp):
            qp_span = qp_spans.get(qnum, {})
            ms_span = ms_spans.get(qnum, {})
            
            # Sum marks
            marks_ms, marks_meta = self.sum_marks_for_question(
                ms_pages, 
                qnum, 
                ms_span.get('pages', []),
                columns.get('marks_col')
            )
            
            questions.append({
                'qnum': qnum,
                'qp_pages': qp_span.get('pages', []),
                'ms_pages': ms_span.get('pages', []),
                'marks_ms': marks_ms,
                'marks_meta': marks_meta
            })
        
        print(f"   ✅ Built {len(questions)} questions")
        
        result = {
            'subject_code': 'WME01',
            'paper': {
                'year': year,
                'season': season,
                'paper_number': paper_number
            },
            'questions': questions,
            'metrics': {
                'question_count': len(questions),
                'ms_linking_pct': ms_link_pct,
                'qp_pages': len(qp_pages),
                'ms_pages': len(ms_pages)
            }
        }
        
        print("\n✅ Processing complete!")
        return result
    
    def extract_question_pdfs(self, qp_path: str, ms_path: str, questions: List[Dict], 
                              output_dir: Path, year: int, season: str, paper_number: str):
        """Extract individual question PDFs for QP and MS"""
        print("\n9️⃣ Extracting individual question PDFs...")
        
        # Create subdirectories
        pages_dir = output_dir / 'pages'
        ms_dir = output_dir / 'markschemes'
        pages_dir.mkdir(parents=True, exist_ok=True)
        ms_dir.mkdir(parents=True, exist_ok=True)
        
        # Read PDFs
        qp_reader = PdfReader(qp_path)
        ms_reader = PdfReader(ms_path)
        
        extracted_count = 0
        
        for q in questions:
            qnum = q['qnum']
            filename_base = f"{year}_{season}_{paper_number}_Q{qnum}"
            
            # Extract QP pages
            if q.get('qp_pages'):
                qp_writer = PdfWriter()
                for page_idx in q['qp_pages']:
                    if 0 <= page_idx < len(qp_reader.pages):
                        qp_writer.add_page(qp_reader.pages[page_idx])
                
                qp_output = pages_dir / f"{filename_base}.pdf"
                with open(qp_output, 'wb') as f:
                    qp_writer.write(f)
                extracted_count += 1
            
            # Extract MS pages
            if q.get('ms_pages'):
                ms_writer = PdfWriter()
                for page_idx in q['ms_pages']:
                    if 0 <= page_idx < len(ms_reader.pages):
                        ms_writer.add_page(ms_reader.pages[page_idx])
                
                ms_output = ms_dir / f"{filename_base}.pdf"
                with open(ms_output, 'wb') as f:
                    ms_writer.write(f)
                extracted_count += 1
        
        print(f"   ✅ Extracted {extracted_count} PDFs ({len(questions)} QP + {len([q for q in questions if q.get('ms_pages')])} MS)")
        return extracted_count

if __name__ == "__main__":
    # Test on JAN 2022 M1
    processor = M1Processor()
    
    raw_dir = Path(__file__).parent.parent / 'data' / 'raw' / 'IAL' / 'Mechanics_1'
    qp_path = raw_dir / 'JAN 2022 M1 QP.pdf'
    ms_path = raw_dir / 'JAN 2022 M1 MS.pdf'
    
    result = processor.process_paper(str(qp_path), str(ms_path), 2022, 'Jan', 'P1')
    
    # Save result
    output_dir = Path(__file__).parent.parent / 'data' / 'processed' / 'Mechanics_1'
    output_dir.mkdir(parents=True, exist_ok=True)
    
    output_file = output_dir / '2022_Jan_P1_segmented.json'
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(result, f, indent=2, ensure_ascii=False)
    
    print(f"\n💾 Saved segmentation to: {output_file}")
    
    # Extract individual question PDFs
    pdf_count = processor.extract_question_pdfs(
        str(qp_path), str(ms_path), 
        result['questions'], 
        output_dir, 
        2022, 'Jan', 'P1'
    )
    
    print(f"\n💾 Saved {pdf_count} PDFs to: {output_dir / 'pages'} and {output_dir / 'markschemes'}")
    
    print(f"\n💾 Saved to: {output_file}")
