-- Run this in Supabase SQL Editor
-- 1) Add pdf_url columns to papers table (they don't exist yet)
-- 2) Allow public (anonymous) access to past papers & subjects

-- ============================================================================
-- STEP 1: Add missing columns to papers table
-- ============================================================================
ALTER TABLE papers ADD COLUMN IF NOT EXISTS pdf_url TEXT;
ALTER TABLE papers ADD COLUMN IF NOT EXISTS markscheme_pdf_url TEXT;

-- ============================================================================
-- STEP 2: RLS policies for public access
-- ============================================================================

-- Allow anonymous users to view subjects
DROP POLICY IF EXISTS "Anyone can view subjects" ON subjects;
DROP POLICY IF EXISTS "Public read subjects" ON subjects;
CREATE POLICY "Public read subjects" ON subjects
  FOR SELECT USING (true);

-- Allow anonymous users to view papers
DROP POLICY IF EXISTS "Authenticated users can view papers" ON papers;
DROP POLICY IF EXISTS "Public read papers" ON papers;
CREATE POLICY "Public read papers" ON papers
  FOR SELECT USING (true);

-- Allow service role to manage papers (for upload script)
DROP POLICY IF EXISTS "Service role manages papers" ON papers;
CREATE POLICY "Service role manages papers" ON papers
  FOR ALL TO service_role USING (true) WITH CHECK (true);

-- Allow service role to manage subjects (for upload script)
DROP POLICY IF EXISTS "Service role manages subjects" ON subjects;
CREATE POLICY "Service role manages subjects" ON subjects
  FOR ALL TO service_role USING (true) WITH CHECK (true);

-- Verify
SELECT schemaname, tablename, policyname, permissive, roles, cmd
FROM pg_policies
WHERE tablename IN ('subjects', 'papers')
ORDER BY tablename, policyname;
