# Matriz requisito → estado → evidência

| Área | Estado 0.18.1 | Evidência / observação |
|---|---|---|
| Saldo contínuo | Implementado | `services/finance_engine.py`, testes de rollover |
| Despesa futura x paga | Implementado | `effective_expense`, `expense_status`, testes |
| Data real da renda | Implementado | snapshot exclui renda sem recebimento/futura |
| Rateio sem duplicação | Implementado | centavos + testes de shares |
| Metas/cenários | Implementado | `goal_scenarios`, testes Nex |
| Concorrência em meta | Implementado no SQL/cliente | `MIGRATION_0_18_1.sql`; validar em staging |
| Despesa + rateio atômicos | Implementado | `SQL_ATOMIC_0_18.sql` + `Cloud.add_expense` RPC |
| Home app-first | Implementado em código | validar visualmente em dispositivos |
| Análises orientadas a ação | Implementado em código | `screens/analysis.py`; validar UX |
| Perfis de família | Implementado | perfil ativo + escopo familiar |
| Nex pipeline estruturado | Parcial forte | ações financeiras no `nex_engine`; fallback legado ainda existe |
| LLM conversacional externo | Não conectado | arquitetura prevista; exige backend/segredo server-side |
| Nex HD transparente | Implementado | `assets/nex/nex_hd.png` |
| Nex estados/3D/Rive completos | Pendente de arte/runtime | master HD + micro movimentos, sem fingir rig 3D |
| Chat Android | Código unificado | exige smoke test em aparelho |
| Trilha Nex | Parcial forte | progresso/etapas/lembrete in-app; push do SO ainda não |
| Lembretes push | Não implementado | exige integração nativa/backend/notifications |
| Sync offline | Fundação implementada | fila cifrada; escrita offline ainda não habilitada |
| Mercado CRUD | Implementado | telas/serviço/RPCs; validar multiusuário real |
| Câmera/galeria | Implementado em código | validar lifecycle/permissão Android |
| OCR de nota | Não implementado | conferência manual continua funcional |
| Afiliados | Base segura implementada | catálogo/whitelist/disclosure; sem personalização financeira padrão |
| Secure storage | Implementado em código | validar DPAPI/Android secure storage em aparelho |
| LGPD UI/consentimentos | Parcial forte | política/consentimentos/export; exclusão completa ainda exige backend |
| Importação legada destrutiva | Bloqueada | proteção contra perda até existir rollback atômico |
| Windows/APK | Script pronto | build real deve ser feito no PC do usuário |
