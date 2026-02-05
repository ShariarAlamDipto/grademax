#!/usr/bin/env python3
"""
Improved Classification Strategy for Mathematics B

Key improvements:
1. Rule-based classification using keyword matching (fast, no API calls)
2. LLM only for ambiguous cases
3. Multi-topic detection within a single question
4. Batch processing to reduce API calls
5. Confidence scoring based on keyword density

This classifier prioritizes:
- Speed: Keywords first, LLM only when needed
- Accuracy: Multiple signals combined
- Completeness: Every question gets classified
"""

import re
import yaml
import os
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from collections import Counter
import fitz
from dotenv import load_dotenv

load_dotenv('.env.local')


@dataclass
class TopicMatch:
    """A potential topic match with confidence score"""
    topic_id: str
    topic_code: str
    topic_name: str
    score: float  # 0-1 confidence
    matched_keywords: List[str]


@dataclass
class ClassificationResult:
    """Final classification for a question"""
    question_number: str
    primary_topic: str
    topic_name: str
    confidence: float
    method: str  # 'keyword', 'llm', 'hybrid'
    all_matches: List[TopicMatch]
    question_text: str


class KeywordClassifier:
    """
    Rule-based classifier using weighted keyword matching
    
    This is the primary classification method - fast and accurate for most questions
    """
    
    def __init__(self, topics_yaml_path: str):
        with open(topics_yaml_path, 'r', encoding='utf-8') as f:
            self.yaml_data = yaml.safe_load(f)
        
        self.topics = self.yaml_data['topics']
        self.precedence = self.yaml_data.get('precedence', [])
        self.thresholds = self.yaml_data.get('thresholds', {})
        
        # Build keyword index with weights
        self.keyword_index = self._build_keyword_index()
        
        # Build phrase patterns for multi-word matching
        self.phrase_patterns = self._build_phrase_patterns()
        
    def _build_keyword_index(self) -> Dict[str, List[Tuple[str, str, float]]]:
        """
        Build index: keyword -> [(topic_id, topic_code, weight), ...]
        
        Single words from phrases are indexed with lower weight
        """
        index = {}
        
        for topic in self.topics:
            topic_id = topic['id']
            topic_code = topic['code']
            
            # Process core keywords (higher weight)
            for item in topic.get('core', []):
                phrase = item['text'].lower()
                weight = item.get('weight', 5) / 5.0  # Normalize to 0-1
                
                # Add full phrase
                if phrase not in index:
                    index[phrase] = []
                index[phrase].append((topic_id, topic_code, weight))
                
                # Add individual words with reduced weight
                words = phrase.split()
                if len(words) > 1:
                    for word in words:
                        if len(word) > 3:  # Skip short words
                            if word not in index:
                                index[word] = []
                            index[word].append((topic_id, topic_code, weight * 0.5))
            
            # Process support keywords (lower weight)
            for item in topic.get('support', []):
                phrase = item['text'].lower()
                weight = item.get('weight', 3) / 5.0 * 0.8  # Support = 80% of core
                
                if phrase not in index:
                    index[phrase] = []
                index[phrase].append((topic_id, topic_code, weight))
                
                words = phrase.split()
                if len(words) > 1:
                    for word in words:
                        if len(word) > 3:
                            if word not in index:
                                index[word] = []
                            index[word].append((topic_id, topic_code, weight * 0.4))
        
        return index
    
    def _build_phrase_patterns(self) -> List[Tuple[re.Pattern, str, str, float]]:
        """Build regex patterns for multi-word phrases"""
        patterns = []
        
        for topic in self.topics:
            topic_id = topic['id']
            topic_code = topic['code']
            
            for item in topic.get('core', []) + topic.get('support', []):
                phrase = item['text'].lower()
                weight = item.get('weight', 4) / 5.0
                
                # Only create patterns for multi-word phrases
                if ' ' in phrase:
                    # Allow some flexibility in matching
                    pattern = re.compile(
                        r'\b' + r'\s+'.join(re.escape(w) for w in phrase.split()) + r'\b',
                        re.IGNORECASE
                    )
                    patterns.append((pattern, topic_id, topic_code, weight))
        
        return patterns
    
    def classify(self, text: str, question_num: str = "") -> ClassificationResult:
        """
        Classify text using keyword matching
        
        Returns classification with confidence score
        """
        text_lower = text.lower()
        
        # Track scores per topic
        topic_scores: Dict[str, float] = {}
        topic_keywords: Dict[str, List[str]] = {}
        
        # 1. Match multi-word phrases first (highest value)
        for pattern, topic_id, topic_code, weight in self.phrase_patterns:
            matches = pattern.findall(text_lower)
            if matches:
                if topic_id not in topic_scores:
                    topic_scores[topic_id] = 0
                    topic_keywords[topic_id] = []
                topic_scores[topic_id] += weight * len(matches)
                topic_keywords[topic_id].extend(matches)
        
        # 2. Match single keywords
        words = set(re.findall(r'\b\w+\b', text_lower))
        for word in words:
            if word in self.keyword_index:
                for topic_id, topic_code, weight in self.keyword_index[word]:
                    if topic_id not in topic_scores:
                        topic_scores[topic_id] = 0
                        topic_keywords[topic_id] = []
                    topic_scores[topic_id] += weight
                    topic_keywords[topic_id].append(word)
        
        # 3. Apply precedence rules
        topic_scores = self._apply_precedence(topic_scores, text_lower)
        
        # 4. Build match list
        matches = []
        for topic_id, score in topic_scores.items():
            topic = next((t for t in self.topics if t['id'] == topic_id), None)
            if topic:
                # Normalize score (cap at 1.0)
                normalized_score = min(1.0, score / 5.0)
                matches.append(TopicMatch(
                    topic_id=topic_id,
                    topic_code=topic['code'],
                    topic_name=topic['name'],
                    score=normalized_score,
                    matched_keywords=topic_keywords.get(topic_id, [])
                ))
        
        # Sort by score
        matches.sort(key=lambda x: x.score, reverse=True)
        
        # Determine result
        if matches and matches[0].score >= 0.3:
            primary = matches[0]
            return ClassificationResult(
                question_number=question_num,
                primary_topic=primary.topic_id,
                topic_name=primary.topic_name,
                confidence=primary.score,
                method='keyword',
                all_matches=matches[:5],
                question_text=text[:200]
            )
        else:
            # No confident match
            return ClassificationResult(
                question_number=question_num,
                primary_topic='',
                topic_name='Unknown',
                confidence=0.0,
                method='keyword',
                all_matches=matches[:5],
                question_text=text[:200]
            )
    
    def _apply_precedence(self, scores: Dict[str, float], text: str) -> Dict[str, float]:
        """Apply precedence rules to resolve conflicts"""
        for rule in self.precedence:
            prefer = rule.get('prefer', '')
            over = rule.get('over', '')
            when_any = rule.get('when_any', [])
            boost = rule.get('boost', 0.05)
            
            # Find topic IDs from codes
            prefer_id = next((t['id'] for t in self.topics if t['code'] == prefer), None)
            over_id = next((t['id'] for t in self.topics if t['code'] == over), None)
            
            if prefer_id and over_id and prefer_id in scores and over_id in scores:
                # Check if any trigger words present
                if any(kw.lower() in text for kw in when_any):
                    scores[prefer_id] += boost * 5  # Boost preferred topic
        
        return scores


