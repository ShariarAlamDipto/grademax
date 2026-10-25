-- 38: reporting controls for the Visitors dashboard. Run after 37.
--
--   * Every section takes p_country (ISO code, or '??' for unknown) and an optional
--     custom range p_from..p_to (local dates in p_tz) besides p_days.
--   * Overview and Countries return the previous period of the same length.
--   * New admin_countries(): every country with visits, conversions and trend.
--   * Retention adds D1 / D7 / D30 and marks cohorts that are still incomplete.
--   * site_events gets a country column (filled by the app from now on).
--   * site_analytics_purge() deletes raw rows older than 13 months.
--   * site_events.props + more event names, and admin_tools() for Tools & health.
--
-- The 37 versions are dropped first: adding parameters would otherwise create
-- overloads that PostgREST cannot choose between. Re-runnable. Service role only.

begin;

alter table public.site_events
  add column if not exists country text check (country ~ '^[A-Z]{2}$'),
  -- Small numeric/boolean facts (question counts, timings), at most 2 KB.
  add column if not exists props jsonb
    check (props is null or (jsonb_typeof(props) = 'object' and pg_column_size(props) <= 2048));

-- Outcome events for the tools and sign-in (Tools & health section).
alter table public.site_events drop constraint if exists site_events_name_check;
alter table public.site_events add constraint site_events_name_check check (name in (
  'download', 'outbound', 'sign_in', 'sign_up', 'sign_in_failed', 'order_placed',
  'worksheet_generated', 'worksheet_failed', 'test_generated', 'test_failed', 'limit_reached'));

drop function if exists public.admin_site_analytics(integer, text);
drop function if exists public.admin_behavior(integer, text);
drop function if exists public.admin_acquisition(integer, text);
drop function if exists public.admin_funnels(integer, text);
drop function if exists public.admin_patterns(integer, text);
drop function if exists public.admin_retention(integer, text);
drop function if exists public.admin_realtime();
drop function if exists public.analytics_sessions(integer, text);

-- The reporting window. A custom range wins over p_days; the end is clipped to
-- today and the span to 366 days. prev_* is the same length just before.
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
  r as (select greatest(f, l - 365) as f, l from raw)
  select (r.f::timestamp) at time zone p_tz,
         ((r.l + 1)::timestamp) at time zone p_tz,
         r.f, r.l,
         ((r.f - (r.l - r.f + 1))::timestamp) at time zone p_tz,
         (r.f::timestamp) at time zone p_tz,
         ((r.l + 1)::timestamp) at time zone p_tz > now()
  from r;
$$;

create or replace function public.analytics_visits(p_since timestamptz, p_until timestamptz, p_country text)
returns setof public.site_visits
language sql
stable
security definer
set search_path = public
as $$
  select * from public.site_visits
  where created_at >= p_since and created_at < p_until
    and (p_country is null or coalesce(country, '??') = p_country);
$$;

create or replace function public.analytics_events(p_since timestamptz, p_until timestamptz, p_country text)
returns setof public.site_events
language sql
stable
security definer
set search_path = public
as $$
  select * from public.site_events
  where created_at >= p_since and created_at < p_until
    and (p_country is null or coalesce(country, '??') = p_country);
$$;

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
         max(v.path)    filter (where v.rn = 1),
         max(v.path)    filter (where v.rn_desc = 1),
         max(v.channel) filter (where v.rn = 1),
         bool_or(v.is_new_visitor),
         count(*) = 1 and sum(v.engaged_seconds) < 10,
         max(coalesce(v.country, '??')) filter (where v.rn = 1)
  from v
  group by v.session_id;
$$;

-- Headline numbers for a window; used for the current and the previous period.
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
    'unknown_country',     (select count(distinct visitor_id) from v where country is null)
  );
$$;

