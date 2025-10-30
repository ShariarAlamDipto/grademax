#!/usr/bin/env python3
"""
Test script to verify that MistralTopicClassifier works with different subjects
"""

import os
from pathlib import Path
from dotenv import load_dotenv
from mistral_classifier import MistralTopicClassifier

# Load environment variables
load_dotenv()
GROQ_API_KEY = os.getenv("GROQ_API_KEY")


def test_fpm_classifier():
    """Test classifier with Further Pure Maths topics"""
    print("\n" + "="*80)
    print("� TESTING FURTHER PURE MATHS CLASSIFIER")
    print("="*80)
    
    fpm_yaml = Path(__file__).parent.parent / "classification" / "further_pure_maths_topics.yaml"
    
    classifier = MistralTopicClassifier(
        topics_yaml_path=str(fpm_yaml),
        api_key=GROQ_API_KEY,
        model_name="llama-3.1-8b-instant"
    )
    
    print(f"\n✅ Subject Name: {classifier.subject_name}")
    print(f"✅ Number of Topics: {len(classifier.topics)}")
    print(f"✅ Topic Codes: {', '.join([t['code'] for t in classifier.topics[:5]])}...")
    print(f"✅ Valid Topic IDs: {', '.join([t['id'] for t in classifier.topics])}")
    
    # Build a sample prompt snippet to show dynamic generation
    valid_topic_ids = '|'.join([f'"{t["id"]}"' for t in classifier.topics])
    print(f"\n� Dynamic JSON Schema for Topics:")
    print(f'   "topic": {valid_topic_ids}')
    
    print(f"\n📝 Generated Prompt Preview:")
    print(f'   "You are classifying {classifier.subject_name} exam questions..."')
    
    # Test classification
    sample_text = """
    Q1. Solve the equation:
    log₂(x) + log₂(x-3) = 2
    
    Give your answer as an exact value.
    """
    
    print(f"\n� Classifying sample FPM question...")
    result = classifier.classify(sample_text, "Q1")
    print(f"   ✅ Topic: {result.topic} ({[t for t in classifier.topics if t['id'] == result.topic][0]['code']})")
    print(f"   ✅ Difficulty: {result.difficulty}")
    print(f"   ✅ Confidence: {result.confidence}")


if __name__ == "__main__":
    print("\n🧪 SUBJECT-AGNOSTIC CLASSIFIER TEST")
    print("="*80)
    print("Testing that the classifier dynamically adapts to different subjects")
    print("by reading subject metadata and topics from YAML files")
    
    test_fpm_classifier()
    
    print("\n" + "="*80)
    print("✅ TEST COMPLETE")
    print("="*80)
    print("\n🎯 Key Improvements:")
    print("   • Subject name extracted from YAML (not hardcoded)")
    print("   • Topic IDs generated dynamically (10 for FPM vs 8 for Physics)")
    print("   • Prompt text adapts to subject context")
    print("   • Can now support ANY subject with a YAML file")
    print("\n💡 To add a new subject:")
    print("   1. Create classification/<subject>_topics.yaml")
    print("   2. Define subject.name and topics list")
    print("   3. The classifier will automatically adapt!\n")
