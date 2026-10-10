-- ============================================================================
-- 34. Workbook taxonomy for IAL Mechanics 1 (WME01)
-- ============================================================================
--
-- The chapter/section tree for the M1 chapterwise workbook. Structure only;
-- scripts/load_m1_workbook_to_db.py loads the questions.
--
-- SOURCE
-- ------
-- Pearson Edexcel International Advanced Subsidiary/Advanced Level in
-- Mathematics, Further Mathematics and Pure Mathematics, Specification,
-- Issue 3, April 2019 -- Unit M1, section M1.3 "Unit content", pp. 45-46.
-- The six topic headings and their statements are followed 1:1, numbered as
-- printed, with ONE split:
--
--   Topic 3 "Kinematics of a particle moving in a straight line" is a single
--   statement (3.1 "Motion in a straight line with constant acceleration"),
--   whose guidance names three distinct demands: the constant-acceleration
--   formulae, motion under gravity, and "displacement-time, velocity-time,
--   speed-time and acceleration-time graphs". Left whole it would hold about
--   a fifth of the book, so it is split along that guidance into 3.1-3.3.
--
-- 1.1 Modelling assumptions is examined as the "state an assumption" tail of a
-- question about something else, never as a question's subject. It is kept so
-- the tree matches the spec, and the classifier treats it as SECONDARY-only.
--
-- 6 chapters / 14 sections, sized against 169 measured questions (22 papers,
-- January 2019 to June 2026).
--
-- Idempotent: safe to re-run.
-- ============================================================================

BEGIN;

INSERT INTO workbook_chapters (subject_id, number, title, spec_ref)
SELECT s.id, v.number, v.title, v.spec_ref
FROM subjects s
CROSS JOIN (VALUES
  (1, 'Mathematical models in mechanics',                     'WME01 M1.3 §1'),
  (2, 'Vectors in mechanics',                                 'WME01 M1.3 §2'),
  (3, 'Kinematics of a particle moving in a straight line',   'WME01 M1.3 §3'),
  (4, 'Dynamics of a particle moving in a straight line or plane', 'WME01 M1.3 §4'),
  (5, 'Statics of a particle',                                'WME01 M1.3 §5'),
  (6, 'Moments',                                              'WME01 M1.3 §6')
) AS v(number, title, spec_ref)
WHERE s.code = 'WME01'
ON CONFLICT (subject_id, number) DO NOTHING;

INSERT INTO workbook_sections (chapter_id, number, title)
SELECT c.id, v.section_number, v.title
FROM workbook_chapters c
JOIN subjects s ON s.id = c.subject_id AND s.code = 'WME01'
JOIN (VALUES
  -- 1. Mathematical models in mechanics
  (1, 1, 'Modelling assumptions'),

  -- 2. Vectors in mechanics
  (2, 1, 'Magnitude, direction and resultant of vectors'),
  (2, 2, 'Vectors for displacement, velocity, acceleration and force'),

  -- 3. Kinematics of a particle moving in a straight line (spec 3.1, split)
  (3, 1, 'Constant acceleration formulae'),
  (3, 2, 'Vertical motion under gravity'),
  (3, 3, 'Motion graphs'),

  -- 4. Dynamics of a particle moving in a straight line or plane
  (4, 1, 'Forces and Newton''s laws of motion'),
  (4, 2, 'Connected particles, pulleys and inclined planes'),
  (4, 3, 'Momentum and impulse'),
  (4, 4, 'Friction in motion'),

  -- 5. Statics of a particle
  (5, 1, 'Resolving forces'),
  (5, 2, 'Equilibrium of a particle'),
  (5, 3, 'Friction in equilibrium'),

  -- 6. Moments
  (6, 1, 'Moments and equilibrium of rods')
) AS v(chapter_number, section_number, title)
  ON v.chapter_number = c.number
ON CONFLICT (chapter_id, number) DO NOTHING;

COMMIT;

-- Verification -------------------------------------------------------------
-- Expect: 1->1, 2->2, 3->3, 4->4, 5->3, 6->1  (6 chapters, 14 sections)
