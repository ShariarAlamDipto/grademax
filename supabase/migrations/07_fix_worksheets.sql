-- Migration 07: Bring worksheets / worksheet_items into the questions-based
-- architecture, preserving any existing rows.
--
-- Strategy: additive only.
--   * ADD COLUMN IF NOT EXISTS for new columns.
--   * DROP NOT NULL on legacy columns instead of dropping the columns, so old
--     rows survive even when their values no longer make sense to the new code.
--   * DROP COLUMN IF EXISTS only on filter columns the app no longer reads
--     (topics, year_start, year_end, difficulty, total_questions on worksheets).
--     Their data was always derivable from `params` and the linked items.
--   * Keep page_id / sequence on worksheet_items: they describe legacy items
--     that the new generator never recreates, but the new code does not read
--     them, so leaving them in place costs nothing.
--   * Replace public RLS with owner-only policies (idempotent).

BEGIN;

-- ─────────────────────────────────────────────────────────────────────────────
-- 1. WORKSHEETS — add new columns (no-ops if they already exist)
-- ─────────────────────────────────────────────────────────────────────────────
ALTER TABLE worksheets ADD COLUMN IF NOT EXISTS user_id     UUID REFERENCES auth.users(id);
ALTER TABLE worksheets ADD COLUMN IF NOT EXISTS title       TEXT;
ALTER TABLE worksheets ADD COLUMN IF NOT EXISTS description TEXT;
ALTER TABLE worksheets ADD COLUMN IF NOT EXISTS params      JSONB;

-- subject_id is no longer required at creation time. Drop the NOT NULL only
-- if it's currently set (avoids a needless ALTER on already-fixed databases).
DO $$
BEGIN
  IF EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_schema = 'public'
      AND table_name   = 'worksheets'
      AND column_name  = 'subject_id'
      AND is_nullable  = 'NO'
  ) THEN
    ALTER TABLE worksheets ALTER COLUMN subject_id DROP NOT NULL;
  END IF;
END $$;

-- ─────────────────────────────────────────────────────────────────────────────
-- 2. WORKSHEETS — drop legacy filter columns
--    These columns were always summaries of values now stored inside `params`.
--    Dropping them does not lose information that isn't already captured
--    elsewhere in the row.
-- ─────────────────────────────────────────────────────────────────────────────
ALTER TABLE worksheets DROP COLUMN IF EXISTS topics;
ALTER TABLE worksheets DROP COLUMN IF EXISTS year_start;
ALTER TABLE worksheets DROP COLUMN IF EXISTS year_end;
ALTER TABLE worksheets DROP COLUMN IF EXISTS difficulty;
ALTER TABLE worksheets DROP COLUMN IF EXISTS total_questions;

-- ─────────────────────────────────────────────────────────────────────────────
-- 3. WORKSHEETS — index for per-user queries
-- ─────────────────────────────────────────────────────────────────────────────
CREATE INDEX IF NOT EXISTS idx_worksheets_user ON worksheets(user_id);

-- ─────────────────────────────────────────────────────────────────────────────
-- 4. WORKSHEETS — replace public policies with owner-only policies
--
-- PERMISSIVE policies use OR logic: an old "USING (true)" policy would let
-- anyone read all worksheets even if an owner policy exists alongside it.
-- ─────────────────────────────────────────────────────────────────────────────
DROP POLICY IF EXISTS "Public read worksheets"   ON worksheets;
DROP POLICY IF EXISTS "Public insert worksheets" ON worksheets;
DROP POLICY IF EXISTS "dev_all"                  ON worksheets;
DROP POLICY IF EXISTS "Owner read worksheets"    ON worksheets;
DROP POLICY IF EXISTS "Owner insert worksheets"  ON worksheets;

CREATE POLICY "Owner read worksheets"
  ON worksheets FOR SELECT
  USING (auth.uid() = user_id);

CREATE POLICY "Owner insert worksheets"
  ON worksheets FOR INSERT
  WITH CHECK (auth.uid() = user_id);

