# Supabase — preparação para login real

Esta entrega **não cria** projeto Supabase nem contas reais. Para ativar produção:

1. Criar um projeto Supabase exclusivo da SIM Labs.
2. Copiar a connection string Postgres para `DATABASE_URL` do backend.
3. Executar `alembic upgrade head`.
4. Executar `python -m app.seed` para pessoas/setores/produto canônicos.
5. Criar/confirmar usuários reais no Supabase Auth administrativamente.
6. Vincular cada `auth.users.id` ao membro canônico com `scripts/link_identity.py`.
7. Configurar `SUPABASE_JWT_SECRET` (ou substituir o verificador pelo método JWKS apropriado ao projeto configurado antes de produção).
8. Definir `APP_ENV=prod`, `AUTO_INIT_DB=0` e CORS somente para o domínio real.
9. Testar usuário sem membership, papel sem permissão e produto fora de escopo antes de publicar.

Nenhum nome da tabela canônica equivale automaticamente a login/e-mail.