-- Overview.
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
      'today',     (select count(distinct visitor_id) from public.site_visits
                    where (created_at at time zone p_tz)::date = (now() at time zone p_tz)::date
                      and (p_country is null or coalesce(country, '??') = p_country)),
      'yesterday', (select count(distinct visitor_id) from public.site_visits
                    where (created_at at time zone p_tz)::date = (now() at time zone p_tz)::date - 1
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

-- Countries: every country, with behaviour, conversions and the previous period.
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
total as (select count(distinct visitor_id) as n from v),
rows as (
  select v.cc,
         count(distinct v.visitor_id)                                   as visitors,
         count(*)                                                       as views,
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
         count(distinct session_id) filter (where name in ('sign_in', 'sign_up')) as sign_ins,
         count(*) filter (where name = 'sign_up')                        as sign_ups,
         count(*) filter (where name = 'order_placed')                   as orders,
         count(*) filter (where name in ('worksheet_generated', 'test_generated')) as generations
  from e group by 1
),
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
  from days d
  cross join top5 t5
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
      'downloads', coalesce(ev.downloads, 0), 'sign_ins', coalesce(ev.sign_ins, 0),
      'sign_ups', coalesce(ev.sign_ups, 0), 'orders', coalesce(ev.orders, 0),
      'generations', coalesce(ev.generations, 0),
      'prev_visitors', coalesce(p.visitors, 0),
      'change', case when coalesce(p.visitors, 0) = 0 then null
                     else round(100.0 * (r.visitors - p.visitors) / p.visitors, 1) end,
      'top_pages', coalesce(tp.pages, '[]'::jsonb)
    ) order by r.visitors desc), '[]'::jsonb)
    from rows r
    left join sess se     on se.cc = r.cc
    left join ev          on ev.cc = r.cc
    left join prev p      on p.cc = r.cc
    left join top_pages tp on tp.cc = r.cc),
  'trend', (select coalesce(jsonb_agg(jsonb_build_object('day', day, 'visitors', visitors) order by day), '[]'::jsonb)
    from (select day, jsonb_object_agg(cc, n) as visitors from trend_counts group by day) t)
);
$$;

-- Behaviour.
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
         count(*) filter (where session_id is not null and rn = 1)      as entries,
         count(*) filter (where session_id is not null and rn = n)      as exits,
         count(*) filter (where session_id is not null and rn = 1 and n = 1 and sess_engaged < 10) as bounces,
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

-- Acquisition.
create or replace function public.admin_acquisition(
  p_days integer default 30, p_tz text default 'Asia/Dhaka',
  p_country text default null, p_from date default null, p_to date default null
) returns jsonb
language sql
stable
security definer
set search_path = public
as $$
with b as (select * from public.analytics_bounds(p_days, p_tz, p_from, p_to)),
starts as (select sv.* from b, public.analytics_visits(b.since, b.until, p_country) sv where sv.is_session_start),
s as (select f.* from b, public.analytics_session_facts(b.since, b.until, p_country) f),
days as (select d::date as day from b, generate_series(b.first_day, b.last_day, interval '1 day') d)
select jsonb_build_object(
  'channels', (select coalesce(jsonb_agg(jsonb_build_object(
                 'channel', channel, 'sessions', n, 'visitors', u, 'bounce_rate', br,
                 'pages_per_session', pps, 'avg_seconds', secs) order by n desc), '[]'::jsonb)
    from (select coalesce(channel, 'direct') as channel, count(*) as n, count(distinct visitor_id) as u,
                 round(100.0 * count(*) filter (where bounced) / count(*), 1) as br,
                 round(avg(pages), 2) as pps, round(avg(engaged)) as secs
          from s group by 1) t),
  'daily', (select coalesce(jsonb_agg(row_to_json(t)::jsonb order by t.day), '[]'::jsonb)
    from (select d.day,
                 count(st.id) filter (where st.channel = 'search')   as search,
                 count(st.id) filter (where st.channel = 'direct' or (st.channel is null and st.id is not null)) as direct,
                 count(st.id) filter (where st.channel = 'social')   as social,
                 count(st.id) filter (where st.channel = 'ai')       as ai,
                 count(st.id) filter (where st.channel = 'referral') as referral,
                 count(st.id) filter (where st.channel in ('email', 'paid')) as campaigns
          from days d
          left join starts st on (st.created_at at time zone p_tz)::date = d.day
          group by d.day) t),
  'referrers', (select coalesce(jsonb_agg(jsonb_build_object('host', referrer_host, 'sessions', n, 'channel', ch) order by n desc), '[]'::jsonb)
    from (select referrer_host, count(*) as n, max(channel) as ch from starts
          where referrer_host is not null group by 1 order by 2 desc limit 20) t),
  'campaigns', (select coalesce(jsonb_agg(jsonb_build_object('source', utm_source, 'medium', utm_medium,
                 'campaign', utm_campaign, 'sessions', n) order by n desc), '[]'::jsonb)
    from (select utm_source, utm_medium, utm_campaign, count(*) as n from starts
          where utm_source is not null or utm_campaign is not null
          group by 1, 2, 3 order by 4 desc limit 20) t),
  'landing', (select coalesce(jsonb_agg(jsonb_build_object('path', landing, 'channel', channel, 'sessions', n) order by n desc), '[]'::jsonb)
    from (select landing, coalesce(channel, 'direct') as channel, count(*) as n
          from s group by 1, 2 order by 3 desc limit 20) t),
  'new_vs_returning', jsonb_build_object(
    'new',       (select count(*) from s where is_new),
    'returning', (select count(*) from s where not is_new)),
  'countries', (select coalesce(jsonb_agg(jsonb_build_object('country', country, 'sessions', n, 'visitors', u) order by n desc), '[]'::jsonb)
    from (select coalesce(country, '??') as country, count(*) as n, count(distinct visitor_id) as u
          from starts group by 1 order by 2 desc limit 20) t)
);
$$;

