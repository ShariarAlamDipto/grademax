-- Migration 004: Core Architecture Redesign for Context-Aware Tagging
-- This migration implements the requirements for:
-- 1. Question-level context (atomic bundles)
-- 2. Fence-based segmentation
-- 3. MS linking with confidence
-- 4. Spec statements and rules
-- 5. Part-level storage with bbox_list

-- ============================================================================
-- PART 1: Extend questions table for question-level context
-- ============================================================================

ALTER TABLE questions ADD COLUMN IF NOT EXISTS header_bbox JSONB;
COMMENT ON COLUMN questions.header_bbox IS 'Bounding box of question stem (before first part)';

ALTER TABLE questions ADD COLUMN IF NOT EXISTS header_visual_url TEXT;
COMMENT ON COLUMN questions.header_visual_url IS 'Storage URL for rendered header/stem region';

ALTER TABLE questions ADD COLUMN IF NOT EXISTS context_text TEXT;
COMMENT ON COLUMN questions.context_text IS 'Full question text: stem + all parts (for tagging)';

ALTER TABLE questions ADD COLUMN IF NOT EXISTS total_marks INT;
COMMENT ON COLUMN questions.total_marks IS 'Total marks for entire question (sum of parts)';

ALTER TABLE questions ADD COLUMN IF NOT EXISTS quality_flags TEXT[];
COMMENT ON COLUMN questions.quality_flags IS 'Quality issues: ocr_used, low_confidence, etc.';

ALTER TABLE questions ADD COLUMN IF NOT EXISTS doc_hash TEXT;
COMMENT ON COLUMN questions.doc_hash IS 'SHA256 of normalized content for dedupe';

CREATE INDEX IF NOT EXISTS idx_questions_doc_hash ON questions(doc_hash);
CREATE INDEX IF NOT EXISTS idx_questions_context_text ON questions USING gin(to_tsvector('english', context_text));

-- ============================================================================
-- PART 2: Create question_parts table (parts are children of questions)
-- ============================================================================

CREATE TABLE IF NOT EXISTS question_parts (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  question_id UUID NOT NULL REFERENCES questions(id) ON DELETE CASCADE,
  code TEXT NOT NULL, -- '(a)', '(b)', '(a)(i)', '(a)(ii)', etc.
  marks INT,
  page_from INT NOT NULL,
  page_to INT NOT NULL,
  bbox_list JSONB NOT NULL, -- Array of {page, x, y, width, height} for multi-page parts
  visual_hash TEXT, -- SHA256 of rendered region for dedupe
  answer_space_lines INT DEFAULT 0,
  ms_link_confidence REAL DEFAULT 0.0, -- [0.0, 1.0] confidence of MS link
  ms_points JSONB, -- Array of markscheme point strings
  ms_snippet TEXT, -- Short MS excerpt for admin QA (not for students)
  features JSONB, -- {command_words: [], formulas: [], has_diagram: boolean, etc.}
  spec_refs TEXT[], -- Inherited from question or refined
  diagram_urls TEXT[], -- URLs of extracted diagram images
  diagram_dims JSONB, -- {width, height} of diagrams
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE(question_id, code)
);

CREATE INDEX idx_question_parts_question_id ON question_parts(question_id);
CREATE INDEX idx_question_parts_visual_hash ON question_parts(visual_hash);
CREATE INDEX idx_question_parts_ms_confidence ON question_parts(ms_link_confidence);

COMMENT ON TABLE question_parts IS 'Individual parts/subparts of questions (children of questions table)';
COMMENT ON COLUMN question_parts.bbox_list IS 'Array of bboxes for this part, can span multiple pages';
COMMENT ON COLUMN question_parts.ms_link_confidence IS 'Confidence [0,1] that markscheme is correctly linked';

-- ============================================================================
-- PART 3: Spec statements and rules (YAML rulepacks)
-- ============================================================================

CREATE TABLE IF NOT EXISTS spec_statements (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  subject_id UUID NOT NULL REFERENCES subjects(id) ON DELETE CASCADE,
  spec_ref TEXT NOT NULL, -- e.g., "P1.2.3", "C2.4.1"
  text TEXT NOT NULL, -- Full spec statement text
  topic_id UUID REFERENCES topics(id),
  keywords TEXT[], -- Extracted keywords for quick matching
  created_at TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE(subject_id, spec_ref)
);

