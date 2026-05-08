-- Migration 10: Add data_file_url column for ICT practical-exam data files,
-- and tighten subject uniqueness to prevent future duplicate-name rows.
--
-- Backfill of data_file_url values + consolidation of duplicate FPM subject
-- rows is performed by scripts/fix-fpm-and-datafiles.ts and the data-file
-- upload script. This migration only handles schema changes that PostgREST
-- can't perform.

-- 1. Add data_file_url column (nullable, idempotent)
ALTER TABLE papers
  ADD COLUMN IF NOT EXISTS data_file_url TEXT;

-- 2. Document the column's purpose
COMMENT ON COLUMN papers.data_file_url IS
  'Public URL for practical-exam data files (e.g. zipped spreadsheets/databases for the ICT Paper 2 practical).';
