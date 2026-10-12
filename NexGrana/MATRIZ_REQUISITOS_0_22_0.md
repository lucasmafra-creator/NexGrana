# Matriz de requisitos — NexGrana 0.22.0

| Requisito | Implementação | Evidência | Estado/limite |
| --- | --- | --- | --- |
| contrato financeiro | `finance_engine.py` | testes de dia 20, competência, rateio e duplicação | testado localmente |
| individual/família | `product_copy.py`, Home e tutorial | `test_product_experience.py`, UI | testado localmente |
| Nex amplo | cliente + `gateway/app.py` | `test_nex_engine.py`, `test_gateway_server.py` | integração real bloqueada |
| conversa e cinco fixados | `screens/nex.py`, tabelas 0.20 | UI e SQL | renomear/excluir implementado; aparelho pendente |
| tutorial vivo | `settings.py` | construção UI em múltiplas larguras | inspeção em aparelho pendente |
| trilha específica | `journeys.py`, `extra_income.py` | testes de especialização/XP | testado localmente |
| painel Achados | `admin/achados_admin.py` | 11 testes de painel/formulário + SQL CRUD | Supabase real pendente |
| seis links | `offers.py` e migration 0.20 | teste de contagem/URLs | implementado |
| offline/performance | `cloud.py`, `sync.py`, host persistente | testes de cache/fila/401 | p50/p95 pendentes |
| segurança | RLS, allowlists, JWT, scan | SQL + unitários + scan | jurídico/hosting pendentes |
| Windows/Android/iOS | scripts de build | comandos reproduzíveis | instaladores não gerados; iOS bloqueado |
