-- NexGrana 0.20.0 — migração aditiva, idempotente e sem exclusão de dados.
-- Aplicar somente após backup e validação em homologação.
begin;

create table if not exists public.nex_conversations (
 id uuid primary key default gen_random_uuid(),
 household_id uuid not null references public.households(id) on delete cascade,
 member_id uuid not null references public.household_members(id) on delete cascade,
 owner_user_id uuid not null references auth.users(id) on delete cascade,
 kind text not null default 'free' check(kind in ('free','pinned')),
 status text not null default 'active' check(status in ('active','archived','deleted')),
 title text not null default 'Conversa com o Nex',
 pinned_slot smallint check(pinned_slot between 1 and 5),
 version integer not null default 1 check(version>0),
 created_at timestamptz not null default now(),
 updated_at timestamptz not null default now(),
 archived_at timestamptz,
 deleted_at timestamptz,
 check((kind='pinned' and pinned_slot is not null) or (kind='free' and pinned_slot is null))
);

create table if not exists public.nex_messages (
 id uuid primary key default gen_random_uuid(),
 conversation_id uuid not null references public.nex_conversations(id) on delete cascade,
 household_id uuid not null references public.households(id) on delete cascade,
 member_id uuid not null references public.household_members(id) on delete cascade,
 owner_user_id uuid not null references auth.users(id) on delete cascade,
 logical_role text not null check(logical_role in ('user','assistant','system')),
 content text not null check(char_length(content) between 1 and 12000),
 request_id uuid,
 state text not null default 'synced' check(state in ('pending','synced','failed','deleted')),
 metadata jsonb not null default '{}'::jsonb,
 created_at timestamptz not null default now(),
 deleted_at timestamptz
);

create unique index if not exists nex_one_free_conversation
 on public.nex_conversations(household_id,member_id,owner_user_id)
 where kind='free' and status='active';
create unique index if not exists nex_unique_pinned_slot
 on public.nex_conversations(household_id,member_id,owner_user_id,pinned_slot)
 where kind='pinned' and status='active';
create unique index if not exists nex_message_request_role
 on public.nex_messages(conversation_id,request_id,logical_role)
 where request_id is not null and state<>'deleted';
create index if not exists nex_conversation_activity
 on public.nex_conversations(household_id,member_id,owner_user_id,updated_at desc);
create index if not exists nex_message_cursor
 on public.nex_messages(conversation_id,created_at desc,id);

create or replace function public.guard_nex_conversation_scope() returns trigger
language plpgsql set search_path='' as $$
begin
 if tg_op='UPDATE' and (
  new.household_id<>old.household_id or new.member_id<>old.member_id or new.owner_user_id<>old.owner_user_id
 ) then raise exception 'Immutable conversation scope'; end if;
 if not exists(
  select 1 from public.household_members hm
  where hm.id=new.member_id and hm.household_id=new.household_id and hm.status='active'
  and (hm.user_id=auth.uid() or hm.user_id is null)
 ) then raise exception 'Member unavailable for this account'; end if;
 if new.owner_user_id<>auth.uid() then raise exception 'Invalid conversation owner'; end if;
 new.updated_at=now();
 if tg_op='UPDATE' then new.version=old.version+1; end if;
 return new;
end $$;

create or replace function public.guard_nex_message_scope() returns trigger
language plpgsql set search_path='' as $$
begin
 if tg_op='UPDATE' and (
  new.conversation_id<>old.conversation_id or new.household_id<>old.household_id
  or new.member_id<>old.member_id or new.owner_user_id<>old.owner_user_id
 ) then raise exception 'Immutable message scope'; end if;
 if new.owner_user_id<>auth.uid() then raise exception 'Invalid message owner'; end if;
 if not exists(
  select 1 from public.nex_conversations c
  where c.id=new.conversation_id and c.household_id=new.household_id
  and c.member_id=new.member_id and c.owner_user_id=new.owner_user_id
  and c.status<>'deleted'
 ) then raise exception 'Conversation scope mismatch'; end if;
 return new;
end $$;

drop trigger if exists guard_nex_conversation on public.nex_conversations;
create trigger guard_nex_conversation before insert or update on public.nex_conversations
for each row execute function public.guard_nex_conversation_scope();
drop trigger if exists guard_nex_message on public.nex_messages;
create trigger guard_nex_message before insert or update on public.nex_messages
for each row execute function public.guard_nex_message_scope();

alter table public.nex_conversations enable row level security;
alter table public.nex_messages enable row level security;

drop policy if exists own_nex_conversations on public.nex_conversations;
create policy own_nex_conversations on public.nex_conversations for all to authenticated
 using(owner_user_id=auth.uid() and public.is_household_member(household_id))
 with check(owner_user_id=auth.uid() and public.is_household_member(household_id));
drop policy if exists own_nex_messages on public.nex_messages;
create policy own_nex_messages on public.nex_messages for all to authenticated
 using(owner_user_id=auth.uid() and public.is_household_member(household_id))
 with check(owner_user_id=auth.uid() and public.is_household_member(household_id));

revoke all on public.nex_conversations,public.nex_messages from anon;
revoke all on public.nex_conversations,public.nex_messages from authenticated;
grant select,insert,update,delete on public.nex_conversations,public.nex_messages to authenticated;

