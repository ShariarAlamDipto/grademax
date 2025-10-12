-- ============================================================================
-- MIGRATION: Clean Start for Page-Based Architecture
-- Run this FIRST before running 00_clean_schema.sql
-- ============================================================================

-- Step 1: Drop old data (but keep storage bucket untouched)
DO $$ 
BEGIN
  -- Drop old tables if they exist (in correct order for foreign keys)
  DROP TABLE IF EXISTS worksheet_items CASCADE;
  DROP TABLE IF EXISTS worksheets CASCADE;
  DROP TABLE IF EXISTS question_topics CASCADE;
  DROP TABLE IF EXISTS questions CASCADE;
  DROP TABLE IF EXISTS pages CASCADE;
  DROP TABLE IF EXISTS papers CASCADE;
  DROP TABLE IF EXISTS topics CASCADE;
  DROP TABLE IF EXISTS subjects CASCADE;
  
  RAISE NOTICE 'Old tables dropped successfully';
END $$;

-- Step 2: Note about storage bucket
-- The 'question-pdfs' bucket will be REUSED with new structure:
-- 
-- OLD structure:
--   papers/2019_Jun_1P/Q3.pdf
--   2019/Jun/1P/Q2.pdf
--   topics/1/Q2.pdf  (partial implementation)
--
-- NEW structure:
--   subjects/Physics/pages/2019_Jun_1P/q1.pdf
--   subjects/Physics/pages/2019_Jun_1P/q1_ms.pdf
--   generated/worksheets/{uuid}_worksheet.pdf
--   generated/worksheets/{uuid}_markscheme.pdf
--
-- ACTION: You can keep old files or clear the bucket for fresh start
-- To clear in Supabase Dashboard: Storage → question-pdfs → Delete all files

-- Step 3: Ready for new schema
SELECT 'Migration complete. Now run: 00_clean_schema.sql' AS next_step;
