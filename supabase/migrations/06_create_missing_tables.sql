-- Migration 06: Bring questions / question_tags / usage_events tables into a
-- known-good state, preserving any existing data.
--
-- Different historical migrations and ad-hoc scripts have created the
-- `questions` table with at least three different shapes:
--   (a) seed/schema.sql      — questions(text, marks, embedding) + question_topics
--   (b) complete_pipeline.py — questions(topic_code, difficulty, page_pdf_url, ...)
--   (c) the new architecture — questions + question_tags
--
-- This migration is fully idempotent: it adds columns / tables / indexes only
-- if missing, and backfills question_tags from any existing topic source
-- (questions.topic_code OR a question_topics junction table). No data is
-- destroyed.

BEGIN;

-- ─────────────────────────────────────────────────────────────────────────────
-- 1. QUESTIONS — create if missing, otherwise add any missing columns
-- ─────────────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS questions (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  paper_id        UUID NOT NULL REFERENCES papers(id) ON DELETE CASCADE,
  question_number TEXT,
  difficulty      TEXT,
  page_pdf_url    TEXT,
  ms_pdf_url      TEXT,
  has_diagram     BOOLEAN   DEFAULT FALSE,
  text_excerpt    TEXT,
  created_at      TIMESTAMPTZ DEFAULT NOW()
);

-- Add columns that may be missing on a pre-existing questions table.
-- These are no-ops if the column already exists.
ALTER TABLE questions ADD COLUMN IF NOT EXISTS question_number TEXT;
ALTER TABLE questions ADD COLUMN IF NOT EXISTS difficulty      TEXT;
ALTER TABLE questions ADD COLUMN IF NOT EXISTS page_pdf_url    TEXT;
ALTER TABLE questions ADD COLUMN IF NOT EXISTS ms_pdf_url      TEXT;
ALTER TABLE questions ADD COLUMN IF NOT EXISTS has_diagram     BOOLEAN DEFAULT FALSE;
ALTER TABLE questions ADD COLUMN IF NOT EXISTS text_excerpt    TEXT;
ALTER TABLE questions ADD COLUMN IF NOT EXISTS created_at      TIMESTAMPTZ DEFAULT NOW();

-- Indexes (idempotent)
CREATE INDEX IF NOT EXISTS idx_questions_paper       ON questions(paper_id);
CREATE INDEX IF NOT EXISTS idx_questions_difficulty  ON questions(difficulty);
CREATE INDEX IF NOT EXISTS idx_questions_with_url
  ON questions(paper_id) WHERE page_pdf_url IS NOT NULL;

-- RLS (idempotent)
ALTER TABLE questions ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "Public read questions" ON questions;
DROP POLICY IF EXISTS "dev_all"               ON questions;
CREATE POLICY "Public read questions" ON questions FOR SELECT USING (true);

-- ─────────────────────────────────────────────────────────────────────────────
-- 2. QUESTION_TAGS — create if missing
-- ─────────────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS question_tags (
  id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  question_id UUID NOT NULL REFERENCES questions(id) ON DELETE CASCADE,
  topic       TEXT NOT NULL,
  created_at  TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE(question_id, topic)
);

CREATE INDEX IF NOT EXISTS idx_question_tags_question ON question_tags(question_id);
CREATE INDEX IF NOT EXISTS idx_question_tags_topic    ON question_tags(topic);

ALTER TABLE question_tags ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "Public read question_tags" ON question_tags;
DROP POLICY IF EXISTS "dev_all"                   ON question_tags;
CREATE POLICY "Public read question_tags" ON question_tags FOR SELECT USING (true);

-- ─────────────────────────────────────────────────────────────────────────────
-- 3. BACKFILL question_tags from any existing topic source
--
--    Source A: questions.topic_code (the column complete_pipeline.py wrote to)
--    Source B: question_topics junction table (the original seed schema)
--
--    Each is wrapped in a DO block so the migration succeeds whether or not
--    the source exists. ON CONFLICT DO NOTHING makes re-runs safe.
-- ─────────────────────────────────────────────────────────────────────────────
DO $$
DECLARE
  inserted_count INT;
BEGIN
  IF EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_schema = 'public'
      AND table_name   = 'questions'
      AND column_name  = 'topic_code'
  ) THEN
    INSERT INTO question_tags (question_id, topic)
    SELECT id, topic_code
    FROM questions
    WHERE topic_code IS NOT NULL AND topic_code <> ''
    ON CONFLICT (question_id, topic) DO NOTHING;
    GET DIAGNOSTICS inserted_count = ROW_COUNT;
    RAISE NOTICE 'Backfilled % question_tags rows from questions.topic_code', inserted_count;
  ELSE
    RAISE NOTICE 'questions.topic_code column not present — skipping topic_code backfill';
  END IF;
END $$;

DO $$
DECLARE
  inserted_count INT;
BEGIN
  IF EXISTS (
    SELECT 1 FROM information_schema.tables
    WHERE table_schema = 'public' AND table_name = 'question_topics'
  ) THEN
    INSERT INTO question_tags (question_id, topic)
    SELECT qt.question_id, t.code
    FROM question_topics qt
    JOIN topics t ON t.id = qt.topic_id
    WHERE t.code IS NOT NULL
    ON CONFLICT (question_id, topic) DO NOTHING;
    GET DIAGNOSTICS inserted_count = ROW_COUNT;
    RAISE NOTICE 'Backfilled % question_tags rows from question_topics junction', inserted_count;
  ELSE
    RAISE NOTICE 'question_topics table not present — skipping junction backfill';
  END IF;
END $$;

-- ─────────────────────────────────────────────────────────────────────────────
-- 4. USAGE_EVENTS — create if missing
-- ─────────────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS usage_events (
  id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id      UUID,
  feature      TEXT NOT NULL,
  subject_id   UUID,
  subject_name TEXT,
  metadata     JSONB,
  created_at   TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_usage_events_user    ON usage_events(user_id);
CREATE INDEX IF NOT EXISTS idx_usage_events_feature ON usage_events(feature);
CREATE INDEX IF NOT EXISTS idx_usage_events_created ON usage_events(created_at);

ALTER TABLE usage_events ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "Service role only" ON usage_events;
CREATE POLICY "Service role only" ON usage_events FOR ALL USING (false);

-- ─────────────────────────────────────────────────────────────────────────────
-- 5. SUMMARY — show how many rows we now have in each table
-- ─────────────────────────────────────────────────────────────────────────────
DO $$
DECLARE
  q_count  INT;
  qt_count INT;
BEGIN
  SELECT COUNT(*) INTO q_count  FROM questions;
  SELECT COUNT(*) INTO qt_count FROM question_tags;
  RAISE NOTICE '--- Migration 06 complete ---';
  RAISE NOTICE '  questions:     % rows', q_count;
  RAISE NOTICE '  question_tags: % rows', qt_count;
END $$;

COMMIT;
