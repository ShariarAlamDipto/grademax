-- ============================================================================
-- 27. Workbook taxonomies for Edexcel IAL Pure Mathematics 1, 2 and 3
--     (WMA11, WMA12, WMA13)
-- ============================================================================
--
-- Completes the IAL pure series alongside migration 19 (P4). Structure only --
-- no questions are loaded here, and nothing reaches a student until verified.
--
-- SOURCE OF THE CHAPTERS
-- ----------------------
-- Each unit's chapters are the numbered content headings of its "Unit content"
-- section in the Pearson Edexcel International Advanced Subsidiary / Advanced
-- Level in Mathematics, Further Mathematics and Pure Mathematics specification,
-- Issue 3, April 2019 -- P1.3 (pp. 14-16), P2.3 (pp. 18-20), P3.3 (pp. 21-25),
-- quoted verbatim:
--
--   P1: 1 Algebra and functions · 2 Coordinate geometry in the (x, y) plane ·
--       3 Trigonometry · 4 Differentiation · 5 Integration
--   P2: 1 Proof · 2 Algebra and functions ·
--       3 Coordinate geometry in the (x, y) plane · 4 Sequences and series ·
--       5 Exponentials and logarithms · 6 Trigonometry · 7 Differentiation ·
--       8 Integration
--   P3: 1 Algebra and functions · 2 Trigonometry ·
--       3 Exponential and logarithms · 4 Differentiation · 5 Integration ·
--       6 Numerical methods
--
-- P3's third heading reads "Exponential and logarithms" in the specification,
-- not "Exponentials". Kept as printed rather than silently corrected, so the
-- tree can be diffed against the source document.
--
-- TWO HEADINGS THAT SETTLE AN EARLIER QUESTION
-- --------------------------------------------
-- P2 statement 8.3 is the trapezium rule and P3 statements 6.1-6.2 are
-- numerical root-finding and iteration. Those are exactly the two topics whose
-- presence identified the mislabelled legacy papers in the P4 folder (10 of 14
-- legacy papers examined the trapezium rule, 0 of 14 genuine WMA14 ones). The
-- specification confirms independently that they belong to P2 and P3.
--
-- SECTION SIZING
-- --------------
-- P1 17, P2 17, P3 16 sections, against roughly 190 / 190 / 155 questions from
-- 19 / 19 / 17 genuine papers -- about eleven per section, matching the 4PM1,
-- 4MB1, WST01 and WMA14 books.
--
-- Idempotent: safe to re-run.
-- ============================================================================

BEGIN;

-- ── P1 (WMA11) ──────────────────────────────────────────────────────────────

INSERT INTO workbook_chapters (subject_id, number, title, spec_ref)
SELECT s.id, v.number, v.title, v.spec_ref
FROM subjects s
CROSS JOIN (VALUES
  (1, 'Algebra and functions',                    'WMA11 P1.3 §1'),
  (2, 'Coordinate geometry in the (x, y) plane',  'WMA11 P1.3 §2'),
  (3, 'Trigonometry',                             'WMA11 P1.3 §3'),
  (4, 'Differentiation',                          'WMA11 P1.3 §4'),
  (5, 'Integration',                              'WMA11 P1.3 §5')
) AS v(number, title, spec_ref)
WHERE s.code = 'WMA11'
ON CONFLICT (subject_id, number) DO NOTHING;

