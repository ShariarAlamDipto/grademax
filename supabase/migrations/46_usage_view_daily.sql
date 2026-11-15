-- 46: the Content and Data quality reports stop reading usage_events.
-- Run after 44. Re-runnable. Adds one small table, extends the usage trigger,
-- replaces admin_content and admin_data_quality, and drops one unused insert
-- policy on usage_events. Takes a share lock on usage_events for the fill
-- (about 15 s on live data); paper opens recorded meanwhile wait for it.
--
-- Found on live data (15 Nov 2026): both reports read every paper_view row of
-- the period from usage_events (150k rows for 30 days, 310k for 90; the table
-- is 257 MB and the database has 224 MB of cache). Warm that took 1.5-4 s;
-- cold it took 8-13 s, past the API limit of 8 s, so Content failed at its
-- default 30-day range and Data quality failed at 90 days.
--
-- usage_daily (migration 44) already has paper opens per day, subject and
-- title, but not the document (QP/MS) or the view (single/split), and at one
-- row per title it is 59 MB. usage_view_daily holds one row per Dhaka day,
-- subject, document and view: a few thousand rows.
--
-- Days are Dhaka days, as in usage_daily. The admin API always asks for
-- Asia/Dhaka (REPORT_TZ), so the report days and the summary days agree.

begin;

create table if not exists public.usage_view_daily (
  day      date    not null,
  subject  text    not null default '',   -- '' when the row named none
  doc      text    not null default '',   -- metadata.doc: qp, ms or ''
  view     text    not null default '',   -- metadata.view: split, single or ''
  n        integer not null default 0 check (n >= 0),
  primary key (day, subject, doc, view)
);
-- Only the service role reads it (the admin API); no policies = no client access.
alter table public.usage_view_daily enable row level security;

-- Rows inserted while this runs wait for the lock, then go through the new
-- trigger function, so the fill below and the trigger cannot double count.
lock table public.usage_events in share mode;

-- As migration 44, plus the paper_view summary by document and view.
create or replace function public.usage_daily_bump() returns trigger
language plpgsql
security definer
set search_path = public
as $$
begin
  insert into public.usage_daily as d (day, feature, subject, title, n)
  values ((new.created_at at time zone 'Asia/Dhaka')::date, new.feature, coalesce(new.subject_name, ''),
          case when new.feature = 'paper_view' then coalesce(nullif(new.metadata->>'title', ''), 'Unknown') else '' end,
          1)
  on conflict (day, feature, subject, title) do update set n = d.n + 1;

  if new.feature = 'paper_view' then
    insert into public.usage_view_daily as v (day, subject, doc, view, n)
    values ((new.created_at at time zone 'Asia/Dhaka')::date, coalesce(new.subject_name, ''),
            coalesce(new.metadata->>'doc', ''), coalesce(new.metadata->>'view', ''), 1)
    on conflict (day, subject, doc, view) do update set n = v.n + 1;
  end if;
  return null;
end;
$$;

truncate public.usage_view_daily;
insert into public.usage_view_daily (day, subject, doc, view, n)
select (created_at at time zone 'Asia/Dhaka')::date, coalesce(subject_name, ''),
       coalesce(metadata->>'doc', ''), coalesce(metadata->>'view', ''), count(*)
from public.usage_events
where feature = 'paper_view'
group by 1, 2, 3, 4;

