"""
PDF Compression Utility for GradeMax
Compresses PDFs before upload to save storage space
Uses PyMuPDF (fitz) compression with quality preservation
"""

import fitz
import os
from pathlib import Path
from typing import Tuple


def get_pdf_size(pdf_path: str) -> int:
    """Get PDF file size in bytes"""
    return os.path.getsize(pdf_path)


def format_size(size_bytes: int) -> str:
    """Format bytes as human-readable size"""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.2f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.2f} TB"


def compress_pdf(input_path: str, output_path: str = None, compression_level: int = 3) -> Tuple[str, int, int, float]:
    """
    Compress PDF using PyMuPDF
    
    Args:
        input_path: Path to input PDF
        output_path: Path for compressed PDF (if None, overwrites input)
        compression_level: 0=no compression, 1=fast, 2=default, 3=high, 4=extreme
        
    Returns:
        (output_path, original_size, compressed_size, compression_ratio)
    """
    input_path = Path(input_path)
    
    if output_path is None:
        output_path = input_path.parent / f"{input_path.stem}_compressed{input_path.suffix}"
    else:
        output_path = Path(output_path)
    
    # Get original size
    original_size = get_pdf_size(str(input_path))
    
    # Open PDF
    doc = fitz.open(str(input_path))
    
    # Compression settings based on level
    if compression_level == 0:
        # No compression
        deflate = 0
        garbage = 0
    elif compression_level == 1:
        # Fast compression
        deflate = 1
        garbage = 1
    elif compression_level == 2:
        # Default compression
        deflate = 1
        garbage = 3
    elif compression_level == 3:
        # High compression (recommended)
        deflate = 1
        garbage = 4
        clean = True
        # Compress images
        for page_num in range(len(doc)):
            page = doc[page_num]
            # Get images and compress them
            image_list = page.get_images(full=True)
            for img_index, img in enumerate(image_list):
                xref = img[0]
                # Get image data
                pix = fitz.Pixmap(doc, xref)
                
                # Only compress if not already compressed
                if pix.n >= 4:  # RGBA or CMYK
                    # Convert to RGB
                    pix = fitz.Pixmap(fitz.csRGB, pix)
                
                # Compress with quality=85 (good balance)
                if pix.width > 100 and pix.height > 100:  # Only compress larger images
                    img_bytes = pix.tobytes("jpeg", jpg_quality=85)
                    # Update image in PDF
                    doc._update_stream(xref, img_bytes)
                
                pix = None  # Free memory
    elif compression_level == 4:
        # Extreme compression (may reduce quality)
        deflate = 1
        garbage = 4
        clean = True
        # More aggressive image compression
        for page_num in range(len(doc)):
            page = doc[page_num]
            image_list = page.get_images(full=True)
            for img_index, img in enumerate(image_list):
                xref = img[0]
                pix = fitz.Pixmap(doc, xref)
                
                if pix.n >= 4:
                    pix = fitz.Pixmap(fitz.csRGB, pix)
                
                # More aggressive compression
                img_bytes = pix.tobytes("jpeg", jpg_quality=75)
                doc._update_stream(xref, img_bytes)
                
                pix = None
    else:
        deflate = 1
        garbage = 3
    
    # Save with compression
    if compression_level >= 3:
        doc.save(
            str(output_path),
            garbage=garbage,
            deflate=True,
            clean=True,
            pretty=False
        )
    else:
        doc.save(
            str(output_path),
            garbage=garbage,
            deflate=bool(deflate)
        )
    
    doc.close()
    
    # Get compressed size
    compressed_size = get_pdf_size(str(output_path))
    
    # Calculate ratio
    compression_ratio = (1 - compressed_size / original_size) * 100 if original_size > 0 else 0
    
    return str(output_path), original_size, compressed_size, compression_ratio


def compress_pdf_in_place(pdf_path: str, compression_level: int = 3) -> Tuple[int, int, float]:
    """
    Compress PDF and replace original
    
    Args:
        pdf_path: Path to PDF to compress
        compression_level: 0-4 (3=high, recommended)
        
    Returns:
        (original_size, compressed_size, compression_ratio)
    """
    import tempfile
    import shutil
    
    # Create temp file
    with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp:
        tmp_path = tmp.name
    
    try:
        # Compress to temp file
        _, original_size, compressed_size, ratio = compress_pdf(
            pdf_path,
            tmp_path,
            compression_level
        )
        
        # Replace original
        shutil.move(tmp_path, pdf_path)
        
        return original_size, compressed_size, ratio
        
    except Exception as e:
        # Clean up temp file on error
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
        raise e


def test_compression():
    """Test compression on sample PDF"""
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python compress_pdf.py <pdf_path> [compression_level]")
        print("Compression levels: 0=none, 1=fast, 2=default, 3=high, 4=extreme")
        return
    
    pdf_path = sys.argv[1]
    level = int(sys.argv[2]) if len(sys.argv) > 2 else 3
    
    print(f"Compressing: {pdf_path}")
    print(f"Level: {level}")
    print()
    
    output_path, orig_size, comp_size, ratio = compress_pdf(pdf_path, compression_level=level)
    
    print(f"✅ Compressed successfully!")
    print(f"   Original:   {format_size(orig_size)}")
    print(f"   Compressed: {format_size(comp_size)}")
    print(f"   Saved:      {format_size(orig_size - comp_size)} ({ratio:.1f}%)")
    print(f"   Output:     {output_path}")


if __name__ == "__main__":
    test_compression()
