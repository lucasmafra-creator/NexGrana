-- Catálogo comercial SIM Labs. Aplicar em homologação depois de 0.25.5.
-- Administração permanece restrita a app_admins; nenhum dado financeiro é acessado.
begin;
create table if not exists public.offer_partner_hosts (
 host text primary key check(host=lower(host) and host ~ '^[a-z0-9]([a-z0-9.-]*[a-z0-9])?$' and position('.' in host)>0 and host !~ '[.][.]' and host !~ '^[0-9.]+$' and host !~ '[.](local|localhost|internal|invalid|test)$'),
 enabled boolean not null default true, updated_at timestamptz not null default now()
);
insert into public.offer_partner_hosts(host) values('meli.la'),('mercadolivre.com.br'),('www.mercadolivre.com.br') on conflict do nothing;
alter table public.offer_partner_hosts enable row level security;
drop policy if exists read_partner_hosts on public.offer_partner_hosts;
create policy read_partner_hosts on public.offer_partner_hosts for select to authenticated using(enabled or public.is_app_admin());
drop policy if exists admin_partner_hosts on public.offer_partner_hosts;
create policy admin_partner_hosts on public.offer_partner_hosts for all to authenticated using(public.is_app_admin()) with check(public.is_app_admin());
revoke all on public.offer_partner_hosts from public,anon,authenticated;
grant select,insert,update,delete on public.offer_partner_hosts to authenticated;
alter table public.affiliate_offers add column if not exists verified_at timestamptz;
alter table public.affiliate_offers add column if not exists availability text not null default 'unknown';
alter table public.affiliate_offers add column if not exists affiliate boolean not null default false;
alter table public.affiliate_offers add column if not exists catalog_origin uuid;
create table if not exists public.sim_catalog_state (
 origin uuid primary key, generated_at timestamptz not null, manifest jsonb not null,
 updated_at timestamptz not null default now()
);
alter table public.sim_catalog_state enable row level security;
drop policy if exists admin_sim_catalog on public.sim_catalog_state;
create policy admin_sim_catalog on public.sim_catalog_state for all to authenticated using(public.is_app_admin()) with check(public.is_app_admin());
revoke all on public.sim_catalog_state from public,anon,authenticated;
grant select,insert,update on public.sim_catalog_state to authenticated;
create or replace function public.offer_url_allowed(p_url text)
returns boolean language sql stable security invoker set search_path='' as $$
 select p_url ~ '^https://[a-z0-9.-]+(/|$)' and char_length(p_url)<=2000 and p_url !~ '#' and exists (
  select 1 from public.offer_partner_hosts h where h.enabled and h.host=substring(p_url from '^https://([^/]+)')
 );
$$;
revoke all on function public.offer_url_allowed(text) from public,anon;
grant execute on function public.offer_url_allowed(text) to authenticated;
create or replace function public.guard_affiliate_offer()
returns trigger language plpgsql security invoker set search_path='' as $$
begin
 if not public.is_app_admin() then raise exception 'Admin permission required'; end if;
 if char_length(trim(new.title))<4 or char_length(new.title)>180 then raise exception 'Invalid title'; end if;
 if not public.offer_url_allowed(new.url) or (new.original_url is not null and not public.offer_url_allowed(new.original_url)) then raise exception 'Partner URL is not allowed'; end if;
 if new.image_url is not null and (new.image_url !~ '^https://http2[.]mlstatic[.]com/' or char_length(trim(new.image_alt))<4) then raise exception 'Image URL or description is not allowed'; end if;
 if (new.price is not null and (new.price<0 or new.price::text in ('NaN','Infinity','-Infinity'))) or (new.previous_price is not null and (new.previous_price<0 or new.previous_price::text in ('NaN','Infinity','-Infinity'))) then raise exception 'Invalid price'; end if;
 if new.currency<>'BRL' or new.availability not in ('unknown','in_stock','out_of_stock') then raise exception 'Invalid currency/availability'; end if;
 if new.sort_order<0 or new.sort_order>999999 or cardinality(new.search_tags)>20 then raise exception 'Invalid order/tags'; end if;
 if new.enabled and new.expires_at<=now() then raise exception 'Published offer is expired'; end if;
 if new.source='sim_labs' and new.enabled and (new.availability='out_of_stock' or new.expires_at>now()+interval '7 days' or (new.price is not null and (new.verified_at is null or new.verified_at<now()-interval '24 hours' or new.verified_at>now()+interval '5 minutes'))) then raise exception 'SIM offer is not current'; end if;
 new.updated_at=now();new.updated_by=auth.uid();
 if tg_op='INSERT' then new.created_by=auth.uid(); end if;
 return new;
