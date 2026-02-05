#!/usr/bin/env python3
"""
Download Mathematics B (4MB1) papers from Physics and Maths Tutor

Paper 1: https://www.physicsandmathstutor.com/past-papers/gcse-maths/edexcel-igcse-b-paper-1/
Paper 2: https://www.physicsandmathstutor.com/past-papers/gcse-maths/edexcel-igcse-b-paper-2/
"""

import os
import re
import time
import requests
from pathlib import Path
from bs4 import BeautifulSoup
from urllib.parse import urljoin

# Output directory
OUTPUT_DIR = Path(__file__).parent.parent / "data" / "raw" / "IGCSE" / "Maths B"

# PMT URLs
PAPER_1_URL = "https://www.physicsandmathstutor.com/past-papers/gcse-maths/edexcel-igcse-b-paper-1/"
PAPER_2_URL = "https://www.physicsandmathstutor.com/past-papers/gcse-maths/edexcel-igcse-b-paper-2/"

# Headers to mimic browser
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.5',
    'Connection': 'keep-alive',
}


def get_pdf_links(page_url: str) -> list:
    """Extract PDF links from a PMT page"""
    print(f"Fetching: {page_url}")
    
    try:
        response = requests.get(page_url, headers=HEADERS, timeout=30)
        response.raise_for_status()
    except Exception as e:
        print(f"  ❌ Failed to fetch page: {e}")
        return []
    
    soup = BeautifulSoup(response.text, 'html.parser')
    
    # Find all PDF links
    pdf_links = []
    for link in soup.find_all('a', href=True):
        href = link['href']
        if '.pdf' in href.lower():
            full_url = urljoin(page_url, href)
            link_text = link.get_text(strip=True)
            pdf_links.append({
                'url': full_url,
                'text': link_text
            })
    
    print(f"  Found {len(pdf_links)} PDF links")
    return pdf_links


def parse_paper_info(url: str, text: str, paper_num: str) -> dict:
    """Parse year and type from URL/text"""
    info = {
        'url': url,
        'paper_number': paper_num,
        'year': None,
        'session': 'May-Jun',
        'is_ms': False
    }
    
    # Check if mark scheme
    url_lower = url.lower()
    text_lower = text.lower()
    if 'mark' in url_lower or 'ms' in url_lower or 'mark' in text_lower:
        info['is_ms'] = True
    
    # Extract year from URL or text
    year_match = re.search(r'20(\d{2})', url + text)
    if year_match:
        info['year'] = int('20' + year_match.group(1))
    
    # Try to get session
    if 'jan' in url_lower or 'jan' in text_lower:
        info['session'] = 'Jan'
    elif 'oct' in url_lower or 'nov' in url_lower or 'oct' in text_lower or 'nov' in text_lower:
        info['session'] = 'Oct-Nov'
    elif 'jun' in url_lower or 'may' in url_lower or 'jun' in text_lower or 'may' in text_lower:
        info['session'] = 'May-Jun'
    
    return info


def download_pdf(url: str, output_path: Path) -> bool:
    """Download a PDF file"""
    try:
        response = requests.get(url, headers=HEADERS, timeout=60, stream=True)
        response.raise_for_status()
        
        # Check content type
        content_type = response.headers.get('content-type', '')
        if 'pdf' not in content_type.lower() and 'octet-stream' not in content_type.lower():
            print(f"    ⚠️  Not a PDF: {content_type}")
            # Still try to save if it looks like a PDF URL
        
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        
        # Verify file size
        size = output_path.stat().st_size
        if size < 1000:
            print(f"    ⚠️  File too small ({size} bytes), may be invalid")
            return False
        
        return True
    except Exception as e:
        print(f"    ❌ Download failed: {e}")
        return False


def download_all_papers():
    """Download all Math B papers"""
    print("=" * 70)
    print("📥 DOWNLOADING MATHEMATICS B PAPERS")
    print("=" * 70)
    
    # Ensure output directory exists
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    downloaded = 0
    skipped = 0
    failed = 0
    
    # Process both paper types
    for paper_num, url in [('1', PAPER_1_URL), ('2', PAPER_2_URL)]:
        print(f"\n📄 Paper {paper_num}")
        print("-" * 40)
        
        links = get_pdf_links(url)
        
        for link in links:
            info = parse_paper_info(link['url'], link['text'], paper_num)
            
            if not info['year']:
                print(f"  ⏭️  Skipping (no year): {link['text'][:50]}")
                continue
            
            # Skip if year is too old or too new
            if info['year'] < 2017 or info['year'] > 2025:
                print(f"  ⏭️  Skipping year {info['year']}")
                continue
            
            # Build output path
            year_dir = OUTPUT_DIR / str(info['year']) / info['session']
            
            if info['is_ms']:
                filename = f"Paper {paper_num}_MS.pdf"
            else:
                filename = f"Paper {paper_num}.pdf"
            
            output_path = year_dir / filename
            
            # Check if already exists
            if output_path.exists():
                print(f"  ⏭️  Already exists: {output_path.relative_to(OUTPUT_DIR)}")
                skipped += 1
                continue
            
            # Download
            print(f"  📥 Downloading: {info['year']} {info['session']} Paper {paper_num} {'(MS)' if info['is_ms'] else '(QP)'}")
            
            if download_pdf(link['url'], output_path):
                size_kb = output_path.stat().st_size / 1024
                print(f"    ✅ Saved ({size_kb:.1f} KB): {output_path.relative_to(OUTPUT_DIR)}")
                downloaded += 1
            else:
                failed += 1
            
            # Rate limiting
            time.sleep(1)
    
    # Summary
    print("\n" + "=" * 70)
    print("📊 DOWNLOAD SUMMARY")
    print("=" * 70)
    print(f"  Downloaded: {downloaded}")
    print(f"  Skipped (already exist): {skipped}")
    print(f"  Failed: {failed}")
    
    # List what we have
    print("\n📁 Downloaded files:")
    for year_dir in sorted(OUTPUT_DIR.iterdir()):
        if year_dir.is_dir():
            for session_dir in year_dir.iterdir():
                if session_dir.is_dir():
                    files = list(session_dir.glob("*.pdf"))
                    if files:
                        print(f"  {year_dir.name}/{session_dir.name}/")
                        for f in sorted(files):
                            print(f"    - {f.name}")


if __name__ == "__main__":
    download_all_papers()
