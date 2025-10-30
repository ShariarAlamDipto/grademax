#!/usr/bin/env python3
"""
Test script to verify both Groq and OpenRouter APIs work with Physics classifier
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from scripts.mistral_classifier import MistralTopicClassifier

# Load environment variables from .env.local
load_dotenv(project_root / '.env.local')

def test_classifier():
    """Test both Groq and OpenRouter models"""
    
    print("="*60)
    print("Testing Dual API Classifier (Groq + OpenRouter)")
    print("="*60)
    
    # Get API keys
    groq_key = os.getenv('GROQ_API_KEY')
    openrouter_key = os.getenv('OPENROUTER_API_KEY')
    
    print(f"\n[API Keys]")
    print(f"  Groq: {'✅ Available' if groq_key else '❌ Missing'}")
    print(f"  OpenRouter: {'✅ Available' if openrouter_key else '❌ Missing'}")
    
    if not groq_key and not openrouter_key:
        print("\n❌ ERROR: At least one API key is required!")
        return False
    
    # Initialize classifier
    print(f"\n[Initializing Classifier]")
    try:
        classifier = MistralTopicClassifier(
            "classification/physics_topics.yaml",
            groq_key,
            openrouter_key
        )
        print(f"  ✅ Classifier initialized")
        print(f"  📊 Topics loaded: {len(classifier.topics)}")
        print(f"  🔑 Keywords: {len(classifier.keyword_map)}")
        print(f"  🤖 Available models: {len(classifier.available_models)}")
    except Exception as e:
        print(f"  ❌ Failed to initialize: {e}")
        return False
    
    # Display all models
    print(f"\n[Available Models]")
    for i, model in enumerate(classifier.available_models):
        current = "👉" if i == classifier.current_model_index else "  "
        print(f"  {current} {model['provider']:12s} | {model['name']:40s} | RPM: {model['rpm']}")
    
    # Test samples
    test_samples = [
        ("A car accelerates from rest to 30 m/s in 5 seconds. Calculate: (a) the acceleration (b) the distance travelled during acceleration. Show all your working.", "Forces & Motion"),
        ("A circuit contains a 12V battery and three resistors in series: 2Ω, 3Ω, and 4Ω. Calculate the total resistance and the current flowing through the circuit.", "Electricity"),
        ("State two differences between alpha radiation and beta radiation.", "Radioactivity"),
    ]
    
    print(f"\n[Testing Classification - {len(test_samples)} samples]")
    print("="*60)
    
    success_count = 0
    for i, (text, expected_topic_area) in enumerate(test_samples, 1):
        print(f"\n[Sample {i}/{len(test_samples)}] {expected_topic_area}")
        print(f"Text: {text[:80]}...")
        
        try:
            result = classifier.classify(text, f"Q{i}")
            
            # Find topic name
            topic_name = "Unknown"
            for topic in classifier.topics:
                if topic['id'] == result.topic:
                    topic_name = topic['name']
                    break
            
            print(f"  ✅ Result:")
            print(f"     Topic: {result.topic} - {topic_name}")
            print(f"     Difficulty: {result.difficulty}")
            print(f"     Confidence: {result.confidence:.2f}")
            print(f"     Model used: {classifier.current_provider}:{classifier.model}")
            success_count += 1
            
        except Exception as e:
            print(f"  ❌ Classification failed: {e}")
    
    # Summary
    print("\n" + "="*60)
    print(f"[Test Summary]")
    print(f"  Success: {success_count}/{len(test_samples)}")
    print(f"  Success rate: {success_count/len(test_samples)*100:.1f}%")
    print(f"  Final model: {classifier.current_provider}:{classifier.model}")
    
    if success_count == len(test_samples):
        print("\n✅ All tests passed! Ready to process Physics papers.")
        return True
    else:
        print(f"\n⚠️  Some tests failed. Check API configuration.")
        return False

if __name__ == "__main__":
    success = test_classifier()
    sys.exit(0 if success else 1)
