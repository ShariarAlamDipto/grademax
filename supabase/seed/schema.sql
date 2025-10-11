-- GradeMax UUID Schema (Idempotent)
-- Run this entire script in Supabase SQL Editor

-- CLEAN SLATE in FK-safe order
drop table if exists worksheet_items cascade;
drop table if exists worksheets cascade;
drop table if exists question_topics cascade;
drop table if exists markschemes cascade;
drop table if exists questions cascade;
drop table if exists papers cascade;
drop table if exists topics cascade;
drop table if exists subjects cascade;

-- Enable extensions
create extension if not exists "vector";
create extension if not exists "pgcrypto";

-- Subjects table
create table subjects (
  id uuid primary key default gen_random_uuid(),
  board text not null default 'Edexcel',
  level text not null check (level in ('IGCSE','IAL')),
  code text not null,
  name text not null,
  color text,
  created_at timestamptz default now(),
  unique(board, level, code)
);

-- Topics table
create table topics (
  id uuid primary key default gen_random_uuid(),
  subject_id uuid not null references subjects(id) on delete cascade,
  code text not null,
  name text not null,
  spec_ref text,
  content text,
  created_at timestamptz default now(),
  unique(subject_id, code)
);

-- Papers table
create table papers (
  id uuid primary key default gen_random_uuid(),
  subject_id uuid not null references subjects(id) on delete cascade,
  paper_number text not null,
  year int not null,
  season text not null,
  pdf_url text,
  markscheme_pdf_url text,
  created_at timestamptz default now(),
  unique(subject_id, year, season, paper_number)
);

-- Questions table
create table questions (
  id uuid primary key default gen_random_uuid(),
  paper_id uuid not null references papers(id) on delete cascade,
  question_number text not null,
  text text not null,
  diagram_urls text[],
  marks int,
  difficulty int check (difficulty between 1 and 3),
  embedding vector(384),
  created_at timestamptz default now()
);

-- Markschemes table
create table markschemes (
  id uuid primary key default gen_random_uuid(),
  question_id uuid not null references questions(id) on delete cascade,
  text text not null,
  marks_breakdown jsonb,
  created_at timestamptz default now(),
  unique(question_id)
);

-- Question_Topics junction table
create table question_topics (
  id uuid primary key default gen_random_uuid(),
  question_id uuid not null references questions(id) on delete cascade,
  topic_id uuid not null references topics(id) on delete cascade,
  confidence real default 1.0,
  created_at timestamptz default now(),
  unique(question_id, topic_id)
);

-- Worksheets table
create table worksheets (
  id uuid primary key default gen_random_uuid(),
  user_id uuid,
  params jsonb,
  created_at timestamptz default now()
);

-- Worksheet_Items table
create table worksheet_items (
  worksheet_id uuid references worksheets(id) on delete cascade,
  question_id uuid references questions(id) on delete cascade,
  position int,
  primary key (worksheet_id, question_id)
);

-- Indexes for performance
create index idx_topics_subject on topics(subject_id);
create index idx_papers_subject on papers(subject_id);
create index idx_questions_paper on questions(paper_id);
create index idx_questions_diff on questions(difficulty);
create index idx_qt_question on question_topics(question_id);
create index idx_qt_topic on question_topics(topic_id);

-- Vector similarity index (IVFFlat)
create index idx_questions_embedding on questions
using ivfflat (embedding vector_cosine_ops) with (lists = 100);

-- Enable RLS on all tables
alter table subjects enable row level security;
alter table topics enable row level security;
alter table papers enable row level security;
alter table questions enable row level security;
alter table markschemes enable row level security;
alter table question_topics enable row level security;
alter table worksheets enable row level security;
alter table worksheet_items enable row level security;

-- Drop existing policies (idempotent)
drop policy if exists "dev_all" on subjects;
drop policy if exists "dev_all" on topics;
drop policy if exists "dev_all" on papers;
drop policy if exists "dev_all" on questions;
drop policy if exists "dev_all" on markschemes;
drop policy if exists "dev_all" on question_topics;
drop policy if exists "dev_all" on worksheets;
drop policy if exists "dev_all" on worksheet_items;

-- Create permissive policies (dev mode)
create policy "dev_all" on subjects for all using (true) with check (true);
create policy "dev_all" on topics for all using (true) with check (true);
create policy "dev_all" on papers for all using (true) with check (true);
create policy "dev_all" on questions for all using (true) with check (true);
create policy "dev_all" on markschemes for all using (true) with check (true);
create policy "dev_all" on question_topics for all using (true) with check (true);
create policy "dev_all" on worksheets for all using (true) with check (true);
create policy "dev_all" on worksheet_items for all using (true) with check (true);

-- Verification
select 
  tablename, 
  hasindexes, 
  rowsecurity 
from pg_tables 
where schemaname = 'public' 
  and tablename in ('subjects', 'topics', 'papers', 'questions', 'markschemes', 'question_topics', 'worksheets', 'worksheet_items')
order by tablename;
