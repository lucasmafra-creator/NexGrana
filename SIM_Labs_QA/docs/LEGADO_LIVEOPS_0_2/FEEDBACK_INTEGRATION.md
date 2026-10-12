# Integração de feedback — LiveOps v0.2

Endpoint:

`POST /api/v1/ingest/feedback`

Header obrigatório:

`X-SIM-Ingest-Token: <FEEDBACK_INGEST_TOKEN>`

Exemplo de payload:

```json
{
  "product_slug": "nexgrana",
  "category": "bug",
  "title": "Falha ao salvar despesa",
  "description": "Passos e contexto observados",
  "expected": "Despesa salva",
  "observed": "Tela permaneceu carregando"
}
```

O token é criado localmente no `.env` pela primeira execução do script Windows. Não exponha esse valor no frontend, logs, Git ou screenshots públicos.

Após a ingestão, o worker faz uma triagem inicial e cria uma task. O endpoint não executa anexos, código ou instruções contidas no feedback.
