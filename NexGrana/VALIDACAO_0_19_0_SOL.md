# Validação — NexGrana 0.19.0 SOL Virada RC4

Data da validação automatizada: 14/09/2026.

## Contrato financeiro validado

A RC4 elimina o carregamento cumulativo de rendas e despesas antigas. O recorte é exclusivamente a competência selecionada:

1. renda da competência é somada ao saldo;
2. despesa da mesma competência é futura até a véspera do vencimento;
3. no dia do vencimento ela reduz o saldo atual;
4. saldo familiar é exatamente a soma dos saldos individuais;
5. movimentos de outros meses são ignorados nesse saldo;
6. nenhuma data é inferida e nenhum registro é alterado pelo cálculo.

A regressão usa os valores reais informados: Mafra R$ 200,79, Karol R$ 82,65, família R$ 283,44. Também testa uma despesa de R$ 10,00 no dia 20 antes e no dia do vencimento.

## Resultado automatizado esperado

A branch executa a matriz em Python 3.11 e 3.14:

- versão, manifesto e arquivos obrigatórios: OK;
- compilação completa de `src`: OK;
- `pip check`: OK;
- 58 testes Python: OK;
- telas em 360, 390, 430, 768, 1366 e 1920 px: OK;
- diálogos e dispatcher assíncrono do Nex: OK;
- falha de conexão sem inventar valores: OK;
- migrations e testes SQL/RLS: OK;
- integridade interna do ZIP: OK;
- SHA-256 do pacote: gerado automaticamente.

## SQL e segurança

A sequência coberta permanece:

1. `supabase_schema.sql`;
2. `SUPABASE_PATCH_V2_RC.sql`;
3. `SUPABASE_SECURITY_0_17.sql`;
4. `MIGRATION_0_18.sql`;
5. `SQL_ATOMIC_0_18.sql`;
6. `MIGRATION_0_18_1.sql`;
7. `MIGRATION_0_19.sql`.

Nenhuma migration é aplicada automaticamente ao banco real.

## Teste manual no Windows

```bat
py -m pip install -r requirements.txt
py validate_release.py --full
py -m flet.cli run src
```

Confira no app:

- Mafra: R$ 200,79;
- Karol: R$ 82,65;
- família: R$ 283,44;
- despesas posteriores ao dia atual apenas em “futuras”;
- no vencimento, a despesa deixa “futuras” e reduz o saldo.
