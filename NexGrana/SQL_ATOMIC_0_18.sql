-- Aplicar após MIGRATION_0_18.sql. Transações de despesas/rateios.
begin;
create or replace function public.save_expense_batch(p_rows jsonb,p_replace boolean default false)
returns integer language plpgsql security invoker set search_path='' as $$
declare r jsonb; s jsonb; hid uuid; rid uuid; existing public.expenses; n integer:=0; total numeric; begin
 if p_rows is null or jsonb_typeof(p_rows)<>'array' or jsonb_array_length(p_rows) not between 1 and 360 then raise exception 'Invalid batch'; end if;
 if p_replace and jsonb_array_length(p_rows)<>1 then raise exception 'Replace one expense at a time'; end if;
 for r in select value from jsonb_array_elements(p_rows) loop
  hid=(r->>'household_id')::uuid; rid=(r->>'id')::uuid;
  if hid is null or rid is null or not public.can_write_household(hid) or r->>'amount' is null
   or (r->>'amount')::numeric<=0 or (r->>'amount')::numeric::text in ('NaN','Infinity','-Infinity')
   or round((r->>'amount')::numeric,2)<>(r->>'amount')::numeric then raise exception 'Invalid expense'; end if;
  if r->'shares' is null or jsonb_typeof(r->'shares')<>'array' or jsonb_array_length(r->'shares')<1 then raise exception 'Missing shares'; end if;
  if exists(select 1 from jsonb_array_elements(r->'shares') where value->>'member_id' is null or value->>'amount' is null
   or (value->>'amount')::numeric<0 or (value->>'amount')::numeric::text in ('NaN','Infinity','-Infinity')
   or round((value->>'amount')::numeric,2)<>(value->>'amount')::numeric)
   or (select count(*)<>count(distinct value->>'member_id') from jsonb_array_elements(r->'shares')) then raise exception 'Invalid shares'; end if;
  select sum((value->>'amount')::numeric) into total from jsonb_array_elements(r->'shares');
  if total<>(r->>'amount')::numeric then raise exception 'Shares must equal expense'; end if;
  perform pg_advisory_xact_lock(hashtextextended(rid::text,0));
  select * into existing from public.expenses where id=rid for update;
  if existing.id is not null and not p_replace then
   if jsonb_build_array(existing.household_id,existing.payer_member_id,existing.amount,existing.description,existing.kind,existing.category,
     existing.expense_date,existing.month,existing.automatic_debit,existing.installments_total,existing.installment_number,existing.installment_group)
    is distinct from jsonb_build_array(hid,(r->>'payer_member_id')::uuid,(r->>'amount')::numeric,r->>'description',r->>'kind',r->>'category',
     r->>'expense_date',r->>'month',(r->>'automatic_debit')::boolean,(r->>'installments_total')::integer,(r->>'installment_number')::integer,r->>'installment_group')
    or (select jsonb_agg(jsonb_build_array(member_id,amount) order by member_id) from public.expense_shares where expense_id=rid)
    is distinct from (select jsonb_agg(jsonb_build_array((value->>'member_id')::uuid,(value->>'amount')::numeric) order by (value->>'member_id')::uuid) from jsonb_array_elements(r->'shares')) then
    raise exception 'Idempotency conflict';
   end if;
   continue;
  end if;
  if p_replace then
   if existing.id is null or existing.household_id<>hid then raise exception 'Expense unavailable'; end if;
   update public.expenses set payer_member_id=(r->>'payer_member_id')::uuid,kind=r->>'kind',category=r->>'category',
    description=r->>'description',amount=(r->>'amount')::numeric,expense_date=r->>'expense_date',month=r->>'month',
    automatic_debit=(r->>'automatic_debit')::boolean where id=rid;
   delete from public.expense_shares where expense_id=rid;
  else
   insert into public.expenses(id,household_id,payer_member_id,kind,category,description,amount,expense_date,month,
    installments_total,installment_number,installment_group,automatic_debit,created_by,payment_status)
   values(rid,hid,(r->>'payer_member_id')::uuid,r->>'kind',r->>'category',r->>'description',(r->>'amount')::numeric,
    r->>'expense_date',r->>'month',(r->>'installments_total')::integer,(r->>'installment_number')::integer,
    r->>'installment_group',(r->>'automatic_debit')::boolean,auth.uid(),'scheduled');
  end if;
  for s in select value from jsonb_array_elements(r->'shares') loop
   insert into public.expense_shares(expense_id,member_id,amount) values(rid,(s->>'member_id')::uuid,(s->>'amount')::numeric);
  end loop;
  n=n+1;
 end loop;
 return n;
