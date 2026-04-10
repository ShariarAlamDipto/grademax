-- ============================================================================
-- Migration 03: Seed Further Pure Mathematics topics
-- Subject code: 9FM0 (Edexcel IGCSE Further Pure Maths)
--
-- IMPORTANT: The classifier stores topic IDs "1"–"10" in pages.topics.
-- These codes MUST match so that topic filtering works in the worksheet
-- generator and test builder.
-- ============================================================================

BEGIN;

DO $$
DECLARE
  fpm_id UUID;
  topic_count INT;
BEGIN
  SELECT id INTO fpm_id
  FROM subjects
  WHERE code IN ('9FM0', '4PM1')
  ORDER BY (CASE WHEN code = '9FM0' THEN 0 ELSE 1 END)
  LIMIT 1;

  IF fpm_id IS NULL THEN
    RAISE EXCEPTION 'Further Pure Maths subject (9FM0 / 4PM1) not found. Ensure it is in the subjects table first.';
  END IF;

  RAISE NOTICE 'Found FPM subject ID: %', fpm_id;

  -- Remove any existing FPM topics to avoid duplicates
  SELECT COUNT(*) INTO topic_count FROM topics WHERE subject_id = fpm_id;
  IF topic_count > 0 THEN
    RAISE NOTICE 'Deleting % existing FPM topics…', topic_count;
    DELETE FROM topics WHERE subject_id = fpm_id;
  END IF;

  -- Insert 10 topics matching YAML classifier IDs ("1"–"10")
  INSERT INTO topics (subject_id, code, name, description) VALUES
    (fpm_id, '1',  'Logarithmic functions & indices',
     'Laws of logarithms, change of base, surds, rationalising denominators, exponential graphs'),
    (fpm_id, '2',  'Quadratic functions',
     'Quadratic formula, discriminant (b²−4ac), completing the square, sum/product of roots'),
    (fpm_id, '3',  'Identities & inequalities',
     'Algebraic division, factor & remainder theorem, proving identities, inequality regions'),
    (fpm_id, '4',  'Graphs',
     'Sketching rational functions, transformations of functions, asymptotes and intercepts'),
    (fpm_id, '5',  'Series',
     'Arithmetic and geometric series sums, convergence (|r|<1), sigma notation'),
    (fpm_id, '6',  'Binomial series',
     '(1+x)ⁿ expansion, general term nCk, binomial for negative/fractional n with range'),
    (fpm_id, '7',  'Scalar & vector quantities',
     'Magnitude |a|, position vectors, displacement, vector addition/subtraction, parallel/collinear tests'),
    (fpm_id, '8',  'Rectangular Cartesian coordinates',
     'Distance formula, gradient & perpendicularity, equation of line, circle centre-radius form'),
    (fpm_id, '9',  'Calculus',
     'Differentiate xⁿ, eˣ, ln x; product/quotient/chain rules; integrate xⁿ; area under curve; stationary points'),
    (fpm_id, '10', 'Trigonometry',
     'R-formula (a sin x + b cos x), compound angle identities, trig equations & exact values, trig graphs');

  SELECT COUNT(*) INTO topic_count FROM topics WHERE subject_id = fpm_id;
  RAISE NOTICE 'Inserted % FPM topics.', topic_count;
END $$;

COMMIT;
