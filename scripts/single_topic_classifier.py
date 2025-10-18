#!/usr/bin/env python3
"""
Simple Single-Topic Classifier for GradeMax
ONE question → ONE topic
"""

import os
import json
import time
from pathlib import Path
from typing import Dict
from dataclasses import dataclass
import yaml

import google.generativeai as genai
from google.generativeai import types
from google.generativeai.protos import Schema, Type


@dataclass
class TopicClassification:
    """ONE topic per question"""
    page_has_question: bool
    topic: str  # Single topic code ("1", "2", etc.)
    difficulty: str  # "easy", "medium", "hard"
    confidence: float


class SingleTopicClassifier:
    """Classifies questions with ONE primary topic only"""
    
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
    
    def __init__(self, topics_yaml_path: str, api_key: str):
        """Initialize classifier"""
        self.topics = self._load_topics(topics_yaml_path)
        self.topic_codes = [t['code'] for t in self.topics]
        
        # Configure Gemini
        genai.configure(api_key=api_key)
        # Use gemini-2.5-flash for production - latest stable Flash model
        # Balanced: Good speed + quality with high rate limits
        self.model = genai.GenerativeModel('gemini-2.5-flash')
        
        # Build schema
        self.schema = Schema(
            type=Type.OBJECT,
            properties={
                'page_has_question': Schema(
                    type=Type.BOOLEAN,
                    description="True if page has a question"
                ),
                'topic': Schema(
                    type=Type.STRING,
                    description="Single PRIMARY topic code",
                    enum=self.topic_codes
                ),
                'difficulty': Schema(
                    type=Type.STRING,
                    description="easy, medium, or hard",
                    enum=['easy', 'medium', 'hard']
                ),
                'confidence': Schema(
                    type=Type.NUMBER,
                    description="Confidence 0.0-1.0"
                )
            },
            required=['page_has_question', 'topic', 'difficulty', 'confidence']
        )
        
        self.last_call_time = 0
        self.min_delay = 4.5  # 15 RPM = 4 second delay
    
    def _load_topics(self, yaml_path: str):
        """Load topics from YAML"""
        with open(yaml_path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
        return data['topics']
    
    def _wait_for_rate_limit(self):
        """Ensure we don't exceed 15 RPM"""
        now = time.time()
        elapsed = now - self.last_call_time
        if elapsed < self.min_delay:
            time.sleep(self.min_delay - elapsed)
        self.last_call_time = time.time()
    
    def classify(self, page_text: str, question_num: str = None) -> TopicClassification:
        """
        Classify ONE page with ONE topic
        
        Args:
            page_text: Extracted text from PDF page
            question_num: Question number for logging
        
        Returns:
            TopicClassification with single topic
        """
        self._wait_for_rate_limit()
        
        # Build enhanced topic list with textbook context
        topic_descriptors = {
            "1": "Forces and Motion – motion graphs, speed, velocity, acceleration, force = ma, momentum, terminal velocity, weight",
            "2": "Electricity – current, voltage, potential difference, resistance, Ohm's law, series/parallel circuits, power, energy = VIt",
            "3": "Waves – sound, light, reflection, refraction, diffraction, electromagnetic spectrum, wave equation v = fλ",
            "4": "Energy Transfers – kinetic/potential energy, efficiency, conduction/convection/radiation, insulation, thermal energy",
            "5": "Solids/Liquids/Gases – density, pressure = F/A, gas laws (pV = k), temperature, heat transfer, molecular motion",
            "6": "Magnetism and Electromagnetism – magnetic fields, induced currents, motors, transformers, generators, flux",
            "7": "Radioactivity and Particles – alpha/beta/gamma decay, half-life, fission vs fusion, radiation hazards, nuclear energy",
            "8": "Astrophysics – solar system, orbits, planets, red shift, expansion of universe, gravitational forces, satellites"
        }
        
        topic_list = "\n".join([
            f"{code}. {topic_descriptors[code]}"
            for code in sorted(topic_descriptors.keys())
        ])
        
        prompt = f"""You are classifying IGCSE Physics exam questions by topic.
Below are all valid topic codes and their detailed descriptors based on the Edexcel 2017 specification:

{topic_list}

INSTRUCTIONS:
• Identify which topic best matches this question (return ONE primary topic).
• Base your choice strictly on the physics concepts being tested, not just vocabulary overlap.
• Consider the equations, units, and physical principles mentioned.
• If sub-questions test different topics, choose the DOMINANT one.
• Return JSON conforming to the schema.

Question Page:
```
{page_text[:2500]}
```

Return JSON with:
- page_has_question: true if this page contains an actual question (false if blank/cover/instructions)
- topic: single topic code (e.g., "1", "2", "3")
- difficulty: "easy" (basic recall/simple calc), "medium" (multi-step/application), or "hard" (complex/synthesis)
- confidence: 0.0-1.0 (how certain you are about the topic classification)
"""
        
        try:
            response = self.model.generate_content(
                contents=[prompt],
                generation_config=types.GenerationConfig(
                    temperature=0,
                    response_mime_type='application/json',
                    response_schema=self.schema
                )
            )
            
            result = json.loads(response.text)
            
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
                    print(f"   ⚠️  Low confidence ({classification.confidence:.2f}), keyword suggests topic {keyword_topic}")
                    # Keep Gemini's choice but log the discrepancy
            
            return classification
            
        except Exception as e:
            print(f"❌ Classification error: {e}")
            # Try keyword fallback
            keyword_topic = self._keyword_check(page_text.lower())
            return TopicClassification(
                page_has_question=True,
                topic=keyword_topic if keyword_topic else '1',
                difficulty='medium',
                confidence=0.3 if keyword_topic else 0.0
            )
    
    def _keyword_check(self, text: str) -> str:
        """Check for keyword matches to suggest a topic"""
        topic_scores = {}
        
        for keyword, topic in self.KEYWORD_MAP.items():
            if keyword in text:
                topic_scores[topic] = topic_scores.get(topic, 0) + 1
        
        if not topic_scores:
            return None
        
        # Return topic with most keyword matches
        return max(topic_scores, key=topic_scores.get)


# Simple test
if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python single_topic_classifier.py <topics_yaml_path>")
        sys.exit(1)
    
    api_key = os.getenv('GEMINI_API_KEY')
    if not api_key:
        print("❌ GEMINI_API_KEY not set!")
        sys.exit(1)
    
    classifier = SingleTopicClassifier(sys.argv[1], api_key)
    
    # Test classification
    test_text = """
    Question 1
    
    A car accelerates from rest to 30 m/s in 5 seconds.
    
    (a) Calculate the acceleration of the car.
    (b) Calculate the distance travelled.
    """
    
    result = classifier.classify(test_text, "Q1")
    print(f"\nTest Classification:")
    print(f"  Topic: {result.topic}")
    print(f"  Difficulty: {result.difficulty}")
    print(f"  Confidence: {result.confidence}")
