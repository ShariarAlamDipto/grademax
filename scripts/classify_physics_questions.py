"""
Classify Physics Questions Using Multimodal Groq Vision

This script:
1. Gets all Physics pages from database (uploaded by upload_physics_to_database.py)
2. Downloads question PDFs from storage
3. Converts first page of each PDF to image
4. Uses Groq Vision (llama-3.2-90b-vision-preview) to classify topics
5. Updates database with topics, difficulty, confidence

Uses physics_topics.yaml with 8 topics:
1. Forces and motion (FM)
2. Electricity (ELEC)
3. Waves (WAVE)
4. Energy resources and transfers (ENRG)
5. Solids, liquids and gases (SLG)
6. Magnetism and electromagnetism (MAG)
7. Radioactivity and particles (RAD)
8. Astrophysics (ASTRO)
"""

import os
import sys
import json
import time
import base64
import requests
from pathlib import Path
from dotenv import load_dotenv
from supabase import create_client, Client
import yaml
from io import BytesIO
import fitz  # PyMuPDF

# Fix Windows console encoding
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

# Load environment
env_path = Path('.env.local')
load_dotenv(env_path)

SUPABASE_URL = os.getenv("NEXT_PUBLIC_SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

if not all([SUPABASE_URL, SUPABASE_KEY, GROQ_API_KEY]):
    print("❌ Missing required environment variables!")
    sys.exit(1)

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# Constants
SUBJECT_ID = "0b142517-d35d-4942-91aa-b4886aaabca3"
PHYSICS_TOPICS_YAML = Path("classification/physics_topics.yaml")
GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
VISION_MODEL = "llama-3.2-90b-vision-preview"  # Multimodal vision model
DELAY_SECONDS = 6  # Groq rate limit: ~10 requests per minute


def load_physics_topics():
    """Load Physics topics from YAML"""
    with open(PHYSICS_TOPICS_YAML, 'r', encoding='utf-8') as f:
        data = yaml.safe_load(f)
    
    topics = {}
    for topic in data['topics']:
        topics[topic['code']] = {
            'id': topic['id'],
            'code': topic['code'],
            'name': topic['name'],
            'core': [item['text'] for item in topic['core']],
            'support': [item['text'] for item in topic['support']]
        }
    
    return topics


def pdf_to_base64_image(pdf_bytes, page_num=0, dpi=150):
    """
    Convert a PDF page to base64-encoded PNG image
    
    Args:
        pdf_bytes: PDF file bytes
        page_num: Page number to convert (0-indexed)
        dpi: Resolution for rendering
    
    Returns:
        base64-encoded PNG image string
    """
    try:
        # Open PDF from bytes
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        
        if page_num >= len(doc):
            page_num = 0
        
        # Get page
        page = doc[page_num]
        
        # Render page to pixmap (image)
        mat = fitz.Matrix(dpi / 72, dpi / 72)  # 72 DPI is default
        pix = page.get_pixmap(matrix=mat)
        
        # Convert to PNG bytes
        png_bytes = pix.tobytes("png")
        
        # Encode to base64
        base64_image = base64.b64encode(png_bytes).decode('utf-8')
        
        doc.close()
        return base64_image
        
    except Exception as e:
        print(f"         ❌ Error converting PDF to image: {e}")
        return None


def download_pdf_from_url(url):
    """Download PDF from public URL"""
    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        return response.content
    except Exception as e:
        print(f"         ❌ Error downloading PDF: {e}")
        return None


def build_classification_prompt(topics):
    """Build prompt for Groq Vision classification"""
    
    topic_list = []
    for code, info in topics.items():
        core_keywords = ", ".join(info['core'][:3])  # Top 3 core keywords
        topic_list.append(f"{info['id']}. {info['name']} ({code}) - Keywords: {core_keywords}")
    
    prompt = f"""You are a Physics question classifier for IGCSE exam papers.

TOPICS:
{chr(10).join(topic_list)}

TASK:
Analyze this Physics question image and classify it into ONE primary topic.

INSTRUCTIONS:
1. Read the question carefully
2. Identify the main physics concept being tested
3. Choose the SINGLE most relevant topic (1-8)
4. Assess difficulty: easy/medium/hard
5. Provide confidence score (0.0-1.0)

Respond in JSON format:
{{
    "topic": "topic_code",
    "difficulty": "easy|medium|hard",
    "confidence": 0.85,
    "reasoning": "Brief explanation"
}}

Example:
{{
    "topic": "FM",
    "difficulty": "medium",
    "confidence": 0.92,
    "reasoning": "Question involves Newton's second law F=ma with calculations"
}}"""
    
    return prompt


def classify_with_groq_vision(image_base64, topics, question_number):
    """
    Classify a question using Groq Vision API
    
    Args:
        image_base64: Base64-encoded PNG image
        topics: Dictionary of Physics topics
        question_number: Question number for context
    
    Returns:
        dict with topic, difficulty, confidence, reasoning
    """
    
    prompt = build_classification_prompt(topics)
    
    payload = {
        "model": VISION_MODEL,
        "messages": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": prompt
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/png;base64,{image_base64}"
                        }
                    }
                ]
            }
        ],
        "temperature": 0.2,
        "max_tokens": 500,
        "response_format": {"type": "json_object"}
    }
    
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }
    
    try:
        response = requests.post(GROQ_API_URL, json=payload, headers=headers, timeout=60)
        response.raise_for_status()
        
        result = response.json()
        content = result['choices'][0]['message']['content']
        classification = json.loads(content)
        
        # Validate topic code
        if classification.get('topic') not in topics:
            print(f"         ⚠️  Invalid topic code: {classification.get('topic')}, defaulting to FM")
            classification['topic'] = 'FM'
        
        # Ensure confidence is float
        classification['confidence'] = float(classification.get('confidence', 0.5))
        
        return classification
        
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 429:
            print(f"         ⚠️  Rate limit hit, waiting 30s...")
            time.sleep(30)
            return classify_with_groq_vision(image_base64, topics, question_number)
        else:
            print(f"         ❌ HTTP Error: {e}")
            return None
    except Exception as e:
        print(f"         ❌ Error calling Groq Vision: {e}")
        return None


