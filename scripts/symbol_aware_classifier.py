"""
Enhanced Topic Classifier for Further Pure Mathematics
Supports symbol-first classification with LLM fallback
"""

import re
import yaml
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass


@dataclass
class ClassificationResult:
    """Enhanced classification result with multi-topic support"""
    topic: str  # Primary topic (for compatibility)
    topics: List[Dict[str, any]]  # All topics with confidences
    confidence: float  # Primary confidence
    difficulty: str
    page_has_question: bool = True
    methods: List[str] = None
    dominant_ao: str = None
    difficulty_hint: str = None


class SymbolAwareClassifier:
    """
    Symbol-first classifier for Further Pure Mathematics
    Falls back to existing SingleTopicClassifier for Physics
    """
    
    def __init__(self, config_path: str, api_key: str):
        self.config_path = Path(config_path)
        self.api_key = api_key
        self.config = self._load_config()
        
        # Detect if this is symbol-aware config (Further Pure) or simple (Physics)
        self.is_symbol_aware = 'symbol_grammar' in self.config
        
        if self.is_symbol_aware:
            self._compile_symbol_patterns()
        
        # Import and initialize LLM classifier
        try:
            import google.generativeai as genai
            genai.configure(api_key=api_key)
            # Use gemini-2.5-flash for production - latest stable Flash model
            # - Balanced: Good speed + quality
            # - High rate limits with paid API (1000+ RPM)
            # - 1M input tokens + 65K output tokens
            self.model = genai.GenerativeModel('gemini-2.5-flash')
            self.llm_available = True
        except Exception as e:
            self.llm_available = False
            print(f"⚠️  LLM not available: {e}")
    
    def _load_config(self) -> Dict:
        """Load YAML configuration"""
        with open(self.config_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    
    def _compile_symbol_patterns(self):
        """Compile regex patterns from symbol grammar"""
        self.symbol_patterns = {}
        
        if 'symbol_grammar' not in self.config:
            return
        
        tokens = self.config['symbol_grammar'].get('tokens', {})
        for token_name, patterns in tokens.items():
            compiled = []
            for pattern in patterns:
                try:
                    compiled.append(re.compile(pattern, re.IGNORECASE))
                except re.error as e:
                    print(f"⚠️  Invalid regex in {token_name}: {pattern} - {e}")
            self.symbol_patterns[token_name] = compiled
    
    def _extract_symbols(self, text: str) -> Dict[str, int]:
        """Extract and count symbol tokens from text"""
        if not self.is_symbol_aware:
            return {}
        
        # Normalize text if specified
        if self.config.get('symbol_grammar', {}).get('normalize', {}):
            text = self._normalize_text(text)
        
        symbol_counts = {}
        for token_name, patterns in self.symbol_patterns.items():
            count = 0
            for pattern in patterns:
                matches = pattern.findall(text)
                count += len(matches)
            if count > 0:
                symbol_counts[token_name] = count
        
        return symbol_counts
    
    def _normalize_text(self, text: str) -> str:
        """Apply text normalizations from config"""
        normalize_rules = self.config.get('symbol_grammar', {}).get('normalize', {})
        
        if normalize_rules.get('superscripts_to_caret'):
            # Convert superscripts: x² → x^2
            superscripts = {'⁰': '0', '¹': '1', '²': '2', '³': '3', '⁴': '4', 
                          '⁵': '5', '⁶': '6', '⁷': '7', '⁸': '8', '⁹': '9'}
            for sup, num in superscripts.items():
                text = text.replace(sup, f'^{num}')
        
        if normalize_rules.get('minus_to_ascii'):
            text = text.replace('−', '-')
        
        if normalize_rules.get('times_to_ascii_x'):
            text = text.replace('×', '*').replace('·', '*').replace('∘', '*')
        
        if normalize_rules.get('divide_slash'):
            text = text.replace('÷', '/')
        
        if normalize_rules.get('greek_letters_to_ascii_names'):
            greek_map = {'θ': 'theta', 'π': 'pi', 'α': 'alpha', 'β': 'beta', 
                        'γ': 'gamma', 'δ': 'delta', 'ε': 'epsilon', 'λ': 'lambda',
                        'μ': 'mu', 'σ': 'sigma', 'Σ': 'Sigma', 'φ': 'phi'}
            for greek, name in greek_map.items():
                text = text.replace(greek, name)
        
        return text
    
    def _check_symbol_hard_floors(self, symbol_counts: Dict[str, int], text: str) -> Dict[str, float]:
        """Check if topics meet symbol-based hard floor requirements"""
        if not self.is_symbol_aware:
            return {}
        
        hard_floors = self.config.get('symbol_hard_floors', {})
        forced_topics = {}
        
        for topic_id, rule in hard_floors.items():
            any_of = rule.get('any_of', [])
            min_conf = rule.get('min_confidence', 0.55)
            
            # Check if any required symbol is present
            for symbol_name in any_of:
                if symbol_name in symbol_counts and symbol_counts[symbol_name] > 0:
                    forced_topics[topic_id] = min_conf
                    break
        
        return forced_topics
    
    def _score_topics_symbol_first(self, text: str) -> List[Dict[str, any]]:
        """Score topics using symbol-first approach"""
        if not self.is_symbol_aware:
            return self._score_topics_simple(text)
        
        # Extract symbols
        symbol_counts = self._extract_symbols(text)
        
        # Check hard floors
        forced_topics = self._check_symbol_hard_floors(symbol_counts, text)
        
        # Score each topic
        topic_scores = []
        weights = self.config.get('scoring', {}).get('weights', {
            'lexical': 0.35, 'symbols': 0.45, 'layout': 0.05, 'co_tag_prior': 0.15
        })
        
        for topic in self.config.get('topics', []):
            topic_id = topic['id']
            
            # Start with forced confidence if applicable
            if topic_id in forced_topics:
                confidence = forced_topics[topic_id]
                evidence = [f"Symbol match: {list(symbol_counts.keys())}"]
            else:
                # Calculate lexical score
                lexical_score = self._lexical_match(text, topic.get('lexical', {}))
                
                # Calculate symbol score
                symbol_score = self._symbol_match(symbol_counts, topic.get('symbols', {}))
                
                # Combined score
                confidence = (lexical_score * weights['lexical'] + 
                            symbol_score * weights['symbols'])
                
                # Apply penalties
                penalties = self.config.get('scoring', {}).get('penalties', {})
                if self._has_negative_hits(text, topic_id):
                    confidence += penalties.get('negative_hits', -0.22)
                
                confidence = max(0.0, min(1.0, confidence))
                
                evidence = []
                if symbol_score > 0.3:
                    evidence.append(f"Symbols: {list(symbol_counts.keys())}")
                if lexical_score > 0.3:
                    evidence.append(f"Keywords present")
            
            if confidence > 0.45:  # Threshold for inclusion
                topic_scores.append({
                    'id': topic_id,
                    'code': topic.get('code', topic_id),
                    'confidence': round(confidence, 2),
                    'evidence': evidence
                })
        
        # Sort by confidence
        topic_scores.sort(key=lambda x: x['confidence'], reverse=True)
        
        return topic_scores
    
    def _lexical_match(self, text: str, lexical_config: Dict) -> float:
        """Calculate lexical match score"""
        if not lexical_config:
            return 0.0
        
        text_lower = text.lower()
        matches = 0
        total = 0
        
        for pattern in lexical_config.get('any', []):
            total += 1
            if re.search(pattern, text_lower):
                matches += 1
        
        return matches / total if total > 0 else 0.0
    
    def _symbol_match(self, symbol_counts: Dict[str, int], symbol_config: Dict) -> float:
        """Calculate symbol match score"""
        if not symbol_config:
            return 0.0
        
        required_sets = symbol_config.get('any_sets', [])
        if not required_sets:
            return 0.0
        
        matches = sum(1 for sym_set in required_sets if sym_set in symbol_counts)
        return matches / len(required_sets)
    
    def _has_negative_hits(self, text: str, topic_id: str) -> bool:
        """Check for negative keywords"""
        negatives = self.config.get('postprocess', {}).get('negatives_global', [])
        text_lower = text.lower()
        return any(neg in text_lower for neg in negatives)
    
    def _score_topics_simple(self, text: str) -> List[Dict[str, any]]:
        """Simple scoring for Physics-style configs"""
        # This maintains compatibility with existing Physics classifier
        topic_scores = []
        
        for topic in self.config.get('topics', []):
            confidence = self._simple_keyword_match(text, topic)
            if confidence > 0.4:
                topic_scores.append({
                    'id': str(topic.get('topic_number', topic.get('code', '?'))),
                    'code': str(topic.get('topic_number', topic.get('code', '?'))),
                    'confidence': confidence,
                    'evidence': ['Keyword match']
                })
        
        topic_scores.sort(key=lambda x: x['confidence'], reverse=True)
        return topic_scores
    
    def _simple_keyword_match(self, text: str, topic: Dict) -> float:
        """Simple keyword matching for basic configs"""
        text_lower = text.lower()
        keywords = topic.get('keywords', [])
        
        if not keywords:
            return 0.0
        
        matches = sum(1 for kw in keywords if kw.lower() in text_lower)
        return min(0.95, matches / len(keywords) * 1.2)
    
    def _should_escalate_to_llm(self, topic_scores: List[Dict]) -> bool:
        """Determine if LLM escalation is needed"""
        if not self.is_symbol_aware or not self.llm_available:
            return False
        
        if not topic_scores:
            return True
        
        max_confidence = max(t['confidence'] for t in topic_scores)
        threshold = self.config.get('escalation', {}).get('llm_escalation_threshold', 0.62)
        
        return max_confidence < threshold
    
    def classify(self, text: str) -> ClassificationResult:
        """
        Main classification method
        Returns: ClassificationResult with topic(s)
        """
        # Score topics using appropriate method
        topic_scores = self._score_topics_symbol_first(text)
        
        # Check if we should escalate to LLM
        if self._should_escalate_to_llm(topic_scores):
            llm_scores = self._classify_with_llm(text)
            if llm_scores:
                topic_scores = llm_scores
        
        if not topic_scores:
            # No topic found
            return ClassificationResult(
                topic="Unknown",
                topics=[],
                confidence=0.0,
                difficulty="unknown",
                page_has_question=False
            )
        
        # Get primary topic (highest confidence)
        primary = topic_scores[0]
        
        # Determine difficulty
        difficulty = self._infer_difficulty(text, primary['id'])
        
        return ClassificationResult(
            topic=primary['code'],  # For compatibility with existing system
            topics=topic_scores,     # Full list with confidences
            confidence=primary['confidence'],
            difficulty=difficulty,
            page_has_question=True,
            methods=self._extract_methods(text) if self.is_symbol_aware else None,
            dominant_ao=self._get_dominant_ao(primary['id']) if self.is_symbol_aware else None
        )
    
    def _classify_with_llm(self, text: str) -> List[Dict[str, any]]:
        """Use LLM for classification when rules are insufficient"""
        if not self.llm_available:
            return None
        
        try:
            # Build prompt based on config type
            if self.is_symbol_aware:
                prompt = self._build_symbol_aware_prompt(text)
            else:
                prompt = self._build_simple_prompt(text)
            
            response = self.model.generate_content(prompt)
            
            # Parse JSON response
            import json
            result = json.loads(response.text.strip())
            
            return result.get('topics', [])
        except Exception as e:
            print(f"⚠️  LLM classification failed: {e}")
            return None
    
    def _build_symbol_aware_prompt(self, text: str) -> str:
        """Build Claude-style prompt for Further Pure Maths"""
        taxonomy = "\n".join([f"- {t['id']} → {t['name']}" 
                            for t in self.config.get('topics', [])])
        
        return f"""You are a precise Edexcel examiner for {self.config['subject']['name']}.
TAG THE WHOLE QUESTION with topics from the taxonomy below and return JSON only.

TAXONOMY:
{taxonomy}

RULES:
1) Whole-question context. Multi-tag allowed.
2) SYMBOL-FIRST: prioritize mathematical symbols/structures over story words.
3) Give confidence in [0,1] for each topic.
4) Include evidence (decisive symbols/patterns).
5) Output JSON only. No prose.

INPUT TEXT:
{text[:3000]}

OUTPUT (JSON only):
{{
  "topics": [
    {{"id": "CALC", "confidence": 0.86, "evidence": ["∫...dx", "dy/dx"]}},
    {{"id": "GRAPHS", "confidence": 0.58, "evidence": ["tangent", "axes present"]}}
  ],
  "methods": ["chain rule"],
  "dominant_ao": "Algebra & calculus",
  "difficulty_hint": "integration followed by tangent gradient"
}}"""
    
    def _build_simple_prompt(self, text: str) -> str:
        """Build simple prompt for Physics-style configs"""
        topics_list = "\n".join([f"{t.get('topic_number', '?')}: {t['name']}" 
                                for t in self.config.get('topics', [])])
        
        return f"""Classify this physics question into ONE topic.

Topics:
{topics_list}

Question text:
{text[:1500]}

Return JSON: {{"topic": "1", "confidence": 0.85, "difficulty": "medium"}}"""
    
    def _extract_methods(self, text: str) -> List[str]:
        """Extract mathematical methods used"""
        if not self.is_symbol_aware:
            return []
        
        methods = []
        methods_catalog = self.config.get('symbol_grammar', {}).get('methods_catalog', {})
        
        text_lower = text.lower()
        for method_name, patterns in methods_catalog.items():
            for pattern in patterns:
                if re.search(pattern, text_lower, re.IGNORECASE):
                    methods.append(method_name)
                    break
        
        return methods
    
    def _get_dominant_ao(self, topic_id: str) -> str:
        """Get dominant assessment objective for topic"""
        if not self.is_symbol_aware:
            return None
        
        ao_mapping = self.config.get('postprocess', {}).get('ao_mapping', {})
        return ao_mapping.get(topic_id, "Algebra & calculus")
    
    def _infer_difficulty(self, text: str, topic_id: str) -> str:
        """Infer question difficulty"""
        text_lower = text.lower()
        
        # Hard indicators
        if any(word in text_lower for word in ['prove', 'hence', 'optimisation', 'product rule', 'quotient rule']):
            return 'hard'
        
        # Easy indicators
        if any(word in text_lower for word in ['calculate', 'find the value', 'evaluate']):
            return 'easy'
        
        return 'medium'


# Backward compatibility wrapper
class SingleTopicClassifier(SymbolAwareClassifier):
    """Wrapper for backward compatibility with existing code"""
    pass
