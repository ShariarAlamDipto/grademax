-- ============================================================================
-- GradeMax — production Supabase schema snapshot (public schema)
-- Generated: 2026-06-12T05:32:15.537769+00:00 by scripts/dump_supabase_schema.py
--
-- Recreates every table, constraint, index, RLS policy, trigger and
-- function. Apply on a FRESH Supabase project via the SQL editor.
-- Default Supabase grants apply because the editor runs as `postgres`.
-- Data restore: scripts/restore_db_from_snapshot.py --data
-- ============================================================================

-- ─── Extensions ─────────────────────────────────────────────────────────────
DO $$ BEGIN
  CREATE EXTENSION IF NOT EXISTS "pg_stat_statements";
EXCEPTION WHEN OTHERS THEN
  RAISE NOTICE 'extension pg_stat_statements unavailable on this server — skipped';
END $$;
DO $$ BEGIN
  CREATE EXTENSION IF NOT EXISTS "pg_trgm";
EXCEPTION WHEN OTHERS THEN
  RAISE NOTICE 'extension pg_trgm unavailable on this server — skipped';
END $$;
DO $$ BEGIN
  CREATE EXTENSION IF NOT EXISTS "pgcrypto";
EXCEPTION WHEN OTHERS THEN
  RAISE NOTICE 'extension pgcrypto unavailable on this server — skipped';
END $$;
DO $$ BEGIN
  CREATE EXTENSION IF NOT EXISTS "supabase_vault";
EXCEPTION WHEN OTHERS THEN
  RAISE NOTICE 'extension supabase_vault unavailable on this server — skipped';
END $$;
DO $$ BEGIN
  CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
EXCEPTION WHEN OTHERS THEN
  RAISE NOTICE 'extension uuid-ossp unavailable on this server — skipped';
END $$;
DO $$ BEGIN
  CREATE EXTENSION IF NOT EXISTS "vector";
EXCEPTION WHEN OTHERS THEN
  RAISE NOTICE 'extension vector unavailable on this server — skipped';
END $$;

-- ─── Functions ──────────────────────────────────────────────────────────────
-- function: check_worksheet_permission
CREATE OR REPLACE FUNCTION public.check_worksheet_permission(check_user_id uuid)
 RETURNS boolean
 LANGUAGE plpgsql
 SECURITY DEFINER
AS $function$
BEGIN
  RETURN EXISTS (
    SELECT 1
    FROM user_permissions
    WHERE user_id = check_user_id
      AND can_generate_worksheets = TRUE
      AND is_active = TRUE
  );
END;
$function$
;
-- function: cleanup_expired_sessions
CREATE OR REPLACE FUNCTION public.cleanup_expired_sessions()
 RETURNS integer
 LANGUAGE plpgsql
 SECURITY DEFINER
AS $function$
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
$function$
;
-- function: create_audit_log_entry
CREATE OR REPLACE FUNCTION public.create_audit_log_entry(p_event_type text, p_event_category text, p_actor_user_id uuid DEFAULT NULL::uuid, p_actor_email text DEFAULT NULL::text, p_target_user_id uuid DEFAULT NULL::uuid, p_target_resource_type text DEFAULT NULL::text, p_target_resource_id text DEFAULT NULL::text, p_ip_address text DEFAULT NULL::text, p_details jsonb DEFAULT NULL::jsonb, p_status text DEFAULT 'success'::text)
 RETURNS uuid
 LANGUAGE plpgsql
 SECURITY DEFINER
AS $function$
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
$function$
;
-- function: get_active_sessions_count
CREATE OR REPLACE FUNCTION public.get_active_sessions_count(check_user_id uuid)
 RETURNS integer
 LANGUAGE plpgsql
 SECURITY DEFINER
AS $function$
BEGIN
  RETURN (
    SELECT COUNT(*)
    FROM user_sessions
    WHERE user_id = check_user_id
      AND is_active = TRUE
      AND expires_at > NOW()
  );
END;
$function$
;
-- function: get_current_month_usage
CREATE OR REPLACE FUNCTION public.get_current_month_usage(check_user_id uuid)
 RETURNS TABLE(worksheets integer, pages integer, questions integer)
 LANGUAGE plpgsql
 SECURITY DEFINER
AS $function$
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
$function$
;
-- function: get_questions_by_topics
CREATE OR REPLACE FUNCTION public.get_questions_by_topics(p_subject_code text, p_topic_codes text[], p_difficulties integer[] DEFAULT NULL::integer[], p_min_confidence real DEFAULT 0.6, p_limit integer DEFAULT 50)
 RETURNS TABLE(question_id uuid, question_number text, page_pdf_url text, ms_pdf_url text, marks integer, difficulty integer, confidence real, topic_count integer)
 LANGUAGE plpgsql
AS $function$
BEGIN
  RETURN QUERY
  SELECT DISTINCT
    q.id as question_id,
    q.question_number,
    q.page_pdf_url,
    q.ms_pdf_url,
    q.marks,
    q.difficulty,
    q.classification_confidence as confidence,
    COUNT(DISTINCT qt.topic_id)::INT as topic_count
  FROM questions q
  JOIN papers p ON q.paper_id = p.id
  JOIN subjects s ON p.subject_id = s.id
  JOIN question_topics qt ON q.id = qt.question_id
  JOIN topics t ON qt.topic_id = t.id
  WHERE 
    s.code = p_subject_code
    AND (p_topic_codes IS NULL OR t.code = ANY(p_topic_codes))
    AND (p_difficulties IS NULL OR q.difficulty = ANY(p_difficulties))
    AND q.classification_confidence >= p_min_confidence
    AND q.page_pdf_url IS NOT NULL  -- Only include questions with PDF pages
  GROUP BY q.id, q.question_number, q.page_pdf_url, q.ms_pdf_url, 
           q.marks, q.difficulty, q.classification_confidence
  ORDER BY q.classification_confidence DESC, RANDOM()
  LIMIT p_limit;
END;
$function$
;
-- function: get_remaining_worksheet_quota
CREATE OR REPLACE FUNCTION public.get_remaining_worksheet_quota(check_user_id uuid)
 RETURNS integer
 LANGUAGE plpgsql
 SECURITY DEFINER
AS $function$
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
$function$
;
-- function: get_worksheet_pages
CREATE OR REPLACE FUNCTION public.get_worksheet_pages(p_subject_code text, p_topics text[], p_year_start integer DEFAULT NULL::integer, p_year_end integer DEFAULT NULL::integer, p_difficulty text DEFAULT NULL::text, p_limit integer DEFAULT 50)
 RETURNS TABLE(page_id uuid, paper_id uuid, year integer, season text, paper_number text, question_number text, topics text[], difficulty text, qp_page_url text, ms_page_url text, has_diagram boolean)
 LANGUAGE plpgsql
