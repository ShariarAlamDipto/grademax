-- 41: accuracy fixes for the Visitors dashboard (found by an audit on 25 Oct 2026).
-- Run after 40. Replaces functions only; no table changes; re-runnable.
--
-- 1. Visits that began before the period were counted inside it, with no
--    channel, so they showed up as "direct". A visit now belongs to the period
--    it began in, and its channel and landing page come from its first page.
-- 2. Password sign-ins never reach the server's /auth/callback, so they were
--    missing from sign-in counts. A sign-in is now a sign-in event OR a visit
--    whose pages go from signed-out to signed-in.
-- 3. "Today" (or any period still running) was compared with the whole
--    previous period. It is now compared with the same elapsed time.
-- 4. D1/D7/D30 counted visitors whose window was not over yet.
--    The weekly table now also says which column is the current, unfinished week.
-- 5. Paper funnel: a download before the past-paper page hid a later viewer
--    visit. The last step now uses the first viewer visit or download after it.
-- 6. Behaviour: page entries/bounces now use each visit's real first page.
-- 8. Performance: Funnels and Retention rewritten to scale (they took minutes
--    at 60k-300k page views); Overview Today/Yesterday use the created_at index.
-- 7. Test Builder subject demand counted a test twice (question paper and mark
--    scheme PDFs); it now counts question-paper PDFs only.

begin;

-- 3. Same signature and columns as 38; only prev_until changes.
create or replace function public.analytics_bounds(p_days integer, p_tz text, p_from date, p_to date)
returns table (since timestamptz, until timestamptz, first_day date, last_day date,
               prev_since timestamptz, prev_until timestamptz, partial boolean)
language sql
stable
as $$
  with t as (select (now() at time zone p_tz)::date as today),
  raw as (
    select case when p_from is null then t.today - (greatest(1, least(coalesce(p_days, 30), 365)) - 1)
                else least(p_from, t.today) end as f,
           case when p_from is null then t.today
                else least(greatest(coalesce(p_to, p_from), p_from), t.today) end as l
    from t
  ),
  r as (select greatest(f, l - 365) as f, l from raw),
  w as (
    select r.f, r.l,
           (r.f::timestamp) at time zone p_tz                    as s,
           ((r.l + 1)::timestamp) at time zone p_tz              as u,
           ((r.f - (r.l - r.f + 1))::timestamp) at time zone p_tz as ps
    from r
  )
  select w.s, w.u, w.f, w.l, w.ps,
         -- A running period is compared with the same elapsed time before it.
         case when w.u > now() then least(w.ps + (now() - w.s), w.s) else w.s end,
         w.u > now()
  from w;
$$;

-- 1. Only visits that began in the period; channel and landing from the first page.
create or replace function public.analytics_session_facts(p_since timestamptz, p_until timestamptz, p_country text)
returns table (
  session_id uuid, visitor_id uuid, started_at timestamptz, pages bigint,
  engaged bigint, landing text, exit_path text, channel text, is_new boolean, bounced boolean, country text
)
language sql
stable
security definer
set search_path = public
as $$
  with v as (
    select sv.*,
           row_number() over (partition by sv.session_id order by sv.created_at, sv.id)           as rn,
           row_number() over (partition by sv.session_id order by sv.created_at desc, sv.id desc) as rn_desc
    from public.analytics_visits(p_since, p_until, p_country) sv
    where sv.session_id is not null
  )
  select v.session_id, min(v.visitor_id::text)::uuid, min(v.created_at), count(*), sum(v.engaged_seconds),
         coalesce(max(v.path) filter (where v.is_session_start), max(v.path) filter (where v.rn = 1)),
         max(v.path)    filter (where v.rn_desc = 1),
         max(v.channel) filter (where v.is_session_start),
         bool_or(v.is_new_visitor),
         count(*) = 1 and sum(v.engaged_seconds) < 10,
         max(coalesce(v.country, '??')) filter (where v.rn = 1)
  from v
  group by v.session_id
  having bool_or(v.is_session_start);
$$;

