-- GradeMax Supabase Schema
-- Run this entire script in Supabase SQL Editor → New Query
-- This creates all tables, indexes, and RLS policies

-- Enable pgvector extension for embeddings
CREATE EXTENSION IF NOT EXISTS vector;

-- ============================================================================
-- TABLES
-- ============================================================================

-- Subjects: Exam boards, levels, courses
CREATE TABLE IF NOT EXISTS subjects (
  id BIGSERIAL PRIMARY KEY,
  board TEXT NOT NULL,
  level TEXT NOT NULL,
  code TEXT NOT NULL,
  name TEXT NOT NULL,
  color TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE(board, level, code)
);

-- Topics: Specification topics for each subject
CREATE TABLE IF NOT EXISTS topics (
  id BIGSERIAL PRIMARY KEY,
  subject_id BIGINT REFERENCES subjects(id) ON DELETE CASCADE,
  code TEXT NOT NULL,
  name TEXT NOT NULL,
  spec_ref TEXT,
  content TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE(subject_id, code)
);

-- Papers: Past papers metadata
CREATE TABLE IF NOT EXISTS papers (
  id BIGSERIAL PRIMARY KEY,
  subject_id BIGINT REFERENCES subjects(id) ON DELETE CASCADE,
  paper_number TEXT NOT NULL,
  year INT NOT NULL,
  season TEXT NOT NULL,
  pdf_url TEXT,
  markscheme_pdf_url TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE(subject_id, year, season, paper_number)
);

-- Questions: Extracted questions from papers
CREATE TABLE IF NOT EXISTS questions (
  id BIGSERIAL PRIMARY KEY,
  paper_id BIGINT REFERENCES papers(id) ON DELETE CASCADE,
  question_number TEXT NOT NULL,
  text TEXT NOT NULL,
  diagram_urls TEXT[],
  marks INT,
  difficulty INT CHECK (difficulty >= 1 AND difficulty <= 3),
  embedding VECTOR(384), -- MiniLM-L6-v2 dimension
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Markschemes: Answers for questions
CREATE TABLE IF NOT EXISTS markschemes (
  id BIGSERIAL PRIMARY KEY,
  question_id BIGINT REFERENCES questions(id) ON DELETE CASCADE,
  text TEXT NOT NULL,
  marks_breakdown JSONB,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE(question_id)
);

-- Question_Topics: Many-to-many with confidence scores
CREATE TABLE IF NOT EXISTS question_topics (
  id BIGSERIAL PRIMARY KEY,
  question_id BIGINT REFERENCES questions(id) ON DELETE CASCADE,
  topic_id BIGINT REFERENCES topics(id) ON DELETE CASCADE,
  confidence REAL DEFAULT 1.0,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE(question_id, topic_id)
);

-- ============================================================================
-- INDEXES FOR PERFORMANCE
-- ============================================================================

CREATE INDEX IF NOT EXISTS idx_topics_subject_id ON topics(subject_id);
CREATE INDEX IF NOT EXISTS idx_papers_subject_id ON papers(subject_id);
CREATE INDEX IF NOT EXISTS idx_questions_paper_id ON questions(paper_id);
CREATE INDEX IF NOT EXISTS idx_questions_difficulty ON questions(difficulty);
CREATE INDEX IF NOT EXISTS idx_markschemes_question_id ON markschemes(question_id);
CREATE INDEX IF NOT EXISTS idx_question_topics_question_id ON question_topics(question_id);
CREATE INDEX IF NOT EXISTS idx_question_topics_topic_id ON question_topics(topic_id);

-- Vector similarity index for semantic search (IVFFlat)
CREATE INDEX IF NOT EXISTS idx_questions_embedding ON questions 
USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100);

-- ============================================================================
-- ROW LEVEL SECURITY (RLS)
-- ============================================================================

-- Enable RLS on all tables
ALTER TABLE subjects ENABLE ROW LEVEL SECURITY;
ALTER TABLE topics ENABLE ROW LEVEL SECURITY;
ALTER TABLE papers ENABLE ROW LEVEL SECURITY;
ALTER TABLE questions ENABLE ROW LEVEL SECURITY;
ALTER TABLE markschemes ENABLE ROW LEVEL SECURITY;
ALTER TABLE question_topics ENABLE ROW LEVEL SECURITY;

-- Drop existing policies if they exist (for idempotency)
DROP POLICY IF EXISTS "Allow all operations" ON subjects;
DROP POLICY IF EXISTS "Allow all operations" ON topics;
DROP POLICY IF EXISTS "Allow all operations" ON papers;
DROP POLICY IF EXISTS "Allow all operations" ON questions;
DROP POLICY IF EXISTS "Allow all operations" ON markschemes;
DROP POLICY IF EXISTS "Allow all operations" ON question_topics;

-- Create permissive policies (adjust later for production)
CREATE POLICY "Allow all operations" ON subjects FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "Allow all operations" ON topics FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "Allow all operations" ON papers FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "Allow all operations" ON questions FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "Allow all operations" ON markschemes FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "Allow all operations" ON question_topics FOR ALL USING (true) WITH CHECK (true);

-- ============================================================================
-- VERIFICATION
-- ============================================================================

-- Check that all tables exist
SELECT 
  tablename, 
  hasindexes, 
  rowsecurity 
FROM pg_tables 
WHERE schemaname = 'public' 
  AND tablename IN ('subjects', 'topics', 'papers', 'questions', 'markschemes', 'question_topics')
ORDER BY tablename;

-- Check that vector extension is enabled
SELECT * FROM pg_extension WHERE extname = 'vector';