-- Funnels.
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
-- Events follow the visit's sessions, so the country filter carries over.
e as (select ev.* from b, public.site_events ev
      where ev.created_at >= b.since and ev.created_at < b.until
        and ev.session_id in (select session_id from v)),
paper as (
  select v.session_id,
         min(v.created_at) filter (where v.path like '/past-papers/%' or v.path like '/qp/%'
                                      or v.path like '/edexcel-%' or v.path like '/cambridge-%') as s2,
         least(min(v.created_at) filter (where v.path = '/viewer'),
               (select min(x.created_at) from e x where x.session_id = v.session_id and x.name = 'download')) as s3
  from v group by v.session_id
),
signup as (
  select v.session_id,
         min(v.created_at) filter (where not v.signed_in) as s1,
         min(v.created_at) filter (where v.path = '/login' and not v.signed_in) as s2,
         least((select min(x.created_at) from e x where x.session_id = v.session_id and x.name in ('sign_in', 'sign_up')),
               min(v.created_at) filter (where v.signed_in and v.path <> '/login')) as s3,
         (select min(x.created_at) from e x where x.session_id = v.session_id and x.name = 'sign_up') as s4
  from v group by v.session_id
),
store as (
  select v.session_id,
         min(v.created_at) filter (where v.path like '/store%' or v.path like '/books%') as s1,
         min(v.created_at) filter (where v.path ~ '^/store/[^/]+$' and v.path <> '/store/orders') as s2,
         min(v.created_at) filter (where v.path = '/cart') as s3,
         min(v.created_at) filter (where v.path = '/checkout') as s4,
         (select min(x.created_at) from e x where x.session_id = v.session_id and x.name = 'order_placed') as s5
  from v group by v.session_id
),
tools as (
  select v.session_id,
         min(v.created_at) filter (where v.path in ('/generate', '/test-builder')) as s1,
         (select min(x.created_at) from e x where x.session_id = v.session_id
            and x.name in ('worksheet_generated', 'test_generated')) as s2
  from v group by v.session_id
)
select jsonb_build_object(
  'paper', (select jsonb_build_array(
      jsonb_build_object('step', 'Visited the site', 'sessions', count(*)),
      jsonb_build_object('step', 'Viewed a past-paper page', 'sessions', count(*) filter (where s2 is not null)),
      jsonb_build_object('step', 'Opened or downloaded a paper', 'sessions', count(*) filter (where s2 is not null and s3 >= s2)))
    from paper),
  'signup', (select jsonb_build_array(
      jsonb_build_object('step', 'Visited while signed out', 'sessions', count(*) filter (where s1 is not null)),
      jsonb_build_object('step', 'Opened the login page', 'sessions', count(*) filter (where s2 is not null)),
      jsonb_build_object('step', 'Signed in', 'sessions', count(*) filter (where s2 is not null and s3 >= s2)),
      jsonb_build_object('step', 'Of which: new account', 'sessions', count(*) filter (where s2 is not null and s4 >= s2)))
    from signup),
  'store', (select jsonb_build_array(
      jsonb_build_object('step', 'Visited the store', 'sessions', count(*) filter (where s1 is not null)),
      jsonb_build_object('step', 'Viewed a product', 'sessions', count(*) filter (where s1 is not null and s2 >= s1)),
      jsonb_build_object('step', 'Opened the cart', 'sessions', count(*) filter (where s2 >= s1 and s3 >= s2)),
      jsonb_build_object('step', 'Started checkout', 'sessions', count(*) filter (where s2 >= s1 and s3 >= s2 and s4 >= s3)),
      jsonb_build_object('step', 'Placed an order', 'sessions', count(*) filter (where s2 >= s1 and s3 >= s2 and s4 >= s3 and s5 >= s4)))
    from store),
  'tools', (select jsonb_build_array(
      jsonb_build_object('step', 'Opened a question tool', 'sessions', count(*) filter (where s1 is not null)),
      jsonb_build_object('step', 'Generated a worksheet or test', 'sessions', count(*) filter (where s1 is not null and s2 >= s1)))
    from tools)
);
$$;