INSERT INTO workbook_sections (chapter_id, number, title)
SELECT c.id, v.section_number, v.title
FROM workbook_chapters c
JOIN subjects s ON s.id = c.subject_id AND s.code = 'WMA11'
JOIN (VALUES
  -- 1. Algebra and functions                        (spec 1.1 - 1.12)
  (1, 1, 'Laws of indices'),
  (1, 2, 'Surds and rationalising denominators'),
  (1, 3, 'Quadratic equations and completing the square'),
  (1, 4, 'The discriminant'),
  (1, 5, 'Simultaneous equations'),
  (1, 6, 'Linear and quadratic inequalities'),
  (1, 7, 'Polynomials: expanding, factorising and simplifying'),
  (1, 8, 'Sketching curves and graphs of functions'),
  (1, 9, 'Transformations of graphs'),

  -- 2. Coordinate geometry in the (x, y) plane      (spec 2.1 - 2.2)
  (2, 1, 'Equation of a straight line'),
  (2, 2, 'Parallel and perpendicular lines'),

  -- 3. Trigonometry                                 (spec 3.1 - 3.3)
  (3, 1, 'The sine and cosine rules and the area of a triangle'),
  (3, 2, 'Radian measure, arc length and sector area'),
  (3, 3, 'Trigonometric graphs, symmetry and periodicity'),

  -- 4. Differentiation                              (spec 4.1 - 4.3)
  (4, 1, 'Differentiating powers of x and the gradient function'),
  (4, 2, 'Tangents and normals'),

  -- 5. Integration                                  (spec 5.1 - 5.2)
  (5, 1, 'Indefinite integration and the constant of integration')
) AS v(chapter_number, section_number, title)
  ON v.chapter_number = c.number
ON CONFLICT (chapter_id, number) DO NOTHING;

-- ── P2 (WMA12) ──────────────────────────────────────────────────────────────

INSERT INTO workbook_chapters (subject_id, number, title, spec_ref)
SELECT s.id, v.number, v.title, v.spec_ref
FROM subjects s
CROSS JOIN (VALUES
  (1, 'Proof',                                    'WMA12 P2.3 §1'),
  (2, 'Algebra and functions',                    'WMA12 P2.3 §2'),
  (3, 'Coordinate geometry in the (x, y) plane',  'WMA12 P2.3 §3'),
  (4, 'Sequences and series',                     'WMA12 P2.3 §4'),
  (5, 'Exponentials and logarithms',              'WMA12 P2.3 §5'),
  (6, 'Trigonometry',                             'WMA12 P2.3 §6'),
  (7, 'Differentiation',                          'WMA12 P2.3 §7'),
  (8, 'Integration',                              'WMA12 P2.3 §8')
) AS v(number, title, spec_ref)
WHERE s.code = 'WMA12'
ON CONFLICT (subject_id, number) DO NOTHING;

INSERT INTO workbook_sections (chapter_id, number, title)
SELECT c.id, v.section_number, v.title
FROM workbook_chapters c
JOIN subjects s ON s.id = c.subject_id AND s.code = 'WMA12'
JOIN (VALUES
  -- 1. Proof                                        (spec 1.1 - 1.3)
  (1, 1, 'Proof by exhaustion and disproof by counter-example'),

  -- 2. Algebra and functions                        (spec 2.1)
  (2, 1, 'Algebraic division, the factor theorem and the remainder theorem'),

  -- 3. Coordinate geometry in the (x, y) plane      (spec 3.1)
  (3, 1, 'Equation of a circle and its geometry'),

  -- 4. Sequences and series                         (spec 4.1 - 4.5)
  (4, 1, 'Sequences, nth terms and recurrence relations'),
  (4, 2, 'Arithmetic sequences and series'),
  (4, 3, 'Geometric sequences and series'),
  (4, 4, 'Binomial expansion for positive integer n'),

  -- 5. Exponentials and logarithms                  (spec 5.1 - 5.3)
  (5, 1, 'Exponential functions and their graphs'),
  (5, 2, 'Laws of logarithms'),
  (5, 3, 'Solving equations of the form a^x = b'),

  -- 6. Trigonometry                                 (spec 6.1 - 6.2)
  (6, 1, 'Trigonometric identities'),
  (6, 2, 'Solving trigonometric equations in a given interval'),

  -- 7. Differentiation                              (spec 7.1)
  (7, 1, 'Stationary points, maxima and minima'),
  (7, 2, 'Increasing and decreasing functions and optimisation'),

  -- 8. Integration                                  (spec 8.1 - 8.3)
  (8, 1, 'Definite integrals'),
  (8, 2, 'Area under and between curves'),
  (8, 3, 'The trapezium rule')
) AS v(chapter_number, section_number, title)
  ON v.chapter_number = c.number
