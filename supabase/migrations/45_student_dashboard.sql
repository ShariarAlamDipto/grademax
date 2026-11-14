-- 45_student_dashboard.sql
--
-- NOT APPLIED YET (written 14 Nov 2026). Run it in the Supabase SQL editor when
-- the student dashboard is approved. Until then the dashboard loads, lets a
-- student add subjects, and shows a notice where saving progress needs these
-- tables.
--
-- The storage behind a student's personal dashboard:
--   1. profiles            + exam target, leaderboard consent and nickname
--   2. user_subjects       + target grade, exam session (table already exists)
--   3. paper_completions   the "I completed this paper" box, with optional score
--   4. question_solves     a question ticked as solved
--   5. study_sessions      minutes from the study timer
--   6. student_exam_dates  the student's own exam timetable (countdowns)
--   7. community_contributions  corrections and solutions sent in by students
--   8. completion_points() and subject_leaderboard()  points and rankings
--
-- Additive only: no existing row or column is changed. Undo steps are at the end.
-- (paper_attempts and papers_catalog, which the old dashboard widgets read,
-- never existed in this database; paper_completions replaces them and points at
-- the real `papers` rows.)

begin;

-- 1. Profile ------------------------------------------------------------------
alter table public.profiles
  add column if not exists target_session     text,
  add column if not exists leaderboard_opt_in boolean not null default false,
  add column if not exists leaderboard_name   text;

alter table public.profiles
  drop constraint if exists profiles_leaderboard_name_len,
  add constraint profiles_leaderboard_name_len
    check (leaderboard_name is null or char_length(btrim(leaderboard_name)) between 2 and 24);

-- 2. A student's subjects -----------------------------------------------------
alter table public.user_subjects
  add column if not exists target_grade text,
  add column if not exists exam_session text;

-- Inserts from the browser may omit user_id; default it to the signed-in user.
alter table public.user_subjects alter column user_id set default auth.uid();

drop policy if exists "Users can update own subjects" on public.user_subjects;
create policy "Users can update own subjects" on public.user_subjects
  for update using (auth.uid() = user_id) with check (auth.uid() = user_id);

-- 3. Completed papers ---------------------------------------------------------
create table if not exists public.paper_completions (
  user_id      uuid not null default auth.uid() references auth.users (id) on delete cascade,
  paper_id     uuid not null references public.papers (id) on delete cascade,
  -- Copied from the paper so a subject's leaderboard needs no join.
  subject_id   uuid not null references public.subjects (id) on delete cascade,
  completed_at timestamptz not null default now(),
  -- The score is optional: ticking the box alone still counts as completed.
  raw_score    numeric(6, 1) check (raw_score is null or raw_score >= 0),
  max_score    numeric(6, 1) check (max_score is null or max_score > 0),
  percentage   numeric(5, 1) generated always as (
                 case when raw_score is not null and max_score is not null
                      then round(least(raw_score / max_score, 1) * 100, 1) end
               ) stored,
  -- Sat under exam conditions (full time, no notes).
  timed        boolean not null default false,
  minutes      integer check (minutes is null or minutes between 1 and 600),
  primary key (user_id, paper_id),
  check (raw_score is null or max_score is null or raw_score <= max_score)
);

create index if not exists paper_completions_subject_idx on public.paper_completions (subject_id, completed_at);
create index if not exists paper_completions_user_idx on public.paper_completions (user_id, completed_at);

alter table public.paper_completions enable row level security;

create policy paper_completions_select_own on public.paper_completions
  for select using (auth.uid() = user_id);
create policy paper_completions_insert_own on public.paper_completions
  for insert with check (auth.uid() = user_id);
create policy paper_completions_update_own on public.paper_completions
  for update using (auth.uid() = user_id) with check (auth.uid() = user_id);
create policy paper_completions_delete_own on public.paper_completions
  for delete using (auth.uid() = user_id);

