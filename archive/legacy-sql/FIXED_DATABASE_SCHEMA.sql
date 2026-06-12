-- Fixed Database Schema for GradeMax
-- This extends the existing schema safely without breaking existing tables
-- Run this in Supabase SQL Editor

-- ============================================================================
-- PART 1: Enable Extensions
-- ============================================================================

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- ============================================================================
-- PART 2: Profiles Table (CRITICAL - fixes login loop)
-- ============================================================================

CREATE TABLE IF NOT EXISTS profiles (
  id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
  email TEXT,
  full_name TEXT,
  avatar_url TEXT,
  study_level TEXT CHECK (study_level IN ('igcse', 'ial', 'a-level')),
  marks_goal_pct INT DEFAULT 90 CHECK (marks_goal_pct >= 0 AND marks_goal_pct <= 100),
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- RLS Policies for profiles
ALTER TABLE profiles ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "Users can view own profile" ON profiles;
CREATE POLICY "Users can view own profile" ON profiles
  FOR SELECT USING (auth.uid() = id);

DROP POLICY IF EXISTS "Users can update own profile" ON profiles;
CREATE POLICY "Users can update own profile" ON profiles
  FOR UPDATE USING (auth.uid() = id);

DROP POLICY IF EXISTS "Users can insert own profile" ON profiles;
CREATE POLICY "Users can insert own profile" ON profiles
  FOR INSERT WITH CHECK (auth.uid() = id);

-- Function to create profile on signup
CREATE OR REPLACE FUNCTION public.handle_new_user()
RETURNS TRIGGER AS $$
BEGIN
  INSERT INTO public.profiles (id, email, full_name, avatar_url)
  VALUES (
    NEW.id,
    NEW.email,
    NEW.raw_user_meta_data->>'full_name',
    NEW.raw_user_meta_data->>'avatar_url'
  )
  ON CONFLICT (id) DO NOTHING;
  RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Trigger to auto-create profile
DROP TRIGGER IF EXISTS on_auth_user_created ON auth.users;
CREATE TRIGGER on_auth_user_created
  AFTER INSERT ON auth.users
  FOR EACH ROW
  EXECUTE FUNCTION public.handle_new_user();

-- ============================================================================
-- PART 3: Extend Papers Table
-- ============================================================================

-- Add new columns to existing papers table
ALTER TABLE papers ADD COLUMN IF NOT EXISTS board TEXT;
ALTER TABLE papers ADD COLUMN IF NOT EXISTS level TEXT;
ALTER TABLE papers ADD COLUMN IF NOT EXISTS subject_code TEXT;
ALTER TABLE papers ADD COLUMN IF NOT EXISTS subject_name TEXT;
ALTER TABLE papers ADD COLUMN IF NOT EXISTS paper_type TEXT;
ALTER TABLE papers ADD COLUMN IF NOT EXISTS variant TEXT;
ALTER TABLE papers ADD COLUMN IF NOT EXISTS pdf_path TEXT;
ALTER TABLE papers ADD COLUMN IF NOT EXISTS doc_hash TEXT;
ALTER TABLE papers ADD COLUMN IF NOT EXISTS meta JSONB;
ALTER TABLE papers ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ DEFAULT NOW();

-- Add constraint for paper_type
DO $$ 
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint WHERE conname = 'papers_paper_type_check'
  ) THEN
    ALTER TABLE papers ADD CONSTRAINT papers_paper_type_check 
      CHECK (paper_type IS NULL OR paper_type IN ('QP', 'MS'));
  END IF;
END $$;

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_papers_doc_hash ON papers(doc_hash);
CREATE INDEX IF NOT EXISTS idx_papers_board_level ON papers(board, level);
CREATE INDEX IF NOT EXISTS idx_papers_year ON papers(year DESC);

-- Enable RLS for papers
ALTER TABLE papers ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "Authenticated users can view papers" ON papers;
CREATE POLICY "Authenticated users can view papers" ON papers
  FOR SELECT TO authenticated USING (true);

-- ============================================================================
-- PART 4: Extend Questions Table
-- ============================================================================