AS $function$
BEGIN
  RETURN QUERY
  SELECT 
    p.id AS page_id,
    p.paper_id,
    pa.year,
    pa.season,
    pa.paper_number,
    p.question_number,
    p.topics,
    p.difficulty,
    p.qp_page_url,
    p.ms_page_url,
    p.has_diagram
  FROM pages p
  JOIN papers pa ON p.paper_id = pa.id
  JOIN subjects s ON pa.subject_id = s.id
  WHERE s.code = p_subject_code
    AND p.topics && p_topics                    -- Array overlap
    AND p.is_question = TRUE
    AND p.qp_page_url IS NOT NULL
    AND (p_year_start IS NULL OR pa.year >= p_year_start)
    AND (p_year_end IS NULL OR pa.year <= p_year_end)
    AND (p_difficulty IS NULL OR p.difficulty = p_difficulty)
  ORDER BY pa.year, pa.season, p.question_number
  LIMIT p_limit;
END;
$function$
;
-- function: handle_new_user
CREATE OR REPLACE FUNCTION public.handle_new_user()
 RETURNS trigger
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'public'
AS $function$
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
$function$
;
-- function: increment_usage_meter
CREATE OR REPLACE FUNCTION public.increment_usage_meter(check_user_id uuid, worksheets_delta integer DEFAULT 0, pages_delta integer DEFAULT 0, questions_delta integer DEFAULT 0)
 RETURNS void
 LANGUAGE plpgsql
 SECURITY DEFINER
AS $function$
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
$function$
;
-- function: set_updated_at
CREATE OR REPLACE FUNCTION public.set_updated_at()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$function$
;
-- function: update_classification_confidence
CREATE OR REPLACE FUNCTION public.update_classification_confidence()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
BEGIN
  -- If a guardrail adds a topic, increase confidence slightly
  IF NEW.classification_method = 'guardrail' THEN
    UPDATE questions 
    SET classification_confidence = LEAST(classification_confidence + 0.1, 1.0)
    WHERE id = NEW.question_id;
  END IF;
  RETURN NEW;
END;
$function$
;
-- function: update_session_activity
CREATE OR REPLACE FUNCTION public.update_session_activity()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
BEGIN
  NEW.last_activity_at = NOW();
  RETURN NEW;
END;
$function$
;
-- function: update_updated_at_column
CREATE OR REPLACE FUNCTION public.update_updated_at_column()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$function$
;

-- ─── Tables ─────────────────────────────────────────────────────────────────
-- table: audit_log
CREATE TABLE IF NOT EXISTS "audit_log" (
  "id" uuid DEFAULT gen_random_uuid() NOT NULL,
  "event_type" text NOT NULL,
  "event_category" text NOT NULL,
  "actor_user_id" uuid,
  "actor_email" text,
  "actor_role" text,
  "target_user_id" uuid,
  "target_resource_type" text,
  "target_resource_id" text,
  "ip_address" text,
  "user_agent" text,
  "session_id" uuid,
  "details" jsonb,
  "status" text NOT NULL,
  "error_message" text,
  "previous_hash" text,
  "current_hash" text,
  "created_at" timestamp with time zone DEFAULT now(),
  CONSTRAINT "audit_log_pkey" PRIMARY KEY (id)
);

-- table: ingestion_manifests
CREATE TABLE IF NOT EXISTS "ingestion_manifests" (
  "id" uuid DEFAULT gen_random_uuid() NOT NULL,
  "paper_id" uuid NOT NULL,
  "manifest_path" text NOT NULL,
  "total_questions" integer NOT NULL,
  "pages_processed" integer NOT NULL,
  "llm_calls" integer DEFAULT 0 NOT NULL,
  "guardrail_corrections" integer DEFAULT 0 NOT NULL,
  "average_confidence" real,
  "processing_time_seconds" integer,
  "gemini_model" text,
  "created_at" timestamp with time zone DEFAULT now(),
  CONSTRAINT "ingestion_manifests_pkey" PRIMARY KEY (id),
  CONSTRAINT "ingestion_manifests_paper_id_key" UNIQUE (paper_id)
);

-- table: ingestions
CREATE TABLE IF NOT EXISTS "ingestions" (
  "id" uuid DEFAULT uuid_generate_v4() NOT NULL,
  "paper_id" uuid,
  "status" text DEFAULT 'pending'::text,
  "questions_found" integer DEFAULT 0,
  "parts_found" integer DEFAULT 0,
  "tags_found" integer DEFAULT 0,
  "error" text,
  "created_at" timestamp with time zone DEFAULT now(),
  "completed_at" timestamp with time zone,
  CONSTRAINT "ingestions_status_check" CHECK ((status = ANY (ARRAY['pending'::text, 'processing'::text, 'completed'::text, 'failed'::text]))),
  CONSTRAINT "ingestions_pkey" PRIMARY KEY (id)
);

-- table: lectures
CREATE TABLE IF NOT EXISTS "lectures" (
  "id" uuid DEFAULT gen_random_uuid() NOT NULL,
  "teacher_id" uuid NOT NULL,
  "subject_id" uuid NOT NULL,
  "week_number" integer NOT NULL,
  "lesson_name" text NOT NULL,
  "file_name" text NOT NULL,
  "file_url" text NOT NULL,
  "file_size" bigint,
  "file_type" text,
  "created_at" timestamp with time zone DEFAULT now(),
  "updated_at" timestamp with time zone DEFAULT now(),
  CONSTRAINT "lectures_week_number_check" CHECK (((week_number >= 1) AND (week_number <= 52))),
  CONSTRAINT "lectures_pkey" PRIMARY KEY (id)
);

-- table: markschemes
CREATE TABLE IF NOT EXISTS "markschemes" (
  "id" uuid DEFAULT gen_random_uuid() NOT NULL,
  "question_id" uuid NOT NULL,
  "text" text NOT NULL,
  "marks_breakdown" jsonb,
  "created_at" timestamp with time zone DEFAULT now(),
  CONSTRAINT "markschemes_pkey" PRIMARY KEY (id),
  CONSTRAINT "markschemes_question_id_key" UNIQUE (question_id)
);

-- table: pages
CREATE TABLE IF NOT EXISTS "pages" (
  "id" uuid DEFAULT gen_random_uuid() NOT NULL,
  "paper_id" uuid NOT NULL,
  "page_number" integer NOT NULL,
  "question_number" text,
  "is_question" boolean DEFAULT true,
  "topics" text[] DEFAULT '{}'::text[] NOT NULL,
  "difficulty" text,
  "confidence" double precision,
  "qp_page_url" text,
  "ms_page_url" text,
  "has_diagram" boolean DEFAULT false,
  "page_count" integer DEFAULT 1,
  "text_excerpt" text,
  "created_at" timestamp with time zone DEFAULT now(),
  CONSTRAINT "pages_pkey" PRIMARY KEY (id),
  CONSTRAINT "pages_paper_id_page_number_key" UNIQUE (paper_id, page_number)
);

