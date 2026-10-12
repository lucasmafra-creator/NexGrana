-- NexGrana 0.19.0 — migração aditiva. NÃO executar automaticamente no app.
-- Aplicar somente após backup/teste em projeto de homologação.
begin;

-- Trilha Nex passa de 6 para 10 etapas sem inventar progresso novo.
alter table public.nex_journeys drop constraint if exists nex_journeys_progress_check;
alter table public.nex_journeys add constraint nex_journeys_progress_check check(progress between 0 and 10);

-- A tabela de ofertas continua somente leitura para clientes autenticados.
-- Campos opcionais permitem validade/plataforma sem atrelar ranking a comissão.
alter table public.affiliate_offers add column if not exists platform text;
alter table public.affiliate_offers add column if not exists product_key text;
alter table public.affiliate_offers add column if not exists currency text not null default 'BRL';
alter table public.affiliate_offers add column if not exists price numeric(14,2);
alter table public.affiliate_offers add column if not exists campaign text;
alter table public.affiliate_offers add column if not exists sponsored boolean not null default false;

-- Nenhuma tabela de analytics remoto é criada nesta versão: o adaptador fica
-- desabilitado até decisão explícita sobre finalidade/base/consentimento.

commit;