-- 2. Every sign-in in the window, one row per visit: a sign_in/sign_up event,
--    or a visit whose pages go from signed-out to signed-in (password sign-ins).
create or replace function public.analytics_sign_ins(p_since timestamptz, p_until timestamptz, p_country text)
returns table (session_id uuid, visitor_id uuid, country text, new_account boolean)
language sql
stable
security definer
set search_path = public
as $$
  with ev as (
    select e.session_id, e.visitor_id, coalesce(e.country, '??') as country, e.name = 'sign_up' as new_account
    from public.analytics_events(p_since, p_until, p_country) e
    where e.name in ('sign_in', 'sign_up') and e.session_id is not null
  ),
  flips as (
    select v.session_id, min(v.visitor_id::text)::uuid as visitor_id, max(coalesce(v.country, '??')) as country
    from public.analytics_visits(p_since, p_until, p_country) v
    where v.session_id is not null
    group by v.session_id
    having min(v.created_at) filter (where not v.signed_in) < max(v.created_at) filter (where v.signed_in)
  ),
  merged as (select session_id, visitor_id, country, new_account from ev
             union all
             select session_id, visitor_id, country, false from flips)
  select session_id, min(visitor_id::text)::uuid, max(country), bool_or(new_account)
  from merged group by session_id;
$$;

-- Countries (as 38, with sign-ins from analytics_sign_ins).
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
  select country as cc, count(*) as sessions,
         round(100.0 * count(*) filter (where bounced) / nullif(count(*), 0), 1) as bounce_rate
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
      'sessions', coalesce(se.sessions, 0), 'bounce_rate', se.bounce_rate,
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

-- Tools & health (as 38, with sign-ins from analytics_sign_ins and test
-- subject demand counted on question-paper PDFs only).
create or replace function public.admin_tools(
  p_days integer default 30, p_tz text default 'Asia/Dhaka',
  p_country text default null, p_from date default null, p_to date default null
) returns jsonb
language sql
stable
security definer
set search_path = public
as $$
with b as (select * from public.analytics_bounds(p_days, p_tz, p_from, p_to)),
e as (
  select ev.*, (ev.props->>'ms')::numeric as ms
  from b, public.analytics_events(b.since, b.until, p_country) ev
  where ev.name in ('worksheet_generated', 'worksheet_failed', 'test_generated', 'test_failed',
                    'limit_reached', 'sign_in', 'sign_up', 'sign_in_failed')
),
si as (select x.* from b, public.analytics_sign_ins(b.since, b.until, p_country) x),
days as (select d::date as day from b, generate_series(b.first_day, b.last_day, interval '1 day') d),
tool as (
  select t.tool, t.ok_name, t.fail_name from (values
    ('worksheet', 'worksheet_generated', 'worksheet_failed'),
    ('test', 'test_generated', 'test_failed')) as t(tool, ok_name, fail_name)
)
select jsonb_build_object(
  'first_day', (select first_day from b), 'last_day', (select last_day from b), 'partial', (select partial from b),
  'tools', (select jsonb_object_agg(tool.tool, jsonb_build_object(
      'generated',  (select count(*) from e where e.name = tool.ok_name),
      'failed',     (select count(*) from e where e.name = tool.fail_name),
      'partial',    (select count(*) from e where e.name = tool.ok_name and (e.props->>'partial')::boolean),
      'avg_ms',     (select round(avg(ms)) from e where e.name = tool.ok_name),
      'p50_ms',     (select round(percentile_cont(0.5) within group (order by ms)::numeric) from e where e.name = tool.ok_name and ms is not null),
      'p90_ms',     (select round(percentile_cont(0.9) within group (order by ms)::numeric) from e where e.name = tool.ok_name and ms is not null),
      'requested',  (select coalesce(sum((props->>'requested')::numeric), 0) from e where e.name = tool.ok_name),
      'supplied',   (select coalesce(sum((props->>'supplied')::numeric), 0) from e where e.name = tool.ok_name),
      'history_failed', (select count(*) from e where e.name = tool.ok_name and (e.props->>'history_saved')::boolean is false),
      'limit_hits', (select count(*) from e where e.name = 'limit_reached' and e.label = tool.tool),
      'fail_reasons', (select coalesce(jsonb_agg(jsonb_build_object('reason', coalesce(label, 'unknown'), 'count', n) order by n desc), '[]'::jsonb)
                       from (select label, count(*) as n from e where e.name = tool.fail_name group by 1) t),
      'subjects', (select coalesce(jsonb_agg(jsonb_build_object('subject', subject, 'count', n) order by n desc), '[]'::jsonb)
                   from (select split_part(coalesce(label, 'Unknown'), ' · ', 1) as subject, count(*) as n
                         from e where e.name = tool.ok_name and (e.props->>'markscheme')::boolean is not true
                         group by 1 order by 2 desc limit 15) t)
    )) from tool),
  'sign_in', jsonb_build_object(
    'completed',    (select count(*) from si),
    'new_accounts', (select count(*) from si where new_account),
    'failed',       (select count(*) from e where name = 'sign_in_failed'),
    'fail_reasons', (select coalesce(jsonb_agg(jsonb_build_object('reason', coalesce(label, 'unknown'), 'count', n) order by n desc), '[]'::jsonb)
                     from (select label, count(*) as n from e where name = 'sign_in_failed' group by 1) t)),
  'daily', (select coalesce(jsonb_agg(row_to_json(t)::jsonb order by t.day), '[]'::jsonb) from (
      select d.day,
             count(e.id) filter (where e.name = 'worksheet_generated') as worksheets,
             count(e.id) filter (where e.name = 'test_generated')      as tests,
             count(e.id) filter (where e.name in ('worksheet_failed', 'test_failed')) as failures,
             count(e.id) filter (where e.name = 'sign_in_failed')      as sign_in_failures
      from days d left join e on (e.created_at at time zone p_tz)::date = d.day
      group by d.day) t)
);
$$;

