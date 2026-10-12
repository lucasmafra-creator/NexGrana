-- QA/staging first: immutable shopping budget history, separate from ledger.
begin;
create table if not exists public.market_budget_events(
 id uuid primary key,
 trip_id uuid not null references public.market_trips(id) on delete cascade,
 household_id uuid not null references public.households(id) on delete cascade,
 actor_user_id uuid not null references auth.users(id),
 old_budget numeric not null, new_budget numeric not null check(new_budget>=0),
 market_name text not null,
 created_at timestamptz not null default now()
);
alter table public.market_budget_events enable row level security;
drop policy if exists market_budget_read on public.market_budget_events;
drop policy if exists market_budget_insert on public.market_budget_events;
create policy market_budget_read on public.market_budget_events for select to authenticated
 using(public.is_household_member(household_id));
create policy market_budget_insert on public.market_budget_events for insert to authenticated
 with check(actor_user_id=auth.uid() and public.is_household_member(household_id) and exists(
 select 1 from public.market_trips t where t.id=trip_id and t.household_id=market_budget_events.household_id));
revoke all on public.market_budget_events from public,anon;
grant select,insert on public.market_budget_events to authenticated;
create or replace function public.update_market_trip_safe(p_trip uuid,p_budget numeric,p_name text,p_expected_budget numeric,p_operation uuid)
 returns jsonb language plpgsql security invoker set search_path='' as $$
declare t public.market_trips; e public.market_budget_events;
begin
 if auth.uid() is null or p_operation is null or p_budget is null or p_budget<0 or p_budget::text in ('NaN','Infinity','-Infinity')
  or p_expected_budget is null or char_length(btrim(p_name)) not between 1 and 120 then raise exception 'Invalid shopping budget'; end if;
 select * into t from public.market_trips where id=p_trip for update;
 if not found then raise exception 'Shopping session unavailable'; end if;
 select * into e from public.market_budget_events where id=p_operation;
 if found then
  if e.trip_id<>p_trip or e.actor_user_id<>auth.uid() or e.new_budget<>round(p_budget,2) or e.market_name<>btrim(p_name) then
   raise exception 'Divergent operation retry';
  end if;
  return to_jsonb(t);
 end if;
 if coalesce(t.budget,0)<>p_expected_budget then raise exception 'Budget version conflict'; end if;
 insert into public.market_budget_events(id,trip_id,household_id,actor_user_id,old_budget,new_budget,market_name)
 values(p_operation,t.id,t.household_id,auth.uid(),coalesce(t.budget,0),round(p_budget,2),btrim(p_name));
 update public.market_trips set budget=round(p_budget,2),market_name=btrim(p_name) where id=t.id returning * into t;
 return to_jsonb(t);
end $$;
revoke all on function public.update_market_trip_safe(uuid,numeric,text,numeric,uuid) from public,anon;
grant execute on function public.update_market_trip_safe(uuid,numeric,text,numeric,uuid) to authenticated;
notify pgrst,'reload schema';
commit;
