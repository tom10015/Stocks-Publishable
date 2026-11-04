-- Run in a DEDICATED Supabase project for Stocks-Publishable.
create table if not exists public.admin_members(user_id uuid primary key references auth.users(id) on delete cascade);
create table if not exists public.admin_tickers(ticker text primary key check (ticker ~ '^[A-Z0-9.-]{1,12}$'),visible boolean not null default true,created_at timestamptz not null default now());
alter table public.admin_members enable row level security;
alter table public.admin_tickers enable row level security;
revoke all on public.admin_members from anon;
revoke all on public.admin_tickers from anon;
grant select on public.admin_members to authenticated;
grant select,insert,update,delete on public.admin_tickers to authenticated;
create policy "admin can verify own membership" on public.admin_members for select to authenticated using (user_id=(select auth.uid()));
create policy "admins can read tickers" on public.admin_tickers for select to authenticated using (exists(select 1 from public.admin_members where user_id=(select auth.uid())));
create policy "admins can insert tickers" on public.admin_tickers for insert to authenticated with check (exists(select 1 from public.admin_members where user_id=(select auth.uid())));
create policy "admins can update tickers" on public.admin_tickers for update to authenticated using (exists(select 1 from public.admin_members where user_id=(select auth.uid()))) with check (exists(select 1 from public.admin_members where user_id=(select auth.uid())));
create policy "admins can delete tickers" on public.admin_tickers for delete to authenticated using (exists(select 1 from public.admin_members where user_id=(select auth.uid())));
-- After creating an Auth user, grant admin using SQL Editor (not public UI):
-- insert into public.admin_members(user_id) values ('REPLACE-WITH-AUTH-USER-UUID');
