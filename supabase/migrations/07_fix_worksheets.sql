-- Migration 07: Fix worksheets + worksheet_items to match questions-based architecture
--
-- The generate-v2 route and download route were updated to use the questions table
-- (not pages). The worksheets table needs new columns (user_id, title, description,
-- params) and worksheet_items needs question_id/position instead of page_id/sequence.
--
-- Run after: 06_create_missing_tables.sql (questions table must exist first)

BEGIN;

-- ─────────────────────────────────────────────────────────────────────────────
-- 1. WORKSHEETS — add new columns
-- ─────────────────────────────────────────────────────────────────────────────
ALTER TABLE worksheets
  ADD COLUMN IF NOT EXISTS user_id     UUID REFERENCES auth.users(id),
  ADD COLUMN IF NOT EXISTS title       TEXT,
  ADD COLUMN IF NOT EXISTS description TEXT,
  ADD COLUMN IF NOT EXISTS params      JSONB;

-- subject_id is no longer required at creation (resolved from papers)
ALTER TABLE worksheets
  ALTER COLUMN subject_id DROP NOT NULL;

-- ─────────────────────────────────────────────────────────────────────────────
-- 2. WORKSHEETS — drop obsolete columns from old architecture
-- ─────────────────────────────────────────────────────────────────────────────
ALTER TABLE worksheets
  DROP COLUMN IF EXISTS topics,
  DROP COLUMN IF EXISTS year_start,
  DROP COLUMN IF EXISTS year_end,
  DROP COLUMN IF EXISTS difficulty,
  DROP COLUMN IF EXISTS total_questions;

-- ─────────────────────────────────────────────────────────────────────────────
-- 3. WORKSHEETS — index for per-user queries
-- ─────────────────────────────────────────────────────────────────────────────
CREATE INDEX IF NOT EXISTS idx_worksheets_user ON worksheets(user_id);

-- ─────────────────────────────────────────────────────────────────────────────
-- 4. WORKSHEETS — replace public policies with owner-only policies
--
-- PERMISSIVE policies use OR logic: an old "USING (true)" policy would let
-- anyone read all worksheets even if an owner policy exists alongside it.
-- Drop the public policies first, then add restricted ones.
-- ─────────────────────────────────────────────────────────────────────────────
DROP POLICY IF EXISTS "Public read worksheets"   ON worksheets;
DROP POLICY IF EXISTS "Public insert worksheets" ON worksheets;

CREATE POLICY "Owner read worksheets"
  ON worksheets FOR SELECT
  USING (auth.uid() = user_id);

CREATE POLICY "Owner insert worksheets"
  ON worksheets FOR INSERT
  WITH CHECK (auth.uid() = user_id);

-- ─────────────────────────────────────────────────────────────────────────────
-- 5. WORKSHEET_ITEMS — clear stale data and replace columns
--
-- All existing rows reference old page_id values; none are valid in the new
-- architecture. TRUNCATE resets the table before altering the schema.
-- ─────────────────────────────────────────────────────────────────────────────
TRUNCATE worksheet_items;

-- Drop old FK columns (page_id, sequence)
ALTER TABLE worksheet_items
  DROP COLUMN IF EXISTS page_id,
  DROP COLUMN IF EXISTS sequence;

-- Add new columns (DEFAULT 0 is required to satisfy NOT NULL on ALTER;
-- the default is removed once the column exists)
ALTER TABLE worksheet_items
  ADD COLUMN IF NOT EXISTS question_id UUID REFERENCES questions(id) ON DELETE CASCADE,
  ADD COLUMN IF NOT EXISTS position    INTEGER NOT NULL DEFAULT 0;

ALTER TABLE worksheet_items ALTER COLUMN position DROP DEFAULT;

-- Enforce one question per worksheet (replace old page_id uniqueness)
ALTER TABLE worksheet_items
  DROP CONSTRAINT IF EXISTS worksheet_items_worksheet_id_page_id_key;

ALTER TABLE worksheet_items
  ADD CONSTRAINT IF NOT EXISTS worksheet_items_worksheet_id_question_id_key
  UNIQUE (worksheet_id, question_id);

-- ─────────────────────────────────────────────────────────────────────────────
-- 6. WORKSHEET_ITEMS — update indexes
-- ─────────────────────────────────────────────────────────────────────────────
DROP INDEX IF EXISTS idx_worksheet_items_sequence;

CREATE INDEX IF NOT EXISTS idx_worksheet_items_position ON worksheet_items(worksheet_id, position);
CREATE INDEX IF NOT EXISTS idx_worksheet_items_question ON worksheet_items(question_id);

-- ─────────────────────────────────────────────────────────────────────────────
-- 7. WORKSHEET_ITEMS — replace public policies with owner-scoped policies
--
-- Ownership is determined via the parent worksheet's user_id.
-- ─────────────────────────────────────────────────────────────────────────────
DROP POLICY IF EXISTS "Public read worksheet_items"   ON worksheet_items;
DROP POLICY IF EXISTS "Public insert worksheet_items" ON worksheet_items;

CREATE POLICY "Owner read worksheet_items"
  ON worksheet_items FOR SELECT
  USING (
    worksheet_id IN (
      SELECT id FROM worksheets WHERE user_id = auth.uid()
    )
  );

CREATE POLICY "Owner insert worksheet_items"
  ON worksheet_items FOR INSERT
  WITH CHECK (
    worksheet_id IN (
      SELECT id FROM worksheets WHERE user_id = auth.uid()
    )
  );

COMMIT;
