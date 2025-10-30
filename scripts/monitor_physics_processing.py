"""
Physics Processing Monitor
Tracks progress of paper processing in real-time
Shows statistics on questions extracted, uploaded, and classified
"""

import os
from pathlib import Path
from supabase import create_client
from dotenv import load_dotenv
from datetime import datetime
import json
from collections import defaultdict

# Load environment variables from correct path
env_path = Path(__file__).parent.parent / '.env.local'
load_dotenv(env_path)

# Initialize Supabase
supabase = create_client(
    os.getenv("NEXT_PUBLIC_SUPABASE_URL"),
    os.getenv("SUPABASE_SERVICE_ROLE_KEY")
)

PHYSICS_SUBJECT_ID = "0b142517-d35d-4942-91aa-b4886aaabca3"

def get_physics_stats():
    """Get comprehensive statistics on Physics processing"""
    
    print("=" * 80)
    print("PHYSICS PROCESSING MONITOR")
    print("=" * 80)
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    # Get paper statistics
    papers_response = supabase.table("papers").select("*").eq("subject_id", PHYSICS_SUBJECT_ID).execute()
    papers = papers_response.data
    
    print(f"📄 PAPERS")
    print(f"   Total papers in database: {len(papers)}")
    
    if papers:
        # Group by year
        papers_by_year = defaultdict(list)
        for paper in papers:
            papers_by_year[paper['year']].append(paper)
        
        print(f"   Years covered: {min(papers_by_year.keys())} - {max(papers_by_year.keys())}")
        print(f"   Papers by year:")
        for year in sorted(papers_by_year.keys()):
            print(f"      {year}: {len(papers_by_year[year])} papers")
    
    print()
    
    # Get page statistics
    if papers:
        paper_ids = [p['id'] for p in papers]
        pages_response = supabase.table("pages").select("*").in_("paper_id", paper_ids).execute()
        pages = pages_response.data
        
        print(f"❓ QUESTIONS")
        print(f"   Total questions extracted: {len(pages)}")
        
        if pages:
            # Questions per paper stats
            questions_per_paper = defaultdict(int)
            for page in pages:
                questions_per_paper[page['paper_id']] += 1
            
            avg_questions = sum(questions_per_paper.values()) / len(questions_per_paper)
            print(f"   Average questions per paper: {avg_questions:.1f}")
            print(f"   Min questions in a paper: {min(questions_per_paper.values())}")
            print(f"   Max questions in a paper: {max(questions_per_paper.values())}")
            
            # Check uploads
            qp_uploaded = sum(1 for p in pages if p.get('qp_page_url'))
            ms_uploaded = sum(1 for p in pages if p.get('ms_page_url'))
            
            print(f"\n📤 UPLOADS")
            print(f"   Question papers uploaded: {qp_uploaded}/{len(pages)} ({qp_uploaded/len(pages)*100:.1f}%)")
            print(f"   Mark schemes uploaded: {ms_uploaded}/{len(pages)} ({ms_uploaded/len(pages)*100:.1f}%)")
            
            # Classification statistics
            classified = sum(1 for p in pages if p.get('topics') and len(p['topics']) > 0)
            
            print(f"\n🏷️  CLASSIFICATION")
            print(f"   Classified questions: {classified}/{len(pages)} ({classified/len(pages)*100:.1f}%)")
            
            if classified > 0:
                # Topic distribution
                topic_counts = defaultdict(int)
                for page in pages:
                    if page.get('topics'):
                        for topic in page['topics']:
                            topic_counts[topic] += 1
                
                print(f"\n   Topic Distribution:")
                for topic, count in sorted(topic_counts.items(), key=lambda x: x[1], reverse=True):
                    print(f"      {topic}: {count} questions")
            
            # Unclassified questions
            unclassified = [p for p in pages if not p.get('topics') or len(p['topics']) == 0]
            if unclassified:
                print(f"\n   ⚠️  Unclassified Questions: {len(unclassified)}")
                
                # Group by paper
                unclassified_by_paper = defaultdict(list)
                for page in unclassified:
                    paper = next((p for p in papers if p['id'] == page['paper_id']), None)
                    if paper:
                        key = f"{paper['year']} {paper['season']} P{paper['paper_number']}"
                        unclassified_by_paper[key].append(page['question_number'])
                
                for paper_name, questions in sorted(unclassified_by_paper.items()):
                    print(f"      {paper_name}: Q{', Q'.join(map(str, sorted(questions)))}")
        else:
            print(f"   No questions found in database")
    else:
        print(f"❓ QUESTIONS")
        print(f"   No papers in database yet")
    
    print()
    
    # Storage check
    print(f"💾 STORAGE")
    try:
        # List files in Physics folder
        storage_response = supabase.storage.from_("question-pdfs").list("subjects/Physics/pages")
        
        if storage_response:
            print(f"   Folders in storage: {len(storage_response)}")
            
            # Count total files
            total_files = 0
            for folder in storage_response:
                folder_contents = supabase.storage.from_("question-pdfs").list(f"subjects/Physics/pages/{folder['name']}")
                if folder_contents:
                    total_files += len(folder_contents)
            
            print(f"   Total files uploaded: {total_files}")
        else:
            print(f"   No files in storage yet")
    except Exception as e:
        print(f"   ⚠️  Could not check storage: {str(e)}")
    
    print()
    
    # Processing recommendations
    print(f"💡 RECOMMENDATIONS")
    if len(papers) == 0:
        print(f"   ➡️  Start processing papers with process_physics_offline.py")
    elif pages and classified < len(pages):
        remaining = len(pages) - classified
        print(f"   ➡️  Classify remaining {remaining} questions")
        print(f"   ➡️  Estimated time: {remaining * 5 / 60:.1f} minutes (5s per question)")
    else:
        print(f"   ✅ All processing complete! Ready for worksheet generation.")
    
    print()
    print("=" * 80)

