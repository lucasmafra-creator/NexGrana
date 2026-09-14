-- FINANCEHUB CLOUD V1
-- Execute este arquivo no SQL Editor do Supabase uma única vez.

create extension if not exists pgcrypto;

create table if not exists public.profiles (
  id uuid primary key references auth.users(id) on delete cascade,
  full_name text not null default '',
  created_at timestamptz not null default now()
);

create table if not exists public.households (
  id uuid primary key default gen_random_uuid(),
  name text not null,
  mode text not null check (mode in ('individual','family')),
  owner_id uuid not null references auth.users(id) on delete cascade,
  invite_code text not null unique,
  created_at timestamptz not null default now()
);

create table if not exists public.household_members (
  id uuid primary key default gen_random_uuid(),
  household_id uuid not null references public.households(id) on delete cascade,
  user_id uuid not null references auth.users(id) on delete cascade,
  display_name text not null,
  role text not null default 'member' check (role in ('owner','member','viewer')),
  status text not null default 'active' check (status in ('active','inactive')),
  created_at timestamptz not null default now(),
  unique(household_id, user_id)
);

create table if not exists public.income (
  id uuid primary key default gen_random_uuid(),
  household_id uuid not null references public.households(id) on delete cascade,
  member_id uuid not null references public.household_members(id) on delete cascade,
  amount numeric(14,2) not null check (amount >= 0),
  month text not null,
  note text not null default '',
  created_by uuid not null references auth.users(id),
  created_at timestamptz not null default now()
);

create table if not exists public.expenses (
  id uuid primary key default gen_random_uuid(),
  household_id uuid not null references public.households(id) on delete cascade,
  payer_member_id uuid references public.household_members(id) on delete set null,
  kind text not null,
  category text not null,
  description text not null,
  amount numeric(14,2) not null check (amount >= 0),
  expense_date text not null,
  month text not null,
  installments_total integer not null default 1 check (installments_total >= 1),
  installment_number integer not null default 1 check (installment_number >= 1),
  installment_group text not null default '',
  automatic_debit boolean not null default false,
  created_by uuid not null references auth.users(id),
  created_at timestamptz not null default now()
);

create table if not exists public.expense_shares (
  id uuid primary key default gen_random_uuid(),
  expense_id uuid not null references public.expenses(id) on delete cascade,
  member_id uuid not null references public.household_members(id) on delete cascade,
  amount numeric(14,2) not null check (amount >= 0),
  unique(expense_id, member_id)
);

create table if not exists public.acquisitions (
  id uuid primary key default gen_random_uuid(),
  household_id uuid not null references public.households(id) on delete cascade,
  member_id uuid references public.household_members(id) on delete set null,
  item text not null,
  priority text not null check (priority in ('Alta','Média','Baixa')),
  estimated numeric(14,2) not null check (estimated >= 0),
  saved numeric(14,2) not null default 0 check (saved >= 0),
  note text not null default '',
  status text not null default 'active' check (status in ('active','completed','cancelled')),
  created_by uuid not null references auth.users(id),
  completed_at date,
  created_at timestamptz not null default now()
);

-- Cria automaticamente o profile quando um usuário entra no Auth.
create or replace function public.handle_new_user()
returns trigger
language plpgsql
security definer set search_path = ''
as $$
begin
  insert into public.profiles (id, full_name)
  values (new.id, coalesce(new.raw_user_meta_data ->> 'full_name', ''))
  on conflict (id) do nothing;
  return new;
end;
$$;

drop trigger if exists on_auth_user_created on auth.users;
create trigger on_auth_user_created
  after insert on auth.users
  for each row execute procedure public.handle_new_user();

-- Helpers para RLS.
create or replace function public.is_household_member(hid uuid)
returns boolean
language sql
security definer
stable
set search_path = public
as $$
  select exists(
    select 1
    from public.household_members hm
    where hm.household_id = hid
      and hm.user_id = auth.uid()
      and hm.status = 'active'
  );
$$;

create or replace function public.is_household_owner(hid uuid)
returns boolean
language sql
security definer
stable
set search_path = public
as $$
  select exists(
    select 1 from public.households h
    where h.id = hid and h.owner_id = auth.uid()
  );
$$;

-- Limite de sete membros ativos em família.
create or replace function public.enforce_family_member_limit()
returns trigger
language plpgsql
as $$
declare
  household_mode text;
  active_count integer;
