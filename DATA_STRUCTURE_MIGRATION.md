# Data Structure Migration Guide

## Overview
The GradeMax data structure has been updated to use a simplified, more intuitive format with watermark-based metadata extraction.

## What Changed?

### OLD Format (Deprecated)
```
data/raw/IGCSE/4PH1/2024/Jun/
├── 4PH1_1P.pdf       ← Question Paper
└── 4PH1_1P_MS.pdf    ← Mark Scheme
```

### NEW Format (Current)
```
data/raw/IGCSE/Physics/2024/May-Jun/
├── Paper 1.pdf       ← Question Paper
└── Paper 1_MS.pdf    ← Mark Scheme
```

## Key Improvements

### 1. **Human-Readable Subject Names**
- **Before:** `4PH1` (subject code)
- **After:** `Physics` (subject name)
- Makes folder structure self-documenting

### 2. **Simplified Filenames**
- **Before:** `4PH1_1P.pdf` (requires knowledge of codes)
- **After:** `Paper 1.pdf` (immediately clear)
- Easier for manual organization

### 3. **Full Season Names**
- **Before:** `Jun` or `Jan` only
- **After:** `May-Jun`, `Oct-Nov`, `Jan`
- More descriptive, matches official exam terminology

### 4. **Watermark-Based Metadata** ✨ NEW
Every page now has a watermark at the bottom left corner:
```
PMT
Physics · 2024 · May/Jun · Paper 1 · QP
```

Format: `Subject · Year · Season · Paper N · Type`
- **Subject:** Physics, Chemistry, Biology, Mathematics
- **Year:** 2011-2024
- **Season:** May/Jun, Oct/Nov, Jan
- **Paper:** Paper number (1, 2, 3, etc.)
- **Type:** QP (Question Paper) or MS (Mark Scheme)

## Technical Changes

### Updated Script: `page_based_ingest.py`

#### New Function: `_extract_watermark_metadata()`
```python
def _extract_watermark_metadata(self, pdf_path: str) -> Dict:
    """
    Extract metadata from PMT watermark at bottom left (X < 30, Y < 10)
    Returns: {
        'subject': 'Physics',
        'year': 2024,
        'season': 'May/Jun',
        'paper': '1',
        'type': 'QP'
    }
    """
```

#### Updated Function: `_parse_filename()`
```python
def _parse_filename(self, filename: str, parent_path: Path, pdf_path: str) -> Dict:
    """
    Parsing priority:
    1. Watermark metadata (most reliable)
    2. Folder path structure (fallback)
    3. Filename parsing (last resort)
    """
```

#### New Function: `_normalize_season()`
```python
def _normalize_season(self, season: str) -> str:
    """
    Database uses normalized seasons:
    - May/Jun, May-Jun → Jun
    - Oct/Nov, Oct-Nov → Jan
    - Jan → Jan
    """
```

## Subject Mapping

| Subject Name | Subject Code | Config File |
|-------------|--------------|-------------|
| Physics | 4PH1 | `config/physics_topics.yaml` |
| Chemistry | 4CH1 | `config/chemistry_topics.yaml` |
| Biology | 4BI1 | `config/biology_topics.yaml` |
| Mathematics | 4MA1 | `config/maths_topics.yaml` |
| Maths | 4MA1 | (alias for Mathematics) |

## Complete Folder Structure

```
data/raw/IGCSE/
├── Physics/
│   ├── 2011/
│   │   ├── Jan/
│   │   │   ├── Paper 1.pdf
│   │   │   ├── Paper 1_MS.pdf
│   │   │   ├── Paper 2.pdf
│   │   │   └── Paper 2_MS.pdf
│   │   └── May-Jun/
│   │       ├── Paper 1.pdf
│   │       ├── Paper 1_MS.pdf
│   │       ├── Paper 2.pdf
│   │       └── Paper 2_MS.pdf
│   ├── 2012/
│   │   └── ...
│   └── 2024/
│       └── May-Jun/
│           ├── Paper 1.pdf
│           ├── Paper 1_MS.pdf
│           ├── Paper 2.pdf
│           └── Paper 2_MS.pdf
├── Chemistry/
│   └── [Same structure]
├── Biology/
│   └── [Same structure]
└── Mathematics/
    └── [Same structure]
```

