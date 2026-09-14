# Correções — NexGrana 0.19.0 RC4

## Falha corrigida

A RC3 aplicava uma lógica acumulada e inferia datas para registros antigos. Isso fazia o painel somar valores de outras competências e exibir saldos sem relação com o mês aberto.

## Implementação

- removida a inferência do primeiro dia do mês para rendas sem data;
- removido o saldo cumulativo de competências anteriores;
- despesas são efetivadas pela data de vencimento, independentemente de marcações legadas;
- despesas futuras não alteram o saldo atual;
- removida a pendência histórica do cartão mensal;
- rótulos da Home agora distinguem saldo atual e saldo projetado;
- adicionadas regressões exatas por pessoa e para a transição do dia 19 para o dia 20.

O motor não escreve no Supabase e não corrige valores silenciosamente. Registros sem dados suficientes são apenas sinalizados.
