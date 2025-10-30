"""Quick debug script to check MS row detection"""

import re
import pdfplumber

MS_ROW_STRICT = re.compile(
    r"^\s*(\d{1,2})\s+(\([a-h]\)|\([ivx]+\)|[a-h]\b|[ivx]+\b)",
    re.MULTILINE | re.IGNORECASE
)

ms_path = r"data\raw\IGCSE\Physics\2018\Jan\Paper 1_MS.pdf"

with pdfplumber.open(ms_path) as pdf:
    for i in range(min(5, len(pdf.pages))):
        page = pdf.pages[i]
        text = page.extract_text() or ""
        
        print(f"\n=== Page {i} ===")
        lines = text.split('\n')
        print(f"First 10 lines:")
        for j, line in enumerate(lines[:10]):
            print(f"  {j}: {line[:80]}")
        
        # Check for header
        if re.search(r'Question.*Answer.*Marks', text, re.IGNORECASE):
            print(f"\n✅ FOUND HEADER")
        
        # Check for rows
        matches = list(MS_ROW_STRICT.finditer(text))
        print(f"\nMS_ROW_STRICT matches: {len(matches)}")
        for match in matches[:5]:
            print(f"  - '{match.group(0)}' -> Q{match.group(1)} subpart {match.group(2)}")
