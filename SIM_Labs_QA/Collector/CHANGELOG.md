# Histórico de alterações

## 0.4.1 — Exclusão em lote

- Permite selecionar várias linhas e excluí-las em uma única confirmação.
- Adiciona “Selecionar visíveis” para aplicar uma busca/filtro e selecionar só os resultados atuais.
- Mantém o console SIM Labs local e seus relatórios no mesmo pacote.

## 0.4.0 — Console SIM Labs local

- Adiciona tela de builds, verificações, feedbacks e checklist de dispositivo.
- Confere pacote sem executar o aplicativo e registra SHA-256, versão e relatório.
- Executa testes de código apenas após confirmação explícita; não instala dependências nem afirma isolamento de rede/processos.
- Mescla partes do Collector por ID e preserva o status de QA já registrado.
- Mantém feedback aberto até confirmação humana de teste funcional.
- Documenta os limites locais e o desenho do control plane futuro.

## 0.3.1 — Correção de exportação

- Corrige geração de ZIP e torna falhas visíveis.
- Abre a pasta de destino automaticamente e preserva corretamente dados no EXE.
- Evidências grandes sem FFmpeg não bloqueiam a criação do pacote.

## 0.3.0 — SIM Labs Bridge

- Adiciona evidências múltiplas, vídeo, ZIP(s) para Work, manifesto e contrato de ingestão.
- Adiciona busca, filtros, duplicação, status e autosave.
