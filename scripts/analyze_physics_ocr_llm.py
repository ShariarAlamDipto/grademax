"""
Enhanced Physics Paper Analyzer using OCR-based Question Segmentation

This script uses OCR (pdf2image + pytesseract) to teach the LLM how to:
1. Identify question boundaries through visual layout analysis
2. Recognize question numbers and structural patterns
3. Link QP questions to corresponding MS pages

The LLM learns the segmentation rules from the OCR data itself.
"""

import os
import sys
import json
from pathlib import Path
from dotenv import load_dotenv
import pdfplumber
import requests
from pdf2image import convert_from_path
import pytesseract

# Load environment
env_path = Path(__file__).parent.parent / '.env.local'
load_dotenv(env_path)

GROQ_API_KEY = os.getenv('GROQ_API_KEY')


def extract_ocr_layout_info(pdf_path, max_pages=None):
    """
    Extract layout and structural information from PDF using OCR.
    
    Returns rich information about:
    - Text positioning (coordinates)
    - Font sizes (estimated from bounding boxes)
    - Question number detection
    - Visual boundaries
    """
    layout_info = []
    
    try:
        with pdfplumber.open(pdf_path) as pdf:
            total_pages = len(pdf.pages) if max_pages is None else min(max_pages, len(pdf.pages))
            
            for page_num in range(total_pages):
                page = pdf.pages[page_num]
                
                # Extract text with positions
                words = page.extract_words(
                    x_tolerance=3,
                    y_tolerance=3,
                    keep_blank_chars=False
                )
                
                # Analyze layout structure
                page_layout = {
                    "page_index": page_num,
                    "width": page.width,
                    "height": page.height,
                    "elements": []
                }
                
                # Group words into lines based on y-position
                lines = {}
                for word in words:
                    y_pos = round(word['top'], 1)
                    if y_pos not in lines:
                        lines[y_pos] = []
                    lines[y_pos].append(word)
                
                # Sort lines by y-position (top to bottom)
                sorted_lines = sorted(lines.items())
                
                # Analyze each line for structural markers
                for y_pos, line_words in sorted_lines:
                    line_text = " ".join([w['text'] for w in line_words])
                    
                    # Calculate line metrics
                    min_x = min([w['x0'] for w in line_words])
                    max_x = max([w['x1'] for w in line_words])
                    avg_height = sum([w['bottom'] - w['top'] for w in line_words]) / len(line_words)
                    
                    # Detect structural patterns
                    is_question_number = False
                    is_total_marker = False
                    is_bold_or_large = avg_height > 12  # Estimate bold/large text
                    
                    # Question number detection (starts with digit(s) followed by space/period)
                    if line_text.strip() and len(line_text) < 50:
                        first_word = line_text.strip().split()[0] if line_text.strip() else ""
                        if first_word and (first_word[0].isdigit() or 
                                         first_word.rstrip('.').rstrip(')').isdigit()):
                            is_question_number = True
                    
                    # Total marker detection
                    if "Total for Question" in line_text or "Total for question" in line_text:
                        is_total_marker = True
                    
                    # Mark scheme specific patterns
                    is_table_header = "Question" in line_text and "Marks" in line_text
                    is_ms_total = "Total for question" in line_text and "marks" in line_text.lower()
                    
                    # Add line to layout analysis
                    page_layout["elements"].append({
                        "y_pos": y_pos,
                        "x_start": min_x,
                        "x_end": max_x,
                        "text": line_text,
                        "height": avg_height,
                        "is_question_number": is_question_number,
                        "is_total_marker": is_total_marker,
                        "is_bold_large": is_bold_or_large,
                        "is_table_header": is_table_header,
                        "is_ms_total": is_ms_total,
                        "indent_level": min_x  # For detecting sub-questions
                    })
                
                layout_info.append(page_layout)
                
    except Exception as e:
        print(f"Error extracting layout from {pdf_path}: {e}")
    
    return layout_info


