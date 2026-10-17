# Gateway do Nex — ativação segura

## Estado

Implementado e coberto por testes locais simulados. Não foi publicado nem validado com um provedor real. O app continua funcional no modo local.

## Arquitetura

`Cliente Flet → gateway HTTPS próprio → provedor de modelo`. A chave do provedor fica apenas no servidor. O cliente envia no máximo oito mensagens reduzidas e somente campos financeiros explicitamente permitidos; conversa externa exige consentimento.

## Configuração do servidor

Crie um ambiente isolado dentro de `gateway` e configure no provedor de hospedagem, nunca no ZIP nem no chat:

- `SUPABASE_URL`: URL do projeto autorizado;
- `SUPABASE_JWT_ISSUER` e `SUPABASE_JWT_AUDIENCE`, se diferentes do padrão;
- `OPENAI_API_KEY`: segredo do provedor, somente no servidor;
- `NEX_PROVIDER_MODEL`: modelo aprovado após avaliação de custo/qualidade;
- `NEX_LOG_SALT`: valor longo e aleatório para pseudonimizar métricas;
- `NEX_RATE_LIMIT` e `NEX_RATE_WINDOW_SECONDS`: orçamento por usuário.

Comandos locais do servidor, destinados apenas ao desenvolvimento:

```bat
py -m venv .venv-gateway
.venv-gateway\Scripts\python -m pip install -r gateway\requirements.txt
.venv-gateway\Scripts\python -m uvicorn gateway.app:app --host 127.0.0.1 --port 8080
```

O aplicativo rejeita localhost: a integração real exige endpoint HTTPS público. Depois da publicação autorizada, configure `src/build_config.py` antes do APK/iOS ou `NEXGRANA_NEX_GATEWAY_URL` no Windows e refaça o teste.

## Critérios antes de ativar

Validar JWT real, 401, 429, timeout, 5xx, custo máximo, retenção do provedor, política de privacidade, qualidade em português e teste de isolamento. O gateway não executa alterações financeiras e não possui `service_role`.