class HybridClassifier:
    """
    Combines keyword classification with LLM for difficult cases
    """
    
    def __init__(self, topics_yaml_path: str, groq_api_key: str = None):
        self.keyword_classifier = KeywordClassifier(topics_yaml_path)
        self.groq_api_key = groq_api_key or os.getenv('GROQ_API_KEY')
        self.topics = self.keyword_classifier.topics
        
        # Track statistics
        self.stats = {
            'keyword_only': 0,
            'llm_used': 0,
            'total': 0
        }
    
    def classify(self, text: str, question_num: str = "") -> ClassificationResult:
        """
        Classify using keywords first, LLM only if needed
        """
        self.stats['total'] += 1
        
        # Try keyword classification first
        result = self.keyword_classifier.classify(text, question_num)
        
        # If confidence is reasonable, use keyword result
        # Lower threshold since our keyword matching is good
        if result.confidence >= 0.35:
            self.stats['keyword_only'] += 1
            return result
        
        # If some matches but low confidence, check if there's a clear winner
        if result.all_matches and len(result.all_matches) >= 2:
            gap = result.all_matches[0].score - result.all_matches[1].score
            if gap >= 0.10:  # Clear winner even with low absolute confidence
                self.stats['keyword_only'] += 1
                result.method = 'keyword'
                return result
        
        # Even with low confidence, if we have ANY match, prefer it over LLM
        # to avoid rate limits
        if result.all_matches and result.all_matches[0].score > 0.15:
            self.stats['keyword_only'] += 1
            result.method = 'keyword_low'
            return result
        
        # Need LLM for ambiguous cases
        if self.groq_api_key:
            self.stats['llm_used'] += 1
            return self._classify_with_llm(text, question_num, result.all_matches)
        else:
            # No LLM available, use best keyword match
            self.stats['keyword_only'] += 1
            return result
    
    def _classify_with_llm(self, text: str, question_num: str, 
                          keyword_matches: List[TopicMatch]) -> ClassificationResult:
        """Use LLM for classification when keywords are ambiguous"""
        import requests
        import json
        
        # Build topic list for prompt
        topic_list = "\n".join([
            f"{t['id']}. {t['name']} ({t['code']}): {t.get('description', '')}"
            for t in self.topics
        ])
        
        # Include keyword hints in prompt
        hints = ""
        if keyword_matches:
            hints = "\nKeyword analysis suggests: " + ", ".join([
                f"{m.topic_name} ({m.score:.2f})" for m in keyword_matches[:3]
            ])
        
        prompt = f"""You are classifying a Mathematics B (IGCSE) exam question.

Topics:
{topic_list}

Question text:
{text[:1500]}
{hints}

Respond with ONLY a JSON object:
{{"topic_id": "<number>", "topic_name": "<name>", "confidence": <0.0-1.0>}}"""

        try:
            response = requests.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.groq_api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": "llama-3.1-8b-instant",
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.1,
                    "max_tokens": 100
                },
                timeout=30
            )
            
            if response.status_code == 200:
                content = response.json()['choices'][0]['message']['content']
                # Parse JSON from response
                json_match = re.search(r'\{[^}]+\}', content)
                if json_match:
                    data = json.loads(json_match.group())
                    topic_id = str(data.get('topic_id', ''))
                    topic = next((t for t in self.topics if t['id'] == topic_id), None)
                    
                    if topic:
                        return ClassificationResult(
                            question_number=question_num,
                            primary_topic=topic_id,
                            topic_name=topic['name'],
                            confidence=float(data.get('confidence', 0.8)),
                            method='llm',
                            all_matches=keyword_matches,
                            question_text=text[:200]
                        )
        except Exception as e:
            print(f"      LLM error: {str(e)[:50]}")
        
        # Fall back to keyword result
        if keyword_matches:
            return ClassificationResult(
                question_number=question_num,
                primary_topic=keyword_matches[0].topic_id,
                topic_name=keyword_matches[0].topic_name,
                confidence=keyword_matches[0].score,
                method='keyword_fallback',
                all_matches=keyword_matches,
                question_text=text[:200]
            )
        
        return ClassificationResult(
            question_number=question_num,
            primary_topic='1',
            topic_name='Number',
            confidence=0.1,
            method='default',
            all_matches=[],
            question_text=text[:200]
        )
    
    def get_stats(self) -> Dict:
        """Return classification statistics"""
        return {
            **self.stats,
            'keyword_rate': self.stats['keyword_only'] / max(1, self.stats['total']),
            'llm_rate': self.stats['llm_used'] / max(1, self.stats['total'])
        }