begin
  select mode into household_mode from public.households where id = new.household_id;
  if household_mode = 'family' and new.status = 'active' then
    select count(*) into active_count
    from public.household_members
    where household_id = new.household_id and status = 'active';
    if active_count >= 7 then
      raise exception 'Family member limit reached (7)';
    end if;
  end if;
  if household_mode = 'individual' then
    select count(*) into active_count
    from public.household_members
    where household_id = new.household_id and status = 'active';
    if active_count >= 1 then
      raise exception 'Individual account supports one member';
    end if;
  end if;
  return new;
end;
$$;

drop trigger if exists trg_family_member_limit on public.household_members;
create trigger trg_family_member_limit
before insert on public.household_members
for each row execute procedure public.enforce_family_member_limit();

-- RLS.
alter table public.profiles enable row level security;
alter table public.households enable row level security;
alter table public.household_members enable row level security;
alter table public.income enable row level security;
alter table public.expenses enable row level security;
alter table public.expense_shares enable row level security;
alter table public.acquisitions enable row level security;

create policy "profile own select" on public.profiles
for select to authenticated using (id = auth.uid());
create policy "profile own update" on public.profiles
for update to authenticated using (id = auth.uid()) with check (id = auth.uid());

create policy "household owner create" on public.households
for insert to authenticated with check (owner_id = auth.uid());

create policy "household members read" on public.households
for select to authenticated using (
  owner_id = auth.uid() or public.is_household_member(id)
);

create policy "household owner update" on public.households
for update to authenticated using (owner_id = auth.uid())
with check (owner_id = auth.uid());

-- Membership creation:
-- 1) owner may insert themselves in a household they own;
-- 2) a user may join an existing family by invite_code through app lookup.
create policy "members read household" on public.household_members
for select to authenticated using (
  user_id = auth.uid() or public.is_household_member(household_id) or public.is_household_owner(household_id)
);

create policy "members join self" on public.household_members
for insert to authenticated with check (
  user_id = auth.uid()
);

create policy "owner manage members" on public.household_members
for update to authenticated using (public.is_household_owner(household_id))
with check (public.is_household_owner(household_id));

-- Financial tables: any active member of household can read/write.
create policy "income household read" on public.income
for select to authenticated using (public.is_household_member(household_id));
create policy "income household insert" on public.income
for insert to authenticated with check (public.is_household_member(household_id) and created_by = auth.uid());
create policy "income household delete" on public.income
for delete to authenticated using (public.is_household_member(household_id));

create policy "expenses household read" on public.expenses
for select to authenticated using (public.is_household_member(household_id));
create policy "expenses household insert" on public.expenses
for insert to authenticated with check (public.is_household_member(household_id) and created_by = auth.uid());
create policy "expenses household update" on public.expenses
for update to authenticated using (public.is_household_member(household_id))
with check (public.is_household_member(household_id));
create policy "expenses household delete" on public.expenses
for delete to authenticated using (public.is_household_member(household_id));

create policy "shares household read" on public.expense_shares
for select to authenticated using (
  exists(select 1 from public.expenses e where e.id = expense_id and public.is_household_member(e.household_id))
);
create policy "shares household insert" on public.expense_shares
for insert to authenticated with check (
  exists(select 1 from public.expenses e where e.id = expense_id and public.is_household_member(e.household_id))
);
create policy "shares household delete" on public.expense_shares
for delete to authenticated using (
  exists(select 1 from public.expenses e where e.id = expense_id and public.is_household_member(e.household_id))
);

create policy "acq household read" on public.acquisitions
for select to authenticated using (public.is_household_member(household_id));
create policy "acq household insert" on public.acquisitions
for insert to authenticated with check (public.is_household_member(household_id) and created_by = auth.uid());
create policy "acq household update" on public.acquisitions
for update to authenticated using (public.is_household_member(household_id))
with check (public.is_household_member(household_id));
create policy "acq household delete" on public.acquisitions
for delete to authenticated using (public.is_household_member(household_id));

-- Permissões mínimas para authenticated.
grant usage on schema public to authenticated;
grant select, insert, update, delete on public.profiles to authenticated;
grant select, insert, update, delete on public.households to authenticated;
grant select, insert, update, delete on public.household_members to authenticated;
grant select, insert, update, delete on public.income to authenticated;
grant select, insert, update, delete on public.expenses to authenticated;
grant select, insert, update, delete on public.expense_shares to authenticated;
grant select, insert, update, delete on public.acquisitions to authenticated;
