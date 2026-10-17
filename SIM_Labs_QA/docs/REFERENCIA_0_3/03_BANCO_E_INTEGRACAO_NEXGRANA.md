# Banco e integração — o que muda e o que você precisa fazer

## Para testar hoje

**Não altere o banco do NexGrana/Supabase.** O iniciador prepara um banco operacional SQLite em `backend/sim_labs.db`, aplica Alembic até `0003_integrated` e cadastra equipe/projetos.

Se houver banco operacional anterior na mesma pasta, o bootstrap faz uma cópia consistente antes da migração. A migração 0003 cria tabelas novas; não remove tabelas ou registros das fases 0001/0002.

O backup completo de banco + evidências + Collector + configuração é feito por `BACKUP_SIM_LABS.bat`. A cópia automática antes da migração é só do banco; não substitui esse backup completo.

## Tabelas adicionadas

| Tabela | Relação / finalidade | Unicidade |
|---|---|---|
| project_configs | Descrição, plataformas, referência de repositório e regras declarativas | Um registro por produto |
| releases | Candidata, notas, estado e referência estável | Produto + versão |
| artifacts | Arquivo privado, hash, plataforma, inspeção e manifesto | Release + hash |
| integration_receipts | ID do Collector, origem, contexto e registro na API | Produto + origem + ID externo |
| evidence | Anexos privados com hash, projeto e vínculo | Feedback + hash quando ligado a feedback |
| test_runs | Resultado estrutural ou homologação manual | Execuções preservadas, sem sobrescrever histórico |
| decisions | Problema, impacto, recomendação, escolha e motivo | Decisão de revisão por release |
| messages | Canal do CEO, origem humana/automação/IA e missão vinculada | Histórico por projeto |
| regression_cases | Passos, esperado e evidência da missão encerrada | Um cenário por missão |
| daily_reports | Resumo de registros acumulados no dia | Produto + dia local de SP |
| jobs | Fila de inspeção, tentativa, lease e resultado | Um job por artefato |
| leases | Liderança do worker | Chave da rotina |

Tabelas anteriores preservadas: products, sectors, team_members, user_identities, memberships, audit_events, sequence_counters, feedbacks, tasks, repo_monitors, automation_runs e worker_states.

Os monitores antigos de comandos ficam catalogados e desabilitados. O caminho com `shell=True` foi retirado do runner da central. O futuro runner isolado precisa de implementação própria.

## Migração técnica

Arquivo: `backend/alembic/versions/0003_integrated.py`.

Rota normal: iniciador → backup → `alembic upgrade head` → `app.seed` → supervisor → API + worker. `create_all` não substitui Alembic na operação normal.

Foi testado upgrade real de uma base 0002 com produto e feedback antigos: os registros permaneceram e as tabelas novas foram criadas. PostgreSQL/Supabase remoto não foi conectado nesta entrega.

O SQL de referência para PostgreSQL está em `docs/SQL_REFERENCIA_POSTGRES_0003.sql`; ele documenta somente as tabelas novas. Não execute junto com Alembic nem cole no banco financeiro. Ele não é um plano completo de produção, não cria login/roles/RLS e não altera `alembic_version`.

Para restauração: pare a central, preserve a pasta atual e extraia seu backup sobre uma cópia da mesma versão do código. Credenciais e arquivos de evidência precisam corresponder ao banco. Não rode downgrade apagando tabelas novas para fazer rollback de uso cotidiano.

## Contratos de entrada implementados

### Collector interno

- `POST /api/v1/collector/ingest-package`: ZIP multipart, cabeçalho de integração limitado ao NexGrana.
- `POST /api/v1/collector/package`: importação pelo painel com sessão do CEO.
- `POST /api/v1/collector/ingest`: JSON `sim-labs.feedback-ingest/1.0`, preserva IDs; sem anexos binários.

O botão do Collector envia um ZIP com manifesto e anexos em segundo plano. A central só aceita seu token para o projeto configurado; não conceder login administrativo ao Collector. Reenvio reconhecido pela origem/ID e anexos por hash.

### Releases

- `POST /api/v1/releases`: cria candidata.
- `POST /api/v1/releases/{id}/artifacts`: registra arquivo e job.
- `GET /api/v1/releases`: retorna estado, artefatos e gates.
- `POST /api/v1/releases/{id}/manual-checks`: resultado real com evidência.
- `POST /api/v1/releases/{id}/request-decision`: encaminha revisão.
- `PATCH /api/v1/decisions/{id}`: decisão de Mafra; aprovação bloqueada sem gates.

### Comunicação e memória

- `POST/GET /api/v1/messages`: canal do projeto.
- `PATCH /api/v1/missions/{id}`: transição de tarefa; encerramento exige cenário e evidência.
- `POST/GET /api/v1/evidence`: arquivos privados.
- `GET /api/v1/daily`, `/regressions`, `/export`, `/company`.
- `GET/PATCH /api/v1/projects/{slug}/config`: configuração declarativa.

Os arquivos não ficam numa pasta pública. Download exige autorização e relação com o projeto. Exportação exclui caminhos locais internos. Não usar endpoints novos como API pública de usuários.

## O que ainda precisa mudar no NexGrana

Não foi modificado o código do NexGrana neste pacote. O ponto de integração futuro é `analytics.py` e um fluxo de feedback de usuário separado do Collector.

1. Criar um **gateway de intake** para clientes do NexGrana, distinto da API administrativa.
2. Autenticar sessão do usuário e derivar projeto/origem no servidor. Não aceitar o aplicativo escolher outro projeto nem embutir o token do Collector no APK.
3. Aplicar allowlist de eventos técnicos: código de erro, versão, plataforma, tela normalizada, classe de duração, código de resultado e ID idempotente.
4. Rejeitar saldos, renda, transações, mensagens do Nex, nomes de familiares, tokens, e-mails e payloads de respostas financeiras na telemetria.
5. Manter consentimento e revogação já previstos no app. Em falha/offline, fila limitada, prazo de retenção e backoff; não travar a interface.
6. Feedback enviado pelo usuário usa texto/anexo voluntário com indicação do que será enviado. Não retransmitir automaticamente conversas privadas.
7. No servidor, limitar tamanho/taxa, sanitizar logs e deduplicar por projeto/origem/evento.
8. Criar tarefa apenas para sinal técnico consistente ou feedback real; observação estatística não prova bug.
9. Testar isolamento entre usuários/projetos, revogação, offline, retry e ausência de dados financeiros.
10. Só depois homologar Windows/Android e publicar a candidata por decisão de Mafra.

## Infraestrutura futura

Recomendo manter o banco operacional separado. Pode ser PostgreSQL em infraestrutura própria ou um projeto separado no Supabase, após autenticação e autorização completas. Não reaproveitar as tabelas financeiras como banco do SIM Labs.

Antes de exposição remota: autenticação de produção no frontend; verificação completa do emissor/audiência/expiração conforme IdP; associação de papel/projeto/ambiente; arquivos privados; credenciais por integração; rate limits; upload em streaming; execução em runners isolados; backups e restauração testados.

A autenticação Supabase herdada é uma base, não uma homologação de produção. Não habilitar `ALLOW_DEV_ACTORS` em servidor.
