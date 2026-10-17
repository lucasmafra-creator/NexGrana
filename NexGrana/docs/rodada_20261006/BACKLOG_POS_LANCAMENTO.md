# Pendências e gates
## Antes de liberar Windows/Android
1. Aplicar migrations revisadas em Supabase staging e reproduzir seis IDs com contas descartáveis isoladas.
2. Compilar EXE/APK no ambiente correto; registrar hash/build report, instalar em QA e testar funcionamento real.
3. Mercado: homologar em staging/dispositivo a finalização compra→despesa e desfazer agora implementados; validar duas contas e conflito entre aparelhos.
4. QA visual e teclado/rotação/voltar/offline nos tamanhos pedidos e Moto G22; confirmar que o foco não conflita com conversas.
5. OCR Android/barcode: solução e dependências nativas ainda ausentes; Pillow/Tesseract Windows requer validação de empacotamento. OCR desktop real passou com uma imagem sintética; isto não valida Android.
6. Validar boot Windows, tarefas Runner/Bridge e recuperação, preservando módulos customizados ativos.
7. Revisar efeitos de exclusão em dois dispositivos; ausência de undo temporário de mensagens permanece explícita.

## Integrações e evolução
- Achados diário/afiliados: EXTERNAL_BLOCKER até feed oficial, contrato/credenciais/limites aprovados.
- Feedback público autenticado separado do Collector interno: contrato/consentimento e retenção ainda a definir.
- Sandbox real para runner antes de execução automática de código não confiável.
- Livro operacional SIM Labs conforme OPERACAO_FINANCEIRA.md; especificado, não implementado.
- Auditoria visual completa e métricas de usabilidade continuam sem evidência nativa.
- iOS depois dos gates Windows/Android: macOS/Xcode, assinatura Apple, dependências Flet/plugins, armazenamento, câmera/permissões, Safe Area, teclado/voltar, builds e TestFlight autorizados. Não abrir outro backend ou reativar Nex Online.
