# Validação — NexGrana 0.19.0 SOL Virada RC2

Data da validação automatizada: 14/09/2026.

## Resultado aprovado

A branch de revisão executou uma matriz limpa em Python 3.11 e Python 3.14 com as dependências fixadas em `requirements.txt`.

Resultados em ambas as versões:

- versão 0.19.0 e arquivos obrigatórios: OK;
- manifesto e variantes canônicas do Nex: OK;
- compilação completa de `src`: OK;
- `pip check`: OK;
- 53 testes Python: OK;
- telas testadas em 360, 390, 430, 768, 1366 e 1920 px: OK;
- diálogos principais: OK;
- dispatcher assíncrono e respostas do Nex: OK;
- falha de conexão sem inventar valores: OK;
- migrations e testes SQL/RLS: OK;
- integridade interna do ZIP: OK;
- SHA-256 do pacote: gerado automaticamente.

## SQL e segurança validados

A sequência testada foi:

1. `supabase_schema.sql`;
2. `SUPABASE_PATCH_V2_RC.sql`;
3. `SUPABASE_SECURITY_0_17.sql`;
4. `MIGRATION_0_18.sql`;
5. `SQL_ATOMIC_0_18.sql`;
6. `MIGRATION_0_18_1.sql`;
7. `MIGRATION_0_19.sql`.

Os testes cobrem isolamento entre famílias, bloqueio de leitura anônima, referências cruzadas, elevação indevida de membro, idempotência, rateios inválidos, rollback atômico, contribuições de meta e fechamento de compra.

## Correções confirmadas na RC2

- ícone incompatível `EVENT_UPCOMING` substituído por `EVENT`;
- `helper_text` incompatível substituído por `helper`;
- testes atualizados para o dispatcher assíncrono real;
- falha de renderização não interrompe mais a resposta segura do Nex;
- teste SQL deixou de apontar para arquivo inexistente;
- migrations 0.18.1 e 0.19 passaram a fazer parte da validação SQL;
- manifesto de arquivos e hashes é regenerado durante o empacotamento.

## Ainda exige teste manual

A automação não substitui estes testes em dispositivo real:

- renderização e navegação no Windows;
- teclado/IME, navegação inferior e botão Enviar no Android;
- câmera e permissões Android;
- geração final de `.exe` e `.apk`;
- login e operações contra um projeto Supabase de homologação;
- troca simultânea de perfil em dois aparelhos;
- acessibilidade com leitor de tela e fonte ampliada;
- desempenho p50/p95 no notebook e celular do usuário.

Nenhuma migration é aplicada automaticamente a um Supabase real.

## Teste recomendado no Windows

```bat
py -m pip install -r requirements.txt
py validate_release.py --full
py -m flet.cli run src
```

Somente depois do teste manual deve-se gerar Windows/APK usando os comandos de `COMANDOS_0_19_0_WINDOWS_ANDROID.txt`.
