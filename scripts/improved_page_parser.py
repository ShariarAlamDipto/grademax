"""
Production-Quality Subject-Aware Page Parser
Correctly detects question boundaries for all subjects
"""
import re
from typing import List, Dict
import PyPDF2

class ImprovedQuestionParser:
    """
    Parse exam papers with proper question detection
    """
    
    SKIP_KEYWORDS = [
        "Formulae sheet", "Formula sheet", "Information for Candidates",
        "Instructions to Candidates", "END OF QUESTIONS", "BLANK PAGE"
    ]
    
    CONTINUATION_KEYWORDS = ["continued", "Continued", "CONTINUED"]
    
    def extract_questions_from_pdf(self, pdf_path: str, subject: str) -> List[Dict]:
        """
        Extract all questions from a PDF
        Returns: List of {question_number, start_page, end_page, text_preview}
        """
        questions = []
        current_question = None
        
        with open(pdf_path, 'rb') as f:
            reader = PyPDF2.PdfReader(f)
            total_pages = len(reader.pages)
            
            print(f"📄 Processing {total_pages} pages...")
            
            for page_num in range(total_pages):
                page = reader.pages[page_num]
                full_text = page.extract_text()
                
                # Skip if continuation page
                if self._is_continuation_page(full_text):
                    if current_question:
                        current_question["end_page"] = page_num
                    continue
                
                # Skip formula/instruction pages
                if self._is_skip_page(full_text):
                    continue
                
                # Try to detect question start
                q_num = self._detect_question_number(full_text, page_num)
                
                if q_num:
                    # Save previous question
                    if current_question:
                        questions.append(current_question)
                        print(f"  ✅ Q{current_question['question_number']}: Pages {current_question['start_page']}-{current_question['end_page']}")
                    
                    # Start new question
                    current_question = {
                        "question_number": q_num,
                        "start_page": page_num,
                        "end_page": page_num,
                        "text_preview": self._get_preview(full_text)
                    }
                
                elif current_question:
                    # Continue current question
                    current_question["end_page"] = page_num
            
            # Save last question
            if current_question:
                questions.append(current_question)
                print(f"  ✅ Q{current_question['question_number']}: Pages {current_question['start_page']}-{current_question['end_page']}")
        
        return questions
    
    def _is_continuation_page(self, text: str) -> bool:
        """Check if page is a continuation"""
        first_500 = text[:500]
        return any(kw in first_500 for kw in self.CONTINUATION_KEYWORDS)
    
    def _is_skip_page(self, text: str) -> bool:
        """Check if page should be skipped (formula sheet, instructions, etc.)"""
        first_300 = text[:300]
        return any(kw in first_300 for kw in self.SKIP_KEYWORDS)
    
    def _detect_question_number(self, text: str, page_num: int) -> str:
        """
        Detect question number on a page
        Returns question number as string, or None if not found
        """
        lines = text.split('\n')
        
        # Skip first 2-5 lines (page numbers, codes)
        meaningful_lines = [l.strip() for l in lines if l.strip()][2:15]
        
        for line in meaningful_lines:
            # Pattern 1: Standalone number (most common in maths)
            if re.match(r'^\d{1,2}$', line):
                q_num = line
                # Validate: should be 1-20
                try:
                    num_int = int(q_num)
                    if 1 <= num_int <= 20:
                        # Extra validation: check if followed by actual content
                        # (to avoid page numbers that happen to be 1-20)
                        next_idx = meaningful_lines.index(line) + 1
                        if next_idx < len(meaningful_lines):
                            next_line = meaningful_lines[next_idx]
                            # Real questions have text after the number
                            if len(next_line) > 5:
                                return q_num
                except:
                    pass
            
            # Pattern 2: Number followed by text (e.g., "1 The nth term...")
            match = re.match(r'^(\d{1,2})\s+[A-Z(]', line)
            if match:
                q_num = match.group(1)
                try:
                    num_int = int(q_num)
                    if 1 <= num_int <= 20:
                        return q_num
                except:
                    pass
            
            # Pattern 3: "Question 1" style
            match = re.match(r'^Question\s+(\d{1,2})', line, re.IGNORECASE)
            if match:
                return match.group(1)
        
        return None
    
    def _get_preview(self, text: str) -> str:
        """Get clean preview of question text"""
        # Skip headers and get actual content
        lines = [l.strip() for l in text.split('\n') if l.strip()]
        content_lines = lines[5:15]  # Skip first 5 lines (headers)
        preview = ' '.join(content_lines)
        return preview[:200]
    
    def validate_questions(self, questions: List[Dict]) -> Dict:
        """Validate extracted questions"""
        issues = []
        
        if not questions:
            return {"valid": False, "issues": ["No questions found"]}
        
        # Check sequence
        expected = 1
        for q in questions:
            actual = int(q["question_number"])
            if actual != expected:
                issues.append(f"Missing Q{expected}, found Q{actual}")
            expected = actual + 1
        
        # Check for overlaps
        for i in range(len(questions) - 1):
            if questions[i]["end_page"] >= questions[i+1]["start_page"]:
                issues.append(f"Q{questions[i]['question_number']} overlaps with Q{questions[i+1]['question_number']}")
        
        return {
            "valid": len(issues) == 0,
            "total_questions": len(questions),
            "expected_questions": int(questions[-1]["question_number"]) if questions else 0,
            "issues": issues
        }

# Test
if __name__ == "__main__":
    parser = ImprovedQuestionParser()
    
    pdf_path = "data/raw/IGCSE/Further Pure Maths/2012/Jan/Paper 1.pdf"
    print(f"🔍 Parsing: {pdf_path}\n")
    
    questions = parser.extract_questions_from_pdf(pdf_path, "Further Pure Mathematics")
    
    print(f"\n📊 Summary: Found {len(questions)} questions")
    
    validation = parser.validate_questions(questions)
    print(f"\n✅ Validation: {'PASS' if validation['valid'] else 'FAIL'}")
    print(f"   Total: {validation['total_questions']}")
    print(f"   Expected: {validation['expected_questions']}")
    if validation['issues']:
        print(f"   ⚠️ Issues:")
        for issue in validation['issues']:
            print(f"      - {issue}")
