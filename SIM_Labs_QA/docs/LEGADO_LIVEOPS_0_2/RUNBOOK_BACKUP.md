# Backup / Restore — Fase A

## SQLite local
Backup de desenvolvimento é cópia consistente do arquivo com aplicação parada. Não representa estratégia de produção.

## PostgreSQL/Supabase
Antes de produção, validar backup nativo da plataforma e um restore drill. Para Postgres autogerenciado, usar `pg_dump`/`pg_restore` com credencial exclusiva e armazenamento protegido. RPO/RTO ainda não foram aprovados; não há promessa de recuperação até o primeiro exercício documentado.