-- Content: what students study. Page paths and downloads follow the country
-- filter; server-side paper opens have no country, so they always cover every
-- country.
create or replace function public.admin_content(
  p_days integer default 30, p_tz text default 'Asia/Dhaka',
  p_country text default null, p_from date default null, p_to date default null
) returns jsonb
language sql
stable
security definer
set search_path = public
as $$
with b as (select * from public.analytics_bounds(p_days, p_tz, p_from, p_to)),
v as (select sv.* from b, public.analytics_visits(b.since, b.until, p_country) sv where sv.path like '/past-papers/%'),
subject_views as (
  select split_part(path, '/', 3) as subject,
         substring(path from '^/past-papers/[^/]+/((19|20)[0-9]{2})') as year,
         visitor_id, engaged_seconds
  from v where split_part(path, '/', 3) not in ('', 'cambridge')
),
-- /igcse/physics/2026/may-jun/Physics_2026_May-Jun_Paper_1P_QP.pdf
-- /cambridge/igcse/Co-ordinated_Sciences/2016/may-jun/..._QP.pdf
dl as (
  select ev.visitor_id, ev.label,
         case when split_part(ev.label, '/', 2) = 'cambridge'
              then 'Cambridge ' || split_part(ev.label, '/', 3) else split_part(ev.label, '/', 2) end as level,
         case when split_part(ev.label, '/', 2) = 'cambridge'
              then split_part(ev.label, '/', 4) else split_part(ev.label, '/', 3) end as subject,
         substring(ev.label from '/((19|20)[0-9]{2})/') as year,
         substring(ev.label from '/(may-jun|oct-nov|jan|feb-mar|june|nov)/') as series,
         case substring(upper(ev.label) from '_([A-Z]{2})\.PDF$')
              when 'QP' then 'Question paper' when 'MS' then 'Mark scheme' when 'IN' then 'Insert'
              when 'ER' then 'Examiner report' when 'GT' then 'Grade thresholds' else 'Other' end as kind
  from b, public.analytics_events(b.since, b.until, p_country) ev
  where ev.name = 'download' and ev.label like '/%'
),
-- Paper opens come from the daily summaries (Dhaka days), not from the
-- ~500k-row usage_events table.
pv as (
  select u.subject, u.doc, u.view, u.n
  from b, public.usage_view_daily u
  where u.day between b.first_day and b.last_day
),
pt as (
  select u.title, sum(u.n) as n
  from b, public.usage_daily u
  where u.feature = 'paper_view' and u.day between b.first_day and b.last_day
  group by 1 order by 2 desc limit 25
)
select jsonb_build_object(
  'first_day', (select first_day from b), 'last_day', (select last_day from b), 'partial', (select partial from b),
  'subjects', (select coalesce(jsonb_agg(jsonb_build_object('subject', subject, 'views', n, 'visitors', u, 'avg_engaged', eng) order by n desc), '[]'::jsonb)
    from (select subject, count(*) as n, count(distinct visitor_id) as u,
                 round(avg(engaged_seconds) filter (where engaged_seconds > 0)) as eng
          from subject_views group by 1 order by 2 desc limit 30) t),
  'years', (select coalesce(jsonb_agg(jsonb_build_object('year', year, 'views', n) order by year desc), '[]'::jsonb)
    from (select year, count(*) as n from subject_views where year is not null group by 1) t),
  'downloads', jsonb_build_object(
    'total',     (select count(*) from dl),
    'visitors',  (select count(distinct visitor_id) from dl),
    'by_level',  (select coalesce(jsonb_agg(jsonb_build_object('name', level, 'count', n) order by n desc), '[]'::jsonb)
                  from (select level, count(*) as n from dl group by 1) t),
    'by_kind',   (select coalesce(jsonb_agg(jsonb_build_object('name', kind, 'count', n) order by n desc), '[]'::jsonb)
                  from (select kind, count(*) as n from dl group by 1) t),
    'by_subject', (select coalesce(jsonb_agg(jsonb_build_object('name', subject, 'count', n, 'visitors', u) order by n desc), '[]'::jsonb)
                  from (select subject, count(*) as n, count(distinct visitor_id) as u from dl group by 1 order by 2 desc limit 20) t),
    'by_year',   (select coalesce(jsonb_agg(jsonb_build_object('name', year, 'count', n) order by year desc), '[]'::jsonb)
                  from (select year, count(*) as n from dl where year is not null group by 1) t),
    'by_series', (select coalesce(jsonb_agg(jsonb_build_object('name', series, 'count', n) order by n desc), '[]'::jsonb)
                  from (select series, count(*) as n from dl where series is not null group by 1) t)),
  'paper_opens', jsonb_build_object(
    'total',      (select coalesce(sum(n), 0) from pv),
    'by_subject', (select coalesce(jsonb_agg(jsonb_build_object('name', subject_name, 'count', n) order by n desc), '[]'::jsonb)
                   from (select case when subject = '' then 'Unknown' else subject end as subject_name, sum(n) as n from pv group by 1 order by 2 desc limit 20) t),
    'by_doc',     (select coalesce(jsonb_agg(jsonb_build_object('name', d, 'count', n) order by n desc), '[]'::jsonb)
                   from (select case doc when 'qp' then 'Question paper' when 'ms' then 'Mark scheme' else 'Other' end as d, sum(n) as n from pv group by 1) t),
    'by_view',    (select coalesce(jsonb_agg(jsonb_build_object('name', w, 'count', n) order by n desc), '[]'::jsonb)
                   from (select case view when 'split' then 'Side by side (QP + MS)' else 'Single' end as w, sum(n) as n from pv group by 1) t),
    'top_papers', (select coalesce(jsonb_agg(jsonb_build_object('title', title, 'count', n) order by n desc), '[]'::jsonb)
                   from pt))
);
$$;

