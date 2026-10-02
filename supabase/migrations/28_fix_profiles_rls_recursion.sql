-- =============================================================================
-- 28: Fix infinite recursion in the profiles RLS policies
-- =============================================================================
-- "Admins can view all profiles" and "Admins can update any profile" looked up
-- the caller's role with a subquery on profiles itself. Evaluating that
-- subquery re-applies the same policies, so every non-service-role read of
-- profiles failed with "infinite recursion detected in policy for relation
-- profiles". Signed-in users could not read even their own row, and every
-- admin other than the super admin (who is matched by email) was treated as a
-- student and bounced out of /admin.
--
-- The role check moves into a SECURITY DEFINER function, which reads profiles
-- as its owner and so bypasses RLS instead of re-entering it.
-- =============================================================================

CREATE OR REPLACE FUNCTION public.is_admin()
RETURNS boolean
LANGUAGE sql
STABLE
SECURITY DEFINER
SET search_path = public
AS $$
  SELECT EXISTS (
    SELECT 1 FROM public.profiles
    WHERE id = auth.uid() AND role = 'admin'
  );
$$;

REVOKE ALL ON FUNCTION public.is_admin() FROM public;
GRANT EXECUTE ON FUNCTION public.is_admin() TO anon, authenticated;

DROP POLICY IF EXISTS "Admins can view all profiles" ON public.profiles;
CREATE POLICY "Admins can view all profiles" ON public.profiles
  FOR SELECT USING (auth.uid() = id OR public.is_admin());

DROP POLICY IF EXISTS "Admins can update any profile" ON public.profiles;
CREATE POLICY "Admins can update any profile" ON public.profiles
  FOR UPDATE USING (public.is_admin());