-- table: paper_pages
CREATE TABLE IF NOT EXISTS "paper_pages" (
  "id" uuid DEFAULT gen_random_uuid() NOT NULL,
  "paper_id" uuid,
  "page_number" integer NOT NULL,
  "visual_url" text NOT NULL,
  "width" integer,
  "height" integer,
  "dpi" integer DEFAULT 300,
  "file_size_kb" integer,
  "created_at" timestamp with time zone DEFAULT now(),
  CONSTRAINT "paper_pages_pkey" PRIMARY KEY (id),
  CONSTRAINT "paper_pages_paper_id_page_number_key" UNIQUE (paper_id, page_number)
);

-- table: papers
CREATE TABLE IF NOT EXISTS "papers" (
  "id" uuid DEFAULT gen_random_uuid() NOT NULL,
  "subject_id" uuid NOT NULL,
  "year" integer NOT NULL,
  "season" text NOT NULL,
  "paper_number" text NOT NULL,
  "processed_at" timestamp with time zone DEFAULT now(),
  "created_at" timestamp with time zone DEFAULT now(),
  "pdf_url" text,
  "markscheme_pdf_url" text,
  "data_file_url" text,
  CONSTRAINT "papers_pkey" PRIMARY KEY (id),
  CONSTRAINT "papers_subject_id_year_season_paper_number_key" UNIQUE (subject_id, year, season, paper_number)
);

-- table: profiles
CREATE TABLE IF NOT EXISTS "profiles" (
  "id" uuid NOT NULL,
  "email" text,
  "full_name" text,
  "avatar_url" text,
  "study_level" text,
  "marks_goal_pct" integer DEFAULT 90,
  "created_at" timestamp with time zone DEFAULT now(),
  "updated_at" timestamp with time zone DEFAULT now(),
  "role" text DEFAULT 'student'::text,
  CONSTRAINT "profiles_marks_goal_pct_check" CHECK (((marks_goal_pct >= 0) AND (marks_goal_pct <= 100))),
  CONSTRAINT "profiles_role_check" CHECK ((role = ANY (ARRAY['student'::text, 'teacher'::text, 'admin'::text]))),
  CONSTRAINT "profiles_study_level_check" CHECK ((study_level = ANY (ARRAY['igcse'::text, 'ial'::text, 'a-level'::text]))),
  CONSTRAINT "profiles_pkey" PRIMARY KEY (id)
);

-- table: question_parts
CREATE TABLE IF NOT EXISTS "question_parts" (
  "id" uuid DEFAULT uuid_generate_v4() NOT NULL,
  "question_id" uuid NOT NULL,
  "code" text NOT NULL,
  "marks" integer,
  "page_from" integer NOT NULL,
  "page_to" integer NOT NULL,
  "bbox_list" jsonb NOT NULL,
  "text_preview" text,
  "visual_hash" text,
  "answer_space_lines" integer DEFAULT 0,
  "ms_link_confidence" real DEFAULT 0.0,
  "ms_points" jsonb,
  "ms_snippet" text,
  "features" jsonb,
  "spec_refs" text[],
  "diagram_urls" text[],
  "diagram_dims" jsonb,
  "created_at" timestamp with time zone DEFAULT now(),
  "updated_at" timestamp with time zone DEFAULT now(),
  CONSTRAINT "question_parts_pkey" PRIMARY KEY (id),
  CONSTRAINT "question_parts_question_id_code_key" UNIQUE (question_id, code)
);

-- table: question_tags
CREATE TABLE IF NOT EXISTS "question_tags" (
  "id" uuid DEFAULT gen_random_uuid() NOT NULL,
  "question_id" uuid NOT NULL,
  "topic" text NOT NULL,
  "created_at" timestamp with time zone DEFAULT now(),
  CONSTRAINT "question_tags_pkey" PRIMARY KEY (id),
  CONSTRAINT "question_tags_question_id_topic_key" UNIQUE (question_id, topic)
);

-- table: questions
CREATE TABLE IF NOT EXISTS "questions" (
  "id" uuid DEFAULT gen_random_uuid() NOT NULL,
  "paper_id" uuid NOT NULL,
  "question_number" text,
  "difficulty" text,
  "page_pdf_url" text,
  "ms_pdf_url" text,
  "has_diagram" boolean DEFAULT false,
  "text_excerpt" text,
  "created_at" timestamp with time zone DEFAULT now(),
  CONSTRAINT "questions_difficulty_check" CHECK ((difficulty = ANY (ARRAY['easy'::text, 'medium'::text, 'hard'::text]))),
  CONSTRAINT "questions_pkey" PRIMARY KEY (id)
);

-- table: subjects
CREATE TABLE IF NOT EXISTS "subjects" (
  "id" uuid DEFAULT gen_random_uuid() NOT NULL,
  "code" text NOT NULL,
  "name" text NOT NULL,
  "board" text NOT NULL,
  "level" text NOT NULL,
  "created_at" timestamp with time zone DEFAULT now(),
  CONSTRAINT "subjects_pkey" PRIMARY KEY (id),
  CONSTRAINT "subjects_code_key" UNIQUE (code)
);

-- table: suggestions
CREATE TABLE IF NOT EXISTS "suggestions" (
  "id" uuid DEFAULT gen_random_uuid() NOT NULL,
  "user_id" uuid,
  "name" text,
  "email" text,
  "message" text NOT NULL,
  "status" text DEFAULT 'new'::text NOT NULL,
  "admin_notes" text,
  "created_at" timestamp with time zone DEFAULT now() NOT NULL,
  "updated_at" timestamp with time zone DEFAULT now() NOT NULL,
  CONSTRAINT "suggestions_message_check" CHECK (((char_length(message) >= 5) AND (char_length(message) <= 5000))),
  CONSTRAINT "suggestions_status_check" CHECK ((status = ANY (ARRAY['new'::text, 'reviewed'::text, 'in_progress'::text, 'done'::text, 'archived'::text]))),
  CONSTRAINT "suggestions_pkey" PRIMARY KEY (id)
);

-- table: test_items
CREATE TABLE IF NOT EXISTS "test_items" (
  "id" uuid DEFAULT gen_random_uuid() NOT NULL,
  "test_id" uuid NOT NULL,
  "page_id" uuid NOT NULL,
  "sequence_order" integer NOT NULL,
  "created_at" timestamp with time zone DEFAULT now(),
  CONSTRAINT "test_items_pkey" PRIMARY KEY (id),
  CONSTRAINT "test_items_test_id_page_id_key" UNIQUE (test_id, page_id)
);

