#!/usr/bin/env python3
"""
Gemini LLM Classifier - GradeMax Phase 2
Uses Google Gemini API to classify question pages by topic
"""

import os
import json
import time
import re
from pathlib import Path
from typing import List, Dict, Optional
from dataclasses import dataclass
import yaml

# Gemini imports
try:
    import google.generativeai as genai
    from google.generativeai import types
    from google.generativeai.protos import Schema, Type
    GEMINI_AVAILABLE = True
except ImportError:
    print("⚠️  google-generativeai not installed. Run: pip install google-generativeai")
    GEMINI_AVAILABLE = False


@dataclass
class TopicClassification:
    """Result of classifying a page"""
    page_has_question: bool
    topic: str  # Single primary topic code (e.g., "1", "2", "3")
    difficulty: str  # "easy", "medium", "hard"
    confidence: float
    raw_response: Optional[Dict] = None


class TopicCatalogue:
    """Loads and manages the topic catalogue"""
    
    def __init__(self, catalogue_path: str):
        self.catalogue_path = Path(catalogue_path)
        self.topics = self._load_catalogue()
        self.topic_by_code = {t['code']: t for t in self.topics}
    
    def _load_catalogue(self) -> List[Dict]:
        """Load topics from YAML"""
        with open(self.catalogue_path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
        return data['topics']
    
    def get_allowed_codes(self) -> List[str]:
        """Get list of allowed topic codes"""
        return [t['code'] for t in self.topics]
    
    def get_topic_summary(self) -> str:
        """Get formatted topic list for LLM prompt"""
        lines = []
        for t in self.topics:
            lines.append(f"{t['code']}: {t['name']}")
            if t.get('keywords'):
                keywords = ', '.join(t['keywords'][:10])  # First 10 keywords
                lines.append(f"   Keywords: {keywords}")
            if t.get('formulas'):
                formulas = ', '.join(t['formulas'][:5])  # First 5 formulas
                lines.append(f"   Formulas: {formulas}")
        return '\n'.join(lines)
    
    def get_guardrail_patterns(self) -> Dict[str, List[str]]:
        """Get regex patterns for guardrail validation"""
        patterns = {}
        for t in self.topics:
            topic_code = t['code']
            topic_patterns = []
            
            # Add formulas as regex patterns
            if t.get('formulas'):
                for formula in t['formulas']:
                    # Escape special regex characters
                    pattern = re.escape(formula)
                    topic_patterns.append(pattern)
            
            # Add key keywords
            if t.get('keywords'):
                for keyword in t['keywords'][:15]:  # Top 15 keywords
                    # Word boundary matching
                    pattern = r'\b' + re.escape(keyword) + r'\b'
                    topic_patterns.append(pattern)
            
            patterns[topic_code] = topic_patterns
        
        return patterns


class RateLimiter:
    """Manages API rate limiting for Gemini free tier"""
    
    def __init__(self, requests_per_minute: int = 15, requests_per_day: int = 1000):
        self.rpm = requests_per_minute
        self.rpd = requests_per_day
        
        self.minute_window = []
        self.day_count = 0
        self.day_reset_time = time.time() + 86400  # 24 hours
    
    def wait_if_needed(self):
        """Block if rate limits would be exceeded"""
        current_time = time.time()
        
        # Reset day counter
        if current_time > self.day_reset_time:
            self.day_count = 0
            self.day_reset_time = current_time + 86400
        
        # Check daily limit
        if self.day_count >= self.rpd:
            wait_time = self.day_reset_time - current_time
            print(f"⏳ Daily quota exhausted. Waiting {wait_time/3600:.1f} hours...")
            time.sleep(wait_time)
            self.day_count = 0
            self.day_reset_time = time.time() + 86400
        
        # Clean up minute window (remove requests older than 60s)
        self.minute_window = [t for t in self.minute_window if current_time - t < 60]
        
        # Check per-minute limit
        if len(self.minute_window) >= self.rpm:
            wait_time = 60 - (current_time - self.minute_window[0])
            if wait_time > 0:
                print(f"⏳ Rate limit: waiting {wait_time:.1f}s...")
                time.sleep(wait_time)
                self.minute_window = []
        
        # Record this request
        self.minute_window.append(current_time)
        self.day_count += 1


class GeminiClassifier:
    """Uses Gemini API to classify question pages"""
    
    def __init__(
        self,
        api_key: str,
        catalogue: TopicCatalogue,
        model_name: str = "gemini-2.0-flash-lite",
        temperature: float = 0.0
    ):
        if not GEMINI_AVAILABLE:
            raise ImportError("google-generativeai package required")
        
        self.catalogue = catalogue
        self.model_name = model_name
        self.temperature = temperature
        
        # Configure Gemini
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel(model_name)
        
        # Rate limiter
        # Flash-Lite: 15 RPM, 1000 RPD
        # Flash: 10 RPM, 250 RPD
        if "lite" in model_name.lower():
            self.rate_limiter = RateLimiter(15, 1000)
        else:
            self.rate_limiter = RateLimiter(10, 250)
        
        # Build JSON schema
        self.schema = self._build_schema()
        
        # System prompt
        self.system_prompt = self._build_system_prompt()
    
    def _build_schema(self) -> Schema:
        """Build structured output schema for SINGLE topic classification"""
        allowed_topics = self.catalogue.get_allowed_codes()
        
        return Schema(
            type=Type.OBJECT,
            properties={
                'page_has_question': Schema(
                    type=Type.BOOLEAN,
                    description="True if page contains an actual question, false if instructions/data only"
                ),
                'topic': Schema(
                    type=Type.STRING,
                    description="Single PRIMARY topic code that best describes this question (e.g., '1', '2', '3')",
                    enum=allowed_topics
                ),
                'difficulty': Schema(
                    type=Type.STRING,
                    description="Question difficulty: easy, medium, or hard",
                    enum=['easy', 'medium', 'hard']
                ),
                'confidence': Schema(
                    type=Type.NUMBER,
                    description="Confidence score 0.0-1.0 for the classification"
                )
            },
            required=['page_has_question', 'topic', 'difficulty', 'confidence']
        )
    
    def _build_system_prompt(self) -> str:
        """Build the system prompt"""
        return f"""You are an expert physics teacher classifying IGCSE Physics exam questions by syllabus topics.

Your task:
1. Read the question page text carefully
2. Identify which physics topics are being tested
3. Use ONLY the allowed topic codes
4. If multiple topics appear, include them all
5. If you see subparts (a), (b), (c), etc., identify topics for each subpart
6. Assess difficulty: easy (recall/simple), medium (application), hard (multi-step/analysis)
7. Provide a confidence score (0-1) for your classification

Allowed topics:
{self.catalogue.get_topic_summary()}

Rules:
- Use ONLY the topic codes shown above (1-8)
    def _build_system_prompt(self) -> str:
        """Build the system prompt"""
        return f"""You are an expert physics teacher classifying IGCSE Physics exam questions by syllabus topics.

Your task:
- Identify the ONE PRIMARY topic that this question tests
- Choose ONLY ONE topic code - the most relevant one
- If a page has no actual question (just instructions/data), set page_has_question=false
- Match the primary concept being tested
- Assess difficulty: easy (basic recall), medium (application), hard (complex analysis)
- Provide confidence based on how clear the topic indicators are

Available topics:
{self._format_topics()}
"""
    
    def classify_page(self, page_text: str, question_number: str = None) -> TopicClassification:
        """
        Classify a single page using Gemini API
        
        Args:
            page_text: Text content of the page (first 3000 chars)
            question_number: Optional question number for context
        
        Returns:
            TopicClassification object
        """
        # Rate limiting
        self.rate_limiter.wait_if_needed()
        
        # Build user prompt
        user_parts = []
        if question_number:
            user_parts.append(f"Question number: {question_number}\n")
        user_parts.append("Page text:\n```\n")
        user_parts.append(page_text[:3000])
        user_parts.append("\n```\n\nClassify this page by topic.")
        
        try:
            # Call Gemini API
            response = self.model.generate_content(
                contents=[
                    {'role': 'user', 'parts': user_parts}
                ],
                generation_config=types.GenerationConfig(
                    temperature=self.temperature,
                    response_mime_type='application/json',
                    response_schema=self.schema
                )
            )
            
            # Parse structured response
            result = json.loads(response.text)
            
            return TopicClassification(
                page_has_question=result.get('page_has_question', True),
                topics=result.get('topics', []),
                subparts=result.get('subparts', []),
                difficulty=result.get('difficulty', 'medium'),
                confidence=result.get('confidence', 0.5),
                raw_response=result
            )
            
        except Exception as e:
            print(f"❌ Gemini API error: {e}")
            # Return fallback classification
            return TopicClassification(
                page_has_question=True,
                topics=[],
                subparts=[],
                difficulty='medium',
                confidence=0.0,
                raw_response={'error': str(e)}
            )
    
    def classify_batch(self, pages: List[Dict]) -> List[TopicClassification]:
        """Classify multiple pages (respects rate limits)"""
        results = []
        
        for i, page in enumerate(pages):
            print(f"🔍 Classifying page {i+1}/{len(pages)}: Q{page.get('question_number', '?')}")
            
            classification = self.classify_page(
                page.get('text_excerpt', page.get('text', '')),
                page.get('question_number')
            )
            
            results.append(classification)
            
            # Show result
            print(f"   Topics: {', '.join(classification.topics)}")
            print(f"   Difficulty: {classification.difficulty}")
            print(f"   Confidence: {classification.confidence:.2f}")
        
        return results


class GuardrailValidator:
    """Validates and corrects LLM classifications using regex"""
    
    def __init__(self, catalogue: TopicCatalogue):
        self.catalogue = catalogue
        self.patterns = catalogue.get_guardrail_patterns()
    
    def validate_and_correct(
        self,
        page_text: str,
        classification: TopicClassification
    ) -> TopicClassification:
        """
        Check page text for formulas/keywords and add missing topics
        """
        detected_topics = set(classification.topics)
        corrections_made = False
        
        # Check each topic's patterns
        for topic_code, patterns in self.patterns.items():
            for pattern in patterns:
                try:
                    if re.search(pattern, page_text, re.IGNORECASE):
                        if topic_code not in detected_topics:
                            detected_topics.add(topic_code)
                            corrections_made = True
                            print(f"   ✓ Guardrail added topic {topic_code}")
                        break  # One match is enough
                except re.error:
                    pass  # Skip invalid patterns
        
        # Update classification if corrections made
        if corrections_made:
            classification.topics = list(detected_topics)
            classification.confidence = min(classification.confidence + 0.1, 1.0)
        
        return classification


def test_classifier():
    """Test the classifier with sample text"""
    
    # Check API key
    api_key = os.environ.get('GEMINI_API_KEY')
    if not api_key:
        print("❌ GEMINI_API_KEY not set")
        print("Get your API key from: https://ai.google.dev/")
        return
    
    # Load catalogue
    catalogue_path = Path(__file__).parent.parent / "config" / "physics_topics.yaml"
    catalogue = TopicCatalogue(str(catalogue_path))
    
    print(f"✅ Loaded {len(catalogue.topics)} topics")
    
    # Create classifier
    classifier = GeminiClassifier(api_key, catalogue)
    
    # Test text
    sample_text = """
    1 A car accelerates from rest to 20 m/s in 4 seconds.
    
    (a) Calculate the acceleration of the car.
        Use the equation: v = u + at
    
    (b) Calculate the distance travelled during this time.
        Use the equation: s = ut + ½at²
    
    (c) Calculate the kinetic energy of the car if its mass is 1200 kg.
        Use the equation: KE = ½mv²
    """
    
    print("\n" + "="*60)
    print("Testing classification...")
    print("="*60)
    
    classification = classifier.classify_page(sample_text, "1")
    
    print(f"\n✅ Classification complete:")
    print(f"   Has question: {classification.page_has_question}")
    print(f"   Topics: {', '.join(classification.topics)}")
    print(f"   Subparts: {len(classification.subparts)}")
    print(f"   Difficulty: {classification.difficulty}")
    print(f"   Confidence: {classification.confidence:.2f}")
    
    # Test guardrails
    validator = GuardrailValidator(catalogue)
    corrected = validator.validate_and_correct(sample_text, classification)
    
    print(f"\n✅ After guardrails:")
    print(f"   Topics: {', '.join(corrected.topics)}")
    print(f"   Confidence: {corrected.confidence:.2f}")


if __name__ == "__main__":
    test_classifier()
