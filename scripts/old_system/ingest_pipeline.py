#!/usr/bin/env python3
"""
Main Ingestion Pipeline - GradeMax Phase 2
Orchestrates page splitting, LLM classification, guardrail validation, and database storage
"""

import os
import sys
import json
import time
from pathlib import Path
from typing import List, Dict, Optional
import argparse
from datetime import datetime

# Add scripts directory to path
sys.path.insert(0, str(Path(__file__).parent))

from split_pages import process_paper_directory, QuestionDetector
from classify_with_gemini import (
    TopicCatalogue, GeminiClassifier, GuardrailValidator,
    TopicClassification, GEMINI_AVAILABLE
)

# Database imports - use Supabase REST API instead of psycopg2
try:
    from supabase_client import SupabaseClient
    DB_AVAILABLE = True
except ImportError:
    print("⚠️  supabase_client not available")
    DB_AVAILABLE = False


class IngestionOrchestrator:
    """Orchestrates the full ingestion pipeline"""
    
    def __init__(
        self,
        gemini_api_key: str,
        db_connection_string: str,
        catalogue_path: str,
        dry_run: bool = False
    ):
        self.gemini_api_key = gemini_api_key
        self.db_connection_string = db_connection_string
        self.dry_run = dry_run
        
        # Load catalogue
        self.catalogue = TopicCatalogue(catalogue_path)
        print(f"✅ Loaded {len(self.catalogue.topics)} topics from catalogue")
        
        # Initialize classifier
        if GEMINI_AVAILABLE and gemini_api_key:
            self.classifier = GeminiClassifier(gemini_api_key, self.catalogue)
            print(f"✅ Gemini classifier ready ({self.classifier.model_name})")
        else:
            self.classifier = None
            print("⚠️  Gemini classifier not available")
        
        # Initialize guardrail validator
        self.validator = GuardrailValidator(self.catalogue)
        print(f"✅ Guardrail validator ready")
        
        # Database connection - use Supabase REST API
        self.db_client = None
        if DB_AVAILABLE and not dry_run:
            self.db_client = SupabaseClient()
            print(f"✅ Database connected (Supabase REST API)")
    
    def process_paper(
        self,
        paper_directory: str,
        output_base: str = "data/processed"
    ) -> Dict:
        """
        Run complete ingestion pipeline for a single paper
        
        Steps:
        1. Split pages and extract text
        2. Classify each page with Gemini
        3. Apply guardrail validation
        4. Store in database
        5. Save manifest
        """
        start_time = time.time()
        
        print(f"\n{'='*70}")
        print(f"🚀 STARTING INGESTION PIPELINE")
        print(f"{'='*70}\n")
        
        # Step 1: Split pages (or load existing manifest)
        print("📄 Step 1: Splitting pages...")
        
        # Try to find existing manifest by looking in processed directory
        # Expected paper IDs: 4PH1_2019_Jun_1P, etc.
        input_path = Path(paper_directory)
        paper_parts = []
        for part in input_path.parts:
            if part not in ['data', 'raw', 'IGCSE', '..', '.']:
                paper_parts.append(part)
        
        # Likely format: 4PH1/2019/Jun -> 4PH1_2019_Jun
        if len(paper_parts) >= 3:
            paper_code = paper_parts[-3]  # 4PH1
            year = paper_parts[-2]  # 2019
            season = paper_parts[-1]  # Jun
            
            # Check both with and without paper number
            for suffix in ['_1P', '']:
                expected_paper_id = f"{paper_code}_{year}_{season}{suffix}"
                expected_manifest_path = os.path.join(output_base, expected_paper_id, "manifest.json")
                
                if os.path.exists(expected_manifest_path):
                    print(f"✅ Found existing manifest: {expected_manifest_path}")
                    with open(expected_manifest_path, 'r', encoding='utf-8') as f:
                        manifest = json.load(f)
                    paper_id = manifest.get('paper_id', expected_paper_id)
                    manifest_path = expected_manifest_path
                    print(f"   Skipping split - using {len(manifest['questions'])} existing questions")
                    manifest_exists = True
                    break
            else:
                manifest_exists = False
        else:
            manifest_exists = False
        
        if not manifest_exists:
            # Not found, need to split
            split_result = process_paper_directory(paper_directory, output_base)
            manifest_path = split_result['manifest_path']
            paper_id = split_result['paper_id']
            
            with open(manifest_path, 'r', encoding='utf-8') as f:
                manifest = json.load(f)
            
            print(f"✅ Split into {len(manifest['questions'])} questions")
        
        # Initialize processing flags if not exists
        if 'processing' not in manifest:
            manifest['processing'] = {}
        
        # Step 1.5: Upload PDFs to Supabase Storage
        if not self.dry_run and self.db_client:
            # Check if already uploaded
            if manifest['processing'].get('pdfs_uploaded'):
                print("\n☁️  Step 1.5: PDFs already uploaded - SKIPPING")
            else:
                print("\n☁️  Step 1.5: Uploading PDFs to Supabase Storage...")
                self._upload_pdfs_to_storage(manifest, paper_id)
                manifest['processing']['pdfs_uploaded'] = True
                # Save checkpoint
                with open(manifest_path, 'w', encoding='utf-8') as f:
                    json.dump(manifest, f, indent=2, ensure_ascii=False, default=str)
                print(f"✅ Uploaded PDFs to storage")
        else:
            print(f"\n⚠️  Step 1.5: SKIPPED (dry run or no database)")
        
        # Step 2: Classify with LLM
        print(f"\n🤖 Step 2: Classifying with Gemini...")
        
        # Check if already classified
        if manifest['processing'].get('questions_classified'):
            print("   Questions already classified - SKIPPING")
            llm_call_count = manifest['processing'].get('llm_calls', 0)
        else:
            classifications = []
            llm_call_count = 0
            
            for q in manifest['questions']:
                q_num = q['question_number']
                print(f"\n📝 Question {q_num}:")
                
                # Classify each page in the question
                page_classifications = []
                for page_data in q['pages']:
                    if not self.classifier:
                        # Skip if no classifier
                        classification = TopicClassification(
                            page_has_question=True,
                            topics=[],
                            subparts=[],
                            difficulty='medium',
                            confidence=0.0
                        )
                    else:
                        classification = self.classifier.classify_page(
                            page_data['text_excerpt'],
                            q_num
                        )
                        llm_call_count += 1
                    
                    page_classifications.append({
                        'page_index': page_data['page_index'],
                        'classification': classification
                    })
                    
                    print(f"   Page {page_data['page_index']}: {', '.join(classification.topics)} "
                          f"({classification.difficulty}, conf={classification.confidence:.2f})")
                
                q['classifications'] = page_classifications
                
                # Aggregate topics from all pages in this question
            all_topics = set()
            for pc in page_classifications:
                all_topics.update(pc['classification'].topics)
            
            q['aggregated_topics'] = list(all_topics)
            
            print(f"✅ Classified {len(manifest['questions'])} questions")
            
            # Mark as classified and save checkpoint
            manifest['processing']['questions_classified'] = True
            manifest['processing']['llm_calls'] = llm_call_count
            
            # Convert TopicClassification objects to dicts for JSON serialization
            for q in manifest['questions']:
                for pc in q.get('classifications', []):
                    if 'classification' in pc and hasattr(pc['classification'], '__dataclass_fields__'):
                        # Convert dataclass to dict
                        from dataclasses import asdict
                        pc['classification'] = asdict(pc['classification'])
            
            with open(manifest_path, 'w', encoding='utf-8') as f:
                json.dump(manifest, f, indent=2, ensure_ascii=False)
        
        # Step 3: Apply guardrails
        print(f"\n🛡️  Step 3: Applying guardrails...")
        
        # Check if already applied
        if manifest['processing'].get('guardrails_applied'):
            print("   Guardrails already applied - SKIPPING")
            guardrail_corrections = manifest['processing'].get('guardrail_corrections', 0)
        else:
            guardrail_corrections = 0
            
            for q in manifest['questions']:
                for page_data, pc in zip(q['pages'], q['classifications']):
                    # Validate against full page text
                    class_data = pc['classification']
                    
                    # Handle both dict and object formats
                    if isinstance(class_data, dict):
                        original_topics = set(class_data.get('topics', []))
                        # Convert dict back to TopicClassification for validation
                        from classify_with_gemini import TopicClassification
                        class_obj = TopicClassification(
                            page_has_question=class_data.get('page_has_question', True),
                            topics=class_data.get('topics', []),
                            subparts=class_data.get('subparts', []),
                            difficulty=class_data.get('difficulty', 'medium'),
                            confidence=class_data.get('confidence', 0.5)
                        )
                    else:
                        original_topics = set(class_data.topics)
                        class_obj = class_data
                    
                    corrected = self.validator.validate_and_correct(
                        page_data['text'],
                        class_obj
                    )
                    
                    if set(corrected.topics) != original_topics:
                        guardrail_corrections += 1
                    
                    # Convert back to dict for storage
                    from dataclasses import asdict
                    pc['classification'] = asdict(corrected)
                
                # Re-aggregate after corrections
                all_topics = set()
                for pc in q['classifications']:
                    class_data = pc['classification']
                    if isinstance(class_data, dict):
                        all_topics.update(class_data.get('topics', []))
                    else:
                        all_topics.update(class_data.topics)
                q['aggregated_topics'] = list(all_topics)
                
                print(f"   Q{q['question_number']}: {', '.join(q['aggregated_topics'])}")
            
            print(f"✅ Guardrails made {guardrail_corrections} corrections")
            
            # Mark as applied and save checkpoint
            manifest['processing']['guardrails_applied'] = True
            manifest['processing']['guardrail_corrections'] = guardrail_corrections
            with open(manifest_path, 'w', encoding='utf-8') as f:
                json.dump(manifest, f, indent=2, ensure_ascii=False, default=str)
        
        # Step 4: Store in database
        if not self.dry_run and self.db_client:
            # Check if already stored
            if manifest['processing'].get('stored_in_db'):
                print("💾 Step 4: Already stored in database - SKIPPING")
            else:
                print("💾 Step 4: Storing in database...")
                self._store_in_database(manifest, paper_id)
                manifest['processing']['stored_in_db'] = True
                with open(manifest_path, 'w', encoding='utf-8') as f:
                    json.dump(manifest, f, indent=2, ensure_ascii=False, default=str)
                print(f"✅ Stored to database")
        else:
            print(f"\n⚠️  Step 4: SKIPPED (dry run or no database)")
        
        # Step 5: Update manifest with final summary
        manifest['processing'].update({
            'llm_calls': llm_call_count,
            'guardrail_corrections': guardrail_corrections,
            'processing_time_seconds': int(time.time() - start_time),
            'gemini_model': self.classifier.model_name if self.classifier else None,
            'timestamp': datetime.now().isoformat()
        })
        
        # Save updated manifest
        with open(manifest_path, 'w', encoding='utf-8') as f:
            json.dump(manifest, f, indent=2, ensure_ascii=False, default=str)
        
        print(f"\n✅ Updated manifest: {manifest_path}")
        
        # Summary
        elapsed_time = time.time() - start_time
        
        print(f"\n{'='*70}")
        print(f"🎉 INGESTION COMPLETE!")
        print(f"{'='*70}")
        print(f"Paper ID: {paper_id}")
        print(f"Questions: {len(manifest['questions'])}")
        print(f"LLM Calls: {llm_call_count}")
        print(f"Guardrail Corrections: {guardrail_corrections}")
        print(f"Processing Time: {elapsed_time:.1f}s")
        print(f"Manifest: {manifest_path}")
        print(f"{'='*70}\n")
        
        return {
            'paper_id': paper_id,
            'manifest_path': manifest_path,
            'questions': len(manifest['questions']),
            'llm_calls': llm_call_count,
            'corrections': guardrail_corrections,
            'time_seconds': elapsed_time
        }
    
    def _upload_pdfs_to_storage(self, manifest: Dict, paper_id: str):
        """
        Upload question page PDFs to Supabase Storage
        Updates manifest with storage URLs
        """
        try:
            bucket_name = 'question-pdfs'
            uploaded_count = 0
            
            # Build storage path: papers/paper_id/Q1.pdf (2 levels max for RLS)
            year = manifest['metadata']['year']
            season = manifest['metadata']['season']
            paper_num = manifest['metadata']['paper_number']
            paper_id_str = f"{year}_{season}_{paper_num}"
            base_path = f"papers/{paper_id_str}"
            
            print(f"   Storage base path: {base_path}")
            
            for q in manifest['questions']:
                q_num = q['question_number']
                
                # Upload question PDF (if exists)
                if 'pdf_path' in q and os.path.exists(q['pdf_path']):
                    dest_path = f"{base_path}/Q{q_num}.pdf"
                    print(f"   Uploading: {q['pdf_path']} → {dest_path}")
                    
                    try:
                        storage_path = self.db_client.upload_file(
                            bucket=bucket_name,
                            file_path=q['pdf_path'],
                            destination_path=dest_path
                        )
                        q['page_pdf_url'] = dest_path  # Store relative path
                        uploaded_count += 1
                        print(f"   ☁️  Q{q_num} → {dest_path}")
                    except Exception as e:
                        print(f"   ❌ Upload failed for Q{q_num}: {e}")
                        # Don't fail the entire pipeline, just skip this file
                        continue
                
                # Upload mark scheme PDF (if exists)
                if 'ms_pdf_path' in q and os.path.exists(q['ms_pdf_path']):
                    dest_path = f"{base_path}/Q{q_num}_MS.pdf"
                    storage_path = self.db_client.upload_file(
                        bucket=bucket_name,
                        file_path=q['ms_pdf_path'],
                        destination_path=dest_path
                    )
                    q['ms_pdf_url'] = dest_path  # Store relative path
                    print(f"   ☁️  Q{q_num}_MS → {dest_path}")
            
            print(f"   Uploaded {uploaded_count} PDFs to storage")
            
        except Exception as e:
            print(f"⚠️  Storage upload failed: {e}")
            print(f"   Continuing without storage URLs...")
    
    def _store_in_database(self, manifest: Dict, paper_id: str):
        """Store classified questions in database using Supabase REST API"""
        try:
            # 1. Get or create paper record
            db_paper_id = self.db_client.get_or_create_paper(
                subject_code=manifest['metadata']['subject_code'],
                year=manifest['metadata']['year'],
                season=manifest['metadata']['season'],
                paper_number=manifest['metadata']['paper_number'],
                qp_url=manifest.get('qp_file'),
                ms_url=manifest.get('ms_file')
            )
            
            print(f"   Paper UUID: {db_paper_id}")
            
            # 2. Insert questions with topics
            for q in manifest['questions']:
                # Get first page classification for main metadata
                first_class = q['classifications'][0]['classification'] if q['classifications'] else None
                if not first_class:
                    continue
                
                # Handle both object and dict formats (after JSON serialization)
                if isinstance(first_class, dict):
                    # Already a dict from JSON
                    first_class_dict = first_class
                else:
                    # TopicClassification object
                    first_class_dict = {
                        'difficulty': first_class.difficulty,
                        'confidence': first_class.confidence,
                        'topics': first_class.topics
                    }
                
                # Build subparts list
                subparts = []
                for page_data in q['pages']:
                    for subpart in page_data.get('subparts', []):
                        if subpart not in [s['label'] for s in subparts]:
                            subparts.append({'label': subpart})
                
                # Determine difficulty as integer (1=easy, 2=medium, 3=hard)
                difficulty_map = {'easy': 1, 'medium': 2, 'hard': 3}
                difficulty = difficulty_map.get(first_class_dict.get('difficulty'), 2)
                
                # Calculate average confidence
                confidences = []
                for pc in q['classifications']:
                    if pc.get('classification'):
                        class_data = pc['classification']
                        if isinstance(class_data, dict):
                            confidences.append(class_data.get('confidence', 0.5))
                        else:
                            confidences.append(class_data.confidence)
                avg_confidence = sum(confidences) / len(confidences) if confidences else 0.5
                
                # Build topics list
                topics = []
                for topic_code in q['aggregated_topics']:
                    # Find confidence for this specific topic
                    topic_confidences = []
                    for pc in q['classifications']:
                        if pc.get('classification'):
                            class_data = pc['classification']
                            if isinstance(class_data, dict):
                                if topic_code in class_data.get('topics', []):
                                    topic_confidences.append(class_data.get('confidence', 0.5))
                            else:
                                if topic_code in class_data.topics:
                                    topic_confidences.append(class_data.confidence)
                    confidence = max(topic_confidences) if topic_confidences else 0.5
                    
                    topics.append({
                        'topic_code': topic_code,
                        'confidence': confidence,
                        'subpart_label': None,
                        'method': 'llm'
                    })
                
                # Get mark scheme page indices
                ms_page_indices = [ms['page_index'] for ms in q.get('ms_pages', [])]
                
                # Insert question with topics
                question_id = self.db_client.insert_question_with_topics(
                    paper_id=db_paper_id,
                    question_number=q['question_number'],
                    topics=topics,
                    text=q['pages'][0]['text'],
                    text_excerpt=q['pages'][0]['text_excerpt'],
                    marks=None,  # Extract later
                    difficulty=difficulty,
                    qp_page_index=q['page_start'],
                    qp_page_count=q['page_count'],
                    page_pdf_url=q.get('page_pdf_url'),  # Storage path
                    ms_page_indices=ms_page_indices if ms_page_indices else None,
                    ms_pdf_url=q.get('ms_pdf_url'),  # Storage path
                    has_diagram=any(p['has_diagram'] for p in q['pages']),
                    classification_confidence=avg_confidence,
                    subparts=subparts
                )
                
                print(f"   Inserted Q{q['question_number']}: {len(topics)} topics")
            
            print(f"✅ Stored {len(manifest['questions'])} questions in database")
            
        except Exception as e:
            print(f"❌ Database storage failed: {e}")
            raise e
    
    def close(self):
        """Close database connection"""
        # Supabase REST API doesn't need closing
        pass