CREATE INDEX idx_spec_statements_subject ON spec_statements(subject_id);
CREATE INDEX idx_spec_statements_topic ON spec_statements(topic_id);
CREATE INDEX idx_spec_statements_ref ON spec_statements(spec_ref);

COMMENT ON TABLE spec_statements IS 'Specification statements from syllabi';

CREATE TABLE IF NOT EXISTS spec_match_rules (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  spec_statement_id UUID NOT NULL REFERENCES spec_statements(id) ON DELETE CASCADE,
  rule_type TEXT NOT NULL CHECK (rule_type IN ('phrase', 'regex', 'formula')),
  pattern TEXT NOT NULL, -- Phrase text, regex pattern, or formula
  weight REAL DEFAULT 1.0, -- Rule confidence weight
  is_active BOOLEAN DEFAULT TRUE,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_spec_match_rules_statement ON spec_match_rules(spec_statement_id);
CREATE INDEX idx_spec_match_rules_type ON spec_match_rules(rule_type) WHERE is_active = true;

COMMENT ON TABLE spec_match_rules IS 'Pattern matching rules for spec statements';

-- ============================================================================
-- PART 4: Topic signals (provenance tracking)
-- ============================================================================

CREATE TABLE IF NOT EXISTS topic_signals (
  question_id UUID NOT NULL REFERENCES questions(id) ON DELETE CASCADE,
  topic_id UUID NOT NULL REFERENCES topics(id) ON DELETE CASCADE,
  s1_sem REAL DEFAULT 0.0, -- Semantic similarity score
  s2_lex REAL DEFAULT 0.0, -- Lexical/phrase match score
  s3_kw REAL DEFAULT 0.0,  -- Keyword boost score
  s4_struct REAL DEFAULT 0.0, -- Structural features score
  final_score REAL NOT NULL, -- Combined score
  source TEXT, -- 'rule_phrase', 'rule_formula', 'ms_cue', 'semantic', etc.
  pipeline_version TEXT DEFAULT '1.0',
  computed_at TIMESTAMPTZ DEFAULT NOW(),
  PRIMARY KEY(question_id, topic_id)
);

CREATE INDEX idx_topic_signals_question ON topic_signals(question_id);
CREATE INDEX idx_topic_signals_topic ON topic_signals(topic_id);
CREATE INDEX idx_topic_signals_score ON topic_signals(final_score DESC);

COMMENT ON TABLE topic_signals IS 'Provenance tracking for topic assignments with sub-scores';

-- ============================================================================
-- PART 5: Part-level topics (optional, inherited from question)
-- ============================================================================

CREATE TABLE IF NOT EXISTS part_topics (
  question_part_id UUID NOT NULL REFERENCES question_parts(id) ON DELETE CASCADE,
  topic_id UUID NOT NULL REFERENCES topics(id) ON DELETE CASCADE,
  confidence REAL NOT NULL,
  inherited_from_question BOOLEAN DEFAULT TRUE,
  PRIMARY KEY(question_part_id, topic_id)
);

CREATE INDEX idx_part_topics_part ON part_topics(question_part_id);
CREATE INDEX idx_part_topics_topic ON part_topics(topic_id);

COMMENT ON TABLE part_topics IS 'Optional part-level topics (usually inherited from question)';

-- ============================================================================
-- PART 6: Extend papers table for metadata and dedupe
-- ============================================================================

ALTER TABLE papers ADD COLUMN IF NOT EXISTS meta JSONB;
COMMENT ON COLUMN papers.meta IS 'Detected metadata: {board, level, paper_type, variant, detected_from}';

ALTER TABLE papers ADD COLUMN IF NOT EXISTS doc_hash TEXT;
COMMENT ON COLUMN papers.doc_hash IS 'SHA256 of normalized text for deduplication';

CREATE INDEX IF NOT EXISTS idx_papers_doc_hash ON papers(doc_hash);

-- ============================================================================
-- PART 7: Ingestion tracking
-- ============================================================================

CREATE TABLE IF NOT EXISTS ingestions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  board TEXT, -- 'Cambridge', 'Edexcel', etc.
  level TEXT, -- 'IGCSE', 'IAL', etc.
  subject_code TEXT,
  year INT,
  season TEXT, -- 'Jun', 'Nov', 'Mar'
  paper_code TEXT, -- '4PH1_1P', '9702_42', etc.
  qp_storage_url TEXT,
  ms_storage_url TEXT,
  status TEXT CHECK (status IN ('pending', 'processing', 'completed', 'failed')),
  error TEXT,
  questions_count INT DEFAULT 0,
  parts_count INT DEFAULT 0,
  processed_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE(subject_code, year, season, paper_code)
);

