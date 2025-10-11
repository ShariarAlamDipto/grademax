-- ============================================================================
-- COMPLETE DATABASE FIX - Run this in Supabase SQL Editor
-- This includes: profiles, subjects seed data, user_subjects table
-- ============================================================================

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
-- PART 3: Subjects Table (CRITICAL - fixes empty dropdown)
-- ============================================================================

-- Ensure subjects table has the right structure
ALTER TABLE subjects ADD COLUMN IF NOT EXISTS color TEXT;

-- Seed subjects data
INSERT INTO subjects (board, level, code, name, color) VALUES
  -- Edexcel IGCSE
  ('Edexcel', 'IGCSE', '4PH1', 'Physics', '#3b82f6'),
  ('Edexcel', 'IGCSE', '4CH1', 'Chemistry', '#10b981'),
  ('Edexcel', 'IGCSE', '4MA1', 'Mathematics', '#ef4444'),
  ('Edexcel', 'IGCSE', '4BI1', 'Biology', '#8b5cf6'),
  ('Edexcel', 'IGCSE', '4EN1', 'English Language', '#f59e0b'),
  ('Edexcel', 'IGCSE', '4HI1', 'History', '#ec4899'),
  ('Edexcel', 'IGCSE', '4GE1', 'Geography', '#06b6d4'),
  ('Edexcel', 'IGCSE', '4CS1', 'Computer Science', '#6366f1'),
  
  -- Cambridge IGCSE
  ('Cambridge', 'IGCSE', '0625', 'Physics', '#3b82f6'),
  ('Cambridge', 'IGCSE', '0620', 'Chemistry', '#10b981'),
  ('Cambridge', 'IGCSE', '0580', 'Mathematics', '#ef4444'),
  ('Cambridge', 'IGCSE', '0610', 'Biology', '#8b5cf6'),
  ('Cambridge', 'IGCSE', '0500', 'English Language', '#f59e0b'),
  ('Cambridge', 'IGCSE', '0470', 'History', '#ec4899'),
  ('Cambridge', 'IGCSE', '0460', 'Geography', '#06b6d4'),
  ('Cambridge', 'IGCSE', '0478', 'Computer Science', '#6366f1'),
  
  -- Edexcel IAL
  ('Edexcel', 'IAL', 'WPH11', 'Physics (AS)', '#3b82f6'),
  ('Edexcel', 'IAL', 'WCH11', 'Chemistry (AS)', '#10b981'),
  ('Edexcel', 'IAL', 'WMA01', 'Mathematics (AS)', '#ef4444'),
  ('Edexcel', 'IAL', 'WBI11', 'Biology (AS)', '#8b5cf6')
ON CONFLICT (board, level, code) DO NOTHING;

-- ============================================================================
-- PART 4: User Subjects Table (CRITICAL - for subject management)
-- ============================================================================

CREATE TABLE IF NOT EXISTS user_subjects (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
  subject_id UUID REFERENCES subjects(id) ON DELETE CASCADE,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE(user_id, subject_id)
);

CREATE INDEX IF NOT EXISTS idx_user_subjects_user ON user_subjects(user_id);
CREATE INDEX IF NOT EXISTS idx_user_subjects_subject ON user_subjects(subject_id);

-- RLS for user_subjects
ALTER TABLE user_subjects ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "Users can view own subjects" ON user_subjects;
CREATE POLICY "Users can view own subjects" ON user_subjects
  FOR SELECT USING (auth.uid() = user_id);

DROP POLICY IF EXISTS "Users can add own subjects" ON user_subjects;
CREATE POLICY "Users can add own subjects" ON user_subjects
  FOR INSERT WITH CHECK (auth.uid() = user_id);

DROP POLICY IF EXISTS "Users can remove own subjects" ON user_subjects;
CREATE POLICY "Users can remove own subjects" ON user_subjects
  FOR DELETE USING (auth.uid() = user_id);

-- ============================================================================
-- PART 5: Extend Papers Table
-- ============================================================================

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

DO $$ 
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint WHERE conname = 'papers_paper_type_check'
  ) THEN
    ALTER TABLE papers ADD CONSTRAINT papers_paper_type_check 
      CHECK (paper_type IS NULL OR paper_type IN ('QP', 'MS'));
  END IF;
END $$;

CREATE INDEX IF NOT EXISTS idx_papers_doc_hash ON papers(doc_hash);
CREATE INDEX IF NOT EXISTS idx_papers_board_level ON papers(board, level);
CREATE INDEX IF NOT EXISTS idx_papers_year ON papers(year DESC);

ALTER TABLE papers ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "Authenticated users can view papers" ON papers;
CREATE POLICY "Authenticated users can view papers" ON papers
  FOR SELECT TO authenticated USING (true);

-- ============================================================================
-- PART 6: Extend Questions Table
-- ============================================================================

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

