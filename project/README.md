# NexGrana 0.19.0 SOL — Virada RC4 saldo validado

A RC4 corrige o cálculo financeiro para seguir uma regra única, mensal e auditável. Ela não carrega saldo histórico, não infere datas e não altera registros no Supabase durante o cálculo.

## Regra financeira oficial

- saldo atual da pessoa = rendas da competência selecionada − despesas dessa competência cuja data de vencimento já chegou;
- saldo atual da família = soma dos saldos atuais das pessoas;
- despesa com vencimento posterior ao dia atual aparece como futura e não reduz o saldo atual;
- no próprio dia do vencimento a despesa passa a reduzir o saldo;
- saldo projetado = saldo atual − despesas futuras do mesmo mês;
- renda ou despesa de outro mês não entra no saldo da competência aberta;
- valores sem competência/data suficiente são sinalizados; o NexGrana não inventa informação.

Exemplo de regressão incluído na suíte:

- Mafra: R$ 2.016,00 − R$ 1.815,21 = R$ 200,79;
- Karol: R$ 1.783,09 − R$ 1.700,44 = R$ 82,65;
- família: R$ 200,79 + R$ 82,65 = R$ 283,44;
- uma conta de R$ 10,00 vencendo no dia 20 fica futura até o dia 19 e só desconta no dia 20.

## Validação automatizada da RC4

Executada no GitHub Actions em Python 3.11 e 3.14:

```text
versão/manifesto Nex: OK
compileall: OK
58 testes Python: OK
migrations SQL 0.18, 0.18.1 e 0.19: OK
testes RLS, isolamento familiar e atomicidade: OK
pip check: OK
ZIP e SHA-256: gerados somente após aprovação da matriz
```

A suíte também cobre Flet, Supabase, fluxo assíncrono do Nex, telas responsivas e falha de conexão sem resposta financeira inventada.

## Antes de publicar

A automação valida código, testes, SQL e integridade do ZIP. Windows e Android reais ainda precisam dos testes manuais de login, lançamentos, troca de perfil, teclado, câmera e navegação descritos em `VALIDACAO_0_19_0_SOL.md`.

Nenhuma migration é aplicada automaticamente ao Supabase real. As migrations da 0.19 já aplicadas com sucesso não precisam ser executadas novamente.
