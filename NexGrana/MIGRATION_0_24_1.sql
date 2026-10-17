-- NexGrana 0.24.1: QA reset can only delete a workspace explicitly enrolled
-- by a trusted administrator. Apply after MIGRATION_0_24.sql in staging first.
begin;
create table if not exists public.qa_workspace_registry (
 household_id uuid primary key references public.households(id) on delete cascade,
 qa_owner_id uuid not null references auth.users(id),
 enrolled_at timestamptz not null default now()
);
create table if not exists public.qa_reset_receipts (
 household_id uuid not null,
 user_id uuid not null references auth.users(id),
 completed_at timestamptz not null default now(),
 primary key(household_id,user_id)
);
revoke all on public.qa_workspace_registry,public.qa_reset_receipts from public,anon,authenticated;
alter table public.qa_workspace_registry enable row level security;
alter table public.qa_reset_receipts enable row level security;

-- A designated QA user may mark only a newly created, empty personal space.
-- Existing spaces require explicit administrator review and enrollment.
create or replace function public.enroll_new_qa_workspace(p_household_id uuid)
returns boolean language plpgsql security definer set search_path='' as $$
declare owner_user uuid; created_time timestamptz; household_mode text;
begin
 if auth.uid() is null or p_household_id is null or not exists(
    select 1 from public.qa_testers where user_id=auth.uid() and enabled
 ) then raise exception 'QA enrollment not allowed'; end if;
 select owner_id,created_at,mode into owner_user,created_time,household_mode
 from public.households where id=p_household_id for update;
 if owner_user is distinct from auth.uid() or household_mode <> 'individual'
    or created_time < now()-interval '10 minutes'
    or (select count(*) from public.household_members where household_id=p_household_id)<>1
    or not exists(select 1 from public.household_members where household_id=p_household_id
      and user_id=auth.uid() and role='owner' and status='active')
    or exists(select 1 from public.income where household_id=p_household_id)
    or exists(select 1 from public.expenses where household_id=p_household_id)
    or exists(select 1 from public.financial_goals where household_id=p_household_id)
    or exists(select 1 from public.acquisitions where household_id=p_household_id)
    or exists(select 1 from public.market_trips where household_id=p_household_id)
 then raise exception 'QA enrollment requires a new empty individual sandbox'; end if;
 insert into public.qa_workspace_registry(household_id,qa_owner_id)
 values(p_household_id,auth.uid()) on conflict (household_id) do nothing;
 return true;
end $$;
revoke all on function public.enroll_new_qa_workspace(uuid) from public,anon;
grant execute on function public.enroll_new_qa_workspace(uuid) to authenticated;

create or replace function public.reset_qa_workspace(p_confirmation text,p_household_id uuid)
returns boolean language plpgsql security definer set search_path='' as $$
declare owner_user uuid; member_count integer;
begin
 if p_confirmation <> 'RESETAR_TESTE' or p_household_id is null or auth.uid() is null or not exists(
  select 1 from public.qa_testers where user_id=auth.uid() and enabled
 ) then raise exception 'QA reset not allowed'; end if;
 -- A retry after a committed reset is safe; the receipt contains no user data.
 if exists(select 1 from public.qa_reset_receipts
           where household_id=p_household_id and user_id=auth.uid()) then
  return true;
 end if;
 select owner_id into owner_user from public.households where id=p_household_id for update;
 if owner_user is null or not exists(select 1 from public.household_members
     where household_id=p_household_id and user_id=auth.uid() and status='active') then
  raise exception 'QA workspace not found or no longer active';
 end if;
 if owner_user=auth.uid() then
  if not exists(select 1 from public.qa_workspace_registry
    where household_id=p_household_id and qa_owner_id=auth.uid()) then
   raise exception 'QA reset blocked: workspace is not an enrolled sandbox';
  end if;
  select count(*) into member_count from public.household_members where household_id=p_household_id;
  if member_count<>1 then
   raise exception 'QA reset blocked: family has other members; transfer ownership manually';
  end if;
  delete from public.households where id=p_household_id and owner_id=auth.uid();
 else
  -- A QA account can leave a family without deleting another owner's data.
  delete from public.household_members where household_id=p_household_id and user_id=auth.uid();
 end if;
 insert into public.qa_reset_receipts(household_id,user_id)
 values(p_household_id,auth.uid()) on conflict (household_id,user_id) do nothing;
 return true;
end $$;
revoke all on function public.reset_qa_workspace(text,uuid) from public,anon;
grant execute on function public.reset_qa_workspace(text,uuid) to authenticated;
notify pgrst,'reload schema';
commit;
