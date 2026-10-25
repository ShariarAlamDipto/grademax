-- 36: first-party visitor analytics (Admin → Analytics → Visitors).
--
-- Why: daily visitor numbers came from Vercel Analytics, which stopped when the
-- site moved to the self-hosted Docker server (Oct 2026). Every page view is now
-- recorded here by /api/visit.
--
-- Privacy: no IP address, no user id, no query string. `visitor_id` is a random
-- UUID from the first-party `gm_vid` cookie, so unique visitors can be counted.
--
-- The dashboard reads one RPC, admin_site_analytics(), because PostgREST caps
-- selects at 1000 rows and aggregate functions are disabled on this instance.
-- Both objects are service-role only.

begin;

create table if not exists public.site_visits (
  id             bigint generated always as identity primary key,
  created_at     timestamptz not null default now(),
  visitor_id     uuid not null,
  is_new_visitor boolean not null default false,
  signed_in      boolean not null default false,
  path           text not null check (char_length(path) between 1 and 300),
  referrer_host  text check (char_length(referrer_host) <= 120),
  country        text check (country ~ '^[A-Z]{2}$'),
  device         text not null check (device in ('mobile', 'tablet', 'desktop'))
);

create index if not exists idx_site_visits_created on public.site_visits (created_at);

-- No policies: only the service role (which bypasses RLS) reads or writes.
alter table public.site_visits enable row level security;
revoke all on public.site_visits from anon, authenticated;
grant select, insert on public.site_visits to service_role;

-- Everything the Visitors dashboard shows, for the last p_days local days
-- (p_tz, default Asia/Dhaka, where most visitors are).
create or replace function public.admin_site_analytics(
  p_days integer default 30,
  p_tz   text    default 'Asia/Dhaka'
) returns jsonb
language sql
stable
security definer
set search_path = public
as $$
with params as (
  select greatest(1, least(coalesce(p_days, 30), 365)) as days,
         (now() at time zone p_tz)::date               as today
),
bounds as (
  select days, today,
         today - (days - 1)                         as first_day,
         ((today - (days - 1))::timestamp) at time zone p_tz as since
  from params
),
v as (
  select sv.*, (sv.created_at at time zone p_tz)::date as day
  from public.site_visits sv, bounds b
  where sv.created_at >= b.since
),
days as (
  select d::date as day
  from bounds b, generate_series(b.first_day, b.today, interval '1 day') d
),
signups as (
  select (u.created_at at time zone p_tz)::date as day, count(*) as n
  from auth.users u, bounds b
  where u.created_at >= b.since
  group by 1
),
daily as (
  select d.day,
         count(v.id)                                                  as views,
         count(distinct v.visitor_id)                                 as visitors,
         count(distinct v.visitor_id) filter (where v.is_new_visitor) as new_visitors,
         count(distinct v.visitor_id) filter (where v.signed_in)      as signed_in,
         coalesce(max(s.n), 0)                                        as signups
  from days d
  left join v       on v.day = d.day
  left join signups s on s.day = d.day
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
    'tracking_since', (select min(created_at) from public.site_visits)
  ),
  'daily', (select coalesce(jsonb_agg(jsonb_build_object(
              'day', day, 'views', views, 'visitors', visitors,
              'new_visitors', new_visitors, 'signed_in', signed_in, 'signups', signups
            ) order by day), '[]'::jsonb) from daily),
  'pages', (select coalesce(jsonb_agg(jsonb_build_object(
                'path', path, 'views', views, 'visitors', visitors) order by views desc), '[]'::jsonb)
            from (select path, count(*) as views, count(distinct visitor_id) as visitors
                  from v group by path order by count(*) desc limit 25) t),
  -- Where visitors came from: the referrer of each first visit, plus any
  -- later visit that arrived from another site.
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

revoke all on function public.admin_site_analytics(integer, text) from public, anon, authenticated;
grant execute on function public.admin_site_analytics(integer, text) to service_role;

commit;
