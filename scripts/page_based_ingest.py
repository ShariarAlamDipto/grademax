#!/usr/bin/env python3
"""
NEW INGESTION PIPELINE - Page-based architecture
- Split QP and MS into individual pages
- Classify each page with topics (multiple topics allowed)
- Upload pages to storage: subjects/Physics/pages/2019_Jun_1P/q1.pdf
- Store in pages table with topics array
"""

import os
import sys
import json
import time
import fitz
import re
from pathlib import Path
from dataclasses import dataclass, asdict
from typing import Dict, List, Optional
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).parent))

from split_pages import PageSplitter
from symbol_aware_classifier import SymbolAwareClassifier
from supabase_client import SupabaseClient
from compress_pdf import compress_pdf_in_place, format_size

# Load environment variables from .env.ingest
load_dotenv('.env.ingest')


@dataclass
class ProcessedPage:
    """Represents a processed page"""
    page_number: int
    question_number: str
    topics: List[str]  # Can have multiple topics
    difficulty: str
    confidence: float
    qp_page_path: str
    ms_page_path: Optional[str]
    qp_storage_url: str
    ms_storage_url: Optional[str]
    has_diagram: bool
    text_excerpt: str


class MarkSchemeExtractor:
    """Extract mark scheme pages for specific questions"""
    
    def __init__(self, ms_pdf_path: str, output_dir: Path):
        self.ms_pdf_path = ms_pdf_path
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        if Path(ms_pdf_path).exists():
            self.doc = fitz.open(ms_pdf_path)
        else:
            self.doc = None
            print(f"   ⚠️  Mark scheme not found: {ms_pdf_path}")
        
    def extract_for_question(self, question_number: str) -> Optional[str]:
        """Extract mark scheme pages for a specific question"""
        if not self.doc:
            return None
            
        matching_pages = []
        
        for page_num in range(len(self.doc)):
            page = self.doc[page_num]
            text = page.get_text()
            
            # Look for question number
            if (f"{question_number})" in text or 
                f"Question {question_number}" in text or
                f"Q{question_number}" in text or
                f"{question_number} " in text[:100]):  # First 100 chars
                matching_pages.append(page_num)
        
        if not matching_pages:
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
        if self.doc:
            self.doc.close()