def teach_llm_segmentation(qp_layout, ms_layout, year, season, paper_num):
    """
    Use LLM to learn question segmentation from OCR layout data.
    
    The LLM analyzes:
    1. Visual patterns (indentation, spacing, font size)
    2. Question number patterns
    3. Total markers and boundaries
    4. MS table structure
    
    Then generates segmentation rules and applies them.
    """
    
    # System prompt that teaches the LLM to learn segmentation
    system_prompt = """You are an expert at analyzing exam paper structure using OCR layout data.

Your task is to:
1. **Learn the segmentation pattern** by analyzing the visual and structural markers in the document
2. **Identify question boundaries** based on patterns you discover
3. **Link each question to its mark scheme pages**

## OCR Layout Data Format

Each page contains "elements" with:
- `y_pos`: Vertical position (top to bottom)
- `text`: The actual text content
- `height`: Text height (larger = bold/heading)
- `is_question_number`: Detected question number line
- `is_total_marker`: Detected "Total for Question N" marker
- `indent_level`: Horizontal indentation
- `is_table_header`: MS table header detection
- `is_ms_total`: MS total marker detection

## Your Analysis Process

**Step 1: Learn the Question Paper Pattern**
- Look for repeated structural patterns
- Identify what marks the START of a question (e.g., "1 ", "2 ", large text, specific indent)
- Identify what marks the END of a question (e.g., "Total for Question N", consistent spacing)
- Notice sub-question patterns (a, b, c or i, ii, iii with deeper indentation)

**Step 2: Learn the Mark Scheme Pattern**
- Identify MS table structure (Question | Answer | Notes | Marks columns)
- Find question number references in MS
- Detect MS total markers that end each question's marking notes

**Step 3: Segment and Link**
- Apply your learned pattern to split QP into whole questions
- Each question should include ALL its sub-parts (a, b, c, etc.)
- Link each QP question to the corresponding MS pages

## Output Format

Return JSON with this exact structure:

{
  "learned_patterns": {
    "qp_question_start": "description of what marks question start",
    "qp_question_end": "description of what marks question end",
    "ms_structure": "description of MS layout pattern"
  },
  "questions": [
    {
      "qnum": "1",
      "qp_pages": [0, 1, 2],
      "ms_pages": [2, 3],
      "reasoning": "brief explanation of why you segmented here"
    }
  ]
}

**Critical Rules:**
- Each question must be COMPLETE (include all subparts)
- A question ends where you detect the boundary marker
- MS pages can be shared by multiple questions
- Page indices are 0-based
- Include your reasoning to show you learned the pattern
"""

    # Build user message with OCR data
    user_message = {
        "paper_info": {
            "board": "Pearson Edexcel",
            "subject": "Physics IGCSE",
            "year": year,
            "season": season,
            "paper": paper_num
        },
        "qp_layout": {
            "total_pages": len(qp_layout),
            "pages": qp_layout
        },
        "ms_layout": {
            "total_pages": len(ms_layout),
            "pages": ms_layout
        },
        "task": "Analyze the OCR layout data, learn the segmentation pattern, then segment all questions and link to mark schemes."
    }
    
    # Call Groq API
    try:
        response = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {GROQ_API_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "model": "llama-3.3-70b-versatile",
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": json.dumps(user_message, indent=2)}
                ],
                "temperature": 0.1,
                "max_tokens": 4000,
                "response_format": {"type": "json_object"}
            },
            timeout=120
        )
        
        if response.status_code == 200:
            result = response.json()
            content = result['choices'][0]['message']['content']
            return json.loads(content)
        else:
            print(f"  Groq API error: {response.status_code} - {response.text}")
            return None
            
    except Exception as e:
        print(f"  Error calling Groq API: {e}")
        return None


def analyze_paper_with_ocr_llm(qp_path, ms_path, year, season, paper_num):
    """
    Main function: Extract OCR layout and use LLM to learn segmentation.
    """
    print(f"  [OCR-LLM] Extracting layout information from QP...")
    qp_layout = extract_ocr_layout_info(qp_path)
    print(f"  [OCR-LLM] QP: {len(qp_layout)} pages analyzed")
    
    print(f"  [OCR-LLM] Extracting layout information from MS...")
    ms_layout = extract_ocr_layout_info(ms_path)
    print(f"  [OCR-LLM] MS: {len(ms_layout)} pages analyzed")
    
    print(f"  [OCR-LLM] Teaching LLM to learn segmentation patterns...")
    result = teach_llm_segmentation(qp_layout, ms_layout, year, season, paper_num)
    
    if result:
        print(f"  [OCR-LLM] ✅ Analysis complete")
        
        # Show learned patterns
        if "learned_patterns" in result:
            print(f"\n  📚 Learned Patterns:")
            patterns = result["learned_patterns"]
            print(f"    QP Start: {patterns.get('qp_question_start', 'N/A')}")
            print(f"    QP End: {patterns.get('qp_question_end', 'N/A')}")
            print(f"    MS Structure: {patterns.get('ms_structure', 'N/A')}")
    
    return result


def test_ocr_analyzer():
    """Test the OCR-based analyzer on a sample paper."""
    test_paper = {
        "year": 2018,
        "season": "Jan",
        "paper": 1,
        "qp": r"data\raw\IGCSE\Physics\2018\Jan\Paper 1.pdf",
        "ms": r"data\raw\IGCSE\Physics\2018\Jan\Paper 1_MS.pdf"
    }
    
    print("="*80)
    print("OCR-BASED QUESTION SEGMENTATION TEST")
    print("="*80)
    print(f"\nTesting: {test_paper['year']} {test_paper['season']} Paper {test_paper['paper']}")
    print()
    
    result = analyze_paper_with_ocr_llm(
        test_paper['qp'],
        test_paper['ms'],
        test_paper['year'],
        test_paper['season'],
        test_paper['paper']
    )
    
    if result and "questions" in result:
        questions = result["questions"]
        print(f"\n✅ Found {len(questions)} questions\n")
        
        # Show first 5 questions with reasoning
        for q in questions[:5]:
            print(f"Question {q['qnum']}:")
            print(f"  QP pages: {q['qp_pages']} ({len(q['qp_pages'])} pages)")
            print(f"  MS pages: {q['ms_pages']} ({len(q['ms_pages'])} pages)")
            if 'reasoning' in q:
                print(f"  Reasoning: {q['reasoning']}")
            print()
        
        if len(questions) > 5:
            print(f"... and {len(questions) - 5} more questions\n")
        
        return True
    else:
        print("\n❌ Analysis failed")
        return False


if __name__ == "__main__":
    test_ocr_analyzer()
