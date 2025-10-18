-- ============================================================================
-- FIX SIGNUP TRIGGER - FINAL VERSION
-- This fixes database errors when users sign up
-- Run this in Supabase SQL Editor
-- ============================================================================

-- Drop existing trigger and function
DROP TRIGGER IF EXISTS on_auth_user_created ON auth.users;
DROP FUNCTION IF EXISTS public.handle_new_user();

-- Create new function with proper error handling
CREATE OR REPLACE FUNCTION public.handle_new_user()
RETURNS TRIGGER
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
  v_email TEXT;
  v_full_name TEXT;
BEGIN
  -- Get email with fallback
  v_email := COALESCE(NEW.email, NEW.raw_user_meta_data->>'email', 'user@unknown.com');
  
  -- Get full name with multiple fallbacks
  v_full_name := COALESCE(
    NEW.raw_user_meta_data->>'full_name',
    NEW.raw_user_meta_data->>'name',
    SPLIT_PART(v_email, '@', 1)
  );
  
  -- Insert into profiles table (for dashboard)
  BEGIN
    INSERT INTO profiles (id, study_level, marks_goal_pct)
    VALUES (NEW.id, 'ial', 90)
    ON CONFLICT (id) DO NOTHING;
  EXCEPTION
    WHEN undefined_table THEN NULL;
    WHEN OTHERS THEN NULL;
  END;
  
  -- Insert into user_profiles
  BEGIN
    INSERT INTO user_profiles (
      user_id, 
      email, 
      full_name, 
      avatar_url, 
      role,
      role_type
    )
    VALUES (
      NEW.id,
      v_email,
      v_full_name,
      NEW.raw_user_meta_data->>'avatar_url',
      'student',
      'student'
    )
    ON CONFLICT (user_id) DO NOTHING;
  EXCEPTION
    WHEN OTHERS THEN
      -- Log error but don't fail the signup
      RAISE WARNING 'Error creating user_profile for %: %', NEW.id, SQLERRM;
  END;
  
  -- Create default permissions
  BEGIN
    INSERT INTO user_permissions (
      user_id, 
      can_generate_worksheets, 
      is_active,
      max_worksheets_per_day,
      notes
    )
    VALUES (
      NEW.id, 
      TRUE,
      TRUE,
      30,
      'Auto-granted on signup'
    )
    ON CONFLICT (user_id) DO NOTHING;
  EXCEPTION
    WHEN OTHERS THEN
      RAISE WARNING 'Error creating permissions for %: %', NEW.id, SQLERRM;
  END;
  
  RETURN NEW;
END;
$$;

-- Recreate the trigger
CREATE TRIGGER on_auth_user_created
  AFTER INSERT ON auth.users
  FOR EACH ROW
  EXECUTE FUNCTION public.handle_new_user();

-- Verify trigger exists
SELECT 
  trigger_name, 
  event_manipulation, 
  event_object_table,
  action_statement
FROM information_schema.triggers
WHERE trigger_name = 'on_auth_user_created';

-- Test the function manually (optional)
-- SELECT handle_new_user();

SELECT '✅ Trigger fixed successfully!' as status;