-- Add new columns from migration 004
ALTER TABLE questions ADD COLUMN IF NOT EXISTS header_bbox JSONB;
ALTER TABLE questions ADD COLUMN IF NOT EXISTS header_visual_url TEXT;
ALTER TABLE questions ADD COLUMN IF NOT EXISTS context_text TEXT;
ALTER TABLE questions ADD COLUMN IF NOT EXISTS total_marks INT;
ALTER TABLE questions ADD COLUMN IF NOT EXISTS quality_flags TEXT[];
ALTER TABLE questions ADD COLUMN IF NOT EXISTS doc_hash TEXT;
ALTER TABLE questions ADD COLUMN IF NOT EXISTS difficulty TEXT;
ALTER TABLE questions ADD COLUMN IF NOT EXISTS difficulty_score REAL;
ALTER TABLE questions ADD COLUMN IF NOT EXISTS estimated_time_minutes INT;
ALTER TABLE questions ADD COLUMN IF NOT EXISTS style TEXT[];
ALTER TABLE questions ADD COLUMN IF NOT EXISTS characteristics TEXT[];
ALTER TABLE questions ADD COLUMN IF NOT EXISTS markscheme_text TEXT;
ALTER TABLE questions ADD COLUMN IF NOT EXISTS ms_page_range JSONB;
ALTER TABLE questions ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ DEFAULT NOW();

-- Add constraint for difficulty
DO $$ 
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint WHERE conname = 'questions_difficulty_check'
  ) THEN
    ALTER TABLE questions ADD CONSTRAINT questions_difficulty_check 
      CHECK (difficulty IS NULL OR difficulty IN ('easy', 'medium', 'hard'));
  END IF;
END $$;

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_questions_paper ON questions(paper_id);
CREATE INDEX IF NOT EXISTS idx_questions_doc_hash ON questions(doc_hash);
CREATE INDEX IF NOT EXISTS idx_questions_difficulty ON questions(difficulty);
CREATE INDEX IF NOT EXISTS idx_questions_context_text ON questions USING gin(to_tsvector('english', context_text));

-- Enable RLS for questions
ALTER TABLE questions ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "Authenticated users can view questions" ON questions;
CREATE POLICY "Authenticated users can view questions" ON questions
  FOR SELECT TO authenticated USING (true);

-- ============================================================================
-- PART 5: Question Parts Table
-- ============================================================================

CREATE TABLE IF NOT EXISTS question_parts (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  question_id UUID NOT NULL REFERENCES questions(id) ON DELETE CASCADE,
  code TEXT NOT NULL,
  marks INT,
  page_from INT NOT NULL,
  page_to INT NOT NULL,
  bbox_list JSONB NOT NULL,
  text_preview TEXT,
  visual_hash TEXT,
  answer_space_lines INT DEFAULT 0,
  ms_link_confidence REAL DEFAULT 0.0,
  ms_points JSONB,
  ms_snippet TEXT,
  features JSONB,
  spec_refs TEXT[],
  diagram_urls TEXT[],
  diagram_dims JSONB,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE(question_id, code)
);

CREATE INDEX IF NOT EXISTS idx_question_parts_question ON question_parts(question_id);
CREATE INDEX IF NOT EXISTS idx_question_parts_visual_hash ON question_parts(visual_hash);
CREATE INDEX IF NOT EXISTS idx_question_parts_ms_confidence ON question_parts(ms_link_confidence);

-- RLS for question_parts
ALTER TABLE question_parts ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "Authenticated users can view parts" ON question_parts;
CREATE POLICY "Authenticated users can view parts" ON question_parts
  FOR SELECT TO authenticated USING (true);

-- ============================================================================
-- PART 6: Question Tags Table
-- ============================================================================

CREATE TABLE IF NOT EXISTS question_tags (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  paper_id UUID REFERENCES papers(id) ON DELETE CASCADE,
  question_id UUID REFERENCES questions(id) ON DELETE CASCADE,
  topic TEXT NOT NULL,
  confidence REAL NOT NULL,
  provenance TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE(question_id, topic)
);

CREATE INDEX IF NOT EXISTS idx_question_tags_question ON question_tags(question_id);
CREATE INDEX IF NOT EXISTS idx_question_tags_topic ON question_tags(topic);
CREATE INDEX IF NOT EXISTS idx_question_tags_paper ON question_tags(paper_id);

