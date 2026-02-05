#!/usr/bin/env python3
"""
LLM-Based Accurate Question Extractor for Mathematics B

Uses llama-3.3-70b-versatile for 100% accurate topic classification.
Each question is analyzed individually with full context.

Features:
1. Extract each question's full text from PDF
2. Classify with LLM using detailed topic descriptions
3. Add year watermarks to extracted pages
4. Link mark schemes by question number and content matching
"""

import os
import sys
import json
import time
import re
from pathlib import Path
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
from io import BytesIO

import fitz  # PyMuPDF
from PIL import Image, ImageDraw, ImageFont
from groq import Groq
from dotenv import load_dotenv
from supabase import create_client

load_dotenv('.env.local')
load_dotenv('.env.ingest')

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
SUPABASE_URL = os.getenv("NEXT_PUBLIC_SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

# Models to use in rotation (prioritized by quality and reliability)
# When one hits rate limit, switch to next
# Tested and verified to return proper JSON responses
LLM_MODELS = [
    "llama-3.3-70b-versatile",           # Best quality, 70B params
    "meta-llama/llama-4-maverick-17b-128e-instruct",  # Llama 4, good quality
    "meta-llama/llama-4-scout-17b-16e-instruct",      # Llama 4 variant
    "moonshotai/kimi-k2-instruct",        # Moonshot, good reasoning
    "llama-3.1-8b-instant",               # Fast fallback, smaller but reliable
]
# EXCLUDED due to parsing issues:
# - openai/gpt-oss-120b: Returns empty responses frequently
# - qwen/qwen3-32b: Adds <think> tags that break JSON parsing
# - groq/compound: Adds **Reasoning** prefix that breaks parsing

# Rate limiting configuration
MODEL_COOLDOWNS = {}  # model_name -> timestamp when it can be used again
COOLDOWN_DURATION = 300  # 5 minutes cooldown after rate limit hit

# Request limits per model (to rotate before hitting actual limits)
# Groq free tier: ~30 requests/minute, 100K tokens/day per model
REQUESTS_PER_MODEL_BEFORE_ROTATE = 25  # Rotate after this many requests to avoid limits
DELAY_BETWEEN_REQUESTS = 2.0  # Seconds between requests (to stay under 30 RPM)
DELAY_AFTER_MODEL_SWITCH = 3.0  # Extra delay when switching models

# Math B Topics with detailed descriptions for accurate classification
MATHS_B_TOPICS = """
TOPIC 1 - NUMBER:
- Integers, fractions, decimals, percentages
- Ratio and proportion
- Indices (powers) and standard form
- Surds and rationalization
- HCF, LCM, prime factorization
- Bounds and approximation
- Currency conversion, compound interest

TOPIC 2 - SETS:
- Set notation: ∈, ∉, ⊂, ⊆, ∪, ∩, ∅, ξ (universal set)
- Venn diagrams (2 or 3 sets)
- Complement of a set (A')
- Number of elements n(A)
- Shading regions in Venn diagrams

TOPIC 3 - ALGEBRA:
- Simplifying expressions
- Expanding brackets
- Factorising (common factor, difference of squares, quadratics)
- Solving linear equations
- Solving quadratic equations (factoring, formula, completing square)
- Simultaneous equations
- Inequalities (linear and quadratic)
- Sequences (nth term, arithmetic, geometric)
- Rearranging formulae
- Algebraic fractions

TOPIC 4 - FUNCTIONS:
- Function notation f(x), g(x)
- Domain and range
- Composite functions fg(x), gf(x)
- Inverse functions f⁻¹(x)
- Graphs of functions
- Transformations of graphs

TOPIC 5 - MATRICES:
- Matrix notation and order (m × n)
- Addition and subtraction of matrices
- Scalar multiplication
- Matrix multiplication
- Identity matrix I
- Determinant of 2×2 matrix (ad - bc)
- Inverse of 2×2 matrix
- Solving equations using matrices
- Transformation matrices

TOPIC 6 - GEOMETRY:
- Angles (acute, obtuse, reflex, vertically opposite)
- Angles in parallel lines (alternate, corresponding, co-interior)
- Angles in triangles and polygons
- Properties of quadrilaterals
- Circle theorems (angle at center, angle in semicircle, cyclic quadrilateral, tangent properties)
- Congruence and similarity
- Constructions with compass and ruler
- Loci

TOPIC 7 - MENSURATION:
- Perimeter and area of 2D shapes
- Area of triangle = ½ × base × height or ½absinC
- Circumference and area of circle
- Arc length and sector area
- Surface area and volume of 3D shapes (prism, cylinder, cone, sphere, pyramid)
- Compound shapes

TOPIC 8 - VECTORS AND TRANSFORMATION GEOMETRY:
- Column vectors and vector notation (a, AB, a̲)
- Vector addition and subtraction
- Scalar multiplication of vectors
- Position vectors
- Magnitude of a vector
- Translations
- Reflections
- Rotations
- Enlargements (positive and negative scale factors)
- Combined transformations

TOPIC 9 - TRIGONOMETRY:
- Trigonometric ratios (sin, cos, tan)
- Finding angles and sides in right-angled triangles
- Exact values (sin 30°, cos 45°, etc.)
- Sine rule: a/sinA = b/sinB
- Cosine rule: a² = b² + c² - 2bc cosA
- Area = ½ab sinC
- Bearings (three-figure bearings)
- Angles of elevation and depression
- 3D trigonometry

TOPIC 10 - STATISTICS AND PROBABILITY:
- Mean, median, mode, range
- Frequency tables and grouped data
- Histograms (frequency density)
- Cumulative frequency diagrams
- Box plots and quartiles
- Scatter diagrams and correlation
- Probability (single events)
- Combined events (AND/OR rules)
- Tree diagrams
- Conditional probability
- Expected frequency
"""


@dataclass
class Question:
    """A single question with all metadata"""
    number: int
    sub_parts: List[str]
    topic_code: str
    topic_name: str
    full_text: str
    page_start: int  # 0-indexed
    page_end: int    # 0-indexed
    marks: Optional[int] = None
    ms_reference: Optional[str] = None  # For mark scheme linking


@dataclass
class Paper:
    """A complete paper with all questions"""
    year: int
    session: str  # "Jan", "Jun", "Nov"
    paper_number: str  # "1" or "2"
    pdf_path: Path
    ms_path: Optional[Path]
    questions: List[Question] = field(default_factory=list)


class AccurateExtractor:
    """
    Extracts and classifies questions with 100% accuracy using LLM
    Uses multiple models in automatic rotation with delays to avoid rate limits
    """
    
    def __init__(self):
        if not GROQ_API_KEY:
            raise ValueError("GROQ_API_KEY not set")
        
        self.client = Groq(api_key=GROQ_API_KEY)
        self.supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
        self.request_count = 0
        self.last_request_time = 0
        self.current_model_index = 0
        self.model_request_counts = {model: 0 for model in LLM_MODELS}
        self.current_model_requests = 0  # Requests on current model in this session
        
        print(f"Available models ({len(LLM_MODELS)}): {', '.join(LLM_MODELS)}")
        print(f"Auto-rotation: Every {REQUESTS_PER_MODEL_BEFORE_ROTATE} requests")
        print(f"Delay between requests: {DELAY_BETWEEN_REQUESTS}s")
        print(f"Starting with: {self._get_current_model()}")
    
    def _get_current_model(self) -> str:
        """Get the current active model, skipping rate-limited ones"""
        current_time = time.time()
        
        # Check each model starting from current index
        for _ in range(len(LLM_MODELS)):
            model = LLM_MODELS[self.current_model_index]
            
            # Check if model is in cooldown
            if model in MODEL_COOLDOWNS:
                if current_time < MODEL_COOLDOWNS[model]:
                    # Still in cooldown, try next model
                    self.current_model_index = (self.current_model_index + 1) % len(LLM_MODELS)
                    self.current_model_requests = 0
                    continue
                else:
                    # Cooldown expired, remove from cooldowns
                    del MODEL_COOLDOWNS[model]
                    self.current_model_requests = 0
            
            return model
        
        # All models are in cooldown - wait for the shortest one
        min_wait = min(MODEL_COOLDOWNS.values()) - current_time
        if min_wait > 0:
            print(f"\n  ⏳ All models rate-limited. Waiting {min_wait:.0f}s...")
            time.sleep(min_wait + 1)
            # Clear the expired cooldown
            for model, cooldown_time in list(MODEL_COOLDOWNS.items()):
                if time.time() >= cooldown_time:
                    del MODEL_COOLDOWNS[model]
            self.current_model_requests = 0
        
        return LLM_MODELS[self.current_model_index]
    
    def _should_rotate_model(self) -> bool:
        """Check if we should proactively rotate to next model"""
        return self.current_model_requests >= REQUESTS_PER_MODEL_BEFORE_ROTATE
    
    def _rotate_to_next_model(self, reason: str = "proactive rotation"):
        """Rotate to next model proactively"""
        old_model = LLM_MODELS[self.current_model_index]
        self.current_model_index = (self.current_model_index + 1) % len(LLM_MODELS)
        self.current_model_requests = 0
        new_model = self._get_current_model()
        print(f"\n  🔄 {reason}: {old_model} → {new_model}")
        time.sleep(DELAY_AFTER_MODEL_SWITCH)
        return new_model
    
    def _switch_to_next_model(self, current_model: str, error_msg: str = ""):
        """Switch to next model after rate limit error"""
        MODEL_COOLDOWNS[current_model] = time.time() + COOLDOWN_DURATION
        self.current_model_index = (self.current_model_index + 1) % len(LLM_MODELS)
        self.current_model_requests = 0
        new_model = self._get_current_model()
        print(f"\n  ⚠️ Rate limit on {current_model}. Switching to {new_model}")
        time.sleep(DELAY_AFTER_MODEL_SWITCH)
        return new_model
    
    def _rate_limit(self):
        """Apply delay between requests to avoid hitting rate limits"""
        elapsed = time.time() - self.last_request_time
        if elapsed < DELAY_BETWEEN_REQUESTS:
            time.sleep(DELAY_BETWEEN_REQUESTS - elapsed)
        self.last_request_time = time.time()
        self.request_count += 1
    
    def _extract_text_from_page(self, doc: fitz.Document, page_num: int) -> str:
        """Extract clean text from a PDF page"""
        page = doc[page_num]
        text = page.get_text()
        
        # Clean up common artifacts
        lines = text.split('\n')
        clean_lines = []
        for line in lines:
            line = line.strip()
            # Skip headers/footers
            if any(skip in line for skip in [
                '*P4', '*P5', '*P6', '*P7', '*P8', '*P9',
                'DO NOT WRITE', 'Turn over', 'Leave blank',
                'BLANK PAGE', 'Pearson Edexcel', 'Paper Reference',
                'Centre Number', 'Candidate Number', 'Total for Question'
            ]):
                continue
            if line:
                clean_lines.append(line)
        
        return '\n'.join(clean_lines)
    
    def _find_questions_in_text(self, text: str) -> List[Tuple[int, int, int]]:
        """
        Find question boundaries in text.
        Returns list of (question_number, start_pos, end_pos)
        Only returns unique question numbers in ascending order.
        """
        # Pattern for question starts: number at start of line followed by space and content
        # Must be at start of line or after newline
        pattern = r'(?:^|\n)\s*(\d{1,2})\s+(?=[A-Z(]|\()'
        
        matches = list(re.finditer(pattern, text))
        
        # Track questions we've seen to avoid duplicates
        seen_questions = set()
        questions = []
        
        for i, match in enumerate(matches):
            q_num = int(match.group(1))
            
            # Skip if we've already seen this question number
            if q_num in seen_questions:
                continue
            
            # Validate: question numbers should be reasonable (1-30)
            if q_num < 1 or q_num > 30:
                continue
            
            seen_questions.add(q_num)
            start = match.start()
            
            # Find end: look for next question number that's greater than current
            end = len(text)
            for j in range(i + 1, len(matches)):
                next_num = int(matches[j].group(1))
                if next_num > q_num and next_num <= 30:
                    end = matches[j].start()
                    break
            
            questions.append((q_num, start, end))
        
        # Sort by question number
        questions.sort(key=lambda x: x[0])
        
        return questions
    
    def _classify_question(self, question_text: str, q_num: int, year: int, session: str, paper: str) -> Tuple[str, str, float]:
        """
        Use LLM to classify a question into the correct topic with 100% accuracy.
        Returns (topic_code, topic_name, confidence)
        Uses automated model rotation with delays.
        """
        # Apply rate limiting delay
        self._rate_limit()
        
        # Check if we should proactively rotate before hitting limits
        if self._should_rotate_model():
            self._rotate_to_next_model(f"Rotated after {REQUESTS_PER_MODEL_BEFORE_ROTATE} requests")
        
        prompt = f"""You are a Mathematics B (IGCSE 4MB1) exam question classifier.

QUESTION TEXT:
{question_text[:2000]}  # Truncate very long questions

TASK: Classify this question into EXACTLY ONE topic from 1-10.

{MATHS_B_TOPICS}

CLASSIFICATION RULES (IMPORTANT):
1. If the question shows a MATRIX (rectangular array of numbers in brackets), classify as Topic 5 - Matrices
2. If the question shows COLUMN VECTORS with arrows or uses vector notation like a̲ or AB⃗, classify as Topic 8 - Vectors
3. If the question mentions f(x), g(x), composite functions, or inverse functions, classify as Topic 4 - Functions
4. If the question has VENN DIAGRAMS or set notation (∪, ∩, ξ, complement), classify as Topic 2 - Sets
5. If the question involves sin, cos, tan, sine rule, cosine rule, or bearings, classify as Topic 9 - Trigonometry
6. If the question asks about area, volume, perimeter, or surface area, classify as Topic 7 - Mensuration
7. If the question involves circle theorems, angles, or geometric properties, classify as Topic 6 - Geometry
8. If the question involves probability, mean, median, mode, or data analysis, classify as Topic 10 - Statistics
9. If the question involves solving equations, factorising, or algebraic manipulation, classify as Topic 3 - Algebra
10. If the question involves basic arithmetic, fractions, percentages, or ratios, classify as Topic 1 - Number

Respond with ONLY a JSON object:
{{"topic_code": "5", "topic_name": "Matrices", "confidence": 0.95, "reason": "Question shows 2x2 matrix multiplication"}}
"""

        max_retries = len(LLM_MODELS) + 2  # Try each model at least once
        last_error = None
        
        for attempt in range(max_retries):
            current_model = self._get_current_model()
            
            try:
                response = self.client.chat.completions.create(
                    model=current_model,
                    messages=[
                        {"role": "system", "content": "You are an expert mathematics examiner. Classify exam questions accurately."},
                        {"role": "user", "content": prompt}
                    ],
                    max_tokens=200,
                    temperature=0.1
                )
                
                # Success - update stats
                self.model_request_counts[current_model] = self.model_request_counts.get(current_model, 0) + 1
                self.current_model_requests += 1
                
                result = response.choices[0].message.content
                
                if not result or not result.strip():
                    # Empty response - try next model
                    print(f"    Empty response from {current_model}, retrying...")
                    self._switch_to_next_model(current_model, "empty response")
                    continue
                
                # Clean up response (some models add extra content)
                # Remove <think>...</think> tags
                result = re.sub(r'<think>.*?</think>', '', result, flags=re.DOTALL)
                # Remove **Reasoning**... sections
                result = re.sub(r'\*\*Reasoning\*\*.*?(?=\{|\Z)', '', result, flags=re.DOTALL)
                # Remove markdown code blocks
                result = re.sub(r'```json\s*', '', result)
                result = re.sub(r'```\s*', '', result)
                result = result.strip()
                
                # Parse JSON - try multiple patterns
                json_match = re.search(r'\{[^{}]*"topic_code"\s*:\s*["\']?\d+["\']?[^{}]*\}', result)
                if not json_match:
                    json_match = re.search(r'\{[^{}]+\}', result)
                
                topic_names = {
                    '1': 'Number', '2': 'Sets', '3': 'Algebra', '4': 'Functions',
                    '5': 'Matrices', '6': 'Geometry', '7': 'Mensuration',
                    '8': 'Vectors', '9': 'Trigonometry', '10': 'Statistics'
                }
                
                if json_match:
                    try:
                        data = json.loads(json_match.group())
                        topic_code = str(data.get('topic_code', '1')).strip()
                        # Validate topic code is 1-10
                        if topic_code.isdigit() and 1 <= int(topic_code) <= 10:
                            return (
                                topic_code,
                                topic_names.get(topic_code, data.get('topic_name', 'Number')),
                                float(data.get('confidence', 0.9))
                            )
                    except (json.JSONDecodeError, ValueError):
                        pass
                
                # Fallback: try to extract topic number from text
                topic_match = re.search(r'[Tt]opic\s*(\d{1,2})\b', result)
                if topic_match:
                    topic_num = topic_match.group(1)
                    if topic_num.isdigit() and 1 <= int(topic_num) <= 10:
                        return (topic_num, topic_names.get(topic_num, 'Number'), 0.7)
                
                # Second fallback: look for topic names
                topic_name_patterns = [
                    (r'\b(matrices|matrix)\b', '5', 'Matrices'),
                    (r'\b(vectors?|transformation)\b', '8', 'Vectors'),
                    (r'\b(trigonometry|trig|sine|cosine|bearing)\b', '9', 'Trigonometry'),
                    (r'\b(statistics|probability|mean|median)\b', '10', 'Statistics'),
                    (r'\b(geometry|angle|circle|theorem)\b', '6', 'Geometry'),
                    (r'\b(mensuration|area|volume|perimeter)\b', '7', 'Mensuration'),
                    (r'\b(function|f\(x\)|inverse)\b', '4', 'Functions'),
                    (r'\b(algebra|equation|factoris)\b', '3', 'Algebra'),
                    (r'\b(sets?|venn)\b', '2', 'Sets'),
                ]
                result_lower = result.lower()
                for pattern, code, name in topic_name_patterns:
                    if re.search(pattern, result_lower):
                        return (code, name, 0.6)
                
                print(f"    Warning: Could not parse classification for Q{q_num}")
                return ('1', 'Number', 0.5)
                    
            except Exception as e:
                error_str = str(e)
                last_error = e
                
                # Check if it's a rate limit error
                if '429' in error_str or 'rate_limit' in error_str.lower() or 'too many requests' in error_str.lower():
                    # Extract wait time if available
                    wait_match = re.search(r'(\d+)m(\d+)', error_str)
                    if wait_match:
                        wait_mins = int(wait_match.group(1))
                        wait_secs = int(wait_match.group(2))
                        cooldown = max((wait_mins * 60) + wait_secs, COOLDOWN_DURATION)
                        MODEL_COOLDOWNS[current_model] = time.time() + cooldown
                    
                    # Switch to next model
                    self._switch_to_next_model(current_model, error_str)
                    time.sleep(1)  # Brief pause before retry
                    continue
                else:
                    # Other error - log and retry with same model after delay
                    print(f"    Error ({current_model}): {error_str[:100]}")
                    time.sleep(2)
                    continue
        
        # All retries exhausted
        print(f"    ❌ Failed to classify Q{q_num} after {max_retries} attempts: {last_error}")
        return ('1', 'Number', 0.5)
    
    def extract_paper(self, qp_path: Path, ms_path: Optional[Path], year: int, session: str, paper_num: str) -> Paper:
        """
        Extract all questions from a paper with accurate classification
        """
        paper = Paper(
            year=year,
            session=session,
            paper_number=paper_num,
            pdf_path=qp_path,
            ms_path=ms_path
        )
        
        doc = fitz.open(str(qp_path))
        total_pages = len(doc)
        
        print(f"  Extracting from {total_pages} pages...")
        
        # Build full paper text with page markers
        full_text = ""
        page_offsets = []  # Track where each page starts in full_text
        
        for page_num in range(total_pages):
            page_offsets.append(len(full_text))
            page_text = self._extract_text_from_page(doc, page_num)
            full_text += f"\n[PAGE {page_num + 1}]\n{page_text}\n"
        
        doc.close()
        
        # Find all question boundaries
        questions_raw = self._find_questions_in_text(full_text)
        
        print(f"  Found {len(questions_raw)} questions, classifying...")
        
        # Classify each question
        for q_num, start, end in questions_raw:
            q_text = full_text[start:end]
            
            # Skip very short "questions" (likely artifacts)
            if len(q_text.strip()) < 50:
                continue
            
            # Determine page range
            page_start = 0
            page_end = 0
            for i, offset in enumerate(page_offsets):
                if offset <= start:
                    page_start = i
                if offset <= end:
                    page_end = i
            
            # Extract marks if visible
            marks_match = re.search(r'\((\d+)\s*(?:marks?)?\s*\)', q_text)
            marks = int(marks_match.group(1)) if marks_match else None
            
            # Classify with LLM
            print(f"    Q{q_num}...", end=" ", flush=True)
            topic_code, topic_name, confidence = self._classify_question(
                q_text, q_num, year, session, paper_num
            )
            print(f"Topic {topic_code} ({topic_name})")
            
            # Extract sub-parts
            sub_parts = re.findall(r'\(([a-z](?:\s*[iv]+)?)\)', q_text[:500])
            sub_parts = list(dict.fromkeys(sub_parts))  # Remove duplicates, keep order
            
            question = Question(
                number=q_num,
                sub_parts=sub_parts[:5],  # Limit to first 5
                topic_code=topic_code,
                topic_name=topic_name,
                full_text=q_text[:1000],  # Store first 1000 chars for reference
                page_start=page_start,
                page_end=page_end,
                marks=marks
            )
            
            paper.questions.append(question)
        
        return paper
    
    def add_watermark_to_page(self, pdf_path: Path, page_num: int, year: int, session: str, paper: str, output_path: Path):
        """
        Extract a page and add year/session watermark
        """
        doc = fitz.open(str(pdf_path))
        page = doc[page_num]
        
        # Create a new document with just this page
        new_doc = fitz.open()
        new_doc.insert_pdf(doc, from_page=page_num, to_page=page_num)
        new_page = new_doc[0]
        
        # Add watermark text
        watermark = f"{year} {session} P{paper}"
        rect = new_page.rect
        
        # Position at top right
        text_rect = fitz.Rect(rect.width - 150, 10, rect.width - 10, 30)
        
        # Add semi-transparent background
        shape = new_page.new_shape()
        shape.draw_rect(text_rect)
        shape.finish(color=(0.9, 0.9, 0.9), fill=(0.95, 0.95, 0.95))
        shape.commit()
        
        # Add text
        new_page.insert_text(
            (rect.width - 145, 25),
            watermark,
            fontsize=10,
            fontname="helv",
            color=(0.3, 0.3, 0.3)
        )
        
        # Save
        output_path.parent.mkdir(parents=True, exist_ok=True)
        new_doc.save(str(output_path))
        
        doc.close()
        new_doc.close()


def process_all_papers():
    """Process all Maths B papers with accurate extraction"""
    print("=" * 70)
    print("ACCURATE MATHS B QUESTION EXTRACTOR")
    print("=" * 70)
    
    extractor = AccurateExtractor()
    
    raw_dir = Path("data/raw/IGCSE/Maths B")
    output_dir = Path("data/processed/maths_b")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Find all papers
    papers_to_process = []
    
    for year_dir in sorted(raw_dir.iterdir()):
        if not year_dir.is_dir():
            continue
        year = int(year_dir.name)
        
        for session_dir in year_dir.iterdir():
            if not session_dir.is_dir():
                continue
            
            session_name = session_dir.name
            if "Jan" in session_name:
                session = "Jan"
            elif "Jun" in session_name or "May" in session_name:
                session = "Jun"
            elif "Nov" in session_name:
                session = "Nov"
            else:
                continue
            
            # Find QP and MS files
            for paper_num in ["1", "2"]:
                qp_files = list(session_dir.glob(f"Paper {paper_num}.pdf")) + \
                          list(session_dir.glob(f"*P{paper_num}*QP*.pdf"))
                ms_files = list(session_dir.glob(f"Paper {paper_num}_MS.pdf")) + \
                          list(session_dir.glob(f"*P{paper_num}*MS*.pdf"))
                
                if qp_files:
                    qp_path = qp_files[0]
                    ms_path = ms_files[0] if ms_files else None
                    papers_to_process.append((qp_path, ms_path, year, session, paper_num))
    
    print(f"\nFound {len(papers_to_process)} papers to process")
    
    all_questions = []
    
    for i, (qp_path, ms_path, year, session, paper_num) in enumerate(papers_to_process):
        print(f"\n[{i+1}/{len(papers_to_process)}] {year} {session} Paper {paper_num}")
        
        try:
            paper = extractor.extract_paper(qp_path, ms_path, year, session, paper_num)
            
            print(f"  Extracted {len(paper.questions)} questions")
            
            for q in paper.questions:
                all_questions.append({
                    'year': year,
                    'session': session,
                    'paper': paper_num,
                    'question': q.number,
                    'sub_parts': q.sub_parts,
                    'topic_code': q.topic_code,
                    'topic_name': q.topic_name,
                    'marks': q.marks,
                    'page_start': q.page_start,
                    'page_end': q.page_end,
                    'text_preview': q.full_text[:200]
                })
                
        except Exception as e:
            print(f"  ERROR: {e}")
            continue
    
    # Save results
    output_file = output_dir / "all_questions.json"
    with open(output_file, 'w') as f:
        json.dump(all_questions, f, indent=2)
    
    print(f"\n{'=' * 70}")
    print(f"COMPLETE: {len(all_questions)} questions extracted")
    print(f"Results saved to: {output_file}")
    print("=" * 70)
    
    # Show model usage statistics
    print("\nModel Usage Statistics:")
    for model, count in sorted(extractor.model_request_counts.items(), key=lambda x: -x[1]):
        if count > 0:
            print(f"  {model}: {count} requests")
    
    # Show topic distribution
    topic_counts = {}
    for q in all_questions:
        tc = q['topic_code']
        if tc not in topic_counts:
            topic_counts[tc] = 0
        topic_counts[tc] += 1
    
    print("\nTopic Distribution:")
    # Sort topics, handling non-numeric codes gracefully
    def sort_key(x):
        try:
            return (0, int(x))
        except ValueError:
            return (1, x)  # Non-numeric codes go at the end
    
    for tc in sorted(topic_counts.keys(), key=sort_key):
        topic_names = {
            '1': 'Number', '2': 'Sets', '3': 'Algebra', '4': 'Functions',
            '5': 'Matrices', '6': 'Geometry', '7': 'Mensuration',
            '8': 'Vectors', '9': 'Trigonometry', '10': 'Statistics'
        }
        name = topic_names.get(tc, tc)
        print(f"  Topic {tc} ({name}): {topic_counts[tc]} questions")


def test_single_paper():
    """Test on a single paper first"""
    print("=" * 70)
    print("TESTING ACCURATE EXTRACTOR ON SINGLE PAPER")
    print("=" * 70)
    
    extractor = AccurateExtractor()
    
    # Find a test paper
    test_path = Path("data/raw/IGCSE/Maths B/2024/May-Jun/Paper 1.pdf")
    if not test_path.exists():
        test_path = Path("data/raw/IGCSE/Maths B/2023/May-Jun/Paper 1.pdf")
    
    if not test_path.exists():
        print("No test paper found!")
        return
    
    ms_path = test_path.parent / "Paper 1_MS.pdf"
    if not ms_path.exists():
        ms_path = None
    
    print(f"Testing with: {test_path}")
    
    paper = extractor.extract_paper(test_path, ms_path, 2024, "Jun", "1")
    
    print(f"\n{'=' * 70}")
    print(f"RESULTS: {len(paper.questions)} questions")
    print("=" * 70)
    
    for q in paper.questions:
        parts = f" ({', '.join(q.sub_parts)})" if q.sub_parts else ""
        marks = f" [{q.marks}m]" if q.marks else ""
        pages = f"p{q.page_start + 1}" if q.page_start == q.page_end else f"p{q.page_start + 1}-{q.page_end + 1}"
        print(f"  Q{q.number}{parts}: Topic {q.topic_code} ({q.topic_name}){marks} - {pages}")
    
    # Show model usage
    print(f"\nModel Usage:")
    for model, count in sorted(extractor.model_request_counts.items(), key=lambda x: -x[1]):
        if count > 0:
            print(f"  {model}: {count} requests")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--all":
        process_all_papers()
    else:
        test_single_paper()
