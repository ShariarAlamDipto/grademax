-- 40: real-user performance, browser errors and Telegram alerts. Run after 38.
-- (39 is reserved for the business analytics migration.)
--
--   * site_visits gets Core Web Vitals per page view (the landing page of each
--     tab load: LCP, INP, CLS x1000, FCP, TTFB), set by site_visit_vital().
--   * site_events accepts js_error (message @ file:line, sanitised by the app).
--   * admin_performance(): percentiles, good/poor shares, by device, country and
--     page, daily trend, top errors.
--   * analytics_alerts + analytics_alert_check(): rules with thresholds and a
--     6-hour cooldown; the app sends what it returns to the shop's Telegram.
--
-- Re-runnable. Service role only.

begin;

alter table public.site_visits
  add column if not exists lcp_ms    integer check (lcp_ms    between 0 and 120000),
  add column if not exists inp_ms    integer check (inp_ms    between 0 and 60000),
  add column if not exists cls_milli integer check (cls_milli between 0 and 50000),
  add column if not exists fcp_ms    integer check (fcp_ms    between 0 and 120000),
  add column if not exists ttfb_ms   integer check (ttfb_ms   between 0 and 120000);

alter table public.site_events drop constraint if exists site_events_name_check;
alter table public.site_events add constraint site_events_name_check check (name in (
  'download', 'outbound', 'js_error', 'sign_in', 'sign_up', 'sign_in_failed', 'order_placed',
  'worksheet_generated', 'worksheet_failed', 'test_generated', 'test_failed', 'limit_reached'));

-- One metric for one page view, only for the visitor who made it.
create or replace function public.site_visit_vital(p_pv uuid, p_visitor uuid, p_name text, p_value numeric)
returns void
language sql
security definer
set search_path = public
as $$
  update public.site_visits
     set lcp_ms    = case when p_name = 'LCP'  then least(round(p_value), 120000)::int        else lcp_ms    end,
         inp_ms    = case when p_name = 'INP'  then least(round(p_value), 60000)::int         else inp_ms    end,
         cls_milli = case when p_name = 'CLS'  then least(round(p_value * 1000), 50000)::int  else cls_milli end,
         fcp_ms    = case when p_name = 'FCP'  then least(round(p_value), 120000)::int        else fcp_ms    end,
         ttfb_ms   = case when p_name = 'TTFB' then least(round(p_value), 120000)::int        else ttfb_ms   end
   where pv_id = p_pv
     and visitor_id = p_visitor
     and p_name in ('LCP', 'INP', 'CLS', 'FCP', 'TTFB')
     and p_value >= 0
     and created_at > now() - interval '1 day';
$$;

-- Percentile summary for one metric column of a set of page views.
-- Thresholds are Google's: good <= first, poor > second.
create or replace function public.analytics_vital_summary(p_values integer[], p_good integer, p_poor integer)
returns jsonb
language sql
immutable
as $$
  with x as (select unnest(p_values) as v)
  select jsonb_build_object(
    'samples', (select count(*) from x),
    'p50', (select round(percentile_cont(0.50) within group (order by v)::numeric) from x),
    'p75', (select round(percentile_cont(0.75) within group (order by v)::numeric) from x),
    'p95', (select round(percentile_cont(0.95) within group (order by v)::numeric) from x),
    'good', (select round(100.0 * count(*) filter (where v <= p_good) / nullif(count(*), 0), 1) from x),
    'poor', (select round(100.0 * count(*) filter (where v >  p_poor) / nullif(count(*), 0), 1) from x)
  );
$$;

