# Deploy 24/7

## Realidade operacional

No Windows local, LiveOps permanece ativo enquanto o computador e a sessão estiverem disponíveis. Para continuar operando com o notebook desligado, é necessário executar API, worker e banco em infraestrutura externa.

## Arquitetura alvo

- PostgreSQL persistente.
- Uma instância `api`.
- Uma instância `worker`.
- HTTPS/reverse proxy do provedor.
- Supabase Auth ou outro IdP configurado para equipe.
- backups e health checks.

O `docker-compose.yml` desta versão sobe DB, migration/seed, API e worker. Antes de qualquer publicação externa, troque senhas padrão, defina secrets fora do repositório, configure `APP_ENV=prod`, Supabase JWT e origem HTTPS permitida.

## Não publicar do jeito DEV

`X-Dev-Actor` existe apenas quando `APP_ENV` é `dev/test/local`. Um deploy público deve usar autenticação real e banco separado do NexGrana.
