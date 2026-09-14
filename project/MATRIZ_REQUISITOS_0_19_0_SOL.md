# Matriz — NexGrana 0.19.0 SOL

| ID | Requisito | Estado | Evidência nesta candidata | Pendência |
|---|---|---|---|---|
| FIN-01 | saldo contínuo / pago ≠ agendado | Implementado/testado | `services/finance_engine.py`, testes financeiros | validar com dados de staging |
| FIN-02 | rateio sem duplicação | Implementado/testado | `split_amount`, `snapshot`, testes | concorrência real |
| NEX-01 | entrada única de conversa | Implementado | `_queue_nex_message`/`_dispatch_nex_message` | Android real |
| NEX-02 | erro explícito, sem inventar valor | Implementado/testado no engine | `services/nex_engine.py` | UX real |
| NEX-03 | teclado Android utilizável | Implementado no layout | composer/foco/nav | aparelho real P0 |
| PERF-01 | evitar página vazia em navegação | Implementado estruturalmente | host persistente em `main.py` | medir p95 no notebook |
| ASSET-01 | Nex sem GIF degradado ativo | Implementado/verificado | manifesto + variantes PNG | pack 3D/Rive final pendente |
| UI-01 | design tokens | Implementado parcial | `ui/design.py` | consolidar telas restantes |
| UI-02 | dialogs críticos responsivos | Implementado parcial | `dialog_dimensions` | inspeção visual 360/390/412 |
| PLAN-01 | simulação numérica | Implementado/testado | `goal_scenarios`, NexEngine | interação real |
| EXTRA-01 | diagnóstico 8 dimensões | Implementado | `screens/nex.py` | persistência do diagnóstico entre sessões |
| JOURNEY-01 | Trilha 10 etapas | Implementado/testado | `extra_income.py`, migration, teste | push nativo não implementado |
| MON-01 | ranking independente de comissão | Implementado/testado | `services/offers.py` | provedores reais |
| MON-02 | app sem Premium | Implementado como decisão | docs/código sem paywall | estratégia comercial real |
| PRIV-01 | analytics sem dado financeiro | Implementado/testado | `services/analytics.py` | envio remoto propositalmente desligado |
| PRIV-02 | Vault/cache seguro | Herdado da 0.18.1 | `services/privacy.py`, testes | dispositivo real |
| MIG-01 | migration 0.19 aditiva | Implementada | `MIGRATION_0_19.sql` | staging/rollback ensaiado |
| MARKET-01 | câmera/conferência | Herdado e preservado | `screens/market.py` | Android real/OCR não pronto |
| OFFLINE-01 | fundação de fila | Implementado/testado | `services/sync.py` | escrita offline continua desativada |
