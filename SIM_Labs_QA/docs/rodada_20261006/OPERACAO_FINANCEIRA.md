# Livro operacional SIM Labs — proposta, não implementado
Banco separado das finanças de usuários. Registros: receitas/despesas, competência, data, fornecedor, categoria, centro de custo, assinatura/infra, valor BRL, previsto/realizado e comprovante opcional com acesso restrito. Movimentos auditáveis, sem pagamentos automáticos.

Visões: orçamento mensal, previsto×realizado, despesas recorrentes, contribuição, caixa disponível e runway = caixa / consumo líquido mensal positivo. Se consumo for zero/negativo, exibir condição, não infinito fictício. Importação com chave externa e deduplicação; fechamento e exportação CSV revisáveis. Não é contabilidade fiscal certificada.

Próxima implementação: schema próprio + migration incremental, RBAC, UI manual, testes Decimal/datas/idempotência/isolamento. Solicitar autorização específica antes de integrar bancos, dados reais ou pagamentos. Nesta rodada não foi criado backend alternativo financeiro.
