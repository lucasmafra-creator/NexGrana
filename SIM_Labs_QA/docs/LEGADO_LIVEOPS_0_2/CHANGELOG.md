# Changelog

## 0.2.0-liveops — 2026-09-26
- Supervisor de processos para execução local em segundo plano.
- Worker com heartbeat e loop contínuo.
- Feedback `SIM-####`, triagem inicial e tasks `TASK-####`.
- RepoMonitor e AutomationRun com checks periódicos e histórico.
- Dashboard LiveOps.
- Frontend compilado servido pelo FastAPI na operação normal.
- Endpoint de ingestão de feedback por token.
- SQLite WAL para concorrência local.
- Scripts Windows start/stop/autostart.
- Docker/Compose e workflow CI agendado.
- Migration `0002_liveops` e ampliação dos testes automatizados.

## 0.1.0-phase-a — 2026-09-26
- Fundação independente SIM Labs.
- Produto `nexgrana` #001.
- Equipe canônica e RBAC inicial.
- Auditoria e isolamento básico por produto.
- Dashboard React inicial.
- Migration e testes da fundação.
