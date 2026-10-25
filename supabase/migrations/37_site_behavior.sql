-- 37: behaviour analytics on top of 36 (Admin → Analytics → Visitors).
--
-- Adds sessions, engagement, acquisition and events, and one read function per
-- dashboard section. Still anonymous: no IP, user id or query string. A session
-- is the gm_sid cookie, which expires after 30 minutes without a page view.
--
--   site_visits  + pv_id (client page-view id), session_id, is_session_start,
--                  engaged_seconds, scroll_pct, channel, utm_*, browser, os
--   site_events  downloads and outbound clicks (sent by the browser) and
--                  sign_in / sign_up / order_placed / worksheet_generated /
--                  test_generated (recorded by the server itself)
--
-- Every function is service-role only. Re-runnable.

begin;

alter table public.site_visits
  add column if not exists pv_id            uuid,
  add column if not exists session_id       uuid,
  add column if not exists is_session_start boolean not null default false,
  add column if not exists engaged_seconds  integer not null default 0
    check (engaged_seconds between 0 and 86400),
  add column if not exists scroll_pct       smallint check (scroll_pct between 0 and 100),
  add column if not exists channel          text
    check (channel in ('direct', 'search', 'social', 'ai', 'email', 'paid', 'referral')),
  add column if not exists utm_source       text check (char_length(utm_source) <= 100),
  add column if not exists utm_medium       text check (char_length(utm_medium) <= 100),
  add column if not exists utm_campaign     text check (char_length(utm_campaign) <= 100),
  add column if not exists browser          text check (char_length(browser) <= 30),
  add column if not exists os               text check (char_length(os) <= 30);

create unique index if not exists uq_site_visits_pv      on public.site_visits (pv_id);
create index        if not exists idx_site_visits_session on public.site_visits (session_id, created_at);
create index        if not exists idx_site_visits_visitor on public.site_visits (visitor_id, created_at);

create table if not exists public.site_events (
  id         bigint generated always as identity primary key,
  created_at timestamptz not null default now(),
  visitor_id uuid not null,
  session_id uuid,
  name       text not null check (name in ('download', 'outbound', 'sign_in', 'sign_up',
                                           'order_placed', 'worksheet_generated', 'test_generated')),
  label      text check (char_length(label) <= 200),
  path       text check (char_length(path) <= 300)
);

create index if not exists idx_site_events_created on public.site_events (created_at);
create index if not exists idx_site_events_session on public.site_events (session_id);

alter table public.site_events enable row level security;
revoke all on public.site_events from anon, authenticated;
grant select, insert on public.site_events to service_role;

-- Engagement arrives after the page view, possibly more than once (tab hidden,
-- then shown again). Keep the largest values, and only for the visitor who
-- made the page view, so nobody can rewrite someone else's numbers.
create or replace function public.site_visit_engage(
  p_pv uuid, p_visitor uuid, p_seconds integer, p_scroll integer
) returns void
language sql
security definer
set search_path = public
as $$
  update public.site_visits
     set engaged_seconds = greatest(engaged_seconds, least(greatest(coalesce(p_seconds, 0), 0), 86400)),
         scroll_pct      = greatest(coalesce(scroll_pct, 0), least(greatest(coalesce(p_scroll, 0), 0), 100))
   where pv_id = p_pv
     and visitor_id = p_visitor
     and created_at > now() - interval '1 day';
$$;

-- Start of the window: midnight p_days - 1 days ago in p_tz.
create or replace function public.analytics_since(p_days integer, p_tz text)
returns timestamptz
language sql
stable
as $$
  select (((now() at time zone p_tz)::date - (greatest(1, least(coalesce(p_days, 30), 365)) - 1))::timestamp)
         at time zone p_tz;
$$;

-- Per-session facts used by several sections.
create or replace function public.analytics_sessions(p_days integer, p_tz text)
returns table (
  session_id uuid, visitor_id uuid, started_at timestamptz, pages bigint,
  engaged bigint, landing text, exit_path text, channel text, is_new boolean, bounced boolean
)
language sql
stable
security definer
set search_path = public
as $$
  with v as (
    select sv.*,
           row_number() over (partition by sv.session_id order by sv.created_at, sv.id)      as rn,
           row_number() over (partition by sv.session_id order by sv.created_at desc, sv.id desc) as rn_desc
    from public.site_visits sv
    where sv.session_id is not null and sv.created_at >= public.analytics_since(p_days, p_tz)
  )
  select v.session_id,
         min(v.visitor_id::text)::uuid,
         min(v.created_at),
         count(*),
         sum(v.engaged_seconds),
         max(v.path)    filter (where v.rn = 1),
         max(v.path)    filter (where v.rn_desc = 1),
         max(v.channel) filter (where v.rn = 1),
         bool_or(v.is_new_visitor),
         count(*) = 1 and sum(v.engaged_seconds) < 10
  from v
  group by v.session_id;
