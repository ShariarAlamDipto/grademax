#!/usr/bin/env python3
"""
OCR Processing for Corrupted/Image-based PDFs
Converts image-based or corrupted PDFs to searchable text PDFs
"""

import fitz  # PyMuPDF
from pathlib import Path
import subprocess
import shutil
import sys

def check_pdf_quality(pdf_path: Path) -> dict:
    """Check if PDF needs OCR"""
    doc = fitz.open(str(pdf_path))
    
    total_chars = 0
    corrupted = False
    
    for page_num in range(min(5, len(doc))):
        text = doc[page_num].get_text()
        total_chars += len(text)
        
        # Check for corruption markers
        if '\x06' in text or '\x0f' in text or text.count('␦') > 10:
            corrupted = True
    
    doc.close()
    
    avg_chars = total_chars / min(5, len(doc))
    needs_ocr = corrupted or avg_chars < 100
    
    return {
        'avg_chars': avg_chars,
        'corrupted': corrupted,
        'needs_ocr': needs_ocr
    }


def ocr_pdf_with_ocrmypdf(input_path: Path, output_path: Path) -> bool:
    """
    Use ocrmypdf to add OCR layer to PDF
    This is the most robust method
    """
    try:
        print(f"   Running OCR with ocrmypdf...")
        
        # Run ocrmypdf
        result = subprocess.run([
            'ocrmypdf',
            '--force-ocr',  # Force OCR even if text exists
            '--optimize', '1',  # Basic optimization
            '--output-type', 'pdf',
            str(input_path),
            str(output_path)
        ], capture_output=True, text=True, timeout=300)
        
        if result.returncode == 0:
            print(f"   ✅ OCR successful")
            return True
        else:
            print(f"   ❌ OCR failed: {result.stderr}")
            return False
            
    except FileNotFoundError:
        print(f"   ⚠️  ocrmypdf not found. Install Tesseract and ocrmypdf:")
        print(f"      Windows: choco install tesseract")
        print(f"      Or download from: https://github.com/UB-Mannheim/tesseract/wiki")
        return False
    except subprocess.TimeoutExpired:
        print(f"   ❌ OCR timed out (>5 minutes)")
        return False
    except Exception as e:
        print(f"   ❌ OCR error: {e}")
        return False


def ocr_pdf_fallback(input_path: Path, output_path: Path) -> bool:
    """
    Fallback OCR method using pdf2image and pytesseract
    """
    try:
        from pdf2image import convert_from_path
        import pytesseract
        from PIL import Image
        import io
        
        print(f"   Running fallback OCR (pdf2image + pytesseract)...")
        
        # Convert PDF to images
        images = convert_from_path(str(input_path), dpi=300)
        
        # Create new PDF with OCR text
        doc = fitz.open()
        
        for i, image in enumerate(images):
            print(f"      Processing page {i+1}/{len(images)}...")
            
            # Convert PIL image to bytes
            img_bytes = io.BytesIO()
            image.save(img_bytes, format='PNG')
            img_bytes.seek(0)
            
            # Create page
            page = doc.new_page(width=image.width, height=image.height)
            
            # Insert image
            page.insert_image(page.rect, stream=img_bytes.getvalue())
            
            # Get OCR text
            ocr_text = pytesseract.image_to_string(image)
            
            # Add invisible text layer (for searchability)
            # Note: This is a simplified approach
            if ocr_text.strip():
                page.insert_text((50, 50), ocr_text, fontsize=8, color=(1, 1, 1))
        
        doc.save(str(output_path))
        doc.close()
        
        print(f"   ✅ Fallback OCR successful")
        return True
        
    except ImportError as e:
        print(f"   ❌ Missing dependencies: {e}")
        return False
    except Exception as e:
        print(f"   ❌ Fallback OCR failed: {e}")
        return False


def process_corrupted_pdfs():
    """Process all corrupted PDFs"""
    
    corrupted_files = [
        {
            'path': 'data/raw/IGCSE/Physics/2013/May-Jun/Paper 1.pdf',
            'backup': 'data/raw/IGCSE/Physics/2013/May-Jun/Paper 1_CORRUPTED_BACKUP.pdf',
            'name': '2013 Jun P1'
        },
        {
            'path': 'data/raw/IGCSE/Physics/2019/May-Jun/Paper 1.pdf',
            'backup': 'data/raw/IGCSE/Physics/2019/May-Jun/Paper 1_IMAGE_BACKUP.pdf',
            'name': '2019 Jun P1'
        }
    ]
    
    print("="*80)
    print("OCR PROCESSING FOR CORRUPTED PDFs")
    print("="*80)
    print()
    
    for file_info in corrupted_files:
        pdf_path = Path(file_info['path'])
        backup_path = Path(file_info['backup'])
        
        if not pdf_path.exists():
            print(f"❌ {file_info['name']}: File not found")
            continue
        
        print(f"\n📄 Processing: {file_info['name']}")
        print(f"   Path: {pdf_path}")
        
        # Check if already processed
        if backup_path.exists():
            print(f"   ⏭️  Already has backup - skipping")
            continue
        
        # Check quality
        quality = check_pdf_quality(pdf_path)
        print(f"   Quality check:")
        print(f"      Avg chars/page: {quality['avg_chars']:.0f}")
        print(f"      Corrupted: {quality['corrupted']}")
        print(f"      Needs OCR: {quality['needs_ocr']}")
        
        if not quality['needs_ocr']:
            print(f"   ✅ PDF is fine - no OCR needed")
            continue
        
        # Create backup
        print(f"   💾 Creating backup...")
        shutil.copy(pdf_path, backup_path)
        
        # Try OCR
        temp_output = pdf_path.with_suffix('.ocr.pdf')
        
        # Try ocrmypdf first (best quality)
        success = ocr_pdf_with_ocrmypdf(pdf_path, temp_output)
        
        if not success:
            # Fallback to pytesseract method
            success = ocr_pdf_fallback(pdf_path, temp_output)
        
        if success and temp_output.exists():
            # Replace original with OCR version
            shutil.move(temp_output, pdf_path)
            print(f"   ✅ PDF replaced with OCR version")
            print(f"   📦 Original backed up to: {backup_path.name}")
        else:
            print(f"   ❌ OCR failed - original file unchanged")
            # Remove backup if OCR failed
            if backup_path.exists():
                backup_path.unlink()
    
    print("\n" + "="*80)
    print("OCR PROCESSING COMPLETE")
    print("="*80)


if __name__ == "__main__":
    print("\n⚠️  WARNING: This will modify the original PDF files!")
    print("   Backups will be created automatically.")
    print()
    response = input("Continue? (yes/no): ").strip().lower()
    
    if response == "yes":
        process_corrupted_pdfs()
    else:
        print("❌ Cancelled")