ON CONFLICT (chapter_id, number) DO NOTHING;

-- ── P3 (WMA13) ──────────────────────────────────────────────────────────────

INSERT INTO workbook_chapters (subject_id, number, title, spec_ref)
SELECT s.id, v.number, v.title, v.spec_ref
FROM subjects s
CROSS JOIN (VALUES
  (1, 'Algebra and functions',        'WMA13 P3.3 §1'),
  (2, 'Trigonometry',                 'WMA13 P3.3 §2'),
  (3, 'Exponential and logarithms',   'WMA13 P3.3 §3'),
  (4, 'Differentiation',              'WMA13 P3.3 §4'),
  (5, 'Integration',                  'WMA13 P3.3 §5'),
  (6, 'Numerical methods',            'WMA13 P3.3 §6')
) AS v(number, title, spec_ref)
WHERE s.code = 'WMA13'
ON CONFLICT (subject_id, number) DO NOTHING;

INSERT INTO workbook_sections (chapter_id, number, title)
SELECT c.id, v.section_number, v.title
FROM workbook_chapters c
JOIN subjects s ON s.id = c.subject_id AND s.code = 'WMA13'
JOIN (VALUES
  -- 1. Algebra and functions                        (spec 1.1 - 1.4)
  (1, 1, 'Rational expressions and algebraic division'),
  (1, 2, 'Functions: domain, range and composition'),
  (1, 3, 'Inverse functions and their graphs'),
  (1, 4, 'The modulus function'),
  (1, 5, 'Combined transformations of graphs'),

  -- 2. Trigonometry                                 (spec 2.1 - 2.3)
  (2, 1, 'Secant, cosecant, cotangent and the inverse trigonometric functions'),
  (2, 2, 'Trigonometric identities and proving identities'),
  (2, 3, 'Compound and double angle formulae'),
  -- Spec 2.3 names a cos t + b sin t -> r cos (t +- a) explicitly, and requires
  -- solving a cos t + b sin t = c in a given interval, so it earns a section.
  (2, 4, 'The form r cos (theta +- alpha) and solving a cos + b sin = c'),

  -- 3. Exponential and logarithms                   (spec 3.1 - 3.3)
  (3, 1, 'The functions e^x and ln x'),
  (3, 2, 'Solving exponential and logarithmic equations'),
  (3, 3, 'Logarithmic graphs to estimate parameters'),

  -- 4. Differentiation                              (spec 4.1 - 4.4)
  (4, 1, 'Differentiating exponential, logarithmic and trigonometric functions'),
  (4, 2, 'The product, quotient and chain rules'),
  (4, 3, 'Exponential growth and decay'),

  -- 5. Integration                                  (spec 5.1 - 5.2)
  (5, 1, 'Integrating standard functions'),
  (5, 2, 'Integration by recognition of known derivatives'),

  -- 6. Numerical methods                            (spec 6.1 - 6.2)
  (6, 1, 'Locating roots by change of sign'),
  (6, 2, 'Iterative methods and recurrence relations')
) AS v(chapter_number, section_number, title)
  ON v.chapter_number = c.number
ON CONFLICT (chapter_id, number) DO NOTHING;

COMMIT;

-- Verification -------------------------------------------------------------
-- SELECT s.code, c.number, c.title, count(sec.id) AS sections
-- FROM workbook_chapters c
-- JOIN subjects s ON s.id = c.subject_id AND s.code IN ('WMA11','WMA12','WMA13')
-- LEFT JOIN workbook_sections sec ON sec.chapter_id = c.id
-- GROUP BY s.code, c.number, c.title ORDER BY s.code, c.number;
-- Expect: WMA11 5 chapters / 17 sections, WMA12 8 / 17, WMA13 6 / 19
