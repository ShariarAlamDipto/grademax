-- ============================================================================
-- Migration 04: Storage & Database Efficiency Cleanup
--
-- Changes:
--   papers:
--     + ADD pdf_url, markscheme_pdf_url (formalise fields used in code but
--       missing from the schema definition)
--     - DROP qp_source_path, ms_source_path (write-only R2 keys; the public
--       URL already stored in pdf_url is sufficient — key can be extracted
--       from URL via R2_PUBLIC_URL prefix if ever needed)
--     - DROP total_pages (never populated, never read by any route)
--
--   worksheets:
--     - DROP worksheet_url, markscheme_url (no code ever writes or reads these;
--       PDFs are generated on-the-fly by /api/worksheets/[id]/download)
--     - DROP total_pages (always inserted with the same value as total_questions;
--       the download route uses items.length directly)
--
--   tests:
--     - DROP question_paper_url, mark_scheme_url (no code ever writes or reads
--       these; PDFs are generated on-the-fly by /api/test-builder/generate)
--
--   pages:
--     - DROP page_count (never populated by any script, never read)
--
--   indexes:
--     + ADD idx_papers_subject_year_season — covers the common 3-column filter
--       used by every past-papers query (replaces separate subject + year indexes
--       for those queries; originals kept for backward safety)
--     + ADD idx_pages_questions_with_url — partial index covering the worksheet
--       hot-path: paper_id WHERE is_question AND qp_page_url IS NOT NULL
--
--   data cleanup:
--     - DELETE orphaned worksheet_items (page or worksheet no longer exists)
--     - DELETE orphaned test_items     (page or test no longer exists)
--     - DEDUPLICATE papers: where the same (subject,year,season,paper_number)
--       has >1 row, keep the row with the most URL data and remove the rest.
--       Pages on the removed rows are re-pointed to the surviving row first.
-- ============================================================================

BEGIN;

-- ──────────────────────────────────────────────────────────────────────────────
-- 1.  PAPERS — formalise missing URL columns
-- ──────────────────────────────────────────────────────────────────────────────
ALTER TABLE papers
  ADD COLUMN IF NOT EXISTS pdf_url             TEXT,
  ADD COLUMN IF NOT EXISTS markscheme_pdf_url  TEXT;

-- ──────────────────────────────────────────────────────────────────────────────
-- 2.  PAPERS — drop redundant source-path columns
-- ──────────────────────────────────────────────────────────────────────────────
ALTER TABLE papers
  DROP COLUMN IF EXISTS qp_source_path,
  DROP COLUMN IF EXISTS ms_source_path,
  DROP COLUMN IF EXISTS total_pages;

-- ──────────────────────────────────────────────────────────────────────────────
-- 3.  WORKSHEETS — drop dead URL-storage fields and redundant aggregate
-- ──────────────────────────────────────────────────────────────────────────────
ALTER TABLE worksheets
  DROP COLUMN IF EXISTS worksheet_url,
  DROP COLUMN IF EXISTS markscheme_url,
  DROP COLUMN IF EXISTS total_pages;

-- ──────────────────────────────────────────────────────────────────────────────
-- 4.  TESTS — drop dead generated-PDF URL fields
-- ──────────────────────────────────────────────────────────────────────────────
ALTER TABLE tests
  DROP COLUMN IF EXISTS question_paper_url,
  DROP COLUMN IF EXISTS mark_scheme_url;

-- ──────────────────────────────────────────────────────────────────────────────
-- 5.  PAGES — drop never-populated page_count
-- ──────────────────────────────────────────────────────────────────────────────
ALTER TABLE pages
  DROP COLUMN IF EXISTS page_count;

-- ──────────────────────────────────────────────────────────────────────────────
-- 6.  NEW INDEXES
-- ──────────────────────────────────────────────────────────────────────────────

-- Compound index for the most common past-papers filter: subject + year + season
CREATE INDEX IF NOT EXISTS idx_papers_subject_year_season
  ON papers (subject_id, year, season);