end $$;
drop policy if exists current_offers on public.affiliate_offers;
create policy current_offers on public.affiliate_offers for select to authenticated using (
 enabled and expires_at>now() and availability<>'out_of_stock' and (source<>'sim_labs' or price is null or (verified_at>=now()-interval '24 hours' and verified_at<=now()+interval '5 minutes'))
);
create or replace function public.apply_sim_offer_catalog(p_manifest jsonb)
returns jsonb language plpgsql security invoker set search_path='' as $$
declare origin_id uuid; generated timestamptz; prev public.sim_catalog_state%rowtype; h text; entry jsonb; oid uuid; ids uuid[]='{}'; n int=0; old public.affiliate_offers%rowtype;
begin
 if not public.is_app_admin() then raise exception 'Admin permission required'; end if;
 if pg_column_size(p_manifest)>8*1024*1024 or p_manifest->>'schema' is distinct from 'sim-labs.offer-catalog/1' or jsonb_typeof(p_manifest->'offers') is distinct from 'array' or jsonb_typeof(p_manifest->'partner_hosts') is distinct from 'array' or coalesce((p_manifest->>'contains_user_finances')::boolean,true) then raise exception 'Invalid manifest'; end if;
 if jsonb_array_length(p_manifest->'offers')>500 or jsonb_array_length(p_manifest->'partner_hosts')>30 then raise exception 'Catalog limit'; end if;
 origin_id=(p_manifest->>'origin')::uuid;generated=(p_manifest->>'generated_at')::timestamptz;
 if origin_id is null or generated is null or generated<now()-interval '30 minutes' or generated>now()+interval '5 minutes' then raise exception 'Invalid catalog timestamp/origin'; end if;
 -- Serialize this origin, including first publication; reject a late snapshot.
 perform pg_advisory_xact_lock(hashtextextended(origin_id::text,0));
 select * into prev from public.sim_catalog_state where origin=origin_id;
 if found then
  if prev.manifest=p_manifest then return jsonb_build_object('status','duplicate','count',jsonb_array_length(p_manifest->'offers')); end if;
  if generated<=prev.generated_at then raise exception 'Stale catalog'; end if;
 end if;
 for h in select jsonb_array_elements_text(p_manifest->'partner_hosts') loop
  insert into public.offer_partner_hosts(host) values(h) on conflict(host) do update set enabled=true,updated_at=now();
 end loop;
 for entry in select jsonb_array_elements(p_manifest->'offers') loop
  oid=(entry->>'id')::uuid;
  if oid is null or oid=any(ids) or entry->>'product_key' is distinct from 'sim:'||origin_id::text||':'||oid::text or entry->>'source' is distinct from 'sim_labs' then raise exception 'Invalid offer identity'; end if;
  ids=array_append(ids,oid);
  select * into old from public.affiliate_offers where id=oid;
  if found and (old.source<>'sim_labs' or old.catalog_origin is distinct from origin_id or old.product_key is distinct from entry->>'product_key') then raise exception 'Existing offer belongs to another catalog'; end if;
  insert into public.affiliate_offers(id,title,subtitle,provider,url,original_url,category,price,previous_price,currency,verified_at,expires_at,availability,affiliate,enabled,source,product_key,campaign,platform,sort_order,catalog_origin)
  values(oid,entry->>'title',coalesce(entry->>'subtitle',''),entry->>'provider',entry->>'url',entry->>'url',coalesce(entry->>'category','Outros'),(entry->>'price')::numeric,(entry->>'previous_price')::numeric,entry->>'currency',(entry->>'verified_at')::timestamptz,(entry->>'expires_at')::timestamptz,entry->>'availability',coalesce((entry->>'affiliate')::boolean,false),coalesce((entry->>'enabled')::boolean,false),'sim_labs',entry->>'product_key','sim-labs-catalog','all',1000,origin_id)
  on conflict(id) do update set title=excluded.title,subtitle=excluded.subtitle,provider=excluded.provider,url=excluded.url,original_url=excluded.original_url,category=excluded.category,price=excluded.price,previous_price=excluded.previous_price,currency=excluded.currency,verified_at=excluded.verified_at,expires_at=excluded.expires_at,availability=excluded.availability,affiliate=excluded.affiliate,enabled=excluded.enabled;
  n=n+1;
 end loop;
 update public.affiliate_offers set enabled=false where catalog_origin=origin_id and source='sim_labs' and enabled and not(id=any(ids));
 insert into public.sim_catalog_state(origin,generated_at,manifest) values(origin_id,generated,p_manifest) on conflict(origin) do update set generated_at=excluded.generated_at,manifest=excluded.manifest,updated_at=now();
 return jsonb_build_object('status','applied','count',n,'origin',origin_id,'contains_user_finances',false);
end $$;
revoke all on function public.apply_sim_offer_catalog(jsonb) from public,anon;
grant execute on function public.apply_sim_offer_catalog(jsonb) to authenticated;
notify pgrst,'reload schema';
commit;
