"""
Physics Paper Segmentation Rule Generator

This script uses LLM to analyze sample papers and generate segmentation rules
that can be used offline to process all papers without needing LLM calls.

Process:
1. Extract OCR layout from 3-5 sample papers (different years)
2. LLM analyzes patterns and generates deterministic rules
3. Save rules to a JSON file
4. Offline processor uses rules to segment all papers
"""

import os
import sys
import json
from pathlib import Path
from dotenv import load_dotenv
import pdfplumber
import requests

# Load environment
env_path = Path(__file__).parent.parent / '.env.local'
load_dotenv(env_path)

GROQ_API_KEY = os.getenv('GROQ_API_KEY')
RULES_OUTPUT_PATH = Path(__file__).parent.parent / "config" / "physics_segmentation_rules.json"


def extract_layout_sample(pdf_path, paper_type="qp", max_pages=5):
    """
    Extract layout information from first few pages as a sample.
    """
    layout_info = {
        "paper_type": paper_type,
        "total_pages": 0,
        "sample_pages": []
    }
    
    try:
        with pdfplumber.open(pdf_path) as pdf:
            layout_info["total_pages"] = len(pdf.pages)
            pages_to_sample = min(max_pages, len(pdf.pages))
            
            for page_num in range(pages_to_sample):
                page = pdf.pages[page_num]
                
                # Extract text with positions
                words = page.extract_words(
                    x_tolerance=3,
                    y_tolerance=3,
                    keep_blank_chars=False
                )
                
                # Group words into lines
                lines = {}
                for word in words:
                    y_pos = round(word['top'], 1)
                    if y_pos not in lines:
                        lines[y_pos] = []
                    lines[y_pos].append(word)
                
                # Sort and analyze lines
                page_data = {
                    "page_index": page_num,
                    "lines": []
                }
                
                sorted_lines = sorted(lines.items())
                
                for y_pos, line_words in sorted_lines:
                    line_text = " ".join([w['text'] for w in line_words])
                    
                    # Calculate metrics
                    min_x = min([w['x0'] for w in line_words])
                    max_x = max([w['x1'] for w in line_words])
                    avg_height = sum([w['bottom'] - w['top'] for w in line_words]) / len(line_words)
                    
                    # Detect patterns
                    is_question_num = False
                    is_total = False
                    
                    first_word = line_text.strip().split()[0] if line_text.strip() else ""
                    if first_word and len(line_text) < 100:
                        if first_word[0].isdigit() or first_word.rstrip('.').rstrip(')').isdigit():
                            is_question_num = True
                    
                    if "Total for Question" in line_text or "Total for question" in line_text:
                        is_total = True
                    
                    # Only include significant lines (question markers, totals, or large text)
                    if is_question_num or is_total or avg_height > 11 or "Question" in line_text or "marks" in line_text:
                        page_data["lines"].append({
                            "text": line_text[:100],  # Truncate long lines
                            "x_pos": round(min_x, 1),
                            "y_pos": round(y_pos, 1),
                            "height": round(avg_height, 1),
                            "is_question_num": is_question_num,
                            "is_total": is_total
                        })
                
                layout_info["sample_pages"].append(page_data)
                
    except Exception as e:
        print(f"Error extracting layout: {e}")
    
    return layout_info