$$;

-- Overview (replaces 36's version, adding sessions and engagement).
create or replace function public.admin_site_analytics(
  p_days integer default 30,
  p_tz   text    default 'Asia/Dhaka'
) returns jsonb
language sql
stable
security definer
set search_path = public
as $$
with bounds as (
  select greatest(1, least(coalesce(p_days, 30), 365)) as days,
         (now() at time zone p_tz)::date                as today,
         public.analytics_since(p_days, p_tz)           as since
),
v as (
  select sv.*, (sv.created_at at time zone p_tz)::date as day
  from public.site_visits sv, bounds b
  where sv.created_at >= b.since
),
s as (select * from public.analytics_sessions(p_days, p_tz)),
days as (
  select d::date as day
  from bounds b, generate_series(b.today - (b.days - 1), b.today, interval '1 day') d
),
signups as (
  select (u.created_at at time zone p_tz)::date as day, count(*) as n
  from auth.users u, bounds b
  where u.created_at >= b.since
  group by 1
),
sess_daily as (
  select (started_at at time zone p_tz)::date as day, count(*) as n
  from s group by 1
),
daily as (
  select d.day,
         count(v.id)                                                  as views,
         count(distinct v.visitor_id)                                 as visitors,
         count(distinct v.visitor_id) filter (where v.is_new_visitor) as new_visitors,
         count(distinct v.visitor_id) filter (where v.signed_in)      as signed_in,
         coalesce(max(su.n), 0)                                       as signups,
         coalesce(max(sd.n), 0)                                       as sessions
  from days d
  left join v          on v.day = d.day
  left join signups su on su.day = d.day
  left join sess_daily sd on sd.day = d.day
  group by d.day
)
select jsonb_build_object(
  'days',     (select days from bounds),
  'timezone', p_tz,
  'totals', jsonb_build_object(
    'live',         (select count(distinct visitor_id) from public.site_visits
                      where created_at >= now() - interval '30 minutes'),
    'today',        (select count(distinct visitor_id) from v, bounds b where v.day = b.today),
    'yesterday',    (select count(distinct visitor_id) from v, bounds b where v.day = b.today - 1),
    'last7',        (select count(distinct visitor_id) from v, bounds b where v.day > b.today - 7),
    'visitors',     (select count(distinct visitor_id) from v),
    'new_visitors', (select count(distinct visitor_id) from v where is_new_visitor),
    'views',        (select count(*) from v),
    'signups',      (select coalesce(sum(n), 0) from signups),
    'sessions',     (select count(*) from s),
    'bounce_rate',  (select round(100.0 * count(*) filter (where bounced) / nullif(count(*), 0), 1) from s),
    'pages_per_session', (select round(avg(pages), 2) from s),
    'avg_session_seconds', (select round(avg(engaged)) from s),
    'avg_engaged_seconds', (select round(avg(engaged_seconds)) from v where engaged_seconds > 0),
    'tracking_since', (select min(created_at) from public.site_visits)
  ),
  'daily', (select coalesce(jsonb_agg(jsonb_build_object(
              'day', day, 'views', views, 'visitors', visitors, 'new_visitors', new_visitors,
              'signed_in', signed_in, 'signups', signups, 'sessions', sessions
            ) order by day), '[]'::jsonb) from daily),
  'pages', (select coalesce(jsonb_agg(jsonb_build_object(
                'path', path, 'views', views, 'visitors', visitors) order by views desc), '[]'::jsonb)
            from (select path, count(*) as views, count(distinct visitor_id) as visitors
                  from v group by path order by count(*) desc limit 25) t),
  'referrers', (select coalesce(jsonb_agg(jsonb_build_object(
                'host', host, 'visitors', visitors) order by visitors desc), '[]'::jsonb)
            from (select coalesce(referrer_host, 'Direct / unknown') as host,
                         count(distinct visitor_id) as visitors
                  from v where is_new_visitor or referrer_host is not null
                  group by 1 order by 2 desc limit 15) t),
  'countries', (select coalesce(jsonb_agg(jsonb_build_object(
                'country', country, 'visitors', visitors) order by visitors desc), '[]'::jsonb)
            from (select coalesce(country, '??') as country, count(distinct visitor_id) as visitors
                  from v group by 1 order by 2 desc limit 15) t),
  'devices', (select coalesce(jsonb_agg(jsonb_build_object(
                'device', device, 'visitors', visitors) order by visitors desc), '[]'::jsonb)
            from (select device, count(distinct visitor_id) as visitors
                  from v group by 1) t)
);
$$;

-- Behaviour: what people do once they arrive.
create or replace function public.admin_behavior(
  p_days integer default 30,
  p_tz   text    default 'Asia/Dhaka'
) returns jsonb
language sql
stable
security definer
set search_path = public
as $$
with v as (
  select sv.*,
         row_number() over w                                  as rn,
         count(*)     over (partition by sv.session_id)       as n,
         sum(sv.engaged_seconds) over (partition by sv.session_id) as sess_engaged,
         lead(sv.path) over w                                 as next_path
  from public.site_visits sv
  where sv.created_at >= public.analytics_since(p_days, p_tz)
  window w as (partition by sv.session_id order by sv.created_at, sv.id)
),
s as (select * from public.analytics_sessions(p_days, p_tz)),
e as (
  select * from public.site_events
  where created_at >= public.analytics_since(p_days, p_tz)
),
pages as (
  select path,
         count(*)                                                        as views,
         count(distinct visitor_id)                                      as visitors,
         count(*) filter (where session_id is not null and rn = 1)       as entries,
         count(*) filter (where session_id is not null and rn = n)       as exits,
         count(*) filter (where session_id is not null and rn = 1 and n = 1 and sess_engaged < 10) as bounces,
         round(avg(engaged_seconds) filter (where engaged_seconds > 0))  as avg_engaged,
         round(avg(scroll_pct) filter (where scroll_pct is not null))    as avg_scroll
  from v group by path
)
select jsonb_build_object(
  'sessions', jsonb_build_object(
    'count',          (select count(*) from s),
    'bounce_rate',    (select round(100.0 * count(*) filter (where bounced) / nullif(count(*), 0), 1) from s),
    'pages_per_session', (select round(avg(pages), 2) from s),
    'avg_seconds',    (select round(avg(engaged)) from s),
    'median_seconds', (select percentile_cont(0.5) within group (order by engaged) from s)
  ),
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
    from (select * from pages order by views desc limit 50) t),
  'flows', (select coalesce(jsonb_agg(jsonb_build_object('from', path, 'to', next_path, 'count', n) order by n desc), '[]'::jsonb)
    from (select path, next_path, count(*) as n from v
          where session_id is not null and next_path is not null and next_path <> path
          group by 1, 2 order by 3 desc limit 30) t),
  'landing', (select coalesce(jsonb_agg(jsonb_build_object('path', landing, 'sessions', n,
              'bounce_rate', br, 'avg_seconds', secs) order by n desc), '[]'::jsonb)
    from (select landing, count(*) as n,
                 round(100.0 * count(*) filter (where bounced) / count(*), 1) as br,
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

-- Acquisition: where visits come from and how each source behaves.
create or replace function public.admin_acquisition(
  p_days integer default 30,
  p_tz   text    default 'Asia/Dhaka'
) returns jsonb
language sql
stable
security definer
set search_path = public
as $$
with starts as (
  select sv.* from public.site_visits sv
  where sv.is_session_start and sv.created_at >= public.analytics_since(p_days, p_tz)
),
s as (select * from public.analytics_sessions(p_days, p_tz)),
days as (
  select d::date as day
  from generate_series((public.analytics_since(p_days, p_tz) at time zone p_tz)::date,
                       (now() at time zone p_tz)::date, interval '1 day') d
)
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
  'landing', (select coalesce(jsonb_agg(jsonb_build_object('path', landing, 'channel', channel,
                 'sessions', n) order by n desc), '[]'::jsonb)
    from (select landing, coalesce(channel, 'direct') as channel, count(*) as n
          from s group by 1, 2 order by 3 desc limit 20) t),
  'new_vs_returning', jsonb_build_object(
    'new',       (select count(*) from s where is_new),
    'returning', (select count(*) from s where not is_new)),
  'countries', (select coalesce(jsonb_agg(jsonb_build_object('country', country, 'sessions', n,
                 'visitors', u) order by n desc), '[]'::jsonb)
    from (select coalesce(country, '??') as country, count(*) as n, count(distinct visitor_id) as u
          from starts group by 1 order by 2 desc limit 20) t)
);
$$;

-- Funnels: share of sessions that reach each step, in order.
create or replace function public.admin_funnels(
  p_days integer default 30,
  p_tz   text    default 'Asia/Dhaka'
) returns jsonb
language sql
stable
security definer
set search_path = public
as $$
with v as (
  select * from public.site_visits
  where session_id is not null and created_at >= public.analytics_since(p_days, p_tz)
),
e as (
  select * from public.site_events
  where session_id is not null and created_at >= public.analytics_since(p_days, p_tz)
),
paper as (
  select v.session_id,
         min(v.created_at) as s1,
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

-- Retention: weekly cohorts by the week a visitor was first seen.
create or replace function public.admin_retention(
  p_weeks integer default 8,
  p_tz    text    default 'Asia/Dhaka'
) returns jsonb
language sql
stable
security definer
set search_path = public
as $$
with params as (
  select greatest(2, least(coalesce(p_weeks, 8), 26)) as weeks,
         date_trunc('week', now() at time zone p_tz)::date as this_week
),
visits as (
  select visitor_id, date_trunc('week', created_at at time zone p_tz)::date as week
  from public.site_visits
  group by 1, 2
),
firsts as (
  select visitor_id, min(week) as cohort from visits group by 1
),
cohorts as (
  select f.cohort, count(*) as size
  from firsts f, params p
  where f.cohort > p.this_week - 7 * p.weeks
  group by 1
),
cells as (
  select f.cohort, ((vi.week - f.cohort) / 7) as offs, count(distinct vi.visitor_id) as n
  from firsts f join visits vi using (visitor_id)
  group by 1, 2
)
select jsonb_build_object(
  'weeks', (select weeks from params),
  'cohorts', (select coalesce(jsonb_agg(jsonb_build_object(
      'week', c.cohort, 'size', c.size,
      'retained', (select jsonb_agg(coalesce((select ce.n from cells ce where ce.cohort = c.cohort and ce.offs = o), 0) order by o)
                   from params p, generate_series(0, ((p.this_week - c.cohort) / 7)) o)
    ) order by c.cohort desc), '[]'::jsonb) from cohorts c)
);
$$;

-- Patterns: when people come and what they use.
create or replace function public.admin_patterns(
  p_days integer default 30,
  p_tz   text    default 'Asia/Dhaka'
) returns jsonb
language sql
stable
security definer
set search_path = public
as $$
with v as (
  select * from public.site_visits where created_at >= public.analytics_since(p_days, p_tz)
)
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

-- Realtime: the last 30 minutes.
create or replace function public.admin_realtime()
returns jsonb
language sql
stable
security definer
set search_path = public
as $$
with v as (
  select * from public.site_visits where created_at >= now() - interval '30 minutes'
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
  'events',     (select coalesce(jsonb_agg(jsonb_build_object('at', created_at, 'name', name, 'label', label)
                   order by created_at desc), '[]'::jsonb)
                 from (select * from public.site_events where created_at >= now() - interval '30 minutes'
                       order by created_at desc limit 15) t)
);
$$;

revoke all on function public.site_visit_engage(uuid, uuid, integer, integer) from public, anon, authenticated;
revoke all on function public.analytics_since(integer, text)                  from public, anon, authenticated;
revoke all on function public.analytics_sessions(integer, text)               from public, anon, authenticated;
revoke all on function public.admin_site_analytics(integer, text)             from public, anon, authenticated;
revoke all on function public.admin_behavior(integer, text)                   from public, anon, authenticated;
revoke all on function public.admin_acquisition(integer, text)                from public, anon, authenticated;
revoke all on function public.admin_funnels(integer, text)                    from public, anon, authenticated;
revoke all on function public.admin_retention(integer, text)                  from public, anon, authenticated;
revoke all on function public.admin_patterns(integer, text)                   from public, anon, authenticated;
revoke all on function public.admin_realtime()                                from public, anon, authenticated;

grant execute on function public.site_visit_engage(uuid, uuid, integer, integer) to service_role;
grant execute on function public.analytics_since(integer, text)                  to service_role;
grant execute on function public.analytics_sessions(integer, text)               to service_role;
grant execute on function public.admin_site_analytics(integer, text)             to service_role;
grant execute on function public.admin_behavior(integer, text)                   to service_role;
grant execute on function public.admin_acquisition(integer, text)                to service_role;
grant execute on function public.admin_funnels(integer, text)                    to service_role;
grant execute on function public.admin_retention(integer, text)                  to service_role;
grant execute on function public.admin_patterns(integer, text)                   to service_role;
grant execute on function public.admin_realtime()                                to service_role;

commit;
