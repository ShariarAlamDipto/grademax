-- Migration: Add columns for new architecture
-- Run this in Supabase SQL Editor

-- Add new columns to questions table if they don't exist
ALTER TABLE questions 
ADD COLUMN IF NOT EXISTS topic_code TEXT,
ADD COLUMN IF NOT EXISTS ms_pdf_url TEXT,
ADD COLUMN IF NOT EXISTS confidence FLOAT;

-- Create index for fast topic queries
CREATE INDEX IF NOT EXISTS idx_questions_topic_code ON questions(topic_code);

-- Create index for paper lookups
CREATE INDEX IF NOT EXISTS idx_questions_paper_id ON questions(paper_id);

-- Add columns to papers table
ALTER TABLE papers
ADD COLUMN IF NOT EXISTS qp_path TEXT,
ADD COLUMN IF NOT EXISTS ms_path TEXT,
ADD COLUMN IF NOT EXISTS total_questions INTEGER;

-- Comments for documentation
COMMENT ON COLUMN questions.topic_code IS 'Single topic code (1-8) for IGCSE Physics';
COMMENT ON COLUMN questions.ms_pdf_url IS 'Storage path to mark scheme PDF';
COMMENT ON COLUMN questions.confidence IS 'LLM classification confidence (0-1)';
COMMENT ON COLUMN papers.qp_path IS 'Original question paper file path';
COMMENT ON COLUMN papers.ms_path IS 'Original mark scheme file path';
