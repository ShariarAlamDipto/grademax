-- Migration 12: Chapterwise workbook schema
-- =============================================================================
-- Adds the curated layer behind the chapterwise practice workbook, plus the
-- homework progress tracking that sits on top of it.
--
-- WHY A SEPARATE LAYER FROM `pages`
-- ---------------------------------
-- `pages` is a regenerable ingest layer: re-segmenting a subject deletes and
-- recreates its rows, and that will keep happening as the pipeline improves.
-- Anchoring student progress to `pages.id` would therefore destroy every
-- student's history each time we fix a segmentation bug.
--
-- `workbook_questions` is the stable identity layer. Each question carries a
-- slug -- FPM.CH09.S04.Q021 -- that survives re-segmentation, re-classification
-- and extension to new years. `workbook_attempts` references THAT, never
-- `pages`. The link back to source material is by (paper, question_number),
-- which is stable regardless of how the PDFs were cut.
--
-- The two tools also want different things: the test builder wants randomised
-- questions matching filters, whereas a workbook needs a fixed, ordered,
-- verified sequence identical for every student -- so that "Chapter 5,
-- questions 12 to 20" means the same thing to everyone in the room.
--
-- Everything here is idempotent and safe to re-run.
-- =============================================================================

BEGIN;

-- ── Reference layer: chapters and sections ───────────────────────────────────

CREATE TABLE IF NOT EXISTS workbook_chapters (
  id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  subject_id  UUID NOT NULL REFERENCES subjects(id) ON DELETE CASCADE,
  number      INTEGER NOT NULL,           -- 1..10, follows the specification order
  title       TEXT NOT NULL,
  spec_ref    TEXT,                       -- specification section this maps to
  created_at  TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE (subject_id, number)
);

CREATE TABLE IF NOT EXISTS workbook_sections (
  id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  chapter_id  UUID NOT NULL REFERENCES workbook_chapters(id) ON DELETE CASCADE,
  number      INTEGER NOT NULL,           -- 1..n within the chapter; displays as 9.4
  title       TEXT NOT NULL,
  created_at  TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE (chapter_id, number)
);

-- Recurring question shapes. Edexcel reuses archetypes heavily, and the
-- workbook clusters repeats together rather than deleting them: meeting the
-- same shape four times in four papers' clothing is how pattern recognition
-- gets built.
CREATE TABLE IF NOT EXISTS workbook_archetypes (
  id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  section_id  UUID REFERENCES workbook_sections(id) ON DELETE SET NULL,
  label       TEXT NOT NULL,
  description TEXT,
  created_at  TIMESTAMPTZ DEFAULT NOW()
);

-- ── The book itself ──────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS workbook_questions (
  id                    UUID PRIMARY KEY DEFAULT gen_random_uuid(),

  -- Stable identity. Never regenerate these: attempts reference them forever.
  slug                  TEXT NOT NULL UNIQUE,   -- FPM.CH09.S04.Q021

  subject_id            UUID NOT NULL REFERENCES subjects(id) ON DELETE CASCADE,
  section_id            UUID NOT NULL REFERENCES workbook_sections(id),
  archetype_id          UUID REFERENCES workbook_archetypes(id) ON DELETE SET NULL,

  -- Position in the printed book.
  ordinal_in_chapter    INTEGER NOT NULL,

  -- Provenance, by natural key rather than by pages.id so it survives re-cuts.
  source_paper_id       UUID REFERENCES papers(id) ON DELETE SET NULL,
  source_paper_key      TEXT NOT NULL,          -- 2022_jan_2
  source_question_number INTEGER NOT NULL,

  marks                 INTEGER NOT NULL CHECK (marks > 0),
  difficulty            TEXT CHECK (difficulty IN ('easy', 'medium', 'hard')),
  sub_parts             JSONB,                  -- [{"label":"a","marks":2}, ...]

  qp_pdf_url            TEXT,
  ms_pdf_url            TEXT,                   -- NULL prints "mark scheme unavailable"

  stem                  TEXT,                   -- classifier input, not printed
  text_status           TEXT CHECK (text_status IN ('ok', 'repaired', 'needs_vision')),

  -- Chapters this question also touches. Primary chapter decides where it is
  -- printed; these make it findable from the others.
  secondary_section_ids UUID[] NOT NULL DEFAULT '{}',

  -- Set once a human has confirmed the section assignment. The book only ships
  -- verified questions.
  verified_by           UUID,
  verified_at           TIMESTAMPTZ,

  created_at            TIMESTAMPTZ DEFAULT NOW(),
  updated_at            TIMESTAMPTZ DEFAULT NOW(),

  UNIQUE (source_paper_key, source_question_number)
);

