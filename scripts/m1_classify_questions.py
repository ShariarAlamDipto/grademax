"""
IAL Mechanics 1 Question Classification using Groq
Classifies questions by topic (M1.1-M1.8) and difficulty using text-based approach
Uses multiple Groq models with HTTP API (following FPM classification pattern)
"""

import os
import json
import time
import requests
from pathlib import Path
from typing import Dict, List, Optional
import pdfplumber
from dotenv import load_dotenv

# Load environment variables
load_dotenv(Path(__file__).parent.parent / ".env.local")

# Groq API configuration
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"

# Model tier system (ordered by speed and capability)
MODELS = [
    "llama-3.1-8b-instant",          # Fast, good for standard questions
    "llama-3.3-70b-versatile",       # Stronger for complex questions  
    "mixtral-8x7b-32768",            # Alternative fast model
]

# M1 Topics (from database)
TOPICS = {
    "M1.1": "Modelling & Assumptions",
    "M1.2": "Vectors in Mechanics",
    "M1.3": "Kinematics",
    "M1.4": "Dynamics",
    "M1.5": "Momentum & Impulse",
    "M1.6": "Friction",
    "M1.7": "Statics of a Particle",
    "M1.8": "Moments"
}

# JSON Schema for classification response
CLASSIFICATION_SCHEMA = {
    "type": "json_schema",
    "json_schema": {
        "name": "question_classification",
        "strict": True,
        "schema": {
            "type": "object",
            "properties": {
                "classification": {
                    "type": "object",
                    "properties": {
                        "topic": {
                            "type": "string",
                            "enum": ["M1.1", "M1.2", "M1.3", "M1.4", "M1.5", "M1.6", "M1.7", "M1.8"]
                        },
                        "difficulty": {
                            "type": "string",
                            "enum": ["easy", "medium", "hard"]
                        },
                        "confidence": {
                            "type": "string",
                            "enum": ["high", "medium", "low"]
                        },
                        "reasoning": {
                            "type": "string"
                        }
                    },
                    "required": ["topic", "difficulty", "confidence", "reasoning"],
                    "additionalProperties": False
                }
            },
            "required": ["classification"],
            "additionalProperties": False
        }
    }
}

# System prompt (comprehensive, based on user's prompt pack)
SYSTEM_PROMPT = """You are an expert examiner for IAL Mechanics 1 (Edexcel). Your task is to classify examination questions by topic and difficulty.

# Topics Reference:

**M1.1 — Modelling & Assumptions**
- Modelling real-world situations as particles, rods, strings
- Stating and justifying assumptions
- Limitations of models
- Using g = 9.8 or 10 m/s²

**M1.2 — Vectors in Mechanics**
- Vector notation (i, j components)
- Magnitude and direction
- Adding/subtracting position vectors
- Vector equations of motion
- Displacement, velocity, acceleration as vectors

**M1.3 — Kinematics**
- Motion in a straight line (SUVAT equations)
- Variable acceleration
- Velocity-time graphs
- Displacement-time graphs
- Vertical motion under gravity
- Projectile motion (2D kinematics)

**M1.4 — Dynamics**
- Newton's laws of motion (F = ma)
- Force diagrams
- Resolving forces
- Motion on horizontal/inclined planes
- Connected particles (strings, pulleys)
- Tension in strings

**M1.5 — Momentum & Impulse**
- Linear momentum (p = mv)
- Conservation of momentum
- Impulse (I = Ft = change in momentum)
- Collisions (elastic/inelastic)
- Newton's experimental law (e = coefficient of restitution)

**M1.6 — Friction**
- Friction force (F ≤ μR)
- Coefficient of friction
- Motion with friction on horizontal/inclined planes
- Limiting equilibrium
- Static vs kinetic friction

**M1.7 — Statics of a Particle**
- Equilibrium conditions (ΣF = 0)
- Forces in equilibrium
- Triangle/polygon of forces
- Lami's theorem
- Resolving forces in equilibrium
- Tension, normal reaction, weight

**M1.8 — Moments**
- Moment of a force (M = Fd)
- Principle of moments (equilibrium: Σclockwise = Σanticlockwise)
- Centre of mass/gravity
- Tilting and toppling
- Non-uniform rods
- Systems in equilibrium

# Difficulty Guidelines:

**Easy:**
- Single concept application
- Direct use of one formula
- Minimal calculation steps
- Clear, straightforward setup

**Medium:**
- Combines 2-3 concepts
- Requires choosing appropriate equations
- Multiple calculation steps
- Some interpretation needed
- Standard exam questions

**Hard:**
- Combines multiple topics
- Complex setup or interpretation
- Multi-step problem solving
- Requires deeper understanding
- Non-standard approach needed
- Challenge questions

# Classification Instructions:

1. Read the question text carefully
2. Identify the PRIMARY topic (the main concept being tested)
3. Assess difficulty based on complexity, not just length
4. Provide confidence based on clarity of topic indicators
5. Give brief reasoning for your classification

# Response Requirements:

- Topic: MUST be one of M1.1 through M1.8
- Difficulty: easy, medium, or hard
- Confidence: high (very clear), medium (mostly clear), or low (ambiguous/multi-topic)
- Reasoning: 1-2 sentences explaining your choice

Be precise and consistent. When questions span multiple topics, choose the PRIMARY topic being assessed."""

