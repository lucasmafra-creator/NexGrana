-- FinanceHub V2 RC — execute UMA VEZ no SQL Editor do Supabase.
-- É seguro executar novamente: tabelas usam IF NOT EXISTS e policies são recriadas.

create table if not exists public.financial_goals (
  id uuid primary key default gen_random_uuid(),
  household_id uuid not null references public.households(id) on delete cascade,
  name text not null,
  target_amount numeric(14,2) not null check (target_amount >= 0),
  saved_amount numeric(14,2) not null default 0 check (saved_amount >= 0),
  target_date date not null,
  strategy text not null default 'Equilibrada',
  status text not null default 'active' check (status in ('active','completed','cancelled')),
  created_by uuid not null references auth.users(id),
  created_at timestamptz not null default now()
);

create table if not exists public.wallet_accounts (
  id uuid primary key default gen_random_uuid(),
  household_id uuid not null references public.households(id) on delete cascade,
  member_id uuid references public.household_members(id) on delete set null,
  name text not null,
  wallet_type text not null,
  limit_amount numeric(14,2) not null default 0 check (limit_amount >= 0),
  closing_day integer not null default 0 check (closing_day between 0 and 31),
  due_day integer not null default 0 check (due_day between 0 and 31),
  created_by uuid not null references auth.users(id),
  created_at timestamptz not null default now()
);

create table if not exists public.semester_summaries (
  id uuid primary key default gen_random_uuid(),
  household_id uuid not null references public.households(id) on delete cascade,
  period_start date not null,
  period_end date not null,
  total_income numeric(14,2) not null default 0,
  total_expense numeric(14,2) not null default 0,
  balance numeric(14,2) not null default 0,
  categories jsonb not null default '{}'::jsonb,
  created_by uuid not null references auth.users(id),
  created_at timestamptz not null default now(),
  unique(household_id, period_start)
);

alter table public.financial_goals enable row level security;
alter table public.wallet_accounts enable row level security;
alter table public.semester_summaries enable row level security;

drop policy if exists "income household update" on public.income;
create policy "income household update" on public.income
for update to authenticated using (public.is_household_member(household_id))
with check (public.is_household_member(household_id));

drop policy if exists "goals household read" on public.financial_goals;
drop policy if exists "goals household insert" on public.financial_goals;
drop policy if exists "goals household update" on public.financial_goals;
drop policy if exists "goals household delete" on public.financial_goals;
create policy "goals household read" on public.financial_goals
for select to authenticated using (public.is_household_member(household_id));
create policy "goals household insert" on public.financial_goals
for insert to authenticated with check (public.is_household_member(household_id) and created_by=auth.uid());
create policy "goals household update" on public.financial_goals
for update to authenticated using (public.is_household_member(household_id))
with check (public.is_household_member(household_id));
create policy "goals household delete" on public.financial_goals
for delete to authenticated using (public.is_household_member(household_id));

drop policy if exists "wallet household read" on public.wallet_accounts;
drop policy if exists "wallet household insert" on public.wallet_accounts;
drop policy if exists "wallet household update" on public.wallet_accounts;
drop policy if exists "wallet household delete" on public.wallet_accounts;
create policy "wallet household read" on public.wallet_accounts
for select to authenticated using (public.is_household_member(household_id));
create policy "wallet household insert" on public.wallet_accounts
for insert to authenticated with check (public.is_household_member(household_id) and created_by=auth.uid());
create policy "wallet household update" on public.wallet_accounts
for update to authenticated using (public.is_household_member(household_id))
with check (public.is_household_member(household_id));
create policy "wallet household delete" on public.wallet_accounts
for delete to authenticated using (public.is_household_member(household_id));

drop policy if exists "semester household read" on public.semester_summaries;
drop policy if exists "semester household insert" on public.semester_summaries;
drop policy if exists "semester household update" on public.semester_summaries;
drop policy if exists "semester household delete" on public.semester_summaries;
create policy "semester household read" on public.semester_summaries
for select to authenticated using (public.is_household_member(household_id));
create policy "semester household insert" on public.semester_summaries
for insert to authenticated with check (public.is_household_member(household_id) and created_by=auth.uid());
create policy "semester household update" on public.semester_summaries
for update to authenticated using (public.is_household_member(household_id))
with check (public.is_household_member(household_id));
create policy "semester household delete" on public.semester_summaries
for delete to authenticated using (public.is_household_member(household_id));

grant select, insert, update, delete on public.financial_goals to authenticated;
grant select, insert, update, delete on public.wallet_accounts to authenticated;
grant select, insert, update, delete on public.semester_summaries to authenticated;

-- FinanceHub 0.8.0 — Mercado
create table if not exists public.market_trips (
  id uuid primary key default gen_random_uuid(), household_id uuid not null references public.households(id) on delete cascade,
  market_name text not null, shopping_date date not null default current_date, budget numeric(14,2) not null default 0,
  cart_total numeric(14,2) not null default 0, receipt_total numeric(14,2) not null default 0,
  status text not null default 'open' check (status in ('open','closed')), finished_at timestamptz,
  created_by uuid not null references auth.users(id), created_at timestamptz not null default now());
create table if not exists public.market_items (
  id uuid primary key default gen_random_uuid(), trip_id uuid not null references public.market_trips(id) on delete cascade,
  household_id uuid not null references public.households(id) on delete cascade, product_name text not null,
  quantity numeric(12,3) not null default 1 check(quantity>0), unit_price numeric(14,2) not null default 0 check(unit_price>=0),
  category text not null default 'Outros', created_by uuid not null references auth.users(id), created_at timestamptz not null default now());
alter table public.market_trips enable row level security; alter table public.market_items enable row level security;
drop policy if exists "market trips household all" on public.market_trips;
create policy "market trips household all" on public.market_trips for all to authenticated using(public.is_household_member(household_id)) with check(public.is_household_member(household_id) and created_by=auth.uid());
drop policy if exists "market items household all" on public.market_items;
create policy "market items household all" on public.market_items for all to authenticated using(public.is_household_member(household_id)) with check(public.is_household_member(household_id) and created_by=auth.uid());
grant select,insert,update,delete on public.market_trips to authenticated; grant select,insert,update,delete on public.market_items to authenticated;

-- FinanceHub 0.9.0 — Mercado/cashback + fluxo de caixa
alter table public.market_trips add column if not exists cashback_amount numeric(14,2) not null default 0 check (cashback_amount >= 0);
alter table public.expenses add column if not exists payment_status text not null default 'scheduled' check (payment_status in ('scheduled','paid','overdue','cancelled'));
alter table public.expenses add column if not exists paid_at date;
create index if not exists idx_expenses_household_date on public.expenses(household_id, expense_date);
create index if not exists idx_income_household_month on public.income(household_id, month);
create index if not exists idx_market_items_household_product on public.market_items(household_id, product_name);

-- Hardening: autenticação obrigatória e RLS permanecem a barreira de acesso entre famílias.
revoke all on public.market_trips from anon;
revoke all on public.market_items from anon;
revoke all on public.financial_goals from anon;
revoke all on public.semester_summaries from anon;