CREATE INDEX IF NOT EXISTS idx_workbook_questions_section
  ON workbook_questions(section_id, ordinal_in_chapter);
CREATE INDEX IF NOT EXISTS idx_workbook_questions_subject
  ON workbook_questions(subject_id);
CREATE INDEX IF NOT EXISTS idx_workbook_questions_archetype
  ON workbook_questions(archetype_id);
CREATE INDEX IF NOT EXISTS idx_workbook_questions_secondary
  ON workbook_questions USING GIN(secondary_section_ids);
CREATE INDEX IF NOT EXISTS idx_workbook_questions_unverified
  ON workbook_questions(subject_id) WHERE verified_at IS NULL;

-- ── Progress ─────────────────────────────────────────────────────────────────

-- One row per student per question. Chapter and section completion are derived
-- from this at read time -- no denormalised counters to drift out of sync.
CREATE TABLE IF NOT EXISTS workbook_attempts (
  id                   UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id              UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  workbook_question_id UUID NOT NULL REFERENCES workbook_questions(id) ON DELETE CASCADE,

  status               TEXT NOT NULL DEFAULT 'not_started'
                       CHECK (status IN ('not_started', 'attempted', 'correct', 'flagged')),
  marks_scored         INTEGER CHECK (marks_scored >= 0),
  seconds_spent        INTEGER CHECK (seconds_spent >= 0),
  notes                TEXT,

  attempted_at         TIMESTAMPTZ,
  created_at           TIMESTAMPTZ DEFAULT NOW(),
  updated_at           TIMESTAMPTZ DEFAULT NOW(),

  UNIQUE (user_id, workbook_question_id)
);

CREATE INDEX IF NOT EXISTS idx_workbook_attempts_user
  ON workbook_attempts(user_id);
CREATE INDEX IF NOT EXISTS idx_workbook_attempts_question
  ON workbook_attempts(workbook_question_id);
CREATE INDEX IF NOT EXISTS idx_workbook_attempts_flagged
  ON workbook_attempts(user_id) WHERE status = 'flagged';

-- ── Assignments ──────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS workbook_assignments (
  id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  teacher_id  UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  subject_id  UUID NOT NULL REFERENCES subjects(id) ON DELETE CASCADE,
  title       TEXT NOT NULL,
  instructions TEXT,

  -- Either a whole section, or an explicit question list. Exactly one.
  section_id  UUID REFERENCES workbook_sections(id) ON DELETE CASCADE,
  question_ids UUID[] NOT NULL DEFAULT '{}',

  due_date    DATE,
  created_at  TIMESTAMPTZ DEFAULT NOW(),
  updated_at  TIMESTAMPTZ DEFAULT NOW(),

  CONSTRAINT assignment_has_a_target CHECK (
    (section_id IS NOT NULL AND cardinality(question_ids) = 0)
    OR (section_id IS NULL AND cardinality(question_ids) > 0)
  )
);

CREATE TABLE IF NOT EXISTS workbook_assignment_members (
  id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  assignment_id UUID NOT NULL REFERENCES workbook_assignments(id) ON DELETE CASCADE,
  student_id    UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  created_at    TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE (assignment_id, student_id)
);

CREATE INDEX IF NOT EXISTS idx_workbook_assignments_teacher
  ON workbook_assignments(teacher_id);
CREATE INDEX IF NOT EXISTS idx_workbook_assignment_members_student
  ON workbook_assignment_members(student_id);

-- ── Row level security ───────────────────────────────────────────────────────
-- Reference data is world-readable; progress data is not. Unlike the older
-- tables in this schema, nothing here uses a blanket USING(true) for writes --
-- attempts are personal, and a permissive policy would let any signed-in user
-- read or rewrite another student's homework record.