def extract_questions_from_paper(pdf_path: Path) -> List[Tuple[str, str]]:
    """
    Extract all questions from a paper PDF
    
    Returns: [(question_number, question_text), ...]
    """
    doc = fitz.open(str(pdf_path))
    questions = []
    current_q_num = None
    current_q_text = []
    
    for page_num in range(len(doc)):
        page = doc[page_num]
        text = page.get_text()
        lines = text.split('\n')
        
        for line in lines:
            # Detect new question start
            match = re.match(r'^\s*(\d{1,2})\s+[A-Z(]', line)
            if match:
                q_num = match.group(1)
                # Validate it's a reasonable question number
                try:
                    if 1 <= int(q_num) <= 15:
                        # Save previous question
                        if current_q_num and current_q_text:
                            questions.append((current_q_num, '\n'.join(current_q_text)))
                        
                        # Start new question
                        current_q_num = q_num
                        current_q_text = [line]
                        continue
                except ValueError:
                    pass
            
            # Continue current question
            if current_q_num:
                # Skip answer lines and page markers
                if not any(skip in line for skip in ['*P', '......', 'DO NOT WRITE', 'Turn over']):
                    current_q_text.append(line)
    
    # Save last question
    if current_q_num and current_q_text:
        questions.append((current_q_num, '\n'.join(current_q_text)))
    
    doc.close()
    return questions