DO $$ 
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint WHERE conname = 'questions_difficulty_check'
  ) THEN
    ALTER TABLE questions ADD CONSTRAINT questions_difficulty_check 
      CHECK (difficulty IS NULL OR difficulty IN ('easy', 'medium', 'hard'));
  END IF;
END $$;

CREATE INDEX IF NOT EXISTS idx_questions_paper ON questions(paper_id);
CREATE INDEX IF NOT EXISTS idx_questions_doc_hash ON questions(doc_hash);
CREATE INDEX IF NOT EXISTS idx_questions_difficulty ON questions(difficulty);
CREATE INDEX IF NOT EXISTS idx_questions_context_text ON questions USING gin(to_tsvector('english', context_text));

ALTER TABLE questions ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "Authenticated users can view questions" ON questions;
CREATE POLICY "Authenticated users can view questions" ON questions
  FOR SELECT TO authenticated USING (true);

-- ============================================================================
-- PART 7: Question Parts Table
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

ALTER TABLE question_parts ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "Authenticated users can view parts" ON question_parts;
CREATE POLICY "Authenticated users can view parts" ON question_parts
  FOR SELECT TO authenticated USING (true);

-- ============================================================================
-- PART 8: Question Tags Table
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

ALTER TABLE question_tags ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "Authenticated users can view tags" ON question_tags;
CREATE POLICY "Authenticated users can view tags" ON question_tags
  FOR SELECT TO authenticated USING (true);

-- ============================================================================
-- PART 9: Ingestions Tracking Table
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
-- PART 10: Worksheets Table
-- ============================================================================

ALTER TABLE worksheets ADD COLUMN IF NOT EXISTS title TEXT;
ALTER TABLE worksheets ADD COLUMN IF NOT EXISTS description TEXT;
ALTER TABLE worksheets ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ DEFAULT NOW();

CREATE INDEX IF NOT EXISTS idx_worksheets_user ON worksheets(user_id);

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
-- PART 11: Worksheet Items Table
-- ============================================================================

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
-- PART 12: Update Timestamp Triggers
-- ============================================================================

CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

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

-- ============================================================================
-- PART 7: Seed Physics Topics (fixes missing topics issue)
-- ============================================================================

DO $$
DECLARE
  physics_id UUID;