ALTER TABLE workbook_chapters            ENABLE ROW LEVEL SECURITY;
ALTER TABLE workbook_sections            ENABLE ROW LEVEL SECURITY;
ALTER TABLE workbook_archetypes          ENABLE ROW LEVEL SECURITY;
ALTER TABLE workbook_questions           ENABLE ROW LEVEL SECURITY;
ALTER TABLE workbook_attempts            ENABLE ROW LEVEL SECURITY;
ALTER TABLE workbook_assignments         ENABLE ROW LEVEL SECURITY;
ALTER TABLE workbook_assignment_members  ENABLE ROW LEVEL SECURITY;

-- Reference layer: anyone may read. Writes go through the service role only,
-- which bypasses RLS, so no write policy is defined at all.
DROP POLICY IF EXISTS "Public read workbook chapters"   ON workbook_chapters;
DROP POLICY IF EXISTS "Public read workbook sections"   ON workbook_sections;
DROP POLICY IF EXISTS "Public read workbook archetypes" ON workbook_archetypes;
DROP POLICY IF EXISTS "Public read workbook questions"  ON workbook_questions;

CREATE POLICY "Public read workbook chapters"   ON workbook_chapters   FOR SELECT USING (true);
CREATE POLICY "Public read workbook sections"   ON workbook_sections   FOR SELECT USING (true);
CREATE POLICY "Public read workbook archetypes" ON workbook_archetypes FOR SELECT USING (true);
-- Only verified questions are publicly visible; unverified ones are visible to
-- the admin tooling, which uses the service role.
CREATE POLICY "Public read workbook questions"  ON workbook_questions  FOR SELECT
  USING (verified_at IS NOT NULL);

-- Attempts: a student owns their own rows, full stop.
DROP POLICY IF EXISTS "Students read own attempts"   ON workbook_attempts;
DROP POLICY IF EXISTS "Students insert own attempts" ON workbook_attempts;
DROP POLICY IF EXISTS "Students update own attempts" ON workbook_attempts;
DROP POLICY IF EXISTS "Students delete own attempts" ON workbook_attempts;
DROP POLICY IF EXISTS "Teachers read assignee attempts" ON workbook_attempts;

CREATE POLICY "Students read own attempts"   ON workbook_attempts FOR SELECT USING (auth.uid() = user_id);
CREATE POLICY "Students insert own attempts" ON workbook_attempts FOR INSERT WITH CHECK (auth.uid() = user_id);
CREATE POLICY "Students update own attempts" ON workbook_attempts FOR UPDATE
  USING (auth.uid() = user_id) WITH CHECK (auth.uid() = user_id);
CREATE POLICY "Students delete own attempts" ON workbook_attempts FOR DELETE USING (auth.uid() = user_id);

-- A teacher sees a student's attempts only where they have actually assigned
-- work to that student -- not by virtue of holding the teacher role.
CREATE POLICY "Teachers read assignee attempts" ON workbook_attempts FOR SELECT
  USING (
    EXISTS (
      SELECT 1
      FROM workbook_assignment_members m
      JOIN workbook_assignments a ON a.id = m.assignment_id
      WHERE m.student_id = workbook_attempts.user_id
        AND a.teacher_id = auth.uid()
    )
  );

-- Assignments: owned by the teacher who created them; readable by their members.
DROP POLICY IF EXISTS "Teachers manage own assignments" ON workbook_assignments;
DROP POLICY IF EXISTS "Students read their assignments" ON workbook_assignments;
DROP POLICY IF EXISTS "Teachers manage assignment members" ON workbook_assignment_members;
DROP POLICY IF EXISTS "Students read own membership" ON workbook_assignment_members;

CREATE POLICY "Teachers manage own assignments" ON workbook_assignments FOR ALL
  USING (auth.uid() = teacher_id) WITH CHECK (auth.uid() = teacher_id);

CREATE POLICY "Students read their assignments" ON workbook_assignments FOR SELECT
  USING (
    EXISTS (
      SELECT 1 FROM workbook_assignment_members m
      WHERE m.assignment_id = workbook_assignments.id
        AND m.student_id = auth.uid()
    )
  );

