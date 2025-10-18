"""
Test the enhanced classifier with both Physics and Further Pure configs
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).parent))

from symbol_aware_classifier import SymbolAwareClassifier

load_dotenv('.env.ingest')


def test_physics_classifier():
    """Test with Physics config (simple)"""
    print(f"\n{'='*70}")
    print(f"🧪 Testing Physics Classifier (Simple Mode)")
    print(f"{'='*70}")
    
    config_path = 'config/physics_topics.yaml'
    api_key = os.getenv('GEMINI_API_KEY')
    
    if not Path(config_path).exists():
        print(f"❌ Config not found: {config_path}")
        return
    
    classifier = SymbolAwareClassifier(config_path, api_key)
    
    print(f"✅ Classifier loaded")
    print(f"   Symbol-aware mode: {classifier.is_symbol_aware}")
    print(f"   LLM available: {classifier.llm_available}")
    
    # Test sample
    test_text = """
    1. A ball is thrown vertically upward with an initial velocity of 20 m/s.
    Calculate the maximum height reached by the ball.
    Use g = 9.8 m/s²
    
    (a) Show that the time to reach maximum height is 2.04 seconds
    (b) Calculate the maximum height
    """
    
    print(f"\n📝 Test question:")
    print(f"{test_text[:200]}...")
    
    result = classifier.classify(test_text)
    
    print(f"\n📊 Classification result:")
    print(f"   Topic: {result.topic}")
    print(f"   Confidence: {result.confidence:.2f}")
    print(f"   Difficulty: {result.difficulty}")
    print(f"   Multi-topics: {result.topics if result.topics else 'N/A'}")
    
    return result


def test_further_pure_classifier():
    """Test with Further Pure config (symbol-aware)"""
    print(f"\n{'='*70}")
    print(f"🧪 Testing Further Pure Classifier (Symbol-Aware Mode)")
    print(f"{'='*70}")
    
    config_path = 'config/further_pure_topics.yaml'
    api_key = os.getenv('GEMINI_API_KEY')
    
    if not Path(config_path).exists():
        print(f"❌ Config not found: {config_path}")
        return
    
    classifier = SymbolAwareClassifier(config_path, api_key)
    
    print(f"✅ Classifier loaded")
    print(f"   Symbol-aware mode: {classifier.is_symbol_aware}")
    print(f"   LLM available: {classifier.llm_available}")
    print(f"   Symbol patterns loaded: {len(classifier.symbol_patterns)}")
    
    # Test sample with calculus symbols
    test_text = """
    5. Given that f(x) = x³ + 2x² - 5x + 3
    
    (a) Find f'(x)
    (b) Hence find the equation of the tangent to the curve y = f(x) at the point where x = 2
    (c) Find ∫f(x)dx
    """
    
    print(f"\n📝 Test question:")
    print(f"{test_text}")
    
    result = classifier.classify(test_text)
    
    print(f"\n📊 Classification result:")
    print(f"   Primary topic: {result.topic}")
    print(f"   Confidence: {result.confidence:.2f}")
    print(f"   Difficulty: {result.difficulty}")
    
    if result.topics:
        print(f"   All topics:")
        for topic in result.topics:
            print(f"      - {topic['id']} (code: {topic['code']}): {topic['confidence']:.2f}")
            if 'evidence' in topic and topic['evidence']:
                print(f"        Evidence: {', '.join(topic['evidence'])}")
    
    if result.methods:
        print(f"   Methods detected: {', '.join(result.methods)}")
    
    if result.dominant_ao:
        print(f"   Assessment objective: {result.dominant_ao}")
    
    return result


def test_further_pure_binomial():
    """Test with binomial question"""
    print(f"\n{'='*70}")
    print(f"🧪 Testing Binomial Classification")
    print(f"{'='*70}")
    
    config_path = 'config/further_pure_topics.yaml'
    api_key = os.getenv('GEMINI_API_KEY')
    
    classifier = SymbolAwareClassifier(config_path, api_key)
    
    test_text = """
    3. Expand (1 + 2x)⁵ in ascending powers of x up to and including the term in x³.
    
    Hence, find the coefficient of x³ in the expansion of (2 - x)(1 + 2x)⁵
    
    Give your answer in the form a + bx + cx² + dx³ where a, b, c, d are constants to be found.
    """
    
    print(f"\n📝 Test question:")
    print(f"{test_text}")
    
    result = classifier.classify(test_text)
    
    print(f"\n📊 Classification result:")
    print(f"   Primary topic: {result.topic} (should be 6 - Binomial)")
    print(f"   Confidence: {result.confidence:.2f}")
    
    if result.topics:
        for topic in result.topics:
            print(f"      - {topic['id']}: {topic['confidence']:.2f} - {topic.get('evidence', [])}")
    
    return result


def main():
    """Run all tests"""
    
    print(f"\n{'='*70}")
    print(f"🧪 CLASSIFIER TEST SUITE")
    print(f"{'='*70}")
    
    # Test 1: Physics (simple mode)
    try:
        test_physics_classifier()
        print(f"\n✅ Physics classifier test PASSED")
    except Exception as e:
        print(f"\n❌ Physics classifier test FAILED: {e}")
        import traceback
        traceback.print_exc()
    
    # Test 2: Further Pure calculus (symbol-aware mode)
    try:
        test_further_pure_classifier()
        print(f"\n✅ Further Pure (Calculus) classifier test PASSED")
    except Exception as e:
        print(f"\n❌ Further Pure classifier test FAILED: {e}")
        import traceback
        traceback.print_exc()
    
    # Test 3: Further Pure binomial (symbol-aware mode)
    try:
        test_further_pure_binomial()
        print(f"\n✅ Further Pure (Binomial) classifier test PASSED")
    except Exception as e:
        print(f"\n❌ Further Pure classifier test FAILED: {e}")
        import traceback
        traceback.print_exc()
    
    print(f"\n{'='*70}")
    print(f"✅ ALL TESTS COMPLETED")
    print(f"{'='*70}")


if __name__ == '__main__':
    main()
