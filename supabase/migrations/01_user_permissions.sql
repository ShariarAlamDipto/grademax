-- ============================================================================
-- USER PERMISSIONS FOR WORKSHEET GENERATION
-- Migration: Add user_permissions table for access control
-- Date: October 18, 2025
-- ============================================================================

-- ============================================================================
-- USER_PERMISSIONS TABLE
-- Tracks which users have permission to generate worksheets
-- ============================================================================
CREATE TABLE IF NOT EXISTS user_permissions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  
  -- Permission details
  can_generate_worksheets BOOLEAN DEFAULT FALSE,
  permission_granted_at TIMESTAMPTZ,
  permission_granted_by UUID REFERENCES auth.users(id),
  
  -- Optional limits
  max_worksheets_per_day INTEGER,
  max_questions_per_worksheet INTEGER,
  
  -- Status
  is_active BOOLEAN DEFAULT TRUE,
  notes TEXT,  -- Admin notes about the permission
  
  -- Timestamps
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW(),
  
  UNIQUE(user_id)
);

-- Index for fast permission checks
CREATE INDEX idx_user_permissions_user ON user_permissions(user_id);
CREATE INDEX idx_user_permissions_active ON user_permissions(user_id, is_active) WHERE is_active = TRUE;

-- ============================================================================
-- USER_PROFILES TABLE (Extended user information)
-- ============================================================================
CREATE TABLE IF NOT EXISTS user_profiles (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  
  -- User information
  email TEXT NOT NULL,
  full_name TEXT,
  avatar_url TEXT,
  
  -- Institution (optional)
  institution TEXT,
  role TEXT,  -- "student", "teacher", "admin"
  
  -- Timestamps
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW(),
  last_login_at TIMESTAMPTZ,
  
  UNIQUE(user_id),
  UNIQUE(email)
);

CREATE INDEX idx_user_profiles_email ON user_profiles(email);
CREATE INDEX idx_user_profiles_role ON user_profiles(role);

-- ============================================================================
-- WORKSHEET GENERATION LOGS (Track usage)
-- ============================================================================
CREATE TABLE IF NOT EXISTS worksheet_generation_logs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  worksheet_id UUID REFERENCES worksheets(id) ON DELETE SET NULL,
  
  -- Request details
  subject_code TEXT NOT NULL,
  topics TEXT[] NOT NULL,
  year_start INTEGER,
  year_end INTEGER,
  difficulty TEXT,
  
  -- Result
  status TEXT NOT NULL,  -- "success", "error", "permission_denied"
  error_message TEXT,
  questions_generated INTEGER,
  
  -- Timestamps
  generated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_worksheet_logs_user ON worksheet_generation_logs(user_id);
CREATE INDEX idx_worksheet_logs_date ON worksheet_generation_logs(generated_at);
CREATE INDEX idx_worksheet_logs_status ON worksheet_generation_logs(status);

-- ============================================================================
-- ROW LEVEL SECURITY (RLS) POLICIES
-- ============================================================================

-- Enable RLS on user_permissions
ALTER TABLE user_permissions ENABLE ROW LEVEL SECURITY;

-- Users can read their own permissions
CREATE POLICY "Users can view own permissions"
  ON user_permissions
  FOR SELECT
  USING (auth.uid() = user_id);

-- Only service role can insert/update permissions (admin only)
CREATE POLICY "Service role can manage permissions"
  ON user_permissions
  FOR ALL
  USING (auth.jwt()->>'role' = 'service_role');

-- Enable RLS on user_profiles
ALTER TABLE user_profiles ENABLE ROW LEVEL SECURITY;

-- Users can read their own profile
CREATE POLICY "Users can view own profile"
  ON user_profiles
  FOR SELECT
  USING (auth.uid() = user_id);

-- Users can update their own profile
CREATE POLICY "Users can update own profile"
  ON user_profiles
  FOR UPDATE
  USING (auth.uid() = user_id);

-- Anyone can insert their profile on signup
CREATE POLICY "Users can insert own profile"
  ON user_profiles
  FOR INSERT
  WITH CHECK (auth.uid() = user_id);