-- Data quality: how far to trust the dashboard (as 42; the paper-open count
-- now comes from the summary).
create or replace function public.admin_data_quality(
  p_days integer default 30, p_tz text default 'Asia/Dhaka',
  p_from date default null, p_to date default null
) returns jsonb
language sql
stable
security definer
set search_path = public
as $$
with b as (select * from public.analytics_bounds(p_days, p_tz, p_from, p_to)),
v as (select sv.* from b, public.analytics_visits(b.since, b.until, null) sv),
e as (select ev.* from b, public.analytics_events(b.since, b.until, null) ev),
s as (select f.* from b, public.analytics_session_facts(b.since, b.until, null) f),
s_ev as (select session_id, count(*) as n, count(*) filter (where name = 'download') as downloads from e group by 1),
recon as (
  select 'Paper opens' as name, 'Server: /viewer page renders (usage_events)' as source,
         (select coalesce(sum(u.n), 0) from b, public.usage_view_daily u where u.day between b.first_day and b.last_day) as truth,
         (select count(*) from v where v.path = '/viewer') as tracked, 'Viewer page views seen by the tracker' as tracked_label, 1 as ord
  union all
  select 'Worksheets', 'worksheets table',
         (select count(*) from b, public.worksheets w where w.created_at >= b.since and w.created_at < b.until),
         (select count(*) from e where e.name = 'worksheet_generated'), 'worksheet_generated events', 2
  union all
  select 'Saved tests', 'tests table',
         (select count(*) from b, public.tests t where t.created_at >= b.since and t.created_at < b.until),
         (select count(*) from e where e.name = 'test_generated'), 'test_generated events', 3
  union all
  select 'New accounts', 'auth.users',
         (select count(*) from b, auth.users u where u.created_at >= b.since and u.created_at < b.until),
         (select count(*) from e where e.name = 'sign_up'), 'sign_up events', 4
  union all
  select 'Orders', 'store_orders table',
         (select count(*) from b, public.store_orders o where o.created_at >= b.since and o.created_at < b.until),
         (select count(*) from e where e.name = 'order_placed'), 'order_placed events', 5
)
select jsonb_build_object(
  'first_day', (select first_day from b), 'last_day', (select last_day from b), 'partial', (select partial from b),
  'reconciliation', (select jsonb_agg(jsonb_build_object('name', name, 'source', source, 'truth', truth,
                       'tracked', tracked, 'tracked_label', tracked_label,
                       'ratio', round(100.0 * tracked / nullif(truth, 0), 1)) order by ord) from recon),
  'coverage', jsonb_build_object(
    'page_views',        (select count(*) from v),
    'country_known',     (select round(100.0 * count(*) filter (where country is not null) / nullif(count(*), 0), 1) from v),
    'engagement_known',  (select round(100.0 * count(*) filter (where engaged_seconds > 0) / nullif(count(*), 0), 1) from v),
    'scroll_known',      (select round(100.0 * count(*) filter (where scroll_pct is not null) / nullif(count(*), 0), 1) from v),
    'landing_with_lcp',  (select round(100.0 * count(*) filter (where lcp_ms is not null) / nullif(count(*), 0), 1) from v where is_session_start),
    'events_with_visit', (select round(100.0 * count(*) filter (where session_id is not null) / nullif(count(*), 0), 1) from e)),
  -- One page, no active time, no clicks, no page-speed report: what an
  -- automated page load (or a tab opened and never looked at) leaves behind.
  'no_interaction_by_country', (select coalesce(jsonb_agg(jsonb_build_object('country', country, 'sessions', n,
        'no_interaction', z, 'share', round(100.0 * z / n, 1)) order by n desc), '[]'::jsonb)
    from (select s.country, count(*) as n,
                 count(*) filter (where s.pages = 1 and s.engaged = 0 and coalesce(se.n, 0) = 0) as z
          from s left join s_ev se on se.session_id = s.session_id
          group by 1 order by 2 desc limit 15) t),
  -- Possible scraping: very many pages or downloads in one visit.
  'heavy_sessions', (select coalesce(jsonb_agg(jsonb_build_object('started', started_at, 'pages', pages, 'downloads', downloads,
        'minutes', minutes, 'engaged', engaged, 'country', country, 'device', device, 'browser', browser, 'channel', channel) order by pages desc), '[]'::jsonb)
    from (select s.started_at, s.pages, coalesce(se.downloads, 0) as downloads, s.engaged, s.country, s.channel,
                 round(extract(epoch from (select max(x.created_at) - min(x.created_at) from v x where x.session_id = s.session_id)) / 60) as minutes,
                 (select max(x.device) from v x where x.session_id = s.session_id and x.is_session_start) as device,
                 (select max(x.browser) from v x where x.session_id = s.session_id and x.is_session_start) as browser
          from s left join s_ev se on se.session_id = s.session_id
          where s.pages >= 60 or coalesce(se.downloads, 0) >= 30
          order by s.pages desc limit 20) t),
  'freshness', jsonb_build_object(
    'last_page_view',  (select max(created_at) from public.site_visits),
    'last_event',      (select max(created_at) from public.site_events),
    'views_last_hour', (select count(*) from public.site_visits where created_at >= now() - interval '1 hour'),
    'views_last_day',  (select count(*) from public.site_visits where created_at >= now() - interval '24 hours'),
    'tracking_since',  (select min(created_at) from public.site_visits))
);
$$;

-- Safety net. PostgREST applies a function's own statement_timeout to the
-- request, so a slow cold read ends with an answer, not the 8 s API limit.
alter function public.admin_content(integer, text, text, date, date) set statement_timeout = '20s';
alter function public.admin_data_quality(integer, text, date, date)  set statement_timeout = '20s';
alter function public.admin_usage(integer)                           set statement_timeout = '20s';

-- Every usage_events row is written by the server with the service role
-- (src/lib/trackUsage.ts). This policy let any signed-in user insert rows
-- straight through the API, including rows with no user, and so inflate the
-- usage numbers. Nothing in the app uses it.
drop policy if exists "Users can insert own events" on public.usage_events;

revoke all on function public.usage_daily_bump() from public, anon, authenticated;
revoke all on function public.admin_content(integer, text, text, date, date)       from public, anon, authenticated;
revoke all on function public.admin_data_quality(integer, text, date, date)        from public, anon, authenticated;
grant execute on function public.admin_content(integer, text, text, date, date)    to service_role;
grant execute on function public.admin_data_quality(integer, text, date, date)     to service_role;

commit;
