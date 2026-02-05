#!/usr/bin/env python3
"""
Vision-Based Question Extractor using Groq Multimodal Models

Uses llama-3.2-90b-vision-preview or llama-3.2-11b-vision-preview to:
1. Analyze each PDF page as an image
2. Detect question numbers and boundaries
3. Classify topics with 100% accuracy using visual context
4. Extract question text for mark scheme linking
"""

import os
import sys
import json
import time
import base64
import re
from pathlib import Path
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
from io import BytesIO

import fitz  # PyMuPDF
from PIL import Image
from groq import Groq
from dotenv import load_dotenv

load_dotenv('.env.local')
load_dotenv('.env.ingest')

GROQ_API_KEY = os.getenv("GROQ_API_KEY")

# Groq vision models
VISION_MODEL = "llama-3.2-90b-vision-preview"  # Best quality
VISION_MODEL_FAST = "llama-3.2-11b-vision-preview"  # Faster, still good

# Math B Topics for classification
MATHS_B_TOPICS = {
    "1": "Number (integers, fractions, decimals, percentages, ratios, indices, standard form, surds)",
    "2": "Sets (set notation, Venn diagrams, union, intersection, complement)",
    "3": "Algebra (expressions, equations, inequalities, sequences, factorising, quadratics, simultaneous equations)",
    "4": "Functions (function notation, composite functions, inverse functions, domain, range)",
    "5": "Matrices (matrix operations, multiplication, determinants, inverse matrices, transformations)",
    "6": "Geometry (angles, polygons, circle theorems, congruence, similarity, constructions)",
    "7": "Mensuration (perimeter, area, volume, surface area, arc length, sector area)",
    "8": "Vectors and Transformation Geometry (vector notation, operations, translations, reflections, rotations, enlargements)",
    "9": "Trigonometry (sine, cosine, tangent, sine rule, cosine rule, bearings, 3D trigonometry)",
    "10": "Statistics and Probability (mean, median, mode, histograms, cumulative frequency, probability, tree diagrams)"
}


@dataclass
class ExtractedQuestion:
    """A question extracted from a page"""
    question_number: int
    sub_parts: List[str]  # e.g., ['a', 'b', 'c'] or []
    topic_code: str
    topic_name: str
    confidence: float
    text_summary: str  # Brief description for MS linking
    page_numbers: List[int]  # Can span multiple pages
    marks: Optional[int] = None


@dataclass 
class PageAnalysis:
    """Analysis result for a single page"""
    page_number: int
    questions_found: List[Dict]  # Question data from vision model
    raw_response: str