-- table: tests
CREATE TABLE IF NOT EXISTS "tests" (
  "id" uuid DEFAULT gen_random_uuid() NOT NULL,
  "user_id" uuid,
  "title" text DEFAULT 'Untitled Test'::text NOT NULL,
  "subject_id" uuid NOT NULL,
  "total_marks" integer DEFAULT 0,
  "total_questions" integer DEFAULT 0,
  "question_paper_url" text,
  "mark_scheme_url" text,
  "status" text DEFAULT 'draft'::text,
  "created_at" timestamp with time zone DEFAULT now(),
  "updated_at" timestamp with time zone DEFAULT now(),
  CONSTRAINT "tests_status_check" CHECK ((status = ANY (ARRAY['draft'::text, 'finalized'::text]))),
  CONSTRAINT "tests_pkey" PRIMARY KEY (id)
);

-- table: topics
CREATE TABLE IF NOT EXISTS "topics" (
  "id" uuid DEFAULT gen_random_uuid() NOT NULL,
  "subject_id" uuid NOT NULL,
  "code" text NOT NULL,
  "name" text NOT NULL,
  "description" text,
  "keywords" text[],
  "formulas" text[],
  "created_at" timestamp with time zone DEFAULT now(),
  CONSTRAINT "topics_pkey" PRIMARY KEY (id),
  CONSTRAINT "topics_subject_id_code_key" UNIQUE (subject_id, code)
);

-- table: trusted_devices
CREATE TABLE IF NOT EXISTS "trusted_devices" (
  "id" uuid DEFAULT gen_random_uuid() NOT NULL,
  "user_id" uuid NOT NULL,
  "device_label" text NOT NULL,
  "device_fingerprint" text NOT NULL,
  "platform" text,
  "browser" text,
  "os" text,
  "is_trusted" boolean DEFAULT false,
  "trust_granted_at" timestamp with time zone,
  "first_seen_at" timestamp with time zone DEFAULT now(),
  "last_seen_at" timestamp with time zone DEFAULT now(),
  "last_ip" text,
  "created_at" timestamp with time zone DEFAULT now(),
  CONSTRAINT "trusted_devices_pkey" PRIMARY KEY (id),
  CONSTRAINT "trusted_devices_user_id_device_fingerprint_key" UNIQUE (user_id, device_fingerprint)
);

-- table: usage_events
CREATE TABLE IF NOT EXISTS "usage_events" (
  "id" uuid DEFAULT gen_random_uuid() NOT NULL,
  "created_at" timestamp with time zone DEFAULT now(),
  "user_id" uuid,
  "feature" text NOT NULL,
  "subject_id" uuid,
  "subject_name" text,
  "metadata" jsonb,
  CONSTRAINT "usage_events_pkey" PRIMARY KEY (id)
);

-- table: usage_meters
CREATE TABLE IF NOT EXISTS "usage_meters" (
  "id" uuid DEFAULT gen_random_uuid() NOT NULL,
  "user_id" uuid NOT NULL,
  "period_start" date NOT NULL,
  "period_end" date NOT NULL,
  "worksheets_generated" integer DEFAULT 0,
  "pages_generated" integer DEFAULT 0,
  "questions_generated" integer DEFAULT 0,
  "updated_at" timestamp with time zone DEFAULT now(),
  CONSTRAINT "usage_meters_pkey" PRIMARY KEY (id),
  CONSTRAINT "usage_meters_user_id_period_start_key" UNIQUE (user_id, period_start)
);

-- table: user_permissions
CREATE TABLE IF NOT EXISTS "user_permissions" (
  "id" uuid DEFAULT gen_random_uuid() NOT NULL,
  "user_id" uuid NOT NULL,
  "can_generate_worksheets" boolean DEFAULT false,
  "permission_granted_at" timestamp with time zone,
  "permission_granted_by" uuid,
  "max_worksheets_per_day" integer,
  "max_questions_per_worksheet" integer,
  "is_active" boolean DEFAULT true,
  "notes" text,
  "created_at" timestamp with time zone DEFAULT now(),
  "updated_at" timestamp with time zone DEFAULT now(),
  CONSTRAINT "user_permissions_pkey" PRIMARY KEY (id),
  CONSTRAINT "user_permissions_user_id_key" UNIQUE (user_id)
);

-- table: user_profiles
CREATE TABLE IF NOT EXISTS "user_profiles" (
  "id" uuid DEFAULT gen_random_uuid() NOT NULL,
  "user_id" uuid NOT NULL,
  "email" text NOT NULL,
  "full_name" text,
  "avatar_url" text,
  "institution" text,
  "role" text,
  "created_at" timestamp with time zone DEFAULT now(),
  "updated_at" timestamp with time zone DEFAULT now(),
  "last_login_at" timestamp with time zone,
  "role_type" text DEFAULT 'student'::text,
  "display_name" text,
  "bio" text,
  "timezone" text DEFAULT 'UTC'::text,
  "locale" text DEFAULT 'en-US'::text,
  "preferences" jsonb DEFAULT '{}'::jsonb,
  CONSTRAINT "user_profiles_pkey" PRIMARY KEY (id),
  CONSTRAINT "user_profiles_email_key" UNIQUE (email),
  CONSTRAINT "user_profiles_user_id_key" UNIQUE (user_id)
);

-- table: user_sessions
CREATE TABLE IF NOT EXISTS "user_sessions" (
  "id" uuid DEFAULT gen_random_uuid() NOT NULL,
  "user_id" uuid NOT NULL,
  "ip_address" text,
  "user_agent" text,
  "device_label" text,
  "platform" text,
  "is_active" boolean DEFAULT true,
  "remember_me" boolean DEFAULT false,
  "last_activity_at" timestamp with time zone DEFAULT now(),
  "created_at" timestamp with time zone DEFAULT now(),
  "expires_at" timestamp with time zone NOT NULL,
  CONSTRAINT "valid_expiry" CHECK ((expires_at > created_at)),
  CONSTRAINT "user_sessions_pkey" PRIMARY KEY (id)
);

-- table: user_subjects
CREATE TABLE IF NOT EXISTS "user_subjects" (
  "id" uuid DEFAULT uuid_generate_v4() NOT NULL,
  "user_id" uuid,
  "subject_id" uuid,
  "created_at" timestamp with time zone DEFAULT now(),
  CONSTRAINT "user_subjects_pkey" PRIMARY KEY (id),
  CONSTRAINT "user_subjects_user_id_subject_id_key" UNIQUE (user_id, subject_id)
);

