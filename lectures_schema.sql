-- ============================================================================
-- LECTURES SYSTEM SCHEMA
-- Run this in Supabase SQL Editor
-- ============================================================================

-- 1. Add 'role' column to profiles (student, teacher, admin)
ALTER TABLE profiles 
ADD COLUMN IF NOT EXISTS role TEXT DEFAULT 'student' 
CHECK (role IN ('student', 'teacher', 'admin'));

-- 2. Lectures metadata table
CREATE TABLE IF NOT EXISTS lectures (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  teacher_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  subject_id UUID NOT NULL REFERENCES subjects(id) ON DELETE CASCADE,
  week_number INT NOT NULL CHECK (week_number >= 1 AND week_number <= 52),
  lesson_name TEXT NOT NULL,
  file_name TEXT NOT NULL,
  file_url TEXT NOT NULL,
  file_size BIGINT,
  file_type TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_lectures_teacher ON lectures(teacher_id);
CREATE INDEX IF NOT EXISTS idx_lectures_subject ON lectures(subject_id);
CREATE INDEX IF NOT EXISTS idx_lectures_week ON lectures(subject_id, week_number);

-- 3. RLS Policies for lectures
ALTER TABLE lectures ENABLE ROW LEVEL SECURITY;

-- Everyone can view lectures (students + teachers + admins)
DROP POLICY IF EXISTS "Anyone can view lectures" ON lectures;
CREATE POLICY "Anyone can view lectures" ON lectures
  FOR SELECT USING (true);

-- Teachers can insert their own lectures
DROP POLICY IF EXISTS "Teachers can insert own lectures" ON lectures;
CREATE POLICY "Teachers can insert own lectures" ON lectures
  FOR INSERT WITH CHECK (
    auth.uid() = teacher_id
    AND EXISTS (
      SELECT 1 FROM profiles WHERE id = auth.uid() AND role IN ('teacher', 'admin')
    )
  );

-- Teachers can update their own lectures
DROP POLICY IF EXISTS "Teachers can update own lectures" ON lectures;
CREATE POLICY "Teachers can update own lectures" ON lectures
  FOR UPDATE USING (
    auth.uid() = teacher_id
    AND EXISTS (
      SELECT 1 FROM profiles WHERE id = auth.uid() AND role IN ('teacher', 'admin')
    )
  );

-- Teachers can delete their own lectures, admins can delete any
DROP POLICY IF EXISTS "Teachers can delete own lectures" ON lectures;
CREATE POLICY "Teachers can delete own lectures" ON lectures
  FOR DELETE USING (
    auth.uid() = teacher_id
    OR EXISTS (
      SELECT 1 FROM profiles WHERE id = auth.uid() AND role = 'admin'
    )
  );

-- 4. Update profiles RLS so admins can update other users' roles
DROP POLICY IF EXISTS "Admins can update any profile" ON profiles;
CREATE POLICY "Admins can update any profile" ON profiles
  FOR UPDATE USING (
    EXISTS (
      SELECT 1 FROM profiles WHERE id = auth.uid() AND role = 'admin'
    )
  );

DROP POLICY IF EXISTS "Admins can view all profiles" ON profiles;
CREATE POLICY "Admins can view all profiles" ON profiles
  FOR SELECT USING (
    auth.uid() = id
    OR EXISTS (
      SELECT 1 FROM profiles WHERE id = auth.uid() AND role = 'admin'
    )
  );

-- 5. Create storage bucket for lecture files
INSERT INTO storage.buckets (id, name, public)
VALUES ('lectures', 'lectures', true)
ON CONFLICT (id) DO NOTHING;

-- 6. Storage RLS policies
-- Allow authenticated users to read lecture files
DROP POLICY IF EXISTS "Anyone can read lecture files" ON storage.objects;
CREATE POLICY "Anyone can read lecture files" ON storage.objects
  FOR SELECT USING (bucket_id = 'lectures');

-- Allow teachers/admins to upload lecture files
DROP POLICY IF EXISTS "Teachers can upload lecture files" ON storage.objects;
CREATE POLICY "Teachers can upload lecture files" ON storage.objects
  FOR INSERT WITH CHECK (
    bucket_id = 'lectures'
    AND EXISTS (
      SELECT 1 FROM profiles WHERE id = auth.uid() AND role IN ('teacher', 'admin')
    )
  );

-- Allow teachers to delete their own uploads, admins can delete any
DROP POLICY IF EXISTS "Teachers can delete lecture files" ON storage.objects;
CREATE POLICY "Teachers can delete lecture files" ON storage.objects
  FOR DELETE USING (
    bucket_id = 'lectures'
    AND (
      auth.uid() = owner
      OR EXISTS (
        SELECT 1 FROM profiles WHERE id = auth.uid() AND role = 'admin'
      )
    )
  );

-- ============================================================================
-- VERIFICATION
-- ============================================================================
SELECT column_name, data_type, column_default 
FROM information_schema.columns 
WHERE table_name = 'lectures' 
ORDER BY ordinal_position;

SELECT column_name, data_type 
FROM information_schema.columns 
WHERE table_name = 'profiles' AND column_name = 'role';
