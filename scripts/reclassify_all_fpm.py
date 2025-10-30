#!/usr/bin/env python3
"""
RECLASSIFY ALL FURTHER PURE MATHS PAPERS
Clears all existing topic classifications and reclassifies using the LLM classifier
"""

import os
import sys
import time
from pathlib import Path
from dotenv import load_dotenv
from supabase import create_client, Client

# Add parent directory to path
sys.path.append(str(Path(__file__).parent))

from mistral_classifier import MistralTopicClassifier

# Load environment
env_path = Path(__file__).parent.parent / '.env.local'
if not env_path.exists():
    print("❌ .env.local not found!")
    sys.exit(1)
load_dotenv(env_path)

SUPABASE_URL = os.getenv("NEXT_PUBLIC_SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    print("❌ Missing Supabase credentials in .env.local")
    sys.exit(1)

# Initialize Supabase
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)


def get_fpm_subject_id():
    """Get the subject ID for Further Pure Mathematics"""
    response = supabase.table("subjects").select("id, name, code").eq("code", "9FM0").execute()
    if response.data and len(response.data) > 0:
        return response.data[0]["id"], response.data[0]["name"]
    else:
        raise ValueError("Subject 9FM0 (Further Pure Mathematics) not found in database")


def clear_existing_classifications(subject_id: str):
    """Clear all existing topic classifications for FPM papers"""
    print("\n📦 STEP 1: Clearing Existing Classifications")
    print("=" * 80)
    
    # Get all FPM papers
    papers_response = supabase.table("papers").select("id, year, season, paper_number").eq("subject_id", subject_id).execute()
    papers = papers_response.data
    print(f"   Found {len(papers)} FPM papers")
    
    # Get all pages for these papers
    paper_ids = [p["id"] for p in papers]
    
    total_cleared = 0
    for paper_id in paper_ids:
        # Clear topic classification fields (topics is an array)
        update_response = supabase.table("pages")\
            .update({
                "topics": [],
                "difficulty": None,
                "confidence": None
            })\
            .eq("paper_id", paper_id)\
            .execute()
        
        if update_response.data:
            total_cleared += len(update_response.data)
    
    print(f"   ✅ Cleared classifications from {total_cleared} pages")
    return total_cleared


def get_pages_to_classify(subject_id: str):
    """Get all FPM pages that need classification"""
    print("\n📦 STEP 2: Finding Pages to Classify")
    print("=" * 80)
    
    # Get all papers for this subject
    papers_response = supabase.table("papers")\
        .select("id, year, season, paper_number")\
        .eq("subject_id", subject_id)\
        .execute()
    
    if not papers_response.data:
        print("   ❌ No papers found")
        return []
    
    papers = papers_response.data
    print(f"   Found {len(papers)} papers")
    
    # Get all pages
    all_pages = []
    for paper in papers:
        pages_response = supabase.table("pages")\
            .select("id, page_number, text_excerpt, qp_page_url, paper_id")\
            .eq("paper_id", paper["id"])\
            .order("page_number")\
            .execute()
        
        if pages_response.data:
            all_pages.extend(pages_response.data)
    
    print(f"   📄 Total pages: {len(all_pages)}")
    
    # Filter out blank pages
    valid_pages = [p for p in all_pages if p.get("text_excerpt") and len(p["text_excerpt"].strip()) > 50]
    blank_pages = len(all_pages) - len(valid_pages)
    
    print(f"   ✅ Valid pages: {len(valid_pages)}")
    print(f"   ⚠️  Blank pages (skipped): {blank_pages}")
    
    return valid_pages