-- Funnels (as 38, but rewritten to scale: events are grouped per visit once and
-- joined, instead of a lookup per visit, which took minutes at 60k page views.
-- Paper step 3 is the first viewer visit or download AFTER step 2, and
-- sign-ins include password sign-ins.)
create or replace function public.admin_funnels(
  p_days integer default 30, p_tz text default 'Asia/Dhaka',
  p_country text default null, p_from date default null, p_to date default null
) returns jsonb
language sql
stable
security definer
set search_path = public
as $$
with b as (select * from public.analytics_bounds(p_days, p_tz, p_from, p_to)),
v as (select sv.* from b, public.analytics_visits(b.since, b.until, p_country) sv where sv.session_id is not null),
e as (select ev.session_id, ev.name, ev.created_at from b, public.site_events ev
      where ev.created_at >= b.since and ev.created_at < b.until and ev.session_id is not null
        and ev.session_id in (select session_id from v)),
-- One row per visit with the first time of every step that only needs a minimum.
per_visit as (
  select v.session_id,
         min(v.created_at) filter (where v.path like '/past-papers/%' or v.path like '/qp/%'
                                      or v.path like '/edexcel-%' or v.path like '/cambridge-%') as paper_page,
         min(v.created_at) filter (where not v.signed_in)                                     as signed_out,
         min(v.created_at) filter (where v.path = '/login' and not v.signed_in)               as login_page,
         min(v.created_at) filter (where v.signed_in and v.path <> '/login')                  as signed_in_page,
         min(v.created_at) filter (where v.path like '/store%' or v.path like '/books%')      as store,
         min(v.created_at) filter (where v.path ~ '^/store/[^/]+$' and v.path <> '/store/orders') as product,
         min(v.created_at) filter (where v.path = '/cart')                                    as cart,
         min(v.created_at) filter (where v.path = '/checkout')                                as checkout,
         min(v.created_at) filter (where v.path in ('/generate', '/test-builder'))            as tool_page
  from v group by v.session_id
),
per_event as (
  select session_id,
         min(created_at) filter (where name in ('sign_in', 'sign_up'))               as sign_in,
         min(created_at) filter (where name = 'sign_up')                             as sign_up,
         min(created_at) filter (where name = 'order_placed')                        as ordered,
         min(created_at) filter (where name in ('worksheet_generated', 'test_generated')) as generated
  from e group by session_id
),
-- Paper step 3 must come after step 2, so it is a join on time, not a minimum.
viewer_after as (
  select pv.session_id, min(v.created_at) as at
  from per_visit pv join v on v.session_id = pv.session_id and v.path = '/viewer' and v.created_at >= pv.paper_page
  group by pv.session_id
),
download_after as (
  select pv.session_id, min(e.created_at) as at
  from per_visit pv join e on e.session_id = pv.session_id and e.name = 'download' and e.created_at >= pv.paper_page
  group by pv.session_id
),
f as (
  select pv.*, pe.sign_in, pe.sign_up, pe.ordered, pe.generated,
         least(va.at, da.at) as paper_opened,
         least(pe.sign_in, pv.signed_in_page) as signed_in_at
  from per_visit pv
  left join per_event pe      on pe.session_id = pv.session_id
  left join viewer_after va   on va.session_id = pv.session_id
  left join download_after da on da.session_id = pv.session_id
)
select jsonb_build_object(
  'paper', (select jsonb_build_array(
      jsonb_build_object('step', 'Visited the site', 'sessions', count(*)),
      jsonb_build_object('step', 'Viewed a past-paper page', 'sessions', count(*) filter (where paper_page is not null)),
      jsonb_build_object('step', 'Opened or downloaded a paper', 'sessions', count(*) filter (where paper_opened is not null)))
    from f),
  'signup', (select jsonb_build_array(
      jsonb_build_object('step', 'Visited while signed out', 'sessions', count(*) filter (where signed_out is not null)),
      jsonb_build_object('step', 'Opened the login page', 'sessions', count(*) filter (where login_page is not null)),
      jsonb_build_object('step', 'Signed in', 'sessions', count(*) filter (where login_page is not null and signed_in_at >= login_page)),
      jsonb_build_object('step', 'Of which: new account', 'sessions', count(*) filter (where login_page is not null and sign_up >= login_page)))
    from f),
  'store', (select jsonb_build_array(
      jsonb_build_object('step', 'Visited the store', 'sessions', count(*) filter (where store is not null)),
      jsonb_build_object('step', 'Viewed a product', 'sessions', count(*) filter (where store is not null and product >= store)),
      jsonb_build_object('step', 'Opened the cart', 'sessions', count(*) filter (where product >= store and cart >= product)),
      jsonb_build_object('step', 'Started checkout', 'sessions', count(*) filter (where product >= store and cart >= product and checkout >= cart)),
      jsonb_build_object('step', 'Placed an order', 'sessions', count(*) filter (where product >= store and cart >= product and checkout >= cart and ordered >= checkout)))
    from f),
  'tools', (select jsonb_build_array(
      jsonb_build_object('step', 'Opened a question tool', 'sessions', count(*) filter (where tool_page is not null)),
      jsonb_build_object('step', 'Generated a worksheet or test', 'sessions', count(*) filter (where tool_page is not null and generated >= tool_page)))
    from f)
);
$$;