def extract_question_text(qp_pdf_path: str, ms_pdf_path: Optional[str] = None) -> Dict[str, str]:
    """Extract text from question paper and mark scheme PDFs"""
    result = {"qp_text": "", "ms_text": ""}
    
    # Extract QP text
    try:
        with pdfplumber.open(qp_pdf_path) as pdf:
            qp_text = "\n".join([page.extract_text() or "" for page in pdf.pages])
            result["qp_text"] = qp_text.strip()
    except Exception as e:
        print(f"   ⚠️  Error extracting QP text: {e}")
    
    # Extract MS text (optional, helps with context)
    if ms_pdf_path and Path(ms_pdf_path).exists():
        try:
            with pdfplumber.open(ms_pdf_path) as pdf:
                ms_text = "\n".join([page.extract_text() or "" for page in pdf.pages])
                result["ms_text"] = ms_text.strip()
        except Exception as e:
            print(f"   ⚠️  Error extracting MS text: {e}")
    
    return result

def classify_question_with_groq(qnum: int, qp_text: str, ms_text: str = "", 
                                model_index: int = 0, max_retries: int = 2) -> Optional[Dict]:
    """
    Classify a question using Groq with JSON schema mode
    Uses model tier system with automatic fallback
    """
    
    if model_index >= len(MODELS):
        print(f"   ❌ All models exhausted for Q{qnum}")
        return None
    
    model = MODELS[model_index]
    
    # Build user message
    topics_list = "\n".join([f"{code} — {desc}" for code, desc in TOPICS.items()])
    
    user_message = f"""Classify this IAL Mechanics 1 exam question:

=== QUESTION {qnum} ===
{qp_text[:2000]}  
{'...(truncated)' if len(qp_text) > 2000 else ''}

Available Topics:
{topics_list}

Provide classification in the required JSON format."""
    
    for attempt in range(max_retries):
        try:
            print(f"   🤖 Attempting classification with {model} (attempt {attempt + 1}/{max_retries})")
            
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_message}
                ],
                response_format=CLASSIFICATION_SCHEMA,
                temperature=0.1,  # Low temperature for consistent classification
                max_tokens=500
            )
            
            # Parse response
            content = response.choices[0].message.content
            result = json.loads(content)
            
            # Validate structure
            if "classification" in result:
                classification = result["classification"]
                required_keys = {"topic", "difficulty", "confidence", "reasoning"}
                if all(k in classification for k in required_keys):
                    # Validate topic code
                    if classification["topic"] in TOPICS:
                        print(f"   ✅ Classified as {classification['topic']} ({classification['difficulty']})")
                        return classification
                    else:
                        print(f"   ⚠️  Invalid topic code: {classification['topic']}")
            
            print(f"   ⚠️  Invalid response structure, retrying...")
            time.sleep(1)
            
        except json.JSONDecodeError as e:
            print(f"   ⚠️  JSON decode error: {e}, retrying...")
            time.sleep(1)
            
        except Exception as e:
            error_msg = str(e)
            
            # Check for rate limit
            if "rate_limit" in error_msg.lower():
                wait_time = 60
                print(f"   ⚠️  Rate limit hit, waiting {wait_time}s...")
                time.sleep(wait_time)
                continue
            
            # Check for model-specific errors
            if "model" in error_msg.lower() or "not available" in error_msg.lower():
                print(f"   ⚠️  Model error: {error_msg}")
                break  # Try next model
            
            print(f"   ⚠️  Error: {error_msg}")
            time.sleep(2)
    
    # If we get here, this model failed - try next model
    print(f"   ⚠️  {model} failed, trying next model...")
    time.sleep(2)
    return classify_question_with_groq(qnum, qp_text, ms_text, model_index + 1, max_retries)

