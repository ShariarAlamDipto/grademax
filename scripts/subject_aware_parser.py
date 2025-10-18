"""
Subject-Aware Page Parser
Handles different question formats for different subjects
"""
import re
from typing import List, Dict, Tuple
from dataclasses import dataclass

@dataclass
class QuestionBoundary:
    """Represents a detected question boundary"""
    page_num: int
    question_num: str
    start_y: float  # Y-coordinate on page
    text_sample: str

class SubjectParser:
    """Subject-specific parsing rules"""
    
    SUBJECT_CONFIGS = {
        "Physics": {
            "question_patterns": [
                r"^\s*(\d+)\s+[A-Z]",  # "1 A force of..."
                r"^\s*Question\s+(\d+)",  # "Question 1"
                r"^\s*(\d+)\s*\.",  # "1."
            ],
            "continuation_keywords": ["continued", "Continued", "CONTINUED"],
            "end_keywords": ["Total for Question", "END OF QUESTION"],
            "gridline_detect": True,
            "min_question_gap_mm": 20  # Minimum gap between questions
        },
        "Further Pure Mathematics": {
            "question_patterns": [
                r"^\s*(\d+)\s*\.",  # "1."
                r"^\s*(\d+)\s+[A-Z(]",  # "1 Solve" or "1 ("
                r"^Question\s+(\d+)",  # "Question 1"
            ],
            "continuation_keywords": ["continued", "Continued", "CONTINUED"],
            "end_keywords": ["Total for Question", "(Total", "END OF"],
            "gridline_detect": True,
            "min_question_gap_mm": 15
        },
        "Chemistry": {
            "question_patterns": [
                r"^\s*(\d+)\s+[A-Z]",
                r"^\s*Question\s+(\d+)",
            ],
            "continuation_keywords": ["continued", "Continued"],
            "end_keywords": ["Total for Question"],
            "gridline_detect": True,
            "min_question_gap_mm": 20
        }
    }
    
    def __init__(self, subject: str):
        self.subject = subject
        self.config = self.SUBJECT_CONFIGS.get(subject, self.SUBJECT_CONFIGS["Physics"])
    
    def is_question_start(self, text: str, prev_text: str = "", full_page_text: str = "") -> Tuple[bool, str]:
        """
        Detect if text is the start of a new question
        Returns: (is_start, question_number)
        """
        text = text.strip()
        
        # CRITICAL: Skip if continuation keyword present in FULL PAGE
        for keyword in self.config["continuation_keywords"]:
            if keyword in full_page_text[:500]:  # Check first 500 chars of page
                return False, ""
        
        # Look for standalone number at start of meaningful content
        # Pattern: newlines/whitespace, then just a number, then newlines
        standalone_pattern = r'^\s*(\d{1,2})\s*$'
        match = re.match(standalone_pattern, text)
        if match:
            q_num = match.group(1)
            # Verify there's actual question content after
            if len(prev_text) > 20 or len(full_page_text) > 300:
                return True, q_num
        
        # Check other patterns (fallback)
        for pattern in self.config["question_patterns"]:
            match = re.search(pattern, text, re.MULTILINE)
            if match:
                q_num = match.group(1)
                # Verify it's not part of "Question 1 continued"
                line = text[:100]
                if not any(kw in line for kw in self.config["continuation_keywords"]):
                    return True, q_num
        
        return False, ""
    
    def is_question_end(self, text: str) -> bool:
        """Detect if text marks end of question"""
        for keyword in self.config["end_keywords"]:
            if keyword in text:
                return True
        return False
    
    def detect_gridlines(self, page) -> List[float]:
        """
        Detect horizontal gridlines that separate questions
        Returns list of Y-coordinates
        """
        if not self.config["gridline_detect"]:
            return []
        
        # This would use PDF layout analysis
        # For now, return empty (will use text-based detection)
        return []

