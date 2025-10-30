#!/usr/bin/env python3
"""
Re-classify difficulty levels for all pages using Gemini
Focus ONLY on difficulty assessment with better prompts
"""

import os
import sys
import time
from pathlib import Path
from dotenv import load_dotenv
from supabase import create_client, Client
import requests
import fitz  # PyMuPDF
import google.generativeai as genai
import json
import re

# Load environment
env_path = Path(__file__).parent.parent / '.env.local'
load_dotenv(env_path)

# Initialize Supabase
url = os.getenv('NEXT_PUBLIC_SUPABASE_URL')
service_key = os.getenv('SUPABASE_SERVICE_ROLE_KEY')
gemini_key = os.getenv('GEMINI_API_KEY')

if not url or not service_key or not gemini_key:
    print("❌ Missing credentials!")
    exit(1)

supabase: Client = create_client(url, service_key)
genai.configure(api_key=gemini_key)
model = genai.GenerativeModel('gemini-2.0-flash-exp')


def download_and_extract_text(url: str) -> str:
    """Download PDF and extract text"""
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        pdf_bytes = response.content
        
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        text = ""
        for page in doc:
            text += page.get_text()
        doc.close()
        
        return text
    except Exception as e:
        return ""


def extract_summary(text: str) -> str:
    """Extract key info for difficulty assessment"""
    # Get first 500 chars
    summary = text[:500]
    
    # Count command words
    easy_words = ["define", "state", "name", "label", "what is", "give"]
    medium_words = ["calculate", "explain", "describe", "compare", "show"]
    hard_words = ["design", "plan", "evaluate", "suggest why", "explain why", "devise"]
    
    # Check for marks (indicator of complexity)
    marks = re.findall(r'\[(\d+)\s*marks?\]', text.lower())
    
    context = {
        "text": summary,
        "marks": marks[0] if marks else None,
        "has_easy_words": any(w in text.lower() for w in easy_words),
        "has_medium_words": any(w in text.lower() for w in medium_words),
        "has_hard_words": any(w in text.lower() for w in hard_words),
        "has_subparts": text.count('(a)') > 0 or text.count('(i)') > 0
    }
    
    return context


def classify_difficulty_batch(questions: list) -> dict:
    """Classify difficulty for a batch of questions"""
    
    # Build questions text with summaries
    questions_text = "\n\n".join([
        f"Q{q['number']}: {q['text'][:400]}..."
        for q in questions
    ])
    
    prompt = f"""You are an expert IGCSE Physics examiner. Assess the difficulty of these questions.

DIFFICULTY CRITERIA (be strict and distribute evenly):

**EASY (20-25% of questions should be easy):**
- Single command word: Define, State, Name, Label, List
- Direct recall of facts or definitions
- Simple 1-step calculation with ALL values given
- Examples: "Define velocity", "State the unit of force", "Calculate F=ma given F=10N, a=5m/s²"

**MEDIUM (50-60% of questions should be medium):**
- Multi-step calculations (use result from part a in part b)
- Explain, Describe, Compare concepts
- Interpret graphs or data tables
- Apply knowledge to familiar contexts
- Examples: "Calculate speed using distance and time, then calculate kinetic energy", "Explain how a transformer works"

**HARD (20-25% of questions should be hard):**
- Design or plan an investigation/experiment
- Evaluate methods or suggest improvements
- Apply to unfamiliar contexts
- Combine 3+ concepts or formulas
- Derive or rearrange complex formulas
- Examples: "Design an experiment to test...", "Explain why method X is more accurate than Y", "Suggest improvements to the apparatus"

IMPORTANT: Do NOT default everything to medium. Look at the actual cognitive demand. Simple recall = easy. Multi-step or explanation = medium. Design/evaluate = hard.

QUESTIONS:
{questions_text}

Return ONLY a JSON array:
[
  {{"question_number": "1", "difficulty": "easy", "reasoning": "simple definition"}},
  {{"question_number": "2", "difficulty": "hard", "reasoning": "requires designing experiment"}}
]"""

    try:
        response = model.generate_content(
            prompt,
            generation_config=genai.GenerationConfig(
                temperature=0.2,
                max_output_tokens=1000
            )
        )
        
        content = response.text.strip()
        
        # Remove markdown
        if content.startswith('```'):
            content = re.sub(r'```json?\s*|\s*```', '', content).strip()
        
        parsed = json.loads(content)
        
        # Convert to dict
        results = {}
        for item in parsed:
            results[str(item['question_number'])] = {
                'difficulty': item['difficulty'],
                'reasoning': item.get('reasoning', '')
            }
        
        return results
        
    except Exception as e:
        print(f"      ❌ Error: {e}")
        return {}


def chunks(lst, n):
    """Split list into chunks"""
    for i in range(0, len(lst), n):
        yield lst[i:i + n]


