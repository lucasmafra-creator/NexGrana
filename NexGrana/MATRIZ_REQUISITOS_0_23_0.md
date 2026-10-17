# Matriz de requisitos — NexGrana 0.23.0

| Requisito | Implementação | Teste/estado |
| --- | --- | --- |
| Nex conversa geral sem resposta repetitiva fixa | `nex_engine.py`, gateway primeiro para intenção geral | `test_nex_engine` |
| Preferência de nome/tom/detalhe | `nex_conversation.py`, `settings.py` | `test_nex_conversation`, `test_nex_engine` |
| Não enviar finanças em papo casual | intenção + payload minimizado | teste de payload casual |
| Descartar resposta atrasada | `ChatScope` completo em `screens/nex.py` | teste de escopo |
| Sair do teclado Android sem enviar | cabeçalho preservado + botão de teclado | `test_android_chat_keeps_exit...` |
| Tutorial interativo responsivo | `services/tutorial.py`, `screens/tutorial.py` | `test_tutorial`, teste UI Android |
| Despesa só debita no vencimento no tutorial | fixture pelo `finance_engine.snapshot` | teste dias 19/20 |
| Sandbox não grava renda | sessão isolada; sem adaptador de commit para saldo hipotético | teste de descarte |
| Nex Vivo sem regressão visual | `nex_controller.py` + Golden fallback | `test_nex_vivo` e SHA-256 |
| Configuração e redução de movimento | diálogo Nex Vivo + settings | teste disabled/reduced motion |
| Nenhuma regressão financeira | motor não modificado pelo Nex Vivo | suíte financeira completa |

