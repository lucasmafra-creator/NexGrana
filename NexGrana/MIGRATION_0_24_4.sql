-- Opt-in enrollment for an existing QA-owned individual workspace.
-- The QA privilege is an allowlist by auth.uid(), never by email text.
begin;
create or replace function public.enroll_owned_qa_workspace(p_household_id uuid,p_confirmation text)
returns boolean language plpgsql security definer set search_path='' as $$
declare owner_user uuid; household_mode text; member_count integer;
begin
 if auth.uid() is null or p_confirmation <> 'VINCULAR_TESTE' or p_household_id is null
  or not exists(select 1 from public.qa_testers where user_id=auth.uid() and enabled)
 then raise exception 'QA enrollment not allowed'; end if;
 select owner_id,mode into owner_user,household_mode from public.households
 where id=p_household_id for update;
 if owner_user is distinct from auth.uid() or household_mode<>'individual' then
  raise exception 'Only your individual QA workspace can be enrolled';
 end if;
 select count(*) into member_count from public.household_members where household_id=p_household_id;
 if member_count<>1 or not exists(select 1 from public.household_members
   where household_id=p_household_id and user_id=auth.uid() and role='owner' and status='active')
 then raise exception 'QA workspace has other members'; end if;
 insert into public.qa_workspace_registry(household_id,qa_owner_id)
 values(p_household_id,auth.uid()) on conflict (household_id) do nothing;
 return true;
end $$;
revoke all on function public.enroll_owned_qa_workspace(uuid,text) from public,anon;
grant execute on function public.enroll_owned_qa_workspace(uuid,text) to authenticated;
notify pgrst,'reload schema';
commit;
