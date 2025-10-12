-- ============================================================================
-- CLEAN DATABASE SCHEMA FOR GRADEMAX
-- Optimized for: Topic-based worksheet generation with year filtering
-- ============================================================================

-- Drop existing tables if they exist
DROP TABLE IF EXISTS worksheet_items CASCADE;
DROP TABLE IF EXISTS worksheets CASCADE;
DROP TABLE IF EXISTS question_topics CASCADE;
DROP TABLE IF EXISTS questions CASCADE;
DROP TABLE IF EXISTS pages CASCADE;
DROP TABLE IF EXISTS papers CASCADE;
DROP TABLE IF EXISTS topics CASCADE;
DROP TABLE IF EXISTS subjects CASCADE;

-- ============================================================================
-- SUBJECTS
-- ============================================================================
CREATE TABLE subjects (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  code TEXT NOT NULL UNIQUE,           -- e.g., "4PH1"
  name TEXT NOT NULL,                   -- e.g., "Physics"
  board TEXT NOT NULL,                  -- e.g., "IGCSE"
  level TEXT NOT NULL,                  -- e.g., "IGCSE"
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================================
-- TOPICS
-- ============================================================================
CREATE TABLE topics (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  subject_id UUID NOT NULL REFERENCES subjects(id) ON DELETE CASCADE,
  code TEXT NOT NULL,                   -- "1", "2", "3", etc.
  name TEXT NOT NULL,                   -- "Forces and motion"
  description TEXT,
  keywords TEXT[],                      -- ["force", "acceleration", "velocity"]
  formulas TEXT[],                      -- ["F = ma", "v = u + at"]
  created_at TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE(subject_id, code)
);

-- ============================================================================
-- PAPERS
-- ============================================================================
CREATE TABLE papers (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  subject_id UUID NOT NULL REFERENCES subjects(id) ON DELETE CASCADE,
  year INTEGER NOT NULL,                -- 2019
  season TEXT NOT NULL,                 -- "Jun", "Oct", "Jan"
  paper_number TEXT NOT NULL,           -- "1P", "2P", "3P"
  qp_source_path TEXT,                  -- Original file path
  ms_source_path TEXT,                  -- Original MS file path
  total_pages INTEGER,
  processed_at TIMESTAMPTZ DEFAULT NOW(),
  created_at TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE(subject_id, year, season, paper_number)
);

CREATE INDEX idx_papers_year ON papers(year);
CREATE INDEX idx_papers_subject ON papers(subject_id);

-- ============================================================================
-- PAGES (Core table for worksheet generation)
-- ============================================================================
CREATE TABLE pages (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  paper_id UUID NOT NULL REFERENCES papers(id) ON DELETE CASCADE,
  
  -- Page identification
  page_number INTEGER NOT NULL,         -- Sequential page in paper
  question_number TEXT,                 -- "1", "2a", "3", etc.
  is_question BOOLEAN DEFAULT TRUE,     -- Is this a question page?
  
  -- Topic classification (ARRAY - supports multiple topics per page)
  topics TEXT[] NOT NULL DEFAULT '{}',  -- ["1", "2"] - topic codes
  
  -- Difficulty & confidence
  difficulty TEXT,                      -- "easy", "medium", "hard"
  confidence FLOAT,                     -- 0.0 to 1.0 (LLM confidence)
  
  -- Storage URLs (Supabase Storage)
  qp_page_url TEXT,                     -- subjects/Physics/pages/2019_Jun_1P/q1.pdf
  ms_page_url TEXT,                     -- subjects/Physics/pages/2019_Jun_1P/q1_ms.pdf
  
  -- Metadata
  has_diagram BOOLEAN DEFAULT FALSE,
  page_count INTEGER DEFAULT 1,         -- Multi-page questions
  text_excerpt TEXT,                    -- First 500 chars for search
  
  created_at TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE(paper_id, page_number)
);

-- Critical indexes for fast queries
CREATE INDEX idx_pages_topics ON pages USING GIN(topics);  -- Array overlap queries
CREATE INDEX idx_pages_paper ON pages(paper_id);
CREATE INDEX idx_pages_difficulty ON pages(difficulty);
CREATE INDEX idx_pages_question ON pages(question_number);

-- ============================================================================
-- WORKSHEETS (Generated worksheets)
-- ============================================================================
CREATE TABLE worksheets (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  
  -- Filters used
  subject_id UUID NOT NULL REFERENCES subjects(id),
  topics TEXT[] NOT NULL,               -- ["1", "3", "5"]
  year_start INTEGER,
  year_end INTEGER,
  difficulty TEXT,                      -- NULL = all difficulties
  
  -- Generated files
  worksheet_url TEXT,                   -- generated/worksheets/uuid_worksheet.pdf
  markscheme_url TEXT,                  -- generated/worksheets/uuid_markscheme.pdf
  
  -- Metadata
  total_questions INTEGER,
  total_pages INTEGER,
  generated_at TIMESTAMPTZ DEFAULT NOW(),
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================================
-- WORKSHEET_ITEMS (Questions in each worksheet)
-- ============================================================================
CREATE TABLE worksheet_items (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  worksheet_id UUID NOT NULL REFERENCES worksheets(id) ON DELETE CASCADE,
  page_id UUID NOT NULL REFERENCES pages(id) ON DELETE CASCADE,
  sequence INTEGER NOT NULL,            -- Order in worksheet (1, 2, 3...)
  created_at TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE(worksheet_id, page_id)
);

CREATE INDEX idx_worksheet_items_worksheet ON worksheet_items(worksheet_id);
CREATE INDEX idx_worksheet_items_sequence ON worksheet_items(worksheet_id, sequence);

-- ============================================================================
-- SEED DATA
-- ============================================================================

-- Insert IGCSE Physics subject
INSERT INTO subjects (code, name, board, level) VALUES
  ('4PH1', 'Physics', 'IGCSE', 'IGCSE')
ON CONFLICT (code) DO NOTHING;

-- Insert 8 Physics topics
INSERT INTO topics (subject_id, code, name, description)
SELECT 
  (SELECT id FROM subjects WHERE code = '4PH1'),
  code, name, description
FROM (VALUES
  ('1', 'Forces and motion', 'Newton''s laws, acceleration, velocity, momentum'),
  ('2', 'Electricity', 'Current, voltage, resistance, circuits, power'),
  ('3', 'Waves', 'Sound, light, reflection, refraction, electromagnetic spectrum'),
  ('4', 'Energy resources', 'Renewable energy, non-renewable, efficiency, conservation'),
  ('5', 'Solids, liquids and gases', 'States of matter, pressure, density, kinetic theory'),
  ('6', 'Magnetism and electromagnetism', 'Magnetic fields, motors, generators, transformers'),
  ('7', 'Radioactivity and particles', 'Atoms, isotopes, radiation, half-life, nuclear'),
  ('8', 'Astrophysics', 'Universe, stars, planets, solar system, cosmology')
) AS t(code, name, description)
ON CONFLICT (subject_id, code) DO NOTHING;

-- ============================================================================
-- HELPER FUNCTIONS
-- ============================================================================

-- Function to get pages matching criteria (for worksheet generation)
CREATE OR REPLACE FUNCTION get_worksheet_pages(
  p_subject_code TEXT,
  p_topics TEXT[],
  p_year_start INTEGER DEFAULT NULL,
  p_year_end INTEGER DEFAULT NULL,
  p_difficulty TEXT DEFAULT NULL,
  p_limit INTEGER DEFAULT 50
)
RETURNS TABLE (
  page_id UUID,
  paper_id UUID,
  year INTEGER,
  season TEXT,
  paper_number TEXT,
  question_number TEXT,
  topics TEXT[],
  difficulty TEXT,
  qp_page_url TEXT,
  ms_page_url TEXT,
  has_diagram BOOLEAN
) AS $$
BEGIN
  RETURN QUERY
  SELECT 
    p.id AS page_id,
    p.paper_id,
    pa.year,
    pa.season,
    pa.paper_number,
    p.question_number,
    p.topics,
    p.difficulty,
    p.qp_page_url,
    p.ms_page_url,
    p.has_diagram
  FROM pages p
  JOIN papers pa ON p.paper_id = pa.id
  JOIN subjects s ON pa.subject_id = s.id
  WHERE s.code = p_subject_code
    AND p.topics && p_topics                    -- Array overlap
    AND p.is_question = TRUE
    AND p.qp_page_url IS NOT NULL
    AND (p_year_start IS NULL OR pa.year >= p_year_start)
    AND (p_year_end IS NULL OR pa.year <= p_year_end)
    AND (p_difficulty IS NULL OR p.difficulty = p_difficulty)
  ORDER BY pa.year, pa.season, p.question_number
  LIMIT p_limit;
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- RLS POLICIES (Public read access)
-- ============================================================================

ALTER TABLE subjects ENABLE ROW LEVEL SECURITY;
ALTER TABLE topics ENABLE ROW LEVEL SECURITY;
ALTER TABLE papers ENABLE ROW LEVEL SECURITY;
ALTER TABLE pages ENABLE ROW LEVEL SECURITY;
ALTER TABLE worksheets ENABLE ROW LEVEL SECURITY;
ALTER TABLE worksheet_items ENABLE ROW LEVEL SECURITY;

-- Allow anonymous read access
CREATE POLICY "Public read subjects" ON subjects FOR SELECT USING (true);
CREATE POLICY "Public read topics" ON topics FOR SELECT USING (true);
CREATE POLICY "Public read papers" ON papers FOR SELECT USING (true);
CREATE POLICY "Public read pages" ON pages FOR SELECT USING (true);
CREATE POLICY "Public read worksheets" ON worksheets FOR SELECT USING (true);
CREATE POLICY "Public read worksheet_items" ON worksheet_items FOR SELECT USING (true);

-- Allow anonymous insert for worksheets (generation)
CREATE POLICY "Public insert worksheets" ON worksheets FOR INSERT WITH CHECK (true);
CREATE POLICY "Public insert worksheet_items" ON worksheet_items FOR INSERT WITH CHECK (true);

-- ============================================================================
-- COMMENTS
-- ============================================================================

COMMENT ON TABLE pages IS 'Core table: Each row = one page (question or answer). Topics stored as array for fast queries.';
COMMENT ON COLUMN pages.topics IS 'Array of topic codes (e.g., ["1", "2"]). Use && operator for overlap queries.';
COMMENT ON COLUMN pages.qp_page_url IS 'Storage path: subjects/Physics/pages/2019_Jun_1P/q1.pdf';
COMMENT ON COLUMN pages.ms_page_url IS 'Storage path: subjects/Physics/pages/2019_Jun_1P/q1_ms.pdf';

COMMENT ON FUNCTION get_worksheet_pages IS 'Query pages for worksheet generation with topic, year, and difficulty filters';
