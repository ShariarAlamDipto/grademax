-- 43: free sign-in after 20 PDF downloads a day (DownloadGate). Run after 42.
-- Allows the browser event gate_shown and adds a "download limit -> signed in"
-- funnel. Re-runnable.

begin;

alter table public.site_events drop constraint if exists site_events_name_check;
alter table public.site_events add constraint site_events_name_check check (name in (
  'download', 'outbound', 'js_error', 'gate_shown', 'sign_in', 'sign_up', 'sign_in_failed', 'order_placed',
  'worksheet_generated', 'worksheet_failed', 'test_generated', 'test_failed', 'limit_reached'));

-- Funnels (as 41, plus the download-limit funnel; 41's notes:
-- rewritten to scale: events are grouped per visit once and
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
         min(created_at) filter (where name in ('worksheet_generated', 'test_generated')) as generated,
         min(created_at) filter (where name = 'gate_shown')                          as gate_shown
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
  select pv.*, pe.sign_in, pe.sign_up, pe.ordered, pe.generated, pe.gate_shown,
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
    from f),
  -- The free sign-in prompt after the daily download limit (migration 43).
  'gate', (select jsonb_build_array(
      jsonb_build_object('step', 'Reached the download limit', 'sessions', count(*) filter (where gate_shown is not null)),
      jsonb_build_object('step', 'Signed in afterwards', 'sessions', count(*) filter (where gate_shown is not null and signed_in_at >= gate_shown)))
    from f)
);
$$;

-- admin_funnels keeps its earlier grants.

commit;
