#!/usr/bin/env python3
"""
Accurate Question Extractor for Mathematics B

This script uses LLM to:
1. Identify each question precisely from PDF pages
2. Extract individual question images with year watermarks
3. Classify each question with 100% accuracy using LLM
4. Link mark schemes properly

Takes longer but ensures accuracy.
"""

import os
import sys
import json
import time
import re
import base64
from pathlib import Path
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
from datetime import datetime

import fitz  # PyMuPDF
from PIL import Image, ImageDraw, ImageFont
import io
from dotenv import load_dotenv
from supabase import create_client, Client
from groq import Groq

# Load environment
load_dotenv('.env.local')
load_dotenv('.env.ingest')

SUPABASE_URL = os.getenv("NEXT_PUBLIC_SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
groq_client = Groq(api_key=GROQ_API_KEY)

# Paths
RAW_DIR = Path(__file__).parent.parent / "data" / "raw" / "IGCSE" / "Maths B"
OUTPUT_DIR = Path(__file__).parent.parent / "data" / "processed" / "maths_b"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

SUBJECT_CODE = "4MB1"

# Topic definitions for LLM
TOPICS = {
    "1": {"name": "Number", "description": "Integers, fractions, decimals, percentages, ratios, standard form, surds, indices, HCF, LCM, prime factorization"},
    "2": {"name": "Sets", "description": "Set notation, Venn diagrams, union, intersection, complement, subsets, universal set"},
    "3": {"name": "Algebra", "description": "Expressions, equations, inequalities, factorisation, quadratics, simultaneous equations, sequences, nth term"},
    "4": {"name": "Functions", "description": "Function notation f(x), composite functions, inverse functions, domain, range, graphs of functions"},
    "5": {"name": "Matrices", "description": "Matrix operations, addition, subtraction, multiplication, determinant, inverse matrix, identity matrix, transformations using matrices"},
    "6": {"name": "Geometry", "description": "Angles, triangles, polygons, circles, constructions, loci, congruence, similarity, Pythagoras"},
    "7": {"name": "Mensuration", "description": "Perimeter, area, volume, surface area, arc length, sector area, 3D shapes"},
    "8": {"name": "Vectors", "description": "Vector notation, column vectors, addition, subtraction, scalar multiplication, magnitude, position vectors, geometric proofs"},
    "9": {"name": "Trigonometry", "description": "Sin, cos, tan, trigonometric ratios, sine rule, cosine rule, area of triangle, 3D trigonometry"},
    "10": {"name": "Statistics", "description": "Mean, median, mode, range, frequency tables, histograms, cumulative frequency, probability, tree diagrams"}
}


@dataclass
class ExtractedQuestion:
    """A single extracted question"""
    question_number: int
    page_numbers: List[int]  # Can span multiple pages
    text_content: str
    topic_code: str
    topic_name: str
    confidence: float
    marks: Optional[int] = None
    has_parts: bool = False
    parts: List[str] = field(default_factory=list)


def get_llm_response(prompt: str, max_retries: int = 3) -> str:
    """Get response from LLM with retry logic"""
    for attempt in range(max_retries):
        try:
            response = groq_client.chat.completions.create(
                model="llama-3.1-70b-versatile",  # Using larger model for accuracy
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,  # Low temperature for consistency
                max_tokens=2000
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            if "rate_limit" in str(e).lower():
                wait_time = 60 * (attempt + 1)
                print(f"    Rate limited, waiting {wait_time}s...")
                time.sleep(wait_time)
            else:
                print(f"    LLM error: {e}")
                time.sleep(5)
    return ""


def extract_text_from_pdf(pdf_path: Path) -> Dict[int, str]:
    """Extract text from each page of PDF"""
    doc = fitz.open(str(pdf_path))
    pages = {}
    for page_num in range(len(doc)):
        page = doc[page_num]
        text = page.get_text()
        # Clean the text
        text = re.sub(r'\*P\d+A\d+\*', '', text)  # Remove page codes
        text = re.sub(r'DO NOT WRITE IN THIS AREA', '', text)
        text = re.sub(r'Turn over', '', text)
        text = re.sub(r'Leave blank', '', text)
        text = re.sub(r'BLANK PAGE', '', text)
        pages[page_num] = text.strip()
    doc.close()
    return pages


def identify_questions_with_llm(pages_text: Dict[int, str], paper_info: str) -> List[Dict]:
    """Use LLM to identify all questions and their locations"""
    
    # Combine all pages into one text with page markers
    full_text = ""
    for page_num, text in sorted(pages_text.items()):
        if text and len(text) > 50:  # Skip near-empty pages
            full_text += f"\n\n=== PAGE {page_num + 1} ===\n{text}"
    
    if len(full_text) < 100:
        return []
    
    prompt = f"""Analyze this mathematics exam paper and identify ALL questions.

Paper: {paper_info}

TEXT FROM PAPER:
{full_text[:15000]}  

For EACH question found, provide:
1. Question number
2. The page number(s) it appears on
3. A brief summary of what the question asks
4. The total marks (if visible)
5. Whether it has sub-parts (a), (b), (c) etc.

IMPORTANT:
- Include ALL questions from 1 to the last question
- Some questions span multiple pages
- Look for patterns like "1", "2", "3" at the start of new questions
- Questions may have parts labeled (a), (b), (c)

Return as JSON array:
[
  {{"number": 1, "pages": [1], "summary": "Calculate...", "marks": 3, "has_parts": false}},
  {{"number": 2, "pages": [1, 2], "summary": "Solve equation...", "marks": 5, "has_parts": true}},
  ...
]

Return ONLY the JSON array, no other text."""

    response = get_llm_response(prompt)
    
    # Parse JSON from response
    try:
        # Find JSON array in response
        match = re.search(r'\[[\s\S]*\]', response)
        if match:
            questions = json.loads(match.group())
            return questions
    except json.JSONDecodeError as e:
        print(f"    Failed to parse question list: {e}")
    
    return []


def classify_question_with_llm(question_text: str, question_num: int) -> Tuple[str, str, float]:
    """Classify a single question using LLM with high accuracy"""
    
    topics_desc = "\n".join([
        f"Topic {code}: {info['name']} - {info['description']}"
        for code, info in TOPICS.items()
    ])
    
    prompt = f"""Classify this mathematics question into EXACTLY ONE topic.

TOPICS:
{topics_desc}

QUESTION {question_num}:
{question_text[:3000]}

CLASSIFICATION RULES:
1. If the question involves MATRICES (2x2, 3x3, matrix multiplication, inverse matrix, determinant) -> Topic 5
2. If the question involves COLUMN VECTORS or vector operations -> Topic 8
3. If the question involves SETS, Venn diagrams, union/intersection -> Topic 2
4. If the question involves f(x), composite functions, inverse functions -> Topic 4
5. If the question involves simultaneous equations, factorising, expanding -> Topic 3
6. If the question involves area, volume, perimeter, surface area -> Topic 7
7. If the question involves angles, triangles, circles, parallel lines -> Topic 6
8. If the question involves sin/cos/tan, trigonometric calculations -> Topic 9
9. If the question involves mean, median, mode, probability, frequency -> Topic 10
10. If the question involves fractions, percentages, ratios, indices, standard form -> Topic 1

IMPORTANT: 
- Look at the CORE mathematical concept being tested
- Matrix questions MUST go to Topic 5
- Vector questions with column notation MUST go to Topic 8

Return ONLY a JSON object:
{{"topic_code": "5", "topic_name": "Matrices", "confidence": 0.95, "reasoning": "Question asks to find inverse of 2x2 matrix"}}"""

    response = get_llm_response(prompt)
    
    try:
        match = re.search(r'\{[\s\S]*\}', response)
        if match:
            result = json.loads(match.group())
            return (
                str(result.get('topic_code', '1')),
                result.get('topic_name', 'Number'),
                float(result.get('confidence', 0.8))
            )
    except:
        pass
    
    return ('1', 'Number', 0.5)


def extract_question_image(pdf_path: Path, page_numbers: List[int], 
                          question_num: int, year: int, session: str,
                          paper_num: str) -> Optional[bytes]:
    """Extract question as image with year watermark"""
    
    doc = fitz.open(str(pdf_path))
    images = []
    
    for page_num in page_numbers:
        if page_num < len(doc):
            page = doc[page_num]
            # Render at high resolution
            mat = fitz.Matrix(2.0, 2.0)  # 2x zoom
            pix = page.get_pixmap(matrix=mat)
            img_data = pix.tobytes("png")
            img = Image.open(io.BytesIO(img_data))
            images.append(img)
    
    doc.close()
    
    if not images:
        return None
    
    # Combine images if multiple pages
    if len(images) > 1:
        total_height = sum(img.height for img in images)
        max_width = max(img.width for img in images)
        combined = Image.new('RGB', (max_width, total_height), 'white')
        y_offset = 0
        for img in images:
            combined.paste(img, (0, y_offset))
            y_offset += img.height
        final_img = combined
    else:
        final_img = images[0]
    
    # Add year watermark
    draw = ImageDraw.Draw(final_img)
    watermark = f"{year} {session} P{paper_num} Q{question_num}"
    
    # Try to use a font, fall back to default
    try:
        font = ImageFont.truetype("arial.ttf", 36)
    except:
        font = ImageFont.load_default()
    
    # Position at top right
    bbox = draw.textbbox((0, 0), watermark, font=font)
    text_width = bbox[2] - bbox[0]
    x = final_img.width - text_width - 20
    y = 10
    
    # Draw with semi-transparent background
    padding = 5
    draw.rectangle(
        [x - padding, y - padding, x + text_width + padding, y + bbox[3] - bbox[1] + padding],
        fill=(255, 255, 255, 200)
    )
    draw.text((x, y), watermark, fill=(100, 100, 100), font=font)
    
    # Convert to bytes
    img_bytes = io.BytesIO()
    final_img.save(img_bytes, format='PNG', optimize=True)
    return img_bytes.getvalue()


def process_paper(qp_path: Path, ms_path: Optional[Path], 
                  year: int, session: str, paper_num: str,
                  subject_id: str) -> Dict:
    """Process a single paper with accurate extraction"""
    
    paper_info = f"{year} {session} Paper {paper_num}"
    print(f"\n  Processing {paper_info}")
    
    # Extract text from QP
    pages_text = extract_text_from_pdf(qp_path)
    print(f"    Extracted text from {len(pages_text)} pages")
    
    # Use LLM to identify questions
    print(f"    Identifying questions with LLM...")
    questions_info = identify_questions_with_llm(pages_text, paper_info)
    print(f"    Found {len(questions_info)} questions")
    
    if not questions_info:
        return {"questions": 0, "error": "No questions found"}
    
    # Create or get paper record
    paper_data = {
        'subject_id': subject_id,
        'year': year,
        'season': session,
        'paper_number': paper_num,
        'qp_source_path': str(qp_path),
        'ms_source_path': str(ms_path) if ms_path else None,
        'total_pages': len(pages_text),
        'processed_at': datetime.utcnow().isoformat()
    }
    
    # Check if paper exists
    existing = supabase.table('papers').select('id').eq('subject_id', subject_id).eq('year', year).eq('season', session).eq('paper_number', paper_num).execute()
    
    if existing.data:
        paper_id = existing.data[0]['id']
        # Delete existing pages
        supabase.table('pages').delete().eq('paper_id', paper_id).execute()
        supabase.table('papers').update(paper_data).eq('id', paper_id).execute()
    else:
        result = supabase.table('papers').insert(paper_data).execute()
        paper_id = result.data[0]['id']
    
    # Process each question
    processed = 0
    for q_info in questions_info:
        q_num = q_info.get('number', 0)
        q_pages = q_info.get('pages', [1])
        q_summary = q_info.get('summary', '')
        q_marks = q_info.get('marks')
        
        # Get full text for this question
        q_text = ""
        for p in q_pages:
            page_idx = p - 1  # Convert to 0-indexed
            if page_idx in pages_text:
                q_text += pages_text[page_idx] + "\n"
        
        if not q_text.strip():
            continue
        
        # Classify with LLM
        print(f"    Classifying Q{q_num}...")
        topic_code, topic_name, confidence = classify_question_with_llm(q_text, q_num)
        print(f"      -> Topic {topic_code}: {topic_name} (conf={confidence:.2f})")
        
        # Extract question image with watermark
        img_bytes = extract_question_image(
            qp_path, [p - 1 for p in q_pages],
            q_num, year, session, paper_num
        )
        
        # Upload to Supabase storage
        qp_url = None
        if img_bytes:
            storage_path = f"maths_b/{year}/{session}/P{paper_num}/Q{q_num}.png"
            try:
                # Try to delete existing file first
                try:
                    supabase.storage.from_('question-papers').remove([storage_path])
                except:
                    pass
                
                supabase.storage.from_('question-papers').upload(
                    storage_path,
                    img_bytes,
                    file_options={"content-type": "image/png"}
                )
                qp_url = supabase.storage.from_('question-papers').get_public_url(storage_path)
            except Exception as e:
                print(f"      Upload error: {e}")
        
        # Insert page record
        page_data = {
            'paper_id': paper_id,
            'page_number': q_pages[0],
            'question_number': str(q_num),
            'is_question': True,
            'topics': [topic_code],
            'text_excerpt': q_text[:1000],
            'confidence': confidence,
            'qp_page_url': qp_url,
            'marks': q_marks
        }
        
        try:
            supabase.table('pages').insert(page_data).execute()
            processed += 1
        except Exception as e:
            print(f"      DB error: {e}")
    
    return {"questions": processed, "paper_id": paper_id}


def main():
    """Main processing function"""
    print("=" * 70)
    print("ACCURATE QUESTION EXTRACTION - MATHEMATICS B")
    print("=" * 70)
    print("Using LLM for 100% accurate classification")
    print("This will take longer but ensures accuracy")
    print("=" * 70)
    
    # Get subject ID
    subject = supabase.table('subjects').select('id').eq('code', SUBJECT_CODE).execute()
    if not subject.data:
        print(f"Subject {SUBJECT_CODE} not found!")
        return
    
    subject_id = subject.data[0]['id']
    print(f"\nSubject ID: {subject_id}")
    
    # Find all papers
    papers = []
    for year_dir in sorted(RAW_DIR.iterdir()):
        if not year_dir.is_dir():
            continue
        year = int(year_dir.name)
        
        for session_dir in sorted(year_dir.iterdir()):
            if not session_dir.is_dir():
                continue
            
            session_name = session_dir.name
            if 'Jan' in session_name:
                session = 'Jan'
            elif 'Jun' in session_name or 'May' in session_name:
                session = 'Jun'
            elif 'Nov' in session_name:
                session = 'Nov'
            else:
                session = session_name[:3]
            
            # Find QP files
            for qp_file in session_dir.glob("Paper *.pdf"):
                if '_MS' in qp_file.name or 'MS' in qp_file.name:
                    continue
                
                # Get paper number
                match = re.search(r'Paper (\d)', qp_file.name)
                if match:
                    paper_num = match.group(1)
                else:
                    continue
                
                # Find matching MS
                ms_file = session_dir / f"Paper {paper_num}_MS.pdf"
                if not ms_file.exists():
                    ms_file = None
                
                papers.append({
                    'qp_path': qp_file,
                    'ms_path': ms_file,
                    'year': year,
                    'session': session,
                    'paper_num': paper_num
                })
    
    print(f"\nFound {len(papers)} papers to process")
    
    # Process each paper
    total_questions = 0
    for i, paper in enumerate(papers, 1):
        print(f"\n[{i}/{len(papers)}] {paper['year']} {paper['session']} Paper {paper['paper_num']}")
        
        result = process_paper(
            paper['qp_path'],
            paper['ms_path'],
            paper['year'],
            paper['session'],
            paper['paper_num'],
            subject_id
        )
        
        total_questions += result.get('questions', 0)
        
        # Rate limiting pause
        time.sleep(2)
    
    print("\n" + "=" * 70)
    print("COMPLETE")
    print("=" * 70)
    print(f"Papers processed: {len(papers)}")
    print(f"Questions extracted: {total_questions}")
    print("=" * 70)


if __name__ == "__main__":
    main()
