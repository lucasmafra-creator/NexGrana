# Validação — NexGrana 0.22.0 QA RC1

## Automatizada

- 113 testes Python: finanças, autenticação simulada, offline, UI, Nex, gateway, painel, Achados, trilhas, investimentos e segurança;
- cadeia SQL completa até `MIGRATION_0_22.sql` em PostgreSQL local PGlite;
- compileall de `src`, `admin` e módulos do gateway;
- varredura estática de segredos e artefatos locais;
- ZIP testado por CRC, raiz única e ausência de `.env`, `.venv`, build, dist, logs e caches.

## Manual obrigatório antes de aprovar instaladores

1. Aplicar migration 0.22 em Supabase de homologação com backup.
2. Autorizar por UUID a conta administrativa em `app_admins`.
3. Abrir o painel, criar rascunho, visualizar, publicar, filtrar, desativar e excluir; conferir auditoria.
4. Testar individual e família, tutorial, saldo/futuro, Mercado com teclado e retorno do Nex em 360/390/412 px.
5. Testar “suave?”, “quero estudar programação”, mês, contas e troca de perfil durante resposta.
6. Instalar Windows/APK e repetir offline, rede mediana e reconexão.
7. Se o gateway for aprovado/publicado, validar consentimento, JWT, 401, 429, timeout, indisponibilidade e custo.

Não validado nesta entrega: login real, dispositivo físico, build instalada, provedor real, pesquisa web e iOS.
