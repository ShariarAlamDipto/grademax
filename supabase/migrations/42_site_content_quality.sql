-- 42: engaged visits, a Content report and a Data quality report. Run after 41.
-- Replaces analytics_totals and admin_countries (adds engaged visits) and adds
-- admin_content and admin_data_quality. No table changes; re-runnable.
--
-- Found on live data (26 Oct): automated or never-viewed page loads (e.g. 64%
-- of visits from China had one page, no active time and no clicks) inflated
-- raw visitor counts, and the tracker saw only about a third of the server's
-- paper opens. "Engaged visits" and the reconciliation table make both visible.

begin;

-- Headline numbers (as 38, plus engaged visits and engagement rate); used for the current and the previous period.
create or replace function public.analytics_totals(p_since timestamptz, p_until timestamptz, p_country text)
returns jsonb
language sql
stable
security definer
set search_path = public
as $$
  with v as (select * from public.analytics_visits(p_since, p_until, p_country)),
       s as (select * from public.analytics_session_facts(p_since, p_until, p_country))
  select jsonb_build_object(
    'visitors',            (select count(distinct visitor_id) from v),
    'new_visitors',        (select count(distinct visitor_id) from v where is_new_visitor),
    'signed_in_visitors',  (select count(distinct visitor_id) from v where signed_in),
    'views',               (select count(*) from v),
    'sessions',            (select count(*) from s),
    'bounce_rate',         (select round(100.0 * count(*) filter (where bounced) / nullif(count(*), 0), 1) from s),
    'pages_per_session',   (select round(avg(pages), 2) from s),
    'avg_session_seconds', (select round(avg(engaged)) from s),
    'avg_engaged_seconds', (select round(avg(engaged_seconds)) from v where engaged_seconds > 0),
    'unknown_country',     (select count(distinct visitor_id) from v where country is null),
    -- Engaged visit (GA4's rule): 10+ active seconds, 2+ pages, or any click,
    -- download, sign-in or other event. Unseen background tabs and most
    -- automated page loads are not engaged.
    'engaged_sessions',    (select count(*) from s where s.engaged >= 10 or s.pages >= 2
                              or exists (select 1 from public.site_events e where e.session_id = s.session_id)),
    'engagement_rate',     (select round(100.0 * count(*) filter (where s.engaged >= 10 or s.pages >= 2
                              or exists (select 1 from public.site_events e where e.session_id = s.session_id)) / nullif(count(*), 0), 1) from s)
  );
$$;

-- Countries (as 41, plus each country's engagement rate).
create or replace function public.admin_countries(
  p_days integer default 30, p_tz text default 'Asia/Dhaka',
  p_from date default null, p_to date default null
) returns jsonb
language sql
stable
security definer
set search_path = public
as $$
with b as (select * from public.analytics_bounds(p_days, p_tz, p_from, p_to)),
v  as (select sv.*, coalesce(sv.country, '??') as cc from b, public.analytics_visits(b.since, b.until, null) sv),
pv as (select coalesce(sv.country, '??') as cc, sv.visitor_id from b, public.analytics_visits(b.prev_since, b.prev_until, null) sv),
s  as (select f.* from b, public.analytics_session_facts(b.since, b.until, null) f),
e  as (select ev.*, coalesce(ev.country, '??') as cc from b, public.analytics_events(b.since, b.until, null) ev),
si as (select x.* from b, public.analytics_sign_ins(b.since, b.until, null) x),
total as (select count(distinct visitor_id) as n from v),
rows as (
  select v.cc, count(distinct v.visitor_id) as visitors, count(*) as views,
         round(avg(v.engaged_seconds) filter (where v.engaged_seconds > 0)) as avg_engaged
  from v group by v.cc
),
sess as (
  select s.country as cc, count(*) as sessions,
         round(100.0 * count(*) filter (where s.bounced) / nullif(count(*), 0), 1) as bounce_rate,
         round(100.0 * count(*) filter (where s.engaged >= 10 or s.pages >= 2
               or exists (select 1 from public.site_events x where x.session_id = s.session_id)) / nullif(count(*), 0), 1) as engagement_rate
  from s group by 1
),
ev as (
  select cc,
         count(*) filter (where name = 'download')                       as downloads,
         count(*) filter (where name = 'order_placed')                   as orders,
         count(*) filter (where name in ('worksheet_generated', 'test_generated')) as generations
  from e group by 1
),
sign as (select country as cc, count(*) as sign_ins, count(*) filter (where new_account) as sign_ups from si group by 1),
prev as (select cc, count(distinct visitor_id) as visitors from pv group by 1),
top_pages as (
  select cc, jsonb_agg(jsonb_build_object('path', path, 'views', n) order by n desc) as pages
  from (select cc, path, count(*) as n, row_number() over (partition by cc order by count(*) desc) as r
        from v group by cc, path) t
  where r <= 5 group by cc
),
top5 as (select cc from rows order by visitors desc limit 5),
days as (select d::date as day from b, generate_series(b.first_day, b.last_day, interval '1 day') d),
trend_counts as (
  select t5.cc, d.day, count(distinct v.visitor_id) as n
  from days d cross join top5 t5
  left join v on v.cc = t5.cc and (v.created_at at time zone p_tz)::date = d.day
  group by 1, 2
)
select jsonb_build_object(
  'first_day', (select first_day from b), 'last_day', (select last_day from b), 'partial', (select partial from b),
  'total_visitors', (select n from total),
  'unknown_visitors', (select coalesce(max(visitors), 0) from rows where cc = '??'),
  'countries', (select coalesce(jsonb_agg(jsonb_build_object(
      'country', r.cc, 'visitors', r.visitors, 'views', r.views, 'avg_engaged', r.avg_engaged,
      'share', round(100.0 * r.visitors / nullif((select n from total), 0), 1),
      'sessions', coalesce(se.sessions, 0), 'bounce_rate', se.bounce_rate, 'engagement_rate', se.engagement_rate,
      'downloads', coalesce(ev.downloads, 0), 'sign_ins', coalesce(sg.sign_ins, 0),
      'sign_ups', coalesce(sg.sign_ups, 0), 'orders', coalesce(ev.orders, 0),
      'generations', coalesce(ev.generations, 0),
      'prev_visitors', coalesce(p.visitors, 0),
      'change', case when coalesce(p.visitors, 0) = 0 then null
                     else round(100.0 * (r.visitors - p.visitors) / p.visitors, 1) end,
      'top_pages', coalesce(tp.pages, '[]'::jsonb)
    ) order by r.visitors desc), '[]'::jsonb)
    from rows r
    left join sess se      on se.cc = r.cc
    left join ev           on ev.cc = r.cc
    left join sign sg      on sg.cc = r.cc
    left join prev p       on p.cc = r.cc
    left join top_pages tp on tp.cc = r.cc),
  'trend', (select coalesce(jsonb_agg(jsonb_build_object('day', day, 'visitors', visitors) order by day), '[]'::jsonb)
    from (select day, jsonb_object_agg(cc, n) as visitors from trend_counts group by day) t)
);
$$;

-- Content: what students study. Page paths and downloads follow the country
-- filter; server-side paper opens (usage_events) have no country, so they
-- always cover every country.
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
pv as (
  select ue.subject_name, ue.metadata
  from b, public.usage_events ue
  where ue.feature = 'paper_view' and ue.created_at >= b.since and ue.created_at < b.until
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
    'total',      (select count(*) from pv),
    'by_subject', (select coalesce(jsonb_agg(jsonb_build_object('name', subject_name, 'count', n) order by n desc), '[]'::jsonb)
                   from (select coalesce(subject_name, 'Unknown') as subject_name, count(*) as n from pv group by 1 order by 2 desc limit 20) t),
    'by_doc',     (select coalesce(jsonb_agg(jsonb_build_object('name', d, 'count', n) order by n desc), '[]'::jsonb)
                   from (select case metadata->>'doc' when 'qp' then 'Question paper' when 'ms' then 'Mark scheme' else 'Other' end as d, count(*) as n from pv group by 1) t),
    'by_view',    (select coalesce(jsonb_agg(jsonb_build_object('name', w, 'count', n) order by n desc), '[]'::jsonb)
                   from (select case metadata->>'view' when 'split' then 'Side by side (QP + MS)' else 'Single' end as w, count(*) as n from pv group by 1) t),
    'top_papers', (select coalesce(jsonb_agg(jsonb_build_object('title', title, 'count', n) order by n desc), '[]'::jsonb)
                   from (select coalesce(metadata->>'title', metadata->>'path', 'Unknown') as title, count(*) as n
                         from pv group by 1 order by 2 desc limit 25) t))
);
$$;

-- Data quality: how far to trust the dashboard. Analytics is compared with the
-- tables that record the real thing, plus coverage, likely automated traffic,
-- unusually heavy visits and whether tracking is still arriving.
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
         (select count(*) from b, public.usage_events ue where ue.feature = 'paper_view' and ue.created_at >= b.since and ue.created_at < b.until) as truth,
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

revoke all on function public.admin_content(integer, text, text, date, date)       from public, anon, authenticated;
revoke all on function public.admin_data_quality(integer, text, date, date)        from public, anon, authenticated;
grant execute on function public.admin_content(integer, text, text, date, date)    to service_role;
grant execute on function public.admin_data_quality(integer, text, date, date)     to service_role;
-- analytics_totals and admin_countries keep their earlier grants.

commit;