def test_classifier():
    """Test the improved classifier"""
    topics_yaml = Path(__file__).parent.parent / "classification" / "maths_b_topics.yaml"
    
    print("=" * 70)
    print("Testing Improved Maths B Classifier")
    print("=" * 70)
    
    classifier = HybridClassifier(str(topics_yaml))
    
    # Test questions
    test_cases = [
        ("Q2", "Find the Highest Common Factor (HCF) of 75, 90 and 120. "
               "Find the first time after 09:30 that both alarms will sound at the same time."),
        ("Q3", "Solve the equation 3a + 6 = 4 - 5a. Solve the inequality 3p > 6p + 12."),
        ("Q4", "A, B and C are points on a circle. DE is a tangent to the circle at A. "
               "Angle BAD = 58° and angle ACB = 71°. Work out the size of angle ABC."),
        ("Q5", "The diagram shows a solid cone with base radius 6 cm. "
               "Calculate the total surface area of the cone."),
        ("Q6", "f(x) = 3x - 2 and g(x) = x² + 1. Find fg(2). Find f⁻¹(x)."),
        ("Q7", "A = (2 3; 1 4) and B = (5 -3; -1 2). Calculate AB. Find A⁻¹."),
        ("Q8", "In a Venn diagram, ξ = {students in a class}, A = {students who study Art}. "
               "Find n(A ∩ B)."),
        ("Q9", "OAB is a triangle. OA = a and OB = b. M is the midpoint of AB. "
               "Find OM in terms of a and b."),
        ("Q10", "A ship sails from port P on a bearing of 040° for 12 km to point Q. "
                "Calculate the distance from Q to a lighthouse using the sine rule."),
        ("Q11", "The table shows information about the ages of 80 people. "
                "Find the class interval containing the median. Calculate an estimate of the mean."),
    ]
    
    print("\nClassification Results:")
    print("-" * 70)
    
    for q_num, text in test_cases:
        result = classifier.classify(text, q_num)
        print(f"{q_num}: Topic {result.primary_topic} ({result.topic_name})")
        print(f"     Confidence: {result.confidence:.2f} | Method: {result.method}")
        if result.all_matches:
            top_matches = result.all_matches[:3]
            matches_str = ", ".join([f"{m.topic_code}({m.score:.2f})" for m in top_matches])
            print(f"     Top matches: {matches_str}")
        print()
    
    print("-" * 70)
    stats = classifier.get_stats()
    print(f"Statistics: {stats['keyword_only']}/{stats['total']} keyword-only " +
          f"({stats['keyword_rate']*100:.0f}%), {stats['llm_used']} LLM calls")


if __name__ == "__main__":
    test_classifier()
