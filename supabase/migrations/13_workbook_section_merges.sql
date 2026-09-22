-- Migration 13: Merge redundant workbook sections (4PM1)
-- =============================================================================
-- Migration 12 seeded 47 sections from the specification. Running the whole
-- 2016-2022 corpus through classification showed six of them never attract a
-- question, and the reason matters: they are not absent topics, they are
-- boundaries drawn in the wrong place.
--
--   1.3 Change of base                  -> always examined inside a log-law question
--   5.3 Sum to infinity and convergence -> inseparable from geometric series
--   6.2 General term / named coefficients -> the same question as the expansion
--   6.4 Approximations using binomial   -> a rider on a fractional-index expansion
--   8.3 Parallel and perpendicular      -> always part of finding a line equation
--   9.7 Volumes of revolution           -> examined alongside area under a curve
--
-- 3.3 "Proving identities" is deliberately KEPT even though it also drew zero
-- questions. It is a genuine skill; the classifier was routing trigonometric
-- proofs to 10.3 instead. That is fixed with a prompt rule rather than by
-- deleting the section.
--
-- Sections are the homework unit -- a section is meant to be one sitting -- so
-- a section nobody can be set is worse than no section at all. 47 -> 41.
--
-- Sections are renumbered contiguously so the printed book reads 1.1, 1.2, 1.3
-- rather than 1.1, 1.2, 1.4. The mapping applied to already-classified data:
--
--   1.3->1.2  1.4->1.3        5.3->5.2  5.4->5.3
--   6.2->6.1  6.3->6.2  6.4->6.2
--   8.3->8.2  8.4->8.3  8.5->8.4
--   9.7->9.6  9.8->9.7
--
-- Safe to re-run. Refuses to run if any question already references a section.
-- =============================================================================

BEGIN;

-- Renumbering would silently orphan question rows. Fail loudly instead.
DO $$
BEGIN
  IF EXISTS (SELECT 1 FROM workbook_questions) THEN
    RAISE EXCEPTION
      'workbook_questions is not empty -- renumbering sections would orphan % row(s). Remap them explicitly first.',
      (SELECT count(*) FROM workbook_questions);
  END IF;
END $$;

DELETE FROM workbook_sections
WHERE chapter_id IN (
  SELECT c.id FROM workbook_chapters c
  JOIN subjects s ON s.id = c.subject_id
  WHERE s.code = '4PM1'
);

INSERT INTO workbook_sections (chapter_id, number, title)
SELECT c.id, v.section_number, v.title
FROM workbook_chapters c
JOIN subjects s ON s.id = c.subject_id AND s.code = '4PM1'
JOIN (VALUES
  (1,  1, 'Laws of indices and surds'),
  (1,  2, 'Laws of logarithms and change of base'),
  (1,  3, 'Exponential and logarithmic equations'),

  (2,  1, 'Completing the square'),
  (2,  2, 'The discriminant and the nature of roots'),
  (2,  3, 'Sum and product of roots'),
  (2,  4, 'Forming new equations from roots'),

  (3,  1, 'Algebraic division'),
  (3,  2, 'Factor and remainder theorem'),
  (3,  3, 'Proving identities'),
  (3,  4, 'Linear and quadratic inequalities'),

  (4,  1, 'Sketching polynomial and rational curves'),
  (4,  2, 'Asymptotes and intercepts'),
  (4,  3, 'Transformations of graphs'),
  (4,  4, 'Graphical solution of equations'),

  (5,  1, 'Arithmetic series'),
  (5,  2, 'Geometric series and sum to infinity'),
  (5,  3, 'Sigma notation and standard results'),

  (6,  1, 'Binomial expansion and the general term'),
  (6,  2, 'Fractional and negative indices, validity and approximations'),

  (7,  1, 'Vector algebra and magnitude'),
  (7,  2, 'Position vectors and ratio division'),
  (7,  3, 'Collinearity and parallel vectors'),
  (7,  4, 'Vector proof in geometry'),

  (8,  1, 'Distance, midpoint and gradient'),
  (8,  2, 'Equations of straight lines, parallel and perpendicular'),
  (8,  3, 'Areas of rectilinear figures'),
  (8,  4, 'Loci and the circle'),

  (9,  1, 'First principles and standard results'),
  (9,  2, 'Product, quotient and chain rules'),
  (9,  3, 'Stationary points and their nature'),
  (9,  4, 'Tangents, normals and rates of change'),
  (9,  5, 'Integration as the reverse process'),
  (9,  6, 'Definite integrals, area and volumes of revolution'),
  (9,  7, 'Kinematics'),

  (10, 1, 'Exact values and the unit circle'),
  (10, 2, 'Sine rule, cosine rule and area of a triangle'),
  (10, 3, 'Identities and compound angles'),
  (10, 4, 'The R-formula'),
  (10, 5, 'Solving trigonometric equations'),
  (10, 6, 'Radians, arc length and sector area')
) AS v(chapter_number, section_number, title)
  ON v.chapter_number = c.number
ON CONFLICT (chapter_id, number) DO UPDATE SET title = EXCLUDED.title;

COMMIT;

-- Verify:
--   SELECT c.number, count(s.id) AS sections
--   FROM workbook_chapters c
--   LEFT JOIN workbook_sections s ON s.chapter_id = c.id
--   GROUP BY c.number ORDER BY c.number;
-- Expect 10 chapters and 41 sections (3,4,4,4,3,2,4,4,7,6).