-- Time & tech.
create or replace function public.admin_patterns(
  p_days integer default 30, p_tz text default 'Asia/Dhaka',
  p_country text default null, p_from date default null, p_to date default null
) returns jsonb
language sql
stable
security definer
set search_path = public
as $$
with b as (select * from public.analytics_bounds(p_days, p_tz, p_from, p_to)),
v as (select sv.* from b, public.analytics_visits(b.since, b.until, p_country) sv)
select jsonb_build_object(
  'heatmap', (select coalesce(jsonb_agg(jsonb_build_object('dow', dow, 'hour', hr, 'views', n)), '[]'::jsonb)
    from (select extract(isodow from created_at at time zone p_tz)::int as dow,
                 extract(hour   from created_at at time zone p_tz)::int as hr, count(*) as n
          from v group by 1, 2) t),
  'browsers', (select coalesce(jsonb_agg(jsonb_build_object('name', name, 'visitors', u) order by u desc), '[]'::jsonb)
    from (select coalesce(browser, 'Unknown') as name, count(distinct visitor_id) as u from v group by 1) t),
  'os', (select coalesce(jsonb_agg(jsonb_build_object('name', name, 'visitors', u) order by u desc), '[]'::jsonb)
    from (select coalesce(os, 'Unknown') as name, count(distinct visitor_id) as u from v group by 1) t),
  'devices', (select coalesce(jsonb_agg(jsonb_build_object('name', device, 'visitors', u, 'avg_engaged', secs,
                 'pages_per_visitor', ppv) order by u desc), '[]'::jsonb)
    from (select device, count(distinct visitor_id) as u,
                 round(avg(engaged_seconds) filter (where engaged_seconds > 0)) as secs,
                 round(count(*)::numeric / nullif(count(distinct visitor_id), 0), 2) as ppv
          from v group by 1) t)
);
$$;

