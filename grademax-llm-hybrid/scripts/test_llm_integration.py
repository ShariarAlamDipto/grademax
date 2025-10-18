#!/usr/bin/env python3
"""
LM Studio Integration Test Suite
Validates offline inference, caching, and model routing
"""

import sys
import time
from pathlib import Path
from typing import List, Tuple

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from lmstudio_client import get_client
from integrate_llm import get_llm


class TestResults:
    """Track test results"""
    
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.tests: List[Tuple[str, bool, str]] = []
    
    def add(self, name: str, passed: bool, message: str = ""):
        """Add test result"""
        self.tests.append((name, passed, message))
        if passed:
            self.passed += 1
        else:
            self.failed += 1
    
    def print_summary(self):
        """Print test summary"""
        print("\n" + "="*70)
        print("📊 TEST SUMMARY")
        print("="*70)
        for name, passed, message in self.tests:
            status = "✅ PASS" if passed else "❌ FAIL"
            print(f"{status}: {name}")
            if message:
                print(f"         {message}")
        
        print(f"\nTotal: {self.passed + self.failed} tests")
        print(f"✅ Passed: {self.passed}")
        print(f"❌ Failed: {self.failed}")
        print("="*70)


def test_lmstudio_connection(results: TestResults):
    """Test 1: LM Studio connectivity"""
    print("\n🔌 Test 1: LM Studio Connection")
    try:
        client = get_client()
        # If we get here, connection succeeded in __init__
        results.add("LM Studio Connection", True, "Connected successfully")
    except Exception as e:
        results.add("LM Studio Connection", False, str(e))


def test_classification(results: TestResults):
    """Test 2: Question classification"""
    print("\n🏷️  Test 2: Question Classification")
    try:
        llm = get_llm()
        
        test_question = """
        A car accelerates uniformly from rest to a velocity of 20 m/s in 5 seconds.
        Calculate:
        (a) the acceleration of the car
        (b) the distance traveled during this time
        """
        
        start_time = time.time()
        result = llm.classify_question(
            question_text=test_question,
            subject="Physics"
        )
        elapsed = time.time() - start_time
        
        # Validate response structure
        has_topics = 'topics' in result
        has_difficulty = 'difficulty' in result
        
        if has_topics and has_difficulty:
            results.add(
                "Classification",
                True,
                f"Topics: {result['topics']}, Difficulty: {result['difficulty']}, Time: {elapsed:.2f}s"
            )
        else:
            results.add("Classification", False, "Invalid response structure")
            
    except Exception as e:
        results.add("Classification", False, str(e))


def test_math_routing(results: TestResults):
    """Test 3: Math subject routing"""
    print("\n🧮 Test 3: Math Subject Routing")
    try:
        client = get_client()
        
        # Test math subject detection
        math_model = client.detect_model_for_subject("Pure Mathematics")
        physics_model = client.detect_model_for_subject("Physics")
        
        is_correct = (
            math_model == client.models['math_reasoner'] and
            physics_model == client.models['classifier']
        )
        
        if is_correct:
            results.add(
                "Math Routing",
                True,
                f"Math: {math_model}, Physics: {physics_model}"
            )
        else:
            results.add("Math Routing", False, "Incorrect model selection")
            
    except Exception as e:
        results.add("Math Routing", False, str(e))


def test_embedding_generation(results: TestResults):
    """Test 4: Embedding generation"""
    print("\n🔢 Test 4: Embedding Generation")
    try:
        llm = get_llm()
        
        test_text = "A particle moves with constant acceleration."
        
        start_time = time.time()
        embedding = llm.generate_embedding(test_text)
        elapsed = time.time() - start_time
        
        # Validate embedding
        is_valid = (
            isinstance(embedding, list) and
            len(embedding) > 0 and
            all(isinstance(x, (int, float)) for x in embedding)
        )
        
        if is_valid:
            results.add(
                "Embedding Generation",
                True,
                f"Dimension: {len(embedding)}, Time: {elapsed:.2f}s"
            )
        else:
            results.add("Embedding Generation", False, "Invalid embedding format")
            
    except Exception as e:
        results.add("Embedding Generation", False, str(e))


