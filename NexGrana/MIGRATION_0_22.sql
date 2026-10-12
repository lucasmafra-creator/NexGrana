-- NexGrana 0.22.0 — painel privado de Achados, acessibilidade e defesa em profundidade.
-- Migração aditiva e idempotente. Aplicar depois da MIGRATION_0_21.sql.
begin;

alter table public.affiliate_offers
 add column if not exists image_alt text not null default '';

create or replace function public.guard_affiliate_offer()
returns trigger language plpgsql security invoker set search_path='' as $$
begin
 if not public.is_app_admin() then raise exception 'Admin permission required'; end if;
 if char_length(trim(new.title)) < 4 or char_length(new.title) > 180 then
  raise exception 'Invalid title';
 end if;
 if new.url !~ '^https://(meli[.]la|([a-z0-9-]+[.])?mercadolivre[.]com[.]br)/' then
  raise exception 'Partner URL is not allowed';
 end if;
 if new.original_url is not null and new.original_url !~ '^https://(meli[.]la|([a-z0-9-]+[.])?mercadolivre[.]com[.]br)/' then
  raise exception 'Original partner URL is not allowed';
 end if;
 if new.image_url is not null and (
  new.image_url !~ '^https://http2[.]mlstatic[.]com/'
  or char_length(trim(new.image_alt)) < 4
 ) then raise exception 'Image URL or description is not allowed'; end if;
 if new.price is not null and new.price < 0 then raise exception 'Invalid price'; end if;
 if new.sort_order < 0 or new.sort_order > 999999 then raise exception 'Invalid sort order'; end if;
 if cardinality(new.search_tags) > 20 then raise exception 'Too many search tags'; end if;
 if new.enabled and new.expires_at <= now() then raise exception 'Published offer is expired'; end if;
 new.updated_at=now();
 new.updated_by=auth.uid();
 if tg_op='INSERT' then new.created_by=auth.uid(); end if;
 return new;
end $$;

drop trigger if exists guard_affiliate_offer on public.affiliate_offers;
create trigger guard_affiliate_offer before insert or update on public.affiliate_offers
 for each row execute function public.guard_affiliate_offer();

create index if not exists affiliate_offers_admin_filter_idx
 on public.affiliate_offers(category,enabled,sort_order,updated_at desc);

notify pgrst,'reload schema';
commit;

select
 to_regclass('public.affiliate_offers') as affiliate_offers,
 exists(
  select 1 from information_schema.columns
  where table_schema='public' and table_name='affiliate_offers' and column_name='image_alt'
 ) as image_alt_ready,
 to_regclass('public.affiliate_offer_audit') as offer_audit;
