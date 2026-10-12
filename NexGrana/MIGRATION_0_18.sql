-- Aplicar depois de SUPABASE_PATCH_V2_RC.sql e SUPABASE_SECURITY_0_17.sql.
-- Aditiva, transacional e idempotente. Não inventa datas dos registros antigos.
begin;
alter table public.income add column if not exists received_at date;
alter table public.income add column if not exists receipt_status text not null default 'received'
  check(receipt_status in ('received','scheduled','cancelled'));
alter table public.financial_goals add column if not exists member_id uuid references public.household_members(id);
alter table public.financial_goals add column if not exists acquisition_id uuid references public.acquisitions(id) on delete set null;
alter table public.financial_goals drop constraint if exists financial_goals_status_check;
alter table public.financial_goals add constraint financial_goals_status_check check(status in ('active','paused','completed','cancelled'));

create table if not exists public.goal_contributions (
 id uuid primary key default gen_random_uuid(), household_id uuid not null references public.households(id) on delete cascade,
 goal_id uuid not null references public.financial_goals(id) on delete cascade, amount numeric(14,2) not null check(amount>0),
 created_by uuid not null references auth.users(id), created_at timestamptz not null default now());
create table if not exists public.nex_journeys (
 id uuid primary key default gen_random_uuid(), household_id uuid not null references public.households(id) on delete cascade,
 member_id uuid not null references public.household_members(id), title text not null, progress integer not null default 0 check(progress between 0 and 6),
 status text not null default 'active' check(status in ('active','paused','completed')),
 reminder_enabled boolean not null default false, reminder_at timestamptz, reminder_days integer[] not null default '{}',
 metrics jsonb not null default '{}', history jsonb not null default '[]',
 created_by uuid not null references auth.users(id), created_at timestamptz not null default now(),
 unique(household_id,member_id,title));
create table if not exists public.privacy_consents (
 id uuid primary key default gen_random_uuid(), household_id uuid not null references public.households(id) on delete cascade,
 user_id uuid not null references auth.users(id), purpose text not null check(purpose in ('reminders','external_ai','affiliate_personalization')),
 granted boolean not null default false, policy_version text not null,
 created_by uuid not null references auth.users(id), created_at timestamptz not null default now(),
 unique(user_id,household_id,purpose));
create table if not exists public.affiliate_offers (
 id uuid primary key default gen_random_uuid(), title text not null, subtitle text not null default '', provider text not null,
 url text not null check(url like 'https://%'), category text not null default 'Geral', enabled boolean not null default false,
 expires_at timestamptz not null, created_at timestamptz not null default now());

create or replace function public.can_write_household(hid uuid) returns boolean
language sql stable security definer set search_path='' as $$
 select exists(select 1 from public.household_members where household_id=hid and user_id=auth.uid()
 and status='active' and role in ('owner','member'));
$$;
revoke all on function public.can_write_household(uuid) from public, anon;
grant execute on function public.can_write_household(uuid) to authenticated;

-- Replace financial policies completely: permissive policies combine with OR.
do $$ declare t text; p record; begin
 foreach t in array array['income','expenses','acquisitions','financial_goals','wallet_accounts','semester_summaries','market_trips','market_items','goal_contributions','nex_journeys'] loop
  execute format('alter table public.%I enable row level security',t);
  for p in select policyname from pg_policies where schemaname='public' and tablename=t loop
   execute format('drop policy %I on public.%I',p.policyname,t);
  end loop;
  execute format('create policy tenant_read on public.%I for select to authenticated using(public.is_household_member(household_id))',t);
  execute format('create policy tenant_insert on public.%I for insert to authenticated with check(public.can_write_household(household_id) and created_by=auth.uid())',t);
  execute format('create policy tenant_update on public.%I for update to authenticated using(public.can_write_household(household_id)) with check(public.can_write_household(household_id))',t);
  execute format('create policy tenant_delete on public.%I for delete to authenticated using(public.can_write_household(household_id))',t);
  execute format('revoke all on public.%I from anon',t);
  execute format('grant select,insert,update,delete on public.%I to authenticated',t);
 end loop;
end $$;

-- No household movement or author changes through direct UPDATE.
create or replace function public.guard_financial_scope() returns trigger
language plpgsql set search_path='' as $$
declare mid uuid; linked uuid; begin
 if tg_op='UPDATE' and (new.household_id<>old.household_id or new.created_by<>old.created_by) then
  raise exception 'Immutable scope';
 end if;
 mid=(to_jsonb(new)->>'member_id')::uuid;
 if mid is null then mid=(to_jsonb(new)->>'payer_member_id')::uuid; end if;
 if mid is not null and not exists(select 1 from public.household_members where id=mid and household_id=new.household_id) then
  raise exception 'Member outside household';
 end if;
 if tg_table_name='market_items' and not exists(select 1 from public.market_trips where id=(to_jsonb(new)->>'trip_id')::uuid and household_id=new.household_id) then
  raise exception 'Trip outside household';
 end if;
 if tg_table_name='goal_contributions' and not exists(select 1 from public.financial_goals where id=(to_jsonb(new)->>'goal_id')::uuid and household_id=new.household_id) then
  raise exception 'Goal outside household';
 end if;
 if tg_table_name='financial_goals' then
  linked=(to_jsonb(new)->>'acquisition_id')::uuid;
  if linked is not null and not exists(select 1 from public.acquisitions where id=linked and household_id=new.household_id) then
   raise exception 'Acquisition outside household';
  end if;
 end if;
 return new;
