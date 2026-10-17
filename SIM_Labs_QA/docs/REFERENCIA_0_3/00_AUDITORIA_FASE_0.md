# SIM Labs — auditoria Fase 0

Data: 02/10/2026. Escopo: fontes locais dos três pacotes abaixo e prompt mestre fornecido por Mafra. Nenhum código de produto foi modificado, nenhuma migração aplicada e nenhuma publicação realizada.

## Diagnóstico executivo

O SIM Labs já possui uma fundação reutilizável. A central LiveOps 0.2 tem API, persistência, equipe canônica, autorização, triagem e worker recorrente. O Collector 0.4.1 incluído no RC6 tem intake de artefatos, inspeção estrutural, importação de feedback e relatórios locais. Essas duas bases ainda não estão conectadas. O NexGrana possui serviços e testes aproveitáveis, mas sua instrumentação analisada não envia eventos para a central.

Não recomendo reconstrução geral. Recomendo manter a central como plano de controle, o Collector como entrada humana e runners separados como executores. A plataforma ainda não cumpre o ciclo completo de descoberta, correção, reteste, decisão e release; não há evidência nesta auditoria de operação remota 24/7.

## 1. Materiais e integridade

| Pacote | Bytes | SHA-256 |
|---|---:|---|
| SIM_Labs_Control_Center_LiveOps_v0.2.0.zip | 5.554.235 | a327336353ba43815dd9255496132e00d3f21809cdca987a6dd0a41d608388c1 |
| NexGrana_Update_Collector_v0_3_1_SIM_Labs_FIX(1).zip | 39.223 | 26aad0f92eb65be37fb9eca2fd3f4d4eabd4158c60cf76b613e42c6b2aae13ad |
| NexGrana_Windows_Android_RC6_SIM_Labs_Fonte_2026-10-01 (1).zip | 22.704.043 | 08f11a4783b7e90605c75877b1b25d80b050864bc85536e96f548681b16649cd |

Fontes extraídas para análise. Os hashes identificam os pacotes usados; não representam assinatura do fornecedor. A auditoria cobre estrutura, componentes centrais, contratos, configurações e testes executáveis disponíveis. Não é homologação integral de cada tela, asset, SQL ou comportamento em produção.

## 2. Arquitetura atual

| Componente | Implementação observada | Persistência e execução |
|---|---|---|
| Central LiveOps | React/TypeScript/Vite; FastAPI; SQLAlchemy; Alembic | SQLite local ou PostgreSQL; API e worker separados; Docker e scripts Windows |
| Collector 0.3.1 | Tkinter, anexos, rascunhos, exportação estruturada | JSON local; exporta ZIP e SIM_LABS_INGEST.json |
| Collector 0.4.1 do RC6 | Collector anterior mais sim_labs_core.py e sim_labs_ui.py | JSON local, cópias de builds e relatórios; sem transporte remoto |
| NexGrana | Flet 0.86.5, serviços Python, cliente Supabase, gateway próprio | Supabase e cache/sessão protegidos por Vault; fila de sincronização |

Na central, backend/app contém models, auth, permissions, routers, liveops, worker, supervisor e seed. Há duas revisões Alembic. frontend/src contém painel, cliente da API e estilos. No RC6, NexGrana e SIM_Labs_Collector são projetos distintos.

As entidades existentes são Product, Sector, TeamMember, UserIdentity, Membership, AuditEvent, SequenceCounter, Feedback, Task, RepoMonitor, AutomationRun e WorkerState. Product ainda é mínimo: ID, slug, nome, status e data. Falta o cadastro completo de plataforma, versão, repositório e regras pedido no prompt.

## 3. Funcionalidades e estado real

| Módulo solicitado | Estado encontrado |
|---|---|
| Projects | Parcial: cadastro/listagem de produtos e escopo de acesso |
| Departments | Setores cadastrados; equipe canônica preservada |
| Collector Inbox | Feedback textual na API; importador de ZIP separado no Collector |
| Tasks | Criação automática após triagem; sem ciclo completo de tratativa/reteste |
| Test Runs | AutomationRun para comandos; resultados locais do Collector separados |
| History | AuditEvent existe; cobertura não engloba todas as ações |
| Releases | Intake local de builds; sem entidade central de release e aprovação |
| Evidence | Referências e relatórios locais; sem central privada de anexos |
| Release Audit | Inspeção estrutural existe; comparação estável versus candidata ausente |
| CEO Desk | Sem fluxo persistido de opções, recomendação e decisão |
| Daily Report | Sem gerador periódico consolidado identificado |
| Regression Library | Testes existentes; sem catálogo ligado a bugs e releases |
| Agentes | Worker por regras e comandos; sem agentes especializados operacionais |

A equipe cadastrada é representação de papéis. Não equivale a pessoas ou agentes executando análises inteligentes automaticamente.

