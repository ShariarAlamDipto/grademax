-- Migration 05: ICT subject seed + data_file_url column for practical exam files
--
-- ICT Paper 2 is a practical exam; students receive data files (spreadsheets,
-- databases, etc.) alongside the question paper. This migration:
--   1. Adds data_file_url to the papers table
--   2. Ensures the ICT subject row exists

-- 1. Add data_file_url column (stores public URL to the practical data file,
--    e.g. a zip of spreadsheet/database files for the ICT practical exam)
ALTER TABLE papers
  ADD COLUMN IF NOT EXISTS data_file_url TEXT;

-- 2. Seed ICT subject if not already present
INSERT INTO subjects (name, code, board, level)
VALUES ('ICT', '4IT1', 'Edexcel', 'igcse')
ON CONFLICT (code) DO NOTHING;