def main():
    print("=" * 70)
    print("🎯 RE-CLASSIFY DIFFICULTY LEVELS")
    print("=" * 70)
    print()
    print("This will re-assess difficulty for all Physics pages using Gemini.")
    print("Goal: More balanced distribution (20% easy, 60% medium, 20% hard)")
    print()
    
    # Load all pages
    print("1️⃣  Loading Physics pages...")
    pages_result = supabase.table('pages').select('*').eq('is_question', True).execute()
    pages = pages_result.data
    
    print(f"   ✅ Found {len(pages)} pages")
    print()
    
    # Current distribution
    from collections import Counter
    current_diff = Counter(p.get('difficulty') for p in pages)
    print(f"📊 Current difficulty distribution:")
    print(f"   Easy: {current_diff.get('easy', 0)} ({current_diff.get('easy', 0)/len(pages)*100:.1f}%)")
    print(f"   Medium: {current_diff.get('medium', 0)} ({current_diff.get('medium', 0)/len(pages)*100:.1f}%)")
    print(f"   Hard: {current_diff.get('hard', 0)} ({current_diff.get('hard', 0)/len(pages)*100:.1f}%)")
    print()
    
    response = input("   Proceed with re-classification? (yes/no): ").strip().lower()
    if response != 'yes':
        print("\n   ❌ Cancelled")
        return
    
    # Download PDFs
    print("\n2️⃣  Downloading PDFs...")
    questions = []
    for i, page in enumerate(pages):
        if (i + 1) % 50 == 0:
            print(f"   📥 {i + 1}/{len(pages)}...")
        
        text = download_and_extract_text(page['qp_page_url'])
        if text and len(text.strip()) > 20:
            questions.append({
                'page_id': page['id'],
                'number': page['question_number'],
                'text': text
            })
    
    print(f"   ✅ {len(questions)} pages ready")
    print()
    
    # Classify in batches
    print("3️⃣  Re-classifying difficulty levels...")
    batch_size = 20
    updated = 0
    failed = 0
    start_time = time.time()
    
    for i, batch in enumerate(chunks(questions, batch_size)):
        batch_num = i + 1
        total_batches = (len(questions) + batch_size - 1) // batch_size
        
        print(f"   📦 Batch {batch_num}/{total_batches} ({len(batch)} questions)...", end=" ", flush=True)
        
        results = classify_difficulty_batch(batch)
        
        if results:
            for q in batch:
                if q['number'] in results:
                    difficulty = results[q['number']]['difficulty']
                    try:
                        supabase.table('pages').update({
                            'difficulty': difficulty
                        }).eq('id', q['page_id']).execute()
                        updated += 1
                    except Exception as e:
                        failed += 1
            
            print(f"✅ {len(results)} updated")
        else:
            print("❌ Failed")
            failed += len(batch)
        
        # Rate limit
        time.sleep(1.0)
        
        # Progress every 10 batches
        if batch_num % 10 == 0:
            elapsed = time.time() - start_time
            rate = updated / elapsed if elapsed > 0 else 0
            remaining = (len(questions) - updated) / rate if rate > 0 else 0
            print(f"\n      ⏱️  Progress: {updated}/{len(questions)} | {elapsed/60:.1f}min | ~{remaining/60:.1f}min remaining\n")
    
    elapsed = time.time() - start_time
    
    # Get new distribution
    pages_result = supabase.table('pages').select('difficulty').eq('is_question', True).execute()
    pages = pages_result.data
    new_diff = Counter(p.get('difficulty') for p in pages)
    
    print("\n" + "=" * 70)
    print("✅ RE-CLASSIFICATION COMPLETE!")
    print("=" * 70)
    print()
    print(f"📊 Results:")
    print(f"   Updated: {updated}")
    print(f"   Failed: {failed}")
    print(f"   Time: {elapsed/60:.1f} minutes")
    print()
    print(f"📈 New difficulty distribution:")
    print(f"   Easy: {new_diff.get('easy', 0)} ({new_diff.get('easy', 0)/len(pages)*100:.1f}%)")
    print(f"   Medium: {new_diff.get('medium', 0)} ({new_diff.get('medium', 0)/len(pages)*100:.1f}%)")
    print(f"   Hard: {new_diff.get('hard', 0)} ({new_diff.get('hard', 0)/len(pages)*100:.1f}%)")
    print()
    
    # Compare
    print(f"📉 Change:")
    print(f"   Easy: {current_diff.get('easy', 0)} → {new_diff.get('easy', 0)} ({new_diff.get('easy', 0) - current_diff.get('easy', 0):+d})")
    print(f"   Medium: {current_diff.get('medium', 0)} → {new_diff.get('medium', 0)} ({new_diff.get('medium', 0) - current_diff.get('medium', 0):+d})")
    print(f"   Hard: {current_diff.get('hard', 0)} → {new_diff.get('hard', 0)} ({new_diff.get('hard', 0) - current_diff.get('hard', 0):+d})")
    print()


if __name__ == '__main__':
    main()
