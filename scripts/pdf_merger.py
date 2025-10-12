#!/usr/bin/env python3
"""
PDF Merger Service - Combines multiple PDFs from Supabase Storage
Used by worksheet generation to create combined Worksheet.pdf and Markscheme.pdf
"""

import sys
import requests
from pathlib import Path
from typing import List
from io import BytesIO
from PyPDF2 import PdfMerger
import os


class PDFMergerService:
    """Merge PDFs from Supabase Storage"""
    
    def __init__(self, supabase_url: str, bucket: str = "question-pdfs"):
        self.supabase_url = supabase_url.rstrip('/')
        self.bucket = bucket
        self.storage_base = f"{self.supabase_url}/storage/v1/object/public/{bucket}"
    
    def merge_pdfs(self, storage_paths: List[str], output_path: str) -> str:
        """
        Merge multiple PDFs from storage into one file
        
        Args:
            storage_paths: List of storage paths (e.g., ["subjects/Physics/pages/2019_Jun_1P/q1.pdf"])
            output_path: Where to save the merged PDF
            
        Returns:
            Path to merged PDF
        """
        merger = PdfMerger()
        
        print(f"📄 Merging {len(storage_paths)} PDFs...")
        
        for i, path in enumerate(storage_paths, 1):
            try:
                # Build full URL
                url = f"{self.storage_base}/{path}"
                
                # Download PDF
                response = requests.get(url, timeout=30)
                response.raise_for_status()
                
                # Add to merger
                pdf_file = BytesIO(response.content)
                merger.append(pdf_file)
                
                print(f"   ✅ [{i}/{len(storage_paths)}] {path}")
                
            except Exception as e:
                print(f"   ❌ [{i}/{len(storage_paths)}] {path}: {e}")
                continue
        
        # Write merged PDF
        merger.write(output_path)
        merger.close()
        
        print(f"✅ Merged PDF saved: {output_path}")
        return output_path
    
    def create_worksheet_pdfs(
        self,
        qp_paths: List[str],
        ms_paths: List[str],
        worksheet_id: str,
        output_dir: str = "data/generated"
    ) -> tuple:
        """
        Create both Worksheet.pdf and Markscheme.pdf
        
        Returns:
            (worksheet_path, markscheme_path)
        """
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Merge worksheet
        worksheet_path = output_dir / f"{worksheet_id}_worksheet.pdf"
        self.merge_pdfs(qp_paths, str(worksheet_path))
        
        # Merge markscheme (filter out None values)
        ms_paths_clean = [p for p in ms_paths if p]
        if ms_paths_clean:
            markscheme_path = output_dir / f"{worksheet_id}_markscheme.pdf"
            self.merge_pdfs(ms_paths_clean, str(markscheme_path))
        else:
            markscheme_path = None
            print("⚠️  No mark schemes available")
        
        return str(worksheet_path), str(markscheme_path) if markscheme_path else None


def main():
    """CLI for testing"""
    if len(sys.argv) < 2:
        print("Usage: python pdf_merger.py <url1> <url2> ... <output.pdf>")
        sys.exit(1)
    
    supabase_url = os.getenv('NEXT_PUBLIC_SUPABASE_URL', 'https://tybaetnvnfgniotdfxze.supabase.co')
    
    urls = sys.argv[1:-1]
    output = sys.argv[-1]
    
    merger = PDFMergerService(supabase_url)
    merger.merge_pdfs(urls, output)


if __name__ == "__main__":
    main()
