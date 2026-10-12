-- NexGrana 0.24 QA: independent shopping lists. Run in a staging Supabase project
-- after previous migrations; review RLS and a backup before production rollout.
begin;

create table if not exists public.shopping_lists (
 id uuid primary key default gen_random_uuid(),
 household_id uuid not null references public.households(id) on delete cascade,
 member_id uuid references public.household_members(id),
 name text not null check(length(btrim(name)) between 1 and 100),
 budget numeric(14,2) not null default 0 check(budget >= 0),
 shared boolean not null default false,
 created_by uuid not null references auth.users(id),
 created_at timestamptz not null default now()
);
create index if not exists shopping_lists_home_idx on public.shopping_lists(household_id,created_at desc);
create table if not exists public.shopping_list_items (
 id uuid primary key default gen_random_uuid(),
 list_id uuid not null references public.shopping_lists(id) on delete cascade,
 household_id uuid not null references public.households(id) on delete cascade,
 name text not null check(length(btrim(name)) between 1 and 150),
 quantity numeric(10,2) not null default 1 check(quantity > 0),
 unit_price numeric(14,2) not null default 0 check(unit_price >= 0),
 purchased boolean not null default false,
 created_by uuid not null references auth.users(id),
 created_at timestamptz not null default now()
);
-- The offline cache and mutation queue scope every table by household_id.
-- Prevent moving an item into a list owned by a different household.
create unique index if not exists shopping_lists_id_household_idx on public.shopping_lists(id,household_id);
do $$ begin
 if not exists(select 1 from pg_constraint where conname='shopping_list_items_parent_household_fk'
  and conrelid='public.shopping_list_items'::regclass) then
  alter table public.shopping_list_items add constraint shopping_list_items_parent_household_fk
   foreign key (list_id,household_id) references public.shopping_lists(id,household_id) on delete cascade;
 end if;
end $$;
create index if not exists shopping_list_items_list_idx on public.shopping_list_items(list_id);

alter table public.shopping_lists enable row level security;
alter table public.shopping_list_items enable row level security;
drop policy if exists shopping_lists_read_024 on public.shopping_lists;
create policy shopping_lists_read_024 on public.shopping_lists for select to authenticated
using (public.is_household_member(household_id) and (created_by = auth.uid() or shared));
drop policy if exists shopping_lists_write_024 on public.shopping_lists;
create policy shopping_lists_write_024 on public.shopping_lists for all to authenticated
using (created_by = auth.uid() and public.is_household_member(household_id))
with check (created_by = auth.uid() and public.is_household_member(household_id)
 and (member_id is null or exists(
  select 1 from public.household_members m where m.id = member_id and m.household_id = shopping_lists.household_id
 )));
drop policy if exists shopping_list_items_read_024 on public.shopping_list_items;
create policy shopping_list_items_read_024 on public.shopping_list_items for select to authenticated
using (exists(select 1 from public.shopping_lists l where l.id = list_id and l.household_id = shopping_list_items.household_id
 and public.is_household_member(l.household_id) and (l.created_by = auth.uid() or l.shared)));
drop policy if exists shopping_list_items_write_024 on public.shopping_list_items;
create policy shopping_list_items_write_024 on public.shopping_list_items for all to authenticated
using (created_by = auth.uid() and exists(select 1 from public.shopping_lists l where l.id = list_id and l.household_id = shopping_list_items.household_id
 and l.created_by = auth.uid() and public.is_household_member(l.household_id)))
with check (created_by = auth.uid() and exists(select 1 from public.shopping_lists l where l.id = list_id and l.household_id = shopping_list_items.household_id
 and l.created_by = auth.uid() and public.is_household_member(l.household_id)));

revoke all on public.shopping_lists,public.shopping_list_items from anon;
grant select,insert,update,delete on public.shopping_lists,public.shopping_list_items to authenticated;
-- Target the exact current workspace; the previous function chose the newest
-- membership and could reset an unrelated family.
create or replace function public.reset_qa_workspace(p_confirmation text,p_household_id uuid)
returns boolean language plpgsql security definer set search_path='' as $$
declare owner_user uuid; member_count integer;
begin
 if p_confirmation <> 'RESETAR_TESTE' or auth.uid() is null or not exists(
  select 1 from public.qa_testers where user_id=auth.uid() and enabled
 ) then raise exception 'QA reset not allowed'; end if;
 select owner_id into owner_user from public.households where id=p_household_id for update;
 if owner_user is null or not exists(select 1 from public.household_members
     where household_id=p_household_id and user_id=auth.uid() and status='active') then
  raise exception 'QA workspace not found or no longer active';
 end if;
 if owner_user=auth.uid() then
  select count(*) into member_count from public.household_members where household_id=p_household_id;
  if member_count<>1 then
   raise exception 'QA reset blocked: family has other members; transfer ownership manually';
  end if;
  delete from public.households where id=p_household_id and owner_id=auth.uid();
 else
  delete from public.household_members where household_id=p_household_id and user_id=auth.uid();
 end if;
 return found;
end $$;
revoke all on function public.reset_qa_workspace(text,uuid) from public,anon;
grant execute on function public.reset_qa_workspace(text,uuid) to authenticated;
drop function if exists public.reset_qa_workspace(text);
notify pgrst,'reload schema';
commit;