CREATE POLICY "Teachers manage assignment members" ON workbook_assignment_members FOR ALL
  USING (
    EXISTS (
      SELECT 1 FROM workbook_assignments a
      WHERE a.id = workbook_assignment_members.assignment_id
        AND a.teacher_id = auth.uid()
    )
  )
  WITH CHECK (
    EXISTS (
      SELECT 1 FROM workbook_assignments a
      WHERE a.id = workbook_assignment_members.assignment_id
        AND a.teacher_id = auth.uid()
    )
  );

CREATE POLICY "Students read own membership" ON workbook_assignment_members FOR SELECT
  USING (auth.uid() = student_id);

-- ── Seed: Further Pure Mathematics (4PM1) chapters and sections ──────────────
-- Chapter numbering follows the 4PM1 specification order so the book maps onto
-- how the subject is taught and examined. Sections are the homework unit: one
-- section is intended to be one sitting.

INSERT INTO workbook_chapters (subject_id, number, title, spec_ref)
SELECT s.id, v.number, v.title, v.spec_ref
FROM subjects s
CROSS JOIN (VALUES
  (1,  'Logarithmic functions and indices',   '4PM1 §1'),
  (2,  'The quadratic function',              '4PM1 §2'),
  (3,  'Identities and inequalities',         '4PM1 §3'),
  (4,  'Graphs',                              '4PM1 §4'),
  (5,  'Series',                              '4PM1 §5'),
  (6,  'The binomial series',                 '4PM1 §6'),
  (7,  'Scalar and vector quantities',        '4PM1 §7'),
  (8,  'Rectangular Cartesian coordinates',   '4PM1 §8'),
  (9,  'Calculus',                            '4PM1 §9'),
  (10, 'Trigonometry',                        '4PM1 §10')
) AS v(number, title, spec_ref)
WHERE s.code = '4PM1'
ON CONFLICT (subject_id, number) DO NOTHING;

INSERT INTO workbook_sections (chapter_id, number, title)
SELECT c.id, v.section_number, v.title
FROM workbook_chapters c
JOIN subjects s ON s.id = c.subject_id AND s.code = '4PM1'
JOIN (VALUES
  (1,  1, 'Laws of indices and surds'),
  (1,  2, 'Laws of logarithms'),
  (1,  3, 'Change of base'),
  (1,  4, 'Exponential and logarithmic equations'),

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
  (5,  2, 'Geometric series'),
  (5,  3, 'Sum to infinity and convergence'),
  (5,  4, 'Sigma notation and standard results'),

  (6,  1, 'Expansion for positive integer n'),
  (6,  2, 'General term and named coefficients'),
  (6,  3, 'Fractional and negative indices, validity'),
  (6,  4, 'Approximations using the binomial series'),

  (7,  1, 'Vector algebra and magnitude'),
  (7,  2, 'Position vectors and ratio division'),
  (7,  3, 'Collinearity and parallel vectors'),
  (7,  4, 'Vector proof in geometry'),

  (8,  1, 'Distance, midpoint and gradient'),
  (8,  2, 'Equations of straight lines'),
  (8,  3, 'Parallel and perpendicular lines'),
  (8,  4, 'Areas of rectilinear figures'),
  (8,  5, 'Loci and the circle'),

  (9,  1, 'First principles and standard results'),
  (9,  2, 'Product, quotient and chain rules'),
  (9,  3, 'Stationary points and their nature'),
  (9,  4, 'Tangents, normals and rates of change'),
  (9,  5, 'Integration as the reverse process'),
  (9,  6, 'Definite integrals and area under a curve'),
  (9,  7, 'Volumes of revolution'),
  (9,  8, 'Kinematics'),

  (10, 1, 'Exact values and the unit circle'),
  (10, 2, 'Sine rule, cosine rule and area of a triangle'),
  (10, 3, 'Identities and compound angles'),
  (10, 4, 'The R-formula'),
  (10, 5, 'Solving trigonometric equations'),
  (10, 6, 'Radians, arc length and sector area')
) AS v(chapter_number, section_number, title)
  ON v.chapter_number = c.number
ON CONFLICT (chapter_id, number) DO NOTHING;

COMMIT;

-- Verify:
--   SELECT c.number, c.title, count(s.id) AS sections
--   FROM workbook_chapters c
--   LEFT JOIN workbook_sections s ON s.chapter_id = c.id
--   GROUP BY c.number, c.title ORDER BY c.number;
-- Expect 10 chapters and 47 sections.