O worker triageia até 100 feedbacks novos por ciclo, usa regras de palavras-chave, cria tarefas, acompanha heartbeat e executa até dois monitores em paralelo. O self-check inclui compilação, pytest e, quando npm está presente, build do frontend. O monitor NexGrana depende de NEXGRANA_REPO_PATH e configuração local. Não executa automaticamente jornadas em APK/EXE.

## 4. Collector e incompatibilidades

Usar o 0.4.1 do RC6 como base de evolução; manter o 0.3.1 para comparação/compatibilidade, sem substituí-lo sobre a versão mais nova.

O 0.4.1 calcula hash, verifica ZIP/CRC, reconhece formatos Android/Windows, usa ferramentas locais quando disponíveis, importa feedbacks mantendo IDs, mescla partes e oferece checklist manual. Executar suíte de fonte exige ação explícita na interface. O runner retira variáveis comuns de segredo e impõe timeout, mas não é uma sandbox.

O contrato exportado tem schema sim-labs.feedback-ingest/1.0, release, records, feedback_id, prioridade, plataforma, tela, status e evidências. A API /api/v1/ingest/feedback aceita somente um FeedbackCreate textual. Não aceita o pacote completo, não preserva feedback_id externo e não possui chave de idempotência. Categorias humanas também precisam de conversão para o enum da API. Enviar o ZIP diretamente ao endpoint atual não resolve a integração.

A documentação do Collector afirma que não há backend entre os arquivos recebidos daquela entrega. Isso descreve o pacote RC6, mas não o conjunto atual: a central LiveOps foi localizada separadamente. Consolidar documentos para evitar duas versões contraditórias do estado do projeto.

## 5. NexGrana e pontos de integração

O pyproject identifica 0.24.0, embora haja migrations até 0.25. Isso não prova erro de runtime, mas exige separar versão do produto, versão do esquema e rótulo RC6.

Serviços reaproveitáveis: finance_engine, monthly_ledger, transactions, sync, privacy, nex_conversation, nex_engine, nex_skins, tutorial e analytics. Gateway e banco financeiro devem continuar separados do banco operacional SIM Labs.

analytics.py contém allowlist de eventos, proibição de campos financeiros/chat e buffer em memória; não há envio remoto nessa implementação. É um ponto de partida para telemetria mínima, não uma integração pronta. O SIM Labs deve receber códigos de erro, versão, plataforma e contexto técnico permitido, sem copiar saldos, conversas ou dados familiares.

Há schema Supabase e migrations de contas, regras financeiras e fechamentos mensais. Políticas e funções SQL foram identificadas estruturalmente; não foram aplicadas nem validadas em servidor. A chave de cliente indicada em cloud.py é publicável; sua presença por si só não caracteriza vazamento de segredo. A proteção efetiva depende das políticas e permissões do backend.

O fluxo humano do Mafra continua no Collector. Eventos técnicos e feedback de usuários precisam de entradas próprias, com origem, consentimento quando aplicável e identidade limitada; não devem depender de Mafra exportar ZIP manualmente.

## 6. Achados, gargalos e riscos

Achados por inspeção de código; riscos potenciais abaixo não são incidentes comprovados.

| Prioridade | Evidência | Consequência e tratativa |
|---|---|---|
| P0 antes de exposição pública | config.py assume dev; frontend/api.ts envia X-Dev-Actor; painel permite selecionar ator | Modo local não é login real. Exigir configuração explícita de produção e autenticação no frontend; testar rejeição do cabeçalho em produção |
| P0 para autonomia | liveops.run_monitor usa shell=True, ambiente completo e permissões do processo | Código testado pode acessar dados e rede. Runner separado, usuário restrito, ambiente efêmero, comandos permitidos e limites de recursos |
| P1 | Principal agrega roles e product_ids sem preservar associação role/produto/ambiente | Pode aplicar papel de um produto a outro; environment não participa da decisão. Autorizar por tupla de escopo |
| P1 | /live/status consulta last_run global; /audit-events não filtra produto | Metadados de outro projeto podem aparecer para papéis autorizados ao endpoint. Filtrar antes de consultar e testar dois projetos |
| P1 | Ingest usa token global e perde ID externo | Reenvio duplica entradas; credencial sem escopo. Idempotência por projeto/origem/ID e credenciais de integração limitadas |
| P1 | next_human_id lê/incrementa contador; tarefas não têm unicidade por source_feedback_id | Concorrência entre workers pode produzir colisões/duplicação. Sequência atômica, constraint e claim de trabalho |
| P1 | Worker só controla active em memória | Dois processos podem executar o mesmo monitor. Lease persistido, recuperação de jobs interrompidos e retentativas limitadas |
| P1 | stdout/stderr são persistidos sem sanitização; API de runs retorna logs | Código testado pode imprimir segredo. Redação antes de persistir e controle separado de leitura |
| P1 | Execução não zero registra falha, mas não abre tratativa vinculada | Falha pode ficar sem responsável; criar finding/tarefa com evidência e deduplicação |
| P2 | Triagem por palavras-chave | Falso positivo e falso negativo; manter classificação explicável e revisão, sem chamar regra de diagnóstico comprovado |
| P2 | frontend usa dependências latest, sem lockfile encontrado na central | Build pouco reproduzível; fixar versões e lock, depois validar atualização |
| P2 | Contratos JSON não são validação completa de schema | Campos malformados podem provocar erro no importador; validar tipo, tamanho, versão e links de evidência |
| P2 | Collector 0.3.1 inclui bytecode | Pacote contém cache desnecessário; padronizar empacotamento |

