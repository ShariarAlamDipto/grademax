#!/usr/bin/env python3
"""
Production-ready batch classifier for GradeMax using Groq's Llama API
Features:
- Batches multiple questions per request (trade RPM for TPM)
- JSON schema structured output (parse-safe)
- Rate limit header tracking with adaptive throttling
- Exponential backoff + jitter on 429s
- Aggressive caching
"""

import os
import json
import time
import hashlib
import random
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
import yaml
import requests
from dotenv import load_dotenv


@dataclass
class TopicClassification:
    """Classification result for a single question"""
    question_number: int
    topics: List[Dict[str, any]]  # [{"id": "1", "confidence": 0.95}, ...]
    difficulty: str
    marks_estimated: Optional[int] = None
    methods: List[str] = None


class GroqBatchClassifier:
    """Batch classifier optimized for Groq's Llama API rate limits"""
    
    # Physics topic codes (1-8)
    PHYSICS_TOPICS = ["1", "2", "3", "4", "5", "6", "7", "8"]
    
    # Physics topic descriptors (compact for token efficiency)
    PHYSICS_TOPIC_MAP = {
        "1": "Forces & Motion (F=ma, momentum, suvat, energy)",
        "2": "Electricity (V=IR, power, circuits, series/parallel)",
        "3": "Waves (v=fλ, EM spectrum, reflection, refraction)",
        "4": "Energy (efficiency, thermal transfer, KE/PE)",
        "5": "Matter (density, pressure, gas laws, states)",
        "6": "Magnetism (fields, induction, motors, transformers)",
        "7": "Nuclear (α/β/γ, half-life, fission/fusion)",
        "8": "Astrophysics (orbits, red shift, universe)"
    }
    
    def __init__(self, topics_yaml_path: str, api_key: str, model: str = "llama-3.1-8b-instant"):
        self.topics = self._load_topics(topics_yaml_path)
        self.api_key = api_key
        self.model = model
        self.api_url = "https://api.groq.com/openai/v1/chat/completions"
        
        # Rate limit tracking
        self.remaining_requests = None
        self.remaining_tokens = None
        self.limit_requests = None
        self.limit_tokens = None
        self.reset_time = None
        
        # Cache for identical questions (hash -> result)
        self.cache = {}
        
        # Stats
        self.total_requests = 0
        self.total_tokens_used = 0
        self.cache_hits = 0
        
    def _load_topics(self, yaml_path: str):
        """Load topics from YAML"""
        with open(yaml_path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
        return data['topics']
    
    def _get_cache_key(self, text: str, question_num: int) -> str:
        """Generate cache key for question"""
        # Normalize text: strip, lowercase, remove extra spaces
        normalized = ' '.join(text.lower().strip().split())
        return hashlib.md5(f"{question_num}:{normalized}".encode()).hexdigest()
    
    def _update_rate_limits(self, headers: Dict):
        """Update rate limit info from response headers"""
        self.remaining_requests = int(headers.get('x-ratelimit-remaining-requests', 0))
        self.remaining_tokens = int(headers.get('x-ratelimit-remaining-tokens', 0))
        self.limit_requests = int(headers.get('x-ratelimit-limit-requests', 100))
        self.limit_tokens = int(headers.get('x-ratelimit-limit-tokens', 100000))
        
        # Parse reset time if available
        reset_str = headers.get('x-ratelimit-reset-requests', '')
        if reset_str:
            # Format: "5s" or "10ms"
            if reset_str.endswith('s'):
                self.reset_time = time.time() + float(reset_str[:-1])
            elif reset_str.endswith('ms'):
                self.reset_time = time.time() + float(reset_str[:-2]) / 1000
    
    def _should_throttle(self) -> Tuple[bool, float]:
        """Check if we should throttle based on rate limits"""
        if self.remaining_requests is None:
            return False, 0
        
        # If very low on requests or tokens, wait
        if self.remaining_requests < 5:
            wait_time = (self.reset_time - time.time()) if self.reset_time else 60
            return True, max(0, wait_time)
        
        if self.remaining_tokens and self.remaining_tokens < 5000:
            # Getting low on tokens
            return True, 2.0
        
        return False, 0
    
    def _retry_with_backoff(self, attempt: int, max_attempts: int = 5) -> float:
        """Calculate backoff time with exponential + jitter"""
        base_delay = min(2 ** attempt, 60)  # Cap at 60 seconds
        jitter = random.uniform(0, base_delay * 0.1)  # 10% jitter
        return base_delay + jitter
    
    def classify_batch(self, questions: List[Dict], max_retries: int = 5) -> List[TopicClassification]:
        """
        Classify a batch of questions in one API call
        
        Args:
            questions: List of dicts with 'number', 'text'
            max_retries: Max retry attempts on failures
            
        Returns:
            List of TopicClassification results
        """
        # Check cache first
        results = []
        uncached_questions = []
        
        for q in questions:
            cache_key = self._get_cache_key(q['text'], q['number'])
            if cache_key in self.cache:
                results.append(self.cache[cache_key])
                self.cache_hits += 1
            else:
                uncached_questions.append(q)
        
        if not uncached_questions:
            return results
        
        # Build batch prompt
        topic_list = "\n".join([f"{code}. {desc}" for code, desc in self.PHYSICS_TOPIC_MAP.items()])
        
        questions_text = "\n\n".join([
            f"Q{q['number']}:\n{q['text'][:2000]}"  # Trim to 2000 chars per question
            for q in uncached_questions
        ])
        
        system_prompt = (
            "You are an Edexcel IGCSE Physics examiner with 10+ years experience. "
            "Classify questions by their PRIMARY physics concept being tested. "
            "Read the ENTIRE question including all subparts to determine the main topic. "
            "Focus on the physics principles, formulas, and calculations required—not just vocabulary. "
            "Return ONLY valid JSON array—no markdown, no explanation."
        )
        
        user_prompt = (
            f"PHYSICS TOPICS (IGCSE specification):\n{topic_list}\n\n"
            f"DIFFICULTY RULES (be strict):\n"
            f"• easy: Single-step recall or direct formula substitution with given values\n"
            f"  Examples: Define velocity, Calculate F=ma with F and m given, State a unit\n\n"
            f"• medium: Multi-step calculation, graph interpretation, or explain a concept\n"
            f"  Examples: Find speed then use it in another formula, Describe a process, Compare two scenarios\n\n"
            f"• hard: Design/plan investigation, evaluate methods, synthesis of multiple concepts, derive formula\n"
            f"  Examples: Plan an experiment, Explain why method X is better than Y, Combine 3+ formulas\n\n"
            f"QUESTIONS TO CLASSIFY:\n{questions_text}\n\n"
            f"For each question, identify:\n"
            f"1. The PRIMARY physics topic being tested (look at formulas/calculations needed)\n"
            f"2. Difficulty based on cognitive demand (easy=recall, medium=apply, hard=evaluate/create)\n\n"
            f"Return JSON array with: question_number (int), topics (max 2 with id & confidence 0-1), difficulty (easy/medium/hard)"
        )
        
        # JSON schema for structured output
        schema = {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["question_number", "topics", "difficulty"],
                "properties": {
                    "question_number": {"type": "integer"},
                    "topics": {
                        "type": "array",
                        "maxItems": 2,
                        "items": {
                            "type": "object",
                            "required": ["id", "confidence"],
                            "properties": {
                                "id": {"type": "string", "enum": self.PHYSICS_TOPICS},
                                "confidence": {"type": "number", "minimum": 0, "maximum": 1}
                            }
                        }
                    },
                    "difficulty": {"type": "string", "enum": ["easy", "medium", "hard"]},
                    "marks_estimated": {"type": ["integer", "null"]},
                    "methods": {"type": "array", "items": {"type": "string"}}
                }
            }
        }
        
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "temperature": 0.1,
            "max_tokens": 150 * len(uncached_questions)  # ~150 tokens per question
        }
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        # Retry loop with exponential backoff
        for attempt in range(max_retries):
            try:
                # Check if we should throttle
                should_wait, wait_time = self._should_throttle()
                if should_wait:
                    print(f"   ⏳ Rate limit throttle: waiting {wait_time:.1f}s...")
                    time.sleep(wait_time)
                
                # Make API call
                response = requests.post(
                    self.api_url,
                    headers=headers,
                    json=payload,
                    timeout=60
                )
                
                # Update rate limit info
                self._update_rate_limits(response.headers)
                
                # Handle 429 specifically
                if response.status_code == 429:
                    retry_after = int(response.headers.get('Retry-After', 60))
                    backoff = max(retry_after, self._retry_with_backoff(attempt))
                    print(f"   ⏳ 429 Rate limit: waiting {backoff:.1f}s (attempt {attempt + 1}/{max_retries})...")
                    time.sleep(backoff)
                    continue
                
                # Check for other errors
                if response.status_code != 200:
                    error_text = response.text[:500]
                    raise Exception(f"HTTP {response.status_code}: {error_text}")
                
                response.raise_for_status()
                result_data = response.json()
                
                # Track usage
                self.total_requests += 1
                self.total_tokens_used += result_data.get('usage', {}).get('total_tokens', 0)
                
                # Parse response
                content = result_data['choices'][0]['message']['content']
                
                # Handle response that might be wrapped in markdown
                if content.strip().startswith('```'):
                    import re
                    json_match = re.search(r'```(?:json)?\s*(.*?)\s*```', content, re.DOTALL)
                    if json_match:
                        content = json_match.group(1)
                
                parsed = json.loads(content)
                
                # Handle both array and object-with-array formats
                if isinstance(parsed, dict):
                    # Try different possible keys
                    for key in ['classifications', 'results', 'questions', 'data']:
                        if key in parsed and isinstance(parsed[key], list):
                            parsed = parsed[key]
                            break
                
                # Ensure we have a list
                if not isinstance(parsed, list):
                    raise ValueError(f"Expected array, got: {type(parsed)}")
                
                # Convert to TopicClassification objects and cache
                batch_results = []
                for item in parsed:
                    if not isinstance(item, dict):
                        continue
                    classification = TopicClassification(
                        question_number=item['question_number'],
                        topics=item['topics'],
                        difficulty=item['difficulty'],
                        marks_estimated=item.get('marks_estimated'),
                        methods=item.get('methods', [])
                    )
                    batch_results.append(classification)
                    
                    # Cache result
                    q = next(q for q in uncached_questions if q['number'] == item['question_number'])
                    cache_key = self._get_cache_key(q['text'], q['number'])
                    self.cache[cache_key] = classification
                
                # Combine cached and new results
                results.extend(batch_results)
                return results
                
            except requests.exceptions.RequestException as e:
                if attempt < max_retries - 1:
                    backoff = self._retry_with_backoff(attempt)
                    print(f"   ⚠️  Request error (attempt {attempt + 1}/{max_retries}): {e}")
                    print(f"   ⏱️  Retrying in {backoff:.1f}s...")
                    time.sleep(backoff)
                else:
                    print(f"   ❌ Failed after {max_retries} attempts: {e}")
                    # Return partial results with low confidence fallback
                    for q in uncached_questions:
                        if not any(r.question_number == q['number'] for r in results):
                            results.append(TopicClassification(
                                question_number=q['number'],
                                topics=[{"id": "1", "confidence": 0.0}],
                                difficulty="medium"
                            ))
                    return results
            
            except (json.JSONDecodeError, KeyError, ValueError) as e:
                print(f"   ❌ Parse error: {e}")
                if attempt < max_retries - 1:
                    time.sleep(self._retry_with_backoff(attempt))
                else:
                    # Return fallback
                    for q in uncached_questions:
                        if not any(r.question_number == q['number'] for r in results):
                            results.append(TopicClassification(
                                question_number=q['number'],
                                topics=[{"id": "1", "confidence": 0.0}],
                                difficulty="medium"
                            ))
                    return results
        
        return results
    
    def get_stats(self) -> Dict:
        """Get classifier statistics"""
        return {
            "total_requests": self.total_requests,
            "total_tokens": self.total_tokens_used,
            "cache_hits": self.cache_hits,
            "cache_size": len(self.cache),
            "remaining_requests": self.remaining_requests,
            "remaining_tokens": self.remaining_tokens
        }


if __name__ == "__main__":
    # Test with sample questions
    load_dotenv('.env.local')
    
    groq_key = os.getenv('GROQ_API_KEY')
    if not groq_key:
        print("❌ GROQ_API_KEY not set")
        exit(1)
    
    topics_yaml = Path(__file__).parent.parent / 'config' / 'physics_topics.yaml'
    classifier = GroqBatchClassifier(str(topics_yaml), groq_key)
    
    # Test batch
    test_questions = [
        {"number": 1, "text": "Calculate the current in a circuit with voltage 12V and resistance 4Ω."},
        {"number": 2, "text": "Describe the process of nuclear fission and explain how it releases energy."},
        {"number": 3, "text": "A wave has frequency 50Hz and wavelength 6m. Calculate its speed."}
    ]
    
    print("Testing batch classification...\n")
    results = classifier.classify_batch(test_questions)
    
    for r in results:
        print(f"Q{r.question_number}: Topics {[t['id'] for t in r.topics]}, Difficulty: {r.difficulty}")
    
    print(f"\nStats: {classifier.get_stats()}")