-- table: worksheet_generation_logs
CREATE TABLE IF NOT EXISTS "worksheet_generation_logs" (
  "id" uuid DEFAULT gen_random_uuid() NOT NULL,
  "user_id" uuid NOT NULL,
  "worksheet_id" uuid,
  "subject_code" text NOT NULL,
  "topics" text[] NOT NULL,
  "year_start" integer,
  "year_end" integer,
  "difficulty" text,
  "status" text NOT NULL,
  "error_message" text,
  "questions_generated" integer,
  "generated_at" timestamp with time zone DEFAULT now(),
  CONSTRAINT "worksheet_generation_logs_pkey" PRIMARY KEY (id)
);

-- table: worksheet_items
CREATE TABLE IF NOT EXISTS "worksheet_items" (
  "id" uuid DEFAULT gen_random_uuid() NOT NULL,
  "worksheet_id" uuid NOT NULL,
  "created_at" timestamp with time zone DEFAULT now(),
  "question_id" uuid,
  "position" integer NOT NULL,
  CONSTRAINT "worksheet_items_pkey" PRIMARY KEY (id),
  CONSTRAINT "worksheet_items_worksheet_id_question_id_key" UNIQUE (worksheet_id, question_id)
);

-- table: worksheets
CREATE TABLE IF NOT EXISTS "worksheets" (
  "id" uuid DEFAULT gen_random_uuid() NOT NULL,
  "subject_id" uuid,
  "worksheet_url" text,
  "markscheme_url" text,
  "total_pages" integer,
  "generated_at" timestamp with time zone DEFAULT now(),
  "created_at" timestamp with time zone DEFAULT now(),
  "user_id" uuid,
  "title" text,
  "description" text,
  "params" jsonb,
  CONSTRAINT "worksheets_pkey" PRIMARY KEY (id)
);

-- ─── Foreign keys ───────────────────────────────────────────────────────────
ALTER TABLE "audit_log" ADD CONSTRAINT "audit_log_actor_user_id_fkey" FOREIGN KEY (actor_user_id) REFERENCES auth.users(id) ON DELETE SET NULL;
ALTER TABLE "audit_log" ADD CONSTRAINT "audit_log_session_id_fkey" FOREIGN KEY (session_id) REFERENCES user_sessions(id) ON DELETE SET NULL;
ALTER TABLE "audit_log" ADD CONSTRAINT "audit_log_target_user_id_fkey" FOREIGN KEY (target_user_id) REFERENCES auth.users(id) ON DELETE SET NULL;
ALTER TABLE "lectures" ADD CONSTRAINT "lectures_subject_id_fkey" FOREIGN KEY (subject_id) REFERENCES subjects(id) ON DELETE CASCADE;
ALTER TABLE "lectures" ADD CONSTRAINT "lectures_teacher_id_fkey" FOREIGN KEY (teacher_id) REFERENCES auth.users(id) ON DELETE CASCADE;
ALTER TABLE "pages" ADD CONSTRAINT "pages_paper_id_fkey" FOREIGN KEY (paper_id) REFERENCES papers(id) ON DELETE CASCADE;
ALTER TABLE "papers" ADD CONSTRAINT "papers_subject_id_fkey" FOREIGN KEY (subject_id) REFERENCES subjects(id) ON DELETE CASCADE;
ALTER TABLE "profiles" ADD CONSTRAINT "profiles_id_fkey" FOREIGN KEY (id) REFERENCES auth.users(id) ON DELETE CASCADE;
ALTER TABLE "question_tags" ADD CONSTRAINT "question_tags_question_id_fkey" FOREIGN KEY (question_id) REFERENCES questions(id) ON DELETE CASCADE;
ALTER TABLE "questions" ADD CONSTRAINT "questions_paper_id_fkey" FOREIGN KEY (paper_id) REFERENCES papers(id) ON DELETE CASCADE;
ALTER TABLE "suggestions" ADD CONSTRAINT "suggestions_user_id_fkey" FOREIGN KEY (user_id) REFERENCES auth.users(id) ON DELETE SET NULL;
ALTER TABLE "test_items" ADD CONSTRAINT "test_items_page_id_fkey" FOREIGN KEY (page_id) REFERENCES pages(id) ON DELETE CASCADE;
ALTER TABLE "test_items" ADD CONSTRAINT "test_items_test_id_fkey" FOREIGN KEY (test_id) REFERENCES tests(id) ON DELETE CASCADE;
ALTER TABLE "tests" ADD CONSTRAINT "tests_subject_id_fkey" FOREIGN KEY (subject_id) REFERENCES subjects(id);
ALTER TABLE "tests" ADD CONSTRAINT "tests_user_id_fkey" FOREIGN KEY (user_id) REFERENCES profiles(id) ON DELETE CASCADE;
ALTER TABLE "topics" ADD CONSTRAINT "topics_subject_id_fkey" FOREIGN KEY (subject_id) REFERENCES subjects(id) ON DELETE CASCADE;
ALTER TABLE "trusted_devices" ADD CONSTRAINT "trusted_devices_user_id_fkey" FOREIGN KEY (user_id) REFERENCES auth.users(id) ON DELETE CASCADE;
ALTER TABLE "usage_events" ADD CONSTRAINT "usage_events_subject_id_fkey" FOREIGN KEY (subject_id) REFERENCES subjects(id) ON DELETE SET NULL;
ALTER TABLE "usage_events" ADD CONSTRAINT "usage_events_user_id_fkey" FOREIGN KEY (user_id) REFERENCES auth.users(id) ON DELETE SET NULL;
ALTER TABLE "usage_meters" ADD CONSTRAINT "usage_meters_user_id_fkey" FOREIGN KEY (user_id) REFERENCES auth.users(id) ON DELETE CASCADE;
ALTER TABLE "user_permissions" ADD CONSTRAINT "user_permissions_permission_granted_by_fkey" FOREIGN KEY (permission_granted_by) REFERENCES auth.users(id);
ALTER TABLE "user_permissions" ADD CONSTRAINT "user_permissions_user_id_fkey" FOREIGN KEY (user_id) REFERENCES auth.users(id) ON DELETE CASCADE;
ALTER TABLE "user_profiles" ADD CONSTRAINT "user_profiles_user_id_fkey" FOREIGN KEY (user_id) REFERENCES auth.users(id) ON DELETE CASCADE;
ALTER TABLE "user_sessions" ADD CONSTRAINT "user_sessions_user_id_fkey" FOREIGN KEY (user_id) REFERENCES auth.users(id) ON DELETE CASCADE;
ALTER TABLE "user_subjects" ADD CONSTRAINT "user_subjects_user_id_fkey" FOREIGN KEY (user_id) REFERENCES auth.users(id) ON DELETE CASCADE;
ALTER TABLE "worksheet_generation_logs" ADD CONSTRAINT "worksheet_generation_logs_user_id_fkey" FOREIGN KEY (user_id) REFERENCES auth.users(id) ON DELETE CASCADE;
ALTER TABLE "worksheet_generation_logs" ADD CONSTRAINT "worksheet_generation_logs_worksheet_id_fkey" FOREIGN KEY (worksheet_id) REFERENCES worksheets(id) ON DELETE SET NULL;
ALTER TABLE "worksheet_items" ADD CONSTRAINT "worksheet_items_question_id_fkey" FOREIGN KEY (question_id) REFERENCES questions(id) ON DELETE CASCADE;
ALTER TABLE "worksheet_items" ADD CONSTRAINT "worksheet_items_worksheet_id_fkey" FOREIGN KEY (worksheet_id) REFERENCES worksheets(id) ON DELETE CASCADE;
ALTER TABLE "worksheets" ADD CONSTRAINT "worksheets_subject_id_fkey" FOREIGN KEY (subject_id) REFERENCES subjects(id);
ALTER TABLE "worksheets" ADD CONSTRAINT "worksheets_user_id_fkey" FOREIGN KEY (user_id) REFERENCES auth.users(id);

