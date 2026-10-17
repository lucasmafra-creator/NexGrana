-- Self-service deletion is atomic and restricted to an individual owner.
-- Shared households require an ownership/retention workflow outside this RPC.
begin;
create or replace function public.delete_my_individual_account(p_household_id uuid,p_confirmation text)
returns boolean language plpgsql security definer set search_path='' as $$
declare uid uuid := auth.uid();
begin
 if uid is null or p_confirmation <> 'EXCLUIR MINHA CONTA' or p_household_id is null then
  raise exception 'Confirmation required';
 end if;
 perform 1 from public.households where id=p_household_id and owner_id=uid
  and mode='individual' for update;
 if not found or (select count(*) from public.household_members where household_id=p_household_id)<>1
   or not exists(select 1 from public.household_members where household_id=p_household_id
                  and user_id=uid and role='owner' and status='active')
   or exists(select 1 from public.household_members where user_id=uid and household_id<>p_household_id)
   or exists(select 1 from public.households where owner_id=uid and id<>p_household_id)
 then raise exception 'Account has shared or other workspaces'; end if;
 -- Any FK to authored content elsewhere blocks the transaction rather than
 -- deleting another household's records or leaving a partial deletion.
 delete from public.households where id=p_household_id and owner_id=uid;
 delete from public.qa_reset_receipts where user_id=uid;
 delete from auth.users where id=uid;
 if not found then raise exception 'Account not found'; end if;
 return true;
end $$;
revoke all on function public.delete_my_individual_account(uuid,text) from public,anon;
grant execute on function public.delete_my_individual_account(uuid,text) to authenticated;
notify pgrst,'reload schema';
commit;