create or replace function public.admin_performance(
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
  select sv.* from b, public.analytics_visits(b.since, b.until, p_country) sv
  where coalesce(sv.lcp_ms, sv.inp_ms, sv.cls_milli, sv.fcp_ms, sv.ttfb_ms) is not null
),
e as (select ev.* from b, public.analytics_events(b.since, b.until, p_country) ev where ev.name = 'js_error'),
days as (select d::date as day from b, generate_series(b.first_day, b.last_day, interval '1 day') d)
select jsonb_build_object(
  'first_day', (select first_day from b), 'last_day', (select last_day from b), 'partial', (select partial from b),
  'metrics', jsonb_build_object(
    'LCP',  (select public.analytics_vital_summary(array_agg(lcp_ms)    filter (where lcp_ms    is not null), 2500, 4000) from v),
    'INP',  (select public.analytics_vital_summary(array_agg(inp_ms)    filter (where inp_ms    is not null), 200, 500)   from v),
    'CLS',  (select public.analytics_vital_summary(array_agg(cls_milli) filter (where cls_milli is not null), 100, 250)   from v),
    'FCP',  (select public.analytics_vital_summary(array_agg(fcp_ms)    filter (where fcp_ms    is not null), 1800, 3000) from v),
    'TTFB', (select public.analytics_vital_summary(array_agg(ttfb_ms)   filter (where ttfb_ms   is not null), 800, 1800)  from v)),
  'by_device', (select coalesce(jsonb_agg(jsonb_build_object('device', device, 'samples', n, 'lcp_p75', lcp, 'inp_p75', inp, 'cls_p75', cls) order by n desc), '[]'::jsonb)
    from (select device, count(*) as n,
                 round(percentile_cont(0.75) within group (order by lcp_ms)::numeric)    as lcp,
                 round(percentile_cont(0.75) within group (order by inp_ms)::numeric)    as inp,
                 round(percentile_cont(0.75) within group (order by cls_milli)::numeric) as cls
          from v group by 1) t),
  'by_country', (select coalesce(jsonb_agg(jsonb_build_object('country', cc, 'samples', n, 'lcp_p75', lcp, 'ttfb_p75', ttfb) order by n desc), '[]'::jsonb)
    from (select coalesce(country, '??') as cc, count(*) as n,
                 round(percentile_cont(0.75) within group (order by lcp_ms)::numeric)  as lcp,
                 round(percentile_cont(0.75) within group (order by ttfb_ms)::numeric) as ttfb
          from v group by 1 order by 2 desc limit 15) t),
  -- Slowest landing pages with enough samples to mean something.
  'slow_pages', (select coalesce(jsonb_agg(jsonb_build_object('path', path, 'samples', n, 'lcp_p75', lcp, 'inp_p75', inp, 'cls_p75', cls) order by lcp desc nulls last), '[]'::jsonb)
    from (select path, count(*) as n,
                 round(percentile_cont(0.75) within group (order by lcp_ms)::numeric)    as lcp,
                 round(percentile_cont(0.75) within group (order by inp_ms)::numeric)    as inp,
                 round(percentile_cont(0.75) within group (order by cls_milli)::numeric) as cls
          from v group by 1 having count(*) >= 5 order by 3 desc nulls last limit 20) t),
  'daily', (select coalesce(jsonb_agg(row_to_json(t)::jsonb order by t.day), '[]'::jsonb) from (
      select d.day,
             round(percentile_cont(0.75) within group (order by v.lcp_ms)::numeric) as lcp_p75,
             round(percentile_cont(0.75) within group (order by v.inp_ms)::numeric) as inp_p75,
             count(v.id) as samples
      from days d left join v on (v.created_at at time zone p_tz)::date = d.day
      group by d.day) t),
  'errors', jsonb_build_object(
    'total',    (select count(*) from e),
    'visitors', (select count(distinct visitor_id) from e),
    'top', (select coalesce(jsonb_agg(jsonb_build_object('label', label, 'count', n, 'visitors', u, 'last_path', lp) order by n desc), '[]'::jsonb)
            from (select label, count(*) as n, count(distinct visitor_id) as u,
                         (array_agg(path order by created_at desc))[1] as lp
                  from e group by 1 order by 2 desc limit 20) t))
);
$$;

-- Alerting: one row per rule holds its last send (cooldown) plus a '_check'
-- row that limits how often the rules are evaluated at all.
create table if not exists public.analytics_alerts (
  rule        text primary key check (char_length(rule) <= 40),
  last_sent   timestamptz,
  last_value  numeric
);
alter table public.analytics_alerts enable row level security;
revoke all on public.analytics_alerts from anon, authenticated;

-- Returns the alerts to send now, already marked as sent. At most one
-- evaluation per 15 minutes and one message per rule per 6 hours.
create or replace function public.analytics_alert_check()
returns jsonb
language plpgsql
security definer
set search_path = public
as $$
declare
  v_due      boolean;
  v_out      jsonb := '[]'::jsonb;
  v_failed   bigint; v_ok bigint;
  v_sfail    bigint; v_sok bigint;
  v_visitors bigint; v_unknown bigint;
  v_backlog  bigint; v_oldest numeric;
  v_errors   bigint; v_err_visitors bigint;
