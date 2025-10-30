#!/usr/bin/env python3
"""
Enhanced Hybrid Multi-Pass Classification System v2.3 for GradeMax
Improvements:
- Replaced Gemini with Groq Llama 3.1 70B (no rate limits)
- Increased context to 4000 chars for better accuracy
- Added page context extraction for incomplete questions
- Better keyword matching with v2.3 config
- Disambiguation rules and postprocessing
"""

import os
import json
import time
import re
from pathlib import Path
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass
import yaml
import requests
from dotenv import load_dotenv


@dataclass
class Classification:
    question_number: int
    topic: str
    difficulty: str
    confidence: float
    method: str  # "groq_bulk", "groq_refine", "keyword"


class HybridClassifierV23:
    """
    v2.3: Groq-only multi-pass classifier
    - Pass 1: Groq Llama 3.1 70B bulk (10 q/batch, high accuracy)
    - Pass 2: Groq Llama 3.1 70B refine (<0.70 confidence, single)
    - Pass 3: Enhanced keywords with disambiguation
    """
    
    # Physics topics (from v2.3 YAML)
    TOPICS = {
        "1": "MOTION - F=ma, suvat, momentum, moments",
        "2": "ELEC - V=IR, circuits, power, safety",
        "3": "WAVES - v=fλ, optics, EM spectrum, Doppler",
        "4": "ENERGY - efficiency, W=Fd, SHC, thermal",
        "5": "SLG - density, pressure, gas laws, kinetic theory",
        "6": "MAG - fields, motor, induction, transformers",
        "7": "RADIO - α/β/γ, half-life, fission/fusion",
        "8": "SPACE - orbits, redshift, stellar evolution"
    }
    
    # Enhanced v2.3 keywords (simplified - load from YAML in production)
    WEIGHTED_KEYWORDS = {
        # Topic 1: MOTION
        "f=ma": ("1", 5), "v²=u²+2as": ("1", 5), "s=ut+(1/2)at²": ("1", 5),
        "v=u+at": ("1", 5), "p=mv": ("1", 5), "impulse": ("1", 5),
        "terminal velocity": ("1", 5), "resultant force": ("1", 4),
        "moment of a force": ("1", 4), "stopping distance": ("1", 4),
        "acceleration": ("1", 3), "velocity": ("1", 2),
        
        # Topic 2: ELEC
        "v=ir": ("2", 5), "p=iv": ("2", 5), "q=it": ("2", 5),
        "ohm's law": ("2", 5), "series circuit": ("2", 4),
        "parallel circuit": ("2", 4), "resistor": ("2", 4),
        "ammeter": ("2", 4), "voltmeter": ("2", 4),
        "fuse": ("2", 4), "earthing": ("2", 4),
        "current": ("2", 2), "voltage": ("2", 2),
        
        # Topic 3: WAVES
        "v=fλ": ("3", 5), "v=f*λ": ("3", 5), "snell": ("3", 5),
        "critical angle": ("3", 5), "total internal reflection": ("3", 5),
        "refractive index": ("3", 4), "electromagnetic spectrum": ("3", 4),
        "doppler": ("3", 4), "wavelength": ("3", 2),
        
        # Topic 4: ENERGY
        "w=fd": ("4", 5), "efficiency": ("4", 5),
        "specific heat capacity": ("4", 5), "mcδθ": ("4", 5),
        "sankey": ("4", 4), "conduction": ("4", 3),
        "convection": ("4", 3), "radiation": ("4", 3),
        
        # Topic 5: SLG
        "ρ=m/v": ("5", 5), "p=f/a": ("5", 5), "p=ρgh": ("5", 5),
        "boyle": ("5", 5), "kinetic theory": ("5", 4),
        "brownian": ("5", 4), "density": ("5", 4),
        
        # Topic 6: MAG
        "electromagnetic induction": ("6", 5), "transformer": ("6", 5),
        "vp/vs = np/ns": ("6", 5), "fleming": ("6", 4),
        "solenoid": ("6", 4), "motor effect": ("6", 4),
        
        # Topic 7: RADIO
        "alpha": ("7", 5), "beta": ("7", 5), "gamma": ("7", 5),
        "half-life": ("7", 5), "fission": ("7", 4), "fusion": ("7", 4),
        "isotope": ("7", 4), "geiger": ("7", 4),
        
        # Topic 8: SPACE
        "v=2πr/t": ("8", 5), "orbital": ("8", 5), "redshift": ("8", 5),
        "red-shift": ("8", 5), "expanding universe": ("8", 5),
        "hubble": ("8", 5), "stellar evolution": ("8", 4),
        "satellite": ("8", 4),
    }
    
    NEGATIVE_KEYWORDS = [
        "current affairs", "radio button", "waves goodbye",
        "power of attorney", "pressure group", "charge for delivery"
    ]
    
    # Disambiguation rules (v2.3)
    DISAMBIGUATION_RULES = [
        {"prefer": "2", "over": "6", "when_any": ["resistor", "ammeter", "ohm"], "boost": 0.05},
        {"prefer": "7", "over": "8", "when_any": ["half-life", "alpha", "isotope"], "boost": 0.07},
        {"prefer": "3", "over": "8", "when_any": ["snell", "critical angle", "tir"], "boost": 0.07},
        {"prefer": "1", "over": "4", "when_any": ["f=ma", "p=mv", "suvat"], "boost": 0.05},
    ]
    
    def __init__(self, groq_key: str):
        self.groq_key = groq_key
        self.stats = {
            "groq_success": 0,
            "groq_failed": 0,
            "keyword_fallback": 0,
            "total_processed": 0
        }
        
        if groq_key:
            # Groq API with Llama 4 Scout 17B
            self.api_url = "https://api.groq.com/openai/v1/chat/completions"
            self.model = "meta-llama/llama-4-scout-17b-16e-instruct"
            self.rate_limit_delay = 2.5  # 30 RPM = 2 sec/req, use 2.5 for safety
            print("   [OK] Groq API initialized")
            print(f"      - Model: Llama 4 Scout 17B")
            print(f"      - Rate Limit: 30 RPM / 1K RPD (2.5 sec delay)")
        else:
            self.api_url = None
            self.model = None
            self.rate_limit_delay = 0
            print("   [WARN] No API available")
    
    def extract_question_context(self, text: str, max_chars: int = 8000) -> str:
        """
        Extract comprehensive context (8000 chars for full questions)
        Returns full text if under limit, otherwise intelligently truncates
        """
        if not text:
            return ""
        
        # Return full text if under 8000 chars
        if len(text) <= max_chars:
            return text.strip()
        
        # If over limit, extract key parts
        # Extract formulas (both inline and equations)
        equations = re.findall(r'[A-Z]\s*=\s*[A-Za-z0-9\s\+\-\*/\(\)\.]+', text)
        
        # Extract numerical data (values with units)
        values = re.findall(r'\b\d+\.?\d*\s*(?:m/s²?|m/s|kg|N|V|A|Ω|Hz|J|W|Pa|°C|K|mol|eV|T|Bq)\b', text)
        
        # Extract diagram indicators
        diagrams = re.findall(r'(?:diagram|figure|graph|chart|table|circuit|ray)\s+(?:\d+|[A-Z])', text, re.IGNORECASE)
        
        # Extract command words (important for difficulty)
        command_words = re.findall(r'\b(calculate|explain|describe|state|define|suggest|evaluate|design|discuss|compare|determine)\b', text, re.IGNORECASE)
        
        # Build comprehensive context
        summary = f"{text[:7000]}\n\n"  # Main text (7000 chars)
        
        if equations:
            summary += f"FORMULAS: {', '.join(equations[:10])}\n"
        if values:
            summary += f"VALUES: {', '.join(values[:15])}\n"
        if diagrams:
            summary += f"DIAGRAMS: {', '.join(diagrams[:5])}\n"
        if command_words:
            summary += f"COMMANDS: {', '.join(set([w.lower() for w in command_words]))}\n"
        
        return summary[:max_chars]
    
    def classify_batch_groq(self, questions: List[Dict]) -> List[Classification]:
        """Pass 1: Bulk classify with Groq Llama 70B (10 q/batch)"""
        if not self.groq_api:
            return []
        
        topic_list = "\n".join([f"{code}. {desc}" for code, desc in self.TOPICS.items()])
        
        questions_text = "\n\n".join([
            f"Q{q['number']}: {self.extract_question_context(q['text'], 8000)}"
            for q in questions
        ])
        
        prompt = f"""You are an expert Edexcel IGCSE Physics examiner. Classify each question by the PRIMARY physics concept being tested.

READ EACH QUESTION CAREFULLY - They test DIFFERENT topics!

TOPICS (use the exact topic numbers 1-8):
{topic_list}

CLASSIFICATION RULES:
1. Read the ENTIRE question text - don't rush to conclusions
2. Identify the PRIMARY formula/concept being tested
3. Each question tests a DIFFERENT topic - don't default to topic 1 or 2
4. Look for key formulas to identify topics:
   - F=ma, suvat equations, momentum → Topic 1 (MOTION)
   - V=IR, P=IV, circuits, resistance → Topic 2 (ELEC)
   - v=fλ, Snell's law, refraction, EM spectrum → Topic 3 (WAVES)
   - W=Fd, efficiency, specific heat capacity → Topic 4 (ENERGY)
   - Density, pressure, gas laws, particles → Topic 5 (SLG)
   - Magnetic fields, motors, transformers → Topic 6 (MAG)
   - Radioactivity, half-life, nuclear → Topic 7 (RADIO)
   - Space, orbits, stars, cosmology → Topic 8 (SPACE)

DIFFICULTY RULES:
- easy: Recall/define/state, 1-step calculation, direct formula substitution
- medium: Multi-step calculation, explain concept, apply to new context
- hard: Design experiment, evaluate, synthesize multiple concepts, justify

QUESTIONS (READ EACH ONE FULLY):
{questions_text}

Return JSON array ONLY (no markdown, no explanation):
[
  {{"question_number": int, "topic": "1-8", "difficulty": "easy|medium|hard", "confidence": 0.0-1.0}},
  ...
]
"""
        
        try:
            response = requests.post(
                self.groq_api,
                headers={
                    "Authorization": f"Bearer {self.groq_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": self.groq_bulk_model,
                    "messages": [
                        {"role": "system", "content": "You are an expert physics examiner. Output strict JSON only."},
                        {"role": "user", "content": prompt}
                    ],
                    "temperature": 0.1,
                    "max_tokens": 1500
                },
                timeout=60
            )
            
            if response.status_code == 429:
                raise Exception("Rate limit (Groq)")
            
            response.raise_for_status()
            result = response.json()
            content = result['choices'][0]['message']['content']
            
            # Parse JSON (handle both array and object with array)
            parsed = json.loads(content)
            if isinstance(parsed, dict) and 'classifications' in parsed:
                parsed = parsed['classifications']
            elif isinstance(parsed, dict) and 'results' in parsed:
                parsed = parsed['results']
            
            # Convert to Classification objects
            results = []
            for item in parsed:
                topic = str(item['topic'])
                difficulty = item['difficulty']
                confidence = item.get('confidence', 0.85)
                q_num = item['question_number']
                
                results.append(Classification(
                    question_number=q_num,
                    topic=topic,
                    difficulty=difficulty,
                    confidence=confidence,
                    method="groq_bulk"
                ))
                self.stats['groq_bulk_success'] += 1
            
            return results
            
        except Exception as e:
            print(f"      [ERROR] Groq bulk failed: {e}")
            if hasattr(e, 'response') and hasattr(e.response, 'text'):
                print(f"      Response: {e.response.text[:500]}")
            return []
    
    def classify_single_groq(self, question: Dict) -> Optional[Classification]:
        """High accuracy: Classify single question with Groq Llama 4 (full question text)"""
        if not self.api_url:
            return None
        
        topic_list = "\n".join([f"{code}. {desc}" for code, desc in self.TOPICS.items()])
        
        # Send ENTIRE question text - no truncation
        question_text = question['text']
        
        prompt = f"""You are an expert Edexcel IGCSE Physics examiner. Classify this question by the PRIMARY physics concept being tested.

READ THE ENTIRE QUESTION CAREFULLY - including all parts and subquestions - before classifying.

TOPICS (Choose ONE that best fits):
{topic_list}

CLASSIFICATION RULES:
- Topic 1 (Forces & Motion): Newton's laws, speed/velocity/acceleration, forces, momentum, pressure
  Examples: "Calculate the acceleration...", "Explain how forces affect motion...", "velocity-time graph"
  
- Topic 2 (Electricity): Circuits, current, voltage, resistance, power, Ohm's law, charge
  Examples: "Calculate the current in the circuit...", "series/parallel circuits", "resistance calculations"
  
- Topic 3 (Waves): Sound, light, reflection, refraction, electromagnetic spectrum, wave properties
  Examples: "Calculate the frequency...", "Explain refraction...", "wavelength calculations"
  
- Topic 4 (Energy): Energy transfers, work done, power, efficiency, energy resources
  Examples: "Calculate kinetic energy...", "energy transformations", "efficiency calculations"
  
- Topic 5 (Thermal Physics): Temperature, heat transfer, specific heat capacity, gas laws
  Examples: "Calculate the energy needed to heat...", "conduction/convection/radiation", "temperature changes"
  
- Topic 6 (Magnetism & Electromagnetism): Magnetic fields, electromagnets, motors, generators
  Examples: "Explain how an electromagnet works...", "magnetic field lines", "motor effect"
  
- Topic 7 (Radioactivity): Nuclear physics, radiation types, half-life, atomic structure
  Examples: "Calculate half-life...", "alpha/beta/gamma radiation", "nuclear decay"
  
- Topic 8 (Astrophysics): Space, solar system, universe, stars
  Examples: "Explain how stars form...", "planetary motion", "Big Bang theory"

DIFFICULTY RULES:
- easy: Recall/define/state, 1-step calculation, direct formula substitution
- medium: Multi-step problem, explain concept, interpret data/graphs, 2-3 calculations
- hard: Design experiment, evaluate/justify, complex multi-step, synthesize concepts

QUESTION TEXT:
{question_text}

CRITICAL: Look at what is actually being CALCULATED or EXPLAINED:
- If calculating forces/acceleration/speed → Topic 1
- If calculating current/voltage/resistance → Topic 2
- If about waves/light/sound → Topic 3
- If about energy/work/power → Topic 4
- If about heat/temperature → Topic 5
- If about magnets/electromagnets → Topic 6
- If about radiation/nuclear → Topic 7
- If about space/planets/stars → Topic 8

IMPORTANT OUTPUT FORMAT:
- topic: Must be a NUMBER from 1-8 (not text description)
- difficulty: Must be "easy", "medium", or "hard"
- confidence: Must be between 0.0 and 1.0

Return ONLY valid JSON (no markdown, no explanation, no code blocks):
{{"topic": "2", "difficulty": "easy", "confidence": 0.95}}
"""
        
        try:
            headers = {
                "Authorization": f"Bearer {self.groq_key}",
                "Content-Type": "application/json"
            }
            
            response = requests.post(
                self.api_url,
                headers=headers,
                json={
                    "model": self.model,
                    "messages": [
                        {"role": "system", "content": "You are an expert Edexcel IGCSE Physics examiner. Output strict JSON only."},
                        {"role": "user", "content": prompt}
                    ],
                    "temperature": 0.1,
                    "max_tokens": 200
                },
                timeout=30
            )
            
            # Debug logging
            print(f"[Status: {response.status_code}] ", end="", flush=True)
            
            if response.status_code == 429:
                raise Exception("Rate limit")
            
            if response.status_code != 200:
                error_msg = f"{response.status_code}: {response.text[:200]}"
                raise Exception(error_msg)
            
            response.raise_for_status()
            result = response.json()
            content = result['choices'][0]['message']['content']
            
            # Clean JSON from markdown code blocks
            content = content.strip()
            if content.startswith('```json'):
                content = content[7:]
            if content.startswith('```'):
                content = content[3:]
            if content.endswith('```'):
                content = content[:-3]
            content = content.strip()
            
            # Try to parse JSON
            try:
                parsed = json.loads(content)
            except json.JSONDecodeError:
                # If parsing fails, try to extract JSON from text
                import re
                json_match = re.search(r'\{[^}]+\}', content)
                if json_match:
                    parsed = json.loads(json_match.group())
                else:
                    raise Exception(f"Could not parse JSON from: {content[:100]}")
            
            # Extract topic number
            topic = parsed.get('topic', '1')
            if not str(topic).isdigit():
                # Try to map text to number
                topic_text = str(topic).lower()
                if 'electricity' in topic_text or 'circuit' in topic_text:
                    topic = "2"
                elif 'wave' in topic_text or 'light' in topic_text:
                    topic = "3"
                elif 'energy' in topic_text:
                    topic = "4"
                elif 'thermal' in topic_text or 'heat' in topic_text:
                    topic = "5"
                elif 'magnet' in topic_text:
                    topic = "6"
                elif 'radio' in topic_text or 'nuclear' in topic_text:
                    topic = "7"
                elif 'space' in topic_text or 'astro' in topic_text:
                    topic = "8"
                else:
                    topic = "1"
            
            self.stats['groq_success'] += 1
            return Classification(
                question_number=question['number'],
                topic=str(topic),
                difficulty=parsed.get('difficulty', 'medium'),
                confidence=parsed.get('confidence', 0.90),
                method="groq"
            )
            
        except Exception as e:
            print(f"[ERROR: {str(e)[:100]}] ", end="", flush=True)
            return None
    
    def apply_disambiguation(self, topic: str, confidence: float, text: str) -> Tuple[str, float]:
        """Apply v2.3 disambiguation rules"""
        text_lower = text.lower()
        
        for rule in self.DISAMBIGUATION_RULES:
            if topic == rule["over"]:
                # Check if any trigger keywords present
                if any(keyword.lower() in text_lower for keyword in rule["when_any"]):
                    # Boost the preferred topic
                    return rule["prefer"], min(1.0, confidence + rule["boost"])
        
        return topic, confidence
    
    def classify_keyword_fallback(self, question: Dict) -> Classification:
        """Pass 3: Enhanced keyword classification with disambiguation"""
        text = question['text'].lower()
        
        # Check negative keywords
        confidence_penalty = 0.25 if any(neg.lower() in text for neg in self.NEGATIVE_KEYWORDS) else 0.0
        
        topic_scores = {}
        for keyword, (topic, weight) in self.WEIGHTED_KEYWORDS.items():
            if keyword.lower() in text:
                topic_scores[topic] = topic_scores.get(topic, 0) + weight
        
        if not topic_scores:
            # No keywords found - return default
            return Classification(
                question_number=question['number'],
                topic="1",
                difficulty="medium",
                confidence=0.0,
                method="keyword"
            )
        
        best_topic = max(topic_scores, key=topic_scores.get)
        best_score = topic_scores[best_topic]
        
        # Calculate confidence
        base_confidence = min(0.6, best_score / 15.0)
        
        # Apply disambiguation
        best_topic, base_confidence = self.apply_disambiguation(best_topic, base_confidence, text)
        
        # Apply penalty
        confidence = max(0.0, base_confidence - confidence_penalty)
        
        self.stats['keyword_fallback'] += 1
        return Classification(
            question_number=question['number'],
            topic=best_topic,
            difficulty="medium",
            confidence=confidence,
            method="keyword"
        )
    
    def classify_hybrid(self, questions: List[Dict]) -> List[Classification]:
        """
        v2.3 HIGH ACCURACY MODE:
        Uses Groq Llama 4 Scout 17B for all classifications
        Processes one question at a time with FULL text (no truncation)
        Optimized for 30 RPM / 1K RPD rate limits
        """
        results = {}
        
        # HIGH ACCURACY: Use Llama 4 for EVERY question (one at a time, full text)
        if self.api_url:
            print(f"      🎯 High-accuracy classification ({len(questions)} questions)...")
            for i, q in enumerate(questions, 1):
                print(f"         Q{q.get('actual_question_number', q['number'])}: ", end="", flush=True)
                
                # Use Groq with full question text
                groq_result = self.classify_single_groq(q)
                
                if groq_result:
                    results[q['number']] = groq_result
                    self.stats['groq_success'] += 1
                    
                    # Show confidence indicator
                    if groq_result.confidence >= 0.90:
                        icon = "✅"
                    elif groq_result.confidence >= 0.70:
                        icon = "⚠️"
                    else:
                        icon = "❓"
                    
                    print(f"{icon} Topic {groq_result.topic}, {groq_result.difficulty} ({groq_result.confidence:.2f})")
                else:
                    # Fallback to keyword if API fails
                    print("❌ API failed, using keyword...", end=" ", flush=True)
                    keyword_result = self.classify_keyword_fallback(q)
                    results[q['number']] = keyword_result
                    self.stats['groq_failed'] += 1
                    print(f"Topic {keyword_result.topic} ({keyword_result.confidence:.2f})")
                
                # Rate limit delay: 30 RPM = 2 sec/req minimum
                time.sleep(self.rate_limit_delay)
        else:
            # No API - use keyword fallback
            print(f"      🔑 Keyword matching ({len(questions)} questions)...")
            for q in questions:
                keyword_result = self.classify_keyword_fallback(q)
                results[q['number']] = keyword_result
        
        self.stats['total_processed'] += len(questions)
        return [results[q['number']] for q in questions]
    
    def get_stats(self) -> Dict:
        """Get classification statistics"""
        total = max(1, self.stats['total_processed'])
        return {
            **self.stats,
            "keyword_rate": f"{self.stats['keyword_success'] / total * 100:.1f}%",
            "groq_refine_rate": f"{self.stats['groq_refine_success'] / total * 100:.1f}%",
            "groq_failed_rate": f"{self.stats['groq_refine_failed'] / total * 100:.1f}%"
        }


if __name__ == "__main__":
    # Test
    load_dotenv('.env.local')
    
    groq_key = os.getenv('GROQ_API_KEY')
    
    if not groq_key:
        print("❌ Need GROQ_API_KEY in .env.local")
        exit(1)
    
    classifier = HybridClassifierV23(groq_key)
    
    test_questions = [
        {"number": 1, "text": "A circuit contains a 12V battery and a 4Ω resistor. Calculate the current using Ohm's law."},
        {"number": 2, "text": "A wave has frequency 50Hz and wavelength 6m. Calculate its speed using v = fλ."},
        {"number": 3, "text": "Uranium-235 has a half-life of 700 million years. Explain the process of nuclear fission in a reactor."}
    ]
    
    print("\n🧪 Testing v2.3 classifier...\n")
    results = classifier.classify_hybrid(test_questions)
    
    print("\n📊 Results:")
    for r in results:
        print(f"   Q{r.question_number}: Topic {r.topic}, {r.difficulty}, confidence={r.confidence:.2f} (via {r.method})")
    
    print(f"\n📈 Stats: {classifier.get_stats()}")
