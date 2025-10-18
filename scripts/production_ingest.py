"""
PRODUCTION INGESTION PIPELINE
Subject-aware page extraction + LM Studio classification + Supabase storage
"""
import os
import sys
from pathlib import Path
import PyPDF2
from dotenv import load_dotenv
from supabase import create_client

# Add scripts to path
sys.path.append(str(Path(__file__).parent))
from final_parser import extract_questions

# Add grademax-llm-hybrid to path
sys.path.append(str(Path(__file__).parent.parent / "grademax-llm-hybrid" / "scripts"))
from lmstudio_client import LMStudioClient

load_dotenv(".env.local")

SUPABASE_URL = os.getenv("NEXT_PUBLIC_SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

def extract_pdf_pages(pdf_path: str, start_page: int, end_page: int, output_path: str):
    """Extract pages from PDF and save to new file"""
    with open(pdf_path, 'rb') as f:
        reader = PyPDF2.PdfReader(f)
        writer = PyPDF2.PdfWriter()
        
        for page_num in range(start_page, end_page + 1):
            if page_num < len(reader.pages):
                writer.add_page(reader.pages[page_num])
        
        with open(output_path, 'wb') as output:
            writer.write(output)
    
    return output_path

def upload_to_supabase_storage(file_path: str, storage_path: str) -> str:
    """Upload file to Supabase storage and return public URL"""
    with open(file_path, 'rb') as f:
        data = f.read()
    
    bucket = "subjects"
    try:
        # Try to create bucket if it doesn't exist
        try:
            supabase.storage.create_bucket(bucket, options={"public": True})
            print(f"✅ Created storage bucket: {bucket}")
        except:
            pass  # Bucket already exists
        
        response = supabase.storage.from_(bucket).upload(
            storage_path,
            data,
            file_options={"content-type": "application/pdf", "upsert": "true"}
        )
        
        # Get public URL
        url = supabase.storage.from_(bucket).get_public_url(storage_path)
        return url
    except Exception as e:
        print(f"⚠️ Upload skipped: {e}")
        # Return local path as fallback
        return f"file://{Path(file_path).absolute()}"

def ingest_paper(subject_name: str, pdf_path: str, ms_path: str, year: int, season: str, paper_num: int):
    """
    Ingest a complete paper with mark scheme
    """
    print(f"\n{'='*80}")
    print(f"📥 INGESTING: {subject_name} - {year} {season} Paper {paper_num}")
    print(f"{'='*80}\n")
    
    # Get subject
    subject = supabase.table('subjects').select('*').eq('name', subject_name).execute()
    if not subject.data:
        print(f"❌ Subject '{subject_name}' not found in database")
        return False
    
    subject_id = subject.data[0]['id']
    print(f"✅ Subject ID: {subject_id}")
    
    # Get topics
    topics = supabase.table('topics').select('*').eq('subject_id', subject_id).execute()
    topic_names = [t['name'] for t in topics.data]
    print(f"✅ Found {len(topic_names)} topics")
    
    # Create/get paper record
    paper_data = {
        'subject_id': subject_id,
        'year': year,
        'season': season,
        'paper_number': paper_num,
        'qp_source_path': str(pdf_path),
        'ms_source_path': str(ms_path) if ms_path else None
    }
    
    # Check if paper exists
    existing_paper = supabase.table('papers').select('*').match({
        'subject_id': subject_id,
        'year': year,
        'season': season,
        'paper_number': paper_num
    }).execute()
    
    if existing_paper.data:
        paper_id = existing_paper.data[0]['id']
        print(f"✅ Paper already exists: {paper_id}")
    else:
        paper_result = supabase.table('papers').insert(paper_data).execute()
        paper_id = paper_result.data[0]['id']
        print(f"✅ Created paper: {paper_id}")
    
    # Extract questions
    print(f"\n📄 Extracting questions from PDF...")
    questions = extract_questions(pdf_path)
    print(f"✅ Found {len(questions)} questions")
    
    # Initialize LM Studio client
    config_path = Path(__file__).parent.parent / "grademax-llm-hybrid" / "config" / "llm.yaml"
    try:
        llm_client = LMStudioClient(str(config_path))
        print(f"✅ LM Studio connected")
    except Exception as e:
        print(f"⚠️ LM Studio connection failed: {e}")
        print(f"   Continuing without classification...")
        llm_client = None
    
    # Process each question
    temp_dir = Path("temp_pages")
    temp_dir.mkdir(exist_ok=True)
    
    for q in questions:
        q_num = q['question_number']
        start_page = q['start_page']
        end_page = q['end_page']
        
        print(f"\n  🔹 Q{q_num} (Pages {start_page}-{end_page})")
        
        # Extract question pages
        qp_temp = temp_dir / f"q{q_num}.pdf"
        extract_pdf_pages(pdf_path, start_page, end_page, str(qp_temp))
        
        # Extract mark scheme pages (matching)
        ms_temp = None
        if ms_path and Path(ms_path).exists():
            # For now, assume MS pages match QP pages (simple heuristic)
            ms_temp = temp_dir / f"q{q_num}_ms.pdf"
            try:
                extract_pdf_pages(ms_path, start_page, end_page, str(ms_temp))
            except:
                ms_temp = None
        
        # Upload to Supabase storage
        storage_base = f"{subject_name.replace(' ', '_')}/pages/{year}_{season}_Paper{paper_num}"
        
        qp_storage_path = f"{storage_base}/q{q_num}.pdf"
        qp_url = upload_to_supabase_storage(str(qp_temp), qp_storage_path)
        
        ms_url = None
        if ms_temp:
            ms_storage_path = f"{storage_base}/q{q_num}_ms.pdf"
            ms_url = upload_to_supabase_storage(str(ms_temp), ms_storage_path)
        
        # Classify with LM Studio
        topic_ids = []
        if llm_client:
            try:
                # Read question text
                with open(qp_temp, 'rb') as f:
                    reader = PyPDF2.PdfReader(f)
                    question_text = '\n'.join([p.extract_text() for p in reader.pages])
                
                classification = llm_client.classify_question(
                    question_text=question_text[:2000],  # Limit to 2000 chars
                    subject=subject_name,
                    topics=topic_names
                )
                
                # Map topic names to IDs
                classified_topics = classification.get('topics', [])
                for topic_name in classified_topics:
                    matching_topic = next((t for t in topics.data if topic_name.lower() in t['name'].lower()), None)
                    if matching_topic:
                        topic_ids.append(matching_topic['topic_id'])
                
                print(f"     Topics: {classified_topics}")
                
            except Exception as e:
                print(f"     ⚠️ Classification failed: {e}")
        
        # Insert into pages table
        page_data = {
            'paper_id': paper_id,
            'page_number': int(q_num),  # Question number as page number
            'topics': topic_ids if topic_ids else ['1'],  # Default to first topic if classification fails
            'qp_page_url': qp_url,
            'ms_page_url': ms_url,
            'difficulty': 'medium',
            'confidence': 0.8 if llm_client else 0.5
        }
        
        try:
            result = supabase.table('pages').insert(page_data).execute()
            print(f"     ✅ Stored in database")
        except Exception as e:
            print(f"     ❌ Database error: {e}")
        
        # Cleanup temp files
        qp_temp.unlink(missing_ok=True)
        if ms_temp:
            ms_temp.unlink(missing_ok=True)
    
    print(f"\n✅ Ingestion complete!")
    return True

if __name__ == "__main__":
    # Ingest Further Pure Maths 2012 Jan Paper 1
    subject = "Further Pure Mathematics"
    qp_path = "data/raw/IGCSE/Further Pure Maths/2012/Jan/Paper 1.pdf"
    ms_path = "data/raw/IGCSE/Further Pure Maths/2012/Jan/Paper 1_MS.pdf"
    
    success = ingest_paper(
        subject_name=subject,
        pdf_path=qp_path,
        ms_path=ms_path,
        year=2012,
        season="Jan",
        paper_num=1
    )
    
    sys.exit(0 if success else 1)