-- ─────────────────────────────────────────────────────────────────────────────
-- 5. WORKSHEET_ITEMS — add new columns alongside the legacy ones
--
-- Existing rows reference page_id; new rows reference question_id. Both
-- columns coexist. The new code reads/writes question_id only.
-- ─────────────────────────────────────────────────────────────────────────────
ALTER TABLE worksheet_items
  ADD COLUMN IF NOT EXISTS question_id UUID REFERENCES questions(id) ON DELETE CASCADE;
ALTER TABLE worksheet_items
  ADD COLUMN IF NOT EXISTS position    INTEGER;

-- Drop NOT NULL on legacy columns so new inserts don't have to provide them.
DO $$
BEGIN
  IF EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_schema = 'public'
      AND table_name   = 'worksheet_items'
      AND column_name  = 'page_id'
      AND is_nullable  = 'NO'
  ) THEN
    ALTER TABLE worksheet_items ALTER COLUMN page_id DROP NOT NULL;
  END IF;

  IF EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_schema = 'public'
      AND table_name   = 'worksheet_items'
      AND column_name  = 'sequence'
      AND is_nullable  = 'NO'
  ) THEN
    ALTER TABLE worksheet_items ALTER COLUMN sequence DROP NOT NULL;
  END IF;
END $$;

-- Replace the legacy uniqueness with one keyed on question_id.
ALTER TABLE worksheet_items
  DROP CONSTRAINT IF EXISTS worksheet_items_worksheet_id_page_id_key;

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint
    WHERE conname = 'worksheet_items_worksheet_id_question_id_key'
      AND conrelid = 'worksheet_items'::regclass
  ) THEN
    ALTER TABLE worksheet_items
      ADD CONSTRAINT worksheet_items_worksheet_id_question_id_key
      UNIQUE (worksheet_id, question_id);
  END IF;
END $$;

-- ─────────────────────────────────────────────────────────────────────────────
-- 6. WORKSHEET_ITEMS — refresh indexes
-- ─────────────────────────────────────────────────────────────────────────────
DROP INDEX IF EXISTS idx_worksheet_items_sequence;
CREATE INDEX IF NOT EXISTS idx_worksheet_items_position
  ON worksheet_items(worksheet_id, position);
CREATE INDEX IF NOT EXISTS idx_worksheet_items_question
  ON worksheet_items(question_id);

-- ─────────────────────────────────────────────────────────────────────────────
-- 7. WORKSHEET_ITEMS — owner-scoped policies via parent worksheet
-- ─────────────────────────────────────────────────────────────────────────────
DROP POLICY IF EXISTS "Public read worksheet_items"   ON worksheet_items;
DROP POLICY IF EXISTS "Public insert worksheet_items" ON worksheet_items;
DROP POLICY IF EXISTS "dev_all"                       ON worksheet_items;
DROP POLICY IF EXISTS "Owner read worksheet_items"    ON worksheet_items;
DROP POLICY IF EXISTS "Owner insert worksheet_items"  ON worksheet_items;

CREATE POLICY "Owner read worksheet_items"
  ON worksheet_items FOR SELECT
  USING (
    worksheet_id IN (SELECT id FROM worksheets WHERE user_id = auth.uid())
  );

CREATE POLICY "Owner insert worksheet_items"
  ON worksheet_items FOR INSERT
  WITH CHECK (
    worksheet_id IN (SELECT id FROM worksheets WHERE user_id = auth.uid())
  );

-- ─────────────────────────────────────────────────────────────────────────────
-- 8. SUMMARY
-- ─────────────────────────────────────────────────────────────────────────────
DO $$
DECLARE
  ws_count  INT;
  wsi_count INT;
BEGIN
  SELECT COUNT(*) INTO ws_count  FROM worksheets;
  SELECT COUNT(*) INTO wsi_count FROM worksheet_items;
  RAISE NOTICE '--- Migration 07 complete ---';
  RAISE NOTICE '  worksheets:      % rows (preserved)', ws_count;
  RAISE NOTICE '  worksheet_items: % rows (preserved)', wsi_count;
END $$;

COMMIT;
