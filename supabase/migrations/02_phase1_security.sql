-- ============================================================================
-- PHASE 1: ESSENTIAL SECURITY UPGRADES
-- Session tracking, device management, audit logging, roles
-- Date: October 19, 2025
-- ============================================================================

-- ============================================================================
-- SESSIONS TABLE (Track active user sessions)
-- ============================================================================
CREATE TABLE IF NOT EXISTS user_sessions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  
  -- Session metadata
  ip_address TEXT,
  user_agent TEXT,
  device_label TEXT,
  platform TEXT, -- 'web', 'mobile', 'desktop'
  
  -- Security
  is_active BOOLEAN DEFAULT TRUE,
  remember_me BOOLEAN DEFAULT FALSE,
  last_activity_at TIMESTAMPTZ DEFAULT NOW(),
  
  -- Timestamps
  created_at TIMESTAMPTZ DEFAULT NOW(),
  expires_at TIMESTAMPTZ NOT NULL,
  
  -- Index for cleanup
  CONSTRAINT valid_expiry CHECK (expires_at > created_at)
);

CREATE INDEX idx_user_sessions_user_id ON user_sessions(user_id);
CREATE INDEX idx_user_sessions_active ON user_sessions(user_id, is_active) WHERE is_active = TRUE;
CREATE INDEX idx_user_sessions_expires ON user_sessions(expires_at) WHERE is_active = TRUE;

-- ============================================================================
-- TRUSTED DEVICES TABLE (Device fingerprinting)
-- ============================================================================
CREATE TABLE IF NOT EXISTS trusted_devices (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  
  -- Device identification
  device_label TEXT NOT NULL, -- User-friendly name (e.g., "Chrome on Windows")
  device_fingerprint TEXT NOT NULL, -- Hash of UA + other identifiers
  platform TEXT,
  browser TEXT,
  os TEXT,
  
  -- Trust status
  is_trusted BOOLEAN DEFAULT FALSE,
  trust_granted_at TIMESTAMPTZ,
  
  -- Activity
  first_seen_at TIMESTAMPTZ DEFAULT NOW(),
  last_seen_at TIMESTAMPTZ DEFAULT NOW(),
  last_ip TEXT,
  
  -- Timestamps
  created_at TIMESTAMPTZ DEFAULT NOW(),
  
  UNIQUE(user_id, device_fingerprint)
);

CREATE INDEX idx_trusted_devices_user_id ON trusted_devices(user_id);
CREATE INDEX idx_trusted_devices_trusted ON trusted_devices(user_id, is_trusted) WHERE is_trusted = TRUE;

