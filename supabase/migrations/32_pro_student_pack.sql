-- =============================================================================
-- 32: Pro Student Pack
-- =============================================================================
-- Normal students may put at most 30 questions in one worksheet or test.
-- Admins, teachers and students holding an active Pro Student Pack have no
-- limit. An admin grants the pack from /admin/users; it runs for 30 days and
-- ends by itself when pro_until passes. NULL means the student never had one.
-- =============================================================================

ALTER TABLE public.profiles ADD COLUMN IF NOT EXISTS pro_until timestamptz;

-- "Users can update own profile" lets a signed-in user write every column of
-- their row, so the guard from migration 29 now covers pro_until as well as
-- role: only the service role, or SQL run without a JWT, may set either.
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
      NEW.pro_until := NULL;
    ELSIF NEW.role IS DISTINCT FROM OLD.role THEN
      RAISE EXCEPTION 'profiles.role can only be changed by an administrator'
        USING ERRCODE = '42501';
    ELSIF NEW.pro_until IS DISTINCT FROM OLD.pro_until THEN
      RAISE EXCEPTION 'profiles.pro_until can only be changed by an administrator'
        USING ERRCODE = '42501';
    END IF;
  END IF;
  RETURN NEW;
END;
$$;
