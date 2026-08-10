-- Migration 14: Review metadata on workbook_questions
-- =============================================================================
-- Phase 4 puts every question in front of a human before it can appear in the
-- book. To make that pass fast rather than uniform, the reviewer needs to know
-- how much attention each question deserves -- and the classifier's own
-- confidence cannot tell them.
--
-- Measured over the 2016-2022 corpus, mean self-reported confidence was:
--     0.858 where two independent models agreed on the section
--     0.850 where they agreed only on the chapter
--     0.827 where they flatly disagreed
-- A 0.03 spread across the entire range of correctness. Useless for triage.
--
-- Agreement between two different model families separates them properly:
--     250 agreed (59%)  -> confirm at a glance
--     106 same chapter  -> check the section
--      54 disputed      -> read it properly
--      13 unconfirmed   -> no second opinion (scanned questions)
--
-- These columns carry that signal so the review queue can be ordered by it.
-- They are scaffolding for the verification pass, not part of the book: once
-- every row has verified_at set they stop being read, and they stay nullable so
-- a subject onboarded without a second pass is unaffected.
--
-- Idempotent and safe to re-run.
-- =============================================================================

BEGIN;

-- What the second model proposed. NULL means it was never asked (or its answer
-- was rejected as invalid), which is itself worth surfacing to the reviewer.
ALTER TABLE workbook_questions
  ADD COLUMN IF NOT EXISTS proposed_section_id UUID REFERENCES workbook_sections(id);

-- Derived from primary vs proposed. Stored rather than computed so the queue
-- can be ordered and paged in the database.
ALTER TABLE workbook_questions
  ADD COLUMN IF NOT EXISTS review_priority TEXT
    CHECK (review_priority IN ('disputed', 'same_chapter', 'unconfirmed', 'agreed'));

-- Kept for the record so the calibration claim above stays checkable against
-- real data rather than becoming folklore.
ALTER TABLE workbook_questions
  ADD COLUMN IF NOT EXISTS classifier_confidence REAL
    CHECK (classifier_confidence >= 0 AND classifier_confidence <= 1);

-- The queue is "unverified, hardest first", so index exactly that.
CREATE INDEX IF NOT EXISTS idx_workbook_questions_review_queue
  ON workbook_questions (subject_id, review_priority, ordinal_in_chapter)
  WHERE verified_at IS NULL;

COMMIT;

-- Verify:
--   SELECT review_priority, count(*) FROM workbook_questions GROUP BY 1;
-- Expect all NULL until the backfill runs
-- (python scripts/backfill_fpm_review_metadata.py --execute).
