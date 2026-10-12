-- NexGrana 0.23.0 — reset de homologação seguro para espaço individual/familiar.
-- Migração aditiva e idempotente. Aplicar depois da MIGRATION_0_22.sql.
begin;

create or replace function public.reset_qa_workspace(p_confirmation text)
returns boolean language plpgsql security definer set search_path='' as $$
declare
 hid uuid;
 is_owner boolean;
 successor_member_id uuid;
 successor_user_id uuid;
 inactive_other_count integer;
begin
 if p_confirmation <> 'RESETAR_TESTE' or not exists(
  select 1
  from public.qa_testers
  where user_id = auth.uid() and enabled
 ) then
  raise exception 'QA reset not allowed';
 end if;

 -- Usa o espaço ativo mais recente da própria conta de homologação.
 select h.id, h.owner_id = auth.uid()
 into hid, is_owner
 from public.household_members m
 join public.households h on h.id = m.household_id
 where m.user_id = auth.uid() and m.status = 'active'
 order by h.created_at desc, m.created_at desc
 limit 1
 for update of h;

 if hid is null then
  return true;
 end if;

 if is_owner then
  -- Havendo outra conta ativa, transfere a propriedade e remove somente a
  -- conta QA. Nenhum dado da família ou do novo proprietário é apagado.
  select id, user_id
  into successor_member_id, successor_user_id
  from public.household_members
  where household_id = hid
    and status = 'active'
    and user_id <> auth.uid()
  order by created_at, id
  limit 1;

  if successor_user_id is not null then
   update public.household_members
   set role = case
    when id = successor_member_id then 'owner'
    when user_id = auth.uid() then 'member'
    else role
   end
   where household_id = hid
     and (id = successor_member_id or user_id = auth.uid());

   update public.households
   set owner_id = successor_user_id
   where id = hid and owner_id = auth.uid();

   delete from public.household_members
   where household_id = hid and user_id = auth.uid();
   return found;
  end if;

  -- Não apaga silenciosamente a associação de outra conta inativa. Esse caso
  -- exige revisão manual para não entregar o espaço a uma conta desativada.
  select count(*)
  into inactive_other_count
  from public.household_members
  where household_id = hid and user_id <> auth.uid();
  if inactive_other_count > 0 then
   raise exception 'QA reset blocked: inactive linked member requires review';
  end if;

  delete from public.households
  where id = hid and owner_id = auth.uid();
  return found;
 end if;

 -- Se a conta QA apenas entrou em uma família, remove somente a participação
 -- dela. O espaço, o proprietário e os dados das outras pessoas permanecem.
 delete from public.household_members
 where household_id = hid and user_id = auth.uid();
 return found;
end $$;

revoke all on function public.reset_qa_workspace(text) from public,anon;
grant execute on function public.reset_qa_workspace(text) to authenticated;

notify pgrst,'reload schema';
commit;

select to_regprocedure('public.reset_qa_workspace(text)') as qa_reset_rpc_023;
