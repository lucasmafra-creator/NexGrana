# NexGrana 0.24.0 QA RC2.1 — Layout Fix

Correção cirúrgica preparada após validação visual em Windows.

## Ajustes
- Mercado/Listas: largura útil limitada no desktop, fundo alinhado ao tema e rolagem automática para evitar bloco vazio gigante.
- Achados: mesma correção de largura/fundo.
- Nex Chat: área de conversa encapsulada em superfície própria, composer preservado e layout centralizado.
- Hero do Nex compactado no desktop para liberar espaço vertical.
- Gateway público configurado no build: https://nexgrana-gateway.onrender.com/v1/chat

## Validação
- Sintaxe Python dos arquivos alterados: OK.
- A suíte completa deve ser executada no ambiente do projeto com `VALIDAR_0_24.cmd` antes dos builds finais.

## Próximo gate
Validar visualmente Mercado e Nex no Windows e, se aprovado, seguir para build Windows e Android.
