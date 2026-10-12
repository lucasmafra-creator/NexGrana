# Correções NexGrana 0.19.0 RC3 — compatibilidade financeira

A RC3 corrige a leitura do histórico criado antes das colunas de confirmação financeira da 0.18.

- Renda com status recebido e sem `received_at` usa a própria competência MM/AAAA para o cálculo, sem gravar uma data inventada no banco.
- Despesa explicitamente marcada como paga e sem `paid_at` usa o vencimento como evidência legada, também sem alterar o banco.
- Pendências de meses anteriores permanecem visíveis para revisão, mas não são misturadas às próximas contas nem debitadas novamente da projeção do mês selecionado.
- A Home deixa claro que o saldo projetado considera compromissos do mês.
- Três testes de regressão reproduzem exatamente essas incompatibilidades.

O saldo continua acumulado: entradas recebidas menos saídas efetivamente pagas até a data de corte, incluindo o resultado anterior. As inferências legadas são apresentadas como avisos para que o usuário informe os dias exatos quando desejar.
