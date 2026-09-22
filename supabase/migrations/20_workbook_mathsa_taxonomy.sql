-- ============================================================================
-- 20. Workbook taxonomy for Edexcel IGCSE Mathematics A (4MA1), Higher Tier
-- ============================================================================
--
-- Adds the chapter/section tree the Maths A chapterwise workbook is built on.
-- Structure only -- no questions are loaded here; scripts/load_mathsa_workbook_
-- to_db.py does that, and nothing reaches a student until it is verified.
--
-- SOURCE OF THE CHAPTERS AND SECTIONS
-- -----------------------------------
-- Unlike 4MB1 -- where the `topics` table carried ten rows and Calculus had to
-- be added as an eleventh chapter -- 4MA1's specification structure is clean
-- and complete, and `topics` holds NO 4MA1 rows at all. So this tree follows
-- the specification exactly, 1:1, numbered as printed.
--
-- Source: Pearson Edexcel International GCSE in Mathematics (Specification A)
-- (9-1), Specification, Issue 2, November 2017 -- HIGHER TIER content tables,
-- spec pp. 29-41. The six area headings and all 39 sub-topic headings are
-- quoted verbatim from those tables, read out of the PDF rather than restated
-- from memory.
--
--   1. Numbers and the number system      (1.1 - 1.11)
--   2. Equations, formulae and identities (2.1 - 2.8)
--   3. Sequences, functions and graphs    (3.1 - 3.4)
--   4. Geometry and trigonometry          (4.1 - 4.11)
--   5. Vectors and transformation geometry(5.1 - 5.2)
--   6. Statistics and probability         (6.1 - 6.3)
--
-- Note this is the HIGHER tier table, which is what papers 1H and 2H are set
-- against. The Foundation table (spec pp. 7-26) shares the six area headings
-- but has different sub-topic content and is deliberately not used.
--
-- SECTION SIZING
-- --------------
-- 39 sections across 1,042 measured questions (43 papers, 2018 May-Jun to
-- 2025 Oct-Nov) -- about 27 per section, a practice set rather than a reading
-- list, in line with the 4PM1 and 4MB1 books.
--
-- THREE THIN SECTIONS, KEPT DELIBERATELY
-- --------------------------------------
-- 1.10 Applying number, 1.11 Electronic calculators and 4.4 Measures are
-- process statements: they are exercised INSIDE other questions and are never
-- a question's own subject. Dropping them would give 36 sections whose
-- numbering no longer matches the specification; keeping them costs three
-- empty headings that the book generator skips. Keeping is reversible,
-- deleting needs a renumbering migration -- the same call recorded for 4MB1's
-- three empty sections and S1's thin 1.1 and 5.3.
--
-- The classifier rule that follows: 1.10, 1.11 and 4.4 are SECONDARY-only
-- labels and must never be assigned as a primary section. Without that rule a
-- catch-all named "Applying number" absorbs the book -- the same skew that put
-- 111 of 431 FPM questions into one chapter.
--
-- Idempotent: safe to re-run.
-- ============================================================================

BEGIN;

INSERT INTO workbook_chapters (subject_id, number, title, spec_ref)
SELECT s.id, v.number, v.title, v.spec_ref
FROM subjects s
CROSS JOIN (VALUES
  (1, 'Numbers and the number system',       '4MA1 Higher §1'),
  (2, 'Equations, formulae and identities',  '4MA1 Higher §2'),
  (3, 'Sequences, functions and graphs',     '4MA1 Higher §3'),
  (4, 'Geometry and trigonometry',           '4MA1 Higher §4'),
  (5, 'Vectors and transformation geometry', '4MA1 Higher §5'),
  (6, 'Statistics and probability',          '4MA1 Higher §6')
) AS v(number, title, spec_ref)
WHERE s.code = '4MA1'
ON CONFLICT (subject_id, number) DO NOTHING;

INSERT INTO workbook_sections (chapter_id, number, title)
SELECT c.id, v.section_number, v.title
FROM workbook_chapters c
JOIN subjects s ON s.id = c.subject_id AND s.code = '4MA1'
JOIN (VALUES
  -- 1. Numbers and the number system                       (spec 1.1 - 1.11)
  (1,  1, 'Integers'),
  (1,  2, 'Fractions'),
  (1,  3, 'Decimals'),
  (1,  4, 'Powers and roots'),
  (1,  5, 'Set language and notation'),
  (1,  6, 'Percentages'),
  (1,  7, 'Ratio and proportion'),
  (1,  8, 'Degree of accuracy'),
  (1,  9, 'Standard form'),
  (1, 10, 'Applying number'),
  (1, 11, 'Electronic calculators'),

  -- 2. Equations, formulae and identities                  (spec 2.1 - 2.8)
  (2,  1, 'Use of symbols'),
  (2,  2, 'Algebraic manipulation'),
  (2,  3, 'Expressions and formulae'),
  (2,  4, 'Linear equations'),
  (2,  5, 'Proportion'),
  (2,  6, 'Simultaneous linear equations'),
  (2,  7, 'Quadratic equations'),
  (2,  8, 'Inequalities'),

  -- 3. Sequences, functions and graphs                     (spec 3.1 - 3.4)
  (3,  1, 'Sequences'),
  (3,  2, 'Function notation'),
  (3,  3, 'Graphs'),
  (3,  4, 'Calculus'),

  -- 4. Geometry and trigonometry                           (spec 4.1 - 4.11)
  (4,  1, 'Angles, lines and triangles'),
  (4,  2, 'Polygons'),
  (4,  3, 'Symmetry'),
  (4,  4, 'Measures'),
  (4,  5, 'Construction'),
  (4,  6, 'Circle properties'),
  (4,  7, 'Geometrical reasoning'),
  (4,  8, 'Trigonometry and Pythagoras'' theorem'),
  (4,  9, 'Mensuration'),
  (4, 10, '3D shapes and volume'),
  (4, 11, 'Similarity'),

  -- 5. Vectors and transformation geometry                 (spec 5.1 - 5.2)
  (5,  1, 'Vectors'),
  (5,  2, 'Transformation geometry'),

  -- 6. Statistics and probability                          (spec 6.1 - 6.3)
  (6,  1, 'Graphical representation of data'),
  (6,  2, 'Statistical measures'),
  (6,  3, 'Probability')
) AS v(chapter_number, section_number, title)
  ON v.chapter_number = c.number
ON CONFLICT (chapter_id, number) DO NOTHING;

COMMIT;

-- Verification -------------------------------------------------------------
-- SELECT c.number, c.title, count(sec.id) AS sections
-- FROM workbook_chapters c
-- JOIN subjects s ON s.id = c.subject_id AND s.code = '4MA1'
-- LEFT JOIN workbook_sections sec ON sec.chapter_id = c.id
-- GROUP BY c.number, c.title ORDER BY c.number;
-- Expect: 1->11, 2->8, 3->4, 4->11, 5->2, 6->3  (6 chapters, 39 sections)