-- RLS for question_tags
ALTER TABLE question_tags ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "Authenticated users can view tags" ON question_tags;
CREATE POLICY "Authenticated users can view tags" ON question_tags
  FOR SELECT TO authenticated USING (true);

-- ============================================================================
-- PART 7: Ingestions Tracking Table
-- ============================================================================

CREATE TABLE IF NOT EXISTS ingestions (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  paper_id UUID REFERENCES papers(id) ON DELETE CASCADE,
  status TEXT CHECK (status IN ('pending', 'processing', 'completed', 'failed')) DEFAULT 'pending',
  questions_found INT DEFAULT 0,
  parts_found INT DEFAULT 0,
  tags_found INT DEFAULT 0,
  error TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  completed_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_ingestions_paper ON ingestions(paper_id);
CREATE INDEX IF NOT EXISTS idx_ingestions_status ON ingestions(status);
CREATE INDEX IF NOT EXISTS idx_ingestions_created ON ingestions(created_at DESC);

-- RLS for ingestions
ALTER TABLE ingestions ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "Authenticated users can view ingestions" ON ingestions;
CREATE POLICY "Authenticated users can view ingestions" ON ingestions
  FOR SELECT TO authenticated USING (true);

DROP POLICY IF EXISTS "Authenticated users can insert ingestions" ON ingestions;
CREATE POLICY "Authenticated users can insert ingestions" ON ingestions
  FOR INSERT TO authenticated WITH CHECK (true);

DROP POLICY IF EXISTS "Authenticated users can update ingestions" ON ingestions;
CREATE POLICY "Authenticated users can update ingestions" ON ingestions
  FOR UPDATE TO authenticated USING (true);

-- ============================================================================
-- PART 8: Worksheets Table
-- ============================================================================

CREATE TABLE IF NOT EXISTS worksheets (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
  title TEXT,
  description TEXT,
  params JSONB,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Add new columns if they don't exist
ALTER TABLE worksheets ADD COLUMN IF NOT EXISTS title TEXT;
ALTER TABLE worksheets ADD COLUMN IF NOT EXISTS description TEXT;
ALTER TABLE worksheets ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ DEFAULT NOW();

CREATE INDEX IF NOT EXISTS idx_worksheets_user ON worksheets(user_id);

-- RLS for worksheets
ALTER TABLE worksheets ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "Users can view own worksheets" ON worksheets;
CREATE POLICY "Users can view own worksheets" ON worksheets
  FOR SELECT USING (auth.uid() = user_id);

DROP POLICY IF EXISTS "Users can insert own worksheets" ON worksheets;
CREATE POLICY "Users can insert own worksheets" ON worksheets
  FOR INSERT WITH CHECK (auth.uid() = user_id);

DROP POLICY IF EXISTS "Users can update own worksheets" ON worksheets;
CREATE POLICY "Users can update own worksheets" ON worksheets
  FOR UPDATE USING (auth.uid() = user_id);

DROP POLICY IF EXISTS "Users can delete own worksheets" ON worksheets;
CREATE POLICY "Users can delete own worksheets" ON worksheets
  FOR DELETE USING (auth.uid() = user_id);

-- ============================================================================
-- PART 9: Worksheet Items Table
-- ============================================================================

CREATE TABLE IF NOT EXISTS worksheet_items (
  worksheet_id UUID REFERENCES worksheets(id) ON DELETE CASCADE,
  question_id UUID REFERENCES questions(id) ON DELETE CASCADE,
  position INT,
  PRIMARY KEY (worksheet_id, question_id)
);

-- Add new columns if they don't exist (for future enhancements)
ALTER TABLE worksheet_items ADD COLUMN IF NOT EXISTS part_code TEXT;
ALTER TABLE worksheet_items ADD COLUMN IF NOT EXISTS marks INT;
ALTER TABLE worksheet_items ADD COLUMN IF NOT EXISTS answer_space_lines INT DEFAULT 0;
ALTER TABLE worksheet_items ADD COLUMN IF NOT EXISTS spec_refs TEXT[];
ALTER TABLE worksheet_items ADD COLUMN IF NOT EXISTS ms_points JSONB;
ALTER TABLE worksheet_items ADD COLUMN IF NOT EXISTS estimated_seconds INT;
ALTER TABLE worksheet_items ADD COLUMN IF NOT EXISTS bbox_cache JSONB;
ALTER TABLE worksheet_items ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ DEFAULT NOW();

CREATE INDEX IF NOT EXISTS idx_worksheet_items_worksheet ON worksheet_items(worksheet_id);
CREATE INDEX IF NOT EXISTS idx_worksheet_items_question ON worksheet_items(question_id);
CREATE INDEX IF NOT EXISTS idx_worksheet_items_position ON worksheet_items(worksheet_id, position);

-- RLS for worksheet_items
ALTER TABLE worksheet_items ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "Users can view own worksheet items" ON worksheet_items;
CREATE POLICY "Users can view own worksheet items" ON worksheet_items
  FOR SELECT USING (
    worksheet_id IN (
      SELECT id FROM worksheets WHERE user_id = auth.uid()
    )
  );

DROP POLICY IF EXISTS "Users can insert own worksheet items" ON worksheet_items;
CREATE POLICY "Users can insert own worksheet items" ON worksheet_items
  FOR INSERT WITH CHECK (
    worksheet_id IN (
      SELECT id FROM worksheets WHERE user_id = auth.uid()
    )
  );

DROP POLICY IF EXISTS "Users can update own worksheet items" ON worksheet_items;
CREATE POLICY "Users can update own worksheet items" ON worksheet_items
  FOR UPDATE USING (
    worksheet_id IN (
      SELECT id FROM worksheets WHERE user_id = auth.uid()
    )
  );

DROP POLICY IF EXISTS "Users can delete own worksheet items" ON worksheet_items;
CREATE POLICY "Users can delete own worksheet items" ON worksheet_items
  FOR DELETE USING (
    worksheet_id IN (
      SELECT id FROM worksheets WHERE user_id = auth.uid()
    )
  );

-- ============================================================================
-- PART 10: Update Timestamp Triggers
-- ============================================================================

CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Add triggers for updated_at columns
DROP TRIGGER IF EXISTS update_profiles_updated_at ON profiles;
CREATE TRIGGER update_profiles_updated_at
  BEFORE UPDATE ON profiles
  FOR EACH ROW
  EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_papers_updated_at ON papers;
CREATE TRIGGER update_papers_updated_at
  BEFORE UPDATE ON papers
  FOR EACH ROW
  EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_questions_updated_at ON questions;
CREATE TRIGGER update_questions_updated_at
  BEFORE UPDATE ON questions
  FOR EACH ROW
  EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_question_parts_updated_at ON question_parts;
CREATE TRIGGER update_question_parts_updated_at
  BEFORE UPDATE ON question_parts
  FOR EACH ROW
  EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_worksheets_updated_at ON worksheets;
CREATE TRIGGER update_worksheets_updated_at
  BEFORE UPDATE ON worksheets
  FOR EACH ROW
  EXECUTE FUNCTION update_updated_at_column();

-- ============================================================================
-- Migration Complete
-- ============================================================================

DO $$
BEGIN
  RAISE NOTICE '✅ Fixed database schema applied successfully!';
  RAISE NOTICE '';
  RAISE NOTICE 'Tables created/updated:';
  RAISE NOTICE '  ✅ profiles (with auto-creation trigger) - FIXES LOGIN LOOP';
  RAISE NOTICE '  ✅ papers (extended with new columns)';
  RAISE NOTICE '  ✅ questions (extended with new columns)';
  RAISE NOTICE '  ✅ question_parts';
  RAISE NOTICE '  ✅ question_tags';
  RAISE NOTICE '  ✅ ingestions';
  RAISE NOTICE '  ✅ worksheets';
  RAISE NOTICE '  ✅ worksheet_items';
  RAISE NOTICE '';
  RAISE NOTICE '🔒 All tables have RLS enabled with proper policies';
  RAISE NOTICE '✅ Ready to use!';
  RAISE NOTICE '';
  RAISE NOTICE '👉 Next: Test login at http://localhost:3001/login';
END $$;