def test_caching(results: TestResults):
    """Test 5: Response caching"""
    print("\n💾 Test 5: Response Caching")
    try:
        llm = get_llm()
        
        test_question = "What is Newton's first law of motion?"
        
        # First call (should be slow)
        start_time = time.time()
        result1 = llm.classify_question(test_question, "Physics")
        time1 = time.time() - start_time
        
        # Second call (should be fast - cached)
        start_time = time.time()
        result2 = llm.classify_question(test_question, "Physics")
        time2 = time.time() - start_time
        
        # Cache should be significantly faster
        is_cached = time2 < time1 * 0.5  # At least 2x faster
        
        if is_cached:
            results.add(
                "Caching",
                True,
                f"First: {time1:.2f}s, Cached: {time2:.2f}s (speedup: {time1/time2:.1f}x)"
            )
        else:
            results.add("Caching", False, f"No speedup detected: {time1:.2f}s vs {time2:.2f}s")
            
    except Exception as e:
        results.add("Caching", False, str(e))


def test_gemini_removed(results: TestResults):
    """Test 6: Gemini removal"""
    print("\n🚫 Test 6: Gemini Removal")
    try:
        import os
        
        # Check environment
        has_gemini_key = 'GEMINI_API_KEY' in os.environ
        
        if has_gemini_key:
            results.add("Gemini Removal", False, "GEMINI_API_KEY still in environment")
        else:
            results.add("Gemini Removal", True, "No Gemini keys found")
            
    except Exception as e:
        results.add("Gemini Removal", False, str(e))


def test_topic_extraction(results: TestResults):
    """Test 7: Topic extraction"""
    print("\n🎯 Test 7: Topic Extraction")
    try:
        llm = get_llm()
        
        test_question = """
        A sample of radioactive material has a half-life of 5 years.
        If the initial activity is 800 Bq, calculate the activity after 15 years.
        """
        
        topics = llm.extract_topics_from_question(
            question_text=test_question,
            subject="Physics"
        )
        
        if topics and len(topics) > 0:
            results.add(
                "Topic Extraction",
                True,
                f"Extracted topics: {topics}"
            )
        else:
            results.add("Topic Extraction", False, "No topics extracted")
            
    except Exception as e:
        results.add("Topic Extraction", False, str(e))


def test_batch_embeddings(results: TestResults):
    """Test 8: Batch embedding generation"""
    print("\n📦 Test 8: Batch Embeddings")
    try:
        llm = get_llm()
        
        test_texts = [
            "Force equals mass times acceleration.",
            "Energy is conserved in an isolated system.",
            "The speed of light is constant in vacuum."
        ]
        
        start_time = time.time()
        embeddings = llm.generate_embeddings(test_texts)
        elapsed = time.time() - start_time
        
        is_valid = (
            len(embeddings) == len(test_texts) and
            all(isinstance(e, list) for e in embeddings)
        )
        
        if is_valid:
            results.add(
                "Batch Embeddings",
                True,
                f"Generated {len(embeddings)} embeddings in {elapsed:.2f}s"
            )
        else:
            results.add("Batch Embeddings", False, "Invalid batch result")
            
    except Exception as e:
        results.add("Batch Embeddings", False, str(e))


def run_performance_benchmark(results: TestResults):
    """Benchmark: Performance test"""
    print("\n⚡ Benchmark: Performance")
    try:
        llm = get_llm()
        
        test_questions = [
            "Calculate the kinetic energy of a 2 kg mass moving at 10 m/s.",
            "A spring with constant k = 100 N/m is compressed by 0.5 m. Find the elastic potential energy.",
            "A wave has frequency 50 Hz and wavelength 2 m. Calculate its speed."
        ]
        
        times = []
        for q in test_questions:
            start = time.time()
            llm.classify_question(q, "Physics")
            times.append(time.time() - start)
        
        avg_time = sum(times) / len(times)
        
        results.add(
            "Performance Benchmark",
            True,
            f"Average inference time: {avg_time:.2f}s per question"
        )
        
    except Exception as e:
        results.add("Performance Benchmark", False, str(e))


def main():
    """Run all tests"""
    print("="*70)
    print("🧪 LM STUDIO INTEGRATION TEST SUITE")
    print("="*70)
    print("\nTesting offline LLM integration...")
    print("Make sure LM Studio is running at http://127.0.0.1:1234")
    
    results = TestResults()
    
    # Run tests
    test_lmstudio_connection(results)
    test_classification(results)
    test_math_routing(results)
    test_embedding_generation(results)
    test_caching(results)
    test_gemini_removed(results)
    test_topic_extraction(results)
    test_batch_embeddings(results)
    run_performance_benchmark(results)
    
    # Print summary
    results.print_summary()
    
    # Exit code
    sys.exit(0 if results.failed == 0 else 1)


if __name__ == "__main__":
    main()
