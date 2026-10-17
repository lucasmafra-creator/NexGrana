-- Reversible Mercado edits/deletions. Source rows are soft deleted; ledger stays untouched.
begin;
alter table public.market_items add column if not exists deleted_at timestamptz;
alter table public.market_trips add column if not exists deleted_at timestamptz;
create table if not exists public.market_actions (
 id uuid primary key, household_id uuid not null references public.households(id),
 actor uuid not null references auth.users(id), kind text not null check(kind in ('item','trip')),
 row_id uuid not null, before_state jsonb not null, after_state jsonb not null,
 undo_of uuid references public.market_actions(id), created_at timestamptz not null default now(),
 unique(undo_of)
);
alter table public.market_actions enable row level security;
drop policy if exists market_actions_read on public.market_actions;
create policy market_actions_read on public.market_actions for select to authenticated
 using(actor=auth.uid() and public.can_write_household(household_id));
drop policy if exists market_actions_insert on public.market_actions;
create policy market_actions_insert on public.market_actions for insert to authenticated
 with check(actor=auth.uid() and public.can_write_household(household_id));
grant select,insert on public.market_actions to authenticated;
revoke all on public.market_actions from anon;

create or replace function public.mutate_market_safe(p_kind text,p_id uuid,p_operation uuid,p_expected jsonb,p_values jsonb,p_undo uuid default null)
returns jsonb language plpgsql security invoker set search_path='' as $$
declare hid uuid; owner uuid; trip uuid; current_state jsonb; target jsonb; old public.market_actions; duplicate public.market_actions;
begin
 if p_kind not in ('item','trip') or p_operation is null or jsonb_typeof(p_expected)<>'object' or jsonb_typeof(p_values)<>'object' then raise exception 'Invalid action'; end if;
 if p_expected ? 'deleted_at' then
  p_expected=jsonb_set(p_expected,'{deleted_at}',coalesce(to_jsonb((p_expected->>'deleted_at')::timestamptz),'null'::jsonb));
 end if;
 if p_values ? 'deleted_at' then
  p_values=jsonb_set(p_values,'{deleted_at}',coalesce(to_jsonb((p_values->>'deleted_at')::timestamptz),'null'::jsonb));
 end if;
 -- Serialize all actions on a trip before row locks, matching the item trigger order.
 if p_kind='item' then select trip_id into trip from public.market_items where id=p_id;
 else trip=p_id; end if;
 perform 1 from public.market_trips where id=trip for update;
 if p_kind='item' then
  select household_id,created_by,jsonb_build_object('product_name',product_name,'quantity',quantity,'unit_price',unit_price,'category',category,'picked',picked,'deleted_at',deleted_at)
  into hid,owner,current_state from public.market_items where id=p_id for update;
 else
  select household_id,created_by,jsonb_build_object('deleted_at',deleted_at)
  into hid,owner,current_state from public.market_trips where id=p_id for update;
 end if;
 if hid is null or owner<>auth.uid() or not public.can_write_household(hid) then raise exception 'Row unavailable'; end if;
 select * into duplicate from public.market_actions where id=p_operation;
 if found then
  if duplicate.row_id<>p_id or duplicate.kind<>p_kind or duplicate.before_state<>p_expected
   or duplicate.after_state<>(p_expected||p_values) or duplicate.undo_of is distinct from p_undo then raise exception 'Idempotency conflict'; end if;
  return duplicate.after_state;
 end if;
 if current_state is distinct from p_expected then raise exception 'Version conflict: refresh before editing'; end if;
 if exists(select 1 from jsonb_object_keys(p_values) k where k not in ('product_name','quantity','unit_price','category','picked','deleted_at'))
 or (p_kind='trip' and exists(select 1 from jsonb_object_keys(p_values) k where k<>'deleted_at')) then raise exception 'Invalid fields'; end if;
 target=current_state||p_values;
 if p_undo is not null then
  select * into old from public.market_actions where id=p_undo and actor=auth.uid() and kind=p_kind and row_id=p_id;
  if not found or old.after_state<>current_state or old.before_state<>target then raise exception 'Undo unavailable or changed'; end if;
 end if;
 if p_kind='item' then
  if length(btrim(target->>'product_name')) not between 1 and 150 or length(target->>'category') not between 1 and 80
   or (target->>'quantity')::numeric<=0 or (target->>'unit_price')::numeric<0
   or (target->>'quantity')::numeric::text in ('NaN','Infinity','-Infinity')
   or (target->>'unit_price')::numeric::text in ('NaN','Infinity','-Infinity')
   or round((target->>'quantity')::numeric,3)<>(target->>'quantity')::numeric
   or round((target->>'unit_price')::numeric,2)<>(target->>'unit_price')::numeric then raise exception 'Invalid product'; end if;
  update public.market_items set product_name=target->>'product_name',quantity=(target->>'quantity')::numeric,
   unit_price=(target->>'unit_price')::numeric,category=target->>'category',picked=(target->>'picked')::boolean,
   deleted_at=(target->>'deleted_at')::timestamptz where id=p_id;
 else update public.market_trips set deleted_at=(target->>'deleted_at')::timestamptz where id=p_id; end if;
 insert into public.market_actions(id,household_id,actor,kind,row_id,before_state,after_state,undo_of)
 values(p_operation,hid,auth.uid(),p_kind,p_id,current_state,target,p_undo);
 return target;
end $$;
revoke all on function public.mutate_market_safe(text,uuid,uuid,jsonb,jsonb,uuid) from public,anon;
grant execute on function public.mutate_market_safe(text,uuid,uuid,jsonb,jsonb,uuid) to authenticated;
-- Retain receipt eligibility: a removed product never contributes to totals.
create or replace function public.recalculate_market_trip() returns trigger language plpgsql set search_path='' as $$
declare trip uuid;
begin
 trip=case when tg_op='DELETE' then old.trip_id else new.trip_id end;
 update public.market_trips set cart_total=coalesce((select round(sum(quantity*unit_price),2) from public.market_items where trip_id=trip and deleted_at is null and (source_list_item_id is null or picked)),0) where id=trip;
 if tg_op='DELETE' then return old; end if;return new;
end $$;
create or replace function public.confirm_market_receipt(p_trip uuid,p_expected numeric,p_receipt numeric,p_cashback numeric)
returns void language plpgsql set search_path='' as $$
declare trip public.market_trips; total numeric;
begin
 select * into trip from public.market_trips where id=p_trip for update;
 if trip.id is null or trip.deleted_at is not null or not public.can_write_household(trip.household_id)
 then raise exception 'Trip unavailable'; end if;
 if p_receipt is null or p_cashback is null or p_receipt<0 or p_cashback<0 or p_cashback>p_receipt
  or p_receipt::text in ('NaN','Infinity','-Infinity') or p_cashback::text in ('NaN','Infinity','-Infinity')
 then raise exception 'Invalid receipt'; end if;
 select coalesce(round(sum(quantity*unit_price),2),0) into total from public.market_items
 where trip_id=p_trip and deleted_at is null and (source_list_item_id is null or picked);
 if p_expected is distinct from total then raise exception 'Cart changed; review again'; end if;
 if trip.status='closed' then
  if trip.receipt_total=p_receipt and trip.cashback_amount=p_cashback then return; end if;
  raise exception 'Receipt already confirmed; review recorded values';
 end if;
 update public.market_trips set cart_total=total,receipt_total=p_receipt,cashback_amount=p_cashback,
 status='closed',finished_at=now() where id=p_trip;
end $$;

notify pgrst,'reload schema';
commit;
