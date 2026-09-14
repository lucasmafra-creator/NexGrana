# Hotfix Android Nex — RC2

Foco desta candidata: corrigir a tela do Nex no Android.

Mudanças:
- envio manual usa handler assíncrono direto; botão Enviar e Enter passam pelo mesmo pipeline `_dispatch_nex_message`;
- sugestões rápidas usam o mesmo pipeline assíncrono, sem `page.run_task` intermediário;
- ao focar o campo de mensagem no celular, cabeçalho grande, hero do Nex e sugestões são recolhidos temporariamente para liberar espaço ao teclado;
- ao sair do campo, esses blocos reaparecem;
- composer ganhou padding inferior e texto maior no mobile para não ficar colado à navegação;
- nenhuma regra financeira ou banco foi alterado por este hotfix.

Validação local disponível neste ambiente:
- `python -m compileall -q src` passou;
- `src/screens/nex.py` passou em `py_compile`.

Ainda requer teste real em Android porque comportamento de teclado/IME depende do aparelho e do runtime Flutter/Flet.