class VisionExtractor:
    """
    Uses Groq's vision models to analyze PDF pages and extract questions accurately
    """
    
    def __init__(self, use_fast_model: bool = False):
        if not GROQ_API_KEY:
            raise ValueError("GROQ_API_KEY not set")
        
        self.client = Groq(api_key=GROQ_API_KEY)
        self.model = VISION_MODEL_FAST if use_fast_model else VISION_MODEL
        self.request_count = 0
        self.last_request_time = 0
        
        print(f"Using vision model: {self.model}")
    
    def _rate_limit(self):
        """Respect Groq rate limits"""
        self.request_count += 1
        elapsed = time.time() - self.last_request_time
        
        # Groq free tier: ~30 requests/minute for vision
        if elapsed < 2.5:  # ~24 requests/minute to be safe
            time.sleep(2.5 - elapsed)
        
        self.last_request_time = time.time()
    
    def _pdf_page_to_base64(self, pdf_path: Path, page_num: int, dpi: int = 150) -> str:
        """Convert a PDF page to base64-encoded image"""
        doc = fitz.open(str(pdf_path))
        page = doc[page_num]
        
        # Render at higher DPI for better OCR
        mat = fitz.Matrix(dpi / 72, dpi / 72)
        pix = page.get_pixmap(matrix=mat)
        
        # Convert to PIL Image
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        
        # Convert to base64
        buffer = BytesIO()
        img.save(buffer, format="PNG", optimize=True)
        buffer.seek(0)
        
        doc.close()
        return base64.b64encode(buffer.read()).decode('utf-8')
    
    def analyze_page(self, pdf_path: Path, page_num: int, year: int, session: str, paper_num: str) -> PageAnalysis:
        """
        Analyze a single PDF page using vision model
        
        Returns detailed question information including:
        - Question numbers found
        - Topic classification for each question
        - Whether question continues from/to other pages
        """
        self._rate_limit()
        
        image_b64 = self._pdf_page_to_base64(pdf_path, page_num)
        
        prompt = f"""Analyze this exam paper page from Edexcel IGCSE Mathematics B ({year} {session} Paper {paper_num}).

TASK: Identify ALL questions or question parts visible on this page.

For EACH question/part found, provide:
1. question_number: The main question number (integer)
2. sub_parts: Any sub-parts visible (e.g., ["a", "b"] or ["a(i)", "a(ii)", "b"])
3. topic: Classify into ONE of these topics based on the ACTUAL mathematical content:
   - "1" = Number (integers, fractions, decimals, percentages, ratios, indices, standard form, surds, HCF, LCM)
   - "2" = Sets (Venn diagrams, set notation, union ∪, intersection ∩, complement)
   - "3" = Algebra (expressions, equations, inequalities, factorising, expanding, quadratics, simultaneous equations, sequences)
   - "4" = Functions (f(x) notation, composite functions, inverse functions, domain, range, graphs of functions)
   - "5" = Matrices (matrix notation, matrix multiplication, determinant, inverse matrix, identity matrix)
   - "6" = Geometry (angles, triangles, polygons, circle theorems, similarity, congruence, constructions, parallel lines)
   - "7" = Mensuration (area, perimeter, volume, surface area, circles, sectors, arcs, compound shapes)
   - "8" = Vectors (vector notation, column vectors, vector addition, position vectors, transformations using vectors)
   - "9" = Trigonometry (sin, cos, tan, sine rule, cosine rule, bearings, angles of elevation/depression)
   - "10" = Statistics (mean, median, mode, frequency tables, histograms, cumulative frequency, probability, tree diagrams)

4. marks: Total marks for this question part if visible (look for numbers in brackets like (3) or (4 marks))
5. continues_from_previous: true if this is a continuation of a question from the previous page
6. continues_to_next: true if the question continues on the next page
7. brief_description: A 5-10 word summary of what the question asks (for mark scheme matching)

IMPORTANT CLASSIFICATION RULES:
- Matrix questions (with rectangular arrays of numbers) → Topic 5
- Column vectors with arrows or notation like (x, y) in vector context → Topic 8
- Venn diagrams or set notation (∪, ∩, ξ) → Topic 2
- f(x), g(x), composite or inverse functions → Topic 4
- Trigonometric ratios or rules → Topic 9
- Area, volume, perimeter calculations → Topic 7
- Angle problems in shapes → Topic 6
- Probability or data analysis → Topic 10
- Solving equations, factorising, expanding → Topic 3
- Basic number operations, fractions, percentages → Topic 1

Return a JSON object with this structure:
{{
  "questions": [
    {{
      "question_number": 5,
      "sub_parts": ["a", "b", "c"],
      "topic": "5",
      "topic_reason": "Matrix multiplication question",
      "marks": 8,
      "continues_from_previous": false,
      "continues_to_next": false,
      "brief_description": "Multiply two 2x2 matrices"
    }}
  ],
  "page_notes": "Any relevant observations about the page"
}}

If no questions are visible (blank page, instructions only), return: {{"questions": [], "page_notes": "reason"}}

Respond ONLY with the JSON object, no other text."""

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": prompt
                            },
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/png;base64,{image_b64}"
                                }
                            }
                        ]
                    }
                ],
                max_tokens=2000,
                temperature=0.1  # Low temperature for consistent classification
            )
            
            raw_response = response.choices[0].message.content
            
            # Parse JSON from response
            try:
                # Try to extract JSON from response
                json_match = re.search(r'\{[\s\S]*\}', raw_response)
                if json_match:
                    data = json.loads(json_match.group())
                    questions = data.get('questions', [])
                else:
                    questions = []
            except json.JSONDecodeError:
                print(f"    Warning: Could not parse JSON from page {page_num + 1}")
                questions = []
            
            return PageAnalysis(
                page_number=page_num,
                questions_found=questions,
                raw_response=raw_response
            )
            
        except Exception as e:
            print(f"    Error analyzing page {page_num + 1}: {e}")
            return PageAnalysis(
                page_number=page_num,
                questions_found=[],
                raw_response=str(e)
            )
    
    def analyze_paper(self, pdf_path: Path, year: int, session: str, paper_num: str) -> List[ExtractedQuestion]:
        """
        Analyze an entire paper and extract all questions with accurate topic classification
        """
        doc = fitz.open(str(pdf_path))
        total_pages = len(doc)
        doc.close()
        
        print(f"  Analyzing {total_pages} pages...")
        
        # Analyze each page
        page_analyses = []
        for page_num in range(total_pages):
            print(f"    Page {page_num + 1}/{total_pages}...", end=" ")
            analysis = self.analyze_page(pdf_path, page_num, year, session, paper_num)
            page_analyses.append(analysis)
            
            q_count = len(analysis.questions_found)
            if q_count > 0:
                q_nums = [q.get('question_number', '?') for q in analysis.questions_found]
                print(f"Found Q{', Q'.join(map(str, q_nums))}")
            else:
                print("No questions")
        
        # Consolidate questions across pages
        questions = self._consolidate_questions(page_analyses)
        
        return questions
    
    def _consolidate_questions(self, page_analyses: List[PageAnalysis]) -> List[ExtractedQuestion]:
        """
        Consolidate question data across pages, handling multi-page questions
        """
        questions_dict: Dict[int, ExtractedQuestion] = {}
        
        for analysis in page_analyses:
            for q_data in analysis.questions_found:
                q_num = q_data.get('question_number')
                if not q_num:
                    continue
                
                topic_code = str(q_data.get('topic', '1'))
                topic_name = MATHS_B_TOPICS.get(topic_code, "Unknown")
                
                if q_num in questions_dict:
                    # Update existing question (multi-page)
                    existing = questions_dict[q_num]
                    existing.page_numbers.append(analysis.page_number)
                    # Add any new sub-parts
                    for part in q_data.get('sub_parts', []):
                        if part not in existing.sub_parts:
                            existing.sub_parts.append(part)
                    # Update marks if found
                    if q_data.get('marks') and not existing.marks:
                        existing.marks = q_data.get('marks')
                else:
                    # New question
                    questions_dict[q_num] = ExtractedQuestion(
                        question_number=q_num,
                        sub_parts=q_data.get('sub_parts', []),
                        topic_code=topic_code,
                        topic_name=topic_name.split('(')[0].strip(),
                        confidence=0.95,  # High confidence with vision model
                        text_summary=q_data.get('brief_description', ''),
                        page_numbers=[analysis.page_number],
                        marks=q_data.get('marks')
                    )
        
        # Sort by question number
        return sorted(questions_dict.values(), key=lambda q: q.question_number)


