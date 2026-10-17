-- Confirmed month-to-month balance continuity for family and member scopes.
-- Apply after the existing NexGrana 0.24 migrations in staging first.
begin;

create table if not exists public.monthly_closures (
  id uuid primary key default gen_random_uuid(),
  household_id uuid not null references public.households(id) on delete cascade,
  member_id uuid references public.household_members(id) on delete cascade,
  month_start date not null check (extract(day from month_start) = 1),
  opening_balance numeric(14,2) not null default 0,
  closing_balance numeric(14,2) not null,
  status text not null default 'closed' check (status = 'closed'),
  closed_by uuid references auth.users(id) on delete set null,
  closed_at timestamptz not null default now(),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create unique index if not exists monthly_closures_scope_month_uq
  on public.monthly_closures (
    household_id,
    month_start,
    coalesce(member_id, '00000000-0000-0000-0000-000000000000'::uuid)
  );
create index if not exists monthly_closures_household_month_idx
  on public.monthly_closures(household_id, month_start desc);

alter table public.monthly_closures enable row level security;
revoke all on public.monthly_closures from public, anon;
grant select, insert, update on public.monthly_closures to authenticated;

drop policy if exists monthly_closures_read on public.monthly_closures;
create policy monthly_closures_read on public.monthly_closures
  for select to authenticated
  using (public.is_household_member(household_id));

drop policy if exists monthly_closures_insert on public.monthly_closures;
create policy monthly_closures_insert on public.monthly_closures
  for insert to authenticated
  with check (
    public.can_write_household(household_id)
    and closed_by = auth.uid()
    and (member_id is null or exists (
      select 1 from public.household_members m
      where m.id = monthly_closures.member_id and m.household_id = monthly_closures.household_id
    ))
  );

drop policy if exists monthly_closures_update on public.monthly_closures;
create policy monthly_closures_update on public.monthly_closures
  for update to authenticated
  using (public.can_write_household(household_id))
  with check (
    public.can_write_household(household_id)
    and closed_by = auth.uid()
    and (member_id is null or exists (
      select 1 from public.household_members m
      where m.id = monthly_closures.member_id and m.household_id = monthly_closures.household_id
    ))
  );

notify pgrst, 'reload schema';
commit;
