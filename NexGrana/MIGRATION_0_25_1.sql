-- Staging first. Scoped message tombstones and retry-safe message persistence.
begin;
create table if not exists public.nex_message_purges (
 id uuid primary key default gen_random_uuid(),
 conversation_id uuid not null references public.nex_conversations(id) on delete cascade,
 owner_user_id uuid not null references auth.users(id) on delete cascade,
 range_start timestamptz not null, range_end timestamptz not null,
 created_at timestamptz not null default now(),
 check(range_start<=range_end),
 unique(conversation_id,owner_user_id,range_start,range_end)
);
alter table public.nex_message_purges enable row level security;
drop policy if exists nex_message_purges_owner on public.nex_message_purges;
create policy nex_message_purges_owner on public.nex_message_purges for all to authenticated
 using(owner_user_id=auth.uid()) with check(owner_user_id=auth.uid() and exists(
 select 1 from public.nex_conversations c where c.id=conversation_id and c.owner_user_id=auth.uid()));
revoke all on public.nex_message_purges from public,anon;
grant select,insert on public.nex_message_purges to authenticated;
create or replace function public.purge_nex_messages(
 p_conversation uuid, p_member uuid, p_start timestamptz, p_end timestamptz,
 p_preview boolean default true
) returns integer language plpgsql security invoker set search_path='' as $$
declare affected integer;
begin
 if auth.uid() is null or p_start is null or p_end is null or p_start>p_end or p_end>now()+interval '5 minutes' then
  raise exception 'Invalid purge interval';
 end if;
 perform 1 from public.nex_conversations c where c.id=p_conversation
  and c.member_id=p_member and c.owner_user_id=auth.uid() and c.status<>'deleted' for update;
 if not found then
  raise exception 'Conversation unavailable for this account';
 end if;
 if p_preview then
  select count(*) into affected from public.nex_messages m where m.conversation_id=p_conversation
   and m.member_id=p_member and m.owner_user_id=auth.uid() and m.state<>'deleted'
   and m.created_at between p_start and p_end;
 else
  insert into public.nex_message_purges(conversation_id,owner_user_id,range_start,range_end)
   values(p_conversation,auth.uid(),p_start,p_end) on conflict do nothing;
  update public.nex_messages m set state='deleted',deleted_at=now(),content='[Mensagem removida]'
   where m.conversation_id=p_conversation and m.member_id=p_member and m.owner_user_id=auth.uid()
   and m.state<>'deleted' and m.created_at between p_start and p_end;
  get diagnostics affected = row_count;
 end if;
 return affected;
end $$;

create or replace function public.save_nex_message_safe(
 p_conversation uuid,p_member uuid,p_role text,p_content text,p_request uuid,
 p_created_at timestamptz default null
) returns jsonb language plpgsql security invoker set search_path='' as $$
declare conversation public.nex_conversations; existing public.nex_messages; message public.nex_messages;
begin
 if auth.uid() is null or p_request is null or p_role not in ('user','assistant','system')
  or p_content is null or char_length(btrim(p_content)) not between 1 and 12000
  or p_created_at>now()+interval '5 minutes' then raise exception 'Invalid message'; end if;
 select * into conversation from public.nex_conversations c where c.id=p_conversation
  and c.member_id=p_member and c.owner_user_id=auth.uid() and c.status<>'deleted' for update;
 if not found then raise exception 'Conversation unavailable for this account'; end if;
 select * into existing from public.nex_messages m where m.conversation_id=p_conversation
  and m.request_id=p_request and m.logical_role=p_role and m.owner_user_id=auth.uid()
  order by (m.state='deleted') desc,m.created_at desc limit 1;
 if found then return jsonb_build_object('id',existing.id,'state',existing.state); end if;
 if exists(select 1 from public.nex_message_purges p where p.conversation_id=p_conversation
  and p.owner_user_id=auth.uid() and coalesce(p_created_at,now()) between p.range_start and p.range_end) then
  return jsonb_build_object('id',null,'state','deleted');
 end if;
 insert into public.nex_messages(conversation_id,household_id,member_id,owner_user_id,
  logical_role,content,request_id,created_at) values(conversation.id,conversation.household_id,
  p_member,auth.uid(),p_role,btrim(p_content),p_request,coalesce(p_created_at,now())) returning * into message;
 return jsonb_build_object('id',message.id,'state',message.state);
end $$;
revoke all on function public.purge_nex_messages(uuid,uuid,timestamptz,timestamptz,boolean) from public,anon;
revoke all on function public.save_nex_message_safe(uuid,uuid,text,text,uuid,timestamptz) from public,anon;
grant execute on function public.purge_nex_messages(uuid,uuid,timestamptz,timestamptz,boolean) to authenticated;
grant execute on function public.save_nex_message_safe(uuid,uuid,text,text,uuid,timestamptz) to authenticated;
notify pgrst,'reload schema';
commit;
