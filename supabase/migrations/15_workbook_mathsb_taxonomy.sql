-- ============================================================================
-- 15. Workbook taxonomy for Edexcel IGCSE Mathematics B (4MB1)
-- ============================================================================
--
-- Adds the chapter/section tree the Maths B chapterwise workbook is built on.
-- Structure only -- no questions are loaded here; scripts/load_mathsb_workbook_
-- to_db.py does that, and nothing reaches a student until it is verified.
--
-- ELEVEN CHAPTERS, NOT TEN
-- ------------------------
-- The `topics` table already carries ten 4MB1 topics and they match the
-- specification's headline list. Calculus is not among them, but it is plainly
-- examined: 11 of the 56 papers in the 2016-2022 window ask candidates to
-- differentiate, find turning points, or work with a velocity-time
-- relationship. Filing that under Algebra would put a distinct skill behind a
-- heading a student would not think to open, so it gets chapter 11.
--
-- The workbook tree is deliberately independent of `topics`: `topics` drives
-- the test builder's tagging, this drives the book's contents page, and the two
-- serve different readers.
--
-- SECTION SIZING
-- --------------
-- 50 sections across 1,069 questions -- around 21 per section, which is a
-- practice set rather than a reading list. Sections are named for what a
-- student would practise in one sitting, not for how the specification words
-- its assessment objectives.
--
-- Idempotent: safe to re-run.
-- ============================================================================

BEGIN;

INSERT INTO workbook_chapters (subject_id, number, title, spec_ref)
SELECT s.id, v.number, v.title, v.spec_ref
FROM subjects s
CROSS JOIN (VALUES
  (1,  'Number',                             '4MB1 §1'),
  (2,  'Sets',                               '4MB1 §2'),
  (3,  'Algebra',                            '4MB1 §3'),
  (4,  'Functions',                          '4MB1 §4'),
  (5,  'Matrices',                           '4MB1 §5'),
  (6,  'Geometry',                           '4MB1 §6'),
  (7,  'Mensuration',                        '4MB1 §7'),
  (8,  'Vectors and transformation geometry','4MB1 §8'),
  (9,  'Trigonometry',                       '4MB1 §9'),
  (10, 'Statistics and probability',         '4MB1 §10'),
  (11, 'Calculus',                           '4MB1 §11')
) AS v(number, title, spec_ref)
WHERE s.code = '4MB1'
ON CONFLICT (subject_id, number) DO NOTHING;

INSERT INTO workbook_sections (chapter_id, number, title)
SELECT c.id, v.section_number, v.title
FROM workbook_chapters c
JOIN subjects s ON s.id = c.subject_id AND s.code = '4MB1'
JOIN (VALUES
  -- 1. Number
  (1,  1, 'Fractions, decimals and percentages'),
  (1,  2, 'Ratio, proportion and rates of change'),
  (1,  3, 'Indices, surds and standard form'),
  (1,  4, 'Accuracy, bounds and estimation'),

  -- 2. Sets
  (2,  1, 'Set notation and Venn diagrams'),
  (2,  2, 'Two-set problems'),
  (2,  3, 'Three-set problems'),

  -- 3. Algebra
  (3,  1, 'Expanding, factorising and simplifying'),
  (3,  2, 'Linear equations and inequalities'),
  (3,  3, 'Simultaneous equations'),
  (3,  4, 'Quadratic equations'),
  (3,  5, 'Algebraic fractions'),
  (3,  6, 'Rearranging formulae and changing the subject'),
  (3,  7, 'Sequences and the nth term'),

  -- 4. Functions
  (4,  1, 'Function notation, domain and range'),
  (4,  2, 'Composite functions'),
  (4,  3, 'Inverse functions'),
  (4,  4, 'Graphs of functions and graphical solutions'),

  -- 5. Matrices
  (5,  1, 'Matrix arithmetic'),
  (5,  2, 'Determinants and inverse matrices'),
  (5,  3, 'Solving simultaneous equations with matrices'),
  (5,  4, 'Matrix transformations'),

  -- 6. Geometry
  (6,  1, 'Angles, parallel lines and polygons'),
  (6,  2, 'Triangles, congruence and similarity'),
  (6,  3, 'Circle theorems'),
  (6,  4, 'Pythagoras'' theorem'),
  (6,  5, 'Constructions and loci'),

  -- 7. Mensuration
  (7,  1, 'Perimeter and area of plane shapes'),
  (7,  2, 'Circles, arcs and sectors'),
  (7,  3, 'Volume and surface area of solids'),
  (7,  4, 'Similar shapes: length, area and volume'),

  -- 8. Vectors and transformation geometry
  (8,  1, 'Vector arithmetic and magnitude'),
  (8,  2, 'Position vectors and geometric proof'),
  (8,  3, 'Single transformations'),
  (8,  4, 'Combined and inverse transformations'),

  -- 9. Trigonometry
  (9,  1, 'Right-angled triangle trigonometry'),
  (9,  2, 'The sine rule'),
  (9,  3, 'The cosine rule and the area of a triangle'),
  (9,  4, 'Bearings and three-dimensional problems'),
  (9,  5, 'Trigonometric graphs and equations'),

  -- 10. Statistics and probability
  (10, 1, 'Presenting and interpreting data'),
  (10, 2, 'Averages and measures of spread'),
  (10, 3, 'Cumulative frequency and box plots'),
  (10, 4, 'Histograms and frequency density'),
  (10, 5, 'Probability of single and combined events'),
  (10, 6, 'Tree diagrams and conditional probability'),

  -- 11. Calculus
  (11, 1, 'Differentiating polynomials'),
  (11, 2, 'Gradients, tangents and normals'),
  (11, 3, 'Turning points and their nature'),
  (11, 4, 'Kinematics: displacement, velocity and acceleration')
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
