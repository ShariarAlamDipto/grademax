-- =============================================================================
-- 30: workbook_questions is server-only
-- =============================================================================
-- Migration 12's "Public read workbook questions" let anyone holding the
-- public anon key (shipped in every page) read every verified row straight
-- from the REST API: chapter, section and the question/mark-scheme PDF links,
-- i.e. the contents of the workbooks sold in the store. Nothing on the site
-- reads this table with the anon key: the Workbook Verification endpoints and
-- every workbook script use the service role, which bypasses RLS and keeps
-- its grants.
--
-- Two layers, so a future permissive policy alone cannot reopen it:
--   1. no policy grants anon/authenticated any row;
--   2. anon/authenticated lose the table privileges themselves.
-- =============================================================================

DROP POLICY IF EXISTS "Public read workbook questions" ON public.workbook_questions;

ALTER TABLE public.workbook_questions ENABLE ROW LEVEL SECURITY;

REVOKE ALL ON TABLE public.workbook_questions FROM anon, authenticated;
GRANT ALL ON TABLE public.workbook_questions TO service_role;
