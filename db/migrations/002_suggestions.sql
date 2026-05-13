BEGIN;

CREATE OR REPLACE FUNCTION set_updated_at()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TABLE IF NOT EXISTS suggestions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES auth.users(id) ON DELETE SET NULL,
  name TEXT,
  email TEXT,
  message TEXT NOT NULL CHECK (char_length(message) BETWEEN 5 AND 5000),
  status TEXT NOT NULL DEFAULT 'new' CHECK (status IN ('new', 'reviewed', 'in_progress', 'done', 'archived')),
  admin_notes TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_suggestions_status_created ON suggestions(status, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_suggestions_user ON suggestions(user_id);

DROP TRIGGER IF EXISTS suggestions_set_updated_at ON suggestions;
CREATE TRIGGER suggestions_set_updated_at
  BEFORE UPDATE ON suggestions
  FOR EACH ROW EXECUTE FUNCTION set_updated_at();

ALTER TABLE suggestions ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "anyone can insert suggestions" ON suggestions;
CREATE POLICY "anyone can insert suggestions"
  ON suggestions FOR INSERT
  WITH CHECK (true);

DROP POLICY IF EXISTS "users see own suggestions" ON suggestions;
CREATE POLICY "users see own suggestions"
  ON suggestions FOR SELECT
  USING (auth.uid() IS NOT NULL AND user_id = auth.uid());

COMMIT;