-- 4. Solved questions ---------------------------------------------------------
create table if not exists public.question_solves (
  user_id     uuid not null default auth.uid() references auth.users (id) on delete cascade,
  -- pages.id of the question (the tools' question rows live in pages).
  question_id uuid not null references public.pages (id) on delete cascade,
  solved_at   timestamptz not null default now(),
  primary key (user_id, question_id)
);

alter table public.question_solves enable row level security;

create policy question_solves_select_own on public.question_solves
  for select using (auth.uid() = user_id);
create policy question_solves_insert_own on public.question_solves
  for insert with check (auth.uid() = user_id);
create policy question_solves_delete_own on public.question_solves
  for delete using (auth.uid() = user_id);

-- 5. Study time ---------------------------------------------------------------
create table if not exists public.study_sessions (
  id         uuid primary key default gen_random_uuid(),
  user_id    uuid not null default auth.uid() references auth.users (id) on delete cascade,
  subject_id uuid references public.subjects (id) on delete set null,
  started_at timestamptz not null default now(),
  minutes    integer not null check (minutes between 1 and 600)
);

create index if not exists study_sessions_user_idx on public.study_sessions (user_id, started_at);

alter table public.study_sessions enable row level security;

create policy study_sessions_select_own on public.study_sessions
  for select using (auth.uid() = user_id);
create policy study_sessions_insert_own on public.study_sessions
  for insert with check (auth.uid() = user_id);
create policy study_sessions_delete_own on public.study_sessions
  for delete using (auth.uid() = user_id);

-- 6. The student's exam timetable ---------------------------------------------
create table if not exists public.student_exam_dates (
  id         uuid primary key default gen_random_uuid(),
  user_id    uuid not null default auth.uid() references auth.users (id) on delete cascade,
  subject_id uuid references public.subjects (id) on delete cascade,
  label      text not null check (char_length(label) between 1 and 80),
  exam_date  date not null
);

create index if not exists student_exam_dates_user_idx on public.student_exam_dates (user_id, exam_date);

alter table public.student_exam_dates enable row level security;

create policy student_exam_dates_all_own on public.student_exam_dates
  for all using (auth.uid() = user_id) with check (auth.uid() = user_id);

-- 7. Community contributions --------------------------------------------------
create table if not exists public.community_contributions (
  id          uuid primary key default gen_random_uuid(),
  user_id     uuid not null default auth.uid() references auth.users (id) on delete cascade,
  kind        text not null check (kind in ('wrong_mark_scheme', 'topic_tag', 'worked_solution', 'missing_paper')),
  -- What the contribution is about: a pages.id, a papers.id or free text.
  target_ref  text,
  body        text not null check (char_length(body) between 10 and 4000),
  status      text not null default 'pending' check (status in ('pending', 'accepted', 'rejected')),
  reviewed_by uuid references auth.users (id),
  reviewed_at timestamptz,
  created_at  timestamptz not null default now()
);

create index if not exists community_contributions_user_idx on public.community_contributions (user_id, status);
create index if not exists community_contributions_queue_idx on public.community_contributions (status, created_at);

alter table public.community_contributions enable row level security;

-- A student sees and creates only their own rows, always as 'pending'.
-- Accepting or rejecting is done by admins through the service role.
create policy community_contributions_select_own on public.community_contributions
  for select using (auth.uid() = user_id);
create policy community_contributions_insert_own on public.community_contributions
  for insert with check (auth.uid() = user_id and status = 'pending' and reviewed_by is null);

-- 8. Points and leaderboards --------------------------------------------------
-- Progression points for one completed paper. MUST match completionPoints() in
-- src/lib/rewards/points.ts: 20 for finishing, up to 30 for the score, 5 for
-- sitting it timed.
create or replace function public.completion_points(percentage numeric, timed boolean)
returns integer
language sql
immutable
as $$
  select 20
       + coalesce(round(least(greatest(percentage, 0), 100) * 0.3), 0)::integer
       + case when timed then 5 else 0 end;
$$;

-- Ranking by progression points for one subject (or every subject when
-- p_subject_id is null), over all time or since p_since.
--
-- Only students who opted in appear, under their chosen nickname (or first name
-- and initial). No email or user id is returned. The caller always gets their
-- own row, flagged is_me, even if they have not opted in: it is visible to
-- them alone.
create or replace function public.subject_leaderboard(
  p_subject_id uuid default null,
  p_since      timestamptz default null,
  p_max_rows   int default 20
)
returns table (rank bigint, display_name text, papers bigint, points bigint, average_percentage numeric, is_me boolean)
language sql
stable
security definer
set search_path = public
as $$
  with scored as (
    select c.user_id,
           count(*)                                                as papers,
           sum(completion_points(c.percentage, c.timed))::bigint   as points,
           round(avg(c.percentage), 1)                             as average_percentage
    from paper_completions c
    where (p_subject_id is null or c.subject_id = p_subject_id)
      and (p_since is null or c.completed_at >= p_since)
    group by c.user_id
  ),
  visible as (
    select s.*, p.full_name, p.leaderboard_name
    from scored s
    join profiles p on p.id = s.user_id
    where p.leaderboard_opt_in or s.user_id = auth.uid()
  ),
  ranked as (
    select v.*, row_number() over (order by v.points desc, v.papers desc, v.user_id) as rank
    from visible v
  )
  select r.rank,
         coalesce(
           nullif(btrim(r.leaderboard_name), ''),
           nullif(split_part(btrim(r.full_name), ' ', 1), '')
             || coalesce(' ' || nullif(left(split_part(btrim(r.full_name), ' ', 2), 1), '') || '.', ''),
           'Student'
         ) as display_name,
         r.papers,
         r.points,
         r.average_percentage,
         r.user_id = auth.uid() as is_me
  from ranked r
  where r.rank <= greatest(1, least(p_max_rows, 100)) or r.user_id = auth.uid()
  order by r.rank;
$$;

revoke all on function public.subject_leaderboard(uuid, timestamptz, int) from public, anon;
grant execute on function public.subject_leaderboard(uuid, timestamptz, int) to authenticated;

commit;

-- Undo:
--   drop function if exists public.subject_leaderboard(uuid, timestamptz, int);
--   drop function if exists public.completion_points(numeric, boolean);
--   drop table if exists public.community_contributions, public.student_exam_dates,
--     public.study_sessions, public.question_solves, public.paper_completions;
--   drop policy if exists "Users can update own subjects" on public.user_subjects;
--   alter table public.user_subjects alter column user_id drop default,
--     drop column if exists target_grade, drop column if exists exam_session;
--   alter table public.profiles drop constraint if exists profiles_leaderboard_name_len,
--     drop column if exists target_session, drop column if exists leaderboard_opt_in,
--     drop column if exists leaderboard_name;
