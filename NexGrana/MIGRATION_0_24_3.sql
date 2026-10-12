-- Link a planning list to one active shopping session. Apply after 0.24.2.
begin;
alter table public.market_trips add column if not exists source_list_id uuid
 references public.shopping_lists(id) on delete set null;
alter table public.market_items add column if not exists source_list_item_id uuid
 references public.shopping_list_items(id) on delete set null;
alter table public.market_items add column if not exists picked boolean not null default false;
create unique index if not exists one_open_trip_per_list_0243
 on public.market_trips(source_list_id) where source_list_id is not null and status='open';
create unique index if not exists one_trip_item_per_list_item_0243
 on public.market_items(trip_id,source_list_item_id) where source_list_item_id is not null;

create or replace function public.start_market_trip_from_list(p_list uuid,p_market text)
returns uuid language plpgsql security invoker set search_path='' as $$
declare source public.shopping_lists%rowtype; existing uuid; trip uuid;
begin
 if auth.uid() is null or length(btrim(coalesce(p_market,''))) not between 1 and 100 then
  raise exception 'Informe o mercado';
 end if;
 select * into source from public.shopping_lists where id=p_list and created_by=auth.uid() for update;
 if not found then raise exception 'Lista indisponível para esta conta'; end if;
 select id into existing from public.market_trips where source_list_id=p_list and status='open' limit 1;
 if existing is not null then return existing; end if;
 insert into public.market_trips(household_id,market_name,budget,created_by,source_list_id)
 values(source.household_id,btrim(p_market),source.budget,auth.uid(),source.id)
 returning id into trip;
 insert into public.market_items(trip_id,household_id,product_name,quantity,unit_price,category,created_by,source_list_item_id)
 select trip,source.household_id,i.name,i.quantity,i.unit_price,'Outros',auth.uid(),i.id
 from public.shopping_list_items i where i.list_id=source.id order by i.created_at,i.id;
 return trip;
end $$;
revoke all on function public.start_market_trip_from_list(uuid,text) from public,anon;
grant execute on function public.start_market_trip_from_list(uuid,text) to authenticated;

-- Compare only confirmed items from a linked list. Manually added products
-- continue to count exactly as in the previous receipt flow.
create or replace function public.confirm_market_receipt(p_trip uuid,p_expected numeric,p_receipt numeric,p_cashback numeric)
returns void language plpgsql set search_path='' as $$
declare trip public.market_trips; total numeric;
begin
 select * into trip from public.market_trips where id=p_trip for update;
 if trip.id is null or trip.status<>'open' or not public.can_write_household(trip.household_id)
 then raise exception 'Trip unavailable'; end if;
 if p_receipt is null or p_cashback is null or p_receipt<0 or p_cashback<0 or p_cashback>p_receipt
  or p_receipt::text in ('NaN','Infinity','-Infinity') or p_cashback::text in ('NaN','Infinity','-Infinity')
 then raise exception 'Invalid receipt'; end if;
 select coalesce(round(sum(quantity*unit_price),2),0) into total from public.market_items
 where trip_id=p_trip and (source_list_item_id is null or picked);
 if p_expected is distinct from total then raise exception 'Cart changed; review again'; end if;
 update public.market_trips set cart_total=total,receipt_total=p_receipt,cashback_amount=p_cashback,
 status='closed',finished_at=now() where id=p_trip;
end $$;
notify pgrst,'reload schema';
commit;