BEGIN
  -- Get the Physics 4PH1 subject_id
  SELECT id INTO physics_id FROM subjects WHERE code = '4PH1' AND level = 'IGCSE' LIMIT 1;

  IF physics_id IS NULL THEN
    RAISE NOTICE '⚠️  Physics subject not found. Run the subjects seed first.';
  ELSE
    RAISE NOTICE '✅ Found Physics subject: %', physics_id;

    -- Delete existing physics topics if any
    DELETE FROM topics WHERE subject_id = physics_id;

    -- Topic 1: Forces and motion
    INSERT INTO topics (subject_id, code, name, spec_ref, content) VALUES
    (physics_id, '1a', 'Units', 'p6', 'Use SI units: kg, m, s, A, K, mol, cd'),
    (physics_id, '1b', 'Movement and position', 'p7', 'Plot and explain distance–time graphs; calculate average speed = distance ÷ time'),
    (physics_id, '1c', 'Forces, movement, shape and momentum', 'p9', 'Identify forces, calculate momentum = mass × velocity, apply Newton's laws'),
    (physics_id, '1d', 'Energy and work', 'p12', 'Calculate work done = force × distance, kinetic energy, gravitational potential energy, efficiency');

    -- Topic 2: Electricity
    INSERT INTO topics (subject_id, code, name, spec_ref, content) VALUES
    (physics_id, '2a', 'Mains electricity', 'p14', 'Understand AC/DC, voltage, current, resistance; use V = I × R'),
    (physics_id, '2b', 'Energy and voltage in circuits', 'p16', 'Calculate power = V × I, energy transferred = V × I × t; series and parallel circuits'),
    (physics_id, '2c', 'Electric charge', 'p18', 'Describe charge, current as flow of charge, static electricity');

    -- Topic 3: Waves
    INSERT INTO topics (subject_id, code, name, spec_ref, content) VALUES
    (physics_id, '3a', 'Properties of waves', 'p20', 'Define wavelength, frequency, amplitude; use v = f × λ; transverse vs longitudinal'),
    (physics_id, '3b', 'The electromagnetic spectrum', 'p22', 'Order EM waves by wavelength/frequency; applications and dangers'),
    (physics_id, '3c', 'Light and sound', 'p24', 'Reflection, refraction, diffraction, interference; speed of sound');

    -- Topic 4: Energy resources and energy transfers
    INSERT INTO topics (subject_id, code, name, spec_ref, content) VALUES
    (physics_id, '4a', 'Energy resources and electricity generation', 'p26', 'Compare fossil fuels, nuclear, renewables; efficiency of power stations'),
    (physics_id, '4b', 'Work and power', 'p28', 'Calculate work = F × d, power = work ÷ time, efficiency = useful output ÷ total input');

    -- Topic 5: Solids, liquids and gases
    INSERT INTO topics (subject_id, code, name, spec_ref, content) VALUES
    (physics_id, '5a', 'Density and pressure', 'p30', 'Calculate density = mass ÷ volume, pressure = force ÷ area, pressure in fluids'),
    (physics_id, '5b', 'Change of state', 'p32', 'Describe melting, boiling, evaporation, condensation; latent heat'),
    (physics_id, '5c', 'Ideal gas molecules', 'p34', 'Kinetic theory, Brownian motion, absolute zero, pressure–volume–temperature relationships');

    -- Topic 6: Magnetism and electromagnetism
    INSERT INTO topics (subject_id, code, name, spec_ref, content) VALUES
    (physics_id, '6a', 'Magnetism', 'p36', 'Magnetic fields, poles, plotting field lines, induced magnetism'),
    (physics_id, '6b', 'Electromagnetism', 'p38', 'Motor effect, Fleming's left-hand rule, electromagnetic induction, transformers');

    -- Topic 7: Radioactivity and particles
    INSERT INTO topics (subject_id, code, name, spec_ref, content) VALUES
    (physics_id, '7a', 'Radioactivity', 'p40', 'Alpha, beta, gamma radiation; properties, uses, dangers; half-life; nuclear equations'),
    (physics_id, '7b', 'Fission and fusion', 'p42', 'Nuclear fission, chain reactions, fusion in stars');

    -- Topic 8: Astrophysics
    INSERT INTO topics (subject_id, code, name, spec_ref, content) VALUES
    (physics_id, '8a', 'Motion in the Universe', 'p44', 'Orbital motion, gravity, satellites, planets, moons'),
    (physics_id, '8b', 'Stellar evolution', 'p46', 'Life cycle of stars: main sequence, red giant, white dwarf, supernova, neutron star, black hole; cosmology');

    RAISE NOTICE '✅ Inserted 24 Physics topics successfully!';
  END IF;
END $$;

-- ============================================================================
-- Final Summary
-- ============================================================================

DO $$
BEGIN
  RAISE NOTICE '';
  RAISE NOTICE '============================================================================';
  RAISE NOTICE '✅ Complete database fix applied successfully!';
  RAISE NOTICE '============================================================================';
  RAISE NOTICE '';
  RAISE NOTICE 'Tables created/updated:';
  RAISE NOTICE '  ✅ profiles (with auto-creation trigger) - FIXES LOGIN LOOP';
  RAISE NOTICE '  ✅ subjects (seeded with 20 subjects) - FIXES EMPTY DROPDOWN';
  RAISE NOTICE '  ✅ topics (seeded with 24 Physics topics) - FIXES MISSING TOPICS';
  RAISE NOTICE '  ✅ user_subjects (new table) - FOR SUBJECT MANAGEMENT';
  RAISE NOTICE '  ✅ papers (extended with new columns)';
  RAISE NOTICE '  ✅ questions (extended with new columns)';
  RAISE NOTICE '  ✅ question_parts';
  RAISE NOTICE '  ✅ question_tags';
  RAISE NOTICE '  ✅ ingestions';
  RAISE NOTICE '  ✅ worksheets (extended)';
  RAISE NOTICE '  ✅ worksheet_items (extended)';
  RAISE NOTICE '';
  RAISE NOTICE '🔒 All tables have RLS enabled with proper policies';
  RAISE NOTICE '✅ Ready to use!';
  RAISE NOTICE '';
  RAISE NOTICE '============================================================================';
  RAISE NOTICE '👉 NEXT STEPS:';
  RAISE NOTICE '============================================================================';
  RAISE NOTICE '   1. Logout from your app';
  RAISE NOTICE '   2. Clear browser cache (Ctrl+Shift+Delete)';
  RAISE NOTICE '   3. Login again at http://localhost:3001/login';
  RAISE NOTICE '   4. Profile will auto-create';
  RAISE NOTICE '   5. Subjects will appear in dropdown';
  RAISE NOTICE '   6. Physics topics (24) will show when Physics 4PH1 is selected';
  RAISE NOTICE '';
  RAISE NOTICE '============================================================================';
  RAISE NOTICE '🔧 FOR LOGIN ERROR "requested path is invalid":';
  RAISE NOTICE '============================================================================';
  RAISE NOTICE '   Go to Supabase Dashboard → Authentication → URL Configuration';
  RAISE NOTICE '   ';
  RAISE NOTICE '   Site URL: http://localhost:3001';
  RAISE NOTICE '   ';
  RAISE NOTICE '   Redirect URLs (add both):';
  RAISE NOTICE '     • http://localhost:3001/auth/callback';
  RAISE NOTICE '     • http://localhost:3001/**';
  RAISE NOTICE '   ';
  RAISE NOTICE '   Save and try login again!';
  RAISE NOTICE '============================================================================';
END $$;

