-- Run this in the Supabase SQL Editor before deploying usage tracking

CREATE TABLE IF NOT EXISTS usage_events (
  id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  created_at  timestamptz DEFAULT now(),
  user_id     uuid REFERENCES auth.users(id) ON DELETE SET NULL,
  feature     text NOT NULL,
  -- 'lecture_view' | 'lecture_download' | 'worksheet_generate' | 'worksheet_download'
  -- | 'test_builder_session' | 'test_builder_download'
  subject_id  uuid REFERENCES subjects(id) ON DELETE SET NULL,
  subject_name text,
  metadata    jsonb
);

CREATE INDEX IF NOT EXISTS usage_events_created_at  ON usage_events (created_at DESC);
CREATE INDEX IF NOT EXISTS usage_events_feature      ON usage_events (feature);
CREATE INDEX IF NOT EXISTS usage_events_subject_id   ON usage_events (subject_id);
CREATE INDEX IF NOT EXISTS usage_events_user_id      ON usage_events (user_id);

-- Allow authenticated users to insert their own events (RLS)
ALTER TABLE usage_events ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can insert own events"
  ON usage_events FOR INSERT
  TO authenticated
  WITH CHECK (user_id = auth.uid() OR user_id IS NULL);

-- Admins (service role) can read everything
CREATE POLICY "Service role full access"
  ON usage_events FOR ALL
  TO service_role
  USING (true)
  WITH CHECK (true);