class QuestionExtractor:
    """Extract questions using subject-aware parsing"""
    
    def __init__(self, subject: str):
        self.parser = SubjectParser(subject)
    
    def extract_questions(self, pdf_path: str) -> List[Dict]:
        """
        Extract questions from PDF using subject-specific rules
        Returns list of question metadata
        """
        import PyPDF2
        
        questions = []
        current_question = None
        
        with open(pdf_path, 'rb') as f:
            reader = PyPDF2.PdfReader(f)
            
            for page_num, page in enumerate(reader.pages):
                full_page_text = page.extract_text()
                lines = full_page_text.split('\n')
                
                # Skip page header/number (first 3-5 lines usually junk)
                # Look at lines 5-20 for question numbers
                meaningful_lines = [(i, l) for i, l in enumerate(lines) if l.strip()]
                search_lines = meaningful_lines[3:20]  # Skip first 3 lines (page number, code, etc.)
                
                for i, (line_idx, line) in enumerate(search_lines):
                    is_start, q_num = self.parser.is_question_start(
                        line, 
                        prev_text='\n'.join([l for _, l in search_lines[:i]]),
                        full_page_text=full_page_text
                    )
                    
                    if is_start:
                        # Validate: question number should be reasonable (1-20)
                        try:
                            q_int = int(q_num)
                            if q_int > 20:  # Probably a page number or something else
                                continue
                        except:
                            continue
                        
                        # Save previous question
                        if current_question:
                            questions.append(current_question)
                        
                        # Start new question
                        current_question = {
                            "question_number": q_num,
                            "start_page": page_num,
                            "end_page": page_num,
                            "text_preview": full_page_text[200:500].replace('\n', ' ')
                        }
                        print(f"  ✅ Found Q{q_num} starting at page {page_num}")
                        break
                
                # Check if question ends
                if self.parser.is_question_end(full_page_text) and current_question:
                    current_question["end_page"] = page_num
                    questions.append(current_question)
                    print(f"     Ended at page {page_num}")
                    current_question = None
                
                # If question continues, update end page
                elif current_question:
                    current_question["end_page"] = page_num
        
            # Save last question
            if current_question:
                current_question["end_page"] = len(reader.pages) - 1
                questions.append(current_question)
                print(f"     Ended at page {current_question['end_page']} (last page)")
        
        return questions
    
    def validate_extraction(self, questions: List[Dict]) -> Dict:
        """Validate extracted questions"""
        issues = []
        
        # Check for gaps
        for i in range(len(questions) - 1):
            expected_next = int(questions[i]["question_number"]) + 1
            actual_next = int(questions[i+1]["question_number"])
            if actual_next != expected_next:
                issues.append(f"Gap between Q{questions[i]['question_number']} and Q{actual_next}")
        
        # Check for single-page questions (suspicious)
        single_page = [q for q in questions if q["start_page"] == q["end_page"]]
        if len(single_page) > len(questions) * 0.8:
            issues.append("Warning: Many single-page questions detected")
        
        return {
            "total_questions": len(questions),
            "page_range": f"{questions[0]['start_page']}-{questions[-1]['end_page']}" if questions else "N/A",
            "issues": issues,
            "questions": questions
        }

# Example usage
if __name__ == "__main__":
    # Test with Further Pure Maths
    extractor = QuestionExtractor("Further Pure Mathematics")
    pdf_path = "data/raw/IGCSE/Further Pure Maths/2012/Jan/Paper 1.pdf"
    
    print("🔍 Extracting questions...")
    questions = extractor.extract_questions(pdf_path)
    
    print(f"\n📊 Found {len(questions)} questions:")
    for q in questions:
        print(f"  Q{q['question_number']}: Pages {q['start_page']}-{q['end_page']}")
        print(f"    Preview: {q['text_preview'][:80]}...")
    
    # Validate
    validation = extractor.validate_extraction(questions)
    print(f"\n✅ Validation:")
    print(f"  Total: {validation['total_questions']} questions")
    print(f"  Page range: {validation['page_range']}")
    if validation['issues']:
        print(f"  ⚠️ Issues: {', '.join(validation['issues'])}")
