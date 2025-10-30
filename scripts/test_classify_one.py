#!/usr/bin/env python3
"""Test classification with full question"""

import os
import sys
sys.path.insert(0, os.path.dirname(__file__))

from dotenv import load_dotenv
from hybrid_classifier_v23 import HybridClassifierV23

load_dotenv('.env.local')

# Sample question
test_question = {
    'number': 1,
    'text': """A car accelerates from rest to a speed of 20 m/s in 5 seconds.
    
(a) Calculate the acceleration of the car.
(b) Calculate the distance travelled by the car during this time.
(c) The car then maintains a constant speed of 20 m/s for 10 seconds. Calculate the total distance travelled.""",
    'actual_question_number': 1
}

print("Testing OpenRouter Classification...")
print(f"Question length: {len(test_question['text'])} chars")
print()

# Initialize classifier
api_key = os.getenv('OPENROUTER_API_KEY')
classifier = HybridClassifierV23(api_key, use_openrouter=True)

print("\nClassifying...")
result = classifier.classify_single_groq(test_question)

if result:
    print(f"\nSUCCESS!")
    print(f"Topic: {result.topic}")
    print(f"Difficulty: {result.difficulty}")
    print(f"Confidence: {result.confidence}")
    print(f"Method: {result.method}")
else:
    print("\nFAILED - No result returned")
