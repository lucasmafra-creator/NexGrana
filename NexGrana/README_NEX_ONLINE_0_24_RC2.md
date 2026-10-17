# Nex online: configuração operacional da candidata

O modo online **ainda não está ativo nos builds**: `src/build_config.py` deixa
`NEX_GATEWAY_URL` vazio. Sem serviço HTTPS e chave do provedor no servidor,
nenhuma mudança no APK cria uma conversa online real.

## Preparar no servidor

1. Hospede `gateway/app.py` como serviço ASGI HTTPS. O Dockerfile incluído usa
   `docker build -f gateway/Dockerfile .` e publica internamente na porta 8000.
   Configure o proxy HTTPS com rota `/v1/chat` e `/health`; não redirecione tokens.
2. Preencha no gerenciador de segredos do servidor: `SUPABASE_URL`,
   `SUPABASE_ANON_KEY`, `OPENAI_API_KEY`, `NEX_LOG_SALT` longo e exclusivo,
   `NEX_PROVIDER_MODEL` aprovado. Verifique a chave JWT assimétrica JWKS no
   Supabase; o gateway atual aceita RS256/ES256, não segredo JWT simétrico.
3. Faça `GET /health` publicamente e verifique status 200. Esse endpoint
   confirma só o processo, **não** o provedor nem a ligação com o Supabase.
4. Confirme migrações e permissão `external_ai` para uma conta QA de teste.
   Teste uma mensagem com JWT válido e consentimento, revogue e confirme 403,
   teste outra conta/família e confirme que nada é devolvido de outro espaço.
5. Defina `NEX_GATEWAY_URL = "https://DOMINIO_PUBLICO/v1/chat"` em
   `src/build_config.py` antes de construir o APK. No Windows em execução,
   `NEXGRANA_NEX_GATEWAY_URL` também pode fornecer a URL. Execute testes e
   rebuild de Windows/Android após essa configuração.

Nenhuma chave de servidor deve ir para `src/build_config.py`, ZIP, APK ou EXE.
Não cole JWT, senhas nem segredo em prints ou logs. A URL pública isolada
não confirma que o modo online funciona: valide resposta efetiva nos dois
dispositivos e registre custo, falhas e revogação.

## Limitações atuais

- O gateway entrega conversa geral com contexto curto e recusa afirmar números
  enviados pelo cliente como extrato. Ferramentas financeiras server-side ainda
  não existem; os cálculos financeiros permanecem locais e determinísticos.
- O limite atual é em memória do processo. Produção com várias réplicas requer
  limitador partilhado e monitoramento de custos antes do lançamento público.
- `request_id` identifica logs, mas não há recibo durável de idempotência do
  provedor. O cliente envia o POST uma só vez para evitar cobranças duplicadas.