-- ─── Indexes ────────────────────────────────────────────────────────────────
CREATE INDEX idx_audit_log_actor ON public.audit_log USING btree (actor_user_id);
CREATE INDEX idx_audit_log_category ON public.audit_log USING btree (event_category);
CREATE INDEX idx_audit_log_created ON public.audit_log USING btree (created_at DESC);
CREATE INDEX idx_audit_log_event_type ON public.audit_log USING btree (event_type);
CREATE INDEX idx_audit_log_status ON public.audit_log USING btree (status);
CREATE INDEX idx_audit_log_target ON public.audit_log USING btree (target_user_id);
CREATE INDEX idx_ingestions_created ON public.ingestions USING btree (created_at DESC);
CREATE INDEX idx_ingestions_paper ON public.ingestions USING btree (paper_id);
CREATE INDEX idx_ingestions_status ON public.ingestions USING btree (status);
CREATE INDEX idx_lectures_subject ON public.lectures USING btree (subject_id);
CREATE INDEX idx_lectures_teacher ON public.lectures USING btree (teacher_id);
CREATE INDEX idx_lectures_week ON public.lectures USING btree (subject_id, week_number);
CREATE INDEX idx_pages_difficulty ON public.pages USING btree (difficulty);
CREATE INDEX idx_pages_paper ON public.pages USING btree (paper_id);
CREATE INDEX idx_pages_question ON public.pages USING btree (question_number);
CREATE INDEX idx_pages_topics ON public.pages USING gin (topics);
CREATE INDEX idx_paper_pages_paper_id ON public.paper_pages USING btree (paper_id);
CREATE INDEX idx_papers_subject ON public.papers USING btree (subject_id);
CREATE INDEX idx_papers_year ON public.papers USING btree (year);
CREATE INDEX idx_question_parts_ms_confidence ON public.question_parts USING btree (ms_link_confidence);
CREATE INDEX idx_question_parts_question ON public.question_parts USING btree (question_id);
CREATE INDEX idx_question_parts_visual_hash ON public.question_parts USING btree (visual_hash);
CREATE INDEX idx_question_tags_question ON public.question_tags USING btree (question_id);
CREATE INDEX idx_question_tags_topic ON public.question_tags USING btree (topic);
CREATE INDEX idx_questions_difficulty ON public.questions USING btree (difficulty);
CREATE INDEX idx_questions_paper ON public.questions USING btree (paper_id);
CREATE INDEX idx_questions_with_url ON public.questions USING btree (paper_id) WHERE (page_pdf_url IS NOT NULL);
CREATE INDEX idx_suggestions_status_created ON public.suggestions USING btree (status, created_at DESC);
CREATE INDEX idx_suggestions_user ON public.suggestions USING btree (user_id);
CREATE INDEX idx_test_items_page ON public.test_items USING btree (page_id);
CREATE INDEX idx_test_items_seq ON public.test_items USING btree (test_id, sequence_order);
CREATE INDEX idx_test_items_test ON public.test_items USING btree (test_id);
CREATE INDEX idx_tests_status ON public.tests USING btree (status);
CREATE INDEX idx_tests_subject ON public.tests USING btree (subject_id);
CREATE INDEX idx_tests_user ON public.tests USING btree (user_id);
CREATE INDEX idx_trusted_devices_trusted ON public.trusted_devices USING btree (user_id, is_trusted) WHERE (is_trusted = true);
CREATE INDEX idx_trusted_devices_user_id ON public.trusted_devices USING btree (user_id);
CREATE INDEX idx_usage_events_created ON public.usage_events USING btree (created_at);
CREATE INDEX idx_usage_events_created_at_btree ON public.usage_events USING btree (created_at);
CREATE INDEX idx_usage_events_feature ON public.usage_events USING btree (feature);
CREATE INDEX idx_usage_events_user ON public.usage_events USING btree (user_id);
CREATE INDEX usage_events_created_at ON public.usage_events USING btree (created_at DESC);
CREATE INDEX usage_events_feature ON public.usage_events USING btree (feature);
CREATE INDEX usage_events_subject_id ON public.usage_events USING btree (subject_id);
CREATE INDEX usage_events_user_id ON public.usage_events USING btree (user_id);
CREATE INDEX idx_usage_meters_user_period ON public.usage_meters USING btree (user_id, period_start DESC);
CREATE INDEX idx_user_permissions_active ON public.user_permissions USING btree (user_id, is_active) WHERE (is_active = true);
CREATE INDEX idx_user_permissions_user ON public.user_permissions USING btree (user_id);
CREATE INDEX idx_user_profiles_email ON public.user_profiles USING btree (email);
CREATE INDEX idx_user_profiles_role ON public.user_profiles USING btree (role);
CREATE INDEX idx_user_profiles_role_type ON public.user_profiles USING btree (role_type);
CREATE INDEX idx_user_sessions_active ON public.user_sessions USING btree (user_id, is_active) WHERE (is_active = true);
CREATE INDEX idx_user_sessions_expires ON public.user_sessions USING btree (expires_at) WHERE (is_active = true);
CREATE INDEX idx_user_sessions_user_id ON public.user_sessions USING btree (user_id);
CREATE INDEX idx_user_subjects_subject ON public.user_subjects USING btree (subject_id);
CREATE INDEX idx_user_subjects_user ON public.user_subjects USING btree (user_id);
CREATE INDEX idx_worksheet_logs_date ON public.worksheet_generation_logs USING btree (generated_at);
CREATE INDEX idx_worksheet_logs_status ON public.worksheet_generation_logs USING btree (status);
CREATE INDEX idx_worksheet_logs_user ON public.worksheet_generation_logs USING btree (user_id);
CREATE INDEX idx_worksheet_items_position ON public.worksheet_items USING btree (worksheet_id, "position");
CREATE INDEX idx_worksheet_items_question ON public.worksheet_items USING btree (question_id);
CREATE INDEX idx_worksheet_items_worksheet ON public.worksheet_items USING btree (worksheet_id);
CREATE INDEX idx_worksheets_user ON public.worksheets USING btree (user_id);