def compare_with_fpm():
    """Compare Physics progress with FPM (benchmark)"""
    
    print("\n" + "=" * 80)
    print("COMPARISON WITH FPM (BENCHMARK)")
    print("=" * 80)
    
    # Get FPM stats
    fpm_subject_id = "bc06b13f-1d64-4c83-b4e4-d8d43c0d7bca"
    fpm_papers = supabase.table("papers").select("*").eq("subject_id", fpm_subject_id).execute().data
    
    if fpm_papers:
        fpm_paper_ids = [p['id'] for p in fpm_papers]
        fpm_pages = supabase.table("pages").select("*").in_("paper_id", fpm_paper_ids).execute().data
        fpm_classified = sum(1 for p in fpm_pages if p.get('topics') and len(p['topics']) > 0)
        
        print(f"\n📊 FPM Stats:")
        print(f"   Papers: {len(fpm_papers)}")
        print(f"   Questions: {len(fpm_pages)}")
        print(f"   Classified: {fpm_classified}/{len(fpm_pages)} ({fpm_classified/len(fpm_pages)*100:.1f}%)")
    
    # Get Physics stats
    physics_papers = supabase.table("papers").select("*").eq("subject_id", PHYSICS_SUBJECT_ID).execute().data
    
    if physics_papers:
        physics_paper_ids = [p['id'] for p in physics_papers]
        physics_pages = supabase.table("pages").select("*").in_("paper_id", physics_paper_ids).execute().data
        physics_classified = sum(1 for p in physics_pages if p.get('topics') and len(p['topics']) > 0)
        
        print(f"\n📊 Physics Stats:")
        print(f"   Papers: {len(physics_papers)}")
        print(f"   Questions: {len(physics_pages)}")
        print(f"   Classified: {physics_classified}/{len(physics_pages)} ({physics_classified/len(physics_pages)*100:.1f}%)")
        
        if fpm_papers:
            print(f"\n📈 Progress:")
            print(f"   Papers: {len(physics_papers)}/{len(fpm_papers)} ({len(physics_papers)/len(fpm_papers)*100:.1f}%)")
            print(f"   Questions: {len(physics_pages)}/{len(fpm_pages)} ({len(physics_pages)/len(fpm_pages)*100:.1f}%)")
    else:
        print(f"\n📊 Physics Stats:")
        print(f"   No data yet - starting from scratch")
    
    print("=" * 80)

def export_progress_report():
    """Export detailed progress report to JSON"""
    
    papers = supabase.table("papers").select("*").eq("subject_id", PHYSICS_SUBJECT_ID).execute().data
    
    report = {
        "timestamp": datetime.now().isoformat(),
        "total_papers": len(papers),
        "papers": []
    }
    
    if papers:
        paper_ids = [p['id'] for p in papers]
        pages = supabase.table("pages").select("*").in_("paper_id", paper_ids).execute().data
        
        for paper in papers:
            paper_pages = [p for p in pages if p['paper_id'] == paper['id']]
            classified = sum(1 for p in paper_pages if p.get('topics') and len(p['topics']) > 0)
            
            report["papers"].append({
                "year": paper['year'],
                "season": paper['season'],
                "paper_number": paper['paper_number'],
                "total_questions": len(paper_pages),
                "classified": classified,
                "classification_rate": classified / len(paper_pages) * 100 if paper_pages else 0,
                "questions": [
                    {
                        "question_number": p['question_number'],
                        "topics": p.get('topics', []),
                        "qp_uploaded": bool(p.get('qp_page_url')),
                        "ms_uploaded": bool(p.get('ms_page_url'))
                    }
                    for p in sorted(paper_pages, key=lambda x: x['question_number'])
                ]
            })
    
    # Save report
    report_path = "config/physics_processing_report.json"
    with open(report_path, 'w') as f:
        json.dump(report, f, indent=2)
    
    print(f"\n📄 Detailed report saved to: {report_path}")

if __name__ == "__main__":
    get_physics_stats()
    compare_with_fpm()
    export_progress_report()