-- Retention (as 38; Dn needs the whole n-day window to be over, and the
-- current unfinished week is reported so the table can mark it).
create or replace function public.admin_retention(
  p_weeks integer default 8, p_tz text default 'Asia/Dhaka', p_country text default null
) returns jsonb
language sql
stable
security definer
set search_path = public
as $$
with params as (
  select greatest(2, least(coalesce(p_weeks, 8), 26)) as weeks,
         (now() at time zone p_tz)::date as today,
         date_trunc('week', now() at time zone p_tz)::date as this_week
),
visit_days as (
  select visitor_id, (created_at at time zone p_tz)::date as day,
         min(created_at) as at, min(coalesce(country, '??')) as cc
  from public.site_visits group by 1, 2
),
firsts as (
  select distinct on (visitor_id) visitor_id, day as first_day, cc
  from visit_days order by visitor_id, at
),
-- Each visitor's first return day, found once (a lookup per visitor took
-- minutes at 300k page views).
returns as (
  select f.visitor_id, min(vd.day) as next_day
  from firsts f join visit_days vd on vd.visitor_id = f.visitor_id and vd.day > f.first_day
  group by f.visitor_id
),
eligible as (
  select f.*, r.next_day from firsts f
  left join returns r using (visitor_id)
  cross join params p
  where f.first_day > p.this_week - 7 * p.weeks
    and (p_country is null or f.cc = p_country)
),
cohorts as (
  select date_trunc('week', first_day)::date as cohort, count(*) as size from eligible group by 1
),
cells as (
  select date_trunc('week', el.first_day)::date as cohort,
         ((date_trunc('week', vd.day)::date - date_trunc('week', el.first_day)::date) / 7) as offs,
         count(distinct vd.visitor_id) as n
  from eligible el join visit_days vd using (visitor_id)
  group by 1, 2
),
-- A visitor counts for Dn only once day first_day + n is over (before today).
dn as (
  select t.n,
         count(el.visitor_id) filter (where el.first_day + t.n < p.today)                                  as base,
         count(el.visitor_id) filter (where el.first_day + t.n < p.today and el.next_day <= el.first_day + t.n) as back
  from (values (1), (7), (30)) as t(n)
  cross join params p
  left join eligible el on true
  group by t.n
)
select jsonb_build_object(
  'weeks', (select weeks from params),
  'country', p_country,
  'this_week', (select this_week from params),
  'day_n', (select jsonb_agg(jsonb_build_object('days', n, 'visitors', base, 'returned', back,
                     'rate', round(100.0 * back / nullif(base, 0), 1)) order by n) from dn),
  'cohorts', (select coalesce(jsonb_agg(jsonb_build_object(
      'week', c.cohort, 'size', c.size,
      'complete', c.cohort < (select this_week from params),
      'retained', (select jsonb_agg(coalesce((select ce.n from cells ce where ce.cohort = c.cohort and ce.offs = o), 0) order by o)
                   from params p, generate_series(0, ((p.this_week - c.cohort) / 7)) o)
    ) order by c.cohort desc), '[]'::jsonb) from cohorts c)
);
$$;

