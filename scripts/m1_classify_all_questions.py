#!/usr/bin/env python3
"""
Classify all M1 questions using the proven MistralTopicClassifier approach
Processes segmented M1 questions and assigns topics using multi-model fallback
"""

import os
import sys
import json
from pathlib import Path
from dotenv import load_dotenv
import PyPDF2

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent))

from mistral_classifier import MistralTopicClassifier

# Load environment
load_dotenv('.env.local')

# Paths
BASE_DIR = Path(__file__).parent.parent
M1_DIR = BASE_DIR / 'data' / 'processed' / 'Mechanics_1'
TOPICS_YAML = BASE_DIR / 'classification' / 'mechanics_1_topics.yaml'
QP_PDF_DIR = M1_DIR / 'pages'
MS_PDF_DIR = M1_DIR / 'markschemes'

def extract_text_from_pdf(pdf_path: Path) -> str:
    """Extract text from PDF file"""
    try:
        with open(pdf_path, 'rb') as f:
            reader = PyPDF2.PdfReader(f)
            text = ''
            for page in reader.pages:
                text += page.extract_text() + '\n'
            return text.strip()
    except Exception as e:
        print(f"   [ERROR] Error reading PDF {pdf_path.name}: {e}")
        return ''

def classify_m1_questions():
    """Classify all M1 questions from segmented JSON files"""
    
    # Get API key
    groq_key = os.getenv('GROQ_API_KEY')
    if not groq_key:
        print("❌ GROQ_API_KEY not found in .env.local")
        return
    
    # Check topics YAML exists
    if not TOPICS_YAML.exists():
        print(f"ERROR: Topics YAML not found: {TOPICS_YAML}")
        return
    
    # Initialize classifier
    print(f"\n[INIT] Initializing M1 Classifier")
    print(f"   Topics: {TOPICS_YAML}")
    
    classifier = MistralTopicClassifier(
        topics_yaml_path=str(TOPICS_YAML),
        groq_api_key=groq_key
    )
    
    print(f"   [OK] Classifier ready with {len(classifier.available_models)} models")
    print(f"   Models: {[m['name'] for m in classifier.available_models]}")
    
    # Find all segmented JSON files
    json_files = list(M1_DIR.glob('*_segmented.json'))
    
    if not json_files:
        print(f"\nERROR: No segmented JSON files found in {M1_DIR}")
        return
    
    print(f"\n[INFO] Found {len(json_files)} segmented paper(s)")
    
    # Process each paper
    for json_file in json_files:
        print(f"\n{'='*80}")
        print(f"Processing: {json_file.name}")
        print(f"{'='*80}")
        
        # Load segmented data
        with open(json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        questions = data.get('questions', [])
        print(f"\n[INFO] Questions: {len(questions)}")
        
        # Statistics
        classified_count = 0
        failed_questions = []
        topic_distribution = {}
        difficulty_distribution = {'easy': 0, 'medium': 0, 'hard': 0}
        
        # Classify each question
        for q in questions:
            q_num = q['qnum']
            
            # Build question identifier from JSON filename
            # e.g., "2022_Jan_P1_segmented.json" -> "2022_Jan_P1"
            paper_id = json_file.stem.replace('_segmented', '')
            qp_pdf_name = f"{paper_id}_Q{q_num}.pdf"
            qp_pdf_path = QP_PDF_DIR / qp_pdf_name
            
            print(f"\n[Q{q_num}]:")
            
            # Check if QP PDF exists
            if not qp_pdf_path.exists():
                # Try MS PDF as fallback
                ms_pdf_name = f"{paper_id}_Q{q_num}.pdf"
                ms_pdf_path = MS_PDF_DIR / ms_pdf_name
                
                if ms_pdf_path.exists():
                    print(f"   [WARN] No QP PDF, using MS PDF: {ms_pdf_name}")
                    pdf_path = ms_pdf_path
                else:
                    print(f"   [ERROR] No QP or MS PDF found")
                    failed_questions.append(q_num)
                    continue
            else:
                pdf_path = qp_pdf_path
            
            # Extract text
            question_text = extract_text_from_pdf(pdf_path)
            
            if not question_text or len(question_text) < 20:
                print(f"   [WARN] PDF text too short ({len(question_text)} chars)")
                failed_questions.append(q_num)
                continue
            
            print(f"   [PDF] Extracted {len(question_text)} characters from PDF")
            print(f"   [CLASSIFY] Using model {classifier.model}...")
            
            # Classify
            try:
                result = classifier.classify(question_text, f"Q{q_num}")
                
                if result is None:
                    print(f"   [ERROR] Classification returned None")
                    failed_questions.append(q_num)
                    continue
                
                # Store classification in question data
                q['classification'] = {
                    'topic': result.topic,
                    'difficulty': result.difficulty,
                    'confidence': result.confidence,
                    'page_has_question': result.page_has_question
                }
                
                # Update statistics
                classified_count += 1
                topic_distribution[result.topic] = topic_distribution.get(result.topic, 0) + 1
                difficulty_distribution[result.difficulty] = difficulty_distribution.get(result.difficulty, 0) + 1
                
                # Display result
                print(f"   [OK] Topic: {result.topic}, Difficulty: {result.difficulty}, Confidence: {result.confidence:.2f}")
                
            except Exception as e:
                print(f"   [ERROR] Classification failed: {e}")
                failed_questions.append(q_num)
                continue
        
        # Save classified data
        output_file = M1_DIR / json_file.name.replace('_segmented.json', '_classified.json')
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        print(f"\n{'='*80}")
        print(f"CLASSIFICATION SUMMARY")
        print(f"{'='*80}")
        print(f"[STATS] Classified: {classified_count}/{len(questions)} ({classified_count/len(questions)*100:.1f}%)")
        
        if failed_questions:
            print(f"[FAILED] Questions: {failed_questions}")
        
        print(f"\n[TOPICS] Distribution:")
        for topic, count in sorted(topic_distribution.items()):
            print(f"   {topic}: {count} questions")
        
        print(f"\n[DIFFICULTY] Distribution:")
        for difficulty, count in sorted(difficulty_distribution.items()):
            print(f"   {difficulty}: {count} questions")
        
        print(f"\n[SAVE] Saved to: {output_file}")

if __name__ == '__main__':
    classify_m1_questions()