CREATE INDEX idx_ingestions_status ON ingestions(status);
CREATE INDEX idx_ingestions_subject ON ingestions(subject_code);
CREATE INDEX idx_ingestions_year ON ingestions(year);

COMMENT ON TABLE ingestions IS 'Tracks ingestion runs for monitoring and dedupe';

-- ============================================================================
-- PART 8: Worksheet items for part-level selection
-- ============================================================================

-- Drop old worksheet_items if exists and recreate
DROP TABLE IF EXISTS worksheet_items CASCADE;

CREATE TABLE worksheet_items (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  worksheet_id UUID NOT NULL REFERENCES worksheets(id) ON DELETE CASCADE,
  question_id UUID NOT NULL REFERENCES questions(id),
  part_code TEXT, -- NULL for whole question, or '(a)', '(a)(i)' for specific parts
  sequence_order INT NOT NULL, -- Order in worksheet
  marks INT NOT NULL,
  answer_space_lines INT DEFAULT 0,
  spec_refs TEXT[], -- Inherited from question or part
  ms_points JSONB, -- Markscheme points for teacher PDF
  estimated_seconds INT, -- marks × subject factor
  bbox_cache JSONB, -- Cached bbox_list for faster PDF generation
  created_at TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE(worksheet_id, question_id, part_code)
);

CREATE INDEX idx_worksheet_items_worksheet ON worksheet_items(worksheet_id);
CREATE INDEX idx_worksheet_items_question ON worksheet_items(question_id);
CREATE INDEX idx_worksheet_items_sequence ON worksheet_items(worksheet_id, sequence_order);

COMMENT ON TABLE worksheet_items IS 'Selected questions/parts in a worksheet (supports whole or part selection)';
COMMENT ON COLUMN worksheet_items.part_code IS 'NULL = whole question, otherwise specific part like (a) or (a)(i)';

-- ============================================================================
-- PART 9: Functions for maintenance
-- ============================================================================

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger for question_parts
DROP TRIGGER IF EXISTS update_question_parts_updated_at ON question_parts;
CREATE TRIGGER update_question_parts_updated_at
  BEFORE UPDATE ON question_parts
  FOR EACH ROW
  EXECUTE FUNCTION update_updated_at_column();

-- ============================================================================
-- PART 10: Views for analytics
-- ============================================================================

CREATE OR REPLACE VIEW question_coverage_stats AS
SELECT 
  q.paper_id,
  COUNT(DISTINCT q.id) as total_questions,
  COUNT(DISTINCT qp.id) as total_parts,
  COUNT(DISTINCT qt.topic_id) as unique_topics,
  AVG(ARRAY_LENGTH(q.quality_flags, 1)) as avg_quality_flags,
  AVG(qp.ms_link_confidence) as avg_ms_confidence,
  COUNT(DISTINCT CASE WHEN qp.ms_link_confidence >= 0.8 THEN qp.id END) as high_confidence_parts,
  COUNT(DISTINCT CASE WHEN 'ocr_used' = ANY(q.quality_flags) THEN q.id END) as ocr_questions
FROM questions q
LEFT JOIN question_parts qp ON qp.question_id = q.id
LEFT JOIN question_topics qt ON qt.question_id = q.id
GROUP BY q.paper_id;

COMMENT ON VIEW question_coverage_stats IS 'Analytics for question coverage, MS linking, and quality';

-- ============================================================================
-- PART 11: Grant permissions (adjust based on your RLS setup)
-- ============================================================================

-- These are examples - adjust based on your actual roles
-- GRANT SELECT ON ALL TABLES IN SCHEMA public TO authenticated;
-- GRANT ALL ON ALL TABLES IN SCHEMA public TO service_role;

-- ============================================================================
-- Migration complete
-- ============================================================================

-- Verify tables created
DO $$
BEGIN
  RAISE NOTICE 'Migration 004 complete. Created tables:';
  RAISE NOTICE '- question_parts';
  RAISE NOTICE '- spec_statements';
  RAISE NOTICE '- spec_match_rules';
  RAISE NOTICE '- topic_signals';
  RAISE NOTICE '- part_topics';
  RAISE NOTICE '- ingestions';
  RAISE NOTICE 'Extended: questions, papers, worksheet_items';
END $$;
