# ADR-001 — Separar Control Plane SIM Labs do NexGrana

**Status:** Aceito para Fase A.

SIM Labs mantém metadados operacionais, equipe, QA, tarefas, releases e auditoria em infraestrutura própria. O NexGrana continua dono dos dados financeiros/clientes. Integrações futuras serão mínimas, autenticadas e versionadas; não haverá service role compartilhada nem console SQL geral do produto financeiro.