-- ============================================================================
-- AUDIT LOG TABLE (Tamper-evident event log)
-- ============================================================================
CREATE TABLE IF NOT EXISTS audit_log (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  
  -- Event details
  event_type TEXT NOT NULL, -- 'auth.login', 'auth.logout', 'permission.granted', 'worksheet.generated', etc.
  event_category TEXT NOT NULL, -- 'auth', 'permission', 'worksheet', 'admin', 'security'
  
  -- Actor
  actor_user_id UUID REFERENCES auth.users(id) ON DELETE SET NULL,
  actor_email TEXT,
  actor_role TEXT,
  
  -- Target (optional)
  target_user_id UUID REFERENCES auth.users(id) ON DELETE SET NULL,
  target_resource_type TEXT, -- 'user', 'worksheet', 'permission', etc.
  target_resource_id TEXT,
  
  -- Context
  ip_address TEXT,
  user_agent TEXT,
  session_id UUID REFERENCES user_sessions(id) ON DELETE SET NULL,
  
  -- Details (JSONB for flexibility)
  details JSONB,
  
  -- Result
  status TEXT NOT NULL, -- 'success', 'failure', 'error'
  error_message TEXT,
  
  -- Hash chain for tamper detection
  previous_hash TEXT,
  current_hash TEXT, -- SHA-256(id || event_type || actor_user_id || timestamp || previous_hash)
  
  -- Timestamp
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_audit_log_event_type ON audit_log(event_type);
CREATE INDEX idx_audit_log_category ON audit_log(event_category);
CREATE INDEX idx_audit_log_actor ON audit_log(actor_user_id);
CREATE INDEX idx_audit_log_target ON audit_log(target_user_id);
CREATE INDEX idx_audit_log_created ON audit_log(created_at DESC);
CREATE INDEX idx_audit_log_status ON audit_log(status);

-- ============================================================================
-- USAGE METERS TABLE (Track usage per user/org for quotas)
-- ============================================================================
CREATE TABLE IF NOT EXISTS usage_meters (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  
  -- Period
  period_start DATE NOT NULL,
  period_end DATE NOT NULL,
  
  -- Counters
  worksheets_generated INTEGER DEFAULT 0,
  pages_generated INTEGER DEFAULT 0,
  questions_generated INTEGER DEFAULT 0,
  
  -- Last update
  updated_at TIMESTAMPTZ DEFAULT NOW(),
  
  UNIQUE(user_id, period_start)
);

CREATE INDEX idx_usage_meters_user_period ON usage_meters(user_id, period_start DESC);

-- ============================================================================
-- UPDATE USER_PROFILES: Add detailed role information
-- ============================================================================
ALTER TABLE user_profiles 
  ADD COLUMN IF NOT EXISTS role_type TEXT DEFAULT 'student', -- 'student', 'teacher', 'org_admin', 'org_owner', 'support', 'billing_admin'
  ADD COLUMN IF NOT EXISTS display_name TEXT,
  ADD COLUMN IF NOT EXISTS bio TEXT,
  ADD COLUMN IF NOT EXISTS timezone TEXT DEFAULT 'UTC',
  ADD COLUMN IF NOT EXISTS locale TEXT DEFAULT 'en-US',
  ADD COLUMN IF NOT EXISTS preferences JSONB DEFAULT '{}'::jsonb;

-- Create index on role_type for filtering
CREATE INDEX IF NOT EXISTS idx_user_profiles_role_type ON user_profiles(role_type);

-- ============================================================================
-- FUNCTIONS
-- ============================================================================

-- Function to get active sessions count for a user
CREATE OR REPLACE FUNCTION get_active_sessions_count(check_user_id UUID)
RETURNS INTEGER
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
BEGIN
  RETURN (
    SELECT COUNT(*)
    FROM user_sessions
    WHERE user_id = check_user_id
      AND is_active = TRUE
      AND expires_at > NOW()
  );
END;
$$;

-- Function to get current month usage
CREATE OR REPLACE FUNCTION get_current_month_usage(check_user_id UUID)
RETURNS TABLE(
  worksheets INTEGER,
  pages INTEGER,
  questions INTEGER
)
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
BEGIN
  RETURN QUERY
  SELECT 
    COALESCE(worksheets_generated, 0) as worksheets,
    COALESCE(pages_generated, 0) as pages,
    COALESCE(questions_generated, 0) as questions
  FROM usage_meters
  WHERE user_id = check_user_id
    AND period_start = DATE_TRUNC('month', CURRENT_DATE)::DATE
  LIMIT 1;
END;
$$;

-- Function to increment usage meter
CREATE OR REPLACE FUNCTION increment_usage_meter(
  check_user_id UUID,
  worksheets_delta INTEGER DEFAULT 0,
  pages_delta INTEGER DEFAULT 0,
  questions_delta INTEGER DEFAULT 0
)
RETURNS VOID
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
  current_period_start DATE := DATE_TRUNC('month', CURRENT_DATE)::DATE;
  current_period_end DATE := (DATE_TRUNC('month', CURRENT_DATE) + INTERVAL '1 month' - INTERVAL '1 day')::DATE;
BEGIN
  INSERT INTO usage_meters (
    user_id, 
    period_start, 
    period_end, 
    worksheets_generated, 
    pages_generated, 
    questions_generated
  )
  VALUES (
    check_user_id,
    current_period_start,
    current_period_end,
    worksheets_delta,
    pages_delta,
    questions_delta
  )
  ON CONFLICT (user_id, period_start)
  DO UPDATE SET
    worksheets_generated = usage_meters.worksheets_generated + worksheets_delta,
    pages_generated = usage_meters.pages_generated + pages_delta,
    questions_generated = usage_meters.questions_generated + questions_delta,
    updated_at = NOW();
END;
$$;

-- Function to create audit log entry with hash chain
CREATE OR REPLACE FUNCTION create_audit_log_entry(
  p_event_type TEXT,
  p_event_category TEXT,
  p_actor_user_id UUID DEFAULT NULL,
  p_actor_email TEXT DEFAULT NULL,
  p_target_user_id UUID DEFAULT NULL,
  p_target_resource_type TEXT DEFAULT NULL,
  p_target_resource_id TEXT DEFAULT NULL,
  p_ip_address TEXT DEFAULT NULL,
  p_details JSONB DEFAULT NULL,
  p_status TEXT DEFAULT 'success'
)
RETURNS UUID
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
  v_log_id UUID := gen_random_uuid();
  v_previous_hash TEXT;
  v_current_hash TEXT;
BEGIN
  -- Get the previous hash from the last entry
  SELECT current_hash INTO v_previous_hash
  FROM audit_log
  ORDER BY created_at DESC
  LIMIT 1;
  
  -- Generate current hash (simplified - in production use proper SHA-256)
  v_current_hash := encode(
    digest(
      v_log_id::TEXT || 
      p_event_type || 
      COALESCE(p_actor_user_id::TEXT, '') || 
      NOW()::TEXT || 
      COALESCE(v_previous_hash, ''),
      'sha256'
    ),
    'hex'
  );
  
  INSERT INTO audit_log (
    id,
    event_type,
    event_category,
    actor_user_id,
    actor_email,
    target_user_id,
    target_resource_type,
    target_resource_id,
    ip_address,
    details,
    status,
    previous_hash,
    current_hash
  ) VALUES (
    v_log_id,
    p_event_type,
    p_event_category,
    p_actor_user_id,
    p_actor_email,
    p_target_user_id,
    p_target_resource_type,
    p_target_resource_id,
    p_ip_address,
    p_details,
    p_status,
    v_previous_hash,
    v_current_hash
  );
  
  RETURN v_log_id;
END;
$$;

-- Function to cleanup expired sessions
CREATE OR REPLACE FUNCTION cleanup_expired_sessions()
RETURNS INTEGER
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
  deleted_count INTEGER;
BEGIN
  WITH deleted AS (
    DELETE FROM user_sessions
    WHERE expires_at < NOW()
      AND is_active = FALSE
    RETURNING id
  )
  SELECT COUNT(*) INTO deleted_count FROM deleted;
  
  RETURN deleted_count;
END;
$$;

-- ============================================================================
-- ROW LEVEL SECURITY
-- ============================================================================

-- Enable RLS on new tables
ALTER TABLE user_sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE trusted_devices ENABLE ROW LEVEL SECURITY;
ALTER TABLE audit_log ENABLE ROW LEVEL SECURITY;
ALTER TABLE usage_meters ENABLE ROW LEVEL SECURITY;

-- Sessions: Users can view their own sessions
CREATE POLICY "Users can view own sessions"
  ON user_sessions
  FOR SELECT
  USING (auth.uid() = user_id);

-- Sessions: Users can delete their own sessions (logout)
CREATE POLICY "Users can delete own sessions"
  ON user_sessions
  FOR DELETE
  USING (auth.uid() = user_id);

-- Devices: Users can view their own devices
CREATE POLICY "Users can view own devices"
  ON trusted_devices
  FOR SELECT
  USING (auth.uid() = user_id);

-- Devices: Users can update their own devices
CREATE POLICY "Users can update own devices"
  ON trusted_devices
  FOR UPDATE
  USING (auth.uid() = user_id);

-- Audit log: Only service role can read (admins access via API)
CREATE POLICY "Service role can read audit log"
  ON audit_log
  FOR SELECT
  USING (auth.jwt()->>'role' = 'service_role');

-- Usage meters: Users can view their own usage
CREATE POLICY "Users can view own usage"
  ON usage_meters
  FOR SELECT
  USING (auth.uid() = user_id);

-- ============================================================================
-- TRIGGERS
-- ============================================================================

-- Auto-update last_activity on session access
CREATE OR REPLACE FUNCTION update_session_activity()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
  NEW.last_activity_at = NOW();
  RETURN NEW;
END;
$$;

CREATE TRIGGER trigger_update_session_activity
  BEFORE UPDATE ON user_sessions
  FOR EACH ROW
  EXECUTE FUNCTION update_session_activity();

-- ============================================================================
-- COMMENTS
-- ============================================================================

COMMENT ON TABLE user_sessions IS 'Active user sessions with device tracking';
COMMENT ON TABLE trusted_devices IS 'Trusted devices for each user';
COMMENT ON TABLE audit_log IS 'Tamper-evident audit log with hash chain';
COMMENT ON TABLE usage_meters IS 'Usage tracking per user per period';

COMMENT ON FUNCTION get_active_sessions_count IS 'Returns count of active sessions for user';
COMMENT ON FUNCTION get_current_month_usage IS 'Returns current month usage counters';
COMMENT ON FUNCTION increment_usage_meter IS 'Increments usage counters atomically';
COMMENT ON FUNCTION create_audit_log_entry IS 'Creates audit log entry with hash chain';
COMMENT ON FUNCTION cleanup_expired_sessions IS 'Removes expired inactive sessions';
