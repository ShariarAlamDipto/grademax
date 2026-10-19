-- Migration 11: Security hardening
-- =============================================================================
-- Brings the previously-untracked security fixes into version control so a
-- rebuild can never silently reintroduce them. Everything here is idempotent
-- and safe to run repeatedly.
--
-- Fixes:
--   1. profiles.role privilege self-escalation (a signed-in student could
--      PATCH their own row to role='admin' via the anon PostgREST API — which
--      defeats requireAdmin/requireTeacher, since those trust profiles.role).
--   2. markschemes anon write (an over-permissive USING(true) WITH CHECK(true)
--      "dev_all" policy let anyone insert/update/delete answer keys).
--   3. suggestions / usage_events: confirm RLS is on and locked to the service
--      role (the app writes them with the service key, never the anon key).
-- =============================================================================

-- ── 1. Block role self-escalation on profiles ────────────────────────────────
-- A trigger is used (not just a policy) so the guard holds regardless of which
-- RLS policies exist on the table now or later. The service role (used only by
-- server-side admin APIs) is exempt, so legitimate role changes still work.
CREATE OR REPLACE FUNCTION public.guard_profile_role_change()
RETURNS trigger
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
BEGIN
  IF NEW.role IS DISTINCT FROM OLD.role THEN
    -- auth.role() is 'service_role' for the service key, 'authenticated' for a
    -- logged-in user, 'anon' for the anon key. Block the PostgREST user paths
    -- (this is what closes the self-escalation hole). The service role and
    -- privileged DB roles (SQL editor / migrations) are allowed through.
    IF coalesce(auth.role(), '') IN ('authenticated', 'anon') THEN
      RAISE EXCEPTION 'Changing profiles.role is not permitted'
        USING ERRCODE = 'insufficient_privilege';
    END IF;
  END IF;
  RETURN NEW;
END;
$$;

DO $$
BEGIN
  IF to_regclass('public.profiles') IS NOT NULL THEN
    EXECUTE 'DROP TRIGGER IF EXISTS trg_guard_profile_role_change ON public.profiles';
    EXECUTE 'CREATE TRIGGER trg_guard_profile_role_change BEFORE UPDATE ON public.profiles FOR EACH ROW EXECUTE FUNCTION public.guard_profile_role_change()';
    -- Also tighten the RLS policy so a user can update their own profile but the
    -- WITH CHECK re-asserts identity. (Defense in depth alongside the trigger.)
    EXECUTE 'ALTER TABLE public.profiles ENABLE ROW LEVEL SECURITY';
    EXECUTE 'DROP POLICY IF EXISTS "Users can update own profile" ON public.profiles';
    EXECUTE 'CREATE POLICY "Users can update own profile" ON public.profiles FOR UPDATE USING (auth.uid() = id) WITH CHECK (auth.uid() = id)';
  END IF;
END $$;

-- ── 2. Lock down markschemes writes ──────────────────────────────────────────
-- Drop any permissive dev policy and enforce: public may read, only the service
-- role may write. (Answer keys must never be anon-writable.) Guarded so the
-- migration is a no-op if the table doesn't exist in this environment.
DO $$
BEGIN
  IF to_regclass('public.markschemes') IS NOT NULL THEN
    EXECUTE 'ALTER TABLE public.markschemes ENABLE ROW LEVEL SECURITY';
    EXECUTE 'DROP POLICY IF EXISTS "dev_all" ON public.markschemes';
    EXECUTE 'DROP POLICY IF EXISTS "Public read markschemes" ON public.markschemes';
    EXECUTE 'DROP POLICY IF EXISTS "Service role write markschemes" ON public.markschemes';
    EXECUTE 'CREATE POLICY "Public read markschemes" ON public.markschemes FOR SELECT USING (true)';
    EXECUTE 'CREATE POLICY "Service role write markschemes" ON public.markschemes FOR ALL USING (auth.role() = ''service_role'') WITH CHECK (auth.role() = ''service_role'')';
  END IF;
END $$;

-- ── 3. suggestions + usage_events: service-role only ─────────────────────────
-- These are written server-side with the service key. RLS "USING(false)" blocks
-- all anon/authenticated access; the service role bypasses RLS entirely, so the
-- app keeps working while the anon PostgREST surface is closed.
DO $$
DECLARE
  tbl text;
BEGIN
  FOREACH tbl IN ARRAY ARRAY['suggestions', 'usage_events'] LOOP
    IF to_regclass('public.' || tbl) IS NOT NULL THEN
      EXECUTE format('ALTER TABLE public.%I ENABLE ROW LEVEL SECURITY', tbl);
      EXECUTE format('DROP POLICY IF EXISTS "Service role only" ON public.%I', tbl);
      EXECUTE format('CREATE POLICY "Service role only" ON public.%I FOR ALL USING (false) WITH CHECK (false)', tbl);
    END IF;
  END LOOP;
END $$;
