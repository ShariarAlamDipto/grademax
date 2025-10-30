#!/usr/bin/env python3
"""
Physics Question Paper & Mark Scheme Analyzer using LLM
Uses the exact specifications from the prompt pack to segment QP and link MS
"""

import os
import sys
import json
import time
from pathlib import Path
from dotenv import load_dotenv
import requests
from PyPDF2 import PdfReader, PdfWriter
from io import BytesIO
import pdfplumber

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Load environment variables
env_path = project_root / '.env.local'
load_dotenv(env_path)

SYSTEM_PROMPT = """You are a deterministic **ingestion agent**. Your job is to **segment the Question Paper (QP) by whole question** and **link each question to its Mark Scheme (MS) pages**, without retypesetting anything. Work from **page text only** (already OCR'd), but return **page indices** so the downstream merger can grab the original PDF pages/snips.

## Non-negotiables

1. **Whole-question only**: subparts (a),(b)… are not tagged separately.
2. **Preserve formatting**: never rewrite text; you only return **page numbers (and optional crop boxes)**.
3. **Multiple questions per MS page**: OK—return the **same MS page** for multiple questions when needed.
4. **Physics 4PH1 layout cues** (anchors you must use):

   * QP shows **"(Total for Question n = X marks)"** at each question end; use it as a **hard stop** for segmentation. 
   * MS pages use a grid like **"Question number | Answer | Notes | Marks"** and end rows with **"Total for question n: X marks."** Use these to collect MS pages per question. 
   * Marking codes such as **M1, A1, B1** are method/accuracy/independent marks; treat them as **evidence** you're on the right MS row but **don't parse marks**.

## Output contract (strict JSON Schema)

You must return **only** JSON matching this schema:

```json
{
  "type": "object",
  "properties": {
    "paper": {
      "type": "object",
      "properties": {
        "board": {"type": "string"},
        "level": {"type": "string"},
        "subject_code": {"type": "string"},
        "paper_code": {"type": "string"},
        "total_marks": {"type": "integer"}
      },
      "required": ["board","level","subject_code","paper_code"]
    },
    "questions": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "qnum": {"type":"string"},
          "qp_pages": {
            "type": "array", "items": {"type":"integer"}
          },
          "ms_pages": {
            "type":"array","items":{"type":"integer"}
          },
          "evidence": {"type":"array","items":{"type":"string"}}
        },
        "required": ["qnum","qp_pages","ms_pages","evidence"]
      }
    }
  },
  "required": ["paper","questions"]
}
```

## Algorithm (do this in order)

**A. Question Paper (QP) segmentation**

1. Scan sequentially, page by page.
2. **Question start** = a line beginning with a bare integer **"1 ", "2 "… at left margin** OR the phrase "**Answer ALL questions**" followed by the first numbered stem.
3. **Question end** = the first occurrence of **"(Total for Question n = X marks)"** after that question's stem; include **all intervening pages** up to that marker. If the marker is absent on a page, keep appending pages until it appears. 
4. Store **qp_pages** as the closed page range from start→end (0-based).

**B. Mark Scheme (MS) linking**

1. For each **qnum**, scan MS pages for either:
   * the row header **"Question number …"** with that **n**, or
   * in-page labels "**(Total for question n: X marks)**".
     Collect all pages from the first match for **n** until the next question's section begins or until you hit **"Total for question n"**. 
2. If two (or more) questions share one MS page, **include the page in each question's `ms_pages`**.
3. Add short **evidence** strings: e.g., `"QP: (Total for Question 4 = 7 marks)"`, `"MS: Total for question 4: 7 marks"`.

**C. Safety & edge cases**

* If a QP question spills across blank pages, still include those pages (they often contain diagrams/continuations). 
* If an MS page contains only a tail line "Total for question n…", still include it for **n**. 
* Ignore global instructions like "The total mark for this paper is 70" (paper-level metadata only). 
* Never infer sub-question boundaries; we tag one **whole** question per JSON object.

## Evidence capture (copy literal snippets)

* From QP: capture the exact **Total** line (e.g., `"(Total for Question 3 = 12 marks)"`). 
* From MS: capture the **table header** (e.g., `"Question number  Answer  Notes  Marks"`) and the **Total for question n** line.

Return **only** valid JSON. No prose, no markdown code blocks."""


def extract_text_from_pdf(pdf_path, extract_type="qp"):
    """Extract text from all pages of a PDF, optimized for size."""
    pages = []
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for i, page in enumerate(pdf.pages):
                text = page.extract_text() or ""
                
                # For QP: Extract only critical markers
                if extract_type == "qp":
                    # Look for question markers and totals
                    lines = text.split('\n')
                    key_lines = []
                    for line in lines:
                        # Keep only lines with question numbers or totals
                        if line.strip() and (
                            (line.strip()[0].isdigit() and len(line.strip()) < 50) or
                            'Total for Question' in line or
                            'Answer ALL questions' in line
                        ):
                            key_lines.append(line)
                    
                    # For large papers (>30 pages), use only key lines
                    if len(pdf.pages) > 30:
                        summary = "\n".join(key_lines[:15])  # Top 15 key lines per page
                    else:
                        # For smaller papers, include more context
                        summary = text[:800] + "\n...\n" + "\n".join(key_lines[-10:])
                    
                    pages.append({"index": i, "text": summary})
                
                # For MS: Extract table structure and totals
                else:
                    lines = text.split('\n')
                    key_lines = []
                    for line in lines:
                        if line.strip() and (
                            'Question' in line or
                            'question' in line or
                            'Total' in line or
                            'Marks' in line or
                            (line.strip()[0].isdigit() and len(line.strip()) < 50)
                        ):
                            key_lines.append(line)
                    
                    # Keep only most relevant lines for MS
                    summary = "\n".join(key_lines[:30])  # First 30 relevant lines
                    pages.append({"index": i, "text": summary})
                    
    except Exception as e:
        print(f"Error extracting text from {pdf_path}: {e}")
    return pages