-- ─── Row level security ─────────────────────────────────────────────────────
ALTER TABLE "audit_log" ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Service role can read audit log" ON "audit_log" FOR SELECT USING (((auth.jwt() ->> 'role'::text) = 'service_role'::text));
ALTER TABLE "ingestions" ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Authenticated users can insert ingestions" ON "ingestions" FOR INSERT TO authenticated WITH CHECK (true);
CREATE POLICY "Authenticated users can update ingestions" ON "ingestions" FOR UPDATE TO authenticated USING (true);
CREATE POLICY "Authenticated users can view ingestions" ON "ingestions" FOR SELECT TO authenticated USING (true);
ALTER TABLE "lectures" ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Anyone can view lectures" ON "lectures" FOR SELECT USING (true);
CREATE POLICY "Teachers can delete own lectures" ON "lectures" FOR DELETE USING (((auth.uid() = teacher_id) OR (EXISTS ( SELECT 1
   FROM profiles
  WHERE ((profiles.id = auth.uid()) AND (profiles.role = 'admin'::text))))));
CREATE POLICY "Teachers can insert own lectures" ON "lectures" FOR INSERT WITH CHECK (((auth.uid() = teacher_id) AND (( SELECT profiles.role
   FROM profiles
  WHERE (profiles.id = auth.uid())) = ANY (ARRAY['teacher'::text, 'admin'::text]))));
CREATE POLICY "Teachers can update own lectures" ON "lectures" FOR UPDATE USING (((auth.uid() = teacher_id) AND (EXISTS ( SELECT 1
   FROM profiles
  WHERE ((profiles.id = auth.uid()) AND (profiles.role = ANY (ARRAY['teacher'::text, 'admin'::text])))))));
ALTER TABLE "markschemes" ENABLE ROW LEVEL SECURITY;
CREATE POLICY "dev_all" ON "markschemes" USING (true) WITH CHECK (true);
ALTER TABLE "pages" ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Public read pages" ON "pages" FOR SELECT USING (true);
ALTER TABLE "papers" ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Public read papers" ON "papers" FOR SELECT USING (true);
CREATE POLICY "Service role manages papers" ON "papers" TO service_role USING (true) WITH CHECK (true);
ALTER TABLE "profiles" ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Admins can update any profile" ON "profiles" FOR UPDATE USING ((EXISTS ( SELECT 1
   FROM profiles profiles_1
  WHERE ((profiles_1.id = auth.uid()) AND (profiles_1.role = 'admin'::text)))));
CREATE POLICY "Admins can view all profiles" ON "profiles" FOR SELECT USING (((auth.uid() = id) OR (( SELECT profiles_1.role
   FROM profiles profiles_1
  WHERE (profiles_1.id = auth.uid())) = 'admin'::text)));
CREATE POLICY "Users can insert own profile" ON "profiles" FOR INSERT WITH CHECK ((auth.uid() = id));
CREATE POLICY "Users can update own profile" ON "profiles" FOR UPDATE USING ((auth.uid() = id));
CREATE POLICY "Users can view own profile" ON "profiles" FOR SELECT USING ((auth.uid() = id));
ALTER TABLE "question_parts" ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Authenticated users can view parts" ON "question_parts" FOR SELECT TO authenticated USING (true);
ALTER TABLE "question_tags" ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Public read question_tags" ON "question_tags" FOR SELECT USING (true);
ALTER TABLE "questions" ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Public read questions" ON "questions" FOR SELECT USING (true);
ALTER TABLE "subjects" ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Public read subjects" ON "subjects" FOR SELECT USING (true);
CREATE POLICY "Service role manages subjects" ON "subjects" TO service_role USING (true) WITH CHECK (true);
ALTER TABLE "suggestions" ENABLE ROW LEVEL SECURITY;
CREATE POLICY "anyone can insert suggestions" ON "suggestions" FOR INSERT WITH CHECK (true);
CREATE POLICY "users see own suggestions" ON "suggestions" FOR SELECT USING (((auth.uid() IS NOT NULL) AND (user_id = auth.uid())));
ALTER TABLE "test_items" ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Owner delete test_items" ON "test_items" FOR DELETE USING ((test_id IN ( SELECT tests.id
   FROM tests
  WHERE (tests.user_id = auth.uid()))));
CREATE POLICY "Owner insert test_items" ON "test_items" FOR INSERT WITH CHECK ((test_id IN ( SELECT tests.id
   FROM tests
  WHERE (tests.user_id = auth.uid()))));
CREATE POLICY "Owner read test_items" ON "test_items" FOR SELECT USING ((test_id IN ( SELECT tests.id
   FROM tests
  WHERE (tests.user_id = auth.uid()))));
CREATE POLICY "Owner update test_items" ON "test_items" FOR UPDATE USING ((test_id IN ( SELECT tests.id
   FROM tests
  WHERE (tests.user_id = auth.uid()))));
CREATE POLICY "test_items: owner delete" ON "test_items" FOR DELETE USING ((EXISTS ( SELECT 1
   FROM tests
  WHERE ((tests.id = test_items.test_id) AND (tests.user_id = auth.uid())))));
CREATE POLICY "test_items: owner insert" ON "test_items" FOR INSERT WITH CHECK ((EXISTS ( SELECT 1
   FROM tests
  WHERE ((tests.id = test_items.test_id) AND (tests.user_id = auth.uid())))));
CREATE POLICY "test_items: owner select" ON "test_items" FOR SELECT USING ((EXISTS ( SELECT 1
   FROM tests
  WHERE ((tests.id = test_items.test_id) AND (tests.user_id = auth.uid())))));
CREATE POLICY "test_items: owner update" ON "test_items" FOR UPDATE USING ((EXISTS ( SELECT 1
   FROM tests
  WHERE ((tests.id = test_items.test_id) AND (tests.user_id = auth.uid())))));
