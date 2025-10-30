"""
Offline Physics Paper Processor

Uses the segmentation rules from physics_segmentation_rules.json to process
all Physics papers WITHOUT needing LLM calls.

This processor:
1. Loads the deterministic rules
2. Extracts layout from PDFs
3. Applies rules to segment questions
4. Links to mark schemes
5. Creates question PDFs and uploads them
6. Creates database records
"""

import os
import sys
import json
import re
from pathlib import Path
from dotenv import load_dotenv
from supabase import create_client, Client
import PyPDF2
import pdfplumber

# Load environment
env_path = Path(__file__).parent.parent / '.env.local'
load_dotenv(env_path)

SUPABASE_URL = os.getenv("NEXT_PUBLIC_SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# Constants
RULES_PATH = Path(__file__).parent.parent / "config" / "physics_segmentation_rules.json"
BUCKET_NAME = "question-pdfs"
SUBJECT = "Physics"
SUBJECT_ID = "0b142517-d35d-4942-91aa-b4886aaabca3"
RAW_DATA_DIR = Path("data/raw/IGCSE/Physics")
PROCESSED_DIR = Path("data/processed/Physics")

# Load rules
with open(RULES_PATH, 'r', encoding='utf-8') as f:
    RULES = json.load(f)

print(f"✅ Loaded segmentation rules v{RULES['version']}")


def extract_lines_with_positions(pdf_path):
    """Extract text lines with position information."""
    pages_data = []
    
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page_num, page in enumerate(pdf.pages):
                words = page.extract_words(x_tolerance=3, y_tolerance=3)
                
                # Group into lines by y-position
                lines = {}
                for word in words:
                    y_pos = round(word['top'], 1)
                    if y_pos not in lines:
                        lines[y_pos] = []
                    lines[y_pos].append(word)
                
                # Sort lines top to bottom
                page_lines = []
                for y_pos in sorted(lines.keys()):
                    line_words = lines[y_pos]
                    line_text = " ".join([w['text'] for w in line_words])
                    min_x = min([w['x0'] for w in line_words])
                    
                    page_lines.append({
                        "text": line_text,
                        "x_pos": min_x,
                        "y_pos": y_pos
                    })
                
                pages_data.append({
                    "page_index": page_num,
                    "lines": page_lines
                })
    
    except Exception as e:
        print(f"Error extracting from {pdf_path}: {e}")
    
    return pages_data


def segment_qp_questions(qp_pages_data):
    """
    Segment QP into questions using the rules.
    
    Returns: list of dicts with {qnum, start_page, end_page, qp_pages[]}
    """
    questions = []
    current_question = None
    
    # Get rules
    start_pattern = re.compile(RULES['qp_rules']['question_start']['text_pattern'])
    end_pattern = RULES['qp_rules']['question_end']['primary_pattern']
    max_qnum = RULES['qp_rules']['question_start'].get('max_question_number', 20)
    
    for page_data in qp_pages_data:
        page_idx = page_data['page_index']
        
        for line in page_data['lines']:
            text = line['text'].strip()
            x_pos = line['x_pos']
            
            # Check position rules - updated for 2011-2024 papers (x: 40-170)
            if x_pos < 40 or x_pos > 170:
                continue
            
            # Check for question start
            if start_pattern.match(text):
                # Extract question number
                qnum_str = text.split()[0].rstrip('.')
                
                # Validate it's a reasonable question number
                try:
                    qnum_int = int(qnum_str)
                    if qnum_int < 1 or qnum_int > max_qnum:
                        continue
                except:
                    continue
                
                # Save previous question if exists
                if current_question:
                    questions.append(current_question)
                
                # Start new question
                current_question = {
                    "qnum": qnum_str,
                    "start_page": page_idx,
                    "qp_pages": [page_idx]
                }
            
            # Check for question end
            elif end_pattern in text and current_question:
                current_question['end_page'] = page_idx
                if page_idx not in current_question['qp_pages']:
                    current_question['qp_pages'].append(page_idx)
                # Don't append yet - might span to next page
            
            # Add current page to current question
            elif current_question and page_idx not in current_question['qp_pages']:
                current_question['qp_pages'].append(page_idx)
    
    # Add last question
    if current_question:
        questions.append(current_question)
    
    return questions


def link_ms_pages(questions, ms_pages_data):
    """
    Link each question to its mark scheme pages using improved rules.
    
    Uses:
    - Position-based question detection (x-position 40-100)
    - "Total for Question N" as section end marker
    - Skips intro pages with keywords
    """
    ms_total_pattern = re.compile(r"Total for [Qq]uestion (\d+)", re.IGNORECASE)
    
    # Get rules
    x_min, x_max = RULES['ms_rules']['question_detection']['x_range']
    intro_keywords = RULES['ms_rules']['page_detection']['intro_keywords']
    
    # Build MS sections
    ms_sections = {}  # {qnum: [page_indices]}
    current_qnum = None
    in_content = False
    
    for page_data in ms_pages_data:
        page_idx = page_data['page_index']
        
        # Check if we're past intro pages
        page_text = " ".join([line['text'] for line in page_data['lines']])
        
        # Skip intro pages
        if not in_content:
            if any(keyword in page_text for keyword in intro_keywords):
                continue
            # Look for table header - this page IS content, don't skip
            if "Question" in page_text and "Answer" in page_text and "Marks" in page_text:
                in_content = True
                # Don't continue - process this page as it may contain Q1
        
        if not in_content:
            continue
        
        # Look for question numbers in the correct position and format
        for line in page_data['lines']:
            text = line['text'].strip()
            x_pos = line['x_pos']
            
            # Must be in question number column
            if x_pos < x_min or x_pos > x_max:
                continue
            
            # Detect question number with sub-part: "1 (a)", "2 (b)", etc.
            # Pattern: digit(s), optional space, then (letter) or just letter
            match = re.match(r'^(\d+)\s*[\(]?[a-z]?', text)
            if match and len(text.split()[0]) <= 3:
                qnum = match.group(1)
                
                # Only update current_qnum if it's a main question number (appears alone or with (a))
                # This prevents sub-questions from creating new sections
                if text.startswith(qnum + " ") or text.startswith(qnum + "("):
                    current_qnum = qnum
                    if current_qnum not in ms_sections:
                        ms_sections[current_qnum] = []
            
            # Check for section end marker
            match = ms_total_pattern.search(text)
            if match:
                end_qnum = match.group(1)
                if end_qnum in ms_sections and page_idx not in ms_sections[end_qnum]:
                    ms_sections[end_qnum].append(page_idx)
                # Reset current question after total marker
                current_qnum = None
        
        # Add current page to current question
        if current_qnum:
            if page_idx not in ms_sections.get(current_qnum, []):
                if current_qnum not in ms_sections:
                    ms_sections[current_qnum] = []
                ms_sections[current_qnum].append(page_idx)
    
    # Link to questions
    for question in questions:
        qnum = question['qnum']
        question['ms_pages'] = sorted(set(ms_sections.get(qnum, [])))
    
    return questions


def extract_pdf_pages(input_pdf, output_pdf, page_indices):
    """Extract specific pages from PDF."""
    reader = PyPDF2.PdfReader(input_pdf)
    writer = PyPDF2.PdfWriter()
    
    for idx in sorted(page_indices):
        if 0 <= idx < len(reader.pages):
            writer.add_page(reader.pages[idx])
    
    os.makedirs(os.path.dirname(output_pdf), exist_ok=True)
    with open(output_pdf, 'wb') as f:
        writer.write(f)


def upload_to_storage(local_path, storage_path):
    """Upload file to Supabase storage."""
    with open(local_path, 'rb') as f:
        file_data = f.read()
    
    supabase.storage.from_(BUCKET_NAME).upload(
        storage_path,
        file_data,
        file_options={"content-type": "application/pdf"}
    )
    
    return supabase.storage.from_(BUCKET_NAME).get_public_url(storage_path)


def process_paper(year, season, paper_number, qp_path, ms_path):
    """Process a single paper using offline rules."""
    print(f"\n{'='*80}")
    print(f"Processing: {year} {season} Paper {paper_number}")
    print(f"{'='*80}")
    
    # Step 1: Extract layout
    print("\n[1/6] Extracting layout...")
    qp_data = extract_lines_with_positions(qp_path)
    ms_data = extract_lines_with_positions(ms_path)
    print(f"  QP: {len(qp_data)} pages, MS: {len(ms_data)} pages")
    
    # Step 2: Segment questions
    print("\n[2/6] Segmenting questions using rules...")
    questions = segment_qp_questions(qp_data)
    print(f"  ✅ Found {len(questions)} questions")
    
    # Step 3: Link mark schemes
    print("\n[3/6] Linking mark schemes...")
    questions = link_ms_pages(questions, ms_data)
    for q in questions:
        print(f"  Q{q['qnum']}: QP pages {q['qp_pages']}, MS pages {q['ms_pages']}")
    
    # Step 4: Create paper record
    print("\n[4/6] Creating database record...")
    # Check if paper exists
    response = supabase.table("papers").select("id").eq("subject_id", SUBJECT_ID).eq("year", year).eq("season", season).eq("paper_number", paper_number).execute()
    
    if response.data:
        paper_id = response.data[0]["id"]
    else:
        paper_data = {
            "subject_id": SUBJECT_ID,
            "year": year,
            "season": season,
            "paper_number": paper_number,
            "total_pages": len(questions)
        }
        insert_response = supabase.table("papers").insert(paper_data).execute()
        paper_id = insert_response.data[0]["id"]
    
    print(f"  ✅ Paper ID: {paper_id}")
    
    # Step 5: Extract and upload PDFs
    print("\n[5/6] Creating and uploading question PDFs...")
    storage_prefix = f"subjects/{SUBJECT}/pages/Phy_{year}_{season}_{paper_number}"
    local_dir = PROCESSED_DIR / f"{year}_{season}_Paper{paper_number}"
    
    for q in questions:
        qnum = q['qnum']
        
        # Extract QP
        qp_local = local_dir / f"q{qnum}.pdf"
        extract_pdf_pages(qp_path, str(qp_local), q['qp_pages'])
        qp_storage_path = f"{storage_prefix}/q{qnum}.pdf"
        qp_url = upload_to_storage(str(qp_local), qp_storage_path)
        
        # Extract MS
        ms_local = local_dir / f"q{qnum}_ms.pdf"
        if q['ms_pages']:
            extract_pdf_pages(ms_path, str(ms_local), q['ms_pages'])
            ms_storage_path = f"{storage_prefix}/q{qnum}_ms.pdf"
            ms_url = upload_to_storage(str(ms_local), ms_storage_path)
        else:
            ms_url = None
        
        # Create page record
        page_data = {
            "paper_id": paper_id,
            "page_number": int(qnum),
            "question_number": int(qnum),
            "topics": [],
            "qp_page_url": qp_url,
            "ms_page_url": ms_url,
            "text_excerpt": f"Question {qnum}"
        }
        supabase.table("pages").insert(page_data).execute()
        
        print(f"  ✅ Q{qnum}: Uploaded")
    
    print(f"\n[6/6] ✅ Complete: {year} {season} Paper {paper_number}")
    return len(questions)


def get_all_papers():
    """Scan for all Physics papers."""
    papers = []
    
    for year_dir in sorted(RAW_DATA_DIR.iterdir()):
        if not year_dir.is_dir():
            continue
        year = int(year_dir.name)
        
        for season_dir in sorted(year_dir.iterdir()):
            if not season_dir.is_dir():
                continue
            season = season_dir.name
            
            qp_files = [f for f in season_dir.glob("Paper *.pdf") if not f.name.endswith("_MS.pdf")]
            
            for qp_file in qp_files:
                paper_number = int(qp_file.stem.replace("Paper ", ""))
                ms_file = season_dir / f"Paper {paper_number}_MS.pdf"
                
                if ms_file.exists():
                    papers.append({
                        "year": year,
                        "season": season,
                        "paper_number": paper_number,
                        "qp_path": str(qp_file),
                        "ms_path": str(ms_file)
                    })
    
    return papers


def main():
    """Main processing function."""
    print("="*80)
    print("OFFLINE PHYSICS PROCESSOR")
    print("="*80)
    print(f"Rules: {RULES['version']} - {RULES['description']}")
    print()
    
    papers = get_all_papers()
    print(f"✅ Found {len(papers)} papers to process\n")
    
    success_count = 0
    total_questions = 0
    
    for i, paper in enumerate(papers[:3], 1):  # Start with first 3 papers for testing
        print(f"\n{'#'*80}")
        print(f"# Paper {i}/{min(3, len(papers))}")
        print(f"{'#'*80}")
        
        try:
            num_questions = process_paper(
                year=paper['year'],
                season=paper['season'],
                paper_number=paper['paper_number'],
                qp_path=paper['qp_path'],
                ms_path=paper['ms_path']
            )
            success_count += 1
            total_questions += num_questions
        except Exception as e:
            print(f"\n❌ FAILED: {e}")
            import traceback
            traceback.print_exc()
    
    print(f"\n\n{'='*80}")
    print("SUMMARY")
    print(f"{'='*80}")
    print(f"✅ Successful: {success_count}/{min(3, len(papers))}")
    print(f"📝 Total questions processed: {total_questions}")


if __name__ == "__main__":
    main()
