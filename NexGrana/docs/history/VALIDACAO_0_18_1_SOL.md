# Validação — NexGrana 0.18.1 SOL

## Executado neste ambiente

- `python -m compileall -q src`: **PASSOU**.
- `python validate_release.py`: **PASSOU**.
- 39 testes independentes de Flet/Supabase: **PASSARAM**.
  - `tests.test_finance`
  - `tests.test_services`
  - `tests.test_nex_engine`
- O ZIP final recebe teste de integridade após empacotamento.

## Não foi possível executar neste ambiente

O ambiente de preparação não possui `flet` nem `supabase` e não tem acesso de rede para instalá-los. Por isso:

- `tests.test_ui` não foi executado aqui;
- `tests.test_market_cloud` não foi executado aqui;
- build Windows real não foi gerado aqui;
- APK real não foi gerado aqui;
- câmera/secure storage não foram validados em aparelho físico aqui.

Isso é limitação do ambiente, não evidência de sucesso ou falha dessas partes. Rode `py validate_release.py --full` no Windows após instalar `requirements.txt`.

## SQL

A base 0.18.0 já possuía evidência de execução idempotente em PGlite isolado. A nova `MIGRATION_0_18_1.sql` foi revisada estaticamente, mas deve ser rodada primeiro em Supabase de staging. Não foi aplicada automaticamente ao banco real.

## Critério para promover RC a release pública

1. `py validate_release.py --full` sem falhas.
2. Migrations aplicadas duas vezes em staging sem erro/idempotência quebrada.
3. Smoke test com duas contas/famílias para RLS.
4. Windows build + login + sync + logout + backup.
5. Android APK + login + teclado/chat + câmera/galeria + troca de perfil + rotação/reabertura.
6. Teste de rede instável/offline sem falso saldo zero.
7. Revisão visual em 360/390/430/768/1366/1920.
8. Revisão jurídica final da política LGPD e publicação de controlador/contato/retenção/suboperadores.