end $$;
do $$ declare t text; begin
 foreach t in array array['income','expenses','acquisitions','financial_goals','wallet_accounts','semester_summaries','market_trips','market_items','goal_contributions','nex_journeys'] loop
  execute format('drop trigger if exists guard_scope on public.%I',t);
  execute format('create trigger guard_scope before insert or update on public.%I for each row execute function public.guard_financial_scope()',t);
 end loop;
end $$;

-- Owners can bootstrap their own membership; placeholders cannot be owners.
drop policy if exists "members join self" on public.household_members;
drop policy if exists "owner insert member placeholders" on public.household_members;
create policy "owner insert member placeholders" on public.household_members for insert to authenticated
with check(public.is_household_owner(household_id) and status='active' and
 ((user_id=auth.uid() and role='owner') or (user_id is null and role='member')));
create or replace function public.guard_membership() returns trigger language plpgsql set search_path='' as $$
begin
 if tg_op='UPDATE' and (new.household_id<>old.household_id or new.role<>old.role
   or new.user_id is distinct from old.user_id) and current_user not in ('postgres','supabase_admin') then
  raise exception 'Membership identity is immutable; use authorized RPC';
 end if;
 if new.user_id is null and new.role<>'member' then raise exception 'Placeholder cannot be privileged'; end if;
 return new;
end $$;
drop trigger if exists guard_membership on public.household_members;
create trigger guard_membership before insert or update on public.household_members for each row execute function public.guard_membership();

-- Lock household to serialize joins, never claim someone else's financial placeholder by name.
create or replace function public.join_household_by_code(p_code text,p_display_name text)
returns uuid language plpgsql security definer set search_path='' as $$
declare hid uuid; mid uuid; n integer; begin
 if auth.uid() is null or length(trim(p_display_name)) not between 1 and 80 then raise exception 'Invalid request'; end if;
 select id into hid from public.households where upper(invite_code)=upper(trim(p_code)) and mode='family' for update;
 if hid is null then raise exception 'Invalid invitation'; end if;
 select id into mid from public.household_members where household_id=hid and user_id=auth.uid() and status='active';
 if mid is not null then return mid; end if;
 select count(*) into n from public.household_members where household_id=hid and status='active';
 if n>=7 then raise exception 'Family member limit reached'; end if;
 insert into public.household_members(household_id,user_id,display_name,role,status)
 values(hid,auth.uid(),trim(p_display_name),'member','active') returning id into mid;
 return mid;
end $$;
revoke all on function public.join_household_by_code(text,text) from public,anon;
grant execute on function public.join_household_by_code(text,text) to authenticated;

-- Share policies verify both sides belong to the same household.
do $$ declare p record; begin
 for p in select policyname from pg_policies where schemaname='public' and tablename='expense_shares' loop
 execute format('drop policy %I on public.expense_shares',p.policyname); end loop;
end $$;
create policy shares_read on public.expense_shares for select to authenticated using(exists(
 select 1 from public.expenses e where e.id=expense_id and public.is_household_member(e.household_id)));
create policy shares_write on public.expense_shares for all to authenticated using(exists(
 select 1 from public.expenses e where e.id=expense_id and public.can_write_household(e.household_id))) with check(exists(
 select 1 from public.expenses e join public.household_members m on m.household_id=e.household_id
 where e.id=expense_id and m.id=member_id and public.can_write_household(e.household_id)));

-- Atomic contribution prevents lost updates and duplicate retry deposits.
create or replace function public.contribute_goal(p_goal uuid,p_amount numeric,p_id uuid)
returns numeric language plpgsql security invoker set search_path='' as $$
declare g public.financial_goals; result numeric; begin
 select * into g from public.financial_goals where id=p_goal for update;
 if g.id is null or p_id is null or p_amount is null or not public.can_write_household(g.household_id) or p_amount<=0
  or p_amount::text in ('NaN','Infinity','-Infinity') or round(p_amount,2)<>p_amount then raise exception 'Invalid contribution'; end if;
 if exists(select 1 from public.goal_contributions where id=p_id and goal_id=p_goal and amount=p_amount) then return g.saved_amount; end if;
 insert into public.goal_contributions(id,household_id,goal_id,amount,created_by) values(p_id,g.household_id,p_goal,p_amount,auth.uid());
 update public.financial_goals set saved_amount=saved_amount+p_amount,
 status=case when saved_amount+p_amount>=target_amount then 'completed' else status end where id=p_goal returning saved_amount into result;
 return result;
end $$;
revoke all on function public.contribute_goal(uuid,numeric,uuid) from public,anon;
grant execute on function public.contribute_goal(uuid,numeric,uuid) to authenticated;

alter table public.privacy_consents enable row level security;
drop policy if exists own_consent on public.privacy_consents;
create policy own_consent on public.privacy_consents for all to authenticated using(user_id=auth.uid() and public.is_household_member(household_id))
with check(user_id=auth.uid() and created_by=auth.uid() and public.is_household_member(household_id));
revoke all on public.privacy_consents from anon;
grant select,insert,update,delete on public.privacy_consents to authenticated;
alter table public.affiliate_offers enable row level security;
drop policy if exists current_offers on public.affiliate_offers;
create policy current_offers on public.affiliate_offers for select to authenticated using(enabled and expires_at>now());
revoke all on public.affiliate_offers from anon,authenticated;
grant select on public.affiliate_offers to authenticated;
create index if not exists income_received_idx on public.income(household_id,received_at);
commit;