ALTER TABLE "tests" ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Owner delete tests" ON "tests" FOR DELETE USING ((auth.uid() = user_id));
CREATE POLICY "Owner insert tests" ON "tests" FOR INSERT WITH CHECK ((auth.uid() = user_id));
CREATE POLICY "Owner read tests" ON "tests" FOR SELECT USING ((auth.uid() = user_id));
CREATE POLICY "Owner update tests" ON "tests" FOR UPDATE USING ((auth.uid() = user_id));
CREATE POLICY "tests: owner delete" ON "tests" FOR DELETE USING ((user_id = auth.uid()));
CREATE POLICY "tests: owner insert" ON "tests" FOR INSERT WITH CHECK ((user_id = auth.uid()));
CREATE POLICY "tests: owner select" ON "tests" FOR SELECT USING ((user_id = auth.uid()));
CREATE POLICY "tests: owner update" ON "tests" FOR UPDATE USING ((user_id = auth.uid()));
ALTER TABLE "topics" ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Public read topics" ON "topics" FOR SELECT USING (true);
ALTER TABLE "trusted_devices" ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Users can update own devices" ON "trusted_devices" FOR UPDATE USING ((auth.uid() = user_id));
CREATE POLICY "Users can view own devices" ON "trusted_devices" FOR SELECT USING ((auth.uid() = user_id));
ALTER TABLE "usage_events" ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Service role full access" ON "usage_events" TO service_role USING (true) WITH CHECK (true);
CREATE POLICY "Service role only" ON "usage_events" USING (false);
CREATE POLICY "Users can insert own events" ON "usage_events" FOR INSERT TO authenticated WITH CHECK (((user_id = auth.uid()) OR (user_id IS NULL)));
ALTER TABLE "usage_meters" ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Users can view own usage" ON "usage_meters" FOR SELECT USING ((auth.uid() = user_id));
ALTER TABLE "user_permissions" ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Service role can manage permissions" ON "user_permissions" USING (((auth.jwt() ->> 'role'::text) = 'service_role'::text));
CREATE POLICY "Users can view own permissions" ON "user_permissions" FOR SELECT USING ((auth.uid() = user_id));
ALTER TABLE "user_profiles" ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Users can insert own profile" ON "user_profiles" FOR INSERT WITH CHECK ((auth.uid() = user_id));
CREATE POLICY "Users can update own profile" ON "user_profiles" FOR UPDATE USING ((auth.uid() = user_id));
CREATE POLICY "Users can view own profile" ON "user_profiles" FOR SELECT USING ((auth.uid() = user_id));
ALTER TABLE "user_sessions" ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Users can delete own sessions" ON "user_sessions" FOR DELETE USING ((auth.uid() = user_id));
CREATE POLICY "Users can view own sessions" ON "user_sessions" FOR SELECT USING ((auth.uid() = user_id));
ALTER TABLE "user_subjects" ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Users can add own subjects" ON "user_subjects" FOR INSERT WITH CHECK ((auth.uid() = user_id));
CREATE POLICY "Users can remove own subjects" ON "user_subjects" FOR DELETE USING ((auth.uid() = user_id));
CREATE POLICY "Users can view own subjects" ON "user_subjects" FOR SELECT USING ((auth.uid() = user_id));
ALTER TABLE "worksheet_generation_logs" ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Users can insert own logs" ON "worksheet_generation_logs" FOR INSERT WITH CHECK ((auth.uid() = user_id));
CREATE POLICY "Users can view own logs" ON "worksheet_generation_logs" FOR SELECT USING ((auth.uid() = user_id));
ALTER TABLE "worksheet_items" ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Owner insert worksheet_items" ON "worksheet_items" FOR INSERT WITH CHECK ((worksheet_id IN ( SELECT worksheets.id
   FROM worksheets
  WHERE (worksheets.user_id = auth.uid()))));
CREATE POLICY "Owner read worksheet_items" ON "worksheet_items" FOR SELECT USING ((worksheet_id IN ( SELECT worksheets.id
   FROM worksheets
  WHERE (worksheets.user_id = auth.uid()))));
ALTER TABLE "worksheets" ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Owner insert worksheets" ON "worksheets" FOR INSERT WITH CHECK ((auth.uid() = user_id));
CREATE POLICY "Owner read worksheets" ON "worksheets" FOR SELECT USING ((auth.uid() = user_id));

-- ─── Triggers ───────────────────────────────────────────────────────────────
CREATE TRIGGER update_profiles_updated_at BEFORE UPDATE ON public.profiles FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_question_parts_updated_at BEFORE UPDATE ON public.question_parts FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER suggestions_set_updated_at BEFORE UPDATE ON public.suggestions FOR EACH ROW EXECUTE FUNCTION set_updated_at();
CREATE TRIGGER update_user_permissions_updated_at BEFORE UPDATE ON public.user_permissions FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_user_profiles_updated_at BEFORE UPDATE ON public.user_profiles FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER trigger_update_session_activity BEFORE UPDATE ON public.user_sessions FOR EACH ROW EXECUTE FUNCTION update_session_activity();

-- ─── Comments ───────────────────────────────────────────────────────────────
COMMENT ON TABLE "audit_log" IS 'Tamper-evident audit log with hash chain';
COMMENT ON TABLE "ingestion_manifests" IS 'Tracks metadata about each paper ingestion batch';
COMMENT ON COLUMN "lectures"."file_url" IS 'Cloudflare R2 public URL. Older rows pointing at Supabase Storage were migrated in Phase E (May 2026).';
COMMENT ON TABLE "pages" IS 'Core table: Each row = one page (question or answer). Topics stored as array for fast queries.';
COMMENT ON COLUMN "pages"."topics" IS 'Array of topic codes (e.g., ["1", "2"]). Use && operator for overlap queries.';
COMMENT ON COLUMN "pages"."qp_page_url" IS 'Cloudflare R2 public URL for the per-question PDF. Migrated from Supabase Storage in Phase B/C (May 2026).';
COMMENT ON COLUMN "pages"."ms_page_url" IS 'Cloudflare R2 public URL for the per-question mark scheme PDF (nullable).';
COMMENT ON TABLE "paper_pages" IS 'Full page renders for visual crop extraction';
COMMENT ON COLUMN "papers"."data_file_url" IS 'Cloudflare R2 public URL for the practical exam data file (e.g. ICT Paper 2 zip).';
COMMENT ON COLUMN "questions"."page_pdf_url" IS 'Cloudflare R2 public URL — mirror of pages.qp_page_url.';
COMMENT ON COLUMN "questions"."ms_pdf_url" IS 'Cloudflare R2 public URL — mirror of pages.ms_page_url (nullable).';
COMMENT ON TABLE "trusted_devices" IS 'Trusted devices for each user';
COMMENT ON TABLE "usage_meters" IS 'Usage tracking per user per period';
COMMENT ON TABLE "user_permissions" IS 'Controls which users can generate worksheets';
COMMENT ON TABLE "user_profiles" IS 'Extended user information and metadata';
COMMENT ON TABLE "user_sessions" IS 'Active user sessions with device tracking';
COMMENT ON TABLE "worksheet_generation_logs" IS 'Audit log of all worksheet generation attempts';
