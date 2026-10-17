# SIM Labs — Estado Atual — LiveOps v0.2.0

## IMPLEMENTADO
- Fundação independente da SIM Labs, separada do banco financeiro do NexGrana.
- Backend FastAPI, frontend React/TypeScript, migrations Alembic e RBAC da equipe canônica.
- Supervisor local que mantém API e worker em segundo plano e relança processos encerrados.
- Worker persistente com heartbeat e loop operacional a cada ~10 segundos.
- Feedback operacional com IDs `SIM-####`.
- Triagem determinística inicial com `severity`, `priority` e setor responsável.
- Geração automática de tasks `TASK-####` a partir de feedbacks novos.
- Monitor de repositório com checks periódicos, timeout, commit, saída e duração persistidos.
- Dashboard LiveOps com status do worker, feedbacks, tasks, monitores e histórico de checks.
- Endpoint de ingestão por token para integrações autorizadas.
- SQLite local configurado com WAL/foreign keys/busy timeout.
- Scripts Windows de start/stop em um clique e tarefa opcional de início no logon.
- Docker/Compose para evolução a serviço 24/7 em infraestrutura externa.

## TESTADO NESTA ENTREGA
- 13 testes backend passando.
- Migration `0001 -> 0002_liveops` aplicada em banco SQLite novo.
- Seed de produtos, monitor e worker state em banco novo.
- Feedback entra como `new`.
- Worker triage feedback e cria task vinculada.
- Segurança é classificada inicialmente como S0/P0 e roteada para security.
- Heartbeat torna o worker visível como online na API.
- RBAC impede UX de disparar monitor manualmente.

## NÃO VALIDADO NESTE AMBIENTE
- Build frontend final não foi executado aqui porque o ambiente de execução não conseguiu resolver o registry npm (`EAI_AGAIN`). O código e o script permanecem configurados para executar `npm install`/`npm run build` no Windows do usuário, onde npm já foi instalado e usado com sucesso.
- Scripts do Agendador do Windows não podem ser exercitados no container Linux desta sessão.
- Docker/Compose não foi publicado em provedor externo.

## PENDENTE
- Supabase Auth/UIDs reais/MFA.
- PostgreSQL remoto e backup/restore exercitado.
- Collector ZIP completo, evidências privadas/quarentena e deduplicação final.
- GitHub webhook/CI conectado ao Control Center.
- Gate de release e Security Gate completos.
- Agentes de IA assistivos e governados.
- Owners humanos explícitos para Engineering, Cybersecurity e Red Team.

## FRONTEIRA DE AUTONOMIA
LiveOps pode observar, testar, classificar, registrar e criar trabalho. Não altera código, não faz merge, não faz deploy e não aprova release sozinho.
