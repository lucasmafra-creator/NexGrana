-- NexGrana 0.17.0 — hardening de segurança/RLS
-- Revisar em ambiente de teste e executar no SQL Editor do Supabase.

-- 1) Nunca permitir acesso anônimo às tabelas financeiras/pessoais.
revoke all on public.profiles from anon;
revoke all on public.households from anon;
revoke all on public.household_members from anon;
revoke all on public.income from anon;
revoke all on public.expenses from anon;
revoke all on public.expense_shares from anon;
revoke all on public.acquisitions from anon;
revoke all on public.financial_goals from anon;
revoke all on public.wallet_accounts from anon;
revoke all on public.semester_summaries from anon;
revoke all on public.market_trips from anon;
revoke all on public.market_items from anon;

-- 2) Corrige uma superfície de escalada: entrar em uma família deve acontecer
-- exclusivamente pela RPC que valida o invite_code, nunca por INSERT direto.
drop policy if exists "members join self" on public.household_members;
drop policy if exists "owner insert member placeholders" on public.household_members;
create policy "owner insert member placeholders"
on public.household_members
for insert to authenticated
with check (
  user_id is null
  and public.is_household_owner(household_id)
);

-- A RPC segura continua sendo a única rota para um usuário autenticado
-- vincular a própria conta a uma família existente.
create or replace function public.join_household_by_code(
  p_code text,
  p_display_name text
)
returns uuid
language plpgsql
security definer
set search_path = public
as $$
declare
  v_household_id uuid;
  v_member_id uuid;
  v_count integer;
begin
  if auth.uid() is null then
    raise exception 'Usuário não autenticado';
  end if;

  select id into v_household_id
  from public.households
  where upper(invite_code) = upper(trim(p_code))
    and mode = 'family'
  limit 1;

  if v_household_id is null then
    raise exception 'Código de família inválido';
  end if;

  select id into v_member_id
  from public.household_members
  where household_id = v_household_id
    and user_id = auth.uid()
    and status = 'active'
  limit 1;
  if v_member_id is not null then return v_member_id; end if;

  select id into v_member_id
  from public.household_members
  where household_id = v_household_id
    and user_id is null
    and status = 'active'
    and lower(trim(display_name)) = lower(trim(p_display_name))
  order by created_at limit 1;

  if v_member_id is not null then
    update public.household_members set user_id = auth.uid() where id = v_member_id;
    return v_member_id;
  end if;

  select count(*) into v_count from public.household_members
  where household_id = v_household_id and status = 'active';
  if v_count >= 7 then raise exception 'Família já possui 7 integrantes'; end if;

  insert into public.household_members(household_id,user_id,display_name,role,status)
  values(v_household_id,auth.uid(),trim(p_display_name),'member','active')
  returning id into v_member_id;
  return v_member_id;
end;
$$;
grant execute on function public.join_household_by_code(text,text) to authenticated;

-- 3) Mercado: INSERT exige created_by do usuário, mas UPDATE/DELETE podem ser
-- feitos por membros ativos da mesma família sem falhar por created_by alheio.
drop policy if exists "market trips household all" on public.market_trips;
drop policy if exists "market items household all" on public.market_items;

drop policy if exists "market trips household read" on public.market_trips;
drop policy if exists "market trips household insert" on public.market_trips;
drop policy if exists "market trips household update" on public.market_trips;
drop policy if exists "market trips household delete" on public.market_trips;
create policy "market trips household read" on public.market_trips
for select to authenticated using (public.is_household_member(household_id));
create policy "market trips household insert" on public.market_trips
for insert to authenticated with check (public.is_household_member(household_id) and created_by=auth.uid());
create policy "market trips household update" on public.market_trips
for update to authenticated using (public.is_household_member(household_id))
with check (public.is_household_member(household_id));
create policy "market trips household delete" on public.market_trips
for delete to authenticated using (public.is_household_member(household_id));

drop policy if exists "market items household read" on public.market_items;
drop policy if exists "market items household insert" on public.market_items;
drop policy if exists "market items household update" on public.market_items;
drop policy if exists "market items household delete" on public.market_items;
create policy "market items household read" on public.market_items
for select to authenticated using (public.is_household_member(household_id));
create policy "market items household insert" on public.market_items
for insert to authenticated with check (public.is_household_member(household_id) and created_by=auth.uid());
create policy "market items household update" on public.market_items
for update to authenticated using (public.is_household_member(household_id))
with check (public.is_household_member(household_id));
create policy "market items household delete" on public.market_items
for delete to authenticated using (public.is_household_member(household_id));

-- 4) Índices para consultas frequentes do app.
create index if not exists idx_members_household_active on public.household_members(household_id,status);
create index if not exists idx_income_household_member on public.income(household_id,member_id);
create index if not exists idx_expenses_household_member on public.expenses(household_id,payer_member_id);
create index if not exists idx_acq_household_member on public.acquisitions(household_id,member_id,status);
create index if not exists idx_goals_household_status on public.financial_goals(household_id,status,target_date);