-- Enable RLS on worksheet_generation_logs
ALTER TABLE worksheet_generation_logs ENABLE ROW LEVEL SECURITY;

-- Users can read their own logs
CREATE POLICY "Users can view own logs"
  ON worksheet_generation_logs
  FOR SELECT
  USING (auth.uid() = user_id);

-- Users can insert their own logs
CREATE POLICY "Users can insert own logs"
  ON worksheet_generation_logs
  FOR INSERT
  WITH CHECK (auth.uid() = user_id);

-- ============================================================================
-- FUNCTIONS
-- ============================================================================

-- Function to check if user has worksheet generation permission
CREATE OR REPLACE FUNCTION check_worksheet_permission(check_user_id UUID)
RETURNS BOOLEAN
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
BEGIN
  RETURN EXISTS (
    SELECT 1
    FROM user_permissions
    WHERE user_id = check_user_id
      AND can_generate_worksheets = TRUE
      AND is_active = TRUE
  );
END;
$$;

-- Function to get user's remaining daily worksheet quota
CREATE OR REPLACE FUNCTION get_remaining_worksheet_quota(check_user_id UUID)
RETURNS INTEGER
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
  max_per_day INTEGER;
  used_today INTEGER;
BEGIN
  -- Get user's daily limit
  SELECT max_worksheets_per_day INTO max_per_day
  FROM user_permissions
  WHERE user_id = check_user_id
    AND can_generate_worksheets = TRUE
    AND is_active = TRUE;
  
  -- No limit if not set
  IF max_per_day IS NULL THEN
    RETURN -1;  -- -1 means unlimited
  END IF;
  
  -- Count worksheets generated today
  SELECT COUNT(*) INTO used_today
  FROM worksheet_generation_logs
  WHERE user_id = check_user_id
    AND status = 'success'
    AND generated_at >= CURRENT_DATE;
  
  RETURN GREATEST(0, max_per_day - used_today);
END;
$$;

-- Function to automatically create profile on user signup
CREATE OR REPLACE FUNCTION handle_new_user()
RETURNS TRIGGER
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
BEGIN
  INSERT INTO user_profiles (user_id, email, full_name, avatar_url)
  VALUES (
    NEW.id,
    NEW.email,
    NEW.raw_user_meta_data->>'full_name',
    NEW.raw_user_meta_data->>'avatar_url'
  );
  
  -- Optionally create default permissions (disabled by default)
  INSERT INTO user_permissions (user_id, can_generate_worksheets, is_active)
  VALUES (NEW.id, FALSE, TRUE);
  
  RETURN NEW;
END;
$$;

-- Trigger to create profile on signup
DROP TRIGGER IF EXISTS on_auth_user_created ON auth.users;
CREATE TRIGGER on_auth_user_created
  AFTER INSERT ON auth.users
  FOR EACH ROW
  EXECUTE FUNCTION handle_new_user();

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$;

-- Triggers for updated_at
CREATE TRIGGER update_user_permissions_updated_at
  BEFORE UPDATE ON user_permissions
  FOR EACH ROW
  EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_user_profiles_updated_at
  BEFORE UPDATE ON user_profiles
  FOR EACH ROW
  EXECUTE FUNCTION update_updated_at_column();

-- ============================================================================
-- COMMENTS
-- ============================================================================

COMMENT ON TABLE user_permissions IS 'Controls which users can generate worksheets';
COMMENT ON TABLE user_profiles IS 'Extended user information and metadata';
COMMENT ON TABLE worksheet_generation_logs IS 'Audit log of all worksheet generation attempts';

COMMENT ON FUNCTION check_worksheet_permission IS 'Returns TRUE if user has active worksheet generation permission';
COMMENT ON FUNCTION get_remaining_worksheet_quota IS 'Returns remaining worksheets user can generate today (-1 = unlimited)';
COMMENT ON FUNCTION handle_new_user IS 'Automatically creates profile and default permissions for new users';
