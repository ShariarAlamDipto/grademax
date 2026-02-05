#!/usr/bin/env python3
"""Test Maths B topic classification"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

import os
from dotenv import load_dotenv
load_dotenv('.env.local')

from mistral_classifier import MistralTopicClassifier

TOPICS_YAML = Path(__file__).parent.parent / "classification" / "maths_b_topics.yaml"

print("=" * 60)
print("Testing Maths B Topic Classification")
print("=" * 60)

# Initialize classifier
classifier = MistralTopicClassifier(
    topics_yaml_path=str(TOPICS_YAML),
    groq_api_key=os.getenv('GROQ_API_KEY'),
    model_name='llama-3.1-8b-instant'
)

print(f"\nLoaded {len(classifier.topics)} topics:")
for t in classifier.topics:
    print(f"  {t['id']}: {t['name']} ({t['code']})")

# Test a sample question
sample_question = """
(a) Find the Highest Common Factor (HCF) of 75, 90 and 120
(2)
Bhu sets the alarm on her phone to sound at 09 10
Her alarm then sounds every 12 minutes.
Dax sets the alarm on his phone to sound at 09 30
His alarm then sounds every 8 minutes.
(b) Find the first time after 09 30 that both alarms will sound at the same time.
"""

print("\n" + "=" * 60)
print("Testing sample question:")
print("=" * 60)
print(sample_question[:200] + "...")

result = classifier.classify(sample_question, "Q2")
print(f"\nResult:")
print(f"  Topic: {result.topic}")
print(f"  Difficulty: {result.difficulty}")
print(f"  Confidence: {result.confidence:.2f}")
print(f"  Has Question: {result.page_has_question}")
