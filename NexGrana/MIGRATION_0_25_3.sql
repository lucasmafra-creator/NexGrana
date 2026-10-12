-- Atomic monthly closure batch; staging only until homologated.
begin;
create or replace function public.save_month_closures_safe(p_rows jsonb)
 returns integer language plpgsql security invoker set search_path='' as $$
declare r jsonb; hid uuid; period date; mid uuid; opened numeric; closed numeric; count_rows integer:=0; seen text[]:='{}'; scope text;
begin
 if auth.uid() is null or jsonb_typeof(p_rows)<>'array' or jsonb_array_length(p_rows) not between 1 and 64 then
  raise exception 'Invalid closure batch';
 end if;
 hid=(p_rows->0->>'household_id')::uuid; period=(p_rows->0->>'month_start')::date;
 if period is null or extract(day from period)<>1 or period+interval '1 month'>current_date then raise exception 'Month still open or invalid'; end if;
 if not public.can_write_household(hid) then raise exception 'Workspace unavailable'; end if;
 -- Shared lock serializes competing closures for this family.
 perform pg_catalog.pg_advisory_xact_lock(pg_catalog.hashtextextended(hid::text,0));
 for r in select value from jsonb_array_elements(p_rows) loop
  if (r->>'household_id')::uuid<>hid or (r->>'month_start')::date<>period then raise exception 'Mixed closure scopes'; end if;
  mid=nullif(r->>'member_id','')::uuid;
  if mid is not null and not exists(select 1 from public.household_members where id=mid and household_id=hid) then raise exception 'Member outside workspace'; end if;
  scope=coalesce(mid::text,'family');
  if scope=any(seen) then raise exception 'Duplicate closure scope'; end if;
  seen=array_append(seen,scope);
  opened=(r->>'opening_balance')::numeric; closed=(r->>'closing_balance')::numeric;
  if opened is null or closed is null or opened::text in ('NaN','Infinity','-Infinity') or closed::text in ('NaN','Infinity','-Infinity') then raise exception 'Invalid balances'; end if;
  insert into public.monthly_closures(id,household_id,member_id,month_start,opening_balance,closing_balance,closed_by,closed_at)
   values((r->>'id')::uuid,hid,mid,period,opened,closed,auth.uid(),now())
   on conflict(household_id,month_start,(coalesce(member_id,'00000000-0000-0000-0000-000000000000'::uuid)))
   do update set opening_balance=excluded.opening_balance,closing_balance=excluded.closing_balance,closed_by=auth.uid(),closed_at=now(),updated_at=now();
  count_rows=count_rows+1;
 end loop;
 return count_rows;
end $$;
revoke all on function public.save_month_closures_safe(jsonb) from public,anon;
grant execute on function public.save_month_closures_safe(jsonb) to authenticated;
notify pgrst,'reload schema';
commit;