def classify_pages_in_batches(pages, classifier, batch_size=20):
    """Classify pages in batches"""
    print("\n📦 STEP 3: Classifying Pages")
    print("=" * 80)
    
    total_pages = len(pages)
    num_batches = (total_pages + batch_size - 1) // batch_size
    
    classified_count = 0
    failed_count = 0
    start_time = time.time()
    
    for batch_num in range(num_batches):
        start_idx = batch_num * batch_size
        end_idx = min(start_idx + batch_size, total_pages)
        batch = pages[start_idx:end_idx]
        
        print(f"\n   📦 Batch {batch_num + 1}/{num_batches} ({len(batch)} pages)")
        
        for page in batch:
            page_id = page["id"]
            page_num = page["page_number"]
            text = page["text_excerpt"]  # Using stored text excerpt for classification
            
            try:
                # Classify
                result = classifier.classify(text, f"Q{page_num}")
                
                # Update database - topics is an array
                if result.page_has_question:
                    update_response = supabase.table("pages")\
                        .update({
                            "topics": [result.topic],  # Single topic in array
                            "difficulty": result.difficulty,
                            "confidence": result.confidence
                        })\
                        .eq("id", page_id)\
                        .execute()
                    
                    classified_count += 1
                    print(f"      ✅ Page {page_num}: Topic {result.topic} | {result.difficulty} | {result.confidence:.2f}")
                else:
                    print(f"      ⚠️  Page {page_num}: No question detected")
                    failed_count += 1
                    
            except Exception as e:
                print(f"      ❌ Page {page_num}: Error - {str(e)[:50]}")
                failed_count += 1
                continue
    
    elapsed = time.time() - start_time
    avg_time = elapsed / total_pages if total_pages > 0 else 0
    
    print("\n" + "=" * 80)
    print("✅ CLASSIFICATION COMPLETE")
    print("=" * 80)
    print(f"   Total pages processed: {total_pages}")
    print(f"   Successfully classified: {classified_count}")
    print(f"   Failed/Skipped: {failed_count}")
    print(f"   Time elapsed: {elapsed:.1f}s")
    print(f"   Average: {avg_time:.2f}s per page")
    
    return classified_count, failed_count


def main():
    print("\n" + "=" * 80)
    print("🔄 RECLASSIFY ALL FURTHER PURE MATHS PAPERS")
    print("=" * 80)
    print("\nThis script will:")
    print("   1. Clear ALL existing topic classifications for FPM")
    print("   2. Reclassify ALL pages using the LLM classifier")
    print("   3. Update the database with new classifications")
    
    # Get subject
    try:
        subject_id, subject_name = get_fpm_subject_id()
        print(f"\n✅ Subject: {subject_name} (ID: {subject_id})")
    except ValueError as e:
        print(f"\n❌ Error: {e}")
        return
    
    # Confirm
    print("\n⚠️  WARNING: This will delete all existing topic classifications!")
    response = input("   Continue? (yes/no): ")
    if response.lower() not in ["yes", "y"]:
        print("   Cancelled.")
        return
    
    # Clear existing classifications
    cleared_count = clear_existing_classifications(subject_id)
    
    # Initialize classifier
    print("\n📦 STEP 2: Initializing Classifier")
    print("=" * 80)
    topics_yaml = Path(__file__).parent.parent / "classification" / "further_pure_maths_topics.yaml"
    print(f"   Topics: {topics_yaml.name}")
    
    classifier = MistralTopicClassifier(
        topics_yaml_path=str(topics_yaml),
        api_key=GROQ_API_KEY,
        model_name="llama-3.1-8b-instant"
    )
    print(f"   ✅ Loaded {len(classifier.topics)} topics")
    
    # Get pages to classify
    pages = get_pages_to_classify(subject_id)
    
    if not pages:
        print("\n❌ No pages to classify")
        return
    
    # Classify
    classified, failed = classify_pages_in_batches(pages, classifier, batch_size=20)
    
    # Final summary
    print("\n" + "=" * 80)
    print("📊 FINAL SUMMARY")
    print("=" * 80)
    print(f"   Papers processed: {len(set(p['paper_id'] for p in pages))}")
    print(f"   Pages cleared: {cleared_count}")
    print(f"   Pages classified: {classified}")
    print(f"   Success rate: {(classified / len(pages) * 100):.1f}%")
    print()


if __name__ == "__main__":
    main()
