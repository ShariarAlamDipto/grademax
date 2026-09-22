-- ============================================================================
-- 18. Workbook taxonomy for Edexcel IAL Statistics 1 (WST01)
-- ============================================================================
--
-- Adds the chapter/section tree the S1 chapterwise workbook is built on.
-- Structure only -- no questions are loaded here; the loader does that, and
-- nothing reaches a student until it is verified.
--
-- SOURCE OF THE CHAPTERS
-- ----------------------
-- The six chapters are the six numbered content headings of section S1.3
-- "Unit content" in the Pearson Edexcel International Advanced Subsidiary /
-- Advanced Level in Mathematics, Further Mathematics and Pure Mathematics
-- specification, Issue 3, April 2019 (pp. 55-56), quoted verbatim:
--
--   1. Mathematical models in probability and statistics
--   2. Representation and summary of data
--   3. Probability
--   4. Correlation and regression
--   5. Discrete random variables
--   6. The Normal distribution
--
-- Note that the unit DESCRIPTION (p. 53) also lists "discrete distributions"
-- as though it were a seventh area, but the unit content table folds it into
-- topic 5 as statement 5.4 "The discrete uniform distribution". The content
-- table wins -- it is what the assessment is written against.
--
-- A genuine typo in the specification, recorded so nobody re-derives it: the
-- single statement under heading "6. The Normal distribution" is numbered
-- "5.1", not "6.1". It is treated here as 6.1.
--
-- SECTION SIZING
-- --------------
-- 19 sections. The corpus is 28 unique WST01 question papers (2014-2025; 31
-- files, three of which are the same paper filed under two sessions) carrying
-- roughly 184 questions, so a section averages about ten -- a practice set
-- rather than a reading list, matching the 4PM1 and 4MB1 books.
--
-- Sections are sized against what the papers actually ask, measured over those
-- 28 papers rather than assumed. Two are expected to stay small and are kept
-- deliberately:
--
--   1.1  Modelling in probability and statistics -- topic 1 is never a
--        standalone question. It is examined as the "comment on the
--        suitability of this model" tail of a question about something else,
--        so it will mostly appear as a SECONDARY section label.
--   5.3  The discrete uniform distribution -- named in only 2 of 28 papers,
--        but it is an explicit specification statement (5.4) and a student
--        revising it needs somewhere to look.
--
-- Keeping a thin section costs a heading the book generator can skip. Deleting
-- one costs a renumbering migration. Keep is reversible; delete is not.
--
-- Idempotent: safe to re-run.
-- ============================================================================

BEGIN;

INSERT INTO workbook_chapters (subject_id, number, title, spec_ref)
SELECT s.id, v.number, v.title, v.spec_ref
FROM subjects s
CROSS JOIN (VALUES
  (1, 'Mathematical models in probability and statistics', 'WST01 S1.3 §1'),
  (2, 'Representation and summary of data',                'WST01 S1.3 §2'),
  (3, 'Probability',                                       'WST01 S1.3 §3'),
  (4, 'Correlation and regression',                         'WST01 S1.3 §4'),
  (5, 'Discrete random variables',                          'WST01 S1.3 §5'),
  (6, 'The Normal distribution',                            'WST01 S1.3 §6')
) AS v(number, title, spec_ref)
WHERE s.code = 'WST01'
ON CONFLICT (subject_id, number) DO NOTHING;

INSERT INTO workbook_sections (chapter_id, number, title)
SELECT c.id, v.section_number, v.title
FROM workbook_chapters c
JOIN subjects s ON s.id = c.subject_id AND s.code = 'WST01'
JOIN (VALUES
  -- 1. Mathematical models in probability and statistics   (spec 1.1)
  (1, 1, 'Modelling in probability and statistics'),

  -- 2. Representation and summary of data                  (spec 2.1 - 2.4)
  (2, 1, 'Measures of location and dispersion'),
  (2, 2, 'Coding'),
  (2, 3, 'Quartiles, percentiles and linear interpolation'),
  (2, 4, 'Histograms and frequency density'),
  (2, 5, 'Stem and leaf diagrams and box plots'),
  (2, 6, 'Skewness, outliers and comparing distributions'),

  -- 3. Probability                                         (spec 3.1 - 3.4)
  (3, 1, 'Sample space, elementary probability and the addition law'),
  (3, 2, 'Venn diagrams'),
  (3, 3, 'Conditional probability and independence'),
  (3, 4, 'Tree diagrams and sampling with and without replacement'),

  -- 4. Correlation and regression                          (spec 4.1 - 4.3)
  (4, 1, 'Scatter diagrams and the summary statistics Sxx, Syy and Sxy'),
  (4, 2, 'The product moment correlation coefficient'),
  (4, 3, 'The least squares regression line, prediction and coding'),

  -- 5. Discrete random variables                           (spec 5.1 - 5.4)
  (5, 1, 'Probability distributions and the cumulative distribution function'),
  (5, 2, 'Expectation and variance'),
  (5, 3, 'The discrete uniform distribution'),

  -- 6. The Normal distribution                             (spec 6.1)
  (6, 1, 'Standardising, z-values and the Normal tables'),
  (6, 2, 'Finding an unknown mean or standard deviation')
) AS v(chapter_number, section_number, title)
  ON v.chapter_number = c.number
ON CONFLICT (chapter_id, number) DO NOTHING;

COMMIT;

-- Verification -------------------------------------------------------------
-- SELECT c.number, c.title, count(sec.id) AS sections
-- FROM workbook_chapters c
-- JOIN subjects s ON s.id = c.subject_id AND s.code = 'WST01'
-- LEFT JOIN workbook_sections sec ON sec.chapter_id = c.id
-- GROUP BY c.number, c.title ORDER BY c.number;
-- Expect: 1->1, 2->6, 3->4, 4->3, 5->3, 6->2  (6 chapters, 19 sections)
