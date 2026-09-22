-- ============================================================================
-- 19. Workbook taxonomy for Edexcel IAL Pure Mathematics 4 (WMA14)
-- ============================================================================
--
-- Adds the chapter/section tree the P4 chapterwise workbook is built on.
-- Structure only -- no questions are loaded here; the loader does that, and
-- nothing reaches a student until it is verified.
--
-- SOURCE OF THE CHAPTERS
-- ----------------------
-- The seven chapters are the seven numbered content headings of section P4.3
-- "Unit content" in the Pearson Edexcel International Advanced Subsidiary /
-- Advanced Level in Mathematics, Further Mathematics and Pure Mathematics
-- specification, Issue 3, April 2019 (pp. 27-29), quoted verbatim:
--
--   1. Proof
--   2. Algebra and functions
--   3. Coordinate geometry in the (x, y) plane
--   4. Binomial expansion
--   5. Differentiation
--   6. Integration
--   7. Vectors
--
-- THE SOURCE WINDOW IS 2020 ONWARDS, AND THAT IS NOT A PREFERENCE
-- ---------------------------------------------------------------
-- WMA14 was first assessed in June 2020. Everything filed as "P4" before that
-- is a DIFFERENT QUALIFICATION: the 125-mark WMA02 "Core Mathematics C34" or
-- the 75-mark legacy C4. Their covers say so, and the papers confirm it -- the
-- trapezium rule appears in 10 of 14 legacy papers and 0 of 14 WMA14 papers,
-- and numerical iteration in 9 of 14 legacy and 0 of 14 WMA14. Both are P2/P3
-- content under the 2018 specification. Mixing those papers into this tree
-- would put off-specification questions in front of a P4 student, so the
-- workbook window is the 2018 specimen plus June 2020 onwards.
--
-- SECTION SIZING
-- --------------
-- 15 sections over 14 unique WMA14 papers (16 files, two of which are the same
-- paper filed under two sessions) carrying 130 questions -- about nine per
-- section.
--
-- Sizing follows what the papers ask, measured over those 14 papers:
--
--   * Proof by contradiction appears in 14 of 14 papers, so it earns a chapter
--     of its own even though the specification gives it a single statement.
--   * Integration by substitution and by parts share one section because the
--     specification pairs them in statement 6.2 and because "by parts" is
--     named in only 1 of 14 papers -- it is examined, but as an unlabelled
--     step, so a separate heading would look empty and mislead.
--   * Vectors gets three sections, not the seven its statements suggest: a P4
--     paper typically carries ONE long vectors question that runs through
--     magnitude, line equations and the scalar product together.
--
-- A CLASSIFIER RULE THIS TREE DEPENDS ON
-- --------------------------------------
-- Parametric equations appear in 14 of 14 papers, but almost never as the
-- task. Chapter 3 is for questions whose OWN subject is the parametric or
-- cartesian form of a curve; a parametric curve that is then differentiated
-- belongs to 5.2 and one that is then integrated to 6.4 or 6.5. Without that
-- rule chapter 3 absorbs most of the paper. This is the same failure the 4PM1
-- book hit with kinematics, and it is fixed the same way -- in the prompt.
--
-- Likewise, "implicit" is never printed in a question: the paper simply gives
-- an equation relating x and y and asks for dy/dx. Section 5.1 must be
-- detected from that shape, not from the word.
--
-- Idempotent: safe to re-run.
-- ============================================================================

BEGIN;

INSERT INTO workbook_chapters (subject_id, number, title, spec_ref)
SELECT s.id, v.number, v.title, v.spec_ref
FROM subjects s
CROSS JOIN (VALUES
  (1, 'Proof',                                'WMA14 P4.3 §1'),
  (2, 'Algebra and functions',                'WMA14 P4.3 §2'),
  (3, 'Coordinate geometry in the (x, y) plane', 'WMA14 P4.3 §3'),
  (4, 'Binomial expansion',                   'WMA14 P4.3 §4'),
  (5, 'Differentiation',                      'WMA14 P4.3 §5'),
  (6, 'Integration',                          'WMA14 P4.3 §6'),
  (7, 'Vectors',                              'WMA14 P4.3 §7')
) AS v(number, title, spec_ref)
WHERE s.code = 'WMA14'
ON CONFLICT (subject_id, number) DO NOTHING;

INSERT INTO workbook_sections (chapter_id, number, title)
SELECT c.id, v.section_number, v.title
FROM workbook_chapters c
JOIN subjects s ON s.id = c.subject_id AND s.code = 'WMA14'
JOIN (VALUES
  -- 1. Proof                                               (spec 1.1)
  (1, 1, 'Proof by contradiction'),

  -- 2. Algebra and functions                               (spec 2.1)
  (2, 1, 'Partial fractions'),

  -- 3. Coordinate geometry in the (x, y) plane             (spec 3.1)
  (3, 1, 'Parametric equations and conversion to cartesian form'),

  -- 4. Binomial expansion                                  (spec 4.1)
  (4, 1, 'Binomial series for any rational n and its range of validity'),

  -- 5. Differentiation                                     (spec 5.1 - 5.2)
  (5, 1, 'Implicit differentiation, tangents and normals'),
  (5, 2, 'Parametric differentiation, tangents and normals'),
  (5, 3, 'Connected rates of change and forming differential equations'),

  -- 6. Integration                                         (spec 6.1 - 6.5)
  (6, 1, 'Integration by substitution and by parts'),
  (6, 2, 'Integration using partial fractions'),
  (6, 3, 'First order differential equations with separable variables'),
  (6, 4, 'Volumes of revolution'),
  (6, 5, 'Area under a curve given parametrically'),

  -- 7. Vectors                                             (spec 7.1 - 7.7)
  (7, 1, 'Vector algebra, magnitude, unit vectors and position vectors'),
  (7, 2, 'Vector equations of lines: parallel, intersecting and skew'),
  (7, 3, 'The scalar product and the angle between two lines')
) AS v(chapter_number, section_number, title)
  ON v.chapter_number = c.number
ON CONFLICT (chapter_id, number) DO NOTHING;

COMMIT;

-- Verification -------------------------------------------------------------
-- SELECT c.number, c.title, count(sec.id) AS sections
-- FROM workbook_chapters c
-- JOIN subjects s ON s.id = c.subject_id AND s.code = 'WMA14'
-- LEFT JOIN workbook_sections sec ON sec.chapter_id = c.id
-- GROUP BY c.number, c.title ORDER BY c.number;
-- Expect: 1->1, 2->1, 3->1, 4->1, 5->3, 6->5, 7->3  (7 chapters, 15 sections)
