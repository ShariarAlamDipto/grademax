-- 44: the admin Usage report is counted in Postgres, from a daily summary.
-- Run after 43. Re-runnable. Adds one table, one trigger, one index, one function.
--
-- Found on live data (6 Nov 2026): /api/admin/analytics/usage paged through at
-- most the newest 20,000 usage_events rows per list. With ~13,000 server-side
-- paper_view rows a day, that window was under one day, so the "last 30 days"
-- chart, Top papers and Paper views by subject described only the last ~22
-- hours.
--
-- usage_events is ~500k rows (168 MB, mostly paper_view rows from scrapers
-- before the viewer fix). One pass over it takes 2-15 s on this instance, past
-- the API's 8 s limit, so the report reads usage_daily instead: one row per
-- Dhaka day, feature, subject and (for paper_view) paper title, kept current
-- by a trigger and filled once from history below. Distinct users cannot be
-- summed per day, so they come from a small partial index instead.

begin;

create table if not exists public.usage_daily (
  day      date    not null,
  feature  text    not null,
  subject  text    not null default '',   -- '' when the row named none
  title    text    not null default '',   -- paper_view only; '' otherwise
  n        integer not null default 0 check (n >= 0),
  primary key (day, feature, subject, title)
);
-- Only the service role reads it (the admin API); no policies = no client access.
alter table public.usage_daily enable row level security;

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
  return null;
end;
$$;

drop trigger if exists trg_usage_daily_bump on public.usage_events;
create trigger trg_usage_daily_bump after insert on public.usage_events
  for each row execute function public.usage_daily_bump();

-- Fill from history. Inside this transaction the trigger and the backfill
-- cannot double count: rows inserted while the migration runs wait for the
-- table lock below, then go through the trigger.
lock table public.usage_events in share mode;
truncate public.usage_daily;
insert into public.usage_daily (day, feature, subject, title, n)
select (created_at at time zone 'Asia/Dhaka')::date, feature, coalesce(subject_name, ''),
       case when feature = 'paper_view' then coalesce(nullif(metadata->>'title', ''), 'Unknown') else '' end,
       count(*)
from public.usage_events
group by 1, 2, 3, 4;

create index if not exists idx_usage_events_feature_user
  on public.usage_events (feature, user_id) where user_id is not null;

create or replace function public.admin_usage(p_days integer default 30)
returns jsonb
language sql
stable
security definer
set search_path = public
as $$
with since as (
  -- Summary days are Dhaka days; the period is the last p_days of them.
  select (now() at time zone 'Asia/Dhaka')::date - (greatest(1, least(coalesce(p_days, 30), 365)) - 1) as day
)
select jsonb_build_object(
  'first_day', (select day from since),
  'timezone', 'Asia/Dhaka',
  'totals', (select coalesce(jsonb_agg(jsonb_build_object('feature', feature, 'count', n)), '[]'::jsonb)
             from (select feature, sum(n) as n from public.usage_daily group by 1) x),
  'users', (select coalesce(jsonb_agg(jsonb_build_object('feature', feature, 'users', n)), '[]'::jsonb)
            from (select feature, count(distinct user_id) as n from public.usage_events
                  where user_id is not null group by 1) x),
  'daily', (select coalesce(jsonb_agg(jsonb_build_object('date', d.day, 'feature', d.feature, 'count', d.n) order by d.day), '[]'::jsonb)
            from (select u.day, u.feature, sum(u.n) as n from public.usage_daily u, since
                  where u.day >= since.day group by 1, 2) d),
  'subjects', (select coalesce(jsonb_agg(jsonb_build_object('feature', feature, 'subject', subject, 'count', n) order by n desc), '[]'::jsonb)
               from (select feature, case when subject = '' then 'Unknown' else subject end as subject, sum(n) as n
                     from public.usage_daily
                     where feature = 'paper_view'
                        or (subject <> '' and feature in
                            ('worksheet_generate', 'worksheet_download', 'test_builder_session', 'test_builder_download'))
                     group by 1, 2) x),
  'papers', (select coalesce(jsonb_agg(jsonb_build_object('title', title, 'total', total, 'last30', recent) order by total desc), '[]'::jsonb)
             from (select u.title, sum(u.n) as total, coalesce(sum(u.n) filter (where u.day >= since.day), 0) as recent
                   from public.usage_daily u, since where u.feature = 'paper_view'
                   group by 1 order by 2 desc limit 30) x)
);
$$;

revoke all on function public.admin_usage(integer) from public, anon, authenticated;
grant execute on function public.admin_usage(integer) to service_role;
revoke all on function public.usage_daily_bump() from public, anon, authenticated;

commit;