def get_unclassified_physics_pages():
    """Get all Physics pages that need classification"""
    
    # Get all Physics papers
    papers = supabase.table('papers')\
        .select('id')\
        .eq('subject_id', SUBJECT_ID)\
        .execute()
    
    if not papers.data:
        print("❌ No Physics papers found in database!")
        return []
    
    paper_ids = [p['id'] for p in papers.data]
    
    # Get all pages that need classification (topics is empty array)
    all_pages = []
    for paper_id in paper_ids:
        pages = supabase.table('pages')\
            .select('id, paper_id, page_number, question_number, qp_page_url, topics')\
            .eq('paper_id', paper_id)\
            .order('page_number')\
            .execute()
        
        if pages.data:
            # Filter for unclassified (topics is None or empty array)
            for page in pages.data:
                if not page.get('topics') or page.get('topics') == []:
                    all_pages.append(page)
    
    return all_pages


def classify_physics_questions():
    """Main classification function"""
    
    print("\n" + "="*80)
    print("🔬 CLASSIFY PHYSICS QUESTIONS - MULTIMODAL GROQ VISION")
    print("="*80)
    
    # Load topics
    print("\n📚 Loading Physics topics...")
    topics = load_physics_topics()
    print(f"   ✅ Loaded {len(topics)} topics:")
    for code, info in topics.items():
        print(f"      {info['id']}. {info['name']} ({code})")
    
    # Get unclassified pages
    print("\n📊 Finding unclassified pages...")
    pages = get_unclassified_physics_pages()
    
    if not pages:
        print("   ✅ All Physics questions are already classified!")
        return
    
    print(f"   Found {len(pages)} unclassified pages")
    
    # Confirm
    print(f"\n⚠️  This will:")
    print(f"   1. Download {len(pages)} question PDFs from storage")
    print(f"   2. Convert to images")
    print(f"   3. Classify with Groq Vision (llama-3.2-90b-vision-preview)")
    print(f"   4. Update database with topics/difficulty/confidence")
    print(f"   Expected time: ~{len(pages) * DELAY_SECONDS / 60:.1f} minutes ({DELAY_SECONDS}s delay per request)")
    
    response = input("\n❓ Continue? (yes/no): ")
    if response.lower() != 'yes':
        print("❌ Cancelled")
        return
    
    # Classify each page
    print("\n" + "="*80)
    print("CLASSIFICATION IN PROGRESS")
    print("="*80)
    
    stats = {
        'total': len(pages),
        'classified': 0,
        'failed': 0,
        'by_topic': {},
        'by_difficulty': {'easy': 0, 'medium': 0, 'hard': 0}
    }
    
    for i, page in enumerate(pages, 1):
        page_id = page['id']
        q_num = page['question_number']
        pdf_url = page.get('qp_page_url')
        
        print(f"\n[{i}/{len(pages)}] Question {q_num}")
        
        if not pdf_url:
            print(f"   ⚠️  No PDF URL, skipping")
            stats['failed'] += 1
            continue
        
        try:
            # Download PDF
            print(f"   📥 Downloading PDF...")
            pdf_bytes = download_pdf_from_url(pdf_url)
            
            if not pdf_bytes:
                print(f"   ❌ Download failed")
                stats['failed'] += 1
                continue
            
            # Convert to image
            print(f"   🖼️  Converting to image...")
            image_base64 = pdf_to_base64_image(pdf_bytes)
            
            if not image_base64:
                print(f"   ❌ Image conversion failed")
                stats['failed'] += 1
                continue
            
            # Classify with Groq Vision
            print(f"   🔬 Classifying with Groq Vision...")
            classification = classify_with_groq_vision(image_base64, topics, q_num)
            
            if not classification:
                print(f"   ❌ Classification failed")
                stats['failed'] += 1
                continue
            
            # Update database
            topic_code = classification['topic']
            difficulty = classification['difficulty']
            confidence = classification['confidence']
            
            supabase.table('pages').update({
                'topics': [topic_code],
                'difficulty': difficulty,
                'confidence': confidence
            }).eq('id', page_id).execute()
            
            # Update stats
            stats['classified'] += 1
            stats['by_topic'][topic_code] = stats['by_topic'].get(topic_code, 0) + 1
            stats['by_difficulty'][difficulty] = stats['by_difficulty'].get(difficulty, 0) + 1
            
            topic_name = topics[topic_code]['name']
            print(f"   ✅ {topic_name} ({topic_code}) | {difficulty} | {confidence:.2f}")
            print(f"      Reasoning: {classification.get('reasoning', 'N/A')[:80]}")
            
            # Rate limit delay
            if i < len(pages):
                print(f"   ⏳ Waiting {DELAY_SECONDS}s (rate limit)...")
                time.sleep(DELAY_SECONDS)
            
        except Exception as e:
            print(f"   ❌ Error: {e}")
            stats['failed'] += 1
            continue
    
    # Summary
    print("\n" + "="*80)
    print("📊 CLASSIFICATION SUMMARY")
    print("="*80)
    
    print(f"\n✅ Successfully classified: {stats['classified']}/{stats['total']}")
    if stats['failed'] > 0:
        print(f"❌ Failed: {stats['failed']}/{stats['total']}")
    
    if stats['classified'] > 0:
        print(f"\n📈 By Topic:")
        for topic_code, count in sorted(stats['by_topic'].items(), key=lambda x: -x[1]):
            topic_name = topics[topic_code]['name']
            pct = (count / stats['classified'] * 100)
            print(f"   {topic_name:40s} ({topic_code}): {count:3d} ({pct:5.1f}%)")
        
        print(f"\n📊 By Difficulty:")
        for difficulty in ['easy', 'medium', 'hard']:
            count = stats['by_difficulty'][difficulty]
            pct = (count / stats['classified'] * 100) if stats['classified'] > 0 else 0
            print(f"   {difficulty.capitalize():10s}: {count:3d} ({pct:5.1f}%)")
    
    success_rate = (stats['classified'] / stats['total'] * 100) if stats['total'] > 0 else 0
    print(f"\n🎯 Overall success rate: {success_rate:.1f}%")
    
    print("\n" + "="*80)
    print("✨ CLASSIFICATION COMPLETE!")
    print("="*80)
    print("\n💡 Next steps:")
    print("   1. Review classifications in database")
    print("   2. Test worksheet generation for Physics topics")
    print("   3. Review any failed classifications manually")


if __name__ == "__main__":
    classify_physics_questions()
