# Alterações — 2026-10-06
Versão de produto preservada: NexGrana 0.24.0 / SIM Labs 0.4.0. Esta rodada não é promoção para release.

## NexGrana
- Chat preserva composer montado e captura conversa/perfil/histórico por requisição; timestamps UTC e ordenação de mensagens.
- Exclusão de mensagens por hora/dia/semana/mês/ano com confirmação, escopo e tombstones; mensagens legadas sem timestamp válido são preservadas.
- Conhecimento offline versionado 2026.10.06.1, 14 tópicos; orientação geral separada de finanças verificadas.
- Fechamento familiar em RPC atômica; competência validada, rejeições não carregam saldo local. Aviso de schema apresenta próxima ação.
- Mercado: restante via Decimal, entrada com foco, OCR Tesseract opcional local, limite editável confirmado, histórico imutável e controle de concorrência.
- QA reset apresenta pré-condições específicas sem contornar permissões.
- 36 outfits RGBA: 768 px para personagem e 128 px para avatar. Cards antigos preservados para reversão; seis masters inalterados.
- Migrações novas: MIGRATION_0_25_1.sql (mensagens), _2 (orçamento), _3 (fechamento em lote). Aplicação somente após revisão em staging.

## SIM Labs
- Backup SQLite fecha explicitamente conexões; retry limitado de snapshot bloqueado preserva backup e snapshot irremovível; DATABASE_URL respeitado.
- Inicialização no boot opt-in S4U com bateria liberada; não aplicada ao Windows ativo.
- Runner manual de código confiável em cópia isolada, comandos fixos, timeout, hashes, diff e terminação restrita. Sem sandbox real de arquivos/rede.
- Registro de artefato local com SHA-256, sem execução; seleção de build concluído exige caminho, tamanho e hash correspondentes.
- Importação de relatório no Release & QA com evidência e deduplicação release/hash. Pode encaminhar missão para REVIEW, nunca DONE automático.
- Migration Alembic 0005_runner_reports incremental e painel de importação compilado.
- Corrigido durante teste final: preservar caminho do Python da venv sem resolver symlink para o interpretador base.

## Complemento RC7 — 2026-10-06 (horário de São Paulo)
- 0.25.4: nota+despesa+rateio+vínculo em uma transação, sem duplicar após retry; cashback não abate despesa automaticamente. Vínculo impede ressuscitar uma despesa excluída manualmente.
- 0.25.5: edição/remoção recuperável com registro da ação e desfazer validando estado atual. Trip removida conserva despesas. Produtos removidos não contam no carrinho. Limite desfeito gera nova alteração auditada.
- Finalização offline entra na fila cifrada; somente após confirmação a compra financeira fecha. Rejeição remove visão otimista do ledger. Replay lê despesa autoritativa para preservar edição posterior.
- UI oferece opt-in, data e confirmação para lançar despesa no perfil; protege troca de perfil e clique duplo.
- OCR real exercitado com imagem sintética local; nenhum upload de foto.
- Auditor técnico de 72 variantes verifica hash, dimensões, RGBA e recorte, sem fingir aprovação estética.
- Preflight nativo e CONCLUIR_RODADA_QA.cmd encadeiam checks/build, com registro opcional Windows+APK na Central. Relatório de build contém origem/dependências reais. CMD/PowerShell não foram executados no Windows aqui.
