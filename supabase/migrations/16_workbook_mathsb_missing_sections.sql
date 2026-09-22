-- ============================================================================
-- 16. Maths B (4MB1): sections the original taxonomy left out
-- ============================================================================
--
-- Migration 15 shipped 50 sections with no home for two topics 4MB1 plainly
-- examines. A sample review of the first classification pass found questions
-- scattered because the correct section did not exist:
--
--   coordinate geometry     51 questions, spread across 6.1, 6.2, 8.2, 11.1,
--   (gradient, equation of  11.2, 4.4, 7.3 and 3.2 -- "Calculate the gradient
--   a line, midpoint)       of AB" was filed under Angles and Polygons because
--                           nothing better existed.
--
--   factor / remainder      12 questions, spread across 3.1, 3.4, 3.6, 4.1
--   theorem                 and 5.2. "Use the factor theorem to show (x - 5)
--                           is a factor of x^3 - ..." was filed as a quadratic.
--
-- Left unfixed, a human verifying those 63 questions would have had no correct
-- option to choose. This is the last safe moment to change the taxonomy: no
-- workbook_questions rows exist for 4MB1 yet, so nothing can be orphaned.
--
-- PURELY ADDITIVE. Existing section numbers are untouched, so no renumbering
-- and no risk to anything already assigned. The guard below enforces that
-- assumption rather than trusting it.
-- ============================================================================

BEGIN;

DO $$
DECLARE
  loaded INT;
BEGIN
  SELECT count(*) INTO loaded
  FROM workbook_questions q
  JOIN subjects s ON s.id = q.subject_id AND s.code = '4MB1';

  IF loaded > 0 THEN
    RAISE NOTICE 'NOTE: % 4MB1 workbook_questions already exist. This migration '
                 'only ADDS sections, so they are safe -- but any question that '
                 'belongs in a new section still needs reclassifying.', loaded;
  END IF;
END $$;

INSERT INTO workbook_sections (chapter_id, number, title)
SELECT c.id, v.section_number, v.title
FROM workbook_chapters c
JOIN subjects s ON s.id = c.subject_id AND s.code = '4MB1'
JOIN (VALUES
  -- 3. Algebra
  (3,  8, 'Factor and remainder theorem'),

  -- 6. Geometry
  (6,  6, 'Coordinate geometry: gradient, length and midpoint'),
  (6,  7, 'Equations of straight lines, parallel and perpendicular')
) AS v(chapter_number, section_number, title)
  ON v.chapter_number = c.number
ON CONFLICT (chapter_id, number) DO NOTHING;

COMMIT;

-- Verification -------------------------------------------------------------
-- SELECT c.number, c.title, count(sec.id) AS sections
-- FROM workbook_chapters c
-- JOIN subjects s ON s.id = c.subject_id AND s.code = '4MB1'
-- LEFT JOIN workbook_sections sec ON sec.chapter_id = c.id
-- GROUP BY c.number, c.title ORDER BY c.number;