-- Partial index covering the worksheet/test-builder hot-path.
-- Only indexes pages that are actually queryable (question, URL set).
CREATE INDEX IF NOT EXISTS idx_pages_questions_with_url
  ON pages (paper_id)
  WHERE is_question = TRUE AND qp_page_url IS NOT NULL;

-- ──────────────────────────────────────────────────────────────────────────────
-- 7.  ORPHAN CLEANUP — worksheet_items
-- ──────────────────────────────────────────────────────────────────────────────
DELETE FROM worksheet_items
WHERE  page_id     NOT IN (SELECT id FROM pages)
   OR  worksheet_id NOT IN (SELECT id FROM worksheets);

-- ──────────────────────────────────────────────────────────────────────────────
-- 8.  ORPHAN CLEANUP — test_items
-- ──────────────────────────────────────────────────────────────────────────────
DELETE FROM test_items
WHERE  page_id NOT IN (SELECT id FROM pages)
   OR  test_id  NOT IN (SELECT id FROM tests);

-- ──────────────────────────────────────────────────────────────────────────────
-- 9.  DEDUPLICATE papers
--
--     Strategy: for each (subject_id, year, season, paper_number) group with
--     more than one row, pick the survivor as the row that:
--       (a) has the most URL fields set (pdf_url + markscheme_pdf_url), then
--       (b) most recently created (higher id as tie-break).
--     Before deleting the losers, re-point any pages that reference them to the
--     survivor so no pages are lost.
-- ──────────────────────────────────────────────────────────────────────────────
DO $$
DECLARE
  r RECORD;
BEGIN
  FOR r IN
    WITH ranked AS (
      SELECT
        id,
        subject_id, year, season, paper_number,
        (CASE WHEN pdf_url            IS NOT NULL THEN 1 ELSE 0 END +
         CASE WHEN markscheme_pdf_url IS NOT NULL THEN 1 ELSE 0 END) AS url_score,
        ROW_NUMBER() OVER (
          PARTITION BY subject_id, year, season, paper_number
          ORDER BY
            (CASE WHEN pdf_url            IS NOT NULL THEN 1 ELSE 0 END +
             CASE WHEN markscheme_pdf_url IS NOT NULL THEN 1 ELSE 0 END) DESC,
            id DESC
        ) AS rn
      FROM papers
    ),
    survivors AS (
      SELECT subject_id, year, season, paper_number, id AS survivor_id
      FROM ranked WHERE rn = 1
    ),
    dupes AS (
      SELECT r.id AS dupe_id, s.survivor_id
      FROM ranked r
      JOIN survivors s USING (subject_id, year, season, paper_number)
      WHERE r.rn > 1
    )
    SELECT dupe_id, survivor_id FROM dupes
  LOOP
    -- Re-point pages from the duplicate to the survivor
    UPDATE pages SET paper_id = r.survivor_id WHERE paper_id = r.dupe_id;

    -- Merge missing URLs from dupe into survivor (in case dupe had something survivor didn't)
    UPDATE papers
    SET
      pdf_url            = COALESCE(pdf_url,            (SELECT pdf_url            FROM papers WHERE id = r.dupe_id)),
      markscheme_pdf_url = COALESCE(markscheme_pdf_url, (SELECT markscheme_pdf_url FROM papers WHERE id = r.dupe_id))
    WHERE id = r.survivor_id;

    -- Delete the duplicate row
    DELETE FROM papers WHERE id = r.dupe_id;
  END LOOP;
END $$;

-- ──────────────────────────────────────────────────────────────────────────────
-- 10. UNIQUE CONSTRAINT — enforce no future duplicates (safe if already exists)
-- ──────────────────────────────────────────────────────────────────────────────
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint
    WHERE conname = 'papers_subject_id_year_season_paper_number_key'
      AND conrelid = 'papers'::regclass
  ) THEN
    ALTER TABLE papers
      ADD CONSTRAINT papers_subject_id_year_season_paper_number_key
      UNIQUE (subject_id, year, season, paper_number);
  END IF;
END $$;

COMMIT;