class PageBasedPipeline:
    """Page-based ingestion pipeline"""
    
    def __init__(self, config_path: str = "config/physics_topics.yaml", subject_name: str = None):
        self.db = SupabaseClient()
        api_key = os.getenv('GEMINI_API_KEY')
        if not api_key:
            raise ValueError("GEMINI_API_KEY not set")
        self.classifier = SymbolAwareClassifier(config_path, api_key)
        
        # Subject mapping (will be auto-detected from folder structure)
        self.subject_map = {
            'Physics': '4PH1',
            'Chemistry': '4CH1',
            'Biology': '4BI1',
            'Mathematics': '4MA1',
            'Maths': '4MA1',
            'Further Pure Maths': '9FM0',
            'FurtherPureMaths': '9FM0',
            'Further Pure Mathematics': '9FM0'
        }
        self.subject_code = None  # Will be set during processing
        self.subject_name = subject_name  # Will be set during processing
        
    def process_paper_pair(self, qp_path: str, ms_path: str):
        """Process a QP and MS pair"""
        qp_path = Path(qp_path)
        ms_path = Path(ms_path)
        
        # Parse filename (with watermark extraction)
        paper_info = self._parse_filename(qp_path.name, qp_path.parent, str(qp_path))
        paper_id_str = f"{paper_info['year']}_{paper_info['season']}_{paper_info['paper']}"
        
        print(f"\n{'='*70}")
        print(f"📋 Processing: {paper_id_str}")
        print(f"{'='*70}")
        
        # Create output directory
        output_dir = Path("data/processed") / paper_id_str
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # STEP 1: Get or create paper record
        print(f"\n1️⃣  Creating paper record...")
        paper_uuid = self._ensure_paper(paper_info, str(qp_path), str(ms_path))
        print(f"   ✅ Paper UUID: {paper_uuid}")
        
        # STEP 2: Split QP into questions
        print(f"\n2️⃣  Splitting QP into pages...")
        qp_splitter = PageSplitter(str(qp_path), str(output_dir / "pages"))
        manifest = qp_splitter.process_paper(paper_id_str, paper_info)
        print(f"   ✅ Split into {len(manifest.questions)} questions")
        
        # STEP 3: Extract mark schemes
        print(f"\n3️⃣  Extracting mark schemes...")
        ms_extractor = MarkSchemeExtractor(str(ms_path), output_dir / "markschemes")
        ms_paths = {}
        for q in manifest.questions:
            q_num = q['question_number']
            ms_path_local = ms_extractor.extract_for_question(q_num)
            if ms_path_local:
                ms_paths[q_num] = ms_path_local
                print(f"   ✅ Q{q_num} MS extracted")
        ms_extractor.close()
        
        # STEP 4: Classify and upload each page
        print(f"\n4️⃣  Classifying and uploading pages...")
        processed_pages = []
        
        for i, q in enumerate(manifest.questions, 1):
            q_num = q['question_number']
            q_pdf = output_dir / "pages" / f"q{q_num}.pdf"
            
            # Read PDF for classification
            doc = fitz.open(str(q_pdf))
            text = ""
            for page in doc:
                text += page.get_text()
            doc.close()
            
            # Classify (gets ONE primary topic)
            result = self.classifier.classify(text[:3000])
            
            if not result.page_has_question:
                print(f"   ⏭️  [{i}/{len(manifest.questions)}] Q{q_num}: No question detected")
                continue
            
            # Storage paths: subjects/Physics/pages/2019_Jun_1P/q1.pdf
            qp_storage_path = f"subjects/{self.subject_name}/pages/{paper_id_str}/q{q_num}.pdf"
            ms_storage_path = f"subjects/{self.subject_name}/pages/{paper_id_str}/q{q_num}_ms.pdf"
            
            # Compress QP before upload
            try:
                orig_size, comp_size, ratio = compress_pdf_in_place(str(q_pdf), compression_level=3)
                if ratio > 10:  # Only mention if significant compression
                    print(f"      📦 Compressed: {format_size(orig_size)} → {format_size(comp_size)} ({ratio:.0f}% saved)")
            except Exception as e:
                print(f"      ⚠️  Compression failed (will upload original): {e}")
            
            # Upload QP
            try:
                self.db.upload_file(
                    bucket="question-pdfs",
                    file_path=str(q_pdf),
                    destination_path=qp_storage_path
                )
            except Exception as e:
                print(f"   ❌ [{i}/{len(manifest.questions)}] Q{q_num}: Upload failed - {e}")
                continue
            
            # Upload MS (if exists)
            ms_url = None
            if q_num in ms_paths:
                # Compress MS before upload
                try:
                    compress_pdf_in_place(ms_paths[q_num], compression_level=3)
                except:
                    pass  # Continue even if compression fails
                
                try:
                    self.db.upload_file(
                        bucket="question-pdfs",
                        file_path=ms_paths[q_num],
                        destination_path=ms_storage_path
                    )
                    ms_url = ms_storage_path
                except Exception as e:
                    print(f"   ⚠️  Q{q_num} MS upload failed: {e}")
            
            processed_pages.append(ProcessedPage(
                page_number=i,
                question_number=q_num,
                topics=[result.topic],  # Store as array (can expand later for multi-topic)
                difficulty=result.difficulty,
                confidence=result.confidence,
                qp_page_path=str(q_pdf),
                ms_page_path=ms_paths.get(q_num),
                qp_storage_url=qp_storage_path,
                ms_storage_url=ms_url,
                has_diagram=q.get('has_diagram', False),
                text_excerpt=text[:500]
            ))
            
            print(f"   ✅ [{i}/{len(manifest.questions)}] Q{q_num} → Topic {result.topic} ({result.difficulty})")
            
            # Rate limiting
            if i < len(manifest.questions):
                time.sleep(4.5)
        
        # STEP 5: Store pages in database
        print(f"\n5️⃣  Storing in database...")
        for page in processed_pages:
            try:
                page_data = {
                    'paper_id': paper_uuid,
                    'page_number': page.page_number,
                    'question_number': page.question_number,
                    'is_question': True,
                    'topics': page.topics,  # PostgreSQL array
                    'difficulty': page.difficulty,
                    'confidence': page.confidence,
                    'qp_page_url': page.qp_storage_url,
                    'ms_page_url': page.ms_storage_url,
                    'has_diagram': page.has_diagram,
                    'text_excerpt': page.text_excerpt
                }
                
                self.db.insert('pages', page_data)
                print(f"   ✅ Q{page.question_number} stored")
                
            except Exception as e:
                print(f"   ❌ Q{page.question_number} DB insert failed: {e}")
        
        print(f"\n{'='*70}")
        print(f"✅ COMPLETE: {paper_id_str}")
        print(f"   Pages processed: {len(processed_pages)}")
        print(f"   Topics found: {set(t for p in processed_pages for t in p.topics)}")
        print(f"{'='*70}\n")
        
        return processed_pages
    
    def _ensure_paper(self, paper_info: Dict, qp_path: str, ms_path: str) -> str:
        """Get or create paper record, return UUID"""
        # Get subject UUID
        subjects = self.db.select('subjects', filters={'code': f'eq.{self.subject_code}'})
        if not subjects:
            raise Exception(f"Subject {self.subject_code} not found in database")
        subject_uuid = subjects[0]['id']
        
        # Check if paper exists
        filters = {
            'subject_id': f'eq.{subject_uuid}',
            'year': f'eq.{paper_info["year"]}',
            'season': f'eq.{paper_info["season"]}',
            'paper_number': f'eq.{paper_info["paper"]}'
        }
        existing = self.db.select('papers', filters=filters)
        
        if existing:
            return existing[0]['id']
        
        # Create new paper
        paper_data = {
            'subject_id': subject_uuid,
            'year': paper_info['year'],
            'season': paper_info['season'],
            'paper_number': paper_info['paper'],
            'qp_source_path': qp_path,
            'ms_source_path': ms_path
        }
        
        result = self.db.insert('papers', paper_data)
        return result[0]['id']
    
    def _extract_watermark_metadata(self, pdf_path: str) -> Dict:
        """Extract metadata from PMT watermark at bottom left of pages
        
        Watermark format: "PMT\nPhysics · 2024 · May/Jun · Paper 1 · QP"
        Returns: {'subject': 'Physics', 'year': 2024, 'season': 'May/Jun', 'paper': '1', 'type': 'QP'}
        """
        try:
            doc = fitz.open(pdf_path)
            # Check first few pages for watermark
            for page_num in range(min(5, len(doc))):
                page = doc[page_num]
                blocks = page.get_text('blocks')
                
                # Look for watermark at bottom left (X < 30, Y < 10)
                for block in blocks:
                    x, y, text = block[0], block[1], block[4].strip()
                    
                    if x < 30 and y < 10 and '·' in text:
                        # Found watermark! Parse it
                        # Format: "PMT\nPhysics · 2024 · May/Jun · Paper 1 · QP"
                        lines = text.split('\n')
                        if len(lines) >= 2 and 'PMT' in lines[0]:
                            parts = lines[1].split('·')
                            if len(parts) >= 5:
                                subject = parts[0].strip()
                                year = int(parts[1].strip())
                                season = parts[2].strip()
                                paper_info = parts[3].strip()  # "Paper 1"
                                paper_num = paper_info.replace('Paper', '').strip()
                                doc_type = parts[4].strip()  # "QP" or "MS"
                                
                                doc.close()
                                return {
                                    'subject': subject,
                                    'year': year,
                                    'season': season,
                                    'paper': paper_num,
                                    'type': doc_type
                                }
            doc.close()
        except Exception as e:
            print(f"   ⚠️  Could not extract watermark: {e}")
        
        return None
    
    def _normalize_season(self, season: str) -> str:
        """Normalize season names to database format
        
        May/Jun, May-Jun -> Jun
        Oct/Nov, Oct-Nov -> Jan (represents Jan sitting of next year)
        Jan -> Jan
        """
        season_lower = season.lower()
        if 'may' in season_lower or 'jun' in season_lower:
            return 'Jun'
        elif 'oct' in season_lower or 'nov' in season_lower:
            return 'Jan'
        elif 'jan' in season_lower:
            return 'Jan'
        else:
            return 'Jun'  # Default fallback
    
    def _parse_filename(self, filename: str, parent_path: Path, pdf_path: str) -> Dict:
        """Parse paper filename and extract metadata from path and watermark
        
        NEW FORMAT:
        - Filename: "Paper 1.pdf", "Paper 2_MS.pdf"
        - Path: data/raw/IGCSE/Physics/2024/May-Jun/
        - Watermark: "PMT\nPhysics · 2024 · May/Jun · Paper 1 · QP"
        """
        # STEP 1: Extract from watermark (most reliable)
        watermark_data = self._extract_watermark_metadata(pdf_path)
        
        if watermark_data:
            print(f"   📍 Watermark: {watermark_data['subject']} · {watermark_data['year']} · {watermark_data['season']} · Paper {watermark_data['paper']} · {watermark_data['type']}")
            
            # Set subject info
            self.subject_name = watermark_data['subject']
            self.subject_code = self.subject_map.get(self.subject_name, '4PH1')
            
            return {
                'year': watermark_data['year'],
                'season': self._normalize_season(watermark_data['season']),
                'paper': f"{watermark_data['paper']}P"
            }
        
        # STEP 2: Fallback to path-based parsing
        print(f"   ⚠️  No watermark found, using path-based parsing")
        parts = parent_path.parts
        year = None
        season = None
        subject = None
        
        # Extract from path: data/raw/IGCSE/Physics/2024/May-Jun/
        for i, part in enumerate(parts):
            if part.isdigit() and len(part) == 4:
                year = int(part)
            elif part in ['Jun', 'Jan', 'May-Jun', 'Oct-Nov', 'May/Jun', 'Oct/Nov']:
                season = self._normalize_season(part)
            elif part in self.subject_map:
                subject = part
        
        # Parse filename: "Paper 1.pdf" or "Paper 2_MS.pdf"
        name_clean = filename.replace('.pdf', '').replace('_MS', '').replace(' MS', '')
        paper_match = re.search(r'Paper\s*(\d+)', name_clean, re.IGNORECASE)
        paper_num = paper_match.group(1) if paper_match else '1'
        
        # Set subject info
        if subject:
            self.subject_name = subject
            self.subject_code = self.subject_map.get(subject, '4PH1')
        
        return {
            'year': year or 2024,
            'season': season or 'Jun',
            'paper': f"{paper_num}P"
        }


def main():
    if len(sys.argv) < 3:
        print("Usage: python page_based_ingest.py <qp_pdf> <ms_pdf>")
        print("Example: python page_based_ingest.py data/raw/.../QP.pdf data/raw/.../MS.pdf")
        sys.exit(1)
    
    qp_path = sys.argv[1]
    ms_path = sys.argv[2]
    
    pipeline = PageBasedPipeline()
    pipeline.process_paper_pair(qp_path, ms_path)


if __name__ == "__main__":
    main()
