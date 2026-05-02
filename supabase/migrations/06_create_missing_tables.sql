-- Migration 06: Create tables required by the questions-based architecture
--
-- The worksheet generator was updated to use a separate `questions` table
-- (with `question_tags` for topic lookups) instead of the `pages` table.
-- These tables were never defined in any prior migration.
-- `usage_events` powers the admin analytics dashboard and is also missing.

BEGIN;

-- ─────────────────────────────────────────────────────────────────────────────
-- 1. QUESTIONS
--    One row per exam question extracted from a paper.
--    Used by: generate-v2 route, worksheet download route.
-- ─────────────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS questions (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  paper_id        UUID NOT NULL REFERENCES papers(id) ON DELETE CASCADE,
  question_number TEXT,
  difficulty      TEXT CHECK (difficulty IN ('easy', 'medium', 'hard')),
  page_pdf_url    TEXT,     -- public URL to the question page PDF
  ms_pdf_url      TEXT,     -- public URL to the mark scheme page PDF
  has_diagram     BOOLEAN   DEFAULT FALSE,
  text_excerpt    TEXT,     -- first ~500 chars for search/display
  created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_questions_paper
  ON questions(paper_id);
CREATE INDEX IF NOT EXISTS idx_questions_difficulty
  ON questions(difficulty);
-- Partial index for the worksheet hot-path (only queryable questions)
CREATE INDEX IF NOT EXISTS idx_questions_with_url
  ON questions(paper_id) WHERE page_pdf_url IS NOT NULL;

ALTER TABLE questions ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Public read questions" ON questions FOR SELECT USING (true);
-- Inserts happen via ingestion scripts using the service role key; no public write needed.


-- ─────────────────────────────────────────────────────────────────────────────
-- 2. QUESTION_TAGS
--    Maps questions to topic codes for overlap filtering.
--    Used by: generate-v2 route (replaces pages.topics array overlap).
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
CREATE POLICY "Public read question_tags" ON question_tags FOR SELECT USING (true);


-- ─────────────────────────────────────────────────────────────────────────────
-- 3. USAGE_EVENTS
--    Append-only audit log for feature usage; powers admin analytics.
--    Written server-side with the service role key (bypasses RLS).
--    Readable only by admins via service role; no client-facing reads.
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
-- Only the service role key may access this table; deny all other callers.
CREATE POLICY "Service role only" ON usage_events FOR ALL USING (false);

COMMIT;