def classify_all_questions(segmented_json_path: str, pages_dir: Path, ms_dir: Path, 
                          output_path: str):
    """Classify all questions from a segmented paper"""
    
    print(f"\n{'='*80}")
    print(f"Classifying questions from: {segmented_json_path}")
    print(f"{'='*80}\n")
    
    # Load segmented data
    with open(segmented_json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    paper_info = data['paper']
    questions = data['questions']
    year = paper_info['year']
    season = paper_info['season']
    paper_num = paper_info['paper_number']
    
    print(f"Paper: {year} {season} {paper_num}")
    print(f"Questions: {len(questions)}\n")
    
    classifications = []
    success_count = 0
    failed_questions = []
    
    for q in questions:
        qnum = q['qnum']
        print(f"\n{'─'*60}")
        print(f"Q{qnum}: Processing...")
        
        # Build file paths
        base_name = f"{year}_{season}_{paper_num}_Q{qnum}"
        qp_path = pages_dir / f"{base_name}.pdf"
        ms_path = ms_dir / f"{base_name}.pdf"
        
        # Check if QP exists
        if not qp_path.exists():
            print(f"   ⚠️  QP PDF not found, skipping")
            failed_questions.append(qnum)
            continue
        
        # Extract text
        texts = extract_question_text(str(qp_path), str(ms_path) if ms_path.exists() else None)
        
        if not texts["qp_text"]:
            print(f"   ⚠️  No text extracted from QP, skipping")
            failed_questions.append(qnum)
            continue
        
        # Classify with Groq
        classification = classify_question_with_groq(
            qnum, 
            texts["qp_text"], 
            texts.get("ms_text", "")
        )
        
        if classification:
            classifications.append({
                "qnum": qnum,
                "topic": classification["topic"],
                "topic_name": TOPICS[classification["topic"]],
                "difficulty": classification["difficulty"],
                "confidence": classification["confidence"],
                "reasoning": classification["reasoning"],
                "marks": q.get("marks_ms"),
                "has_ms": bool(q.get("ms_pages"))
            })
            success_count += 1
        else:
            print(f"   ❌ Classification failed")
            failed_questions.append(qnum)
        
        # Small delay to be respectful to API
        time.sleep(0.5)
    
    # Save results
    output_data = {
        "paper": {
            "year": year,
            "season": season,
            "paper_number": paper_num,
            "subject_code": "WME01"
        },
        "classifications": classifications,
        "summary": {
            "total_questions": len(questions),
            "classified": success_count,
            "failed": len(failed_questions),
            "success_rate": (success_count / len(questions) * 100) if questions else 0,
            "failed_questions": failed_questions
        }
    }
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, indent=2, ensure_ascii=False)
    
    # Print summary
    print(f"\n{'='*80}")
    print("CLASSIFICATION SUMMARY")
    print(f"{'='*80}")
    print(f"✅ Classified: {success_count}/{len(questions)} ({success_count/len(questions)*100:.1f}%)")
    
    if failed_questions:
        print(f"❌ Failed: {failed_questions}")
    
    # Topic distribution
    topic_counts = {}
    for c in classifications:
        topic = c["topic"]
        topic_counts[topic] = topic_counts.get(topic, 0) + 1
    
    if topic_counts:
        print(f"\n📊 Topic Distribution:")
        for topic in sorted(topic_counts.keys()):
            print(f"   {topic} ({TOPICS[topic]}): {topic_counts[topic]} questions")
    
    # Difficulty distribution
    diff_counts = {}
    for c in classifications:
        diff = c["difficulty"]
        diff_counts[diff] = diff_counts.get(diff, 0) + 1
    
    if diff_counts:
        print(f"\n📈 Difficulty Distribution:")
        for diff in ["easy", "medium", "hard"]:
            count = diff_counts.get(diff, 0)
            if count > 0:
                print(f"   {diff.capitalize()}: {count} questions")
    
    print(f"\n💾 Saved to: {output_path}\n")
    
    return output_data

if __name__ == "__main__":
    # Paths
    base_dir = Path(__file__).parent.parent
    processed_dir = base_dir / "data" / "processed" / "Mechanics_1"
    
    # Input files
    segmented_json = processed_dir / "2022_Jan_P1_segmented.json"
    pages_dir = processed_dir / "pages"
    ms_dir = processed_dir / "markschemes"
    
    # Output file
    output_json = processed_dir / "2022_Jan_P1_classified.json"
    
    # Verify Groq API key
    if not os.environ.get("GROQ_API_KEY"):
        print("❌ Error: GROQ_API_KEY environment variable not set!")
        print("Set it with: $env:GROQ_API_KEY='your-api-key'")
        exit(1)
    
    # Run classification
    result = classify_all_questions(
        str(segmented_json),
        pages_dir,
        ms_dir,
        str(output_json)
    )
    
    print("\n✅ Classification complete!")
