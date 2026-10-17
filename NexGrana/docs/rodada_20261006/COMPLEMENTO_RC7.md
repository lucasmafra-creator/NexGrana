# Histórico RC7
Este complemento descreve a rodada anterior. O estado atual do RC8 e seus testes está em SIM_LABS_STATUS.md e ANALISE_ENTREGA_RC8.md.

# Pendências de código concluídas — RC7
Mercado: finalizar compra como despesa, com nota+rateio+vínculo atômicos, idempotência, data/perfil confirmados, offline, deduplicação, rollback e leitura do ledger autoritativo; desfazer edição/remoção de item, remoção de compra e ajuste do limite. Cashback permanece informado separadamente. Nenhuma despesa histórica é apagada ao remover compra. Novas migrations 0.25.4/0.25.5 têm teste SQL.

O pedido de “não faltar nada” não permite substituir validação física por testes fake. Windows instalado, Moto G22 e Supabase staging não estão acessíveis neste host. EXE/APK, instalação na Central ativa, reboot/logoff e screenshots reais são dependências de ambiente, registradas em native-environment-report.json e ACCEPTANCE_MATRIX.json, sem conclusão inventada.

CONCLUIR_RODADA_QA.cmd deixa a execução nativa encadeada e reportável. O modo registrar sobe apenas artefatos gerados e verificados para o Release & QA; não lança binários. Fonte pronta para revisão/homologação, não certificada para distribuição. iOS posterior; Nex Online congelado. Automatização de código não confiável permanece desativada sem sandbox real. Nenhum dado privado/produção foi modificado.
