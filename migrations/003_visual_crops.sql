-- Migration: Add visual crop fields to questions table
-- Run with: psql or Supabase SQL Editor

-- Add visual crop columns
ALTER TABLE questions 
ADD COLUMN IF NOT EXISTS visual_url TEXT,
ADD COLUMN IF NOT EXISTS visual_dims JSONB,
ADD COLUMN IF NOT EXISTS visual_hash TEXT,
ADD COLUMN IF NOT EXISTS bbox JSONB;

-- Create index for deduplication
CREATE INDEX IF NOT EXISTS idx_questions_visual_hash 
  ON questions(visual_hash) 
  WHERE visual_hash IS NOT NULL;

-- Create table for storing full page renders
CREATE TABLE IF NOT EXISTS paper_pages (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  paper_id UUID REFERENCES papers(id) ON DELETE CASCADE,
  page_number INT NOT NULL,
  visual_url TEXT NOT NULL,
  width INT,
  height INT,
  dpi INT DEFAULT 300,
  file_size_kb INT,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE(paper_id, page_number)
);

CREATE INDEX IF NOT EXISTS idx_paper_pages_paper_id 
  ON paper_pages(paper_id);

-- Add comments
COMMENT ON COLUMN questions.visual_url IS 'Supabase Storage URL for question crop PNG';
COMMENT ON COLUMN questions.visual_dims IS 'JSON: {width: int, height: int, dpi: int}';
COMMENT ON COLUMN questions.visual_hash IS 'SHA256 hash of PNG for deduplication';
COMMENT ON COLUMN questions.bbox IS 'JSON: {page: int, x: float, y: float, width: float, height: float}';

COMMENT ON TABLE paper_pages IS 'Full page renders for visual crop extraction';
