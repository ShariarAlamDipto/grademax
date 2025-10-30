#!/usr/bin/env python3
"""
Hybrid Multi-Pass Classification System for GradeMax
- Pass 1: Gemini 2.0 Flash bulk classification (fast, free, 1500 RPM)
- Pass 2: Groq refinement for low confidence (<0.70)
- Pass 3: Improved keyword fallback for failures
"""

import os
import json
import time
import re
from pathlib import Path
from typing import List, Dict, Tuple
from dataclasses import dataclass
import yaml
import requests
from dotenv import load_dotenv

try:
    import google.generativeai as genai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False
    print("⚠️  google-generativeai not installed. Install with: pip install google-generativeai")


@dataclass
class Classification:
    question_number: int
    topic: str
    difficulty: str
    confidence: float
    method: str  # "gemini", "groq", "keyword"


class HybridClassifier:
    """Multi-pass classifier with fallback strategies"""
    
    # Physics topics
    TOPICS = {
        "1": "Forces & Motion (F=ma, momentum, suvat, terminal velocity, weight)",
        "2": "Electricity (V=IR, power, circuits, series/parallel, resistance)",
        "3": "Waves (v=fλ, EM spectrum, reflection, refraction, sound, light)",
        "4": "Energy (efficiency, thermal transfer, KE/PE, conduction/convection)",
        "5": "Matter (density, pressure, gas laws, states, molecular motion)",
        "6": "Magnetism (fields, induction, motors, transformers, generators)",
        "7": "Nuclear (α/β/γ, half-life, fission/fusion, radioactivity)",
        "8": "Astrophysics (orbits, planets, red shift, universe, gravity)"
    }
    
    # Enhanced weighted keywords (v2.2 - Physics specification)
    WEIGHTED_KEYWORDS = {
        # Topic 1: Forces & Motion (core: suvat, Newton's laws, momentum)
        "v = u + at": ("1", 5), "v² = u²": ("1", 5), "suvat": ("1", 5),
        "f=ma": ("1", 5), "f = ma": ("1", 5), "resultant force": ("1", 5),
        "conservation of momentum": ("1", 5), "p = mv": ("1", 5),
        "terminal velocity": ("1", 5), "newton's second law": ("1", 5),
        "momentum": ("1", 4), "impulse": ("1", 4), "deceleration": ("1", 4),
        "velocity-time": ("1", 4), "distance-time": ("1", 4), "acceleration-time": ("1", 4),
        "acceleration": ("1", 3), "velocity": ("1", 3), "displacement": ("1", 3),
        "w = mg": ("1", 4), "area under graph": ("1", 3), "slope": ("1", 2),
        
        # Topic 2: Electricity (core: Ohm's law, circuits, power)
        "v = ir": ("2", 5), "v=ir": ("2", 5), "ohm's law": ("2", 5),
        "p = iv": ("2", 5), "p=iv": ("2", 5), "p = i²r": ("2", 5),
        "e = vit": ("2", 5), "q = it": ("2", 5),
        "series circuit": ("2", 5), "parallel circuit": ("2", 5),
        "potential difference": ("2", 5), "circuit diagram": ("2", 5),
        "ammeter": ("2", 4), "voltmeter": ("2", 4), "resistor": ("2", 4),
        "variable resistor": ("2", 4), "led": ("2", 4), "diode": ("2", 4),
        "resistance": ("2", 3), "current": ("2", 3), "voltage": ("2", 3),
        "battery": ("2", 2), "cell": ("2", 2), "switch": ("2", 2),
        
        # Topic 3: Waves (core: wave equation, optics, sound)
        "v = fλ": ("3", 5), "v=fλ": ("3", 5), "wave equation": ("3", 5),
        "electromagnetic spectrum": ("3", 5), "snell's law": ("3", 5),
        "critical angle": ("3", 5), "total internal reflection": ("3", 5),
        "1/f = 1/u + 1/v": ("3", 5), "ray diagram": ("3", 5),
        "converging lens": ("3", 4), "diverging lens": ("3", 4),
        "principal focus": ("3", 4), "focal length": ("3", 4),
        "refraction": ("3", 4), "reflection": ("3", 4), "diffraction": ("3", 4),
        "double slit": ("3", 4), "interference": ("3", 4), "young's": ("3", 4),
        "wavelength": ("3", 3), "frequency": ("3", 3), "amplitude": ("3", 3),
        "sound wave": ("3", 3), "speed of sound": ("3", 3),
        "crest": ("3", 2), "trough": ("3", 2), "phase": ("3", 2),
        
        # Topic 4: Energy (core: work, power, efficiency, thermal)
        "w = fd": ("4", 5), "ek = ½mv²": ("4", 5), "ep = mgh": ("4", 5),
        "efficiency": ("4", 5), "sankey diagram": ("4", 5),
        "q = mcδt": ("4", 5), "q = ml": ("4", 5),
        "specific heat capacity": ("4", 5), "specific latent heat": ("4", 5),
        "kinetic energy": ("4", 4), "potential energy": ("4", 4),
        "useful energy": ("4", 4), "thermal conductivity": ("4", 4),
        "conduction": ("4", 3), "convection": ("4", 3), "radiation": ("4", 3),
        "insulation": ("4", 3), "energy transfer": ("4", 3),
        "renewable": ("4", 2), "fossil": ("4", 2), "solar": ("4", 2),
        
        # Topic 5: Matter (core: density, pressure, gas laws)
        "ρ = m/v": ("5", 5), "density = m/v": ("5", 5),
        "p = f/a": ("5", 5), "p = ρgh": ("5", 5),
        "pv = constant": ("5", 5), "boyle's law": ("5", 5),
        "v/t = constant": ("5", 5), "charles's law": ("5", 5),
        "brownian motion": ("5", 5), "kinetic theory": ("5", 5),
        "density": ("5", 4), "pressure": ("5", 4), "gas law": ("5", 4),
        "molecule": ("5", 3), "particle": ("5", 3), "random motion": ("5", 3),
        "solid": ("5", 2), "liquid": ("5", 2), "gas": ("5", 2),
        "volume": ("5", 2), "temperature": ("5", 2),
        
        # Topic 6: Magnetism (core: motors, induction, transformers)
        "f = bil": ("6", 5), "fleming's left": ("6", 5),
        "electromagnetic induction": ("6", 5), "faraday": ("6", 5),
        "vp/vs = np/ns": ("6", 5), "transformer": ("6", 5),
        "primary coil": ("6", 5), "secondary coil": ("6", 5),
        "magnetic field": ("6", 4), "motor": ("6", 4), "generator": ("6", 4),
        "electromagnet": ("6", 4), "solenoid": ("6", 4), "soft iron": ("6", 4),
        "induced emf": ("6", 4), "induced current": ("6", 4),
        "flux": ("6", 3), "coil": ("6", 3), "lenz": ("6", 4),
        "ac": ("6", 3), "alternating current": ("6", 3),
        
        # Topic 7: Nuclear (core: radioactivity, half-life, nuclear equations)
        "alpha particle": ("7", 5), "beta particle": ("7", 5), "gamma ray": ("7", 5),
        "half-life": ("7", 5), "fission": ("7", 5), "fusion": ("7", 5),
        "radioactive decay": ("7", 5), "nuclear equation": ("7", 5),
        "geiger": ("7", 5), "count rate": ("7", 5),
        "background radiation": ("7", 4), "activity": ("7", 4),
        "isotope": ("7", 4), "nuclide": ("7", 4),
        "alpha": ("7", 3), "beta": ("7", 3), "gamma": ("7", 3),
        "radioactive": ("7", 3), "nuclear": ("7", 3), "decay": ("7", 2),
        
        # Topic 8: Astrophysics (core: orbits, redshift, Big Bang)
        "red shift": ("8", 5), "redshift": ("8", 5), "big bang": ("8", 5),
        "expanding universe": ("8", 5), "cosmic microwave background": ("8", 5),
        "v = 2πr/t": ("8", 5), "orbital speed": ("8", 5),
        "geostationary": ("8", 5), "doppler": ("8", 5),
        "solar system": ("8", 4), "satellite": ("8", 4), "orbit": ("8", 4),
        "planet": ("8", 4), "gravity field": ("8", 4), "hubble": ("8", 4),
        "star": ("8", 3), "moon": ("8", 2), "sun": ("8", 2), "earth": ("8", 2),
    }
    
    # Negative keywords (avoid false positives)
    NEGATIVE_KEYWORDS = [
        "current affairs",      # avoid ELEC false positive
        "radio button",         # avoid RADIO false positive
        "power of attorney",    # avoid ENERGY 'power' generic
        "pressure group",       # avoid SLG 'pressure'
        "waves goodbye",        # avoid WAVES false positive
    ]
    
    def __init__(self, gemini_key: str = None, groq_key: str = None):
        self.gemini_key = gemini_key
        self.groq_key = groq_key
        self.stats = {
            "gemini_success": 0,
            "groq_success": 0,
            "keyword_fallback": 0,
            "total_processed": 0
        }
        
        # Initialize Gemini if available
        if GEMINI_AVAILABLE and gemini_key:
            genai.configure(api_key=gemini_key)
            self.gemini_model = genai.GenerativeModel('gemini-2.0-flash-exp')
            print("   ✅ Gemini 2.0 Flash initialized")
        else:
            self.gemini_model = None
            print("   ⚠️  Gemini not available")
        
        # Groq setup
        if groq_key:
            self.groq_api = "https://api.groq.com/openai/v1/chat/completions"
            self.groq_model = "llama-3.1-8b-instant"
            print("   ✅ Groq API initialized")
        else:
            self.groq_api = None
            print("   ⚠️  Groq not available")
    
    def extract_question_summary(self, text: str, max_chars: int = 400) -> str:
        """Extract key information for compact classification"""
        text = text[:2000]  # Limit input
        
        # Extract equations
        equations = re.findall(r'\b[A-Z]\s*=\s*[A-Za-z0-9\s\+\-\*/\(\)]+', text)
        
        # Extract units
        units = re.findall(r'\b(m/s²?|m/s|kg|N|V|A|Ω|Hz|J|W|Pa|°C|K|mol|eV)\b', text)
        
        # Extract numbers with units (likely given values)
        values = re.findall(r'\b\d+\.?\d*\s*(?:m/s²?|m/s|kg|N|V|A|Ω|Hz|J|W|Pa|°C)\b', text)
        
        # Get first sentence
        sentences = re.split(r'[.!?]\s+', text)
        first_sentence = sentences[0][:200] if sentences else text[:200]
        
        summary = f"{first_sentence}. "
        if equations:
            summary += f"Equations: {', '.join(equations[:2])}. "
        if values:
            summary += f"Values: {', '.join(values[:3])}. "
        if units:
            summary += f"Units: {', '.join(set(units))}."
        
        return summary[:max_chars]
    
    def classify_batch_gemini(self, questions: List[Dict]) -> List[Classification]:
        """Pass 1: Bulk classify with Gemini (20 questions per request)"""
        if not self.gemini_model:
            return []
        
        # Build compact batch prompt
        topic_list = "\n".join([f"{code}. {desc}" for code, desc in self.TOPICS.items()])
        
        questions_text = "\n\n".join([
            f"Q{q['number']}: {self.extract_question_summary(q['text'])}"
            for q in questions
        ])
        
        prompt = f"""Classify these IGCSE Physics questions by topic and difficulty.

TOPICS:
{topic_list}

DIFFICULTY:
- easy: Recall, define, state, simple 1-step calculation
- medium: Multi-step, explain, interpret graphs, apply concepts
- hard: Design experiment, evaluate, synthesize 3+ concepts, derive

QUESTIONS:
{questions_text}

Return JSON array ONLY (no markdown):
[
  {{"question_number": int, "topic": "1-8", "difficulty": "easy/medium/hard", "confidence": 0.0-1.0}},
  ...
]

Focus on PRIMARY physics concept tested (formulas, calculations, principles)."""

        try:
            response = self.gemini_model.generate_content(
                prompt,
                generation_config=genai.GenerationConfig(
                    temperature=0.1,
                    max_output_tokens=800
                )
            )
            
            # Parse response
            content = response.text.strip()
            
            # Remove markdown if present
            if content.startswith('```'):
                json_match = re.search(r'```(?:json)?\s*(.*?)\s*```', content, re.DOTALL)
                if json_match:
                    content = json_match.group(1)
            
            parsed = json.loads(content)
            
            # Convert to Classification objects
            results = []
            for item in parsed:
                results.append(Classification(
                    question_number=item['question_number'],
                    topic=str(item['topic']),
                    difficulty=item['difficulty'],
                    confidence=item.get('confidence', 0.8),
                    method="gemini"
                ))
                self.stats['gemini_success'] += 1
            
            return results
            
        except Exception as e:
            print(f"      ❌ Gemini batch failed: {e}")
            return []
    
    def classify_single_groq(self, question: Dict) -> Classification:
        """Pass 2: Refine single question with Groq"""
        if not self.groq_api:
            return None
        
        topic_list = "\n".join([f"{code}. {desc}" for code, desc in self.TOPICS.items()])
        
        prompt = f"""Classify this IGCSE Physics question.

TOPICS:
{topic_list}

DIFFICULTY:
- easy: Recall/define, 1-step calc, state a fact
- medium: Multi-step, explain concept, interpret data
- hard: Design/evaluate, synthesize, complex reasoning

QUESTION:
{question['text'][:2000]}

Return JSON only:
{{"topic": "1-8", "difficulty": "easy/medium/hard", "confidence": 0.0-1.0}}"""

        try:
            response = requests.post(
                self.groq_api,
                headers={
                    "Authorization": f"Bearer {self.groq_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": self.groq_model,
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.1,
                    "max_tokens": 200,
                    "response_format": {"type": "json_object"}
                },
                timeout=30
            )
            
            if response.status_code == 429:
                raise Exception("Rate limit")
            
            response.raise_for_status()
            result = response.json()
            content = result['choices'][0]['message']['content']
            parsed = json.loads(content)
            
            self.stats['groq_success'] += 1
            return Classification(
                question_number=question['number'],
                topic=str(parsed['topic']),
                difficulty=parsed['difficulty'],
                confidence=parsed.get('confidence', 0.9),
                method="groq"
            )
            
        except Exception as e:
            return None
    
    def classify_keyword_fallback(self, question: Dict) -> Classification:
        """Pass 3: Enhanced keyword-based classification (v2.2) with confidence scoring"""
        text = question['text'].lower()
        
        # Check for negative keywords (false positive indicators)
        has_negative = any(neg.lower() in text for neg in self.NEGATIVE_KEYWORDS)
        if has_negative:
            confidence_penalty = 0.2
        else:
            confidence_penalty = 0.0
        
        topic_scores = {}
        total_weight = 0
        matches_found = []
        
        for keyword, (topic, weight) in self.WEIGHTED_KEYWORDS.items():
            if keyword.lower() in text:
                topic_scores[topic] = topic_scores.get(topic, 0) + weight
                total_weight += weight
                matches_found.append((keyword, topic, weight))
        
        if not topic_scores:
            # No matches - default to topic 1 with zero confidence
            self.stats['keyword_fallback'] += 1
            return Classification(
                question_number=question['number'],
                topic="1",
                difficulty="medium",
                confidence=0.0,
                method="keyword"
            )
        
        best_topic = max(topic_scores, key=topic_scores.get)
        best_score = topic_scores[best_topic]
        second_best_score = sorted(topic_scores.values(), reverse=True)[1] if len(topic_scores) > 1 else 0
        
        # Enhanced confidence calculation (v2.2)
        # Base confidence from score strength (max 0.5 for keywords)
        base_confidence = min(0.5, best_score / 15.0)
        
        # Boost if best topic is significantly higher than second best (clear winner)
        if second_best_score > 0:
            score_ratio = best_score / second_best_score
            if score_ratio > 2.0:
                base_confidence += 0.1
        
        # Apply negative keyword penalty
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
        Multi-pass classification:
        1. Try Gemini batch (fast, free)
        2. Refine low confidence with Groq
        3. Keyword fallback for failures
        """
        results = {}  # question_number -> Classification
        
        # Pass 1: Gemini bulk classification
        if self.gemini_model:
            print(f"      📦 Gemini batch ({len(questions)} questions)...", end=" ", flush=True)
            batch_results = self.classify_batch_gemini(questions)
            
            for result in batch_results:
                results[result.question_number] = result
            
            print(f"✅ {len(batch_results)} classified")
            time.sleep(1.0)  # Rate limit buffer
        
        # Pass 2: Groq refinement for low confidence or missing
        low_confidence = [
            q for q in questions 
            if q['number'] not in results or results[q['number']].confidence < 0.70
        ]
        
        if low_confidence and self.groq_api:
            print(f"      🔄 Groq refinement ({len(low_confidence)} questions)...")
            for q in low_confidence:
                groq_result = self.classify_single_groq(q)
                if groq_result and groq_result.confidence > results.get(q['number'], Classification(0, "1", "medium", 0.0, "none")).confidence:
                    results[q['number']] = groq_result
                    print(f"         Q{q['number']}: ✅ Topic {groq_result.topic} ({groq_result.confidence:.2f})")
                time.sleep(2.0)  # Groq rate limit
        
        # Pass 3: Keyword fallback for any remaining
        for q in questions:
            if q['number'] not in results:
                keyword_result = self.classify_keyword_fallback(q)
                results[q['number']] = keyword_result
                print(f"         Q{q['number']}: ⚠️  Keyword fallback (Topic {keyword_result.topic}, {keyword_result.confidence:.2f})")
        
        return [results[q['number']] for q in questions]
    
    def get_stats(self) -> Dict:
        """Get classification statistics"""
        return {
            **self.stats,
            "gemini_rate": f"{self.stats['gemini_success'] / max(1, self.stats['total_processed']) * 100:.1f}%",
            "groq_rate": f"{self.stats['groq_success'] / max(1, self.stats['total_processed']) * 100:.1f}%",
            "keyword_rate": f"{self.stats['keyword_fallback'] / max(1, self.stats['total_processed']) * 100:.1f}%"
        }


if __name__ == "__main__":
    # Test with sample questions
    load_dotenv('.env.local')
    
    gemini_key = os.getenv('GEMINI_API_KEY')
    groq_key = os.getenv('GROQ_API_KEY')
    
    if not gemini_key and not groq_key:
        print("❌ Need at least one API key (GEMINI_API_KEY or GROQ_API_KEY)")
        exit(1)
    
    classifier = HybridClassifier(gemini_key, groq_key)
    
    test_questions = [
        {"number": 1, "text": "Calculate the current in a circuit with voltage 12V and resistance 4Ω using Ohm's law."},
        {"number": 2, "text": "A wave has frequency 50Hz and wavelength 6m. Calculate its speed using v = fλ."},
        {"number": 3, "text": "Describe the process of nuclear fission and explain how it releases energy in a nuclear reactor."}
    ]
    
    print("\n🧪 Testing hybrid classifier...\n")
    results = classifier.classify_hybrid(test_questions)
    
    print("\n📊 Results:")
    for r in results:
        print(f"   Q{r.question_number}: Topic {r.topic}, {r.difficulty}, confidence={r.confidence:.2f} (via {r.method})")
    
    print(f"\n📈 Stats: {classifier.get_stats()}")
