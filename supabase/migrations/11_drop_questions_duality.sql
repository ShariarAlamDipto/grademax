-- Migration 11: Finish the pages/questions consolidation — pages is canonical.
--
-- History: migration 09 backfilled `questions` (and `question_tags`) from
-- `pages` with IDENTICAL UUIDs (questions.id = pages.id) so the worksheet
-- generator could read `questions`. The generator has since been switched
-- back to `pages` (commit 99364027), and the last remaining reader
-- (/api/admin/nav-badges) now counts unclassified pages directly.
--
-- This migration:
--   1. Repoints worksheet_items.question_id FK from questions(id) to pages(id).
--      Data is already compatible because the UUIDs are shared. Orphaned
--      values (legacy rows whose target no longer exists) are NULLed, not
--      deleted, so worksheet history rows survive.
--   2. Drops questions, question_tags, and the legacy question_topics tables.
--
-- Apply via the Supabase dashboard SQL editor. Re-runnable.

BEGIN;

-- ─────────────────────────────────────────────────────────────────────────────
-- 1. Repoint worksheet_items.question_id → pages(id)
-- ─────────────────────────────────────────────────────────────────────────────
ALTER TABLE worksheet_items
  DROP CONSTRAINT IF EXISTS worksheet_items_question_id_fkey;

UPDATE worksheet_items wi
SET question_id = NULL
WHERE wi.question_id IS NOT NULL
  AND NOT EXISTS (SELECT 1 FROM pages p WHERE p.id = wi.question_id);

ALTER TABLE worksheet_items
  ADD CONSTRAINT worksheet_items_question_id_fkey
  FOREIGN KEY (question_id) REFERENCES pages(id) ON DELETE CASCADE;

COMMENT ON COLUMN worksheet_items.question_id IS
  'References pages(id). Named question_id for historical reasons (the dropped questions table shared UUIDs with pages).';

-- ─────────────────────────────────────────────────────────────────────────────
-- 2. Drop the duplicated tables
-- ─────────────────────────────────────────────────────────────────────────────
DROP TABLE IF EXISTS question_tags   CASCADE;
DROP TABLE IF EXISTS question_topics CASCADE;
DROP TABLE IF EXISTS questions       CASCADE;

-- ─────────────────────────────────────────────────────────────────────────────
-- 3. Summary
-- ─────────────────────────────────────────────────────────────────────────────
DO $$
DECLARE
  wsi_total    INT;
  wsi_linked   INT;
BEGIN
  SELECT COUNT(*) INTO wsi_total  FROM worksheet_items;
  SELECT COUNT(*) INTO wsi_linked FROM worksheet_items WHERE question_id IS NOT NULL;
  RAISE NOTICE '--- Migration 11 complete ---';
  RAISE NOTICE '  worksheet_items rows:               %', wsi_total;
  RAISE NOTICE '  rows still linked to a page:        %', wsi_linked;
  RAISE NOTICE '  questions / question_tags dropped.';
END $$;

COMMIT;