def generate_segmentation_rules_with_llm(sample_papers):
    """
    Use LLM to analyze sample papers and generate deterministic segmentation rules.
    """
    
    system_prompt = """You are an expert at analyzing exam paper structure to create deterministic segmentation rules.

Your task: Analyze the provided sample papers and generate **explicit, code-ready rules** that a program can use to segment papers WITHOUT needing an LLM.

## What You're Given

Multiple sample papers (different years) with OCR layout data:
- Line text content
- Position (x, y coordinates)
- Text height (font size indicator)
- Detected patterns (is_question_num, is_total)

## Your Job

Analyze the samples and create **deterministic rules** that answer:

1. **Question Start Detection:**
   - What pattern marks the beginning of a new question?
   - Text pattern? (e.g., starts with "\\d+\\s" regex)
   - Position pattern? (e.g., x_pos < 100, height > 12)
   - Context pattern? (e.g., after blank line, before answer space)

2. **Question End Detection:**
   - What pattern marks the end of a question?
   - Text pattern? (e.g., "Total for Question \\d+ = \\d+ marks")
   - Position pattern?
   - Page boundary rules? (e.g., question can span pages)

3. **Sub-question Detection:**
   - How to identify sub-questions (a, b, c, i, ii)?
   - Indentation rules? (x_pos > main_question_x + offset)
   - Numbering patterns?

4. **Mark Scheme Linking:**
   - MS table structure? (columns: Question | Answer | Marks)
   - Question number detection in MS?
   - MS section end markers? (e.g., "Total for question N")

5. **Edge Cases:**
   - Questions spanning multiple pages
   - Shared MS pages for multiple questions
   - Diagrams/images in questions

## Output Format

Return a JSON object with EXPLICIT rules a program can execute:

```json
{
  "version": "1.0",
  "board": "Pearson Edexcel IGCSE Physics",
  "confidence": "high/medium/low",
  
  "qp_rules": {
    "question_start": {
      "method": "regex|position|combined",
      "text_pattern": "regex pattern",
      "position_rules": {
        "x_min": 50,
        "x_max": 150,
        "height_min": 10
      },
      "context_required": ["previous_line_blank", "etc"],
      "explanation": "why this works"
    },
    "question_end": {
      "method": "text_marker",
      "pattern": "Total for Question (\\d+) = (\\d+) marks",
      "fallback": "next question start",
      "explanation": "why this works"
    },
    "sub_question_detection": {
      "patterns": ["(a)", "(b)", "(i)", "etc"],
      "indent_offset": 30,
      "explanation": "how to detect"
    },
    "page_spanning": {
      "allowed": true,
      "detection": "continue until end marker found"
    }
  },
  
  "ms_rules": {
    "structure": "table|sequential|mixed",
    "question_detection": {
      "pattern": "Question \\d+",
      "column_position": "left"
    },
    "section_end": {
      "pattern": "Total for question \\d+: \\d+ marks"
    },
    "table_columns": ["Question number", "Answer", "Notes", "Marks"]
  },
  
  "linking_rules": {
    "method": "question_number_match",
    "ms_per_question": "variable",
    "shared_pages": true
  },
  
  "validation_notes": [
    "Rule tested on papers from 2011-2024",
    "Works for Paper 1 and Paper 2",
    "Known limitation: very old format (pre-2011) may differ"
  ]
}
```

**Critical:** Rules must be DETERMINISTIC (no ambiguity). A programmer should be able to implement these in any language without needing ML/LLM.
"""

    user_message = {
        "task": "Analyze these Physics IGCSE sample papers and generate deterministic segmentation rules",
        "samples": sample_papers,
        "requirement": "Rules must be executable by a simple Python script without LLM"
    }
    
    try:
        print("  [LLM] Analyzing samples to generate rules...")
        response = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {GROQ_API_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "model": "llama-3.1-8b-instant",  # Smaller, faster model
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": json.dumps(user_message, indent=2)}
                ],
                "temperature": 0.1,
                "max_tokens": 3000,
                "response_format": {"type": "json_object"}
            },
            timeout=90
        )
        
        if response.status_code == 200:
            result = response.json()
            content = result['choices'][0]['message']['content']
            return json.loads(content)
        else:
            print(f"  ❌ Groq API error: {response.status_code}")
            print(f"     {response.text}")
            return None
            
    except Exception as e:
        print(f"  ❌ Error: {e}")
        return None


def main():
    """
    Main function: Collect samples and generate rules.
    """
    print("="*80)
    print("PHYSICS SEGMENTATION RULE GENERATOR")
    print("="*80)
    print("\nThis tool analyzes sample papers to generate segmentation rules")
    print("that can be used offline without LLM calls.\n")
    
    # Sample papers from different years for comprehensive rule generation
    # Using just 1 paper with 2 pages to minimize token usage
    sample_papers_list = [
        {
            "year": 2018,
            "season": "Jan",
            "paper": 1,
            "qp": r"data\raw\IGCSE\Physics\2018\Jan\Paper 1.pdf",
            "ms": r"data\raw\IGCSE\Physics\2018\Jan\Paper 1_MS.pdf"
        }
    ]
    
    samples_data = []
    
    for i, paper in enumerate(sample_papers_list, 1):
        print(f"[{i}/{len(sample_papers_list)}] Extracting layout from {paper['year']} {paper['season']} Paper {paper['paper']}...")
        
        if not Path(paper['qp']).exists():
            print(f"  ⚠️  QP not found: {paper['qp']}")
            continue
        
        if not Path(paper['ms']).exists():
            print(f"  ⚠️  MS not found: {paper['ms']}")
            continue
        
        # Extract layout from first 2 pages only (minimal sample)
        qp_layout = extract_layout_sample(paper['qp'], "qp", max_pages=2)
        ms_layout = extract_layout_sample(paper['ms'], "ms", max_pages=2)
        
        samples_data.append({
            "metadata": {
                "year": paper['year'],
                "season": paper['season'],
                "paper": paper['paper']
            },
            "qp_layout": qp_layout,
            "ms_layout": ms_layout
        })
        
        print(f"  ✅ Extracted: QP {qp_layout['total_pages']} pages, MS {ms_layout['total_pages']} pages")
    
    if not samples_data:
        print("\n❌ No sample papers found!")
        return
    
    print(f"\n✅ Collected {len(samples_data)} sample papers")
    print("\nGenerating segmentation rules with LLM...")
    
    rules = generate_segmentation_rules_with_llm(samples_data)
    
    if rules:
        # Save rules to file
        RULES_OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
        
        with open(RULES_OUTPUT_PATH, 'w', encoding='utf-8') as f:
            json.dump(rules, f, indent=2, ensure_ascii=False)
        
        print(f"\n✅ Rules generated and saved to: {RULES_OUTPUT_PATH}")
        print(f"\nRule Summary:")
        print(f"  Version: {rules.get('version', 'N/A')}")
        print(f"  Confidence: {rules.get('confidence', 'N/A')}")
        print(f"  QP Method: {rules.get('qp_rules', {}).get('question_start', {}).get('method', 'N/A')}")
        print(f"  MS Structure: {rules.get('ms_rules', {}).get('structure', 'N/A')}")
        
        if 'validation_notes' in rules:
            print(f"\n  Validation Notes:")
            for note in rules['validation_notes']:
                print(f"    - {note}")
        
        print(f"\n📝 Next step: Use 'process_physics_offline.py' to process all papers using these rules")
        
    else:
        print("\n❌ Failed to generate rules")


if __name__ == "__main__":
    main()