-- Retention: weekly cohorts plus D1 / D7 / D30. A visitor's cohort follows the
-- country of their first visit. Cohorts too young to measure are flagged.
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
eligible as (
  select f.* from firsts f, params p
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
dn as (
  select n, (select count(*) from eligible el, params p where el.first_day <= p.today - n) as base,
         (select count(*) from eligible el, params p where el.first_day <= p.today - n
            and exists (select 1 from visit_days vd where vd.visitor_id = el.visitor_id
                        and vd.day > el.first_day and vd.day <= el.first_day + n)) as back
  from (values (1), (7), (30)) as t(n)
)
select jsonb_build_object(
  'weeks', (select weeks from params),
  'country', p_country,
  -- Dn = came back within n days of the first visit, among visitors first
  -- seen at least n days ago (so everyone counted had the full n days).
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

-- Realtime.
create or replace function public.admin_realtime(p_country text default null)
returns jsonb
language sql
stable
security definer
set search_path = public
as $$
with v as (
  select * from public.site_visits
  where created_at >= now() - interval '30 minutes'
    and (p_country is null or coalesce(country, '??') = p_country)
),
latest as (
  select distinct on (visitor_id) visitor_id, path, created_at
  from v where created_at >= now() - interval '5 minutes'
  order by visitor_id, created_at desc
)
select jsonb_build_object(
  'active_5m',  (select count(*) from latest),
  'active_30m', (select count(distinct visitor_id) from v),
  'per_minute', (select jsonb_agg(jsonb_build_object('minute', m, 'views',
                   (select count(*) from v where v.created_at >= now() - make_interval(mins => m + 1)
                                              and v.created_at <  now() - make_interval(mins => m)))
                 order by m desc) from generate_series(0, 29) m),
  'pages_now',  (select coalesce(jsonb_agg(jsonb_build_object('path', path, 'visitors', n) order by n desc), '[]'::jsonb)
                 from (select path, count(*) as n from latest group by 1 order by 2 desc limit 15) t),
  'recent',     (select coalesce(jsonb_agg(jsonb_build_object('at', created_at, 'path', path, 'country', country,
                   'device', device, 'channel', channel, 'referrer', referrer_host, 'new', is_new_visitor)
                   order by created_at desc), '[]'::jsonb)
                 from (select * from v order by created_at desc limit 25) t),
  'events',     (select coalesce(jsonb_agg(jsonb_build_object('at', created_at, 'name', name, 'label', label, 'country', country)
                   order by created_at desc), '[]'::jsonb)
                 from (select * from public.site_events
                       where created_at >= now() - interval '30 minutes'
                         and (p_country is null or coalesce(country, '??') = p_country)
                       order by created_at desc limit 15) t)
);
$$;

-- Tools & health: outcomes of the Worksheet Generator, Test Builder and sign-in,
-- from the server-recorded events and their props.
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
                         from e where e.name = tool.ok_name group by 1 order by 2 desc limit 15) t)
    )) from tool),
  'sign_in', jsonb_build_object(
    'completed', (select count(*) from e where name in ('sign_in', 'sign_up')),
    'new_accounts', (select count(*) from e where name = 'sign_up'),
    'failed',    (select count(*) from e where name = 'sign_in_failed'),
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

-- Raw rows older than p_months are deleted (the privacy policy's retention).
-- The app calls this now and then; it is cheap thanks to the created_at indexes.
create or replace function public.site_analytics_purge(p_months integer default 13)
returns integer
language plpgsql
security definer
set search_path = public
as $$
declare
  v_cutoff timestamptz := now() - make_interval(months => greatest(coalesce(p_months, 13), 6));
  v_visits integer;
  v_events integer;
begin
  delete from public.site_visits where created_at < v_cutoff;
  get diagnostics v_visits = row_count;
  delete from public.site_events where created_at < v_cutoff;
  get diagnostics v_events = row_count;
  return v_visits + v_events;
end;
$$;

revoke all on function public.analytics_bounds(integer, text, date, date)                  from public, anon, authenticated;
revoke all on function public.analytics_visits(timestamptz, timestamptz, text)             from public, anon, authenticated;
revoke all on function public.analytics_events(timestamptz, timestamptz, text)             from public, anon, authenticated;
revoke all on function public.analytics_session_facts(timestamptz, timestamptz, text)      from public, anon, authenticated;
revoke all on function public.analytics_totals(timestamptz, timestamptz, text)             from public, anon, authenticated;
revoke all on function public.admin_site_analytics(integer, text, text, date, date)        from public, anon, authenticated;
revoke all on function public.admin_countries(integer, text, date, date)                   from public, anon, authenticated;
revoke all on function public.admin_behavior(integer, text, text, date, date)              from public, anon, authenticated;
revoke all on function public.admin_acquisition(integer, text, text, date, date)           from public, anon, authenticated;
revoke all on function public.admin_funnels(integer, text, text, date, date)               from public, anon, authenticated;
revoke all on function public.admin_patterns(integer, text, text, date, date)              from public, anon, authenticated;
revoke all on function public.admin_retention(integer, text, text)                         from public, anon, authenticated;
revoke all on function public.admin_realtime(text)                                         from public, anon, authenticated;
revoke all on function public.site_analytics_purge(integer)                                from public, anon, authenticated;
revoke all on function public.admin_tools(integer, text, text, date, date)                 from public, anon, authenticated;

grant execute on function public.analytics_bounds(integer, text, date, date)               to service_role;
grant execute on function public.analytics_visits(timestamptz, timestamptz, text)          to service_role;
grant execute on function public.analytics_events(timestamptz, timestamptz, text)          to service_role;
grant execute on function public.analytics_session_facts(timestamptz, timestamptz, text)   to service_role;
grant execute on function public.analytics_totals(timestamptz, timestamptz, text)          to service_role;
grant execute on function public.admin_site_analytics(integer, text, text, date, date)     to service_role;
grant execute on function public.admin_countries(integer, text, date, date)                to service_role;
grant execute on function public.admin_behavior(integer, text, text, date, date)           to service_role;
grant execute on function public.admin_acquisition(integer, text, text, date, date)        to service_role;
grant execute on function public.admin_funnels(integer, text, text, date, date)            to service_role;
grant execute on function public.admin_patterns(integer, text, text, date, date)           to service_role;
grant execute on function public.admin_retention(integer, text, text)                      to service_role;
grant execute on function public.admin_realtime(text)                                      to service_role;
grant execute on function public.site_analytics_purge(integer)                             to service_role;
grant execute on function public.admin_tools(integer, text, text, date, date)              to service_role;

commit;
