-- Newsletter subscribers table
create table if not exists newsletter_subscribers (
  id          uuid primary key default gen_random_uuid(),
  email       text not null unique,
  subscribed_at timestamptz not null default now()
);

-- Only service role can insert/read; no public access
alter table newsletter_subscribers enable row level security;

create policy "service role only"
  on newsletter_subscribers
  for all
  using (auth.role() = 'service_role');
