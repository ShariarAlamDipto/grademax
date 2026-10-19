-- =============================================================================
-- 29: Close the write holes found in the 2026-10-02 RLS audit
-- =============================================================================
-- Read from pg_policies / grants on production. The app's own writes go through
-- server routes using the service role, which bypasses RLS, so tightening the
-- anon/authenticated paths below does not affect them. The one browser-side
-- write is a user saving their own profile (name, level, goal), which stays.
-- =============================================================================

-- ── 1. profiles.role cannot be set by the user ──────────────────────────────
-- Migration 11's guard trigger never reached production, and "Users can update
-- own profile" lets a signed-in user write every column of their row,
-- including role. Only the service role, or SQL run from the dashboard (no JWT),
-- may set or change it.
CREATE OR REPLACE FUNCTION public.guard_profile_role_change()
RETURNS trigger
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
BEGIN
  IF coalesce(auth.role(), '') IN ('anon', 'authenticated') THEN
    IF TG_OP = 'INSERT' THEN
      NEW.role := 'student';
    ELSIF NEW.role IS DISTINCT FROM OLD.role THEN
      RAISE EXCEPTION 'profiles.role can only be changed by an administrator'
        USING ERRCODE = '42501';
    END IF;
  END IF;
  RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trg_guard_profile_role_change ON public.profiles;
CREATE TRIGGER trg_guard_profile_role_change
  BEFORE INSERT OR UPDATE ON public.profiles
  FOR EACH ROW EXECUTE FUNCTION public.guard_profile_role_change();

DROP POLICY IF EXISTS "Users can update own profile" ON public.profiles;
CREATE POLICY "Users can update own profile" ON public.profiles
  FOR UPDATE USING (auth.uid() = id) WITH CHECK (auth.uid() = id);

-- ── 2. tests / test_items: drop the "Public" policies ───────────────────────
-- They let anyone, signed in or not, read, edit and delete every user's tests.
-- The owner-scoped policies that sit alongside them stay.
DROP POLICY IF EXISTS "Public read tests"   ON public.tests;
DROP POLICY IF EXISTS "Public insert tests" ON public.tests;
DROP POLICY IF EXISTS "Public update tests" ON public.tests;
DROP POLICY IF EXISTS "Public delete tests" ON public.tests;
DROP POLICY IF EXISTS "Public read test_items"   ON public.test_items;
DROP POLICY IF EXISTS "Public insert test_items" ON public.test_items;
DROP POLICY IF EXISTS "Public update test_items" ON public.test_items;
DROP POLICY IF EXISTS "Public delete test_items" ON public.test_items;

-- ── 3. markschemes: remove the leftover dev policy ──────────────────────────
DROP POLICY IF EXISTS "dev_all" ON public.markschemes;
DROP POLICY IF EXISTS "Public read markschemes" ON public.markschemes;
CREATE POLICY "Public read markschemes" ON public.markschemes FOR SELECT USING (true);

-- ── 4. Tables with RLS switched off ─────────────────────────────────────────
-- With RLS off, the anon key has full read/write. No policies are added, so
-- only the service role can reach them.
ALTER TABLE public.paper_pages ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.ingestion_manifests ENABLE ROW LEVEL SECURITY;

-- ── 5. ingestions: pipeline-only ────────────────────────────────────────────
DROP POLICY IF EXISTS "Authenticated users can insert ingestions" ON public.ingestions;
DROP POLICY IF EXISTS "Authenticated users can update ingestions" ON public.ingestions;

-- ── 6. Storage: anonymous upload into any bucket ────────────────────────────
-- "Allow uploads 1h83zns_0" lets anyone put files in the public buckets, which
-- are then served from your Supabase domain. Lecture uploads go through
-- presigned R2 URLs now, and teachers keep their own insert policy.
DROP POLICY IF EXISTS "Allow uploads 1h83zns_0" ON storage.objects;

-- ── 7. SECURITY DEFINER functions callable by anyone ────────────────────────
-- These run as their owner and bypass RLS, and each takes a user id or writes
-- a log. None is called from the app with the anon key; the server routes use
-- the service role, which keeps EXECUTE.
REVOKE EXECUTE ON FUNCTION public.increment_usage_meter(uuid, integer, integer, integer) FROM public, anon, authenticated;
REVOKE EXECUTE ON FUNCTION public.create_audit_log_entry(text, text, uuid, text, uuid, text, text, text, jsonb, text) FROM public, anon, authenticated;
REVOKE EXECUTE ON FUNCTION public.cleanup_expired_sessions() FROM public, anon, authenticated;
REVOKE EXECUTE ON FUNCTION public.get_current_month_usage(uuid) FROM public, anon, authenticated;
REVOKE EXECUTE ON FUNCTION public.get_remaining_worksheet_quota(uuid) FROM public, anon, authenticated;
REVOKE EXECUTE ON FUNCTION public.check_worksheet_permission(uuid) FROM public, anon, authenticated;
REVOKE EXECUTE ON FUNCTION public.get_active_sessions_count(uuid) FROM public, anon, authenticated;
REVOKE EXECUTE ON FUNCTION public.handle_new_user() FROM public, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.increment_usage_meter(uuid, integer, integer, integer) TO service_role;
GRANT EXECUTE ON FUNCTION public.create_audit_log_entry(text, text, uuid, text, uuid, text, text, text, jsonb, text) TO service_role;
GRANT EXECUTE ON FUNCTION public.cleanup_expired_sessions() TO service_role;
GRANT EXECUTE ON FUNCTION public.get_current_month_usage(uuid) TO service_role;
GRANT EXECUTE ON FUNCTION public.get_remaining_worksheet_quota(uuid) TO service_role;
GRANT EXECUTE ON FUNCTION public.check_worksheet_permission(uuid) TO service_role;
GRANT EXECUTE ON FUNCTION public.get_active_sessions_count(uuid) TO service_role;