-- Behaviour (as 38; entries and bounces use the visit's real first page, so a
-- visit that began before the period is not counted as entering here).
create or replace function public.admin_behavior(
  p_days integer default 30, p_tz text default 'Asia/Dhaka',
  p_country text default null, p_from date default null, p_to date default null
) returns jsonb
language sql
stable
security definer
set search_path = public
as $$
with b as (select * from public.analytics_bounds(p_days, p_tz, p_from, p_to)),
v as (
  select sv.*,
         row_number() over w                                       as rn,
         count(*)     over (partition by sv.session_id)            as n,
         sum(sv.engaged_seconds) over (partition by sv.session_id) as sess_engaged,
         lead(sv.path) over w                                      as next_path
  from b, public.analytics_visits(b.since, b.until, p_country) sv
  window w as (partition by sv.session_id order by sv.created_at, sv.id)
),
s as (select f.* from b, public.analytics_session_facts(b.since, b.until, p_country) f),
e as (select ev.* from b, public.analytics_events(b.since, b.until, p_country) ev),
pages as (
  select path,
         count(*)                                                       as views,
         count(distinct visitor_id)                                     as visitors,
         count(*) filter (where is_session_start)                     as entries,
         count(*) filter (where session_id is not null and rn = n)      as exits,
         count(*) filter (where is_session_start and n = 1 and sess_engaged < 10) as bounces,
         round(avg(engaged_seconds) filter (where engaged_seconds > 0)) as avg_engaged,
         round(avg(scroll_pct) filter (where scroll_pct is not null))   as avg_scroll
  from v group by path
)
select jsonb_build_object(
  'sessions', jsonb_build_object(
    'count',             (select count(*) from s),
    'bounce_rate',       (select round(100.0 * count(*) filter (where bounced) / nullif(count(*), 0), 1) from s),
    'pages_per_session', (select round(avg(pages), 2) from s),
    'avg_seconds',       (select round(avg(engaged)) from s),
    'median_seconds',    (select percentile_cont(0.5) within group (order by engaged) from s)),
  'session_lengths', (select coalesce(jsonb_agg(jsonb_build_object('bucket', bucket, 'sessions', n) order by ord), '[]'::jsonb)
    from (select case when pages = 1 then '1 page' when pages = 2 then '2 pages'
                      when pages <= 5 then '3-5 pages' when pages <= 10 then '6-10 pages' else '11+ pages' end as bucket,
                 min(least(pages, 11)) as ord, count(*) as n
          from s group by 1) t),
  'engagement', (select coalesce(jsonb_agg(jsonb_build_object('bucket', bucket, 'views', n) order by ord), '[]'::jsonb)
    from (select case when engaged_seconds < 10 then 'under 10s' when engaged_seconds < 30 then '10-30s'
                      when engaged_seconds < 60 then '30-60s' when engaged_seconds < 180 then '1-3 min'
                      when engaged_seconds < 600 then '3-10 min' else '10+ min' end as bucket,
                 min(engaged_seconds) as ord, count(*) as n
          from v where pv_id is not null group by 1) t),
  'pages', (select coalesce(jsonb_agg(jsonb_build_object(
              'path', path, 'views', views, 'visitors', visitors, 'entries', entries, 'exits', exits,
              'exit_rate', round(100.0 * exits / nullif(views, 0), 1),
              'bounce_rate', round(100.0 * bounces / nullif(entries, 0), 1),
              'avg_engaged', avg_engaged, 'avg_scroll', avg_scroll) order by views desc), '[]'::jsonb)
    from (select * from pages order by views desc limit 100) t),
  'flows', (select coalesce(jsonb_agg(jsonb_build_object('from', path, 'to', next_path, 'count', n) order by n desc), '[]'::jsonb)
    from (select path, next_path, count(*) as n from v
          where session_id is not null and next_path is not null and next_path <> path
          group by 1, 2 order by 3 desc limit 30) t),
  'landing', (select coalesce(jsonb_agg(jsonb_build_object('path', landing, 'sessions', n,
              'bounce_rate', br, 'avg_seconds', secs) order by n desc), '[]'::jsonb)
    from (select landing, count(*) as n, round(100.0 * count(*) filter (where bounced) / count(*), 1) as br,
                 round(avg(engaged)) as secs
          from s group by 1 order by 2 desc limit 15) t),
  'exits', (select coalesce(jsonb_agg(jsonb_build_object('path', exit_path, 'sessions', n) order by n desc), '[]'::jsonb)
    from (select exit_path, count(*) as n from s group by 1 order by 2 desc limit 15) t),
  'events', (select coalesce(jsonb_agg(jsonb_build_object('name', name, 'count', n, 'visitors', u) order by n desc), '[]'::jsonb)
    from (select name, count(*) as n, count(distinct visitor_id) as u from e group by 1) t),
  'downloads', (select coalesce(jsonb_agg(jsonb_build_object('label', label, 'count', n, 'visitors', u) order by n desc), '[]'::jsonb)
    from (select label, count(*) as n, count(distinct visitor_id) as u from e
          where name = 'download' group by 1 order by 2 desc limit 25) t),
  'outbound', (select coalesce(jsonb_agg(jsonb_build_object('label', label, 'count', n) order by n desc), '[]'::jsonb)
    from (select label, count(*) as n from e where name = 'outbound' group by 1 order by 2 desc limit 15) t)
);
$$;