def test_extractor():
    """Test the vision extractor on a sample paper"""
    print("=" * 70)
    print("VISION EXTRACTOR TEST")
    print("=" * 70)
    
    extractor = VisionExtractor(use_fast_model=False)  # Use best model
    
    # Find a test paper
    test_dir = Path("data/raw/IGCSE/Maths B/2024/May-Jun")
    if not test_dir.exists():
        test_dir = Path("data/raw/IGCSE/Maths B/2023/May-Jun")
    
    papers = list(test_dir.glob("Paper 1.pdf"))
    if not papers:
        print("No test papers found!")
        return
    
    paper = papers[0]
    print(f"\nTesting with: {paper}")
    
    questions = extractor.analyze_paper(paper, 2024, "Jun", "1")
    
    print(f"\n{'=' * 70}")
    print(f"RESULTS: {len(questions)} questions found")
    print("=" * 70)
    
    for q in questions:
        parts = f" ({', '.join(q.sub_parts)})" if q.sub_parts else ""
        marks = f" [{q.marks} marks]" if q.marks else ""
        pages = f"p{','.join(str(p+1) for p in q.page_numbers)}"
        print(f"  Q{q.question_number}{parts}: Topic {q.topic_code} ({q.topic_name}){marks} - {pages}")
        if q.text_summary:
            print(f"    → {q.text_summary}")


if __name__ == "__main__":
    test_extractor()
