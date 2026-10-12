# Arquitetura — Fase A

```text
[ React Control Center ]
          |
          | HTTPS / JWT Supabase (produção)
          v
[ FastAPI Control Plane ] ---- [ Audit Log ]
          |
          +---- RBAC / product scope
          |
          v
[ PostgreSQL/Supabase SIM Labs ]

NexGrana permanece fora desse banco.
Integrações futuras usam APIs/eventos minimizados e versionados.
```

O frontend nunca recebe segredo administrativo. O backend aplica autorização antes da consulta. `X-Dev-Actor` existe apenas em `dev/test/local` para desenvolvimento e não representa identidade de produção.