def main():
    parser = argparse.ArgumentParser(
        description='GradeMax Phase 2 - Page-based ingestion with LLM classification'
    )
    parser.add_argument(
        'input',
        help='Input directory containing PDF files (e.g., data/raw/IGCSE/4PH1/2019/Jun/)'
    )
    parser.add_argument(
        '--output',
        default='data/processed',
        help='Output base directory for processed files'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Run without database storage (testing only)'
    )
    parser.add_argument(
        '--catalogue',
        default='config/physics_topics.yaml',
        help='Path to topic catalogue YAML'
    )
    
    args = parser.parse_args()
    
    # Check environment variables
    gemini_api_key = os.environ.get('GEMINI_API_KEY')
    if not gemini_api_key and not args.dry_run:
        print("❌ GEMINI_API_KEY environment variable not set")
        print("Get your API key from: https://ai.google.dev/")
        sys.exit(1)
    
    # Supabase uses NEXT_PUBLIC_SUPABASE_URL and NEXT_PUBLIC_SUPABASE_ANON_KEY
    # No need to check DATABASE_URL anymore
    
    # Create orchestrator
    orchestrator = IngestionOrchestrator(
        gemini_api_key=gemini_api_key or '',
        db_connection_string='',  # Not used with Supabase REST API
        catalogue_path=args.catalogue,
        dry_run=args.dry_run
    )
    
    try:
        # Process paper
        result = orchestrator.process_paper(args.input, args.output)
        
        print(f"\n✨ Success! Processed {result['questions']} questions in {result['time_seconds']:.1f}s")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        orchestrator.close()


if __name__ == "__main__":
    main()
