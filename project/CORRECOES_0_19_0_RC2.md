# Correções — NexGrana 0.19.0 SOL Virada RC2

## Código

- `src/screens/home.py`: substituição do ícone inexistente `EVENT_UPCOMING`.
- `src/screens/analysis.py`: mesma correção no indicador de compromissos futuros.
- `src/screens/planning.py`: uso do parâmetro `helper` compatível com Flet 0.86.5.
- `src/screens/nex.py`: proteção da renderização anterior ao dispatcher para que uma falha visual ou de dados não interrompa a resposta segura do Nex.

## Testes

- `tests/test_ui.py`: página falsa executa coroutines; testes verificam aceite da fila e a mensagem final do chat.
- O cenário de indisponibilidade comprova que o Nex não inventa valores e não deixa a exceção escapar.
- `tests/test_sql.mjs`: removida referência a arquivo ausente, eliminadas migrations duplicadas e adicionadas 0.18.1/0.19.

## Resultado

- 53 testes Python aprovados em Python 3.11 e 3.14.
- Todas as telas e diálogos cobertos pela suíte foram construídos sem erro.
- Sequência completa das migrations aprovada no PGlite.
- Testes RLS, isolamento familiar, atomicidade e idempotência aprovados.
- Dependências Python aprovadas pelo `pip check`.
- ZIP verificado internamente e acompanhado de SHA-256.

## Limite honesto

O pacote é uma base de código validada automaticamente. Ele não declara que câmera, teclado Android, Supabase real ou build nativo foram comprovados sem o teste manual em dispositivo.
