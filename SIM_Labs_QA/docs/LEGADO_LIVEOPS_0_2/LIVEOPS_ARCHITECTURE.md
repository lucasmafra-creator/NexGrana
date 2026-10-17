# SIM Labs LiveOps — arquitetura v0.2

## Processos vivos

`app.supervisor` mantém dois filhos:

1. `uvicorn app.main:app` — API + frontend compilado.
2. `python -m app.worker` — automação contínua.

O supervisor verifica os processos a cada poucos segundos e os relança quando terminam inesperadamente. PIDs e logs são gravados em `.runtime/`.

## Loop do worker

A cada ~10 segundos:
- atualiza heartbeat;
- busca feedbacks `new`;
- aplica triagem determinística inicial;
- cria uma task quando necessário;
- busca monitores vencidos;
- executa checks em subprocesso com timeout;
- grava resultado, commit, duração e saída;
- agenda o próximo check.

A triagem é sugestão operacional inicial, não aprovação final. Achados críticos de segurança são roteados para `security`, mas decisão de release continua humana.

## Fluxo implementado

`Feedback -> SIM-#### -> triagem -> TASK-#### -> setor responsável`

E em paralelo:

`RepoMonitor -> code-check -> AutomationRun -> histórico/alerta no dashboard`

## Persistência

Desenvolvimento local usa SQLite com `WAL`, `foreign_keys=ON` e `busy_timeout`. Produção deve migrar para PostgreSQL/Supabase dedicado à SIM Labs.

## Resiliência atual

- supervisor reinicia API/worker;
- worker mantém heartbeat;
- checks têm timeout de 15 minutos;
- outputs são limitados antes de persistir;
- frontend não depende mais do Vite para uso normal;
- browser pode fechar sem encerrar o worker.

## Próximos gates

1. Postgres/Supabase Auth real.
2. Collector/feedback contract completo com anexos/quarentena.
3. GitHub read-only + CI/webhook assinado.
4. release registry/security gate.
5. agentes assistivos limitados, começando read-only/rascunho.
