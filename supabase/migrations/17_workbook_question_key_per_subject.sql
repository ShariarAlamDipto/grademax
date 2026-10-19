-- ============================================================================
-- 17. Scope the workbook question source key to its subject
-- ============================================================================
--
-- Migration 12 declared:
--
--     UNIQUE (source_paper_key, source_question_number)
--
-- which is global. A paper key is only "2022_may-jun_1R" -- it carries the
-- year, session and paper number but NOT the subject, because the subject was
-- already implied when Further Pure Maths was the only workbook.
--
-- Every Edexcel subject sits the same sessions, so Maths B's 2022 May-June
-- Paper 1R collides with FPM's. The failure is total rather than partial:
-- loading Maths B aborted on its very first row, because FPM already owned
-- (2022_may-jun_1R, 1) as FPM.CH05.S01.Q004. The table held zero Maths B rows
-- and still rejected the insert as a duplicate.
--
-- The constraint is doing a real job -- it stops the same question being loaded
-- twice -- so it is re-scoped rather than dropped. Any third subject would have
-- hit exactly the same wall.
--
-- Purely a relaxation: every pair unique globally is still unique per subject,
-- so no existing row can violate the new constraint.
-- ============================================================================

BEGIN;

ALTER TABLE workbook_questions
  DROP CONSTRAINT IF EXISTS workbook_questions_source_paper_key_source_question_number_key;

ALTER TABLE workbook_questions
  ADD CONSTRAINT workbook_questions_subject_source_key
  UNIQUE (subject_id, source_paper_key, source_question_number);

COMMIT;

-- Verification -------------------------------------------------------------
-- SELECT conname, pg_get_constraintdef(oid)
-- FROM pg_constraint
-- WHERE conrelid = 'workbook_questions'::regclass AND contype = 'u';