def analyze_paper_with_llm(qp_path, ms_path, year, season, paper_num):
    """Use LLM to analyze QP and MS, return question mapping."""
    print(f"  [LLM] Extracting text from QP and MS...")
    
    # Convert to Path objects if strings
    qp_path = Path(qp_path) if isinstance(qp_path, str) else qp_path
    ms_path = Path(ms_path) if isinstance(ms_path, str) else ms_path
    
    # Extract text from both PDFs (optimized)
    qp_pages = extract_text_from_pdf(qp_path, "qp")
    ms_pages = extract_text_from_pdf(ms_path, "ms") if ms_path and ms_path.exists() else []
    
    print(f"  [LLM] QP: {len(qp_pages)} pages, MS: {len(ms_pages)} pages")
    
    # Build the user message
    user_message = {
        "qp": {"pages": qp_pages},
        "ms": {"pages": ms_pages},
        "paper_hint": {
            "board": "Pearson Edexcel",
            "level": "International GCSE (9-1)",
            "subject_code": "4PH1",
            "paper_code": paper_num
        }
    }
    
    task_instruction = """Segment the QP into whole questions using the anchors above, then link each question to all relevant MS pages. Return **only** JSON matching the schema. Do not include prose.

**Quality checklist (must satisfy)**

* Every `qnum` that appears in QP has a corresponding entry with **at least one MS page**.
* Every `qp_pages` set ends exactly where the **Total for Question n** marker appears. 
* If an MS page covers several questions, it appears in each relevant `ms_pages`."""
    
    # Only use Groq (OpenRouter not working reliably)
    groq_key = os.getenv('GROQ_API_KEY')
    
    if groq_key:
        print(f"  [LLM] Using Groq API...")
        result = call_groq(user_message, task_instruction, groq_key)
        if result:
            return result
    else:
        print("  [ERROR] No Groq API key found")
        return None
    
    print(f"  [ERROR] No valid API response")
    return None


def call_openrouter(user_message, task_instruction, api_key):
    """Call OpenRouter with structured output."""
    try:
        # Use a model that supports JSON mode
        model = "google/gemma-3-27b:free"  # Good balance of capability and speed
        
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://grademax.app",
            "X-Title": "GradeMax Physics QP/MS Analyzer"
        }
        
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": json.dumps(user_message) + "\n\n" + task_instruction}
            ],
            "temperature": 0.1,
            "response_format": {"type": "json_object"}
        }
        
        response = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers=headers,
            json=payload,
            timeout=120
        )
        
        response.raise_for_status()
        result = response.json()
        content = result['choices'][0]['message']['content']
        
        # Parse JSON
        data = json.loads(content)
        return data
        
    except Exception as e:
        print(f"    OpenRouter error: {e}")
        return None


def call_groq(user_message, task_instruction, api_key):
    """Call Groq with JSON mode."""
    try:
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": "llama-3.3-70b-versatile",
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": json.dumps(user_message) + "\n\n" + task_instruction}
            ],
            "temperature": 0.1,
            "response_format": {"type": "json_object"}
        }
        
        response = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers=headers,
            json=payload,
            timeout=120
        )
        
        response.raise_for_status()
        result = response.json()
        content = result['choices'][0]['message']['content']
        
        # Parse JSON
        data = json.loads(content)
        return data
        
    except Exception as e:
        print(f"    Groq error: {e}")
        return None


def test_analyzer():
    """Test the analyzer on one Physics paper."""
    print("="*70)
    print("PHYSICS QP/MS ANALYZER TEST")
    print("="*70)
    
    # Test on 2018 Jan Paper 1
    qp_path = Path("data/raw/IGCSE/Physics/2018/Jan/Paper 1.pdf")
    ms_path = Path("data/raw/IGCSE/Physics/2018/Jan/Paper 1_MS.pdf")
    
    if not qp_path.exists():
        print(f"ERROR: QP not found: {qp_path}")
        return
    
    if not ms_path.exists():
        print(f"ERROR: MS not found: {ms_path}")
        return
    
    print(f"\nTesting on: 2018 Jan Paper 1")
    print(f"QP: {qp_path}")
    print(f"MS: {ms_path}\n")
    
    result = analyze_paper_with_llm(qp_path, ms_path, 2018, "Jan", "1P")
    
    if result:
        print("\n" + "="*70)
        print("ANALYSIS RESULT")
        print("="*70)
        print(json.dumps(result, indent=2))
        
        # Validate
        if "questions" in result:
            print(f"\n✅ Found {len(result['questions'])} questions")
            
            for q in result['questions']:
                qnum = q['qnum']
                qp_pages = q['qp_pages']
                ms_pages = q['ms_pages']
                evidence = q.get('evidence', [])
                
                print(f"\nQuestion {qnum}:")
                print(f"  QP pages: {qp_pages} ({len(qp_pages)} pages)")
                print(f"  MS pages: {ms_pages} ({len(ms_pages)} pages)")
                print(f"  Evidence: {evidence[:2] if len(evidence) > 2 else evidence}")
        else:
            print("\n❌ No questions found in result")
    else:
        print("\n❌ Analysis failed")


if __name__ == "__main__":
    test_analyzer()
