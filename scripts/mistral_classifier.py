#!/usr/bin/env python3
"""
Simple Single-Topic Classifier for GradeMax using Local LM Studio
ONE question → ONE topic
Connects to local server at http://127.0.0.1:1234
"""

import os
import json
import time
from pathlib import Path
from typing import Dict
from dataclasses import dataclass
import yaml
import requests
from dotenv import load_dotenv


@dataclass
class TopicClassification:
    """ONE topic per question"""
    page_has_question: bool
    topic: str  # Single topic code ("1", "2", etc.)
    difficulty: str  # "easy", "medium", "hard"
    confidence: float


class MistralTopicClassifier:
    """Classifies questions with ONE primary topic only using Local LM Studio"""
    
    # Keyword mapping based on IGCSE Physics textbook vocabulary
    KEYWORD_MAP = {
        "force": "1", "momentum": "1", "acceleration": "1", "velocity": "1", "speed": "1",
        "mass": "1", "weight": "1", "terminal velocity": "1", "newton": "1",
        "current": "2", "ohm": "2", "circuit": "2", "voltage": "2", "resistance": "2",
        "potential difference": "2", "series": "2", "parallel": "2", "power": "2", "vit": "2",
        "wave": "3", "reflection": "3", "frequency": "3", "refraction": "3", "diffraction": "3",
        "electromagnetic": "3", "spectrum": "3", "sound": "3", "wavelength": "3",
        "energy": "4", "efficiency": "4", "conduction": "4", "convection": "4", "radiation": "4",
        "kinetic": "4", "potential energy": "4", "insulation": "4", "thermal": "4",
        "pressure": "5", "density": "5", "temperature": "5", "gas law": "5", "volume": "5",
        "solid": "5", "liquid": "5", "molecule": "5",
        "magnet": "6", "induced": "6", "coil": "6", "electromagnetic": "6", "motor": "6",
        "transformer": "6", "generator": "6", "flux": "6",
        "alpha": "7", "beta": "7", "gamma": "7", "radiation": "7", "half-life": "7",
        "radioactive": "7", "nuclear": "7", "fission": "7", "fusion": "7", "decay": "7",
        "orbit": "8", "planet": "8", "red shift": "8", "universe": "8", "solar": "8",
        "gravity": "8", "satellite": "8", "star": "8", "expansion": "8"
    }
    
    def __init__(self, topics_yaml_path: str, groq_api_key: str = None, openrouter_api_key: str = None, model_name: str = "llama-3.1-8b-instant"):
        """Initialize classifier

        Uses both Groq and OpenRouter APIs with automatic failover.
        Automatically switches between models if rate limits are hit.
        """
        # Load environment variables
        load_dotenv()
        
        # Load YAML and extract subject info
        with open(topics_yaml_path, 'r', encoding='utf-8') as f:
            yaml_data = yaml.safe_load(f)
        
        self.topics = yaml_data['topics']
        self.topic_codes = [t['code'] for t in self.topics]
        
        # Extract subject name for prompt generation
        self.subject_name = yaml_data.get('subject', {}).get('name', 'exam')
        
        # Load API keys from environment or parameters
        self.groq_api_key = groq_api_key or os.getenv('GROQ_API_KEY')
        
        if not self.groq_api_key:
            raise ValueError("GROQ_API_KEY is required")

        # Only use Groq models (OpenRouter not reliable)
        self.available_models = [
            {"name": "llama-3.1-8b-instant", "rpm": 30, "tpm": 6000, "supports_json": True, "provider": "groq"},
            {"name": "llama-3.3-70b-versatile", "rpm": 30, "tpm": 12000, "supports_json": True, "provider": "groq"},
        ]
        self.current_model_index = 0
        self.model = self.available_models[0]["name"]
        self.current_provider = "groq"
        
        # Track requests per model
        self.model_requests = {model["name"]: [] for model in self.available_models}
        
        self.last_call_time = 0
        # Conservative rate limiting: 5 seconds between requests for stability
        self.min_delay = 5.0
        
        # Build keyword map from topics
        self._build_keyword_map()
    
    def _build_keyword_map(self):
        """Build keyword map from YAML topics for faster classification"""
        self.keyword_map = {}
        
        for topic in self.topics:
            topic_id = topic['id']
            
            # Add core phrases as keywords
            if 'core' in topic:
                for phrase_item in topic['core']:
                    phrase = phrase_item.get('text', '').lower()
                    if phrase:
                        self.keyword_map[phrase] = topic_id
            
            # Add support phrases as keywords
            if 'support' in topic:
                for phrase_item in topic['support']:
                    phrase = phrase_item.get('text', '').lower()
                    if phrase:
                        self.keyword_map[phrase] = topic_id
        
        print(f"   [OK] Built keyword map with {len(self.keyword_map)} keywords")
    
    def _load_topics(self, yaml_path: str):
        """Load topics from YAML"""
        with open(yaml_path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
        return data['topics']
    
    def _switch_to_next_model(self):
        """Switch to the next available model when rate limit is hit."""
        old_model = self.model
        old_provider = self.current_provider
        self.current_model_index = (self.current_model_index + 1) % len(self.available_models)
        self.model = self.available_models[self.current_model_index]["name"]
        self.current_provider = self.available_models[self.current_model_index]["provider"]
        print(f"   [SWITCH] From {old_provider}:{old_model} to {self.current_provider}:{self.model}")
        return self.model
    
    def _wait_for_rate_limit(self):
        """Ensure we don't exceed rate limits - with automatic model switching"""
        now = time.time()
        current_model_info = self.available_models[self.current_model_index]
        model_rpm = current_model_info["rpm"]
        
        # Remove requests older than 60 seconds for current model
        self.model_requests[self.model] = [t for t in self.model_requests[self.model] if now - t < 60]
        
        # If we've hit the limit for this model, try switching
        if len(self.model_requests[self.model]) >= model_rpm - 2:  # Leave 2 request buffer
            # Try to find a model with available capacity
            for _ in range(len(self.available_models)):
                next_index = (self.current_model_index + 1) % len(self.available_models)
                next_model_name = self.available_models[next_index]["name"]
                next_model_rpm = self.available_models[next_index]["rpm"]
                
                # Clean up old requests for next model
                self.model_requests[next_model_name] = [
                    t for t in self.model_requests[next_model_name] if now - t < 60
                ]
                
                # If this model has capacity, switch to it
                if len(self.model_requests[next_model_name]) < next_model_rpm - 2:
                    self._switch_to_next_model()
                    break
            else:
                # All models at capacity, wait for the oldest request to expire
                oldest_request = min(self.model_requests[self.model])
                wait_time = 61 - (now - oldest_request)
                if wait_time > 0:
                    print(f"   [WAIT] All models at capacity. Waiting {wait_time:.1f}s...", flush=True)
                    time.sleep(wait_time)
                    now = time.time()
                    self.model_requests[self.model] = [t for t in self.model_requests[self.model] if now - t < 60]
        
        # Ensure minimum delay between requests
        elapsed = now - self.last_call_time
        if elapsed < self.min_delay:
            time.sleep(self.min_delay - elapsed)
        
        # Record this request
        self.last_call_time = time.time()
        self.model_requests[self.model].append(self.last_call_time)
    
    def _build_topic_descriptors(self):
        """Build topic descriptors dynamically from YAML data"""
        descriptors = []
        for topic in self.topics:
            # Get core phrases and format them nicely
            core_phrases = []
            if 'core' in topic:
                for phrase_item in topic['core']:
                    phrase_text = phrase_item.get('text', '')
                    if phrase_text:
                        core_phrases.append(phrase_text)
            
            # Get support phrases
            support_phrases = []
            if 'support' in topic:
                for phrase_item in topic['support']:
                    phrase_text = phrase_item.get('text', '')
                    if phrase_text:
                        support_phrases.append(phrase_text)
            
            # Build descriptor
            topic_id = topic['id']
            topic_code = topic['code']
            topic_name = topic['name']
            
            # Combine phrases
            all_phrases = core_phrases + support_phrases
            phrases_str = ', '.join(all_phrases[:8])  # Limit to 8 phrases for conciseness
            
            descriptor = f"{topic_id}. {topic_code} - {topic_name}: {phrases_str}"
            descriptors.append(descriptor)
        
        return "\n".join(descriptors)
    
    def classify(self, page_text: str, question_num: str = None, _retry_count: int = 0) -> TopicClassification:
        """
        Classify ONE page with ONE topic using Groq API
        
        Args:
            page_text: Extracted text from PDF page
            question_num: Question number for logging
            _retry_count: Internal retry counter to prevent infinite recursion
        
        Returns:
            TopicClassification with single topic
        """
        # Prevent infinite recursion
        if _retry_count >= len(self.available_models) * 2:
            print(f"   [ERROR] Max retries exceeded, using keyword fallback")
            keyword_topic = self._keyword_check(page_text.lower())
            return TopicClassification(
                page_has_question=True,
                topic=keyword_topic if keyword_topic else '1',
                difficulty='medium',
                confidence=0.2 if keyword_topic else 0.0
            )
        
        # Try keyword-based classification FIRST to reduce API calls
        keyword_topic = self._keyword_check(page_text.lower())
        
        if keyword_topic:
            # Count keyword matches per topic
            topic_scores = {}
            text_lower = page_text.lower()
            
            for keyword, topic in self.keyword_map.items():
                if keyword in text_lower:
                    topic_scores[topic] = topic_scores.get(topic, 0) + 1
            
            # If we have 3+ keyword matches for a topic, use it without LLM call
            if topic_scores and max(topic_scores.values()) >= 3:
                best_topic = max(topic_scores, key=topic_scores.get)
                return TopicClassification(
                    page_has_question=True,
                    topic=best_topic,
                    difficulty='medium',
                    confidence=0.85  # High confidence for keyword-based
                )
        
        # If keywords don't give strong match, use LLM
        self._wait_for_rate_limit()
        
        # Build topic list dynamically from YAML
        topic_list = self._build_topic_descriptors()
        
        # Get subject info from YAML if available
        subject_name = getattr(self, 'subject_name', 'exam')
        
        # Build list of valid topic IDs for JSON schema
        valid_topic_ids = '|'.join([f'"{t["id"]}"' for t in self.topics])

        # Build the prompt as a safely concatenated string (avoid f-string brace issues)
        prompt = (
            f"You are classifying {subject_name} exam questions by topic and difficulty.\n"
            "Below are all valid topic codes and their detailed descriptors:\n\n"
            + topic_list + "\n\n"
            "TOPIC CLASSIFICATION:\n"
            "- Identify which topic best matches this question (return ONE primary topic).\n"
            "- Base your choice strictly on the concepts being tested, not just vocabulary overlap.\n"
            "- Consider the key terms, formulas, and principles mentioned.\n"
            "- If sub-questions test different topics, choose the DOMINANT one.\n\n"
            "DIFFICULTY CLASSIFICATION:\n"
            "- \"easy\": Simple recall, basic definitions, one-step calculations, direct formula application\n"
            "  Examples: Define a term, Calculate using a formula with all values given, State a basic fact\n\n"
            "- \"medium\": Multi-step problems, application to new contexts, interpreting graphs/data, explaining concepts\n"
            "  Examples: Calculate multiple quantities in sequence, Explain why something occurs, Compare scenarios\n\n"
            "- \"hard\": Complex synthesis, multiple concepts combined, extended explanations, design questions, evaluation\n"
            "  Examples: Design something, Evaluate a method, Apply multiple concepts together, Analyze unfamiliar contexts\n\n"
            "Question Page:\n"
            + page_text[:4000] + "\n\n"
            "CRITICAL: Your response MUST be ONLY a valid JSON object. No explanations, no markdown, no code blocks.\n"
            "Start your response with { and end with }. Nothing else.\n\n"
            "Required JSON schema:\n"
            "{\n"
            "    \"page_has_question\": true,\n"
            f"    \"topic\": {valid_topic_ids},\n"
            "    \"difficulty\": \"easy\"|\"medium\"|\"hard\",\n"
            "    \"confidence\": 0.0-1.0\n"
            "}\n\n"
            "Rules:\n"
            "- Start response with { and end with }\n"
            "- NO markdown code blocks (no ```json)\n"
            "- NO explanatory text before or after the JSON\n"
            "- \"confidence\" MUST be a decimal number between 0.0 and 1.0\n"
            "- \"topic\" MUST be one of the valid topic IDs listed above\n"
            "- \"difficulty\" MUST be exactly \"easy\", \"medium\", or \"hard\"\n"
            "- \"page_has_question\" MUST be true or false (boolean)\n\n"
            "Respond with the JSON object now:\n"
        )
        
        try:
            # Get current provider and set appropriate API endpoint and headers
            current_model_info = self.available_models[self.current_model_index]
            provider = current_model_info["provider"]
            
            # Only Groq provider supported
            api_url = "https://api.groq.com/openai/v1/chat/completions"
            api_key = self.groq_api_key
            if not api_key:
                print(f"   [WARN] Groq API key not available")
                return None
            
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {api_key}"
            }

            # Check if current model supports JSON mode
            supports_json = current_model_info.get("supports_json", True)
            
            # Groq uses OpenAI-compatible format, OpenRouter too
            payload = {
                "model": self.model,
                "messages": [
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.1,
                "max_tokens": 500
            }
            
            # Only add response_format if model supports it
            if supports_json:
                payload["response_format"] = {"type": "json_object"}

            timeout_seconds = 60

            # Call API
            response = requests.post(
                api_url,
                headers=headers,
                json=payload,
                timeout=timeout_seconds
            )
            
            response.raise_for_status()
            result_data = response.json()
            
        except requests.exceptions.HTTPError as e:
            # Handle rate limit errors - try switching models
            if e.response.status_code == 429:
                print(f"   [RATE LIMIT] Hit on {self.model}, switching...")
                old_model = self.model
                self._switch_to_next_model()
                # If we're back to the original model, all models are rate limited
                if self.model == old_model:
                    print(f"   [WAIT] All models rate limited, waiting 60s...")
                    time.sleep(60)
                else:
                    time.sleep(2)
                # Retry with new model
                return self.classify(page_text, question_num, _retry_count + 1)
            elif e.response.status_code == 400:
                print(f"   [WARN] Bad request on {self.model} (possibly unsupported feature), switching models...")
                old_model = self.model
                self._switch_to_next_model()
                time.sleep(1)
                # Don't retry indefinitely
                if self.model != old_model:
                    return self.classify(page_text, question_num, _retry_count + 1)
                # All models failed with 400
                keyword_topic = self._keyword_check(page_text.lower())
                return TopicClassification(
                    page_has_question=True,
                    topic=keyword_topic if keyword_topic else '1',
                    difficulty='medium',
                    confidence=0.3 if keyword_topic else 0.0
                )
            elif e.response.status_code == 503:
                print(f"   [UNAVAILABLE] Service unavailable on {self.model}")
                self._switch_to_next_model()
                time.sleep(1)
                return self.classify(page_text, question_num, _retry_count + 1)
            else:
                print(f"   [HTTP ERROR] {e.response.status_code}: {e}")
                # Try keyword fallback
                keyword_topic = self._keyword_check(page_text.lower())
                return TopicClassification(
                    page_has_question=True,
                    topic=keyword_topic if keyword_topic else '1',
                    difficulty='medium',
                    confidence=0.3 if keyword_topic else 0.0
                )
        except Exception as e:
            print(f"   [ERROR] Classification error: {e}")
            # Try keyword fallback
            keyword_topic = self._keyword_check(page_text.lower())
            return TopicClassification(
                page_has_question=True,
                topic=keyword_topic if keyword_topic else '1',
                difficulty='medium',
                confidence=0.3 if keyword_topic else 0.0
            )
        
        try:
            message_content = result_data['choices'][0]['message']['content'].strip()
            
            # Enhanced JSON extraction with multiple fallback strategies
            result = None
            
            # Strategy 1: Direct JSON parse
            try:
                result = json.loads(message_content)
            except json.JSONDecodeError:
                pass
            
            # Strategy 2: Extract from markdown code blocks
            if result is None:
                import re
                json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', message_content, re.DOTALL)
                if json_match:
                    try:
                        result = json.loads(json_match.group(1))
                    except json.JSONDecodeError:
                        pass
            
            # Strategy 3: Find first complete JSON object
            if result is None:
                import re
                json_match = re.search(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', message_content, re.DOTALL)
                if json_match:
                    try:
                        result = json.loads(json_match.group(0))
                    except json.JSONDecodeError:
                        pass
            
            # Strategy 4: Try to clean common formatting issues
            if result is None:
                # Remove any leading/trailing text, keep only the JSON
                cleaned = message_content
                if '{' in cleaned and '}' in cleaned:
                    start = cleaned.find('{')
                    end = cleaned.rfind('}') + 1
                    cleaned = cleaned[start:end]
                    try:
                        result = json.loads(cleaned)
                    except json.JSONDecodeError:
                        pass
            
            # If all strategies failed, raise error
            if result is None:
                print(f"   [WARN] Failed to parse JSON from {self.model}. Response: {message_content[:200]}")
                print(f"   [RETRY] Switching models and retrying...")
                self._switch_to_next_model()
                time.sleep(1)
                return self.classify(page_text, question_num, _retry_count + 1)
            
            # Validate required fields
            if 'topic' not in result or 'difficulty' not in result:
                print(f"   [WARN] Invalid JSON structure from {self.model}. Missing required fields.")
                print(f"   [RETRY] Switching models and retrying...")
                self._switch_to_next_model()
                time.sleep(1)
                return self.classify(page_text, question_num, _retry_count + 1)
            
            classification = TopicClassification(
                page_has_question=result.get('page_has_question', True),
                topic=result.get('topic', '1'),
                difficulty=result.get('difficulty', 'medium'),
                confidence=result.get('confidence', 0.5)
            )
            
            # Apply keyword-based guardrail if confidence is low
            if classification.confidence < 0.7:
                keyword_topic = self._keyword_check(page_text.lower())
                if keyword_topic and keyword_topic != classification.topic:
                    print(f"   [WARN] Low confidence ({classification.confidence:.2f}), keyword suggests topic {keyword_topic}")
            
            return classification
            
        except Exception as e:
            print(f"   [ERROR] JSON parsing error: {e}")
            print(f"   [RETRY] Switching models and retrying...")
            self._switch_to_next_model()
            time.sleep(1)
            return self.classify(page_text, question_num, _retry_count + 1)
    
    def _keyword_check(self, text: str) -> str:
        """Check for keyword matches to suggest a topic"""
        topic_scores = {}
        
        # Use the dynamically built keyword map from YAML
        if hasattr(self, 'keyword_map'):
            for keyword, topic in self.keyword_map.items():
                if keyword in text:
                    topic_scores[topic] = topic_scores.get(topic, 0) + 1
        else:
            # Fallback to hardcoded KEYWORD_MAP for backward compatibility
            for keyword, topic in self.KEYWORD_MAP.items():
                if keyword in text:
                    topic_scores[topic] = topic_scores.get(topic, 0) + 1
        
        if not topic_scores:
            return None
        
        # Return topic with most keyword matches
        return max(topic_scores, key=topic_scores.get)


# Simple test / CLI
if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python mistral_classifier.py <topics_yaml_path>")
        sys.exit(1)

    # Load environment variables from .env.local for CLI testing
    load_dotenv('.env.local')

    # Get both API keys
    groq_key = os.getenv('GROQ_API_KEY')
    openrouter_key = os.getenv('OPENROUTER_API_KEY')
    
    if not groq_key and not openrouter_key:
        print("[ERROR] Neither GROQ_API_KEY nor OPENROUTER_API_KEY set in .env.local!")
        sys.exit(1)

    print(f"\\n[OK] Groq API: {'Available' if groq_key else 'Not available'}")
    print(f"[OK] OpenRouter API: {'Available' if openrouter_key else 'Not available'}")

    classifier = MistralTopicClassifier(sys.argv[1], groq_key, openrouter_key)

    # Test classification on 3 short samples
    samples = [
        ("A car accelerates from rest to 30 m/s in 5 seconds. (a) Calculate the acceleration. (b) Calculate the distance travelled.", "Q1"),
        ("A light ray passes from air into glass with refractive index 1.5. Calculate the angle of refraction given an incident angle of 30 degrees.", "Q2"),
        ("State two differences between alpha and beta radiation.", "Q3")
    ]

    for text, qid in samples:
        print(f"\n---\nSample {qid}:\n{text[:120]}...")
        try:
            res = classifier.classify(text, qid)
            print(f"Result -> topic: {res.topic}, difficulty: {res.difficulty}, confidence: {res.confidence:.2f}")
        except Exception as e:
            print(f"Test classification failed: {e}")
