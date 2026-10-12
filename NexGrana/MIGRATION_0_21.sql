-- NexGrana 0.21.0 — administração segura de Achados e homologação isolada.
-- Aditiva e idempotente. Aplicar primeiro em um projeto Supabase de homologação.
begin;

create table if not exists public.app_admins (
 user_id uuid primary key references auth.users(id) on delete cascade,
 role text not null default 'offers_admin' check(role in ('offers_admin','owner')),
 enabled boolean not null default true,
 created_at timestamptz not null default now()
);

alter table public.app_admins enable row level security;
drop policy if exists own_admin_record on public.app_admins;
create policy own_admin_record on public.app_admins for select to authenticated
 using(user_id=auth.uid() and enabled);
revoke all on public.app_admins from anon,authenticated;
grant select on public.app_admins to authenticated;

create or replace function public.is_app_admin()
returns boolean language sql stable security definer set search_path='' as $$
 select exists(select 1 from public.app_admins where user_id=auth.uid() and enabled);
$$;
revoke all on function public.is_app_admin() from public,anon;
grant execute on function public.is_app_admin() to authenticated;

alter table public.affiliate_offers add column if not exists search_tags text[] not null default '{}';
alter table public.affiliate_offers add column if not exists sort_order integer not null default 1000;
alter table public.affiliate_offers add column if not exists created_by uuid references auth.users(id);
alter table public.affiliate_offers add column if not exists updated_by uuid references auth.users(id);

create table if not exists public.affiliate_offer_audit (
 id bigint generated always as identity primary key,
 offer_id uuid,
 actor_id uuid,
 action text not null check(action in ('INSERT','UPDATE','DELETE')),
 before_row jsonb,
 after_row jsonb,
 created_at timestamptz not null default now()
);
alter table public.affiliate_offer_audit enable row level security;
drop policy if exists admin_reads_offer_audit on public.affiliate_offer_audit;
create policy admin_reads_offer_audit on public.affiliate_offer_audit for select to authenticated
 using(public.is_app_admin());
revoke all on public.affiliate_offer_audit from anon,authenticated;
grant select on public.affiliate_offer_audit to authenticated;

create or replace function public.guard_affiliate_offer()
returns trigger language plpgsql security invoker set search_path='' as $$
begin
 if not public.is_app_admin() then raise exception 'Admin permission required'; end if;
 if new.url !~ '^https://(meli[.]la|([a-z0-9-]+[.])?mercadolivre[.]com[.]br)/' then
  raise exception 'Partner URL is not allowed';
 end if;
 if new.original_url is not null and new.original_url !~ '^https://(meli[.]la|([a-z0-9-]+[.])?mercadolivre[.]com[.]br)/' then
  raise exception 'Original partner URL is not allowed';
 end if;
 if new.price is not null and new.price < 0 then raise exception 'Invalid price'; end if;
 new.updated_at=now();
 new.updated_by=auth.uid();
 if tg_op='INSERT' then new.created_by=auth.uid(); end if;
 return new;
end $$;

drop trigger if exists guard_affiliate_offer on public.affiliate_offers;
create trigger guard_affiliate_offer before insert or update on public.affiliate_offers
 for each row execute function public.guard_affiliate_offer();

create or replace function public.audit_affiliate_offer()
returns trigger language plpgsql security definer set search_path='' as $$
begin
 insert into public.affiliate_offer_audit(offer_id,actor_id,action,before_row,after_row)
 values(coalesce(new.id,old.id),auth.uid(),tg_op,to_jsonb(old),to_jsonb(new));
 if tg_op='DELETE' then return old; end if;
 return new;
end $$;
drop trigger if exists audit_affiliate_offer on public.affiliate_offers;
create trigger audit_affiliate_offer after insert or update or delete on public.affiliate_offers
 for each row execute function public.audit_affiliate_offer();

drop policy if exists admin_manages_offers on public.affiliate_offers;
create policy admin_manages_offers on public.affiliate_offers for all to authenticated
 using(public.is_app_admin()) with check(public.is_app_admin());
grant select,insert,update,delete on public.affiliate_offers to authenticated;

-- Homologação: esta tabela deve receber UUIDs apenas no projeto de testes,
-- usando o SQL Editor/service role. Ela não concede administração de Achados.
create table if not exists public.qa_testers (
 user_id uuid primary key references auth.users(id) on delete cascade,
 enabled boolean not null default true,
 label text not null default '',
 created_at timestamptz not null default now()
);
alter table public.qa_testers enable row level security;
drop policy if exists own_qa_record on public.qa_testers;
create policy own_qa_record on public.qa_testers for select to authenticated
 using(user_id=auth.uid() and enabled);
revoke all on public.qa_testers from anon,authenticated;
grant select on public.qa_testers to authenticated;

create or replace function public.reset_qa_workspace(p_confirmation text)
returns boolean language plpgsql security definer set search_path='' as $$
declare hid uuid; member_count integer;
begin
 if p_confirmation<>'RESETAR_TESTE' or not exists(
  select 1 from public.qa_testers where user_id=auth.uid() and enabled
 ) then raise exception 'QA reset not allowed'; end if;
 select h.id into hid from public.households h
  join public.household_members m on m.household_id=h.id
  where h.owner_id=auth.uid() and m.user_id=auth.uid() and m.role='owner' and m.status='active'
  order by h.created_at desc limit 1 for update of h;
 if hid is null then return true; end if;
 select count(*) into member_count from public.household_members
  where household_id=hid and status='active';
 if member_count<>1 then raise exception 'QA reset requires a single-member workspace'; end if;
 delete from public.households where id=hid and owner_id=auth.uid();
 return found;
end $$;
revoke all on function public.reset_qa_workspace(text) from public,anon;
grant execute on function public.reset_qa_workspace(text) to authenticated;

create index if not exists affiliate_offers_enabled_order_idx
 on public.affiliate_offers(enabled,sort_order,updated_at desc);

notify pgrst,'reload schema';
commit;

select
 to_regclass('public.app_admins') as app_admins,
 to_regclass('public.affiliate_offer_audit') as offer_audit,
 to_regclass('public.qa_testers') as qa_testers,
 to_regprocedure('public.reset_qa_workspace(text)') as qa_reset_rpc;

-- Configuração manual em HOMOLOGAÇÃO, substituindo os UUIDs reais:
-- insert into public.qa_testers(user_id,label) values ('UUID-DA-CONTA-SIMTESTES86','Android QA') on conflict(user_id) do update set enabled=true;
-- insert into public.app_admins(user_id,role) values ('UUID-DA-CONTA-DO-LUCAS','owner') on conflict(user_id) do update set enabled=true,role='owner';
