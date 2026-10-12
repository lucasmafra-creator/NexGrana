# Auditoria visual preliminar — RC2, 2026-09-27

Fonte: código da RC2 e descrição do proprietário. O vídeo
`https://youtu.be/FWE3qUOfI-8` não pôde ser reproduzido neste ambiente
(acesso bloqueado); não atribuir resolução, timestamp ou screenshots ao vídeo.
Esta limitação impede declarar a homologação visual concluída.

| Problema | Tela | Causa provável no código | Componente | Correção | Critério de aceite |
| --- | --- | --- | --- | --- | --- |
| Cartões esticam e deixam espaço vazio | Mercado/Listas | `Container(expand=True)` envolve a coluna inteira sem limitar largura; formulário usa `Row` com `TextField(expand=True)` | `market_screen`, `_shopping_lists_panel` | Área com largura máxima, colunas compactas e scroll vertical previsível | Lista pequena usa altura do conteúdo em desktop e mobile |
| Campo e sugestões competem com histórico | Nex | Hero, faixa, banner, spacer, lista, sugestões e composer dividem a mesma coluna | `chat_screen` | Header compacto, histórico expandido, composer fora da rolagem | Mensagens e composer simultaneamente visíveis, teclado não bloqueia saída |
| Modal de privacidade difícil de usar | Privacidade | Texto integral de política seguido de toggles em modal limitado | `privacy_dialog` | Consentimentos no início, detalhes recolhíveis/área separada, ação salvar acessível | Consentimentos compreensíveis em 360×800 e 1366×768 |
| Saldo hipotético exige formulário | Tutorial | Módulo `balance` antecede renda/despesa e desenha 4 campos | `TUTORIAL_MODULES`, `_tutorial_balance_activity` | Mover após despesa, explicar diferença temporal sem entrada obrigatória | Quarta etapa, sem registrar números de treino |
| Confusão entre concluir e próximo | Tutorial | `save_training` marca concluído, rodapé exibe Próximo para concluir novamente | `_navigation_controls` | Uma ação principal contextual após prática | Conclusão e avanço sem dupla confirmação implícita |
| Nex treino não preserva conversa | Tutorial | `reply` único sobrescrito a cada mensagem | `_tutorial_interactive_activity` | Histórico temporário multi turno em sandbox | Ao menos três mensagens visíveis em ordem |
| Superfícies claras indevidas | Todas | Tema embutido ou componente Flet herdando superfície não definida | `ui/theme.py`, cards/diálogos | Aplicar cor de página/superfície explicitamente e auditar controles | Nenhum bloco claro não intencional no modo escuro |

Validação visual manual do vídeo e de builds Windows/Android continua pendente.
