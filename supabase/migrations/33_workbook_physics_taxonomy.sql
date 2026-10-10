-- ============================================================================
-- 33. Workbook taxonomy for Edexcel International GCSE Physics (4PH1)
-- ============================================================================
--
-- Adds the chapter/section tree the Physics chapterwise workbook is built on.
-- Structure only -- no questions are loaded here; scripts/load_physics_
-- workbook_to_db.py does that, and nothing reaches a student until verified.
--
-- SOURCE
-- ------
-- Pearson Edexcel International GCSE in Physics (4PH1), Specification, Issue 2,
-- April 2018, section 2 "Physics content" (spec pp. 11-28). The eight topic
-- headings are quoted verbatim and numbered as printed.
--
-- SECTIONS = THE SPEC'S OWN SUB-TOPICS, WITH TWO DELIBERATE CHANGES
-- -----------------------------------------------------------------
-- 1. Every topic opens with an "(a) Units" sub-topic. Units are exercised
--    inside every calculation and are never a question's own subject, so they
--    are not sections at all (the same reasoning that made 4MA1's "Applying
--    number" secondary-only, taken one step further because a Units section
--    could never hold a question).
-- 2. Three sub-topics are too broad to practise as one set, so they are split
--    along the spec's own statement ranges -- the split points are where the
--    spec itself changes subject, not where it was convenient:
--      1(c) Forces, movement, shape and momentum  -> 1.2-1.6
--      2(c) Energy and voltage in circuits        -> 2.2-2.3
--      7(b) Radioactivity                         -> 7.1-7.2
--    Every other section is one spec sub-topic, 1:1.
--
-- The legacy 4PH0 papers in the window (2018 Jan to 2019 Jan) are set against
-- the same eight topics, so they share this tree.
--
-- Section -> spec statements:
--   1.1 1.3-1.10   1.2 1.11-1.18   1.3 1.19-1.21   1.4 1.22-1.24
--   1.5 1.25-1.29  1.6 1.30-1.33
--   2.1 2.2-2.6    2.2 2.7-2.13, 2.17-2.19   2.3 2.14-2.16, 2.20-2.21
--   2.4 2.22-2.28
--   3.1 3.2-3.9    3.2 3.10-3.13   3.3 3.14-3.22   3.4 3.23-3.29
--   4.1 4.2-4.5    4.2 4.6-4.10    4.3 4.11-4.17   4.4 4.18-4.19
--   5.1 5.3-5.7    5.2 5.8-5.14    5.3 5.15-5.22
--   6.1 6.2-6.7    6.2 6.8-6.14    6.3 6.15-6.20
--   7.1 7.2-7.10   7.2 7.11-7.16   7.3 7.17-7.26
--   8.1 8.2-8.6    8.2 8.7-8.12    8.3 8.13-8.18
--
-- 8 chapters / 30 sections across 457 measured questions (46 papers, 2018 Jan
-- to 2023 Oct-Nov).
--
-- Idempotent: safe to re-run.
-- ============================================================================

BEGIN;

INSERT INTO workbook_chapters (subject_id, number, title, spec_ref)
SELECT s.id, v.number, v.title, v.spec_ref
FROM subjects s
CROSS JOIN (VALUES
  (1, 'Forces and motion',                     '4PH1 §1'),
  (2, 'Electricity',                           '4PH1 §2'),
  (3, 'Waves',                                 '4PH1 §3'),
  (4, 'Energy resources and energy transfers', '4PH1 §4'),
  (5, 'Solids, liquids and gases',             '4PH1 §5'),
  (6, 'Magnetism and electromagnetism',        '4PH1 §6'),
  (7, 'Radioactivity and particles',           '4PH1 §7'),
  (8, 'Astrophysics',                          '4PH1 §8')
) AS v(number, title, spec_ref)
WHERE s.code = '4PH1'
ON CONFLICT (subject_id, number) DO NOTHING;

INSERT INTO workbook_sections (chapter_id, number, title)
SELECT c.id, v.section_number, v.title
FROM workbook_chapters c
JOIN subjects s ON s.id = c.subject_id AND s.code = '4PH1'
JOIN (VALUES
  -- 1. Forces and motion
  (1, 1, 'Movement and position'),
  (1, 2, 'Forces and their effects'),
  (1, 3, 'Stopping distance and terminal velocity'),
  (1, 4, 'Hooke''s law and elastic behaviour'),
  (1, 5, 'Momentum'),
  (1, 6, 'Moments and centre of gravity'),

  -- 2. Electricity
  (2, 1, 'Mains electricity and electrical power'),
  (2, 2, 'Current, voltage and resistance in circuits'),
  (2, 3, 'Charge, current and energy transfer'),
  (2, 4, 'Electric charge'),

  -- 3. Waves
  (3, 1, 'Properties of waves'),
  (3, 2, 'The electromagnetic spectrum'),
  (3, 3, 'Light: reflection, refraction and total internal reflection'),
  (3, 4, 'Sound'),

  -- 4. Energy resources and energy transfers
  (4, 1, 'Energy stores, transfers and efficiency'),
  (4, 2, 'Thermal energy transfer'),
  (4, 3, 'Work and power'),
  (4, 4, 'Energy resources and electricity generation'),

  -- 5. Solids, liquids and gases
  (5, 1, 'Density and pressure'),
  (5, 2, 'Change of state and specific heat capacity'),
  (5, 3, 'Ideal gas molecules'),

  -- 6. Magnetism and electromagnetism
  (6, 1, 'Magnetism'),
  (6, 2, 'Electromagnetism'),
  (6, 3, 'Electromagnetic induction'),

  -- 7. Radioactivity and particles
  (7, 1, 'Atoms and radioactive emissions'),
  (7, 2, 'Half-life, uses and dangers of radioactivity'),
  (7, 3, 'Fission and fusion'),

  -- 8. Astrophysics
  (8, 1, 'Motion in the universe'),
  (8, 2, 'Stellar evolution'),
  (8, 3, 'Cosmology')
) AS v(chapter_number, section_number, title)
  ON v.chapter_number = c.number
ON CONFLICT (chapter_id, number) DO NOTHING;

COMMIT;

-- Verification -------------------------------------------------------------
-- SELECT c.number, c.title, count(sec.id) AS sections
-- FROM workbook_chapters c
-- JOIN subjects s ON s.id = c.subject_id AND s.code = '4PH1'
-- LEFT JOIN workbook_sections sec ON sec.chapter_id = c.id
-- GROUP BY c.number, c.title ORDER BY c.number;
-- Expect: 1->6, 2->4, 3->4, 4->4, 5->3, 6->3, 7->3, 8->3  (8 chapters, 30 sections)