begin
  insert into analytics_alerts (rule, last_sent) values ('_check', now() - interval '1 hour')
    on conflict (rule) do nothing;
  update analytics_alerts set last_sent = now()
   where rule = '_check' and last_sent < now() - interval '15 minutes'
  returning true into v_due;
  if v_due is null then return v_out; end if;

  -- 1. Worksheet/test generation failing (last hour).
  select count(*) filter (where name in ('worksheet_failed', 'test_failed')),
         count(*) filter (where name in ('worksheet_generated', 'test_generated'))
    into v_failed, v_ok
    from site_events where created_at > now() - interval '1 hour';
  if v_failed >= 5 and v_failed > 0.2 * (v_failed + v_ok) then
    v_out := v_out || jsonb_build_object('rule', 'tool_failures', 'value', v_failed,
      'message', format('%s of %s worksheet/test requests failed in the last hour. Check Admin → Analytics → Tools & health.', v_failed, v_failed + v_ok));
  end if;

  -- 2. Sign-in failing (last hour).
  select count(*) filter (where name = 'sign_in_failed'),
         count(*) filter (where name in ('sign_in', 'sign_up'))
    into v_sfail, v_sok
    from site_events where created_at > now() - interval '1 hour';
  if v_sfail >= 5 and v_sfail > 0.3 * (v_sfail + v_sok) then
    v_out := v_out || jsonb_build_object('rule', 'sign_in_failures', 'value', v_sfail,
      'message', format('%s of %s sign-ins failed in the last hour.', v_sfail, v_sfail + v_sok));
  end if;

  -- 3. Country data missing (Cloudflare header lost), last 6 hours.
  select count(distinct visitor_id), count(distinct visitor_id) filter (where country is null)
    into v_visitors, v_unknown
    from site_visits where created_at > now() - interval '6 hours';
  if v_visitors >= 50 and v_unknown > 0.2 * v_visitors then
    v_out := v_out || jsonb_build_object('rule', 'unknown_country', 'value', v_unknown,
      'message', format('Country is unknown for %s of %s visitors in the last 6 hours. Cloudflare IP geolocation may be off.', v_unknown, v_visitors));
  end if;

  -- 4. Payments waiting for verification longer than the 12-hour promise.
  select count(*), round(extract(epoch from now() - min(created_at)) / 3600)
    into v_backlog, v_oldest
    from store_payments where status = 'submitted' and created_at < now() - interval '12 hours';
  if v_backlog > 0 then
    v_out := v_out || jsonb_build_object('rule', 'payment_backlog', 'value', v_backlog,
      'message', format('%s payment(s) waiting for verification for over 12 hours (oldest %s h). Admin → Store.', v_backlog, v_oldest));
  end if;

  -- 5. A burst of browser errors (last hour).
  select count(*), count(distinct visitor_id) into v_errors, v_err_visitors
    from site_events where name = 'js_error' and created_at > now() - interval '1 hour';
  if v_err_visitors >= 10 then
    v_out := v_out || jsonb_build_object('rule', 'js_errors', 'value', v_errors,
      'message', format('%s JavaScript errors hit %s visitors in the last hour. See Admin → Analytics → Performance.', v_errors, v_err_visitors));
  end if;

  -- Keep only rules out of cooldown, and mark them sent.
  with candidates as (select a from jsonb_array_elements(v_out) a),
  sent as (
    insert into analytics_alerts (rule, last_sent, last_value)
    select c.a->>'rule', now(), (c.a->>'value')::numeric from candidates c
    on conflict (rule) do update set last_sent = excluded.last_sent, last_value = excluded.last_value
      where analytics_alerts.last_sent is null or analytics_alerts.last_sent < now() - interval '6 hours'
    returning rule
  )
  select coalesce(jsonb_agg(c.a), '[]'::jsonb) into v_out
    from candidates c where c.a->>'rule' in (select rule from sent);
  return v_out;
end;
$$;

revoke all on function public.site_visit_vital(uuid, uuid, text, numeric)               from public, anon, authenticated;
revoke all on function public.analytics_vital_summary(integer[], integer, integer)      from public, anon, authenticated;
revoke all on function public.admin_performance(integer, text, text, date, date)        from public, anon, authenticated;
revoke all on function public.analytics_alert_check()                                   from public, anon, authenticated;
grant execute on function public.site_visit_vital(uuid, uuid, text, numeric)            to service_role;
grant execute on function public.analytics_vital_summary(integer[], integer, integer)   to service_role;
grant execute on function public.admin_performance(integer, text, text, date, date)     to service_role;
grant execute on function public.analytics_alert_check()                                to service_role;

commit;