## Usage Examples

### Processing a Paper (New Format)
```powershell
python scripts/page_based_ingest.py `
  "data/raw/IGCSE/Physics/2024/May-Jun/Paper 1.pdf" `
  "data/raw/IGCSE/Physics/2024/May-Jun/Paper 1_MS.pdf"
```

### What Happens During Ingestion?

1. **Watermark Extraction**
   ```
   📍 Watermark: Physics · 2024 · May/Jun · Paper 1 · QP
   ```
   - Automatically detects subject (Physics → 4PH1)
   - Extracts year (2024)
   - Normalizes season (May/Jun → Jun)
   - Identifies paper number (1 → 1P)

2. **Paper Record Creation**
   ```
   1️⃣  Creating paper record...
      ✅ Paper UUID: 123e4567-e89b-12d3-a456-426614174000
   ```

3. **Page Splitting**
   ```
   2️⃣  Splitting QP into pages...
      ✅ Split into 15 questions
   ```

4. **Topic Classification**
   ```
   4️⃣  Classifying and uploading pages...
      ✅ [1/15] Q1 → Topic 1 (Easy)
      ✅ [2/15] Q2 → Topic 3 (Medium)
      ...
   ```

## Database Schema (Unchanged)

The database structure remains the same:
- **subjects:** Stores subject codes (4PH1, 4CH1, etc.)
- **papers:** References subjects by UUID
- **pages:** Stores individual questions with topics array

## Migration Notes

### For Existing Data
If you have files in the old format (`4PH1_1P.pdf`), you can either:
1. **Rename manually** to new format
2. **Keep old format** - script still has fallback parsing
3. **Wait for new papers** - all new downloads use new format

### For New Papers
- Use scraper to download papers (automatically uses new format)
- Or manually organize using new structure
- Watermarks are embedded in PDFs from source (PMT)

## Benefits of New Structure

1. **Self-Documenting:** Folders are readable without knowledge of subject codes
2. **Watermark Validation:** Metadata extracted directly from PDF content
3. **Error Reduction:** Less manual data entry for year/season/paper
4. **Easier Organization:** Natural folder structure matches exam board naming
5. **Future-Proof:** Can add new subjects without code mapping
6. **Quality Check:** Watermark mismatch alerts if wrong file in wrong folder

## Testing

Run the watermark checker to verify PDFs:
```powershell
python scripts/check_watermark.py "data/raw/IGCSE/Physics/2024/May-Jun/Paper 1.pdf"
```

Expected output:
```
Checking: data/raw/IGCSE/Physics/2024/May-Jun/Paper 1.pdf
Total pages: 36

Watermarks found:

Page 1:
  X:16.0, Y:1.1 -> PMT
Physics · 2024 · May/Jun · Paper 1 · QP
```

## Troubleshooting

### No Watermark Found
If watermark extraction fails, script falls back to path-based parsing:
```
⚠️  No watermark found, using path-based parsing
```
This usually means:
- PDF is from a different source (not PMT)
- PDF has been modified/cropped
- Solution: Ensure folder structure is correct

### Season Mismatch
If watermark season differs from folder:
```
📍 Watermark: Physics · 2024 · May/Jun · Paper 1 · QP
⚠️  Folder season (Jan) doesn't match watermark (May-Jun)
```
- Trust the watermark (it's embedded in PDF)
- Update folder structure to match

### Subject Code Not Found
If subject name isn't in mapping:
```
⚠️  Subject 'Maths' not found in mapping, using default
```
- Add to `subject_map` in `page_based_ingest.py`
- Or use existing aliases (Maths → Mathematics)

## Summary

✅ **What's Better:**
- Human-readable folder names
- Automatic metadata extraction
- Less manual configuration
- Built-in validation via watermarks

⚠️ **What to Know:**
- Season names are normalized for database (May-Jun → Jun)
- Subject names auto-map to codes (Physics → 4PH1)
- Watermark extraction happens on first page check

🔄 **Backward Compatibility:**
- Old format still works (fallback parsing)
- No database schema changes needed
- Migration is optional
