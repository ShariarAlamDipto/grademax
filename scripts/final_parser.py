"""
FINAL PRODUCTION PARSER - Simple and Robust
"""
import re
import PyPDF2
from typing import List, Dict

def extract_questions(pdf_path: str) -> List[Dict]:
    """
    Simple, robust question extraction
    Returns: List of {question_number, start_page, end_page}
    """
    questions = []
    current_q = None
    
    with open(pdf_path, 'rb') as f:
        reader = PyPDF2.PdfReader(f)
        
        for page_num in range(len(reader.pages)):
            text = reader.pages[page_num].extract_text()
            lines = [l.strip() for l in text.split('\n') if l.strip()]
            
            # Skip continuation pages
            first_300 = text[:300].lower()
            if "continued" in first_300:
                if current_q:
                    current_q["end_page"] = page_num
                continue
            
            # Skip formula sheets and instruction pages
            if any(kw in text[:400] for kw in ["Formulae sheet", "Formula sheet", "International GCSE in"]):
                continue
            
            # Look for standalone question number
            # Skip first 3 lines (page number, code, etc.)
            search_lines = lines[3:15]
            found_new_q = False
            for i, line in enumerate(search_lines):
                # Standalone number between 1-20
                if re.match(r'^\d{1,2}$', line):
                    try:
                        q_num = int(line)
                        if not (1 <= q_num <= 20):
                            continue
                        
                        # Check next line has content OR check if there are multiple lines after
                        # (Questions with diagrams may have single letters like "O", "A" as diagram labels)
                        has_content = False
                        if i+1 < len(search_lines):
                            next_line = search_lines[i+1]
                            # Accept if next line has real content (> 3 chars)
                            if len(next_line) > 3:
                                has_content = True
                            # OR if there are several more lines (diagram questions)
                            elif i+3 < len(search_lines):
                                has_content = True
                        
                        if has_content:
                                # Save previous question
                                if current_q:
                                    questions.append(current_q)
                                    print(f"  Q{current_q['question_number']}: Pages {current_q['start_page']}-{current_q['end_page']}")
                                
                                # Start new question
                                current_q = {
                                    "question_number": str(q_num),
                                    "start_page": page_num,
                                    "end_page": page_num
                                }
                                found_new_q = True
                                break
                    except:
                        pass
            
            # Update end page if question continues (and no new question found)
            if current_q and not found_new_q:
                current_q["end_page"] = page_num
        
        # Save last question
        if current_q:
            questions.append(current_q)
            print(f"  Q{current_q['question_number']}: Pages {current_q['start_page']}-{current_q['end_page']}")
    
    return questions

if __name__ == "__main__":
    print("🔍 Extracting questions from Further Pure Maths 2012 Jan Paper 1\n")
    questions = extract_questions("data/raw/IGCSE/Further Pure Maths/2012/Jan/Paper 1.pdf")
    
    print(f"\n📊 Total: {len(questions)} questions")
    
    # Validate
    expected = list(range(1, len(questions) + 1))
    actual = [int(q["question_number"]) for q in questions]
    
    if actual == expected:
        print("✅ All questions found in order!")
    else:
        print(f"⚠️ Expected Q1-Q{len(expected)}, found: {actual}")
