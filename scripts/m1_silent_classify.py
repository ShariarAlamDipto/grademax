#!/usr/bin/env python3
"""
Silent M1 classification - no emojis, minimal output
Classifies all M1 questions using proven MistralTopicClassifier
"""

import os
import sys
import json
from pathlib import Path
from io import StringIO
from contextlib import redirect_stdout, redirect_stderr
import PyPDF2

# Add parent directory to path
sys.path.append(str(Path(__file__).parent))

from mistral_classifier import MistralTopicClassifier
from dotenv import load_dotenv

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
        return ''

def main():
    """Classify all M1 questions silently"""
    
    # Get API key
    groq_key = os.getenv('GROQ_API_KEY')
    if not groq_key:
        print("ERROR: GROQ_API_KEY not found")
        return
    
    # Check topics YAML
    if not TOPICS_YAML.exists():
        print(f"ERROR: Topics YAML not found: {TOPICS_YAML}")
        return
    
    print(f"M1 Question Classification")
    print(f"Topics: {TOPICS_YAML.name}\n")
    
    # Initialize classifier (suppress output)
    f = StringIO()
    with redirect_stdout(f):
        classifier = MistralTopicClassifier(
            topics_yaml_path=str(TOPICS_YAML),
            groq_api_key=groq_key
        )
    
    print(f"Classifier ready: {len(classifier.available_models)} models\n")
    
    # Find all segmented files
    json_files = list(M1_DIR.glob('*_segmented.json'))
    print(f"Found {len(json_files)} papers\n")
    
    # Process each paper
    total_classified = 0
    total_failed = 0
    topic_dist = {}
    difficulty_dist = {'easy': 0, 'medium': 0, 'hard': 0}
    
    for json_file in sorted(json_files):
        paper_id = json_file.stem.replace('_segmented', '')
        
        # Load segmented data
        with open(json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        questions = data.get('questions', [])
        print(f"{paper_id}: {len(questions)}Q ", end='', flush=True)
        
        classified_this_paper = 0
        
        # Classify each question
        for q in questions:
            q_num = q['qnum']
            
            # Build PDF path
            qp_pdf_name = f"{paper_id}_Q{q_num}.pdf"
            qp_pdf_path = QP_PDF_DIR / qp_pdf_name
            
            # Check for PDF
            if not qp_pdf_path.exists():
                ms_pdf_name = f"{paper_id}_Q{q_num}.pdf"
                ms_pdf_path = MS_PDF_DIR / ms_pdf_name
                if ms_pdf_path.exists():
                    pdf_path = ms_pdf_path
                else:
                    print(f"X", end='', flush=True)
                    total_failed += 1
                    continue
            else:
                pdf_path = qp_pdf_path
            
            # Extract text
            question_text = extract_text_from_pdf(pdf_path)
            if not question_text or len(question_text) < 20:
                print(f"x", end='', flush=True)
                total_failed += 1
                continue
            
            # Classify (suppress output)
            try:
                f = StringIO()
                with redirect_stdout(f), redirect_stderr(f):
                    result = classifier.classify(question_text, f"Q{q_num}")
                
                if result is None:
                    print(f"!", end='', flush=True)
                    total_failed += 1
                    continue
                
                # Store classification
                q['classification'] = {
                    'topic': result.topic,
                    'difficulty': result.difficulty,
                    'confidence': result.confidence,
                    'page_has_question': result.page_has_question
                }
                
                # Update stats
                classified_this_paper += 1
                total_classified += 1
                topic_dist[result.topic] = topic_dist.get(result.topic, 0) + 1
                difficulty_dist[result.difficulty] = difficulty_dist.get(result.difficulty, 0) + 1
                
                print(f".", end='', flush=True)
                
            except Exception as e:
                print(f"E", end='', flush=True)
                total_failed += 1
                continue
        
        # Save classified data
        if classified_this_paper > 0:
            output_file = M1_DIR / json_file.name.replace('_segmented.json', '_classified.json')
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            print(f" OK ({classified_this_paper})")
        else:
            print(f" SKIP")
    
    # Final summary
    total_questions = total_classified + total_failed
    print(f"\n{'='*60}")
    print(f"CLASSIFICATION COMPLETE")
    print(f"{'='*60}")
    print(f"Classified: {total_classified}/{total_questions} ({total_classified/total_questions*100:.1f}%)")
    
    if total_failed > 0:
        print(f"Failed: {total_failed}")
    
    print(f"\nTopic Distribution:")
    for topic in sorted(topic_dist.keys()):
        print(f"  {topic}: {topic_dist[topic]}")
    
    print(f"\nDifficulty Distribution:")
    for diff in ['easy', 'medium', 'hard']:
        print(f"  {diff}: {difficulty_dist[diff]}")

if __name__ == '__main__':
    main()
