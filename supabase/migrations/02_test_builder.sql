-- ============================================================================
-- TEST BUILDER SCHEMA
-- New tables for the test-builder feature (does NOT modify existing tables)
-- ============================================================================

-- Tests (user-assembled custom tests)
CREATE TABLE IF NOT EXISTS tests (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  
  -- Owner
  user_id UUID,  -- nullable for anonymous usage
  
  -- Test metadata
  title TEXT NOT NULL DEFAULT 'Untitled Test',
  subject_id UUID NOT NULL REFERENCES subjects(id),
  
  -- Aggregates (cached for display)
  total_marks INTEGER DEFAULT 0,
  total_questions INTEGER DEFAULT 0,
  
  -- Generated PDFs
  question_paper_url TEXT,
  mark_scheme_url TEXT,
  
  -- Status
  status TEXT DEFAULT 'draft' CHECK (status IN ('draft', 'finalized')),
  
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Test Items (individual questions selected into a test)
CREATE TABLE IF NOT EXISTS test_items (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  test_id UUID NOT NULL REFERENCES tests(id) ON DELETE CASCADE,
  page_id UUID NOT NULL REFERENCES pages(id) ON DELETE CASCADE,
  
  sequence_order INTEGER NOT NULL,  -- position in the test (1, 2, 3...)
  
  created_at TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE(test_id, page_id)
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_tests_user ON tests(user_id);
CREATE INDEX IF NOT EXISTS idx_tests_subject ON tests(subject_id);
CREATE INDEX IF NOT EXISTS idx_tests_status ON tests(status);
CREATE INDEX IF NOT EXISTS idx_test_items_test ON test_items(test_id);
CREATE INDEX IF NOT EXISTS idx_test_items_page ON test_items(page_id);
CREATE INDEX IF NOT EXISTS idx_test_items_sequence ON test_items(test_id, sequence_order);

-- RLS
ALTER TABLE tests ENABLE ROW LEVEL SECURITY;
ALTER TABLE test_items ENABLE ROW LEVEL SECURITY;

-- Public read/write for now (same pattern as worksheets)
CREATE POLICY "Public read tests" ON tests FOR SELECT USING (true);
CREATE POLICY "Public insert tests" ON tests FOR INSERT WITH CHECK (true);
CREATE POLICY "Public update tests" ON tests FOR UPDATE USING (true);
CREATE POLICY "Public delete tests" ON tests FOR DELETE USING (true);

CREATE POLICY "Public read test_items" ON test_items FOR SELECT USING (true);
CREATE POLICY "Public insert test_items" ON test_items FOR INSERT WITH CHECK (true);
CREATE POLICY "Public update test_items" ON test_items FOR UPDATE USING (true);
CREATE POLICY "Public delete test_items" ON test_items FOR DELETE USING (true);
