# Physics Papers Batch Processing Summary

## What We're Processing

**Total Papers:** 56 paper pairs (112 PDFs)
**Date Range:** 2011-2024
**Subject:** Physics (4PH1)

## Papers Breakdown

- **2011:** 2 papers (May-Jun)
- **2012:** 4 papers (Jan, May-Jun)
- **2013:** 4 papers (Jan, May-Jun)
- **2014:** 4 papers (Jan, May-Jun)
- **2015:** 4 papers (Jan, May-Jun)
- **2016:** 4 papers (Jan, May-Jun)
- **2017:** 6 papers (Jan, May-Jun, Specimen)
- **2018:** 4 papers (Jan, May-Jun)
- **2019:** 4 papers (Jan, May-Jun)
- **2020:** 4 papers (Jan, May-Jun)
- **2021:** 6 papers (Jan, May-Jun, Oct-Nov)
- **2022:** 4 papers (Jan, May-Jun)
- **2023:** 4 papers (Jan, May-Jun)
- **2024:** 2 papers (May-Jun)

## Processing Pipeline

For each paper, the system will:

1. **Extract Watermark Metadata**
   - Format: "PMT\nPhysics · 2024 · May/Jun · Paper 1 · QP"
   - Auto-detects: Subject, Year, Season, Paper number

2. **Create/Verify Paper Record**
   - Checks if paper already exists in database
   - Creates new record if needed
   - Links to subject (4PH1)

3. **Split into Questions**
   - Detects question starts (patterns like "1    This question...")
   - Groups continuation pages
   - Typical papers have 10-20 questions

4. **Extract Mark Schemes**
   - Matches MS pages to each question
   - Creates separate MS PDF per question

5. **AI Topic Classification**
   - Uses Google Gemini API
   - Classifies each question to one of 8 topics:
     1. Forces and motion
     2. Electricity
     3. Waves
     4. Energy resources
     5. Solids, liquids and gases
     6. Magnetism and electromagnetism
     7. Radioactivity and particles
     8. Astrophysics
   - Determines difficulty (easy/medium/hard)
   - Rate limited: 4.5 seconds between questions

6. **PDF Compression** ✨ NEW
   - Compresses each question PDF before upload
   - Level 3 (high quality, good compression)
   - Typical savings: 30-40%
   - Also compresses mark schemes

7. **Upload to Storage**
   - Supabase Storage bucket: `question-pdfs`
   - Path format: `subjects/Physics/pages/2024_Jun_1P/q1.pdf`
   - Separate uploads for QP and MS

8. **Store in Database**
   - Table: `pages`
   - Includes: topics[], difficulty, confidence, URLs, metadata

## Time Estimates

**Per Question:**
- Split: ~1 second
- Classify: ~2 seconds (AI processing)
- Compress: ~0.5 seconds
- Upload: ~1 second
- Total: ~5 seconds per question

**Per Paper:**
- Average questions: ~15
- Time: ~75 seconds (~1.25 minutes)
- With rate limiting: ~90 seconds (~1.5 minutes)

**Total Batch:**
- 56 papers × 1.5 minutes = **84 minutes (~1.5 hours)**

## Storage Impact

**Without Compression:**
- Average question PDF: 40 KB
- Average paper: 15 questions = 600 KB
- 56 papers = 33.6 MB (QP only)
- With MS: ~67 MB total

**With Compression (30% savings):**
- Average question PDF: 28 KB
- Average paper: 15 questions = 420 KB
- 56 papers = 23.5 MB (QP only)
- With MS: **~47 MB total**
- **Savings: ~20 MB**

## Error Handling

The batch processor:
- ✅ Skips papers already in database (default)
- ✅ Continues on errors (doesn't stop batch)
- ✅ Logs all operations to file
- ✅ Can resume from specific index
- ✅ Handles Ctrl+C gracefully (saves progress)

## Commands

**List all papers:**
```powershell
python scripts/batch_process_physics.py --list-only
```

**Process all papers (skip existing):**
```powershell
python scripts/batch_process_physics.py
```

**Process all papers (including existing):**
```powershell
python scripts/batch_process_physics.py --no-skip
```

**Resume from specific index:**
```powershell
python scripts/batch_process_physics.py --start-from 30
```

## Monitoring

**Real-time Output:**
- Shows current paper being processed
- Question-by-question progress
- Topic classifications
- Compression stats
- Upload status

**Log File:**
- Saved to: `logs/batch_process_YYYYMMDD_HHMMSS.log`
- Contains full processing history
- Includes errors and warnings

## What Gets Created

**Database Records:**
- 1 subject: Physics (4PH1)
- 8 topics: All physics topics
- 56 papers: One per paper
- ~840 pages: Questions (15 avg × 56 papers)

**Storage Files:**
- ~1680 PDFs: Questions + Mark Schemes
- Size: ~47 MB (compressed)
- Organized by: subjects/Physics/pages/YEAR_SEASON_PAPER/

## Success Criteria

✅ All 56 papers processed
✅ Questions correctly classified
✅ Mark schemes linked
✅ PDFs compressed and uploaded
✅ Database updated
✅ No critical errors

## After Processing

**Verification Steps:**
1. Check database: `python scripts/check_database.py`
2. Verify paper count: Should show 56 papers
3. Check page count: Should show ~840 pages
4. Test worksheet generation: Try creating a worksheet

**Next Steps:**
1. Add Chemistry papers (similar structure)
2. Add Biology papers (similar structure)
3. Add Mathematics papers (similar structure)
4. Update documentation for new subjects
