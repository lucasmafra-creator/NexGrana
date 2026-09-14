begin;

-- Optimistic concurrency for goal edits. Contributions and edits both bump
-- version so a stale dialog cannot silently overwrite another member's work.
alter table public.financial_goals add column if not exists version bigint not null default 0;
alter table public.financial_goals add column if not exists updated_at timestamptz not null default now();

create or replace function public.update_goal_safe(
    p_goal uuid,
    p_expected_version bigint,
    p_name text,
    p_target numeric,
    p_target_date date,
    p_strategy text,
    p_member uuid,
    p_status text
) returns bigint
language plpgsql security invoker set search_path='' as $$
declare g public.financial_goals; next_version bigint; begin
    select * into g from public.financial_goals where id=p_goal for update;
    if g.id is null or not public.can_write_household(g.household_id) then
        raise exception 'Goal unavailable';
    end if;
    if g.version <> coalesce(p_expected_version,-1) then
        raise exception 'Goal changed; refresh before saving';
    end if;
    if length(trim(coalesce(p_name,''))) not between 1 and 120
       or p_target is null or p_target<=0
       or p_target::text in ('NaN','Infinity','-Infinity')
       or round(p_target,2)<>p_target
       or p_target_date is null
       or p_status not in ('active','paused','completed','cancelled') then
        raise exception 'Invalid goal';
    end if;
    if p_member is not null and not exists(
        select 1 from public.household_members m
        where m.id=p_member and m.household_id=g.household_id and m.status='active'
    ) then raise exception 'Member outside household'; end if;
    if p_target < g.saved_amount then
        raise exception 'Target cannot be lower than saved amount';
    end if;
    update public.financial_goals
       set name=trim(p_name), target_amount=p_target, target_date=p_target_date,
           strategy=coalesce(nullif(trim(p_strategy),''),'Equilibrada'), member_id=p_member,
           status=p_status, version=version+1, updated_at=now()
     where id=p_goal
     returning version into next_version;
    return next_version;
end $$;
revoke all on function public.update_goal_safe(uuid,bigint,text,numeric,date,text,uuid,text) from public,anon;
grant execute on function public.update_goal_safe(uuid,bigint,text,numeric,date,text,uuid,text) to authenticated;

create or replace function public.contribute_goal(p_goal uuid,p_amount numeric,p_id uuid)
returns numeric language plpgsql security invoker set search_path='' as $$
declare g public.financial_goals; result numeric; begin
 select * into g from public.financial_goals where id=p_goal for update;
 if g.id is null or p_id is null or p_amount is null or not public.can_write_household(g.household_id) or p_amount<=0
  or p_amount::text in ('NaN','Infinity','-Infinity') or round(p_amount,2)<>p_amount then raise exception 'Invalid contribution'; end if;
 if exists(select 1 from public.goal_contributions where id=p_id and goal_id=p_goal and amount=p_amount) then return g.saved_amount; end if;
 if exists(select 1 from public.goal_contributions where id=p_id) then
   raise exception 'Contribution id already used with different payload';
 end if;
 if g.status in ('completed','cancelled') then raise exception 'Goal is closed'; end if;
 if g.saved_amount + p_amount > g.target_amount then raise exception 'Contribution exceeds remaining target'; end if;
 insert into public.goal_contributions(id,household_id,goal_id,amount,created_by) values(p_id,g.household_id,p_goal,p_amount,auth.uid());
 update public.financial_goals set saved_amount=saved_amount+p_amount,
 status=case when saved_amount+p_amount>=target_amount then 'completed' else status end,
 version=version+1,updated_at=now()
 where id=p_goal returning saved_amount into result;
 return result;
end $$;
revoke all on function public.contribute_goal(uuid,numeric,uuid) from public,anon;
grant execute on function public.contribute_goal(uuid,numeric,uuid) to authenticated;

-- Consent purpose remains explicit and scoped to the authenticated user.
alter table public.privacy_consents enable row level security;
drop policy if exists own_consent on public.privacy_consents;
create policy own_consent on public.privacy_consents for all to authenticated
using(user_id=auth.uid() and public.is_household_member(household_id))
with check(user_id=auth.uid() and created_by=auth.uid() and public.is_household_member(household_id));
revoke all on public.privacy_consents from anon;
grant select,insert,update,delete on public.privacy_consents to authenticated;

commit;