Timeout de subprocesso não garante encerramento de toda a árvore de filhos. A captura de saída também precisa de limite durante a execução, não só truncamento após finalizar. O worker chama create_all mesmo fora do ciclo Alembic: padronizar migrations e separar bootstrap de operação.

## 7. Verificação realizada

Ambiente: Linux, Python 3.12. Sem dispositivo Android, Windows, backend remoto ou credenciais de homologação utilizados.

| Verificação | Resultado |
|---|---|
| Parse sintático Python com ast.parse | 103 arquivos: 25 da central, 1 do Collector antigo e 77 do RC6; zero erros de sintaxe |
| Collector 0.4.1: unittest discover | 3 testes aprovados: inspeção/hash, importação preservando ID e rejeição de traversal |
| NexGrana: unittest discover | 131 entradas reportadas: 126 aprovadas e 5 erros; suíte geral não aprovada |
| Backend central: pytest | Bloqueado: pytest ausente; testes não executados |
| Frontend build, containers e migrações | Não executados |
| Windows/Android, fluxo visual e persistência real | Não testados |
| Qualidade visual Nex e microanimações | Não homologadas; requer referência e captura real no app |

Os cinco erros do NexGrana decorreram de módulos ausentes: flet, supabase, fastapi e httpx. Três foram módulos de teste que não carregaram; dois foram casos do gateway. Não há falha funcional comprovada nesses cinco itens, mas também não há aprovação. Nenhuma dependência foi instalada para contornar o bloqueio.

Logs completos desta execução: anexados ao final deste relatório. Saídas de verificações antigas dentro dos ZIPs são histórico, não evidência de execução nesta sessão.

## 8. Arquitetura proposta

Manter FastAPI/SQLAlchemy/Alembic e React. Usar PostgreSQL como fonte operacional central quando homologado, com armazenamento privado de artefatos. Evoluir primeiro um monólito modular e worker coordenado; evitar dezenas de serviços e agentes.

Entidades novas: Release, Artifact, Evidence, Finding, TestRun/TestCaseResult, Decision, Routine, Job/Lease, RegressionCase e IntegrationReceipt. Todas vinculadas a projeto; release opcional em entradas anteriores ao build. Acrescentar descrição/plataformas/repositório/configuração ao Product sem renomear tabelas por estética.

Entrada Collector → validação → receipt/idempotência → inbox/evidence → classificação → tarefa. Entrada autônoma → job/runner → test run/finding → tarefa. O orquestrador resolve prioridades e dependências; alterações preparadas ficam em branch/checkpoint de teste. Gates persistidos encaminham apenas decisões necessárias ao CEO Desk.

Runners recebem especificações de trabalho, não acesso irrestrito ao banco/API. Adaptadores separados para Python, Node, Windows e Android; resultados precisam identificar plataforma, versão das ferramentas, artefato/hash, comando, duração e evidência. Inspeção estrutural, teste automatizado e homologação de dispositivo continuam categorias diferentes.

Daily e CEO Desk usam exclusivamente registros reais. Status obrigatório: implementado, testado, parcialmente testado, não testado, bloqueado, falhou ou aprovado. Promoção exige decisão humana persistida e evidências correspondentes, sem aprovação automática por exit code zero.

## 9. Migração incremental e sequência

| Etapa | Entrega concreta | Critério de aceite |
|---|---|---|
| 1 — Fundação | Expandir Product; adicionar releases, artefatos, evidence e history; corrigir autorização | Migração em banco descartável, isolamento entre dois projetos e restauração de checkpoint verificados |
| 2 — Collector | Importação versionada com ID externo, multipartes, idempotência e anexos privados | Reimportar pacote não duplica; preservar versão/origem/ID; falha parcial não perde itens |
| 3 — QA Engine | Job persistido, lease, runner isolado, resultados e findings | Falha e timeout geram evidência/tarefa; filhos encerrados; secrets e produção inacessíveis |
| 4 — Release Audit | Manifesto/hash por arquivo, baseline estável e seleção de testes por área alterada | Comparação reproduzível; ausência de baseline fica explícita; chat/banco/assets reforçam cobertura |
| 5 — CEO Desk | Decision com problema/evidência/impacto/opções/recomendação/resposta | Aprovar/rejeitar/adiar fica auditado; produção não é promovida sem decisão válida |
| 6 — Rotina | Agenda, retentativas, daily e recuperação após reinício | Reinício não duplica execução; resumo só contém dados reais; falhas de infraestrutura separadas de bugs |
| 7 — Especialização | QA, Security, UX, Product e Intelligence sobre contratos comuns | Ferramentas e autonomia por escopo; recomendação não vira correção sem teste |
| 8 — Interface | Representação empresarial interativa ligada aos jobs | Agente visual só aparece trabalhando com atividade real |

