-- Staging: apply after 0.25.3. Receipt -> ledger atomically, once per trip.
begin;
alter table public.market_items add column if not exists deleted_at timestamptz;
alter table public.market_trips add column if not exists deleted_at timestamptz;
create table if not exists public.market_expense_links (
 trip_id uuid primary key, household_id uuid not null references public.households(id),
 expense_id uuid not null unique, request jsonb not null,
 created_by uuid not null references auth.users(id), created_at timestamptz not null default now()
);
alter table public.market_expense_links enable row level security;
drop policy if exists market_expense_read on public.market_expense_links;
create policy market_expense_read on public.market_expense_links for select to authenticated
 using(public.can_write_household(household_id));
drop policy if exists market_expense_insert on public.market_expense_links;
create policy market_expense_insert on public.market_expense_links for insert to authenticated
 with check(created_by=auth.uid() and public.can_write_household(household_id)
 and exists(select 1 from public.market_trips t where t.id=trip_id and t.household_id=market_expense_links.household_id and t.created_by=auth.uid())
 and exists(select 1 from public.expenses e where e.id=expense_id and e.household_id=market_expense_links.household_id and e.created_by=auth.uid()));
grant select,insert on public.market_expense_links to authenticated;
revoke all on public.market_expense_links from anon;

create or replace function public.finalize_market_expense_safe(
 p_trip uuid,p_expected numeric,p_receipt numeric,p_cashback numeric,p_member uuid,p_date date,p_expense uuid)
returns uuid language plpgsql security invoker set search_path='' as $$
declare trip public.market_trips; link public.market_expense_links; total numeric; request jsonb; body jsonb;
begin
 select * into trip from public.market_trips where id=p_trip for update;
 if trip.id is null or trip.deleted_at is not null or trip.created_by<>auth.uid() or not public.can_write_household(trip.household_id) then raise exception 'Trip unavailable'; end if;
 if p_expense is null or p_member is null or p_date is null or p_receipt is null or p_cashback is null
 or p_receipt<=0 or p_cashback<0 or p_cashback>p_receipt
 or p_receipt::text in ('NaN','Infinity','-Infinity') or p_cashback::text in ('NaN','Infinity','-Infinity')
 or round(p_receipt,2)<>p_receipt or round(p_cashback,2)<>p_cashback then raise exception 'Invalid receipt'; end if;
 if not exists(select 1 from public.household_members where id=p_member and household_id=trip.household_id) then raise exception 'Member unavailable'; end if;
 request=jsonb_build_array(p_expected,p_receipt,p_cashback,p_member,p_date,p_expense);
 select * into link from public.market_expense_links where trip_id=p_trip;
 if found then
  if link.request is distinct from request then raise exception 'Idempotency conflict: purchase already posted'; end if;
  if not exists(select 1 from public.expenses where id=link.expense_id and household_id=trip.household_id) then
   raise exception 'Purchase already posted; expense was removed. Review ledger';
  end if;
  return link.expense_id;
 end if;
 select coalesce(round(sum(quantity*unit_price),2),0) into total from public.market_items
 where trip_id=p_trip and deleted_at is null and (source_list_item_id is null or picked);
 if p_expected is distinct from total then raise exception 'Cart changed; review again'; end if;
 body=jsonb_build_object('id',p_expense,'household_id',trip.household_id,'payer_member_id',p_member,
 'kind','Variável','category','Alimentação','description','Compra em '||trip.market_name,'amount',p_receipt,
 'expense_date',p_date::text,'month',to_char(p_date,'MM/YYYY'),'installments_total',1,
 'installment_number',1,'installment_group','','automatic_debit',false,
 'shares',jsonb_build_array(jsonb_build_object('member_id',p_member,'amount',p_receipt)));
 perform public.save_expense_batch(jsonb_build_array(body),false);
 insert into public.market_expense_links(trip_id,household_id,expense_id,request,created_by)
 values(p_trip,trip.household_id,p_expense,request,auth.uid());
 update public.market_trips set cart_total=total,receipt_total=p_receipt,cashback_amount=p_cashback,
 status='closed',finished_at=now() where id=p_trip;
 return p_expense;
end $$;
revoke all on function public.finalize_market_expense_safe(uuid,numeric,numeric,numeric,uuid,date,uuid) from public,anon;
grant execute on function public.finalize_market_expense_safe(uuid,numeric,numeric,numeric,uuid,date,uuid) to authenticated;
notify pgrst,'reload schema';
commit;