end $$;
revoke all on function public.save_expense_batch(jsonb,boolean) from public,anon;
grant execute on function public.save_expense_batch(jsonb,boolean) to authenticated;

create or replace function public.journey_history() returns trigger language plpgsql set search_path='' as $$
begin
 if tg_op='UPDATE' then
  new.history=old.history || jsonb_build_array(jsonb_build_object('at',now(),'progress',new.progress,'status',new.status));
 end if;
 return new;
end $$;
drop trigger if exists journey_history on public.nex_journeys;
create trigger journey_history before update on public.nex_journeys for each row execute function public.journey_history();

-- Serialize edits per trip before changing line items. Recompute gross cart total
-- inside the same transaction; the fiscal receipt and cashback remain independent.
create or replace function public.lock_market_trip() returns trigger language plpgsql set search_path='' as $$
declare trip uuid;
begin
 if tg_op='UPDATE' and new.trip_id<>old.trip_id then raise exception 'Moving items between trips is not supported'; end if;
 trip=case when tg_op='DELETE' then old.trip_id else new.trip_id end;
 perform 1 from public.market_trips where id=trip for update;
 if tg_op='DELETE' then return old; end if;
 return new;
end $$;
create or replace function public.recalculate_market_trip() returns trigger language plpgsql set search_path='' as $$
declare trip uuid;
begin
 trip=case when tg_op='DELETE' then old.trip_id else new.trip_id end;
 update public.market_trips set cart_total=coalesce((select round(sum(quantity*unit_price),2) from public.market_items where trip_id=trip),0) where id=trip;
 if tg_op='DELETE' then return old; end if;
 return new;
end $$;
drop trigger if exists lock_market_trip on public.market_items;
create trigger lock_market_trip before insert or update or delete on public.market_items for each row execute function public.lock_market_trip();
drop trigger if exists recalculate_market_trip on public.market_items;
create trigger recalculate_market_trip after insert or update or delete on public.market_items for each row execute function public.recalculate_market_trip();

create or replace function public.confirm_market_receipt(p_trip uuid,p_expected numeric,p_receipt numeric,p_cashback numeric)
returns void language plpgsql set search_path='' as $$
declare trip public.market_trips; total numeric;
begin
 select * into trip from public.market_trips where id=p_trip for update;
 if trip.id is null or not public.can_write_household(trip.household_id) then raise exception 'Trip unavailable'; end if;
 if p_receipt is null or p_cashback is null or p_receipt<0 or p_cashback<0 or p_cashback>p_receipt
  or p_receipt::text in ('NaN','Infinity','-Infinity') or p_cashback::text in ('NaN','Infinity','-Infinity') then raise exception 'Invalid receipt'; end if;
 select coalesce(round(sum(quantity*unit_price),2),0) into total from public.market_items where trip_id=p_trip;
 if p_expected is distinct from total then raise exception 'Cart changed; review again'; end if;
 update public.market_trips set cart_total=total,receipt_total=p_receipt,cashback_amount=p_cashback,status='closed',finished_at=now() where id=p_trip;
end $$;
revoke all on function public.confirm_market_receipt(uuid,numeric,numeric,numeric) from public,anon;
grant execute on function public.confirm_market_receipt(uuid,numeric,numeric,numeric) to authenticated;
commit;