create or replace function public.pin_nex_conversation(
 p_conversation uuid, p_title text, p_replace uuid default null
) returns uuid
language plpgsql security invoker set search_path='' as $$
declare c public.nex_conversations%rowtype; slot_no integer; new_free uuid;
begin
 select * into c from public.nex_conversations
  where id=p_conversation and owner_user_id=auth.uid() and kind='free' and status='active'
  for update;
 if c.id is null then raise exception 'Free conversation unavailable'; end if;
 perform pg_advisory_xact_lock(hashtext(c.household_id::text||c.member_id::text||auth.uid()::text));
 if p_replace is not null then
  update public.nex_conversations set status='archived',archived_at=now()
   where id=p_replace and household_id=c.household_id and member_id=c.member_id
   and owner_user_id=auth.uid() and kind='pinned' and status='active';
 end if;
 select s into slot_no from generate_series(1,5) s
  where not exists(select 1 from public.nex_conversations x where x.household_id=c.household_id
   and x.member_id=c.member_id and x.owner_user_id=auth.uid() and x.kind='pinned'
   and x.status='active' and x.pinned_slot=s) order by s limit 1;
 if slot_no is null then raise exception 'Pinned conversation limit reached'; end if;
 update public.nex_conversations set kind='pinned',pinned_slot=slot_no,
  title=left(coalesce(nullif(trim(p_title),''),'Conversa com o Nex'),120)
  where id=c.id;
 insert into public.nex_conversations(household_id,member_id,owner_user_id,kind,status,title)
  values(c.household_id,c.member_id,auth.uid(),'free','active','Chat livre') returning id into new_free;
 return new_free;
end $$;

create or replace function public.unpin_nex_conversation(p_conversation uuid) returns boolean
language plpgsql security invoker set search_path='' as $$
begin
 update public.nex_conversations set status='archived',archived_at=now()
  where id=p_conversation and owner_user_id=auth.uid() and kind='pinned' and status='active';
 return found;
end $$;

revoke all on function public.pin_nex_conversation(uuid,text,uuid) from public,anon;
revoke all on function public.unpin_nex_conversation(uuid) from public,anon;
grant execute on function public.pin_nex_conversation(uuid,text,uuid) to authenticated;
grant execute on function public.unpin_nex_conversation(uuid) to authenticated;

alter table public.affiliate_offers add column if not exists original_url text;
alter table public.affiliate_offers add column if not exists image_url text;
alter table public.affiliate_offers add column if not exists seller text;
alter table public.affiliate_offers add column if not exists compatibility text;
alter table public.affiliate_offers add column if not exists source text not null default 'manual';
alter table public.affiliate_offers add column if not exists previous_price numeric(14,2);
alter table public.affiliate_offers add column if not exists rating numeric(3,2);
alter table public.affiliate_offers add column if not exists sales_count integer;
alter table public.affiliate_offers add column if not exists updated_at timestamptz not null default now();

insert into public.affiliate_offers(id,title,subtitle,provider,url,original_url,category,enabled,expires_at,platform,product_key,currency,price,campaign,sponsored,compatibility,source)
values
 ('02000000-0000-0000-0000-000000000001','Cafeteira Espresso LOV preta — TRES 3 Corações','Confira voltagem, vendedor, preço e condições.','Mercado Livre','https://meli.la/1PQ6Tsq','https://meli.la/1PQ6Tsq','Casa e cozinha',true,'2099-12-31T23:59:59Z','all','cafeteira-lov-preta','BRL',null,'catalogo-inicial-020',false,'Confirmar voltagem','owner_provided'),
 ('02000000-0000-0000-0000-000000000002','Carregador compatível com iPhone — fonte tipo C','Confirme potência, certificação e compatibilidade.','Mercado Livre','https://meli.la/1eo2BxR','https://meli.la/1eo2BxR','Tecnologia',true,'2099-12-31T23:59:59Z','all','carregador-iphone-tipo-c','BRL',null,'catalogo-inicial-020',false,'Confirmar modelos compatíveis','owner_provided'),
 ('02000000-0000-0000-0000-000000000003','Lavadora portátil com duas baterias e maleta','Confira pressão declarada e itens incluídos.','Mercado Livre','https://meli.la/1UHNRHW','https://meli.la/1UHNRHW','Casa e ferramentas',true,'2099-12-31T23:59:59Z','all','lavadora-portatil-maleta','BRL',null,'catalogo-inicial-020',false,'Confirmar pressão e itens','owner_provided'),
 ('02000000-0000-0000-0000-000000000004','Kit com 2 travesseiros Oaktex 70 × 50 cm','Confirme composição, medidas e quantidade.','Mercado Livre','https://meli.la/1hC8mC7','https://meli.la/1hC8mC7','Casa',true,'2099-12-31T23:59:59Z','all','kit-travesseiros-oaktex','BRL',null,'catalogo-inicial-020',false,'Confirmar composição e quantidade','owner_provided'),
 ('02000000-0000-0000-0000-000000000005','Kit de soquetes e catraca, 216 peças, Cr-V','Confira a composição real do kit.','Mercado Livre','https://meli.la/1D1t21D','https://meli.la/1D1t21D','Ferramentas',true,'2099-12-31T23:59:59Z','all','kit-soquetes-216','BRL',null,'catalogo-inicial-020',false,'Confirmar composição','owner_provided'),
 ('02000000-0000-0000-0000-000000000006','Fone para capacete Bluetooth RGB','Confira funções e compatibilidade; não presumimos intercomunicação.','Mercado Livre','https://meli.la/1YRwdMx','https://meli.la/1YRwdMx','Acessórios',true,'2099-12-31T23:59:59Z','all','fone-capacete-bluetooth','BRL',null,'catalogo-inicial-020',false,'Confirmar funções','owner_provided')
on conflict(id) do nothing;

notify pgrst,'reload schema';
commit;

select
 to_regclass('public.nex_conversations') as nex_conversations,
 to_regclass('public.nex_messages') as nex_messages,
 to_regprocedure('public.pin_nex_conversation(uuid,text,uuid)') as pin_rpc,
 (select count(*) from public.affiliate_offers where campaign='catalogo-inicial-020') as initial_offers;
