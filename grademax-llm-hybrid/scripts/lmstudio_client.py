#!/usr/bin/env python3
"""
LM Studio Client for GradeMax
Replaces all Gemini API calls with local LM Studio inference
"""

import hashlib
import json
import os
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import requests
import yaml


class LMStudioClient:
    """Client for interacting with local LM Studio API"""
    
    def __init__(self, config_path: str = "config/llm.yaml"):
        """Initialize client with configuration"""
        self.config = self._load_config(config_path)
        self.base_url = self.config['lmstudio']['base_url']
        self.models = self.config['lmstudio']['models']
        self.defaults = self.config['lmstudio']['defaults']
        self.retry_policy = self.config['lmstudio']['retry_policy']
        self.cache_dir = Path(self.config['lmstudio']['cache_dir'])
        self.cache_enabled = self.config['lmstudio'].get('cache_enabled', True)
        self.subject_routing = self.config.get('subject_routing', {})
        
        # Create cache directory
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        # Verify Gemini is removed
        self._verify_gemini_removed()
        
        # Test connection
        self._test_connection()
    
    def _load_config(self, config_path: str) -> Dict:
        """Load YAML configuration"""
        with open(config_path, 'r') as f:
            return yaml.safe_load(f)
    
    def _verify_gemini_removed(self):
        """Ensure no Gemini references in environment"""
        removed_vars = self.config.get('removed', {}).get('env_vars', [])
        for var in removed_vars:
            if os.getenv(var):
                raise RuntimeError(
                    f"❌ Found {var} in environment. "
                    f"Gemini is no longer supported. Remove this key."
                )
    
    def _test_connection(self):
        """Test connection to LM Studio server"""
        try:
            response = requests.get(
                f"{self.base_url}/v1/models",
                timeout=5
            )
            response.raise_for_status()
            models = response.json()
            print(f"✅ Connected to LM Studio - {len(models.get('data', []))} models available")
        except requests.exceptions.ConnectionError:
            print(f"⚠️ LM Studio not running at {self.base_url}")
            print("   Start it with: lmstudio server start")
        except Exception as e:
            print(f"⚠️ Could not connect to LM Studio: {e}")
    
    def _get_cache_key(self, prompt: str, model: str, params: Dict) -> str:
        """Generate cache key from prompt and parameters"""
        content = f"{model}:{prompt}:{json.dumps(params, sort_keys=True)}"
        return hashlib.sha256(content.encode()).hexdigest()
    
    def _get_from_cache(self, cache_key: str) -> Optional[str]:
        """Retrieve cached response"""
        if not self.cache_enabled:
            return None
        
        cache_file = self.cache_dir / f"{cache_key}.json"
        if not cache_file.exists():
            return None
        
        try:
            with open(cache_file, 'r') as f:
                cached = json.load(f)
            
            # Check TTL
            ttl_hours = self.config['lmstudio'].get('cache_ttl_hours', 168)
            age_hours = (time.time() - cached['timestamp']) / 3600
            if age_hours > ttl_hours:
                cache_file.unlink()  # Delete expired cache
                return None
            
            return cached['response']
        except Exception:
            return None
    
    def _save_to_cache(self, cache_key: str, response: str):
        """Save response to cache"""
        if not self.cache_enabled:
            return
        
        cache_file = self.cache_dir / f"{cache_key}.json"
        with open(cache_file, 'w') as f:
            json.dump({
                'timestamp': time.time(),
                'response': response
            }, f)
    
    def detect_model_for_subject(self, subject: str) -> str:
        """Choose appropriate model based on subject"""
        math_subjects = self.subject_routing.get('math_subjects', [])
        
        # Check if it's a math subject
        for math_subj in math_subjects:
            if math_subj.lower() in subject.lower():
                return self.models['math_reasoner']
        
        # Default to general classifier
        return self.models['classifier']
    
    def _make_request(
        self,
        endpoint: str,
        payload: Dict,
        retries: int = 0
    ) -> Dict:
        """Make request to LM Studio with retry logic"""
        max_retries = self.retry_policy['max_retries']
        backoff = self.retry_policy['backoff']
        timeout = self.defaults['timeout_seconds']
        
        try:
            start_time = time.time()
            response = requests.post(
                f"{self.base_url}{endpoint}",
                json=payload,
                timeout=timeout
            )
            elapsed = time.time() - start_time
            
            response.raise_for_status()
            
            if elapsed > self.config.get('monitoring', {}).get('warn_if_slower_than_seconds', 10):
                print(f"⚠️ Slow inference: {elapsed:.2f}s")
            
            return response.json()
            
        except requests.exceptions.Timeout:
            if retries < max_retries and self.retry_policy.get('retry_on_timeout', True):
                wait_time = backoff ** retries
                print(f"⏱️ Timeout, retrying in {wait_time}s...")
                time.sleep(wait_time)
                return self._make_request(endpoint, payload, retries + 1)
            raise
            
        except requests.exceptions.RequestException as e:
            if retries < max_retries:
                wait_time = backoff ** retries
                print(f"🔄 Request failed, retrying in {wait_time}s...")
                time.sleep(wait_time)
                return self._make_request(endpoint, payload, retries + 1)
            raise RuntimeError(f"LM Studio request failed after {max_retries} retries: {e}")
    
    def classify_question(
        self,
        question_text: str,
        subject: str,
        topics: Optional[List[str]] = None,
        temperature: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Classify question and extract topics/subtopics
        
        Args:
            question_text: The question to classify
            subject: Subject name (e.g., "Physics", "Pure Mathematics")
            topics: Optional list of known topics to match against
            temperature: Override default temperature
        
        Returns:
            Dict with classification results:
            {
                "topics": ["Topic 1", "Topic 2"],
                "subtopics": ["Subtopic A", "Subtopic B"],
                "difficulty": "medium",
                "reasoning": "explanation"
            }
        """
        # Choose model based on subject
        model = self.detect_model_for_subject(subject)
        
        # Build prompt
        prompt = self._build_classification_prompt(question_text, subject, topics)
        
        # Parameters
        params = {
            'temperature': temperature or self.defaults['temperature'],
            'max_tokens': self.defaults['max_tokens'],
            'top_p': self.defaults.get('top_p', 0.95)
        }
        
        # Check cache
        cache_key = self._get_cache_key(prompt, model, params)
        cached_response = self._get_from_cache(cache_key)
        if cached_response:
            print("💾 Cache hit")
            return json.loads(cached_response)
        
        # Make request (JSON mode via prompt engineering)
        payload = {
            'model': model,
            'messages': [
                {'role': 'system', 'content': 'You are an expert education content classifier. You MUST respond ONLY with valid JSON, no other text.'},
                {'role': 'user', 'content': prompt}
            ],
            **params
        }
        
        response = self._make_request('/v1/chat/completions', payload)
        content = response['choices'][0]['message']['content']
        
        # Parse JSON response
        try:
            result = json.loads(content)
        except json.JSONDecodeError:
            # Fallback: extract JSON from markdown code blocks
            import re
            json_match = re.search(r'```json\n(.*?)\n```', content, re.DOTALL)
            if json_match:
                result = json.loads(json_match.group(1))
            else:
                raise ValueError(f"Could not parse LLM response as JSON: {content}")
        
        # Cache result
        self._save_to_cache(cache_key, json.dumps(result))
        
        return result
    
    def _build_classification_prompt(
        self,
        question_text: str,
        subject: str,
        topics: Optional[List[str]] = None
    ) -> str:
        """Build prompt for question classification"""
        prompt = f"""Analyze this {subject} exam question and classify it.

Question:
{question_text[:1000]}

"""
        if topics:
            prompt += f"Available topics: {', '.join(topics[:10])}\n\n"
        
        prompt += """You MUST respond with ONLY a valid JSON object, no other text before or after.

Required JSON format:
{
  "topics": ["Topic1", "Topic2"],
  "difficulty": "medium",
  "reasoning": "brief explanation"
}

Respond with JSON only:"""
        
        return prompt
    
    def generate_embedding(self, text: str) -> List[float]:
        """
        Generate embedding vector for text
        
        Args:
            text: Text to embed
        
        Returns:
            List of floats representing the embedding
        """
        model = self.models['embedder']
        
        # Check cache
        cache_key = self._get_cache_key(text, model, {})
        cached_response = self._get_from_cache(cache_key)
        if cached_response:
            return json.loads(cached_response)
        
        # Make request
        payload = {
            'model': model,
            'input': text
        }
        
        response = self._make_request('/v1/embeddings', payload)
        embedding = response['data'][0]['embedding']
        
        # Cache result
        self._save_to_cache(cache_key, json.dumps(embedding))
        
        return embedding
    
    def reason(
        self,
        prompt: str,
        subject: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None
    ) -> str:
        """
        General reasoning/generation task
        
        Args:
            prompt: The prompt to send
            subject: Optional subject for model selection
            max_tokens: Override default max tokens
            temperature: Override default temperature
        
        Returns:
            Generated text response
        """
        # Choose model
        model = self.detect_model_for_subject(subject) if subject else self.models['classifier']
        
        # Parameters
        params = {
            'temperature': temperature or self.defaults['temperature'],
            'max_tokens': max_tokens or self.defaults['max_tokens'],
            'top_p': self.defaults.get('top_p', 0.95)
        }
        
        # Check cache
        cache_key = self._get_cache_key(prompt, model, params)
        cached_response = self._get_from_cache(cache_key)
        if cached_response:
            print("💾 Cache hit")
            return cached_response
        
        # Make request
        payload = {
            'model': model,
            'messages': [
                {'role': 'user', 'content': prompt}
            ],
            **params
        }
        
        response = self._make_request('/v1/chat/completions', payload)
        content = response['choices'][0]['message']['content']
        
        # Cache result
        self._save_to_cache(cache_key, content)
        
        return content


# Singleton instance
_client = None

def get_client() -> LMStudioClient:
    """Get or create LM Studio client singleton"""
    global _client
    if _client is None:
        config_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            'config',
            'llm.yaml'
        )
        _client = LMStudioClient(config_path)
    return _client
