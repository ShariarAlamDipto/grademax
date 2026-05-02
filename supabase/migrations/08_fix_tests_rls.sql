-- Migration 08: Fix tests/test_items RLS, seed FPM subject, normalize ICT level
--
-- Addresses three issues:
--   1. tests/test_items have fully public RLS (any user can read/write/delete
--      anyone else's tests). Tighten to owner-only.
--   2. Migration 03 (FPM topics) raises an EXCEPTION if the FPM subject row
--      doesn't exist. Seed it here as a safety net so migration 03 can run.
--   3. ICT subject was seeded with level = 'igcse' (lowercase) in migration 05;
--      all other subjects use 'IGCSE' (uppercase). Normalize for consistency.
--
-- IMPORTANT: The tests/[testId]/route.ts must be updated to use requireAuth()
-- before this migration is applied, otherwise GET/PUT/DELETE on individual
-- tests will return 0 rows (RLS blocks the anon client).

BEGIN;

-- ─────────────────────────────────────────────────────────────────────────────
-- 1. SEED FPM SUBJECT (safety net for migration 03)
--
--    Migration 03 fails on a fresh DB if the FPM subject doesn't exist yet.
--    Insert it here with ON CONFLICT DO NOTHING so it's always present.
-- ─────────────────────────────────────────────────────────────────────────────
INSERT INTO subjects (code, name, board, level)
VALUES ('9FM0', 'Further Pure Mathematics', 'Edexcel', 'IAL')
ON CONFLICT (code) DO NOTHING;

-- 4PM1 is the legacy code for the same qualification
INSERT INTO subjects (code, name, board, level)
VALUES ('4PM1', 'Further Pure Mathematics', 'Edexcel', 'IGCSE')
ON CONFLICT (code) DO NOTHING;

-- ─────────────────────────────────────────────────────────────────────────────
-- 2. NORMALIZE ICT LEVEL
-- ─────────────────────────────────────────────────────────────────────────────
UPDATE subjects SET level = 'IGCSE' WHERE code = '4IT1' AND level = 'igcse';

-- ─────────────────────────────────────────────────────────────────────────────
-- 3. ADD MISSING FK on tests.user_id → auth.users(id)
--
--    The column was declared nullable with no FK in migration 02.
--    Add the constraint now (VALIDATE = false avoids scanning existing rows).
-- ─────────────────────────────────────────────────────────────────────────────
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint
    WHERE conname = 'tests_user_id_fkey'
      AND conrelid = 'tests'::regclass
  ) THEN
    ALTER TABLE tests
      ADD CONSTRAINT tests_user_id_fkey
      FOREIGN KEY (user_id) REFERENCES auth.users(id)
      NOT VALID;
  END IF;
END $$;

-- ─────────────────────────────────────────────────────────────────────────────
-- 4. TESTS — replace fully public RLS with owner-only policies
--
-- The public DELETE policy is the most dangerous: any anonymous caller can
-- delete any test. Drop all public policies and replace with owner policies.
-- ─────────────────────────────────────────────────────────────────────────────
DROP POLICY IF EXISTS "Public read tests"   ON tests;
DROP POLICY IF EXISTS "Public insert tests" ON tests;
DROP POLICY IF EXISTS "Public update tests" ON tests;
DROP POLICY IF EXISTS "Public delete tests" ON tests;

CREATE POLICY "Owner read tests"
  ON tests FOR SELECT
  USING (auth.uid() = user_id);

CREATE POLICY "Owner insert tests"
  ON tests FOR INSERT
  WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Owner update tests"
  ON tests FOR UPDATE
  USING (auth.uid() = user_id);

CREATE POLICY "Owner delete tests"
  ON tests FOR DELETE
  USING (auth.uid() = user_id);

-- ─────────────────────────────────────────────────────────────────────────────
-- 5. TEST_ITEMS — replace fully public RLS with owner-scoped policies
--
-- Ownership is determined via the parent test's user_id.
-- ─────────────────────────────────────────────────────────────────────────────
DROP POLICY IF EXISTS "Public read test_items"   ON test_items;
DROP POLICY IF EXISTS "Public insert test_items" ON test_items;
DROP POLICY IF EXISTS "Public update test_items" ON test_items;
DROP POLICY IF EXISTS "Public delete test_items" ON test_items;

CREATE POLICY "Owner read test_items"
  ON test_items FOR SELECT
  USING (
    test_id IN (SELECT id FROM tests WHERE user_id = auth.uid())
  );

CREATE POLICY "Owner insert test_items"
  ON test_items FOR INSERT
  WITH CHECK (
    test_id IN (SELECT id FROM tests WHERE user_id = auth.uid())
  );

CREATE POLICY "Owner update test_items"
  ON test_items FOR UPDATE
  USING (
    test_id IN (SELECT id FROM tests WHERE user_id = auth.uid())
  );

CREATE POLICY "Owner delete test_items"
  ON test_items FOR DELETE
  USING (
    test_id IN (SELECT id FROM tests WHERE user_id = auth.uid())
  );

COMMIT;