Antes de cada migração: inventário de banco/arquivos, backup protegido, branch/tag e versão do schema. Migrar cópias e validar compatibilidade antes de alterar ambiente ativo. Collector continua exportando o formato atual enquanto o novo adaptador é homologado. Não aplicar migrations do NexGrana como se fossem migrations SIM Labs.

## 10. Próxima ação e limites

A próxima implementação é a Fundação: esquema incremental e autorização correta, antes de upload remoto ou execução autônoma de ZIP. Primeiramente preparar ambiente reproduzível e executar a suíte da central para estabelecer baseline. Depois implementar releases/evidence e o adaptador Collector.

Fase 0 entregue como diagnóstico técnico e plano, com verificação parcial explícita. Homologação dinâmica da central, banco, frontend e dispositivos permanece pendente. Não declarar a plataforma operacional completa nem uma release aprovada com esta auditoria.

## Anexo — log NexGrana desta auditoria

```text
test_admin_filters (test_admin_offers.AdminOffersTests.test_admin_filters) ... ok
test_build_payload_normalizes_safe_fields (test_admin_offers.AdminOffersTests.test_build_payload_normalizes_safe_fields) ... ok
test_draft_may_be_expired_for_repair (test_admin_offers.AdminOffersTests.test_draft_may_be_expired_for_repair) ... ok
test_edit_preserves_product_key (test_admin_offers.AdminOffersTests.test_edit_preserves_product_key) ... ok
test_image_host_allowlist (test_admin_offers.AdminOffersTests.test_image_host_allowlist) ... ok
test_image_requires_accessible_description (test_admin_offers.AdminOffersTests.test_image_requires_accessible_description) ... ok
test_price_and_tags_validation (test_admin_offers.AdminOffersTests.test_price_and_tags_validation) ... ok
test_published_offer_requires_future_expiry (test_admin_offers.AdminOffersTests.test_published_offer_requires_future_expiry) ... ok
test_rejects_untrusted_product_and_image_urls (test_admin_offers.AdminOffersTests.test_rejects_untrusted_product_and_image_urls) ... ok
test_admin_panel (unittest.loader._FailedTest.test_admin_panel) ... ERROR
test_analysis_summary_uses_safe_margin (test_finance.FinanceTests.test_analysis_summary_uses_safe_margin) ... ok
test_automatic_due_expense_debits (test_finance.FinanceTests.test_automatic_due_expense_debits) ... ok
test_automatic_future_expense_stays_future (test_finance.FinanceTests.test_automatic_future_expense_stays_future) ... ok
test_cancelled_expense_is_ignored (test_finance.FinanceTests.test_cancelled_expense_is_ignored) ... ok
test_dates (test_finance.FinanceTests.test_dates) ... ok
test_due_date_debits_automatically (test_finance.FinanceTests.test_due_date_debits_automatically) ... ok
test_due_date_never_invents_payment_confirmation (test_finance.FinanceTests.test_due_date_never_invents_payment_confirmation) ... ok
test_duplicate_ids_are_counted_once (test_finance.FinanceTests.test_duplicate_ids_are_counted_once) ... ok
test_expense_changes_exactly_on_day_twenty (test_finance.FinanceTests.test_expense_changes_exactly_on_day_twenty) ... ok
test_future_expense_does_not_debit (test_finance.FinanceTests.test_future_expense_does_not_debit) ... ok
test_goals (test_finance.FinanceTests.test_goals) ... ok
test_income_is_summed_by_competence_without_inventing_day (test_finance.FinanceTests.test_income_is_summed_by_competence_without_inventing_day) ... ok
test_income_with_month_and_no_date_is_valid (test_finance.FinanceTests.test_income_with_month_and_no_date_is_valid) ... ok
test_income_without_month_or_date_is_rejected (test_finance.FinanceTests.test_income_without_month_or_date_is_rejected) ... ok
test_installments_in_other_month_are_ignored (test_finance.FinanceTests.test_installments_in_other_month_are_ignored) ... ok
test_invalid_money (test_finance.FinanceTests.test_invalid_money) ... ok
test_invalid_share_does_not_change_family_total (test_finance.FinanceTests.test_invalid_share_does_not_change_family_total) ... ok
test_mafra_karol_balance_and_future_bill_exactly (test_finance.FinanceTests.test_mafra_karol_balance_and_future_bill_exactly) ... ok
test_member_snapshot_never_uses_other_person_values (test_finance.FinanceTests.test_member_snapshot_never_uses_other_person_values) ... ok
test_monthly_income_enters_balance (test_finance.FinanceTests.test_monthly_income_enters_balance) ... ok
test_no_margin_no_purchase (test_finance.FinanceTests.test_no_margin_no_purchase) ... ok
test_other_goals (test_finance.FinanceTests.test_other_goals) ... ok
test_other_month_income_is_ignored (test_finance.FinanceTests.test_other_month_income_is_ignored) ... ok
test_paid_flag_does_not_debit_before_due_date (test_finance.FinanceTests.test_paid_flag_does_not_debit_before_due_date) ... ok
test_paused_goal_does_not_commit_margin (test_finance.FinanceTests.test_paused_goal_does_not_commit_margin) ... ok
test_payment_date_does_not_move_expense_between_months (test_finance.FinanceTests.test_payment_date_does_not_move_expense_between_months) ... ok
test_price_limit_is_full_price (test_finance.FinanceTests.test_price_limit_is_full_price) ... ok
test_prior_month_expense_is_ignored (test_finance.FinanceTests.test_prior_month_expense_is_ignored) ... ok
test_rejected_local_mutations_never_change_balance (test_finance.FinanceTests.test_rejected_local_mutations_never_change_balance) ... ok
test_reserve (test_finance.FinanceTests.test_reserve) ... ok
test_rounding_shares (test_finance.FinanceTests.test_rounding_shares) ... ok
test_saved_goal_not_reserved_twice (test_finance.FinanceTests.test_saved_goal_not_reserved_twice) ... ok
test_shared_expense_is_subtracted_once (test_finance.FinanceTests.test_shared_expense_is_subtracted_once) ... ok
test_consent_scope_revocation_and_transport_failure_are_fail_closed (test_gateway_server.GatewayServerTests.test_consent_scope_revocation_and_transport_failure_are_fail_closed) ... ERROR
test_gateway_does_not_treat_client_financial_dict_as_real_records (test_gateway_server.GatewayServerTests.test_gateway_does_not_treat_client_financial_dict_as_real_records) ... ERROR
test_log_identity_is_pseudonymous_and_salted (test_gateway_server.GatewayServerTests.test_log_identity_is_pseudonymous_and_salted) ... ok
test_provider_output_parser_accepts_responses_shape (test_gateway_server.GatewayServerTests.test_provider_output_parser_accepts_responses_shape) ... ok
test_rate_limit_is_per_subject_and_recovers_after_window (test_gateway_server.GatewayServerTests.test_rate_limit_is_per_subject_and_recovers_after_window) ... ok
test_safety_filter_allows_defensive_help (test_gateway_server.GatewayServerTests.test_safety_filter_allows_defensive_help) ... ok
test_annual_rate_uses_monthly_compound_equivalence (test_investments.InvestmentProjectionTests.test_annual_rate_uses_monthly_compound_equivalence) ... ok
test_beginning_contribution_earns_one_more_period (test_investments.InvestmentProjectionTests.test_beginning_contribution_earns_one_more_period) ... ok
test_invalid_period_rate_and_money_are_rejected (test_investments.InvestmentProjectionTests.test_invalid_period_rate_and_money_are_rejected) ... ok
test_negative_rate_costs_and_taxes_are_explicit (test_investments.InvestmentProjectionTests.test_negative_rate_costs_and_taxes_are_explicit) ... ok
test_zero_rate_keeps_only_declared_contributions (test_investments.InvestmentProjectionTests.test_zero_rate_keeps_only_declared_contributions) ... ok
test_market_cloud (unittest.loader._FailedTest.test_market_cloud) ... ERROR
test_confirmed_month_carries_forward_once (test_monthly_ledger.MonthlyLedgerTests.test_confirmed_month_carries_forward_once) ... ok
test_continuity_stops_at_first_unconfirmed_month (test_monthly_ledger.MonthlyLedgerTests.test_continuity_stops_at_first_unconfirmed_month) ... ok
test_late_expense_in_closed_month_recalculates_next_opening (test_monthly_ledger.MonthlyLedgerTests.test_late_expense_in_closed_month_recalculates_next_opening) ... ok
test_member_and_family_closures_are_independent (test_monthly_ledger.MonthlyLedgerTests.test_member_and_family_closures_are_independent) ... ok
test_unconfirmed_prior_month_does_not_carry (test_monthly_ledger.MonthlyLedgerTests.test_unconfirmed_prior_month_does_not_carry) ... ok
test_async_scope_changes_for_user_conversation_and_generation (test_nex_conversation.NexConversationTests.test_async_scope_changes_for_user_conversation_and_generation) ... ok
test_async_scope_comparison_ignores_request_id_but_keeps_conversation (test_nex_conversation.NexConversationTests.test_async_scope_comparison_ignores_request_id_but_keeps_conversation) ... ok
test_intent_keeps_casual_chat_out_of_financial_context (test_nex_conversation.NexConversationTests.test_intent_keeps_casual_chat_out_of_financial_context) ... ok
test_preferred_name_requires_explicit_command (test_nex_conversation.NexConversationTests.test_preferred_name_requires_explicit_command) ... ok
test_short_continuation_keeps_recent_financial_subject (test_nex_conversation.NexConversationTests.test_short_continuation_keeps_recent_financial_subject) ... ok
test_acquisition_uses_specific_entity_and_budget (test_nex_engine.NexEngineTests.test_acquisition_uses_specific_entity_and_budget) ... ok
test_basic_slang_and_nex_suffix_are_natural_locally (test_nex_engine.NexEngineTests.test_basic_slang_and_nex_suffix_are_natural_locally) ... ok
test_connection_help_distinguishes_consent_and_last_success (test_nex_engine.NexEngineTests.test_connection_help_distinguishes_consent_and_last_success) ... ok
test_connection_help_explains_missing_gateway_without_generic_fallback (test_nex_engine.NexEngineTests.test_connection_help_explains_missing_gateway_without_generic_fallback) ... ok
test_defensive_security_question_is_not_blocked (test_nex_engine.NexEngineTests.test_defensive_security_question_is_not_blocked) ... ok
test_engine_does_not_send_message_without_external_ai_consent (test_nex_engine.NexEngineTests.test_engine_does_not_send_message_without_external_ai_consent) ... ok
test_engine_uses_online_gateway_only_for_generic_fallback_with_consent (test_nex_engine.NexEngineTests.test_engine_uses_online_gateway_only_for_generic_fallback_with_consent) ... ok
test_gateway_client_authenticates_and_rejects_invalid_response (test_nex_engine.NexEngineTests.test_gateway_client_authenticates_and_rejects_invalid_response) ... ok
test_gateway_never_replays_ambiguous_post (test_nex_engine.NexEngineTests.test_gateway_never_replays_ambiguous_post) ... ok
test_gateway_payload_has_intent_preferences_and_no_finances_for_casual_chat (test_nex_engine.NexEngineTests.test_gateway_payload_has_intent_preferences_and_no_finances_for_casual_chat) ... ok
test_gateway_payload_limits_conversation_history (test_nex_engine.NexEngineTests.test_gateway_payload_limits_conversation_history) ... ok
test_gateway_refuses_redirect_to_avoid_leaking_bearer_token (test_nex_engine.NexEngineTests.test_gateway_refuses_redirect_to_avoid_leaking_bearer_token) ... ok
test_gateway_requires_public_https_and_minimizes_context (test_nex_engine.NexEngineTests.test_gateway_requires_public_https_and_minimizes_context) ... ok
test_gateway_updates_connection_state (test_nex_engine.NexEngineTests.test_gateway_updates_connection_state) ... ok
test_generic_offline_chat_does_not_query_goals_from_network (test_nex_engine.NexEngineTests.test_generic_offline_chat_does_not_query_goals_from_network) ... ok
test_generic_offline_fallback_does_not_repeat_immediately (test_nex_engine.NexEngineTests.test_generic_offline_fallback_does_not_repeat_immediately) ... ok
test_goal_simulation_has_numeric_scenarios (test_nex_engine.NexEngineTests.test_goal_simulation_has_numeric_scenarios) ... ok
test_household_context_guard_does_not_invent (test_nex_engine.NexEngineTests.test_household_context_guard_does_not_invent) ... nex_failed kind=ValueError
ok
test_preferred_name_command_is_explicit_and_can_be_remembered (test_nex_engine.NexEngineTests.test_preferred_name_command_is_explicit_and_can_be_remembered) ... ok
test_prompt_injection_cannot_extract_other_family_or_secrets (test_nex_engine.NexEngineTests.test_prompt_injection_cannot_extract_other_family_or_secrets) ... ok
test_disabled_and_reduced_motion_are_safe (test_nex_vivo.NexVivoTests.test_disabled_and_reduced_motion_are_safe) ... ok
test_event_changes_visual_state_without_financial_write (test_nex_vivo.NexVivoTests.test_event_changes_visual_state_without_financial_write) ... ok
test_event_cooldown_and_state_antirepetition (test_nex_vivo.NexVivoTests.test_event_cooldown_and_state_antirepetition) ... ok
test_golden_asset_is_final_fallback_and_unapproved_asset_is_ignored (test_nex_vivo.NexVivoTests.test_golden_asset_is_final_fallback_and_unapproved_asset_is_ignored) ... ok
test_multi_click_has_progressive_reactions (test_nex_vivo.NexVivoTests.test_multi_click_has_progressive_reactions) ... ok
test_export_includes_lists_but_only_own_private_chat (test_privacy_and_skins.PrivacyAndSkinsTests.test_export_includes_lists_but_only_own_private_chat) ... ok
test_manual_skin_is_available_outside_its_date_and_cards_stay_in_large_slots (test_privacy_and_skins.PrivacyAndSkinsTests.test_manual_skin_is_available_outside_its_date_and_cards_stay_in_large_slots) ... ok
test_manual_skin_overrides_december_and_auto_returns (test_privacy_and_skins.PrivacyAndSkinsTests.test_manual_skin_overrides_december_and_auto_returns) ... ok
test_occasions_include_festive_and_social_awareness_art (test_privacy_and_skins.PrivacyAndSkinsTests.test_occasions_include_festive_and_social_awareness_art) ... ok
test_analytics_is_off_by_default_and_rejects_financial_payload (test_product_019.Product019Tests.test_analytics_is_off_by_default_and_rejects_financial_payload) ... ok
test_initial_affiliate_catalog_has_six_real_configured_links_without_fake_prices (test_product_019.Product019Tests.test_initial_affiliate_catalog_has_six_real_configured_links_without_fake_prices) ... ok
test_journey_has_ten_steps (test_product_019.Product019Tests.test_journey_has_ten_steps) ... ok
test_nex_quick_actions_are_deterministic (test_product_019.Product019Tests.test_nex_quick_actions_are_deterministic) ... ok
test_offer_ranking_is_independent_from_commission (test_product_019.Product019Tests.test_offer_ranking_is_independent_from_commission) ... ok
test_performance_monitor_summary (test_product_019.Product019Tests.test_performance_monitor_summary) ... ok
test_family_copy_is_explicit (test_product_experience.ProductExperienceTests.test_family_copy_is_explicit) ... ok
test_individual_copy_never_claims_family_scope (test_product_experience.ProductExperienceTests.test_individual_copy_never_claims_family_scope) ... ok
test_journey_has_ten_actionable_steps_and_specialization (test_product_experience.ProductExperienceTests.test_journey_has_ten_actionable_steps_and_specialization) ... ok
test_journey_rewards_derive_only_from_real_progress (test_product_experience.ProductExperienceTests.test_journey_rewards_derive_only_from_real_progress) ... ok
test_backup_round_trip (test_services.ServiceTests.test_backup_round_trip) ... ok
test_breakpoints (test_services.ServiceTests.test_breakpoints) ... ok
test_clear (test_services.ServiceTests.test_clear) ... ok
test_encryption (test_services.ServiceTests.test_encryption) ... ok
test_offer_search_and_category_are_local_and_accent_insensitive (test_services.ServiceTests.test_offer_search_and_category_are_local_and_accent_insensitive) ... ok
test_offers (test_services.ServiceTests.test_offers) ... ok
test_queue_backoff_and_manual_retry (test_services.ServiceTests.test_queue_backoff_and_manual_retry) ... ok
test_queue_cancel_conflict (test_services.ServiceTests.test_queue_cancel_conflict) ... ok
test_queue_conflict (test_services.ServiceTests.test_queue_conflict) ... ok
test_queue_idempotent (test_services.ServiceTests.test_queue_idempotent) ... ok
test_queue_rejects_non_transient_error_without_retry_loop (test_services.ServiceTests.test_queue_rejects_non_transient_error_without_retry_loop) ... ok
test_queue_retry (test_services.ServiceTests.test_queue_retry) ... ok
test_tampering (test_services.ServiceTests.test_tampering) ... ok
test_catalog_contains_all_required_modules (test_tutorial.TutorialTests.test_catalog_contains_all_required_modules) ... ok
test_commit_id_is_stable_for_retry_and_progress_is_separate (test_tutorial.TutorialTests.test_commit_id_is_stable_for_retry_and_progress_is_separate) ... ok
test_expense_only_debits_on_due_date_using_canonical_engine (test_tutorial.TutorialTests.test_expense_only_debits_on_due_date_using_canonical_engine) ... ok
test_legacy_key_migrates_only_same_user_household_member (test_tutorial.TutorialTests.test_legacy_key_migrates_only_same_user_household_member) ... ok
test_new_scope_does_not_accept_old_sandbox_mapping (test_tutorial.TutorialTests.test_new_scope_does_not_accept_old_sandbox_mapping) ... ok
test_refresh_preserves_progress_but_change_of_owner_does_not (test_tutorial.TutorialTests.test_refresh_preserves_progress_but_change_of_owner_does_not) ... ok
test_sandbox_discard_never_creates_commit (test_tutorial.TutorialTests.test_sandbox_discard_never_creates_commit) ... ok
test_training_money_rejects_invalid_input_and_accepts_brazilian_amount (test_tutorial.TutorialTests.test_training_money_rejects_invalid_input_and_accepts_brazilian_amount) ... ok
test_unscoped_progress_is_not_trusted_for_another_account (test_tutorial.TutorialTests.test_unscoped_progress_is_not_trusted_for_another_account) ... ok
test_basket_exact_change_and_edit (test_tutorial_activities.TutorialActivityTests.test_basket_exact_change_and_edit) ... ok
test_goal_progress_and_monthly_need (test_tutorial_activities.TutorialActivityTests.test_goal_progress_and_monthly_need) ... ok
test_income_is_practice_and_competence_is_explicit (test_tutorial_activities.TutorialActivityTests.test_income_is_practice_and_competence_is_explicit) ... ok
test_investment_is_projection_without_real_record (test_tutorial_activities.TutorialActivityTests.test_investment_is_projection_without_real_record) ... ok
test_ui (unittest.loader._FailedTest.test_ui) ... ERROR

======================================================================
ERROR: test_admin_panel (unittest.loader._FailedTest.test_admin_panel)
----------------------------------------------------------------------
ImportError: Failed to import test module: test_admin_panel
Traceback (most recent call last):
  File "/opt/codex/runtimes/codex-primary-runtime/dependencies/python/lib/python3.12/unittest/loader.py", line 396, in _find_test_path
    module = self._get_module_from_name(name)
             ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/opt/codex/runtimes/codex-primary-runtime/dependencies/python/lib/python3.12/unittest/loader.py", line 339, in _get_module_from_name
    __import__(name)
  File "/workspace/scratch/1553e693eef5/audit_extracted/2/NexGrana/tests/test_admin_panel.py", line 7, in <module>
    import flet as ft
ModuleNotFoundError: No module named 'flet'


======================================================================
ERROR: test_consent_scope_revocation_and_transport_failure_are_fail_closed (test_gateway_server.GatewayServerTests.test_consent_scope_revocation_and_transport_failure_are_fail_closed)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/workspace/scratch/1553e693eef5/audit_extracted/2/NexGrana/tests/test_gateway_server.py", line 52, in test_consent_scope_revocation_and_transport_failure_are_fail_closed
    from fastapi import HTTPException
ModuleNotFoundError: No module named 'fastapi'

======================================================================
ERROR: test_gateway_does_not_treat_client_financial_dict_as_real_records (test_gateway_server.GatewayServerTests.test_gateway_does_not_treat_client_financial_dict_as_real_records)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/workspace/scratch/1553e693eef5/audit_extracted/2/NexGrana/tests/test_gateway_server.py", line 72, in test_gateway_does_not_treat_client_financial_dict_as_real_records
    module=self._app()
           ^^^^^^^^^^^
  File "/workspace/scratch/1553e693eef5/audit_extracted/2/NexGrana/tests/test_gateway_server.py", line 49, in _app
    return importlib.import_module("gateway.app")
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/opt/codex/runtimes/codex-primary-runtime/dependencies/python/lib/python3.12/importlib/__init__.py", line 90, in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "<frozen importlib._bootstrap>", line 1387, in _gcd_import
  File "<frozen importlib._bootstrap>", line 1360, in _find_and_load
  File "<frozen importlib._bootstrap>", line 1331, in _find_and_load_unlocked
  File "<frozen importlib._bootstrap>", line 935, in _load_unlocked
  File "<frozen importlib._bootstrap_external>", line 999, in exec_module
  File "<frozen importlib._bootstrap>", line 488, in _call_with_frames_removed
  File "/workspace/scratch/1553e693eef5/audit_extracted/2/NexGrana/gateway/app.py", line 10, in <module>
    import httpx
ModuleNotFoundError: No module named 'httpx'

======================================================================
ERROR: test_market_cloud (unittest.loader._FailedTest.test_market_cloud)
----------------------------------------------------------------------
ImportError: Failed to import test module: test_market_cloud
Traceback (most recent call last):
  File "/opt/codex/runtimes/codex-primary-runtime/dependencies/python/lib/python3.12/unittest/loader.py", line 396, in _find_test_path
    module = self._get_module_from_name(name)
             ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/opt/codex/runtimes/codex-primary-runtime/dependencies/python/lib/python3.12/unittest/loader.py", line 339, in _get_module_from_name
    __import__(name)
  File "/workspace/scratch/1553e693eef5/audit_extracted/2/NexGrana/tests/test_market_cloud.py", line 10, in <module>
    from cloud import Cloud, ReauthenticationRequired, SessionUnavailable
  File "/workspace/scratch/1553e693eef5/audit_extracted/2/NexGrana/src/cloud.py", line 11, in <module>
    from supabase import create_client
ModuleNotFoundError: No module named 'supabase'


======================================================================
ERROR: test_ui (unittest.loader._FailedTest.test_ui)
----------------------------------------------------------------------
ImportError: Failed to import test module: test_ui
Traceback (most recent call last):
  File "/opt/codex/runtimes/codex-primary-runtime/dependencies/python/lib/python3.12/unittest/loader.py", line 396, in _find_test_path
    module = self._get_module_from_name(name)
             ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/opt/codex/runtimes/codex-primary-runtime/dependencies/python/lib/python3.12/unittest/loader.py", line 339, in _get_module_from_name
    __import__(name)
  File "/workspace/scratch/1553e693eef5/audit_extracted/2/NexGrana/tests/test_ui.py", line 13, in <module>
    import flet as ft
ModuleNotFoundError: No module named 'flet'


----------------------------------------------------------------------
Ran 131 tests in 0.026s

FAILED (errors=5)

```
