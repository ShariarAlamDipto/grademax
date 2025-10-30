#!/usr/bin/env python3
import sys
sys.path.insert(0, 'scripts')
from reprocess_all_papers import QuestionDetector
import fitz

doc = fitz.open('data/raw/IGCSE/Further Pure Maths/2011/May-Jun/Paper 1.pdf')
detector = QuestionDetector()

for i in range(2, 15):
    result = detector.detect_question_start(doc[i].get_text())
    print(f'Page {i+1}: detected Q{result if result else "None"}')