-- Overview (as 38; Today/Yesterday use indexed time ranges).
create or replace function public.admin_site_analytics(
  p_days integer default 30, p_tz text default 'Asia/Dhaka',
  p_country text default null, p_from date default null, p_to date default null
) returns jsonb
language sql
stable
security definer
set search_path = public
as $$
with b as (select * from public.analytics_bounds(p_days, p_tz, p_from, p_to)),
v as (
  select sv.*, (sv.created_at at time zone p_tz)::date as day
  from b, public.analytics_visits(b.since, b.until, p_country) sv
),
s as (select f.* from b, public.analytics_session_facts(b.since, b.until, p_country) f),
days as (select d::date as day from b, generate_series(b.first_day, b.last_day, interval '1 day') d),
-- Accounts are not visits, so they ignore the country filter.
signups as (
  select (u.created_at at time zone p_tz)::date as day, count(*) as n
  from auth.users u, b where u.created_at >= b.since and u.created_at < b.until group by 1
),
sess_daily as (select (started_at at time zone p_tz)::date as day, count(*) as n from s group by 1),
daily as (
  select d.day,
         count(v.id)                                                  as views,
         count(distinct v.visitor_id)                                 as visitors,
         count(distinct v.visitor_id) filter (where v.is_new_visitor) as new_visitors,
         count(distinct v.visitor_id) filter (where v.signed_in)      as signed_in,
         coalesce(max(su.n), 0)                                       as signups,
         coalesce(max(sd.n), 0)                                       as sessions
  from days d
  left join v             on v.day = d.day
  left join signups su    on su.day = d.day
  left join sess_daily sd on sd.day = d.day
  group by d.day
)
select jsonb_build_object(
  'days',      (select last_day - first_day + 1 from b),
  'first_day', (select first_day from b),
  'last_day',  (select last_day from b),
  'partial',   (select partial from b),
  'timezone',  p_tz,
  'country',   p_country,
  'totals', (select public.analytics_totals(b.since, b.until, p_country) from b)
    || jsonb_build_object(
      'live', (select count(distinct visitor_id) from public.site_visits
               where created_at >= now() - interval '30 minutes'
                 and (p_country is null or coalesce(country, '??') = p_country)),
      -- Time ranges, not "date of created_at", so the created_at index is used
      -- instead of scanning every row ever recorded.
      'today',     (select count(distinct visitor_id) from public.site_visits
                    where created_at >= public.analytics_since(1, p_tz)
                      and (p_country is null or coalesce(country, '??') = p_country)),
      'yesterday', (select count(distinct visitor_id) from public.site_visits
                    where created_at >= public.analytics_since(2, p_tz) and created_at < public.analytics_since(1, p_tz)
                      and (p_country is null or coalesce(country, '??') = p_country)),
      'last7',     (select count(distinct visitor_id) from public.site_visits
                    where created_at >= public.analytics_since(7, p_tz)
                      and (p_country is null or coalesce(country, '??') = p_country)),
      'signups',   (select coalesce(sum(n), 0) from signups),
      'tracking_since', (select min(created_at) from public.site_visits)),
  'previous', (select public.analytics_totals(b.prev_since, b.prev_until, p_country) from b),
  'daily', (select coalesce(jsonb_agg(jsonb_build_object(
              'day', day, 'views', views, 'visitors', visitors, 'new_visitors', new_visitors,
              'signed_in', signed_in, 'signups', signups, 'sessions', sessions) order by day), '[]'::jsonb) from daily),
  'pages', (select coalesce(jsonb_agg(jsonb_build_object('path', path, 'views', views, 'visitors', visitors) order by views desc), '[]'::jsonb)
            from (select path, count(*) as views, count(distinct visitor_id) as visitors
                  from v group by path order by count(*) desc limit 25) t),
  'referrers', (select coalesce(jsonb_agg(jsonb_build_object('host', host, 'visitors', visitors) order by visitors desc), '[]'::jsonb)
            from (select coalesce(referrer_host, 'Direct / unknown') as host, count(distinct visitor_id) as visitors
                  from v where is_new_visitor or referrer_host is not null
                  group by 1 order by 2 desc limit 15) t),
  'countries', (select coalesce(jsonb_agg(jsonb_build_object('country', country, 'visitors', visitors) order by visitors desc), '[]'::jsonb)
            from (select coalesce(country, '??') as country, count(distinct visitor_id) as visitors
                  from v group by 1 order by 2 desc limit 15) t),
  'devices', (select coalesce(jsonb_agg(jsonb_build_object('device', device, 'visitors', visitors) order by visitors desc), '[]'::jsonb)
            from (select device, count(distinct visitor_id) as visitors from v group by 1) t)
);
$$;

revoke all on function public.analytics_sign_ins(timestamptz, timestamptz, text) from public, anon, authenticated;
grant execute on function public.analytics_sign_ins(timestamptz, timestamptz, text) to service_role;
-- The replaced functions keep their 38 grants (create or replace keeps privileges).

commit;
